#!/usr/bin/env python3
"""make_fuzz_rebuilds.py (DRACO-AC03) - synthetic rebuilds of two fuzzing finds (written from scratch, no fuzzer output):
  tiling_bbox_wide.pdf       tiling pattern, /BBox [0 0 100000 10], /XStep 10 /YStep 10 (control: tiling_bbox_ok.pdf, BBox [0 0 10 10])
  rc4_r3_length256.pdf       Standard security handler /V 2 /R 3 with /Length 256 (control: rc4_r3_length128.pdf, /Length 128)"""

def write(path, objs, trailer_extra=b''):
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
    out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R'.encode() + trailer_extra + f' >>\nstartxref\n{x}\n%%EOF\n'.encode()
    open(path, 'wb').write(out)

def tiling(path, bbox):
    write(path, [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Pattern << /P1 5 0 R >> >> >>',
        (b'<< >>', b'/Pattern cs /P1 scn 0 0 100 100 re f'),
        (f'<< /Type /Pattern /PatternType 1 /PaintType 1 /TilingType 1 /BBox {bbox} /XStep 10 /YStep 10 /Resources << >> >>'.encode(),
         b'0.5 g 0 0 5 5 re f'),
    ])

def rc4(path, length):
    o = '28bf4e5e4e758a4164004e56fffa01082e2e00b6d0683e802f0ca9fe6453697a'
    write(path, [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>',
        f'<< /Filter /Standard /V 2 /R 3 /Length {length} /O <{o}> /U <{"00" * 32}> /P -4 >>'.encode(),
    ], b' /Encrypt 4 0 R /ID [<0123456789abcdef0123456789abcdef> <0123456789abcdef0123456789abcdef>]')

if __name__ == '__main__':
    tiling('tiling_bbox_wide.pdf', '[0 0 100000 10]')
    tiling('tiling_bbox_ok.pdf', '[0 0 10 10]')
    rc4('rc4_r3_length256.pdf', 256)
    rc4('rc4_r3_length128.pdf', 128)
