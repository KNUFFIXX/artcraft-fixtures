#!/usr/bin/env python3
"""make_tounicode_name.py (DRACO-AC03) - synthetic Type0 fixtures for text extraction.
Embedded DejaVu Sans subset (Bitstream Vera licence) as CIDFontType2, /Encoding /Identity-H, codes = UTF-16BE
(CID = Unicode code point), CIDToGIDMap stream CID -> GID.
  tounicode_name_identity_h.pdf : /ToUnicode /Identity-H  (a name instead of a CMap stream, as some invoice generators write it)
  type0_identity_no_tounicode.pdf: no /ToUnicode at all (text only recoverable through the font's own cmap)"""
import io, sys, zlib
from fontTools import subset
from fontTools.ttLib import TTFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
LINES = ['Faktura nr FV 1/2026', 'Sprzedawca: Kacza 11/2, 91-504 Łódź', 'Zażółć gęślą jaźń', 'Grüße aus Neuss, 12,50 €']

def build_font(chars):
    opts = subset.Options(); opts.notdef_outline = True; opts.name_IDs = ['*']; opts.recalc_bounds = True
    f = TTFont(FONT); s = subset.Subsetter(opts); s.populate(unicodes=[ord(c) for c in chars]); s.subset(f)
    buf = io.BytesIO(); f.save(buf)
    cmap = f.getBestCmap(); order = f.getGlyphOrder(); hmtx = f['hmtx']; upm = f['head'].unitsPerEm
    gid = {c: order.index(cmap[ord(c)]) for c in chars}
    width = {c: round(hmtx[cmap[ord(c)]][0] * 1000 / upm) for c in chars}
    return buf.getvalue(), gid, width

class Pdf:
    def __init__(self): self.objs = []
    def add(self, body): self.objs.append(body); return len(self.objs)
    def write(self, path, root):
        out = bytearray(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n'); offs = []
        for i, o in enumerate(self.objs, 1):
            offs.append(len(out))
            if isinstance(o, tuple):
                d, s = o; out += f'{i} 0 obj\n'.encode() + d[:-2] + f' /Length {len(s)} >>\nstream\n'.encode() + s + b'\nendstream\nendobj\n'
            else: out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
        x = len(out)
        out += f'xref\n0 {len(self.objs) + 1}\n0000000000 65535 f \n'.encode()
        for o in offs: out += f'{o:010d} 00000 n \n'.encode()
        out += f'trailer\n<< /Size {len(self.objs) + 1} /Root {root} 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
        open(path, 'wb').write(out)

def make(path, tounicode):
    chars = sorted(set(''.join(LINES)))
    data, gid, width = build_font(chars)
    p = Pdf()
    ff = p.add((f'<< /Length1 {len(data)} /Filter /FlateDecode >>'.encode(), zlib.compress(data)))
    fd = p.add(f'<< /Type /FontDescriptor /FontName /AAAAAA+DejaVuSans /Flags 32 /FontBBox [-1021 -463 1793 1232] /ItalicAngle 0 /Ascent 928 /Descent -236 /CapHeight 729 /StemV 80 /FontFile2 {ff} 0 R >>'.encode())
    maxcid = max(ord(c) for c in chars)
    m = bytearray(2 * (maxcid + 1))
    for c in chars: m[2 * ord(c)] = gid[c] >> 8; m[2 * ord(c) + 1] = gid[c] & 255
    c2g = p.add((b'<< /Filter /FlateDecode >>', zlib.compress(bytes(m))))
    w = ' '.join(f'{ord(c)} [{width[c]}]' for c in chars)
    cid = p.add(f'<< /Type /Font /Subtype /CIDFontType2 /BaseFont /AAAAAA+DejaVuSans /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /FontDescriptor {fd} 0 R /DW 600 /W [{w}] /CIDToGIDMap {c2g} 0 R >>'.encode())
    tu = ' /ToUnicode /Identity-H' if tounicode == 'name' else ''
    f0 = p.add(f'<< /Type /Font /Subtype /Type0 /BaseFont /AAAAAA+DejaVuSans /Encoding /Identity-H /DescendantFonts [{cid} 0 R]{tu} >>'.encode())
    helv = p.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    label = 'ToUnicode is the name /Identity-H' if tounicode == 'name' else 'no ToUnicode'
    cs = f'BT /F1 9 Tf 50 790 Td (Type0 / CIDFontType2 / Identity-H, {label}:) Tj ET\n'.encode()
    y = 760
    for line in LINES:
        hexs = ''.join(f'{ord(c):04X}' for c in line)
        cs += f'BT /F2 14 Tf 50 {y} Td <{hexs}> Tj ET\n'.encode(); y -= 24
    content = p.add((b'<< >>', cs))
    pages_id = len(p.objs) + 2
    page = p.add(f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Contents {content} 0 R /Resources << /Font << /F1 {helv} 0 R /F2 {f0} 0 R >> >> >>'.encode())
    pages = p.add(f'<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>'.encode()); assert pages == pages_id
    root = p.add(f'<< /Type /Catalog /Pages {pages} 0 R >>'.encode())
    p.write(path, root)

if __name__ == '__main__':
    make('tounicode_name_identity_h.pdf', 'name')
    make('type0_identity_no_tounicode.pdf', None)
