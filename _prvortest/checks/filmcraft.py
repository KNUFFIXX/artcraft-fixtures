#!/usr/bin/env python3
"""filmcraft.py (THV-AC03, 14.10.2026) - FilmCraft fixture checks for the PR pre-test.
Linux port of Tools/ac_film_nachtest.ps1 (same steps, same thresholds), for a self-built filmcraft-cli.
Call: python3 -I filmcraft.py <filmcraft-cli> <artcraft-fixtures/filmcraft> <out.json> [--work DIR]
Issues: storytold/filmcraft #1700 (frame rate from ms-rounded timestamps), #1701 (5.1 in MP4 read as stereo),
#1702 (empty pixel format), #1791 (SCC export: close caption pops on late), #1792 (EDL round trip at 24 fps).
known_main = the values of the v0.7.2 Windows release (Nachtest 14.10.2026), as in the issues."""
import json
import math
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('filmcraft', sys.argv)
W = ck.work
TICKS_25 = 254_016_000_000 // 25  # ticks per second / 25 (Unterstriche: secret_scan DIGITS, SYS42)


def fc_run(tag, lines, timeout=300):
    """filmcraft-cli run <jsonl> --keep-going; returns {line_no: output object}."""
    jl = os.path.join(W, tag + '.jsonl')
    with open(jl, 'w', encoding='utf-8') as f:
        f.write('\n'.join(json.dumps(x) for x in lines) + '\n')
    rc, so, se = C.run([ck.cli, 'run', jl, '--keep-going', '--data-dir', os.path.join(W, 'datadir'), '--compact'],
                       timeout=timeout, cwd=W, log_prefix=os.path.join(W, tag))
    res = {}
    for ln in so.splitlines():
        if ln.startswith('{'):
            try:
                o = json.loads(ln)
                res[int(o.get('line'))] = o
            except (ValueError, TypeError):
                pass
    if not res:
        raise RuntimeError('no JSON output (rc=%s): %s' % (rc, se.strip()[-300:]))
    return res


def get(r, line, *path):
    o = r.get(line)
    if o is None:
        raise KeyError('no output for script line %d' % line)
    if not o.get('ok', True):
        raise RuntimeError('line %d %s failed: %s' % (line, o.get('id'), str(o.get('error'))[:300]))
    v = o.get('result')
    for p in path:
        v = v[p]
    return v


class Lazy:
    def __init__(self, fn):
        self.fn, self.done, self.val, self.err = fn, False, None, None

    def __call__(self):
        if not self.done:
            self.done = True
            try:
                self.val = self.fn()
            except Exception as e:  # noqa: BLE001
                self.err = e
        if self.err:
            raise self.err
        return self.val


# ---------- WAV + Goertzel (same as Get-Tone in ac_film_nachtest.ps1) ----------
def wav_read(path):
    with open(path, 'rb') as f:
        b = f.read()
    if b[:4] != b'RIFF' or b[8:12] != b'WAVE':
        raise ValueError('not a RIFF/WAVE file: ' + os.path.basename(path))
    pos, fmt, chs, sr, bits, off, ln = 12, 1, 2, 48000, 16, -1, 0
    while pos + 8 <= len(b):
        cid = b[pos:pos + 4]
        size = struct.unpack_from('<I', b, pos + 4)[0]
        if cid == b'fmt ':
            fmt, chs, sr = struct.unpack_from('<HHI', b, pos + 8)
            bits = struct.unpack_from('<H', b, pos + 22)[0]
            if fmt == 0xFFFE and size >= 40:
                fmt = struct.unpack_from('<H', b, pos + 32)[0]
        if cid == b'data':
            off, ln = pos + 8, min(size, len(b) - pos - 8)
            break
        pos += 8 + size + (size % 2)
    if off < 0:
        raise ValueError('no data chunk')
    return {'b': b, 'fmt': fmt, 'channels': chs, 'rate': sr, 'bits': bits, 'off': off, 'len': ln}


def channel(w, ch, start, n):
    bps = w['bits'] // 8
    frame = bps * w['channels']
    b, off = w['b'], w['off']
    end = off + w['len']
    out = []
    for k in range(start, start + n):
        o = off + k * frame + ch * bps
        if o + bps > end:
            break
        if w['bits'] == 16:
            x = struct.unpack_from('<h', b, o)[0] / 32768.0
        elif w['bits'] == 32 and w['fmt'] == 3:
            x = struct.unpack_from('<f', b, o)[0]
        elif w['bits'] == 24:
            x = int.from_bytes(b[o:o + 3], 'little', signed=True) / 8388608.0
        else:
            x = struct.unpack_from('<i', b, o)[0] / 2147483648.0
        out.append(x)
    return out


def tone_db(w, freq, ch):
    """Goertzel magnitude of one channel, 1 s from 0.5 s; a sine of amplitude 1 = 0 dB."""
    sr = w['rate']
    xs = channel(w, ch, int(sr * 0.5), int(sr))
    n = len(xs)
    if n == 0:
        return -999.0
    coef = 2 * math.cos(2 * math.pi * freq / sr)
    s1 = s2 = 0.0
    for x in xs:
        s0 = x + coef * s1 - s2
        s2, s1 = s1, s0
    pw = s1 * s1 + s2 * s2 - coef * s1 * s2
    amp = 2 * math.sqrt(max(pw, 0.0)) / n
    return round(20 * math.log10(amp + 1e-12), 1)


# ---------- #1700 ----------
R1700 = Lazy(lambda: fc_run('c1700', [
    {'id': 'file.newProject', 'params': {'name': 'c1700'}},
    {'id': 'file.import', 'params': {'paths': [ck.fx('fps60_ms_timestamps.mp4')]}},
    {'id': 'mediaBrowser.probe', 'params': {'path': ck.fx('fps30_ms_timestamps.mp4')}},
    {'id': 'mediaBrowser.probe', 'params': {'path': ck.fx('fps60_ms_timestamps.mp4')}},
    {'id': 'file.newSequenceFromClip', 'params': {'items': [1]}},
    {'id': 'sequence.inspect', 'params': {}}]))


def c1700_30():
    v, s = C.ratio(get(R1700(), 3, 'info', 'video', 'frame_rate'))
    ok = v is not None and (abs(v - 30) < 1e-4 or abs(v - 30000 / 1001) < 1e-4)
    old = v is not None and abs(v - 30.303) < 0.001
    return 'probe %s (%.3f fps)' % (s, v), ('FIXED' if ok else 'NOT FIXED' if old else 'CHANGED'), {'frame_rate': s}


def c1700_60():
    r = R1700()
    v, s = C.ratio(get(r, 4, 'info', 'video', 'frame_rate'))
    frames = get(r, 6, 'durationFrames')
    try:
        _, sq = C.ratio(get(r, 6, 'settings', 'frame_rate'))
    except Exception:  # noqa: BLE001 - only for the detail
        sq = '?'
    ok = v is not None and (abs(v - 60) < 1e-4 or abs(v - 60000 / 1001) < 1e-4) and abs(frames - 240) <= 1
    old = v is not None and abs(v - 58.824) < 0.001
    act = 'probe %s (%.3f fps); New Sequence From Clip: %s frames at %s' % (s, v, frames, sq)
    return act, ('FIXED' if ok else 'NOT FIXED' if old else 'CHANGED'), {'frame_rate': s, 'seq_frames': frames, 'seq_rate': sq}


ck.check('fps30_ms_timestamps.mp4', 'filmcraft#1700', 'frame rate of a 90 kHz track with ms-rounded frame times',
         '30/1 (or 30000/1001)', '30303/1000 (30.303 fps)', c1700_30)
ck.check('fps60_ms_timestamps.mp4', 'filmcraft#1700', 'frame rate of a 90 kHz track with ms-rounded frame times',
         '60/1 (or 60000/1001); New Sequence From Clip 240 frames', '7353/125 (58.824 fps); sequence 235 frames', c1700_60)


# ---------- #1701 ----------
def c1701(name, control):
    def fn():
        tag = 'c1701_' + re.sub('[^A-Za-z0-9]', '_', name)
        wav = os.path.join(W, tag + '.wav')
        r = fc_run(tag, [
            {'id': 'file.newProject', 'params': {'name': tag}},
            {'id': 'file.import', 'params': {'paths': [ck.fx(name)]}},
            {'id': 'mediaBrowser.probe', 'params': {'path': ck.fx(name)}},
            {'id': 'file.newSequenceFromClip', 'params': {'items': [1]}},
            {'id': 'file.exportMedia', 'params': {'path': wav, 'format': 'wav', 'range': 'entire', 'wait': True}}])
        chn = get(r, 3, 'info', 'audio_streams')[0]['channels']
        w = wav_read(wav)
        if w['channels'] >= 6:      # 5.1 kept in the export: centre channel (index 2) vs FL
            centre = round(tone_db(w, 500, 2) - tone_db(w, 300, 0), 1)
            present = -6 < centre < 1
            where = 'C channel'
        else:                       # stereo downmix: centre tone in L, about -3 dB below FL
            centre = round(tone_db(w, 500, 0) - tone_db(w, 300, 0), 1)
            present = -6 < centre < 0
            where = 'L of the downmix'
        act = 'probe %s ch; WAV export %s ch, centre tone in %s %.1f dB vs FL' % (chn, w['channels'], where, centre)
        fixed = chn == 6 and present
        if control:
            v = 'FIXED' if fixed else 'CHANGED'
        else:
            v = 'FIXED' if fixed else ('NOT FIXED' if chn == 2 and centre < -60 else 'CHANGED')
        return act, v, {'probe_channels': chn, 'wav_channels': w['channels'], 'centre_rel_db': centre}
    return fn


for n, known in [('surround51_ac3.mp4', 'probe 2 ch; centre in L -139.8 dB (silent)'),
                 ('surround51_eac3.mp4', 'probe 2 ch; centre in L -132.2 dB (silent)'),
                 ('surround51side_aac_pce.mp4', 'probe 2 ch; centre in L -133.0 dB (silent)')]:
    ck.check(n, 'filmcraft#1701', '5.1 in MP4: channel count and centre channel', '6 ch; centre tone present (-6..0 dB vs FL)',
             known, c1701(n, False))
ck.check('surround51_ac3.mov', 'filmcraft#1701', '5.1 in MOV (control, same stream)', '6 ch; centre tone present',
         'probe 6 ch; centre in L -3.1 dB (correct)', c1701('surround51_ac3.mov', True), role='control')

# ---------- #1702 ----------
R1702 = Lazy(lambda: fc_run('c1702', [
    {'id': 'mediaBrowser.probe', 'params': {'path': ck.fx('av1_in_mp4.mp4')}},
    {'id': 'mediaBrowser.probe', 'params': {'path': ck.fx('h264_in_mkv.mkv')}}]))


def c1702(line):
    def fn():
        p = get(R1702(), line, 'info', 'video').get('pixel_format')
        p = '' if p is None else str(p)
        return 'pixel_format "%s"' % p, ('FIXED' if p else 'NOT FIXED'), {'pixel_format': p}
    return fn


ck.check('av1_in_mp4.mp4', 'filmcraft#1702', 'pixel format label (AV1 in MP4)', 'non-empty (yuv420p)', 'empty', c1702(1))
ck.check('h264_in_mkv.mkv', 'filmcraft#1702', 'pixel format label (H.264 in Matroska)', 'non-empty (yuv420p)', 'empty', c1702(2))


# ---------- #1791 ----------
def c1791():
    scc = os.path.join(W, 'c1791.scc')
    seq = [{'id': 'file.newProject', 'params': {'name': 'c1791'}},
           {'id': 'file.import', 'params': {'paths': [ck.fx('edl/clipA.mov')]}},
           {'id': 'file.newSequence', 'params': {'name': 'S', 'width': 640, 'height': 360, 'fps': 25, 'video': 1, 'audio': 1}},
           {'id': 'timeline.place', 'params': {'item': 1, 'track': 'V1', 'frame': 0}}]
    r = fc_run('c1791a', seq + [{'id': 'captions.import', 'params': {'path': ck.fx('scc_tight.srt')}},
                                {'id': 'captions.export', 'params': {'path': scc, 'format': 'scc'}}])
    get(r, 6)
    r = fc_run('c1791b', seq + [{'id': 'captions.import', 'params': {'path': scc}},
                                {'id': 'captions.list', 'params': {}}])
    caps = [c for t in get(r, 6, 'tracks') for c in t.get('captions', [])]
    c2 = str(caps[1]['in'])
    h, m, s, f = [int(x) for x in re.split('[:;.]', c2)]
    fr = h * 90000 + m * 1500 + s * 25 + f
    v = 'FIXED' if fr <= 58 else ('NOT FIXED' if c2 == '00:00:03:07' else 'CHANGED')
    return 'caption 2 back from the SCC at %s' % c2, v, {'caption2_in': c2, 'frames': fr, 'captions': len(caps)}


ck.check('scc_tight.srt', 'filmcraft#1791', 'SCC export: caption 2 (2.24 s) close after caption 1',
         'caption 2 in at about 00:00:02:06, at the latest 00:00:02:08', '00:00:03:07 (pops on 1.1 s late)', c1791)


# ---------- #1792 ----------
def c1792():
    edl = os.path.join(W, 'c1792.edl')
    r = fc_run('c1792a', [
        {'id': 'file.newProject', 'params': {'name': 'c1792'}},
        {'id': 'file.import', 'params': {'paths': [ck.fx('edl/clipA.mov')]}},
        {'id': 'file.import', 'params': {'paths': [ck.fx('edl/clipB.mov')]}},
        {'id': 'file.newSequence', 'params': {'name': 'S25', 'width': 640, 'height': 360, 'fps': 25, 'video': 1, 'audio': 1}},
        {'id': 'timeline.place', 'params': {'item': 1, 'track': 'V1', 'frame': 0, 'sourceIn': 0, 'duration': 100 * TICKS_25}},
        {'id': 'timeline.place', 'params': {'item': 2, 'track': 'V1', 'frame': 100, 'sourceIn': 25 * TICKS_25, 'duration': 100 * TICKS_25}},
        {'id': 'file.exportInterchange', 'params': {'format': 'edl', 'path': edl}}])
    get(r, 7)
    r = fc_run('c1792b', [
        {'id': 'file.newProject', 'params': {'name': 'c1792b'}},
        {'id': 'file.import', 'params': {'paths': [edl]}},
        {'id': 'sequence.inspect', 'params': {}}])
    v, s = C.ratio(get(r, 3, 'settings', 'frame_rate'))
    verdict = 'FIXED' if abs(v - 25) < 0.001 else ('NOT FIXED' if abs(v - 24) < 0.001 else 'CHANGED')
    return 're-imported sequence at %s' % s, verdict, {'reimport_fps': s}


ck.check('edl/clipA.mov + edl/clipB.mov', 'filmcraft#1792', 'EDL of a 25 fps sequence, exported and re-imported',
         're-import at 25/1', '24/1', c1792)

ck.write({'known_main_label': 'FilmCraft 0.7.2', 'known_main_source': 'FilmCraft v0.7.2 Windows x64 release, Nachtest 14.10.2026 (ac_film_nachtest.ps1)'})
