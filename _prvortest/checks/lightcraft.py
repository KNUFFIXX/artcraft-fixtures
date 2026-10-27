#!/usr/bin/env python3
"""lightcraft.py (THV-AC03, 14.10.2026) - LightCraft fixture checks for the PR pre-test.
Linux port of Tools/ac_lc_nachtest.ps1 (same steps and conditions). Call:
  python3 -I lightcraft.py <lightcraft-cli> <artcraft-fixtures/lightcraft> <out.json> [--work DIR]
Issues: storytold/lightcraft #1617 (GPS placeholder read as 0 N 0 E), #1618 (export Make/Model), #1619 (0.4 s shutter),
#1620 (export Width & Height), #1670 (alpha channel in opaque 8-bit PNG/TIFF), #1671 (Panasonic RW2 lens name).
#1671 needs the CC0 sample P1000403.RW2 from raw.pixls.us (cached in $PRV_HOME/ext, else in the work folder).
known_main = LightCraft 0.7.1 (Windows x64 release) as in the issues.
THV-AC04 (17.10.2026): #1671 is FIXED on main f34c7a8 (fix PR #1703 merged 15.10.; baseline of the PR #1861 run)."""
import json
import os
import re
import struct
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('lightcraft', sys.argv)
W = ck.work
ENV = dict(os.environ, LIGHTCRAFT_CONFIG_DIR=os.path.join(W, 'cfg'))
os.makedirs(ENV['LIGHTCRAFT_CONFIG_DIR'], exist_ok=True)
RW2_URL = 'https://raw.pixls.us/download/data/Panasonic/DMC-G80/P1000403.RW2'
N = [0]


def lc(imp, steps, timeout=180):
    """lightcraft-cli run --keep-going --import <file> --script <jsonl>; returns the parsed output lines."""
    N[0] += 1
    tag = 's%d' % N[0]
    scr = os.path.join(W, tag + '.jsonl')
    with open(scr, 'w', encoding='utf-8') as f:
        f.write('\n'.join(json.dumps(s) for s in steps) + '\n')
    rc, so, se = C.run([ck.cli, 'run', '--keep-going', '--import', imp, '--script', scr], timeout=timeout, cwd=W, env=ENV,
                       log_prefix=os.path.join(W, tag))
    res = []
    for ln in so.splitlines():
        ln = ln.strip()
        if ln.startswith('{'):
            try:
                res.append(json.loads(ln))
            except ValueError:
                pass
    if not res:
        raise RuntimeError('no JSON output (rc=%s): %s' % (rc, se.strip()[-300:]))
    return res


def tag_of(am, name):
    for e in (am.get('result') or {}).get('exif') or []:
        if e.get('name') == name:
            return str(e.get('value'))
    return None


def c1617():
    out = os.path.join(W, 'gps_out.jpg')
    r = lc(ck.fx('lc_gps_placeholder.jpg'), [{'command': 'photo.inspect', 'params': {}},
                                              {'command': 'app.export', 'params': {'path': out, 'conflict': 'overwrite'}}])
    g = ((r[0].get('result') or {}).get('meta') or {}).get('gps')
    lat = tag_of(lc(out, [{'command': 'photo.allMetadata', 'params': {}}])[0], 'GPS Latitude')
    a, b = g is None, not (lat and re.search(r'\d', lat))
    v = 'FIXED' if a and b else ('NOT FIXED' if not a and not b else 'CHANGED')
    return 'inspect gps=%s; export GPS Latitude=%s' % (g, lat), v, {'gps': g, 'export_lat': lat}


def c1618():
    out = os.path.join(W, 'mm_out.jpg')
    r = lc(ck.fx('lc_make_model.jpg'), [{'command': 'photo.inspect', 'params': {}},
                                         {'command': 'app.export', 'params': {'path': out, 'conflict': 'overwrite'}}])
    cam = ((r[0].get('result') or {}).get('meta') or {}).get('camera')
    am = lc(out, [{'command': 'photo.allMetadata', 'params': {}}])[0]
    mk, md = tag_of(am, 'Make'), tag_of(am, 'Model')
    v = 'FIXED' if mk == 'Canon' and md == 'Canon IXUS 185' else ('NOT FIXED' if md == 'Canon Canon IXUS 185' else 'CHANGED')
    return 'export Make=%s, Model=%s (label %s)' % (mk, md, cam), v, {'make': mk, 'model': md, 'label': cam}


def c1619():
    out = os.path.join(W, 'exp_out.jpg')
    r = lc(ck.fx('lc_exposure_0.4s.jpg'), [{'command': 'photo.inspect', 'params': {}}, {'command': 'photo.allMetadata', 'params': {}},
                                            {'command': 'app.export', 'params': {'path': out, 'conflict': 'overwrite'}}])
    sh = str(((r[0].get('result') or {}).get('meta') or {}).get('shutter'))
    orig = tag_of(r[1], 'Exposure Time')
    exp = tag_of(lc(out, [{'command': 'photo.allMetadata', 'params': {}}])[0], 'Exposure Time')
    a, b = bool(re.match(r'^0[.,]4', sh)), exp == orig
    v = 'FIXED' if a and b else ('NOT FIXED' if not a and not b else 'CHANGED')
    return 'catalog %s; EXIF original %s, export %s' % (sh, orig, exp), v, {'shutter': sh, 'orig': orig, 'export': exp}


def c1620():
    out = os.path.join(W, 'wh_out.jpg')
    r = lc(ck.fx('lc_make_model.jpg'), [{'command': 'app.export', 'params': {'path': out, 'width': 270, 'height': 337, 'conflict': 'overwrite'}}])
    w, h = (r[0].get('result') or {}).get('width'), (r[0].get('result') or {}).get('height')
    return 'width=270 height=337 -> %sx%s' % (w, h), ('FIXED' if (w, h) == (270, 180) else 'NOT FIXED'), {'w': w, 'h': h}


def png_mode(p):
    with open(p, 'rb') as f:
        b = f.read(33)
    if b[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('not a PNG')
    depth, ctype = b[24], b[25]
    return {0: 'L', 2: 'RGB', 3: 'P', 4: 'LA', 6: 'RGBA'}.get(ctype, '?') + '/%d' % depth


def tiff_mode(p):
    try:
        from PIL import Image  # noqa: PLC0415 - optional
        with Image.open(p) as im:
            return im.mode
    except ImportError:
        with open(p, 'rb') as f:
            b = f.read()
        e = '<' if b[:2] == b'II' else '>'
        off = struct.unpack_from(e + 'I', b, 4)[0]
        n = struct.unpack_from(e + 'H', b, off)[0]
        spp, extra = 1, False
        for i in range(n):
            t, ty, cnt, val = struct.unpack_from(e + 'HHII', b, off + 2 + 12 * i)
            if t == 277:
                spp = struct.unpack_from(e + 'H', b, off + 2 + 12 * i + 8)[0]
            if t == 338:
                extra = True
        return 'samples=%d%s' % (spp, ' extra' if extra else '')


def c1670():
    p8, t8 = os.path.join(W, 'alpha_p8.png'), os.path.join(W, 'alpha_t8.tif')
    lc(ck.fx('lc_make_model.jpg'), [{'command': 'app.export', 'params': {'path': p8, 'conflict': 'overwrite'}},
                                     {'command': 'app.export', 'params': {'path': t8, 'bitDepth': 8, 'tiffCompression': 'none', 'conflict': 'overwrite'}}])
    fp, ft = png_mode(p8), tiff_mode(t8)
    alpha = lambda m: bool(re.search(r'A|samples=4|extra', m))  # noqa: E731
    a, b = not alpha(fp), not alpha(ft)
    v = 'FIXED' if a and b else ('NOT FIXED' if not a and not b else 'CHANGED')
    return 'PNG %s; TIFF %s' % (fp, ft), v, {'png': fp, 'tiff': ft}


def c1671():
    ext = os.path.join(os.environ['PRV_HOME'], 'ext') if os.environ.get('PRV_HOME') else W
    os.makedirs(ext, exist_ok=True)
    rw2 = os.path.join(ext, 'P1000403.RW2')
    if not os.path.exists(rw2) or os.path.getsize(rw2) < 1000000:
        req = urllib.request.Request(RW2_URL, headers={'User-Agent': 'thv-prvortest (CC0 sample)'})
        with urllib.request.urlopen(req, timeout=300) as r, open(rw2 + '.part', 'wb') as f:
            f.write(r.read())
        os.replace(rw2 + '.part', rw2)
    r = lc(rw2, [{'command': 'photo.inspect', 'params': {}}])
    lens = str(((r[0].get('result') or {}).get('meta') or {}).get('lens'))
    return 'DMC-G80 P1000403.RW2: lens=%s' % lens, ('FIXED' if '60mm' in lens else 'NOT FIXED'), {'lens': lens}


ck.check('lc_gps_placeholder.jpg', 'lightcraft#1617', 'empty GPS block (refs NUL, 0/0)', 'no position; nothing written into the export',
         'read as 0° N 0° E and written into the export', c1617)
ck.check('lc_make_model.jpg', 'lightcraft#1618', 'export EXIF Make/Model', 'Make=Canon, Model=Canon IXUS 185',
         'Make dropped, Model "Canon Canon IXUS 185"', c1618, aspect='make/model')
ck.check('lc_exposure_0.4s.jpg', 'lightcraft#1619', 'shutter 0.4 s in the catalog and the exported EXIF', 'catalog 0.4 s; export EXIF = original',
         'rounded to a whole step on display and in the export', c1619)
ck.check('lc_make_model.jpg', 'lightcraft#1620', 'export box width=270 height=337 on a 480x320 photo', '270x180 (Lightroom Width & Height)',
         'box applied as Dimensions', c1620, role='extra', aspect='width/height')   # extra since PR #1861: the default box is Lightroom's Dimensions


def c1620_fit():
    # DRACO-AC05: the fix in PR #1861 keeps the old box (now "Dimensions") and adds fit: widthHeight for Lightroom's Width & Height
    out = os.path.join(W, 'c1620_fit.jpg')
    r = lc(ck.fx('lc_make_model.jpg'), [{'command': 'app.export', 'params': {'path': out, 'width': 270, 'height': 337, 'fit': 'widthHeight', 'conflict': 'overwrite'}}])
    res = r[0].get('result') or {}
    w, h = res.get('width'), res.get('height')
    if w is None:
        return 'fit: widthHeight not accepted (%s)' % str(r[0].get('error') or r[0])[:120], 'NOT FIXED', {'resp': str(r[0])[:300]}
    return 'fit: widthHeight, width=270 height=337 -> %sx%s' % (w, h), ('FIXED' if (w, h) == (270, 180) else 'NOT FIXED'), {'w': w, 'h': h}


ck.check('lc_make_model.jpg', 'lightcraft#1620', 'export box width=270 height=337 with fit: widthHeight (Lightroom Width & Height)', '270x180',
         'no such option', c1620_fit, aspect='width/height, fit widthHeight')
ck.check('lc_make_model.jpg', 'lightcraft#1670', 'opaque photo as 8-bit PNG and TIFF', 'no alpha channel (RGB)',
         'alpha channel written (RGBA)', c1670, aspect='alpha')
ck.check('P1000403.RW2 (raw.pixls.us, CC0)', 'lightcraft#1671', 'Panasonic RW2 lens name (DMC-G80, Sigma 60mm F2.8 DN)',
         'lens contains 60mm', 'FIXED on `main` f34c7a8 (fix #1703); 0.7.1: lens missing', c1671)  # main f34c7a8, 17.10.2026 THV-AC04

ck.write({'known_main_label': 'LightCraft 0.7.1 / `main` f34c7a8',
          'known_main_source': 'LightCraft 0.7.1 Windows x64 release (issue reports, ac_lc_nachtest.ps1); #1671 main f34c7a8 (17.10.2026)'})
