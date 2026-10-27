"""prv_common.py (THV-AC03, 14.10.2026) - shared helpers for the PR pre-test checks (checks/<app>.py).

Every check script is called as
    python3 -I checks/<app>.py <cli> <fixtures-dir> <out.json> [--work DIR]
<fixtures-dir> is the app folder of a KNUFFIXX/artcraft-fixtures checkout (e.g. .../artcraft-fixtures/filmcraft).
Each result: {"fixture", "issue", "aspect", "what", "role", "expected", "known_main", "actual", "verdict", "detail"}
verdict: FIXED | NOT FIXED | CHANGED | ERROR. role "control" = a sister file that already behaved correctly
(there FIXED means "still correct", CHANGED means it regressed).
Standard library only; nothing is posted anywhere.
"""
import datetime
import json
import os
import platform
import subprocess
import sys
import time
import traceback

VERDICTS = ('FIXED', 'NOT FIXED', 'CHANGED', 'ERROR')


def run(cmd, timeout=300, cwd=None, env=None, log_prefix=None):
    """Runs a command, returns (rc, stdout, stderr); rc is 'TIMEOUT' on timeout. Optionally keeps stdout/stderr files."""
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, cwd=cwd, env=env)
        rc, so, se = p.returncode, p.stdout.decode('utf-8', 'replace'), p.stderr.decode('utf-8', 'replace')
    except subprocess.TimeoutExpired as e:
        rc = 'TIMEOUT'
        so = (e.stdout or b'').decode('utf-8', 'replace') if isinstance(e.stdout, bytes) else (e.stdout or '')
        se = (e.stderr or b'').decode('utf-8', 'replace') if isinstance(e.stderr, bytes) else (e.stderr or '')
    if log_prefix:
        with open(log_prefix + '.out.txt', 'w', encoding='utf-8') as f:
            f.write(so)
        with open(log_prefix + '.err.txt', 'w', encoding='utf-8') as f:
            f.write('# ' + ' '.join(str(c) for c in cmd) + '\n# rc=%s, %.1f s\n' % (rc, time.time() - t0) + se)
    return rc, so, se


class Checker:
    def __init__(self, app, argv):
        a = [x for x in argv[1:]]
        work = None
        if '--work' in a:
            i = a.index('--work')
            work = a[i + 1]
            del a[i:i + 2]
        if len(a) < 3:
            sys.stderr.write('usage: %s <cli> <fixtures-dir> <out.json> [--work DIR]\n' % os.path.basename(argv[0]))
            sys.exit(2)
        self.app = app
        self.cli = os.path.abspath(a[0])
        self.fixtures = os.path.abspath(a[1])
        self.out = os.path.abspath(a[2])
        self.work = os.path.abspath(work or os.path.join(os.path.dirname(self.out), app + '_work'))
        os.makedirs(self.work, exist_ok=True)
        self.results = []
        self.t0 = time.time()
        self.started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')

    def fx(self, name):
        return os.path.join(self.fixtures, *name.split('/'))

    def check(self, fixture, issue, what, expected, known_main, fn, role='repro', aspect=''):
        """fn() -> (actual: str, verdict: str, detail: dict|None). Exceptions become verdict ERROR."""
        e = {'fixture': fixture, 'issue': issue, 'aspect': aspect, 'what': what, 'role': role,
             'expected': expected, 'known_main': known_main}
        t = time.time()
        try:
            actual, verdict, detail = fn()
            if verdict not in VERDICTS:
                raise ValueError('bad verdict ' + repr(verdict))
            e.update(actual=actual, verdict=verdict, detail=detail)
        except Exception as ex:  # noqa: BLE001 - every failure is a result
            e.update(actual='check failed: ' + repr(ex)[:300], verdict='ERROR',
                     detail={'traceback': traceback.format_exc()[-1500:]})
        e['seconds'] = round(time.time() - t, 1)
        self.results.append(e)
        print('%-9s %-18s %-38s %s' % (e['verdict'], issue, fixture + (' [' + aspect + ']' if aspect else ''), e['actual'][:110]), flush=True)
        return e

    def cli_version(self):
        rc, so, se = run([self.cli, '--version'], timeout=30)
        return ((so or se).strip().splitlines() or [''])[0]

    def write(self, extra=None):
        doc = {'app': self.app, 'cli': self.cli, 'cli_version': self.cli_version(), 'fixtures': self.fixtures,
               'work': self.work, 'host': platform.platform(), 'started_utc': self.started,
               'seconds': round(time.time() - self.t0, 1), 'results': self.results}
        if extra:
            doc.update(extra)
        tmp = self.out + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.out)
        return doc


def ratio(fr):
    """{'num': a, 'den': b} -> (float, 'a/b'); None-safe."""
    if not isinstance(fr, dict) or not fr.get('den'):
        return None, str(fr)
    return fr['num'] / fr['den'], '%s/%s' % (fr['num'], fr['den'])


def today_strings():
    """Local and UTC date of 'now' (the CLI may use either), as date objects."""
    return {datetime.date.today(), datetime.datetime.now(datetime.timezone.utc).date()}
