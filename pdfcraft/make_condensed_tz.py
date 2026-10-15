#!/usr/bin/env python3
"""Contributor-original fixture for a PdfCraft bug report (KNUFFIXX/artcraft-fixtures, pdfcraft/).

condensed_tz_ocr.pdf - one landscape A4 page, drawn by hand below with the standard-14 Helvetica (never embedded): the same line of
words with doubled and single letters, horizontally scaled with Tz 100, 50, 30, 20, 10 and 5 - the way OCR text layers
squeeze each word into its box on the scan. No real-world documents, no personal data.

    python3 make_condensed_tz.py      # writes condensed_tz_ocr.pdf into the current directory

Licence: MIT OR Apache-2.0, at your option. Written by Claude (Anthropic) on behalf of Udo Funk.
"""
import io

WORDS = b'Hallo Mitte Wille Kommission Illustration still Brunnen Kaffee'
SCALES = (100, 50, 30, 20, 10, 5)


def build(path):
    content = b''
    y = 540
    for tz in SCALES:
        content += b'BT /F1 9 Tf 100 Tz 1 0 0 1 30 %d Tm (Tz %d:) Tj ET\n' % (y, tz)
        content += b'BT /F1 24 Tf %d Tz 1 0 0 1 80 %d Tm (%s) Tj 100 Tz ET\n' % (tz, y - 4, WORDS)
        y -= 80
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
            b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
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
    out.write(b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x))
    open(path, 'wb').write(out.getvalue())
    print('wrote', path, out.tell(), 'bytes')


if __name__ == '__main__':
    build('condensed_tz_ocr.pdf')
