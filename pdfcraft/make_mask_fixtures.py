#!/usr/bin/env python3
"""make_mask_fixtures.py (DRACO-AC03) - synthetic fixtures: 1-bit image masks / 1-bit images downscaled at render time.
Text bitmap drawn with DejaVu Sans (Bitstream Vera licence) at 300 dpi, placed at 12 pt and 9 pt:
  (1) /ImageMask true stencil, (2) DeviceGray /BitsPerComponent 1 image, (3) Type3 font with image-mask glyphs (16 px tall).
--edge writes mask_downscale_edge.pdf (Type3 glyphs in 25 px and 24 px cells shrunk 25 -> 22 and 24 -> 21 px at 96 dpi; see edge())."""
import zlib, sys
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
TEXT = 'Hamburgefonstiv 0123456789 Rechnung'

def bitmap(text, px):
    f = ImageFont.truetype(FONT, px)
    l, t, r, b = f.getbbox(text)
    im = Image.new('1', (r - l + 8, b - t + 8), 1)
    ImageDraw.Draw(im).text((4 - l, 4 - t), text, font=f, fill=0)
    return im

def packbits(im, ink_one):
    # rows padded to bytes; ink_one: 1 bit = ink (for /Decode [1 0] masks) else 0 = black (DeviceGray)
    w, h = im.size; out = bytearray()
    px = im.load()
    for y in range(h):
        byte = 0; n = 0
        for x in range(w):
            ink = px[x, y] == 0
            bit = (1 if ink else 0) if ink_one else (0 if ink else 1)
            byte = (byte << 1) | bit; n += 1
            if n == 8: out.append(byte); byte = 0; n = 0
        if n: out.append(byte << (8 - n))
    return bytes(out)

class Pdf:
    def __init__(self): self.objs = []
    def add(self, body):
        self.objs.append(body); return len(self.objs)
    def write(self, path, root):
        out = bytearray(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n'); offs = []
        for i, o in enumerate(self.objs, 1):
            offs.append(len(out))
            if isinstance(o, tuple):
                d, s = o; out += f'{i} 0 obj\n'.encode() + d[:-2] + f' /Length {len(s)} >>\nstream\n'.encode() + s + b'\nendstream\nendobj\n'
            else:
                out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
        x = len(out)
        out += f'xref\n0 {len(self.objs) + 1}\n0000000000 65535 f \n'.encode()
        for o in offs: out += f'{o:010d} 00000 n \n'.encode()
        out += f'trailer\n<< /Size {len(self.objs) + 1} /Root {root} 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
        open(path, 'wb').write(out)

def main(path):
    p = Pdf()
    helv = p.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    big = bitmap(TEXT, 50)            # ~50 px glyph height at 300 dpi = 12 pt
    w, h = big.size
    mask = p.add((f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ImageMask true /BitsPerComponent 1 /Decode [1 0] /Filter /FlateDecode >>'.encode(), zlib.compress(packbits(big, True))))
    gray = p.add((f'<< /Type /XObject /Subtype /Image /Width {w} /Height {h} /ColorSpace /DeviceGray /BitsPerComponent 1 /Filter /FlateDecode >>'.encode(), zlib.compress(packbits(big, False))))
    # Type3 font: one glyph per character, 16 px tall bitmaps (like an OCR or TeX pk font at 10-12 pt)
    chars = sorted(set(TEXT.replace(' ', '')))
    procs = {}; widths = {}
    for ch in chars:
        g = bitmap(ch, 16); gw, gh = g.size
        data = packbits(g, True)
        procs[ch] = p.add((b'<< >>', f'{gw} 0 0 0 {gw} {gh} d1\n{gw} 0 0 {gh} 0 0 cm\nBI /W {gw} /H {gh} /BPC 1 /IM true /Decode [1 0] ID '.encode() + data + b'\nEI'))
        widths[ord(ch)] = gw
    procs[' '] = p.add((b'<< >>', b'6 0 0 0 0 0 d1\n')); widths[32] = 6; chars = [' '] + chars
    first, last = 32, 122
    wl = ' '.join(str(widths.get(c, 6 if c == 32 else 0)) for c in range(first, last + 1))
    names = ' '.join(f'{ord(ch)} /g{ord(ch)}' for ch in chars)
    cp = ' '.join(f'/g{ord(ch)} {procs[ch]} 0 R' for ch in chars)
    t3 = p.add(f'<< /Type /Font /Subtype /Type3 /FontBBox [0 0 40 20] /FontMatrix [0.0625 0 0 0.0625 0 0] /CharProcs << {cp} >> /Encoding << /Type /Encoding /Differences [{names}] >> /FirstChar {first} /LastChar {last} /Widths [{wl}] /Resources << >> >>'.encode())
    cs = b'0 g\n'
    y = 780
    for size_pt in (12, 9):
        sc = size_pt / 12.0
        dw, dh = w * 72 / 300 * sc, h * 72 / 300 * sc
        cs += f'BT /F1 9 Tf 40 {y + 22} Td (1 /ImageMask stencil, {size_pt} pt) Tj ET\n'.encode()
        cs += f'q {dw:.3f} 0 0 {dh:.3f} 40 {y:.1f} cm /Im1 Do Q\n'.encode(); y -= 50
        cs += f'BT /F1 9 Tf 40 {y + 22} Td (2 DeviceGray 1-bit image, {size_pt} pt) Tj ET\n'.encode()
        cs += f'q {dw:.3f} 0 0 {dh:.3f} 40 {y:.1f} cm /Im2 Do Q\n'.encode(); y -= 50
        cs += f'BT /F1 9 Tf 40 {y + 22} Td (3 Type3 image-mask glyphs, {size_pt} pt) Tj ET\n'.encode()
        tx = ''.join(c if c != ' ' else ' ' for c in TEXT)
        cs += f'BT /F3 {size_pt * 0.6:.2f} Tf 40 {y} Td ({tx}) Tj ET\n'.encode(); y -= 60
    content = p.add((b'<< >>', cs))
    pages_id = len(p.objs) + 2
    page = p.add(f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Contents {content} 0 R /Resources << /Font << /F1 {helv} 0 R /F3 {t3} 0 R >> /XObject << /Im1 {mask} 0 R /Im2 {gray} 0 R >> >> >>'.encode())
    pages = p.add(f'<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>'.encode())
    assert pages == pages_id
    root = p.add(f'<< /Type /Catalog /Pages {pages} 0 R >>'.encode())
    p.write(path, root)

def pad(im, w, h):
    # glyph bitmap centred in a w x h cell, bottom-aligned like the glyphs above
    cell = Image.new('1', (w, h), 1)
    cell.paste(im, ((w - im.size[0]) // 2, h - im.size[1]))
    return cell

def ruler(w, h, k):
    # w x h glyph whose only ink is a one-pixel vertical stroke in column k (rows 2 .. h-3)
    im = Image.new('1', (w, h), 1)
    ImageDraw.Draw(im).line([(k, 2), (k, h - 3)], fill=0)
    return im

def type3_font(p, glyphs):
    # glyphs: {char code: 1-bit PIL image}; image-mask glyphs as in main(), 16 glyph px per em
    procs = {}; widths = {}
    for code, g in glyphs.items():
        gw, gh = g.size
        data = packbits(g, True)
        procs[code] = p.add((b'<< >>', f'{gw} 0 0 0 {gw} {gh} d1\n{gw} 0 0 {gh} 0 0 cm\nBI /W {gw} /H {gh} /BPC 1 /IM true /Decode [1 0] ID '.encode() + data + b'\nEI'))
        widths[code] = gw
    procs[32] = p.add((b'<< >>', b'6 0 0 0 0 0 d1\n')); widths[32] = 6
    first, last = min(procs), max(procs)
    wl = ' '.join(str(widths.get(c, 0)) for c in range(first, last + 1))
    names = ' '.join(f'{c} /g{c}' for c in sorted(procs))
    cp = ' '.join(f'/g{c} {procs[c]} 0 R' for c in sorted(procs))
    return p.add(f'<< /Type /Font /Subtype /Type3 /FontBBox [0 0 40 20] /FontMatrix [0.0625 0 0 0.0625 0 0] /CharProcs << {cp} >> /Encoding << /Type /Encoding /Differences [{names}] >> /FirstChar {first} /LastChar {last} /Widths [{wl}] /Resources << >> >>'.encode())

EDGE_TEXT = 'Hamburgefonstiv 0123456789'
EDGE_DPI = 96
EDGE_SCALE = 0.86                         # device px per glyph px at EDGE_DPI
EDGE_TF = EDGE_SCALE * 16 * 72 / EDGE_DPI  # 10.32 pt with the 1/16 FontMatrix
EDGE_H = 20                                # 20 -> 18 px tall: not an affected pair

def edge(path):
    """mask_downscale_edge.pdf: Type3 image-mask glyphs in 25 px and 24 px wide cells, shrunk to
    0.86 device px per glyph px at 96 dpi: 25 -> 22 px (22 * (25 / 22) > 25 in f64) and the
    control 24 -> 21 px. Rows 1-2: 'ruler' glyphs, glyph k with one 1 px stroke in column k
    (codes 65 + k). Rows 3-4: the glyphs of main() padded to the cell width."""
    p = Pdf()
    helv = p.add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    fonts = {}
    for w in (25, 24):
        fonts[f'R{w}'] = type3_font(p, {65 + k: ruler(w, EDGE_H, k) for k in range(w)})
        fonts[f'T{w}'] = type3_font(p, {ord(ch): pad(bitmap(ch, 16), w, EDGE_H) for ch in sorted(set(EDGE_TEXT.replace(' ', '')))})
    cs = b'0 g\n'
    y = 200
    rows = [('R25', ''.join(chr(65 + k) for k in range(25)), '1 Type3 ruler glyphs, 25 px cells (25 -> 22 px at 96 dpi)'),
            ('R24', ''.join(chr(65 + k) for k in range(24)), '2 Type3 ruler glyphs, 24 px cells (24 -> 21 px at 96 dpi, control)'),
            ('T25', EDGE_TEXT, '3 Type3 text glyphs, 25 px cells (25 -> 22 px at 96 dpi)'),
            ('T24', EDGE_TEXT, '4 Type3 text glyphs, 24 px cells (24 -> 21 px at 96 dpi, control)')]
    for font, text, label in rows:
        cs += f'BT /F1 9 Tf 40 {y + 22} Td ({label}) Tj ET\n'.encode()
        cs += f'BT /{font} {EDGE_TF:.2f} Tf 40 {y} Td ({text}) Tj ET\n'.encode(); y -= 55
    content = p.add((b'<< >>', cs))
    pages_id = len(p.objs) + 2
    fres = ' '.join(f'/{k} {v} 0 R' for k, v in fonts.items())
    page = p.add(f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 240] /Contents {content} 0 R /Resources << /Font << /F1 {helv} 0 R {fres} >> >> >>'.encode())
    pages = p.add(f'<< /Type /Pages /Kids [{page} 0 R] /Count 1 >>'.encode())
    assert pages == pages_id
    root = p.add(f'<< /Type /Catalog /Pages {pages} 0 R >>'.encode())
    p.write(path, root)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--edge':
        edge(sys.argv[2] if len(sys.argv) > 2 else 'mask_downscale_edge.pdf')
    else:
        main(sys.argv[1] if len(sys.argv) > 1 else 'mask_downscale.pdf')
