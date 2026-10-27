#!/usr/bin/env python3
"""openmailclient.py (THV-AC10, 24.10.2026) - OpenMailClient checks for the PR pre-test (AdriaanBoshoff/OpenMailClient).
Call:
  python3 -I openmailclient.py <openmailclient-cli> <fixtures-dir> <out.json> [--work DIR]
Issue: AdriaanBoshoff/OpenMailClient #2 (convert .msg -> .eml drops the trailing space of the subject; .msg -> .msg keeps it).
No fixture files: the repro is synthetic and built by the CLI itself from the sample mailbox (run --template sample ...
--save trailing_space.msg), exactly as in the issue. <fixtures-dir> is accepted and ignored.
Target openmailclient#2: "eml subject" (inspect of the converted .eml keeps the trailing space). Controls: the saved .msg
carries the trailing space (precondition), .msg -> .msg keeps it (control from the issue).
known_main = main @ 93002ee (23.10.2026, static musl build): NOT FIXED; the project has no releases, so main-head runs
(pr_vortest.sh openmailclient main --issue 2) are the way to re-test a fix.
Standard library only."""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('openmailclient', sys.argv)
W = ck.work
ISSUE = 'openmailclient#2'
SUBJ = 'Subject with trailing space '
HOME = os.path.join(W, 'home')
os.makedirs(HOME, exist_ok=True)
ENV = dict(os.environ, HOME=HOME, XDG_CONFIG_HOME=os.path.join(HOME, 'cfg'), XDG_DATA_HOME=os.path.join(HOME, 'data'))
N = [0]


def omc(args, tag, timeout=120):
    N[0] += 1
    return C.run([ck.cli] + args, timeout=timeout, cwd=W, env=ENV, log_prefix=os.path.join(W, '%02d_%s' % (N[0], tag)))


def errline(so, se):
    t = (se.strip() or so.strip()).replace(W + os.sep, '').splitlines()
    return t[-1][:200] if t else ''


def find_subject(obj):
    """first 'subject' value anywhere in the inspect JSON (untrusted_content.subject in main @ 93002ee)"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() == 'subject' and isinstance(v, str):
                return v
        for v in obj.values():
            s = find_subject(v)
            if s is not None:
                return s
    elif isinstance(obj, list):
        for v in obj:
            s = find_subject(v)
            if s is not None:
                return s
    return None


def inspect_subject(path, tag):
    rc, so, se = omc(['inspect', path], tag)
    if rc != 0:
        raise RuntimeError('inspect %s rc=%s: %s' % (os.path.basename(path), rc, errline(so, se)))
    try:
        j = json.loads(so[so.index('{'):])
        s = find_subject(j)
    except Exception:  # noqa: BLE001 - fall back to a text line
        m = re.search(r'(?im)^\s*"?subject"?\s*[:=]\s*"?(.*?)"?\s*,?\s*$', so)
        s = m.group(1) if m else None
    if s is None:
        raise RuntimeError('inspect %s: no subject in the output' % os.path.basename(path))
    return s


def show(s):
    return json.dumps(s, ensure_ascii=False)


MSG = os.path.join(W, 'trailing_space.msg')
EML = os.path.join(W, 'out.eml')
MSG2 = os.path.join(W, 'copy.msg')
STATE = {}


def make_msg():
    rc, so, se = omc(['run', '--template', 'sample', '--cmd', 'mail.new',
                      '--cmd', 'compose.setField=' + json.dumps({'field': 'subject', 'value': SUBJ}),
                      '--cmd', 'compose.setField=' + json.dumps({'field': 'to', 'value': 'bob@' + 'example.com'}),
                      '--cmd', 'compose.setField=' + json.dumps({'field': 'body', 'value': 'Synthetic body.'}),
                      '--cmd', 'compose.saveDraft', '--cmd', 'mail.select=' + json.dumps({'folder': 'Drafts', 'index': 0}),
                      '--save', MSG], 'run_save', timeout=300)
    if rc != 0 or not os.path.exists(MSG):
        raise RuntimeError('run --save rc=%s: %s' % (rc, errline(so, se)))
    STATE['msg_subject'] = inspect_subject(MSG, 'inspect_msg')
    return STATE['msg_subject']


def c_precondition():
    s = make_msg()
    ok = s == SUBJ
    return 'saved .msg subject %s' % show(s), 'FIXED' if ok else 'CHANGED', {'subject': s, 'bytes': os.path.getsize(MSG)}


def c_eml():
    if 'msg_subject' not in STATE:
        make_msg()
    rc, so, se = omc(['convert', MSG, EML], 'convert_eml')
    if rc != 0 or not os.path.exists(EML):
        raise RuntimeError('convert .msg -> .eml rc=%s: %s' % (rc, errline(so, se)))
    s = inspect_subject(EML, 'inspect_eml')
    with open(EML, 'rb') as f:
        raw = f.read()
    m = re.search(rb'(?im)^Subject:[ \t]*(.*?)\r?$', raw)
    header = m.group(1).decode('utf-8', 'replace') if m else ''
    ok = s == SUBJ
    return '.eml subject %s (header line %s)' % (show(s), show(header)), 'FIXED' if ok else ('NOT FIXED' if s == SUBJ.rstrip() else 'CHANGED'), \
        {'subject': s, 'header': header, 'bytes': len(raw)}


def c_msg_copy():
    if 'msg_subject' not in STATE:
        make_msg()
    rc, so, se = omc(['convert', MSG, MSG2], 'convert_msg')
    if rc != 0 or not os.path.exists(MSG2):
        raise RuntimeError('convert .msg -> .msg rc=%s: %s' % (rc, errline(so, se)))
    s = inspect_subject(MSG2, 'inspect_msg_copy')
    return '.msg copy subject %s' % show(s), 'FIXED' if s == SUBJ else 'CHANGED', {'subject': s, 'bytes': os.path.getsize(MSG2)}


ck.check('trailing_space.msg (built)', ISSUE, 'saved draft keeps the trailing space of the subject (precondition)', show(SUBJ),
         show(SUBJ), c_precondition, role='control', aspect='msg subject')
ck.check('trailing_space.msg (built)', ISSUE, 'convert .msg -> .eml keeps the trailing space of the subject', show(SUBJ),
         'NOT FIXED: ' + show(SUBJ.rstrip()) + ' (main @ 93002ee)', c_eml, aspect='eml subject')
ck.check('trailing_space.msg (built)', ISSUE, 'convert .msg -> .msg keeps the trailing space of the subject', show(SUBJ),
         show(SUBJ), c_msg_copy, role='control', aspect='msg copy subject')

rc, so, se = omc(['commands'], 'commands')
ver = 'openmailclient-cli (%d commands)' % len([ln for ln in so.splitlines() if ln.strip()]) if rc == 0 else 'openmailclient-cli'
ck.write({'cli_version': ver, 'known_main_label': 'main @ 93002ee (23.10.2026)', 'known_main_source': 'AdriaanBoshoff/OpenMailClient#2 (static musl build of main @ 93002ee)'})
