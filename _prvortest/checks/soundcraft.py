#!/usr/bin/env python3
"""soundcraft.py (THV-AC04, 17.10.2026) - SoundCraft fixture checks for the PR pre-test.
Call:
  python3 -I soundcraft.py <soundcraft-cli> <artcraft-fixtures/soundcraft> <out.json> [--work DIR]
Issues: storytold/soundcraft #707 (MP4 edit list ignored: AAC priming stays in), #708 (5.1 AAC "aac too complex"),
#709 (AC-3/E-AC-3 reported as "malformed audio: end of stream"), #710 (MP3 frames with an empty last granule dropped),
#712 (HE-AAC with 48 kHz sample entry at half length / double speed; v2 mono).
Needs ffmpeg/ffprobe (reference decode, control files) and numpy. Controls are built in the work folder:
an AAC-LC MP4 without edit list (remux of aac_priming.m4a, -use_editlist 0), the generator's WAVs (tone_mono_48k,
tone_51_48k, noise_left_44k) and a LAME 320 kbps MP3 of the noise WAV.
known_main = SoundCraft 0.7.0 (Windows x64 release) as in the issues."""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

import numpy as np  # noqa: E402

ck = C.Checker('soundcraft', sys.argv)
W = ck.work
ENV = dict(os.environ, SOUNDCRAFT_NO_PREFS='1', HOME=os.path.join(W, 'home'), XDG_CONFIG_HOME=os.path.join(W, 'cfg'))
os.makedirs(ENV['HOME'], exist_ok=True)
FF = shutil.which('ffmpeg') or 'ffmpeg'
FP = shutil.which('ffprobe') or 'ffprobe'
N = [0]


def sc(args, tag=None, timeout=300):
    N[0] += 1
    return C.run([ck.cli] + args, timeout=timeout, cwd=W, env=ENV, log_prefix=os.path.join(W, '%02d_%s' % (N[0], tag or args[0])))


def errline(so, se):
    t = (se.strip() or so.strip()).replace(ck.fixtures + os.sep, '').replace(GEN + os.sep, '').replace(W + os.sep, '').splitlines()
    return t[-1][:240] if t else ''


def info(path):
    rc, so, se = sc(['info', path], 'info_' + os.path.basename(path))
    if rc != 0 or '{' not in so:
        return None, errline(so, se)
    return json.loads(so[so.index('{'):]), ''


def decode(path):
    """ffmpeg decode of a file -> (float32 frames x ch, rate)"""
    j = json.loads(subprocess.run([FP, '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=channels,sample_rate',
                                   '-of', 'json', path], capture_output=True, timeout=120).stdout)['streams'][0]
    raw = subprocess.run([FF, '-v', 'error', '-i', path, '-f', 'f32le', '-c:a', 'pcm_f32le', '-'], capture_output=True, timeout=300).stdout
    return np.frombuffer(raw, '<f4').reshape(-1, int(j['channels'])), int(j['sample_rate'])


def convert(path):
    """soundcraft-cli convert -> 32-bit float WAV, decoded with ffmpeg. Returns (x, rate, err)."""
    out = os.path.join(W, os.path.basename(path) + '.sc.wav')
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = sc(['convert', path, out, '--bit-depth', '32f'], 'convert_' + os.path.basename(path))
    if rc != 0 or not os.path.exists(out):
        return None, None, errline(so, se) or 'rc=%s' % rc
    x, sr = decode(out)
    return x, sr, ''


def import_audio(path, rate):
    """session.new + file.import_audio -> (imported dict, err)"""
    rc, so, se = sc(['run', '--cmd', 'session.new=' + json.dumps({'sample_rate': rate}),
                     '--cmd', 'file.import_audio=' + json.dumps({'path': path})], 'import_' + os.path.basename(path))
    for ln in so.splitlines():
        if ln.startswith('file.import_audio:'):
            j = json.loads(ln.split(':', 1)[1])
            imp = (j.get('imported') or [None])[0]
            if imp:
                return imp, ''
            return None, str(j)[:200]
    return None, errline(so, se) or 'rc=%s' % rc


def click(x):
    return int(np.argmax(np.abs(x[:, 0])))


def pitch_step(x, sr):
    """time (s) of the first quarter-second window whose peak frequency is > 1.5x the first window's; plus the first freq"""
    w = sr // 4
    fr = []
    for k in range(0, len(x) - w + 1, w):
        s = np.abs(np.fft.rfft(x[k:k + w, 0] * np.hanning(w)))
        fr.append(round(float(np.argmax(s)) * sr / w))
    if not fr:
        return None, None
    for i, f in enumerate(fr[1:], 1):
        if f > 1.5 * fr[0] and fr[0] > 100:
            return round(i * w / sr, 2), fr[0]
    return None, fr[0]


# ---------- controls built in the work folder
GEN = os.path.join(W, 'gen')


def build_controls():
    os.makedirs(GEN, exist_ok=True)
    gen = os.path.join(ck.fixtures, 'make_fixtures_soundcraft.py')
    if not os.path.exists(os.path.join(GEN, 'noise_left_44k.wav')):
        subprocess.run([sys.executable, '-I', gen, FF], cwd=GEN, capture_output=True, timeout=300)
    p = os.path.join(GEN, 'aac_noelst.m4a')
    if not os.path.exists(p):
        subprocess.run([FF, '-v', 'error', '-y', '-nostdin', '-i', ck.fx('aac_priming.m4a'), '-c', 'copy', '-use_editlist', '0',
                        '-map_metadata', '-1', p], capture_output=True, timeout=120)
    p = os.path.join(GEN, 'mp3_lame320_left.mp3')
    if not os.path.exists(p) and os.path.exists(os.path.join(GEN, 'noise_left_44k.wav')):
        subprocess.run([FF, '-v', 'error', '-y', '-nostdin', '-i', os.path.join(GEN, 'noise_left_44k.wav'), '-c:a', 'libmp3lame',
                        '-b:a', '320k', '-map_metadata', '-1', p], capture_output=True, timeout=120)


try:
    build_controls()
except Exception as ex:  # noqa: BLE001 - controls then report ERROR
    print('control build failed:', ex)


def g(name):
    return os.path.join(GEN, name)


# ---------- #707 edit list / priming
def c707(path, want_frames, want_click, old_frames, old_click, tol_frames=200):
    def fn():
        if not os.path.exists(path):
            raise RuntimeError('missing ' + path)
        x, sr, err = convert(path)
        inf, ierr = info(path)
        if x is None:
            return 'convert failed: ' + err, 'CHANGED', {'error': err}
        n, c = len(x), click(x)
        nf = (inf or {}).get('frames')
        ok = abs(n - want_frames) <= tol_frames and abs(c - want_click) <= 8
        old = n == old_frames and abs(c - old_click) <= 8
        v = 'FIXED' if ok else ('NOT FIXED' if old else 'CHANGED')
        return 'convert %d frames, click at %d; info frames %s' % (n, c, nf), v, {'frames': n, 'click': c, 'info_frames': nf, 'rate': sr}
    return fn


ck.check('aac_priming.m4a', 'soundcraft#707', 'AAC-LC in MP4 with edit list (media_time 1024, duration 48000)',
         '48000 frames (ffmpeg 6.1: 48128), click at 24000', '49152 frames, click at 25024',
         c707(ck.fx('aac_priming.m4a'), 48000, 24000, 49152, 25024), aspect='frames/click')
ck.check('aac_noelst.m4a (built)', 'soundcraft#707', 'AAC-LC in MP4 without edit list (aac_priming.m4a remuxed, -use_editlist 0): nothing to trim',
         '49152 frames, click at 25024 (as ffmpeg)', '49152 frames, click at 25024',
         c707(g('aac_noelst.m4a'), 49152, 25024, -1, -1, tol_frames=0), role='control')
ck.check('tone_mono_48k.wav (generator)', 'soundcraft#707', 'source WAV of aac_priming.m4a (measurement check)',
         '48000 frames, click at 24000', '48000 frames, click at 24000',
         c707(g('tone_mono_48k.wav'), 48000, 24000, -1, -1, tol_frames=0), role='control')


# ---------- #708 5.1 AAC
def c708(path, role):
    def fn():
        if not os.path.exists(path):
            raise RuntimeError('missing ' + path)
        imp, err = import_audio(path, 48000)
        if imp is None:
            v = 'NOT FIXED' if 'too complex' in err else 'CHANGED'
            return 'import failed: ' + err, v, {'error': err}
        ch, fr = imp.get('channels'), imp.get('frames')
        x, sr, cerr = convert(path)
        cch = None if x is None else x.shape[1]
        ok = ch == 6 and fr and 47000 <= fr <= 49300
        return 'import %s ch, %s frames; convert %s ch' % (ch, fr, cch), ('FIXED' if ok else 'CHANGED'), {'import': imp, 'convert_channels': cch, 'convert_error': cerr}
    return fn


ck.check('aac_51.m4a', 'soundcraft#708', '5.1 AAC-LC import (file.import_audio, 48 kHz session)', '6 channels, ~48000 frames',
         'unsupported audio: aac: aac too complex', c708(ck.fx('aac_51.m4a'), 'repro'))
ck.check('tone_51_48k.wav (generator)', 'soundcraft#708', '5.1 WAV import (source of aac_51.m4a)', '6 channels, 48000 frames',
         '6 channels, 48000 frames', c708(g('tone_51_48k.wav'), 'control'), role='control')


# ---------- #709 AC-3 / E-AC-3 message
def c709(name):
    def fn():
        p = ck.fx(name)
        inf, err = info(p)
        imp, ierr = import_audio(p, 48000)
        if inf is not None and imp is not None:
            ok = imp.get('channels') == 6
            return 'imports: info %s ch %s frames; import %s ch' % (inf.get('channels'), inf.get('frames'), imp.get('channels')), \
                ('FIXED' if ok else 'CHANGED'), {'info': inf, 'import': imp}
        msg = err or ierr
        low = msg.lower()
        if 'end of stream' in low and 'malformed' in low:
            v = 'NOT FIXED'
        elif 'unsupported' in low or 'not supported' in low:
            v = 'FIXED'
        else:
            v = 'CHANGED'
        return 'info: %s | import: %s' % (err or 'ok', ierr or 'ok'), v, {'info_error': err, 'import_error': ierr}
    return fn


ck.check('ac3_51.ac3', 'soundcraft#709', 'AC-3 elementary stream: message (or import)', '"unsupported ..." or 6-channel import',
         'malformed audio: end of stream', c709('ac3_51.ac3'))
ck.check('eac3_51.eac3', 'soundcraft#709', 'E-AC-3 elementary stream: message (or import)', '"unsupported ..." or 6-channel import',
         'malformed audio: end of stream', c709('eac3_51.eac3'))


# ---------- #710 MP3 empty last granule
def c710(path, want, old):
    def fn():
        if not os.path.exists(path):
            raise RuntimeError('missing ' + path)
        inf, err = info(path)
        rate = (inf or {}).get('sample_rate') or 44100
        imp, ierr = import_audio(path, rate)
        x, sr, cerr = convert(path)
        ref = want if want else len(decode(path)[0])
        fr = (imp or {}).get('frames')
        n = None if x is None else len(x)
        ok = fr is not None and n is not None and abs(fr - ref) <= 1152 and abs(n - ref) <= 1152
        bad = old is not None and (fr == old or n == old)
        v = 'FIXED' if ok else ('NOT FIXED' if bad else 'CHANGED')
        return 'info %s, import %s, convert %s frames (ref %d)' % ((inf or {}).get('frames'), fr, n, ref), v, \
            {'info': inf, 'import': imp, 'convert_frames': n, 'reference': ref, 'errors': [err, ierr, cerr]}
    return fn


ck.check('mp3_mf320_left.mp3', 'soundcraft#710', 'MP3 (Media Foundation, 320 kbps) with empty last granules: length after import',
         '134784 frames (info, ffmpeg)', '103680 frames (27 x 1152 dropped)', c710(ck.fx('mp3_mf320_left.mp3'), 134784, 103680))
ck.check('mp3_lame320_left.mp3 (built)', 'soundcraft#710', 'MP3 from LAME 320 kbps (noise_left_44k.wav of the generator): decodes completely',
         'frames = ffmpeg decode (+-1152)', 'complete', c710(g('mp3_lame320_left.mp3'), None, None), role='control')


# ---------- #712 HE-AAC
def c712(name, aspect, want_ch=None, ref_frames=192512, alt_frames=None):
    def fn():
        p = ck.fx(name)
        x, sr, err = convert(p)
        inf, ierr = info(p)
        if x is None:
            return 'convert failed: ' + err, 'CHANGED', {'error': err}
        n, ch = len(x), x.shape[1]
        dur = n / sr
        step, f0 = pitch_step(x, sr)
        d = {'frames': n, 'rate': sr, 'channels': ch, 'seconds': round(dur, 3), 'step_s': step, 'first_hz': f0, 'info': inf}
        act = '%d frames @ %d Hz (%.2f s), %d ch, %s Hz then step at %s s' % (n, sr, dur, ch, f0, step)
        if aspect == 'channels':
            v = 'FIXED' if ch == want_ch else ('NOT FIXED' if ch == 1 else 'CHANGED')
            return act, v, d
        ref_dur = ref_frames / 48000.0
        len_ok = abs(dur - ref_dur) <= 0.06 and step is not None and abs(step - 2.0) <= 0.15 and f0 and abs(f0 - 440) < 30
        if alt_frames and not len_ok:  # DRACO-AC12: iTunSMPB applied = exact source length (PR #814: 192000 frames @ 48 kHz)
            len_ok = abs(dur - alt_frames / 48000.0) <= 0.011 and step is not None and abs(step - 2.0) <= 0.15 and f0 and abs(f0 - 440) < 30
        if aspect == 'control':
            return act, ('FIXED' if len_ok else 'CHANGED'), d
        len_ok = len_ok and sr == 48000
        old = sr == 48000 and abs(dur - ref_dur / 2) <= 0.15 and step is not None and abs(step - 1.0) <= 0.15
        return act, ('FIXED' if len_ok else ('NOT FIXED' if old else 'CHANGED')), d
    return fn


ck.check('he_aac_v1_sr48k.m4a', 'soundcraft#712', 'HE-AAC v1, sample entry 48000: length and pitch (convert)',
         '192512 frames @ 48 kHz (4.01 s), 440 -> 880 Hz at 2.0 s', '99328 frames (2.07 s), 880 -> 1760 Hz at 1.0 s',
         c712('he_aac_v1_sr48k.m4a', 'length'), aspect='length/pitch')
ck.check('he_aac_v2_sr48k.m4a', 'soundcraft#712', 'HE-AAC v2 (PS), sample entry 48000: length and pitch (convert)',
         '192512 frames @ 48 kHz (4.01 s), 440 -> 880 Hz at 2.0 s', '100352 frames (2.09 s), 880 -> 1760 Hz at 1.0 s',
         c712('he_aac_v2_sr48k.m4a', 'length'), aspect='length/pitch')
ck.check('he_aac_v2_sr48k.m4a', 'soundcraft#712', 'HE-AAC v2 (parametric stereo): channel count', '2 channels', '1 channel',
         c712('he_aac_v2_sr48k.m4a', 'channels', want_ch=2), aspect='channels')
ck.check('he_aac_v1_stereo.m4a', 'soundcraft#712', 'HE-AAC v1, sample entry 24000 (fdkaac original): length and pitch',
         '~4.14 s untrimmed or 4.00 s with iTunSMPB applied, step at 2.0 s (any rate)', '99328 frames @ 24 kHz (4.14 s), step at 2.0 s',
         c712('he_aac_v1_stereo.m4a', 'control', ref_frames=198656, alt_frames=192000), role='control', aspect='length/pitch')

ck.write({'known_main_label': 'SoundCraft 0.7.0', 'known_main_source': 'SoundCraft 0.7.0 Windows x64 release (issues #707-#710, #712)',
          'ffmpeg': (subprocess.run([FF, '-version'], capture_output=True).stdout.decode('utf-8', 'replace').splitlines() or [''])[0]})
