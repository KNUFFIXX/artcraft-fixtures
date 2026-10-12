#!/usr/bin/env python3
"""Contributor-original fixtures for PdfCraft bug reports (KNUFFIXX/artcraft-fixtures).

Every PDF is written by hand below. Fonts: the standard-14 Helvetica (never embedded), a subset of
DejaVu Sans (Bitstream Vera licence; path below) built with fontTools, and three hand-drawn 8x14
bitmaps. No real-world documents, no personal data.

    python3 make_fixtures.py            # writes the PDFs into the current directory

Licence: MIT OR Apache-2.0, at your option. Written by Claude (Anthropic) on behalf of Udo Funk.
"""
import io
from fontTools.ttLib import TTFont
from fontTools import subset
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

DEJAVU = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


class Pdf:
    """Minimal PDF writer: objects are bytes, or (dict_bytes_without_Length, stream_bytes)."""

    def __init__(self):
        self.objs = []

    def add(self, body):
        self.objs.append(body)
        return len(self.objs)

    def write(self, path, root):
        out = io.BytesIO()
        out.write(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n')
        offs = []
        for i, b in enumerate(self.objs, 1):
            offs.append(out.tell())
            out.write(f'{i} 0 obj\n'.encode())
            if isinstance(b, tuple):
                d, s = b
                out.write(d[:-2] + f' /Length {len(s)} >>'.encode() + b'\nstream\n' + s + b'\nendstream')
            else:
                out.write(b)
            out.write(b'\nendobj\n')
        x = out.tell()
        out.write(f'xref\n0 {len(self.objs) + 1}\n0000000000 65535 f \n'.encode())
        for o in offs:
            out.write(f'{o:010d} 00000 n \n'.encode())
        out.write(f'trailer\n<< /Size {len(self.objs) + 1} /Root {root} 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode())
        open(path, 'wb').write(out.getvalue())
        print('wrote', path, len(out.getvalue()), 'bytes')


def pdf_string(text):
    t = text.encode('cp1252')
    return b'(' + t.replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)') + b')'


def one_page(p, content, fonts, extra_page=b'', extra_root=b''):
    """Finish a one-page document: fonts = {name: objnum}."""
    content_id = p.add((b'<< >>', content))
    pages_id = len(p.objs) + 2
    res = b'/Font << ' + b' '.join(f'/{n} {o} 0 R'.encode() for n, o in fonts.items()) + b' >>'
    page = p.add(f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << '.encode() + res + b' >> /Contents ' + f'{content_id} 0 R'.encode() + extra_page + b' >>')
    pages = p.add(f'<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>'.encode())
    return p.add(f'<< /Type /Catalog /Pages {pages} 0 R'.encode() + extra_root + b' >>')


# --- 1. double letters in condensed text (Tz) --------------------------------------------------
def double_letters_condensed_tz(path):
    p = Pdf()
    helv = p.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    cs = b'BT\n'
    y = 780
    for tz in (100, 80, 70, 65, 60, 55, 50):
        cs += f'/F1 11 Tf {tz} Tz 1 0 0 1 50 {y} Tm '.encode() + pdf_string(f'Tz {tz}: Alle Stellen sollen Hallo Mitte Wille Kommission Illustration still') + b' Tj\n'
        y -= 22
    cs += b'ET\n'
    p.write(path, one_page(p, cs, {'F1': helv}))


# --- 2. simple TrueType fonts without /Encoding -------------------------------------------------
def subset_dejavu(text, cmaps):
    """DejaVu Sans subset for `text` with ONLY the given cmap subtables and no glyph names (post 3.0).
    cmaps: list of (platformID, platEncID, format, {code: char})."""
    f = TTFont(DEJAVU)
    opts = subset.Options()
    opts.name_IDs = ['*']
    opts.notdef_outline = True
    opts.glyph_names = False
    opts.hinting = False
    s = subset.Subsetter(opts)
    s.populate(text=text)
    s.subset(f)
    uni = {}
    for st in f['cmap'].tables:
        if st.isUnicode():
            uni.update(st.cmap)
    tables = []
    for pid, eid, fmt, mapping in cmaps:
        st = CmapSubtable.newSubtable(fmt)
        st.platformID, st.platEncID, st.language = pid, eid, 0
        st.cmap = {code: uni[ord(ch)] for code, ch in mapping.items() if ord(ch) in uni}
        tables.append(st)
    f['cmap'].tables = tables
    f['post'].formatType = 3.0
    upm = f['head'].unitsPerEm
    sc = lambda v: round(v * 1000 / upm)
    widths = {}
    for pid, eid, fmt, mapping in cmaps:
        for code, ch in mapping.items():
            g = uni.get(ord(ch))
            if g:
                widths[code] = sc(f['hmtx'][g][0])
    buf = io.BytesIO()
    f.save(buf)
    bbox = [sc(v) for v in (f['head'].xMin, f['head'].yMin, f['head'].xMax, f['head'].yMax)]
    return buf.getvalue(), widths, bbox, sc(f['hhea'].ascent), sc(f['hhea'].descent)


WINANSI = {c: chr(c).encode('latin1').decode('cp1252') for c in range(32, 256) if c not in (0x81, 0x8d, 0x8f, 0x90, 0x9d)}
UMLAUT_TEXT = 'Rückfragen für Überhitzungsschutz: können, weiß, benötigen, Grüßen'


def truetype_no_encoding(path, flags, cmaps, tounicode_ascii_only=False):
    ttf, widths, bbox, asc, desc = subset_dejavu(UMLAUT_TEXT, cmaps)
    p = Pdf()
    ff = p.add((f'<< /Length1 {len(ttf)} >>'.encode(), ttf))
    fd = p.add(f'<< /Type /FontDescriptor /FontName /AAAAAA+DejaVuSans /Flags {flags} /FontBBox [{bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}] /ItalicAngle 0 /Ascent {asc} /Descent {desc} /CapHeight 700 /StemV 80 /FontFile2 {ff} 0 R >>'.encode())
    extra = b''
    if tounicode_ascii_only:
        cm = (b'/CIDInit /ProcSet findresource begin 12 dict begin begincmap /CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def '
              b'/CMapName /PartialToUnicode def /CMapType 2 def 1 begincodespacerange <20> <FF> endcodespacerange 1 beginbfrange <20> <7E> <0020> endbfrange endcmap CMapName currentdict /CMap defineresource pop end end')
        tu = p.add((b'<< >>', cm))
        extra = f' /ToUnicode {tu} 0 R'.encode()
    w = ' '.join(str(widths.get(c, 600)) for c in range(32, 256))
    font = p.add(f'<< /Type /Font /Subtype /TrueType /BaseFont /AAAAAA+DejaVuSans /FirstChar 32 /LastChar 255 /Widths [{w}] /FontDescriptor {fd} 0 R'.encode() + extra + b' >>')
    cs = b'BT /F1 14 Tf 1 0 0 1 50 760 Tm ' + pdf_string(UMLAUT_TEXT) + b' Tj ET\n'
    p.write(path, one_page(p, cs, {'F1': font}))


# --- 3. Type 3 image-mask glyphs under text rendering mode 2 ------------------------------------
GLYPHS = {
    'l': ['........', '........', '...#....', '...#....', '...#....', '...#....', '...#....', '...#....', '...#....', '...#....', '...#....', '...#....', '...#....', '........'],
    'H': ['........', '........', '.#....#.', '.#....#.', '.#....#.', '.#....#.', '.######.', '.#....#.', '.#....#.', '.#....#.', '.#....#.', '.#....#.', '.#....#.', '........'],
    'o': ['........', '........', '........', '........', '........', '..####..', '.#....#.', '.#....#.', '.#....#.', '.#....#.', '.#....#.', '..####..', '........', '........'],
}


def type3_imagemask_tr2(path):
    def charproc(rows):
        bits = bytes(int(''.join('1' if c == '#' else '0' for c in r), 2) for r in rows)
        return (b'<< >>', b'10 0 0 0 10 14 d1\n8 0 0 14 1 0 cm\nBI\n/W 8\n/H 14\n/BPC 1\n/Decode [1 0]\n/IM true\nID ' + bits + b'\nEI')
    p = Pdf()
    cl, cH, co = (p.add(charproc(GLYPHS[k])) for k in ('l', 'H', 'o'))
    widths = ' '.join('10' if c in (72, 108, 111) else '0' for c in range(72, 112))
    font = p.add(f'<< /Type /Font /Subtype /Type3 /FontBBox [0 0 10 14] /FontMatrix [0.03 0 0 0.03 0 0] /CharProcs << /l {cl} 0 R /H {cH} 0 R /o {co} 0 R >> /Encoding << /Type /Encoding /Differences [72 /H 108 /l 111 /o] >> /FirstChar 72 /LastChar 111 /Widths [{widths}] /Resources << >> >>'.encode())
    helv = p.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    cs = b'0 g 0 G\n'
    y = 780
    for size in (10, 16, 24):
        for tr in (0, 2):
            cs += f'BT /F2 9 Tf 1 0 0 1 40 {y + 4} Tm (Type3 image-mask glyphs, {size} pt, {tr} Tr:) Tj ET\n'.encode()
            cs += f'BT {tr} Tr /F1 {size} Tf 1 0 0 1 260 {y} Tm (HolloHlloHoll) Tj 0 Tr ET\n'.encode()
            y -= size * 0.7 + 26
    p.write(path, one_page(p, cs, {'F1': font, 'F2': helv}))


# --- 4. flatten with an orphan field ------------------------------------------------------------
def flatten_orphan_field(path):
    p = Pdf()
    font = p.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    res = b'/Resources << /Font << /Helv ' + f'{font}'.encode() + b' 0 R >> >>'
    ap1 = p.add((b'<< /Type /XObject /Subtype /Form /BBox [0 0 200 20] ' + res + b' >>', b'/Tx BMC BT /Helv 10 Tf 2 6 Td (on page) Tj ET EMC'))
    ap2 = p.add((b'<< /Type /XObject /Subtype /Form /BBox [0 0 200 20] ' + res + b' >>', b'/Tx BMC BT /Helv 10 Tf 2 6 Td (orphan) Tj ET EMC'))
    page_id = 7
    f1 = p.add(f'<< /Type /Annot /Subtype /Widget /FT /Tx /T (on_page) /V (on page) /DA (/Helv 10 Tf 0 g) /F 4 /Rect [50 700 250 720] /AP << /N {ap1} 0 R >> /P {page_id} 0 R >>'.encode())
    f2 = p.add(f'<< /Type /Annot /Subtype /Widget /FT /Tx /T (orphan) /V (orphan) /DA (/Helv 10 Tf 0 g) /F 4 /Rect [50 650 250 670] /AP << /N {ap2} 0 R >> >>'.encode())
    cs = b'BT /F1 12 Tf 50 780 Td (Field on_page is in /Annots; field orphan is only in /AcroForm /Fields.) Tj ET'
    root = one_page(p, cs, {'F1': font}, extra_page=f' /Annots [{f1} 0 R]'.encode(),
                    extra_root=f' /AcroForm << /Fields [{f1} 0 R {f2} 0 R] /DA (/Helv 10 Tf 0 g) /DR << /Font << /Helv {font} 0 R >> >> >>'.encode())
    assert p.objs[page_id - 1].startswith(b'<< /Type /Page ')
    p.write(path, root)


if __name__ == '__main__':
    double_letters_condensed_tz('double_letters_condensed_tz.pdf')
    truetype_no_encoding('symbolic_truetype_mac_cmap_no_tounicode.pdf', 4, [(1, 0, 0, WINANSI)])
    truetype_no_encoding('nonsymbolic_truetype_partial_tounicode.pdf', 32, [(3, 1, 4, WINANSI), (1, 0, 0, WINANSI)], tounicode_ascii_only=True)
    type3_imagemask_tr2('type3_imagemask_tr2.pdf')
    flatten_orphan_field('flatten_orphan_field.pdf')
