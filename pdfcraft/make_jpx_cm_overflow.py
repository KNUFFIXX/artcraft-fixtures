#!/usr/bin/env python3
"""make_jpx_cm_overflow.py (DRACO-AC03) - synthetic fixture: a 64x64 grey JPEG 2000 (JP2, written by Pillow/OpenJPEG,
two diagonal lines) drawn with `100 0 0 9223372036854775807 0 0 cm` (the d entry is i64::MAX).
Found by mutation fuzzing (the mutated file came from a public PDFium test file); rebuilt here from scratch."""
import io, sys
from PIL import Image

def jp2():
    im = Image.new('L', (64, 64), 255)
    for x in range(64):
        im.putpixel((x, x), 0); im.putpixel((63 - x, x), 0)
    b = io.BytesIO(); im.save(b, format='JPEG2000'); return b.getvalue()

def pdf(path, cm):
    j = jp2()
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /XObject << /Im1 5 0 R >> >> >>',
            (b'<< >>', f'q {cm} cm /Im1 Do Q'.encode()),
            (b'<< /Type /XObject /Subtype /Image /Width 64 /Height 64 /ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /JPXDecode >>', j)]
    out = bytearray(b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n'); offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        if isinstance(o, tuple):
            d, s = o; out += f'{i} 0 obj\n'.encode() + d[:-2] + f' /Length {len(s)} >>\nstream\n'.encode() + s + b'\nendstream\nendobj\n'
        else:
            out += f'{i} 0 obj\n'.encode() + o + b'\nendobj\n'
    x = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
    for o in offs: out += f'{o:010d} 00000 n \n'.encode()
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
    open(path, 'wb').write(out)

if __name__ == '__main__':
    pdf('jpx_cm_i64max.pdf', '100 0 0 9223372036854775807 0 0')   # panics (divide by zero) in hayro-jpeg2000
    pdf('jpx_cm_ok.pdf', '100 0 0 100 50 50')                       # same image, ordinary placement: renders
