#!/usr/bin/env python3
"""pdfcraft.py (DRACO-AC05, 15.10.2026) - PdfCraft fixture checks for the PR pre-test.
Linux port of the PdfCraft part of Scheduled_Scripts/ac-nachtest/ac_nachtest.py (same steps and thresholds), plus #2456 and
#2457 (posted 15.10.2026). Call:
  python3 -I pdfcraft.py <pdfcraft-cli> <artcraft-fixtures/pdfcraft> <out.json> [--work DIR]
Needs PIL and pypdf (both in the container). #1698 needs the public oss-fuzz file from the pdfplumber test suite; it is
downloaded once into $PRV_HOME/ext (or <work>/../ext) and checked by sha256 - without network that check is ERROR.
known_main = PdfCraft 0.8.0 (Windows x64 release, AC Nachtest 15.10.2026) or what the issue reported.
Issues: storytold/pdfcraft #1467 #1468 #1469 #1470 #1698 #1699 #1700 #1761 #1769 #1770 #2456 #2457 #4017 #5641.
known_main of #4017 and #5641: the release named in the issue report."""
import hashlib
import json
import os
import re
import shutil
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

from PIL import Image, ImageChops, ImageStat  # noqa: E402

ck = C.Checker('pdfcraft', sys.argv)
W = ck.work
OSS_URL = 'https://raw.githubusercontent.com/jsvine/pdfplumber/stable/tests/pdfs/from-oss-fuzz/load/5317294594523136.pdf'
OSS_SHA = '50dc70a42f43a0676f6bb776a0fb4651e5b0149a846475db1289544db3ed47f8'


def pc(args, tag, timeout=180, cwd=None):
    return C.run([ck.cli] + args, timeout=timeout, cwd=cwd or W, log_prefix=os.path.join(W, tag))


def text(path, tag, page=None):
    args = ['text', path] + (['--page', str(page)] if page else [])
    rc, so, se = pc(args, tag)
    if rc not in (0,) and not so.strip():
        raise RuntimeError('text failed (rc=%s): %s' % (rc, se.strip()[-300:]))
    return so


def check_one(path, tag):
    rc, so, se = pc(['check-one', path], tag)
    j = {}
    for ln in so.strip().splitlines():
        try:
            j = json.loads(ln)
            break
        except ValueError:
            continue
    return rc, j, se


def render(path, dpi, name, page=1):
    out = os.path.join(W, name)
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = pc(['render', path, '--page', str(page), '--dpi', str(dpi), '--out', out], 'render_' + name)
    if not os.path.exists(out):
        raise RuntimeError('render wrote nothing (rc=%s): %s' % (rc, se.strip()[-300:]))
    return Image.open(out).convert('L')


def ink(img, box):
    c = img.crop(box).point(lambda v: 255 if v < 128 else 0)
    return ImageStat.Stat(c).mean[0] / 255.0


def run_script(steps, tag, files):
    d = os.path.join(W, tag)
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    for src, dst in files:
        shutil.copy(src, os.path.join(d, dst))
    with open(os.path.join(d, 's.json'), 'w') as f:
        json.dump(steps, f)
    rc, so, se = pc(['run', '--script', 's.json', '--root', '.'], tag, cwd=d)
    return d, rc, so, se


# ---------- #1467 ----------
def c1467():
    t = text(ck.fx('double_letters_condensed_tz.pdf'), 'c1467')
    n_lines = len(re.findall(r'Tz \d+:', t))
    n_ok = t.count('Alle Stellen sollen Hallo Mitte Wille Kommission Illustration still')
    v = 'FIXED' if n_lines and n_ok == n_lines else ('NOT FIXED' if n_lines else 'CHANGED')
    return '%d/%d lines intact' % (n_ok, n_lines), v, {'text': t[:400]}


ck.check('double_letters_condensed_tz.pdf', 'pdfcraft#1467', 'doubled narrow letters in condensed text (Tz <= 80 %)',
         '7/7 lines intact', '7/7 (fixed in 0.8.0)', c1467, aspect='text')


# ---------- #1468 ----------
WANT1468 = 'Rückfragen für Überhitzungsschutz: können, weiß, benötigen, Grüßen'


def c1468(name):
    def fn():
        t = text(ck.fx(name), 'c1468_' + name[:12])
        ok = WANT1468 in t
        return 'umlauts %s' % ('ok' if ok else 'lost'), 'FIXED' if ok else 'NOT FIXED', {'text': t[:300]}
    return fn


ck.check('symbolic_truetype_mac_cmap_no_tounicode.pdf', 'pdfcraft#1468', 'umlauts: symbolic TrueType, (1,0) cmap, no /ToUnicode',
         'full sentence with umlauts', 'ok (fixed in 0.8.0)', c1468('symbolic_truetype_mac_cmap_no_tounicode.pdf'), aspect='text')
ck.check('nonsymbolic_truetype_partial_tounicode.pdf', 'pdfcraft#1468', 'umlauts: nonsymbolic TrueType, /ToUnicode 0x20-0x7E only',
         'full sentence with umlauts', 'ok (fixed in 0.8.0)', c1468('nonsymbolic_truetype_partial_tounicode.pdf'), aspect='text')


# ---------- #1469 ----------
def c1469():
    img = render(ck.fx('type3_imagemask_tr2.pdf'), 150, 't3.png')
    s = 150 / 72
    H = img.size[1]
    y = 780
    rows = []
    for size in (10, 16, 24):
        pair = []
        for _tr in (0, 2):
            top = H - (y + 0.42 * size + 2) * s
            bot = H - (y - 2) * s
            pair.append(ink(img, (int(260 * s), int(top), int(560 * s), int(bot))))
            y -= size * 0.7 + 26
        rows.append(pair)
    ratios = [b / a if a else 0 for a, b in rows]
    ok = all(0.9 <= r <= 1.1 for r in ratios)
    return 'Tr2/Tr0 ink ' + ', '.join('%.2f' % r for r in ratios), 'FIXED' if ok else 'NOT FIXED', {'ratios': ratios}


ck.check('type3_imagemask_tr2.pdf', 'pdfcraft#1469', 'Type 3 glyphs not drawn bold under 2 Tr (ink ratio Tr2/Tr0)',
         'ratio 0.90-1.10 at 10/16/24 pt', '1.00, 0.96, 1.00 (fixed in 0.8.0)', c1469, aspect='render 150 dpi')


# ---------- #1470 ----------
def c1470():
    import pypdf  # noqa: PLC0415
    d, rc, so, se = run_script([{'tool': 'doc_open', 'args': {'path': 'in.pdf'}}, {'tool': 'doc_flatten', 'args': {'doc': 1}},
                                {'tool': 'doc_save', 'args': {'doc': 1, 'full': True, 'path': 'out.pdf'}}], 'c1470',
                               [(ck.fx('flatten_orphan_field.pdf'), 'in.pdf')])
    out = os.path.join(d, 'out.pdf')
    if not os.path.exists(out):
        raise RuntimeError('no out.pdf (rc=%s): %s' % (rc, (se or so).strip()[-300:]))
    n = len(pypdf.PdfReader(out).get_fields() or {})
    return '%d fields left after flatten' % n, 'FIXED' if n == 0 else 'NOT FIXED', {'fields': n}


ck.check('flatten_orphan_field.pdf', 'pdfcraft#1470', 'doc_flatten removes a field whose widget is on no page',
         '0 fields after flatten + save', '0 (fixed in 0.8.0)', c1470, aspect='run script')


# ---------- #1698 ----------
def oss_file():
    home = os.environ.get('PRV_HOME') or os.path.join(W, '..', '..')
    ext = os.path.join(home, 'ext')
    os.makedirs(ext, exist_ok=True)
    p = os.path.join(ext, 'pdfplumber_oss_fuzz_5317294594523136.pdf')
    if not os.path.exists(p) or hashlib.sha256(open(p, 'rb').read()).hexdigest() != OSS_SHA:
        req = urllib.request.Request(OSS_URL, headers={'User-Agent': 'thv-ac-prvortest'})
        data = urllib.request.urlopen(req, timeout=60).read()
        if hashlib.sha256(data).hexdigest() != OSS_SHA:
            raise RuntimeError('oss-fuzz file: sha256 mismatch')
        with open(p, 'wb') as f:
            f.write(data)
    return p


def c1698():
    import pypdf  # noqa: PLC0415
    src = oss_file()
    d, rc, so, se = run_script([{'tool': 'doc_open', 'args': {'path': 'x.pdf'}}, {'tool': 'doc_save', 'args': {'doc': 1, 'full': True}}],
                               'c1698', [(src, 'x.pdf')])
    x = os.path.join(d, 'x.pdf')
    h0 = OSS_SHA
    h1 = hashlib.sha256(open(x, 'rb').read()).hexdigest()
    try:
        pages = len(pypdf.PdfReader(x).pages)
    except Exception:  # noqa: BLE001
        pages = 0
    if h0 == h1:
        return 'save refused or no-op, original kept (rc=%s)' % rc, 'FIXED', {'rc': rc}
    if pages >= 1:
        return 'file rewritten, result opens with %d page(s)' % pages, 'FIXED', {'rc': rc, 'bytes': os.path.getsize(x)}
    return 'original REPLACED by an unreadable file (%d bytes)' % os.path.getsize(x), 'NOT FIXED', {'rc': rc}


ck.check('pdfplumber oss-fuzz 5317294594523136.pdf (public)', 'pdfcraft#1698', 'a failed full save keeps the original file',
         'original kept or a readable result', 'original kept (fixed in 0.8.0)', c1698, aspect='run script')


# ---------- #1699 ----------
def c1699(name):
    def fn():
        t = text(ck.fx(name), 'c1699_' + name[:10])
        ok = 'Zażółć gęślą jaźń' in t
        return 'Type 0 text %s' % ('extracted' if ok else 'missing: %r' % t.strip()[:60]), 'FIXED' if ok else 'NOT FIXED', {'text': t[:300]}
    return fn


ck.check('tounicode_name_identity_h.pdf', 'pdfcraft#1699', 'Type 0 / Identity-H, /ToUnicode = the name /Identity-H',
         '"Zażółć gęślą jaźń"', 'no text (0.8.0)', c1699('tounicode_name_identity_h.pdf'), aspect='text')
ck.check('type0_identity_no_tounicode.pdf', 'pdfcraft#1699', 'Type 0 / Identity-H without /ToUnicode',
         '"Zażółć gęślą jaźń"', 'no text (0.8.0)', c1699('type0_identity_no_tounicode.pdf'), aspect='text')


# ---------- #1700 ----------
def c1700():
    lo = render(ck.fx('mask_downscale.pdf'), 96, 'm96.png')
    hi = render(ck.fx('mask_downscale.pdf'), 384, 'm384.png')
    ref = hi.resize(lo.size, Image.BOX)
    box = (50, 201, 460, 216)   # row 3 (Type 3 glyphs, 12 pt) at 96 dpi
    d = ImageStat.Stat(ImageChops.difference(lo.crop(box), ref.crop(box))).mean[0]
    # < 4 = fixed (threshold from the report, not yet confirmed on a merged fix); about 12.9 = 0.8.0; in between = improved, review
    v = 'FIXED' if d < 4.0 else ('NOT FIXED' if d >= 10.0 else 'CHANGED')
    return 'row 3 mean |diff| vs area-averaged 384 dpi = %.1f' % d, v, {'mean_diff': round(d, 1)}


ck.check('mask_downscale.pdf', 'pdfcraft#1700', 'Type 3 bitmap glyphs shrunk below 2:1 keep their strokes (96 vs 384 dpi)',
         'mean |diff| < 4 (4-10: improved, review)', '12.9 (0.8.0)', c1700, aspect='render 96 dpi')


# ---------- #1761 #1769 #1770 (no panic) ----------
def crash_free(name, control):
    def fn():
        rc0, j0, se0 = check_one(ck.fx(control), 'ctl_' + control[:12])
        if 'panicked' in se0 or rc0 == 'TIMEOUT' or 'crashed' in json.dumps(j0):
            raise RuntimeError('control %s also fails: %s' % (control, json.dumps(j0)[:200]))
        rc, j, se = check_one(ck.fx(name), 'chk_' + name[:12])
        crashed = 'crashed' in json.dumps(j) or 'panicked' in se
        status = j.get('status') if isinstance(j, dict) else None
        if rc == 'TIMEOUT':
            return 'timeout', 'CHANGED', {'json': j}
        return 'status=%s%s' % (status, ' panic' if crashed else ''), 'NOT FIXED' if crashed else 'FIXED', {'status': status, 'panic': crashed}
    return fn


ck.check('jpx_cm_i64max.pdf', 'pdfcraft#1761', 'JPX image under an out-of-range cm: no panic (check-one)',
         'no panic', 'panic (0.8.0)', crash_free('jpx_cm_i64max.pdf', 'jpx_cm_ok.pdf'), aspect='check-one')
ck.check('rc4_r3_length256.pdf', 'pdfcraft#1769', 'Standard security V2/R3 with /Length 256: no panic on open',
         'no panic', 'panic (0.8.0)', crash_free('rc4_r3_length256.pdf', 'rc4_r3_length128.pdf'), aspect='check-one')
ck.check('tiling_bbox_wide.pdf', 'pdfcraft#1770', 'tiling pattern with a huge /BBox: no panic in the renderer',
         'no panic', 'panic (0.8.0)', crash_free('tiling_bbox_wide.pdf', 'tiling_bbox_ok.pdf'), aspect='check-one')


# ---------- #2456 ----------
EI_LINES = ['Line 1: plain ASCII after the image', 'Line 3: EINGANG']


def c2456(page, role_note):
    def fn():
        t = text(ck.fx('inline_image_ei_lookahead.pdf'), 'c2456_p%d' % page, page=page)
        want = list(EI_LINES)
        if page == 2:
            want = ['Line 1: plain ASCII after the image', 'Line 3: eingang']
        if page == 4:
            want = ['Line 1: invisible OCR text', 'Line 3: EINGANG']
        got = [w for w in want if w in t]
        umlaut = ('Grüße aus Köln' in t) if page != 3 else ('Gruesse aus Koeln' in t)
        n = len(got) + (1 if umlaut else 0)
        v = 'FIXED' if n == 3 else ('NOT FIXED' if n == 0 else 'CHANGED')
        return 'page %d: %d of 3 text lines after the inline image%s' % (page, n, role_note), v, {'text': t[:400]}
    return fn


ck.check('inline_image_ei_lookahead.pdf', 'pdfcraft#2456', 'page 1: inline image, then a byte > 0x7F and a later "EI": rest of page',
         '3 of 3 lines (text and drawn)', '0 of 3 (0.8.0)', c2456(1, ''), aspect='text p1')
ck.check('inline_image_ei_lookahead.pdf', 'pdfcraft#2456', 'page 4: OCR pattern, 1x1 ASCII85 mask then invisible text with "EI"',
         '3 of 3 lines', '0 of 3 (0.8.0)', c2456(4, ''), aspect='text p4')
ck.check('inline_image_ei_lookahead.pdf', 'pdfcraft#2456', 'page 2 (control): lower-case "ei"',
         '3 of 3 lines', '3 of 3 (0.8.0)', c2456(2, ' (control)'), role='control', aspect='text p2')
ck.check('inline_image_ei_lookahead.pdf', 'pdfcraft#2456', 'page 3 (control): "EI" without a byte > 0x7F before it',
         '3 of 3 lines', '3 of 3 (0.8.0)', c2456(3, ' (control)'), role='control', aspect='text p3')


# ---------- #2457 ----------
TZ_WORDS = 'Hallo Mitte Wille Kommission Illustration still Brunnen Kaffee'
KNOWN_2457 = 3   # scales that were already exact in the reported build (Tz 100/50/30)


def c2457():
    t = text(ck.fx('condensed_tz_ocr.pdf'), 'c2457')
    lines = [re.sub(r'\s+', ' ', ln) for ln in t.splitlines() if ln.strip()]
    # the order of label and words on a line differs between builds, so count the lines that hold the exact word sequence
    exact = sum(1 for ln in lines if TZ_WORDS in ln)
    v = 'FIXED' if exact >= 6 else ('NOT FIXED' if exact <= KNOWN_2457 else 'CHANGED')
    return '%d of 6 scales give the words unchanged' % exact, v, {'exact': exact, 'lines': lines[:14]}


ck.check('condensed_tz_ocr.pdf', 'pdfcraft#2457', 'doubled and repeated letters in text condensed to Tz 20 % and less',
         '6 of 6 scales exact', '3 of 6 (0.8.0: Tz 20/10/5 lose letters)', c2457, aspect='text')


# ---------- #4017 ----------
def c4017():
    import pypdf  # noqa: PLC0415
    d, rc, so, se = run_script([{'tool': 'doc_open', 'args': {'path': 'in.pdf'}}, {'tool': 'doc_flatten', 'args': {'doc': 1, 'fields': True}},
                                {'tool': 'doc_save', 'args': {'doc': 1, 'full': True, 'path': 'out.pdf'}}], 'c4017',
                               [(ck.fx('flatten_empty_field_no_ap.pdf'), 'in.pdf')])
    out = os.path.join(d, 'out.pdf')
    if not os.path.exists(out):
        raise RuntimeError('no out.pdf (rc=%s): %s' % (rc, (se or so).strip()[-300:]))
    left = sorted((pypdf.PdfReader(out).get_fields() or {}).keys())
    return '%d fields left after flatten (%s)' % (len(left), ', '.join(left) or '-'), 'FIXED' if not left else 'NOT FIXED', {'fields': left}


ck.check('flatten_empty_field_no_ap.pdf', 'pdfcraft#4017', 'doc_flatten removes empty text fields without an appearance stream',
         '0 fields after flatten + save', '2 (empty_no_ap_1, empty_no_ap_2; 0.11.0)', c4017, aspect='run script')

# ---------- #5641 ----------
# text_overlap_sizes.pdf: rows A = 8 pt "Walter Example" on a 10 pt dot leader, rows B = 11 pt space glyphs over an 8 pt
# line, each shifted by -3 .. +3 pt. A row is intact when the text between its label and the next label holds exactly the
# expected words in order (dot-only tokens of the leader are ignored, so the value may stand before or after the dots).
# Splicing the run into the line glyph by glyph breaks the words, e.g. ".W...a..lt.e..r. E..x..a.m...p.l.e....".
ROWS_5641 = ['%+.1f' % d for d in (-3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 3)]
KNOWN_5641 = ['A-1.5', 'A-1.0', 'A+2.0', 'A+3.0', 'B-3.0', 'B+1.0', 'B+1.5']   # rows spliced in 0.16.1
LABEL_5641 = re.compile(r'([AB])([+-]\d\.\d):?(?=\s)')
ROWSTART_5641 = re.compile(r'(?m)^\s*[AB]\s*[+-]')   # start of a row line, also with a spliced label


def words_5641(seg):
    return [w for w in seg.split() if w.strip('.')]


def bad_rows_5641(t):
    found = {}
    marks = list(LABEL_5641.finditer(t))
    for i, m in enumerate(marks):
        nxt = ROWSTART_5641.search(t, m.end())
        end = min(marks[i + 1].start() if i + 1 < len(marks) else len(t), nxt.start() if nxt else len(t))
        found.setdefault(m.group(1) + m.group(2), t[m.end():end])
    bad = []
    for kind, want in (('A', ['Walter', 'Example']), ('B', ['quick', 'brown', 'fox', 'jumps'])):
        for r in ROWS_5641:
            seg = found.get(kind + r)
            if seg is None or words_5641(seg) != want:
                bad.append(kind + r)
    return bad


def c5641_rows():
    t = text(ck.fx('text_overlap_sizes.pdf'), 'c5641_rows')
    bad = bad_rows_5641(t)
    v = 'FIXED' if not bad else ('NOT FIXED' if bad == KNOWN_5641 else 'CHANGED')
    return '%d of 22 rows keep their words%s' % (22 - len(bad), (' (spliced: %s)' % ', '.join(bad)) if bad else ''), v, \
        {'bad': bad, 'text': t[:1600]}


def c5641_field():
    t = text(ck.fx('text_field_on_leader.pdf'), 'c5641_field')
    m = re.search(r'Name:(.*?)Control line', t, re.S)
    w = words_5641(m.group(1)) if m else None
    ctl = 'Control line without anything on top of it' in re.sub(r'\s+', ' ', t)
    if w == ['Walter', 'Example'] and ctl:
        return 'field value "Walter Example" kept on the leader line', 'FIXED', {'text': t[:300]}
    spliced = bool(m) and ctl and 'Walter' not in w and re.search(r'W\.+a', m.group(1)) is not None
    return 'field line: %r' % re.sub(r'\s+', ' ', (m.group(1) if m else t)).strip()[:90], 'NOT FIXED' if spliced else 'CHANGED', \
        {'text': t[:300]}


ck.check('text_overlap_sizes.pdf', 'pdfcraft#5641', 'a glyph run of another size drawn over a line keeps its words (22 rows)',
         '22 of 22 rows (0.15.0)', '15 of 22, A-1.5 A-1.0 A+2.0 A+3.0 B-3.0 B+1.0 B+1.5 spliced (0.16.1)', c5641_rows, aspect='text')
ck.check('text_field_on_leader.pdf', 'pdfcraft#5641', 'AcroForm field value drawn on a dot leader keeps its words',
         '"Name: ... Walter Example" (0.15.0)', '"Name: .W..a..lt.e..r. .E..x.a..m..p..le..." (0.16.1)', c5641_field, aspect='text')

ck.write({'known_main_label': 'PdfCraft 0.8.0', 'known_main_source': 'PdfCraft 0.8.0 Windows x64 release (AC Nachtest 15.10.2026) and the issue reports'})
