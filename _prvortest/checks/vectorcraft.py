#!/usr/bin/env python3
"""vectorcraft.py (THV-AC04, 17.10.2026) - VectorCraft fixture checks for the PR pre-test.
Call:
  python3 -I vectorcraft.py <vectorcraft-cli> <artcraft-fixtures/vectorcraft> <out.json> [--work DIR]
Issues: storytold/vectorcraft #2673 (WMF placeable header: SETWINDOWORG/SETWINDOWEXT ignored, art off the artboard),
#2674 (PDF "0 w" strokes vanish in PNG/SVG/PDF export), #2675 (PDF invisible text, 3 Tr, dropped without a warning).
Needs Pillow, numpy and Poppler (pdftoppm, pdftotext). Pixel counts as in the issue (convert --scale 2 = 144 dpi,
ink = a channel more than 48 below white after compositing on white). Control WMF (window = placeable box) is written
into the work folder with the fixture generator's own functions.
known_main = VectorCraft 0.12.0 (Windows x64 release) as in the issues."""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

ck = C.Checker('vectorcraft', sys.argv)
W = ck.work
ENV = dict(os.environ, HOME=os.path.join(W, 'home'), XDG_CONFIG_HOME=os.path.join(W, 'cfg'), XDG_DATA_HOME=os.path.join(W, 'data'))
os.makedirs(ENV['HOME'], exist_ok=True)
PDFTOPPM = shutil.which('pdftoppm') or 'pdftoppm'
PDFTOTEXT = shutil.which('pdftotext') or 'pdftotext'
INK_DIFF = 48
N = [0]


def vc(args, tag, timeout=180):
    N[0] += 1
    return C.run([ck.cli] + args, timeout=timeout, cwd=W, env=ENV, log_prefix=os.path.join(W, '%02d_%s' % (N[0], tag)))


def convert(src, ext, extra=None):
    out = os.path.join(W, os.path.splitext(os.path.basename(src))[0] + '_out.' + ext)
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = vc(['convert', src, out] + (extra or []), 'convert_%s_%s' % (os.path.basename(src), ext))
    if not os.path.exists(out):
        raise RuntimeError('convert to %s wrote nothing (rc=%s): %s' % (ext, rc, (se or so).strip()[-300:]))
    return out


def info(src):
    rc, so, se = vc(['info', src], 'info_' + os.path.basename(src))
    if '{' not in so:
        raise RuntimeError('info failed (rc=%s): %s' % (rc, se.strip()[-300:]))
    return json.loads(so[so.index('{'):])


def load_on_white(p):
    im = Image.open(p)
    im.load()
    if im.mode in ('RGBA', 'LA', 'P', 'PA'):
        im = im.convert('RGBA')
        bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return np.asarray(im.convert('RGB'), dtype=np.int16)


def ink(a):
    return (255 - a).max(axis=2) > INK_DIFF


def pdftoppm(pdf, dpi=144):
    pre = os.path.splitext(pdf)[0] + '_ppm%d' % dpi
    subprocess.run([PDFTOPPM, '-f', '1', '-l', '1', '-singlefile', '-png', '-r', str(dpi), pdf, pre], capture_output=True, timeout=120)
    if not os.path.exists(pre + '.png'):
        raise RuntimeError('pdftoppm failed for ' + os.path.basename(pdf))
    return pre + '.png'


def pdftext(pdf):
    return subprocess.run([PDFTOTEXT, pdf, '-'], capture_output=True, timeout=120).stdout.decode('utf-8', 'replace')


# ---------- SVG helpers
NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def path_points(d):
    """absolute points of an SVG path (M L H V C S Q T Z, abs and rel; arcs: end point only)"""
    toks = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|' + NUM, d)
    pts, x, y, sx, sy, cmd, i = [], 0.0, 0.0, 0.0, 0.0, None, 0
    arity = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2, 'A': 7, 'Z': 0}
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t
            i += 1
            if cmd in 'Zz':
                x, y = sx, sy
                continue
        if cmd is None:
            break
        n = arity[cmd.upper()]
        a = [float(v) for v in toks[i:i + n]]
        if len(a) < n:
            break
        i += n
        rel = cmd.islower()
        u = cmd.upper()
        if u == 'H':
            x = a[0] + (x if rel else 0)
            pts.append((x, y))
        elif u == 'V':
            y = a[0] + (y if rel else 0)
            pts.append((x, y))
        elif u == 'A':
            x, y = a[5] + (x if rel else 0), a[6] + (y if rel else 0)
            pts.append((x, y))
        else:
            for k in range(0, n, 2):
                pts.append((a[k] + (x if rel else 0), a[k + 1] + (y if rel else 0)))
            x, y = pts[-1]
        if u == 'M':
            sx, sy = x, y
            cmd = 'l' if rel else 'L'
    return pts


def svg_paths(svg):
    """list of (element text, bbox) for every <path> with a d attribute"""
    out = []
    for m in re.finditer(r'<path\b[^>]*>', svg):
        el = m.group(0)
        d = re.search(r'\sd="([^"]*)"', el)
        if not d:
            continue
        p = path_points(d.group(1))
        if p:
            xs, ys = [q[0] for q in p], [q[1] for q in p]
            out.append((el, (min(xs), min(ys), max(xs), max(ys))))
    return out


def stroked(el):
    m = re.search(r'stroke="([^"]*)"', el) or re.search(r'stroke:\s*([^;"]+)', el)
    if not m or m.group(1).strip().lower() in ('none', 'transparent'):
        return False
    w = re.search(r'stroke-width="([^"]*)"', el) or re.search(r'stroke-width:\s*([^;"]+)', el)
    if w:
        try:
            return float(re.match(NUM, w.group(1).strip()).group(0)) > 0
        except (AttributeError, ValueError):
            return True
    return True


def fmt_box(b):
    return '%g,%g - %g,%g' % tuple(round(v, 2) for v in b)


# ---------- #2673 WMF window
def control_wmf():
    p = os.path.join(W, 'wmf_window_box.wmf')
    if not os.path.exists(p):
        spec = importlib.util.spec_from_file_location('mkfx_vc', os.path.join(ck.fixtures, 'make_fixtures_vectorcraft.py'))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        with open(p, 'wb') as f:   # window = placeable box: 0,0 + 1000 x 500, rectangle 250,125 - 750,375 -> 18,9 - 54,27 pt
            f.write(m.wmf((0, 0, 1000, 500, 1000), m.picture((0, 0), (1000, 500), (250, 125, 750, 375))))
    return p


WANT = (18.0, 9.0, 54.0, 27.0)


def near(b, want, tol):
    return b is not None and all(abs(u - v) <= tol for u, v in zip(b, want))


def c2673_svg(src_fn, old):
    def fn():
        src = src_fn()
        svg = open(convert(src, 'svg'), encoding='utf-8').read()
        vb = re.search(r'viewBox="([^"]*)"', svg)
        paths = svg_paths(svg)
        red = [b for el, b in paths if re.search(r'#(?:ff0000|f00)\b|rgb\(255,\s*0,\s*0\)|\bred\b', el, re.I)] or [b for el, b in paths]
        b = red[0] if red else None
        v = 'FIXED' if near(b, WANT, 0.6) else ('NOT FIXED' if old and near(b, old, 0.6) else 'CHANGED')
        return 'SVG rectangle %s (viewBox %s)' % (fmt_box(b) if b else 'missing', vb.group(1) if vb else '?'), v, \
            {'paths': [[el[:200], b] for el, b in paths][:6], 'viewBox': vb.group(1) if vb else None}
    return fn


def c2673_png(src_fn):
    def fn():
        src = src_fn()
        a = load_on_white(convert(src, 'png', ['--scale', '4']))
        m = (a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 2] < 80)
        h, w = m.shape
        if not m.any():
            return 'PNG %dx%d: no red pixels' % (w, h), 'NOT FIXED', {'size': [w, h]}
        ys, xs = np.nonzero(m)
        b = (xs.min() / 4.0, ys.min() / 4.0, (xs.max() + 1) / 4.0, (ys.max() + 1) / 4.0)
        v = 'FIXED' if near(b, WANT, 1.0) else 'CHANGED'
        return 'PNG %dx%d: red %s pt (%d px)' % (w, h, fmt_box(b), int(m.sum())), v, {'size': [w, h], 'red_box_pt': b, 'red_px': int(m.sum())}
    return fn


for name, old in (('wmf_window_ext.wmf', (72, 36, 216, 108)), ('wmf_window_org.wmf', (738, 1449, 774, 1467))):
    ck.check(name, 'vectorcraft#2673', 'placeable WMF, window differs from the box: rectangle in the SVG export',
             '18,9 - 54,27 pt on the 72 x 36 pt artboard', fmt_box(old) + ' (off the artboard)',
             c2673_svg(lambda n=name: ck.fx(n), old), aspect='svg')
    ck.check(name, 'vectorcraft#2673', 'placeable WMF, window differs from the box: red area in the PNG export (scale 4)',
             'red 18,9 - 54,27 pt', 'blank artboard', c2673_png(lambda n=name: ck.fx(n)), aspect='png')
ck.check('wmf_window_box.wmf (built)', 'vectorcraft#2673', 'placeable WMF, window = box: rectangle in the SVG export',
         '18,9 - 54,27 pt', '18,9 - 54,27 pt', c2673_svg(control_wmf, None), role='control', aspect='svg')


# ---------- #2674 zero-width lines
ZW = 'pdf_zero_width_lines.pdf'
ROWS = {'0w_lines': (284, 330), '0w_box': (480, 690), '1w_lines': (880, 930)}   # 144 dpi rows (y 700/680, 500-600, 400/380 pt)
REF = {'0w_lines': 1600, '0w_box': 801, '1w_lines': 3200}                        # Poppler 26.09 at 144 dpi (issue)


def counts(png):
    a = ink(load_on_white(png))
    return {k: int(a[y0:y1, 200:1000].sum()) for k, (y0, y1) in ROWS.items()}


ZC = {}


def zw_counts(kind):
    if kind not in ZC:
        src = ck.fx(ZW)
        if kind == 'png':
            ZC[kind] = counts(convert(src, 'png', ['--scale', '2']))
        elif kind == 'pdf':
            ZC[kind] = counts(pdftoppm(convert(src, 'pdf')))
        elif kind == 'ref':
            ZC[kind] = counts(pdftoppm(src))
    return ZC[kind]


def zw_verdict(c):
    a, b = c['0w_lines'], c['0w_box']
    if a >= 0.5 * REF['0w_lines'] and b >= 0.4 * REF['0w_box']:
        return 'FIXED'
    if a < 50 and b < 50:
        return 'NOT FIXED'
    return 'CHANGED'


def c2674_px(kind):
    def fn():
        c = zw_counts(kind)
        try:
            ref = zw_counts('ref')
        except Exception:  # noqa: BLE001 - reference is only detail
            ref = None
        return '0 w lines %d px, 0 w box outline %d px (1 pt lines %d)' % (c['0w_lines'], c['0w_box'], c['1w_lines']), zw_verdict(c), \
            {'counts': c, 'pdftoppm_original': ref, 'issue_reference': REF}
    return fn


def c2674_control():
    c = zw_counts('png')
    ok = 0.75 * REF['1w_lines'] <= c['1w_lines'] <= 1.25 * REF['1w_lines']
    return '1 pt lines %d px' % c['1w_lines'], ('FIXED' if ok else 'CHANGED'), {'counts': c}


def c2674_svg():
    svg = open(convert(ck.fx(ZW), 'svg'), encoding='utf-8').read()
    paths = svg_paths(svg)
    # page coordinates (y down): 0 w lines at y 142/162, box 242-342, 1 pt lines at y 442/462
    def pick(y0, y1):
        return [el for el, b in paths if y0 <= b[1] and b[3] <= y1]
    zl, bx, one = pick(130, 175), pick(235, 350), pick(430, 475)
    s = lambda els: sum(1 for e in els if stroked(e))  # noqa: E731
    act = 'stroked: 0 w lines %d/%d, 0 w box %d/%d, 1 pt lines %d/%d' % (s(zl), len(zl), s(bx), len(bx), s(one), len(one))
    if zl and bx and s(zl) == len(zl) and s(bx) == len(bx):
        v = 'FIXED'
    elif zl and s(zl) == 0 and s(bx) == 0:
        v = 'NOT FIXED'
    else:
        v = 'CHANGED'
    return act, v, {'paths': [el[:200] for el, b in paths][:8]}


ck.check(ZW, 'vectorcraft#2674', '"0 w" strokes in the PNG export (scale 2, 144 dpi)', 'hairlines: ~1600 px lines, ~801 px box outline (pdftoppm)',
         '0 px', c2674_px('png'), aspect='png')
ck.check(ZW, 'vectorcraft#2674', '"0 w" strokes in the SVG export', 'the 0 w paths carry a stroke', 'no stroke on the 0 w paths',
         c2674_svg, aspect='svg')
ck.check(ZW, 'vectorcraft#2674', '"0 w" strokes in the PDF export (rendered with pdftoppm, 144 dpi)', 'hairlines visible', '0 px',
         c2674_px('pdf'), aspect='pdf')
ck.check(ZW, 'vectorcraft#2674', '1 pt control lines in the PNG export', '~3200 px (as pdftoppm)', '3200 px', c2674_control,
         role='control', aspect='1 pt lines')


# ---------- #2675 invisible text
IT = 'pdf_invisible_text.pdf'
LINES = ('Invisible OCR layer line one', 'Invisible OCR layer line two')


def c2675():
    src = ck.fx(IT)
    j = info(src)
    warns = j.get('warnings') or []
    t = pdftext(convert(src, 'pdf'))
    kept = all(ln in t for ln in LINES)
    told = any(re.search(r'invisible|render(ing)? mode|hidden text|ocr|text.*(left out|dropped|skipped|omitted)', str(w), re.I) for w in warns)
    # other warnings (Linux: "fonts that aren't available show in the fallback font ...: Helvetica") do not count
    v = 'FIXED' if kept or told else ('NOT FIXED' if not any(ln in t for ln in LINES) else 'CHANGED')
    return 'export text: %s; info warnings %s; kinds %s' % ('both lines' if kept else 'without the invisible lines', json.dumps(warns)[:120],
                                                            json.dumps(j.get('kinds'))), v, \
        {'pdftotext_export': t[:400], 'warnings': warns, 'kinds': j.get('kinds')}


def c2675_visible():
    t = pdftext(convert(ck.fx(IT), 'pdf'))
    ok = 'Visible caption below the box' in t
    return 'visible line %s in the exported PDF' % ('present' if ok else 'missing'), ('FIXED' if ok else 'CHANGED'), {'pdftotext_export': t[:400]}


def c2675_still_invisible():
    out = convert(ck.fx(IT), 'pdf')
    a = load_on_white(pdftoppm(out))
    box = a[int((842 - 700) * 2):int((842 - 400) * 2), 100:990]   # the grey box (y 400-700 pt, x 50-545 pt) at 144 dpi
    dark = int((box.max(axis=2) < 128).sum())
    return '%d dark px inside the grey box of the exported PDF' % dark, ('FIXED' if dark < 20 else 'CHANGED'), {'dark_px': dark}


ck.check(IT, 'vectorcraft#2675', 'invisible text (3 Tr): kept in the PDF export or reported by info',
         'pdftotext of the export has both lines, or a warning says they were left out', 'left out, warnings: [] (Windows)', c2675)
ck.check(IT, 'vectorcraft#2675', 'visible line in the PDF export', '"Visible caption below the box" in pdftotext', 'present',
         c2675_visible, role='control', aspect='visible text')
ck.check(IT, 'vectorcraft#2675', 'invisible text stays invisible in the PDF export (pdftoppm, 144 dpi)', 'no dark pixels in the grey box',
         'none (text dropped)', c2675_still_invisible, role='control', aspect='render')

ck.write({'known_main_label': 'VectorCraft 0.12.0', 'known_main_source': 'VectorCraft 0.12.0 Windows x64 release (issues #2673-#2675)',
          'poppler': (subprocess.run([PDFTOPPM, '-v'], capture_output=True).stderr.decode('utf-8', 'replace').splitlines() or [''])[0]})
