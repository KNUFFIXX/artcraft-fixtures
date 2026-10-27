#!/usr/bin/env python3
"""effectcraft.py (THV-AC03, 14.10.2026) - EffectCraft fixture checks for the PR pre-test.
Linux port of the EffectCraft part of Tools/ac_wc_ec_nachtest.py (same steps and thresholds). Call:
  python3 -I effectcraft.py <effectcraft-cli> <artcraft-fixtures/effectcraft> <out.json> [--work DIR]
Issue: storytold/effectcraft #1442 (MP4 with millisecond frame times read as 30.303 / 58.824 fps).
known_main = EffectCraft 0.9.2 (Windows x64 release) as in the issue."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('effectcraft', sys.argv)
W = ck.work


def meta(name):
    f = ck.fx(name)
    args = ['run', '--empty', '--save-as', os.path.join(W, name + '.ecproj'), '--json',
            'file.import', json.dumps({'paths': [f]}), 'item.metadata', json.dumps({'item': name})]
    rc, so, se = C.run([ck.cli] + args, timeout=180, cwd=W, log_prefix=os.path.join(W, name))
    if '{' not in so:
        raise RuntimeError('no JSON output (rc=%s): %s' % (rc, se.strip()[-300:]))
    j = json.loads(so[so.index('{'):])
    if 'error' in j and 'result' not in j:
        raise RuntimeError('error: %s' % str(j['error'])[:300])
    for r in j.get('result', []):
        if r.get('command') == 'item.metadata':
            it = r['result']['item']
            return it.get('frameRate'), it.get('frames')
    raise RuntimeError('no item.metadata result')


def c1442(rate, name, old):
    def fn():
        fr, frames = meta(name)
        if fr is None:
            return 'no frame rate (frames %s)' % frames, 'ERROR', {'frameRate': fr, 'frames': frames}
        v = 'FIXED' if abs(fr - rate) < 0.01 else ('NOT FIXED' if abs(fr - old) < 0.01 else 'CHANGED')
        return '%s fps, %s frames' % (fr, frames), v, {'frameRate': fr, 'frames': frames}
    return fn


ck.check('ec_fps30_ms_timescale.mp4', 'effectcraft#1442', 'frame rate of an MP4 with ms-rounded frame times',
         '30 fps, 120 frames', '30.303 fps', c1442(30, 'ec_fps30_ms_timescale.mp4', 30.303))
ck.check('ec_fps60_ms_timescale.mp4', 'effectcraft#1442', 'frame rate of an MP4 with ms-rounded frame times',
         '60 fps, 240 frames', '58.824 fps', c1442(60, 'ec_fps60_ms_timescale.mp4', 58.824))

ck.write({'known_main_label': 'EffectCraft 0.9.2', 'known_main_source': 'EffectCraft 0.9.2 Windows x64 release (issue report, ac_wc_ec_nachtest.py)'})
