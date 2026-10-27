#!/usr/bin/env python3
"""deckcraft.py (THV-AC04, 17.10.2026) - DeckCraft fixture checks for the PR pre-test. Call:
  python3 -I deckcraft.py <deckcraft-cli> <artcraft-fixtures/deckcraft> <out.json> [--work DIR]
Issues: storytold/deckcraft #780 (an empty line inside a paragraph is sized by the first run, not by the a:br /
a:endParaRPr that ends it), #203 (an embedded Excel worksheet, p:oleObj + package part, is saved as a picture).

#780 measurement (as in the issue and the fixture README): render slide 1 of dc_empty_line_height.pptx at 1 px per pt
(`render FILE --all --scale 1 DIR`, which works whether --slide is 1-based (0.7.0) or 0-based (main since 10/2026)),
then per text box the ink rows: the top of the first and of the second text line = the first row of the first and of
the second band of rows that hold dark pixels (luminance < 128; the grey box outline 9CA3AF stays out), inside the box
(x0+3 .. x0+217, y 62 .. 498). Anti-aliasing: +-1 px. Verdict on the gap second - first line top
(the first-line top differs by host font/rasteriser: Linux renders Arial with Liberation Sans, ~+1 px vs Windows). Expected values: PowerPoint for Microsoft 365 (Windows),
the slide exported at 1 px per pt. known_main = DeckCraft 0.7.0 Windows x64 as reported in #780.
Pillow + numpy are needed for the measurement (else the #780 checks end as ERROR)."""
import glob
import os
import re
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('deckcraft', sys.argv)
W = ck.work
TOL = 1
FIX_780 = 'dc_empty_line_height.pptx'
# box: (name, x0 of the 220 pt wide box, PowerPoint (first, second line top), DeckCraft 0.7.0 (first, second), role, what)
BOXES = [
    ('A', 10, (70, 131), (70, 166), 'repro', 'box A: empty line ended by a 10 pt a:br (A1 40 pt, br 40 pt, br 10 pt, A2 40 pt)'),
    ('B', 250, (70, 131), (70, 166), 'repro', 'box B: empty last line, a:endParaRPr 10 pt (B1 40 pt, br 40 pt; next paragraph B2)'),
    ('C', 490, (64, 160), (65, 113), 'repro', 'box C: empty line ended by a 60 pt a:br (C1 20 pt, br 20 pt, br 60 pt, C2 20 pt)'),
    ('D', 730, (70, 131), (70, 130), 'control', 'box D: empty paragraph with a:endParaRPr 10 pt (control; already right in 0.7.0)'),
]
BOX_Y0, BOX_Y1, BOX_W = 60, 500, 220
_render = {}


def render_780():
    """Renders slide 1 once per run; returns (path, (w, h))."""
    if 'png' in _render:
        return _render['png']
    out = os.path.join(W, 'render_780')
    shutil.rmtree(out, ignore_errors=True)
    rc, so, se = C.run([ck.cli, 'render', ck.fx(FIX_780), '--all', '--scale', '1', out], timeout=300, cwd=W,
                       log_prefix=os.path.join(W, 'render_780'))
    png = os.path.join(out, 'slide-01.png')
    if not os.path.exists(png):
        cand = sorted(glob.glob(os.path.join(out, '*.png')))
        if not cand:
            raise RuntimeError('render gave no PNG (rc=%s): %s' % (rc, (se or so).strip()[-300:]))
        png = cand[0]
    from PIL import Image  # noqa: PLC0415
    with Image.open(png) as im:
        size = im.size
    shutil.copyfile(png, os.path.join(W, 'dc_empty_line_height_render.png'))
    _render['png'] = (png, size)
    return _render['png']


def ink_bands(png, x0):
    import numpy as np  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415
    with Image.open(png) as im:   # composited on white in case the render has transparency
        rgba = im.convert('RGBA')
    bg = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
    bg.alpha_composite(rgba)
    g = np.asarray(bg.convert('L'), dtype=np.int16)
    sub = g[BOX_Y0 + 2:BOX_Y1 - 1, x0 + 3:x0 + BOX_W - 2]
    rows = (sub < 128).any(axis=1)
    bands, start = [], None
    for i, v in enumerate(rows):
        y = BOX_Y0 + 2 + i
        if v and start is None:
            start = y
        if not v and start is not None:
            bands.append((start, y - 1))
            start = None
    if start is not None:
        bands.append((start, BOX_Y1 - 2))
    return bands


def box_check(name, x0, pp, old, role):
    def fn():
        png, size = render_780()
        if size != (960, 540):
            raise RuntimeError('render is %dx%d, expected 960x540 at --scale 1' % size)
        bands = ink_bands(png, x0)
        if len(bands) < 2:
            raise RuntimeError('fewer than two ink bands in box %s: %s' % (name, bands))
        t1, t2 = bands[0][0], bands[1][0]
        gap, pp_gap, old_gap = t2 - t1, pp[1] - pp[0], old[1] - old[0]
        # verdict on the gap second - first line top: the bug moves only the second line, while the first-line top
        # depends on the host font and rasteriser (Linux: Liberation Sans for Arial, about +1 px against Windows)
        if abs(gap - pp_gap) <= TOL:
            v = 'FIXED'
        elif role != 'control' and abs(gap - old_gap) <= TOL:
            v = 'NOT FIXED'
        else:
            v = 'CHANGED'
        actual = '%d, %d (gap %d; PowerPoint %d)' % (t1, t2, gap, pp_gap)
        return actual, v, {'first_top': t1, 'second_top': t2, 'gap': gap, 'pp_gap': pp_gap, 'known_main_gap': old_gap,
                           'abs_ok': abs(t1 - pp[0]) <= TOL and abs(t2 - pp[1]) <= TOL, 'bands': [list(b) for b in bands[:4]]}
    return fn


for name, x0, pp, old, role, what in BOXES:
    ck.check(FIX_780, 'deckcraft#780', what + ': top of the first and second text line (px = pt)',
             '%d, %d (gap %d; PowerPoint, +-1 px)' % (pp + (pp[1] - pp[0],)), '%d, %d (gap %d)' % (old + (old[1] - old[0],)), box_check(name, x0, pp, old, role),
             role=role, aspect='box %s' % name)


def c203():
    """oleObj kept and its r:id resolving to a package relationship whose part is in the saved deck (XML only)."""
    out = os.path.join(W, 'ole_saved.pptx')
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = C.run([ck.cli, 'run', '--in', ck.fx('dc_ole_embedded_xlsx.pptx'), '--save', out], timeout=180, cwd=W,
                       log_prefix=os.path.join(W, 'ole_save'))
    if not os.path.exists(out):
        raise RuntimeError('no saved deck (rc=%s): %s' % (rc, (se or so).strip()[-300:]))
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        slide = z.read('ppt/slides/slide1.xml').decode('utf-8', 'replace')
        rels = z.read('ppt/slides/_rels/slide1.xml.rels').decode('utf-8', 'replace') if 'ppt/slides/_rels/slide1.xml.rels' in names else ''
    m = re.search(r'<p:oleObj\b[^>]*\br:id="([^"]+)"', slide)
    part = None
    if m:
        r = re.search(r'<Relationship\b[^>]*Id="%s"[^>]*>' % re.escape(m.group(1)), rels)
        if r and 'relationships/package' in r.group(0):
            tgt = re.search(r'Target="([^"]+)"', r.group(0)).group(1)
            part = os.path.normpath(os.path.join('ppt/slides', tgt)).replace(os.sep, '/')
            part = part if part in names else None
    v = 'FIXED' if m and part else ('NOT FIXED' if not m and not part else 'CHANGED')
    return 'p:oleObj %s; package part %s' % ('kept' if m else 'gone', part or 'missing'), v, {'oleObj': bool(m), 'package_part': part}


ck.check('dc_ole_embedded_xlsx.pptx', 'deckcraft#203', 'save as .pptx keeps the embedded worksheet (p:oleObj + package part)',
         'p:oleObj kept with its package part (XML only, not opened in PowerPoint)', 'saved as a plain picture (0.7.0)', c203, role='extra', aspect='save')


def font_note():
    try:
        p = subprocess.run(['fc-match', 'Arial'], capture_output=True, timeout=20)
        return p.stdout.decode('utf-8', 'replace').strip()
    except Exception:  # noqa: BLE001
        return 'fc-match not available'


ck.write({'known_main_label': 'DeckCraft 0.7.0', 'known_main_source': 'DeckCraft 0.7.0 Windows x64 portable (issue #780 / #203 reports)',
          'render': {'cmd': 'render FILE --all --scale 1 DIR', 'size': list(_render['png'][1]) if 'png' in _render else None},
          'arial_on_host': font_note(), 'tolerance_px': TOL})
