#!/usr/bin/env python3
"""Contributor-original fixture for a PdfCraft bug report (KNUFFIXX/artcraft-fixtures, pdfcraft/).

inline_image_ei_lookahead.pdf - four A5 pages, each drawn by hand below with the standard-14 Helvetica (never embedded)
and two tiny hand-made inline images. No real-world documents, no personal data.

  page 1  inline image, then a line with WinAnsi bytes (u-umlaut, sharp s), then a line with the capitals "EI"
  page 2  control: the same with lower-case "ei"
  page 3  control: the same without a byte above 0x7F before the "EI"
  page 4  the pattern of OCR'd scans: a 1x1 ASCII85 image mask, then invisible text (3 Tr) with umlauts and "EI"

    python3 make_inline_image_ei.py       # writes inline_image_ei_lookahead.pdf into the current directory

Licence: MIT OR Apache-2.0, at your option. Written by Claude (Anthropic) on behalf of Udo Funk.
"""
import io

IMAGE = b'q 120 0 0 60 40 430 cm BI /W 2 /H 2 /BPC 8 /CS /G ID \x00\x80\x80\x00 EI Q\n'
MASK = b'q 0 0 1 rg 40 520 m 160 520 l 160 532 l 40 532 l h W* n q 120 12 0 0 40 520 cm BI /IM true/F[/A85]/H 1/W 1/BPC 1 ID !!~> EI Q Q\n'


def lines(texts, y0, tr=0):
    out = b'BT /F1 14 Tf %d Tr ' % tr
    y = y0
    for t in texts:
        out += b'1 0 0 1 40 %d Tm (%s) Tj ' % (y, t)
        y -= 24
    return out + b'0 Tr ET\n'


def title(t):
    return b'BT /F1 11 Tf 1 0 0 1 40 560 Tm (%s) Tj ET\n' % t


PAGES = [
    title(b'Page 1: inline image, then WinAnsi umlauts, then capitals EI') + IMAGE +
    lines([b'Line 1: plain ASCII after the image', b'Line 2: Gr\xfc\xdfe aus K\xf6ln', b'Line 3: EINGANG'], 390),
    title(b'Page 2 (control): the same with lower-case ei') + IMAGE +
    lines([b'Line 1: plain ASCII after the image', b'Line 2: Gr\xfc\xdfe aus K\xf6ln', b'Line 3: eingang'], 390),
    title(b'Page 3 (control): EI without a byte above 0x7F before it') + IMAGE +
    lines([b'Line 1: plain ASCII after the image', b'Line 2: Gruesse aus Koeln', b'Line 3: EINGANG'], 390),
    title(b'Page 4: OCR pattern - 1x1 ASCII85 mask, then invisible text') + MASK +
    lines([b'Line 1: invisible OCR text', b'Line 2: Gr\xfc\xdfe aus K\xf6ln', b'Line 3: EINGANG'], 490, tr=3),
]


def build(path):
    objs = []

    def add(b):
        objs.append(b)
        return len(objs)
    font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    pages_id = len(objs) + 2 * len(PAGES) + 1
    kids = []
    for content in PAGES:
        c = add(b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream')
        kids.append(add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 420 595] /Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>' % (pages_id, font, c)))
    assert add(b'<< /Type /Pages /Kids [' + b' '.join(b'%d 0 R' % k for k in kids) + b'] /Count %d >>' % len(kids)) == pages_id
    root = add(b'<< /Type /Catalog /Pages %d 0 R >>' % pages_id)
    out = io.BytesIO()
    out.write(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n')
    offs = []
    for i, b in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(b'%d 0 obj\n' % i + b + b'\nendobj\n')
    x = out.tell()
    out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for o in offs:
        out.write(b'%010d 00000 n \n' % o)
    out.write(b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, root, x))
    open(path, 'wb').write(out.getvalue())
    print('wrote', path, out.tell(), 'bytes')


if __name__ == '__main__':
    build('inline_image_ei_lookahead.pdf')
