#!/usr/bin/env python3
"""photocraft.py (THV-AC04, 17.10.2026) - PhotoCraft fixture checks for the PR pre-test.
Call:
  python3 -I photocraft.py <photocraft-cli> <artcraft-fixtures/photocraft> <out.json> [--work DIR]
Issues: storytold/photocraft #6957 (developed raws open without EXIF: File Info Camera Data empty),
#6958 (File Info exposure 0.031714 s shown as "0.03 s", 0.0215 s as "0.02 s").
#6957 needs the public CC0 sample DSC00087.ARW (Sony ILCE-6400, 24.8 MB) from raw.pixls.us; it is downloaded once into
$PRV_HOME/ext (or <work>/../ext) and checked by SHA-256 - without network that check is ERROR.
Controls: JPEGs written in the work folder with Pillow (ExposureTime 1/250 s and 0.4 s), same pattern as the generator.
known_main = PhotoCraft 0.9.0 (Windows x64 release) as in the issues."""
import hashlib
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('photocraft', sys.argv)
W = ck.work
ENV = dict(os.environ, HOME=os.path.join(W, 'home'), XDG_CONFIG_HOME=os.path.join(W, 'cfg'), XDG_DATA_HOME=os.path.join(W, 'data'))
os.makedirs(ENV['HOME'], exist_ok=True)
ARW_URL = 'https://raw.pixls.us/download/data/Sony/ILCE-6400/DSC00087.ARW'
ARW_SHA = '8a37c80fc47c6026efa2e55279220e79460e2f470b1aa48b440f8f2d47873aa6'
N = [0]


def file_info(path, timeout=300):
    """photocraft-cli run <file> --cmd file.fileInfo -> (result dict, warnings list)"""
    N[0] += 1
    rc, so, se = C.run([ck.cli, 'run', path, '--cmd', 'file.fileInfo'], timeout=timeout, cwd=W, env=ENV,
                       log_prefix=os.path.join(W, '%02d_fileinfo_%s' % (N[0], os.path.basename(path))))
    res = None
    for ln in so.splitlines():
        ln = ln.strip()
        if ln.startswith('{'):
            try:
                j = json.loads(ln)
            except ValueError:
                continue
            if j.get('command') == 'file.fileInfo':
                res = j.get('result')
    warn = [ln[:200] for ln in (se + '\n' + so).splitlines() if ln.startswith('warning')]
    if res is None:
        raise RuntimeError('no file.fileInfo result (rc=%s): %s' % (rc, se.strip()[-300:]))
    return res, warn


def exposure_value(s):
    """'1/32 s' -> 0.03125, '0.0317 s' -> 0.0317, else None"""
    if not isinstance(s, str):
        return None
    m = re.match(r'^\s*(\d+)\s*/\s*(\d+(?:\.\d+)?)\s*s', s)
    if m:
        return float(m.group(1)) / float(m.group(2))
    m = re.match(r'^\s*(\d+(?:[.,]\d+)?)\s*s', s)
    if m:
        return float(m.group(1).replace(',', '.'))
    return None


# ---------- #6958 exposure text
def make_jpeg(name, num, den):
    from PIL import Image  # noqa: PLC0415
    from PIL.TiffImagePlugin import IFDRational as R  # noqa: PLC0415
    p = os.path.join(W, name)
    if not os.path.exists(p):
        im = Image.linear_gradient('L').resize((64, 64)).convert('RGB')
        ex = Image.Exif()
        ex[0x010F] = 'Example'
        ex[0x0110] = 'Fixture Cam'
        e2 = ex.get_ifd(0x8769)
        e2[0x829A] = R(num, den)
        e2[0x829D] = R(19, 10)
        e2[0x8827] = 400
        im.save(p, quality=90, exif=ex)
    return p


def c6958(path_fn, true_t, want_frac, old_text, tol=0.02):
    def fn():
        res, warn = file_info(path_fn())
        cam = res.get('camera') or {}
        e = cam.get('exposure')
        v = exposure_value(e)
        ok = v is not None and abs(v - true_t) <= tol * true_t
        if want_frac and e is not None:
            ok = ok or e.replace(' ', '') == want_frac.replace(' ', '')
        verdict = 'FIXED' if ok else ('NOT FIXED' if e == old_text else 'CHANGED')
        dev = '' if v is None else ' (%+.1f %% vs %.6g s)' % ((v - true_t) / true_t * 100, true_t)
        return 'exposure %s%s' % (json.dumps(e), dev), verdict, {'camera': cam}
    return fn


ck.check('exposure_fraction.jpg', 'photocraft#6958', 'File Info exposure of ExposureTime 31714/1000000 s', '"1/32 s" or ~0.0317 s (within 2 %)',
         '"0.03 s"', c6958(lambda: ck.fx('exposure_fraction.jpg'), 0.031714, '1/32 s', '0.03 s'))
ck.check('exposure_fraction_2.jpg', 'photocraft#6958', 'File Info exposure of ExposureTime 215/10000 s', '"1/47 s" or ~0.0215 s (within 2 %)',
         '"0.02 s"', c6958(lambda: ck.fx('exposure_fraction_2.jpg'), 0.0215, '1/47 s', '0.02 s'))
ck.check('exp_1_250.jpg (built)', 'photocraft#6958', 'File Info exposure of ExposureTime 1/250 s', '"1/250 s"',
         '"1/250 s"', c6958(lambda: make_jpeg('exp_1_250.jpg', 1, 250), 0.004, '1/250 s', None, tol=0.0), role='control')
ck.check('exp_0.4.jpg (built)', 'photocraft#6958', 'File Info exposure of ExposureTime 4/10 s', '0.4 s (within 1 %)',
         '"0.4 s"', c6958(lambda: make_jpeg('exp_0.4.jpg', 4, 10), 0.4, None, None, tol=0.01), role='control')


# ---------- #6957 raw EXIF
def arw():
    ext = os.path.join(os.environ['PRV_HOME'], 'ext') if os.environ.get('PRV_HOME') else os.path.join(os.path.dirname(W), 'ext')
    os.makedirs(ext, exist_ok=True)
    p = os.path.join(ext, 'DSC00087.ARW')

    def sha(f):
        h = hashlib.sha256()
        with open(f, 'rb') as fh:
            for b in iter(lambda: fh.read(1 << 20), b''):
                h.update(b)
        return h.hexdigest()
    if not os.path.exists(p) or sha(p) != ARW_SHA:
        req = urllib.request.Request(ARW_URL, headers={'User-Agent': 'thv-prvortest (CC0 sample)'})
        with urllib.request.urlopen(req, timeout=600) as r, open(p + '.part', 'wb') as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        if sha(p + '.part') != ARW_SHA:
            raise RuntimeError('DSC00087.ARW: SHA-256 mismatch after download')
        os.replace(p + '.part', p)
    return p


ARW_WANT = {'make': 'SONY', 'model': 'ILCE-6400', 'exposure': '1/250 s', 'fNumber': 'f/4', 'iso': 'ISO 250',
            'dateTaken': '2019-09-12 17:36:01', 'lens': 'E PZ 18-105mm F4 G OSS'}


def c6957():
    res, warn = file_info(arw(), timeout=600)
    cam = res.get('camera') or {}
    core = all(cam.get(k) for k in ('make', 'model', 'exposure'))
    match = {k: (cam.get(k) == v) for k, v in ARW_WANT.items()}
    if core:
        verdict = 'FIXED'
    elif not cam:
        verdict = 'NOT FIXED'
    else:
        verdict = 'CHANGED'
    miss = [k for k, ok in match.items() if not ok]
    act = 'camera %s' % (json.dumps(cam, ensure_ascii=False)[:160] if cam else '{}')
    if core and miss:
        act += '; differs from the EXIF values in: ' + ', '.join(miss)
    return act, verdict, {'camera': cam, 'expected': ARW_WANT, 'match': match, 'warnings': warn[:5]}


ck.check('DSC00087.ARW (raw.pixls.us, CC0)', 'photocraft#6957', 'developed Sony ARW: File Info Camera Data',
         'make/model/exposure present (SONY / ILCE-6400 / 1/250 s; f/4, ISO 250, lens E PZ 18-105mm F4 G OSS)', 'camera: {}', c6957)

ck.write({'known_main_label': 'PhotoCraft 0.9.0', 'known_main_source': 'PhotoCraft 0.9.0 Windows x64 release (issues #6957, #6958)'})
