#!/usr/bin/env python3
"""make_fixtures_vectorcraft.py (THV-AC04, 17.10.2026) - synthetic fixtures for VectorCraft reports.

Python standard library only, own geometry and text, written from the public MS-WMF and PDF
specifications (no Office or Adobe program involved; the PDF uses Helvetica, not embedded). Usage: python make_fixtures_vectorcraft.py [out_dir]

wmf_window_ext.wmf
  Placeable WMF, box 0,0 - 1000,500 at 1000 units an inch (1 x 0.5 in = 72 x 36 pt).
  The records set MM_ANISOTROPIC, window origin 0,0 and window extent 4000 x 2000, then fill a red
  rectangle 1000,500 - 3000,1500 (logical units). A player maps the window onto the placeable box,
  so the rectangle covers the middle half of the picture: 18,9 - 54,27 pt.
wmf_window_org.wmf
  Same picture, but the logical coordinates are shifted: window origin 10000,20000, extent 1000 x 500
  (= the box size), rectangle 10250,20125 - 10750,20375. Expected: the same centred rectangle.
pdf_invisible_text.pdf
  Two lines of invisible text (Tr 3) over a grey box, like the OCR layer of a scanned page, and one
  visible line (Helvetica, not embedded).
pdf_zero_width_lines.pdf
  Lines and a box outline drawn with line width 0 (the thinnest renderable line), and 1 pt lines as a
  control (Helvetica labels, not embedded).
"""
import os
import struct
import sys


def rec(fn, *words):
    body = struct.pack('<%dh' % len(words), *words) if words else b''
    return struct.pack('<IH', 3 + len(words), fn) + body


def wmf(box, records):
    l, t, r, b, inch = box
    head = struct.pack('<IHhhhhHI', 0x9AC6CDD7, 0, l, t, r, b, inch, 0)
    chk = 0
    for (w,) in struct.iter_unpack('<H', head[:20]):
        chk ^= w
    placeable = head + struct.pack('<H', chk)
    body = b''.join(records) + rec(0x0000)
    max_rec = max(len(x) for x in records) // 2
    size_words = (18 + len(body)) // 2
    mfh = struct.pack('<HHHIHIH', 1, 9, 0x0300, size_words, 1, max_rec, 0)
    return placeable + mfh + body


def picture(org, ext, rect):
    x0, y0, x1, y1 = rect
    return [
        rec(0x0103, 8),                       # SETMAPMODE MM_ANISOTROPIC
        rec(0x020B, org[1], org[0]),          # SETWINDOWORG (y, x)
        rec(0x020C, ext[1], ext[0]),          # SETWINDOWEXT (y, x)
        rec(0x02FC, 0, 0x00FF, 0x0000, 0),    # CREATEBRUSHINDIRECT solid, COLORREF 0x000000FF = red
        rec(0x012D, 0),                       # SELECTOBJECT 0
        rec(0x0324, 4, x0, y0, x1, y0, x1, y1, x0, y1),  # POLYGON
    ]


def pdf(page_dict_extra, content):
    """one-page PDF 1.4, A4 portrait media box, Helvetica (standard 14, not embedded)"""
    objs = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] ' + page_dict_extra +
        b' /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
    ]
    out = b'%PDF-1.4\n'
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for o in offs:
        out += b'%010d 00000 n \n' % o
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    return out


# Invisible text (render mode 3) over a grey box, as an OCR layer lies over a scanned page, and one
# line of visible text. Expected after open + export to PDF: both lines can still be found
# (pdftotext), or the open result notes that the invisible text was left out.
INVISIBLE_CONTENT = (b'0.85 g 50 400 495 300 re f\n'
                     b'BT 3 Tr 0 g /F1 24 Tf 70 600 Td (Invisible OCR layer line one) Tj 0 -40 Td (Invisible OCR layer line two) Tj ET\n'
                     b'BT 0 Tr 0 g /F1 18 Tf 70 300 Td (Visible caption below the box) Tj ET\n')


# Zero-width lines: ISO 32000-1 (8.4.3.2) makes "0 w" the thinnest line the device can render (one
# device pixel). Two such lines, a light grey box filled and stroked with "0 w" (b operator), and
# two 1 pt lines as a control, each with a label.
ZERO_WIDTH_CONTENT = (b'0 G 0 w 50 700 m 545 700 l S 50 680 m 545 680 l S\n'
                      b'0.9 g 0 w 50 500 m 250 500 l 250 600 l 50 600 l b\n'
                      b'1 w 50 400 m 545 400 l S 50 380 m 545 380 l S\n'
                      b'0 g BT /F1 12 Tf 50 710 Td (two lines, 0 w) Tj 0 -100 Td (box filled and stroked, 0 w) Tj 0 -200 Td (two lines, 1 w) Tj ET\n')


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out, exist_ok=True)
    box = (0, 0, 1000, 500, 1000)
    files = {
        'wmf_window_ext.wmf': wmf(box, picture((0, 0), (4000, 2000), (1000, 500, 3000, 1500))),
        'wmf_window_org.wmf': wmf(box, picture((10000, 20000), (1000, 500), (10250, 20125, 10750, 20375))),
        'pdf_invisible_text.pdf': pdf(b'', INVISIBLE_CONTENT),
        'pdf_zero_width_lines.pdf': pdf(b'', ZERO_WIDTH_CONTENT),
    }
    for name, data in files.items():
        with open(os.path.join(out, name), 'wb') as f:
            f.write(data)
        print(name, len(data), 'bytes')


if __name__ == '__main__':
    main()
