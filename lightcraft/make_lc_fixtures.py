#!/usr/bin/env python3
"""make_lc_fixtures.py - synthetic LightCraft test fixtures (no personal data, no third-party assets).
Writes small 480x320 JPEGs (colour bars + grey ramp drawn in code) whose EXIF is built byte by byte,
so every tag value is explicit. Usage: python3 make_lc_fixtures.py [outdir]   (Pillow only for the pixels)

lc_gps_placeholder.jpg   GPS IFD as Android phones write it without a position fix: refs NUL, every rational 0/0
lc_make_model.jpg        Make "Canon", Model "Canon IXUS 185" (the model repeats the maker, as Canon writes it)
lc_exposure_*.jpg        ExposureTime 3/10 ... 32/10 s (third-stop values above 1/4 s)"""
import struct, sys, os
from PIL import Image, ImageDraw

out = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(out, exist_ok=True)

ASCII, SHORT, LONG, RATIONAL, BYTE, UNDEFINED = 2, 3, 4, 5, 1, 7

def tiff_exif(ifd0, exif=None, gps=None):
    """Little-endian TIFF block for an APP1 Exif segment. Each IFD is a list of (tag, type, value);
    ASCII values are bytes (written as given, NUL-terminated by the caller), RATIONAL values are
    lists of (num, den) pairs written verbatim (so 0/0 stays 0/0)."""
    def enc(typ, val):
        if typ in (ASCII, UNDEFINED, BYTE): return bytes(val), len(val)
        if typ == SHORT: return b''.join(struct.pack('<H', v) for v in val), len(val)
        if typ == LONG: return b''.join(struct.pack('<I', v) for v in val), len(val)
        if typ == RATIONAL: return b''.join(struct.pack('<II', n, d) for n, d in val), len(val)
        raise ValueError(typ)
    ifds = [('ifd0', list(ifd0))]
    if exif is not None: ifds.append(('exif', list(exif)))
    if gps is not None: ifds.append(('gps', list(gps)))
    # pointers are patched after layout
    if exif is not None: ifds[0][1].append((0x8769, LONG, [0]))
    if gps is not None: ifds[0][1].append((0x8825, LONG, [0]))
    for _, e in ifds: e.sort(key=lambda t: t[0])
    sizes = {name: 2 + 12 * len(e) + 4 for name, e in ifds}
    off, starts = 8, {}
    for name, e in ifds:
        starts[name] = off
        off += sizes[name]
        for tag, typ, val in e:
            data, _ = enc(typ, val)
            if len(data) > 4: off += len(data) + (len(data) & 1)
    blob = bytearray(b'II*\x00' + struct.pack('<I', 8))
    for name, e in ifds:
        assert len(blob) == starts[name]
        data_off = starts[name] + sizes[name]
        head, tail = bytearray(struct.pack('<H', len(e))), bytearray()
        for tag, typ, val in e:
            if tag == 0x8769: val = [starts['exif']]
            if tag == 0x8825: val = [starts['gps']]
            data, count = enc(typ, val)
            if len(data) <= 4:
                head += struct.pack('<HHI', tag, typ, count) + data.ljust(4, b'\x00')
            else:
                head += struct.pack('<HHII', tag, typ, count, data_off + len(tail))
                tail += data + (b'\x00' if len(data) & 1 else b'')
        head += struct.pack('<I', 0)
        blob += head + tail
    return b'Exif\x00\x00' + bytes(blob)

def picture(w=480, h=320):
    im = Image.new('RGB', (w, h), (128, 128, 128))
    d = ImageDraw.Draw(im)
    bars = [(200, 40, 40), (40, 160, 60), (40, 70, 200), (230, 200, 40), (240, 240, 240), (20, 20, 20)]
    for k, c in enumerate(bars):
        d.rectangle([k * w // 6, 0, (k + 1) * w // 6 - 1, h // 2], fill=c)
    for x in range(w):
        v = round(255 * x / (w - 1))
        d.line([(x, h // 2), (x, h - 1)], fill=(v, v, v))
    return im

def save(name, exif):
    p = os.path.join(out, name)
    picture().save(p, 'JPEG', quality=92, exif=exif)
    print('wrote', p, os.path.getsize(p), 'bytes')

s = lambda t: t.encode('ascii') + b'\x00'
base_exif = [(0x9000, UNDEFINED, b'0232'), (0x9003, ASCII, s('2025:06:01 12:00:00')),
             (0x829A, RATIONAL, [(1, 250)]), (0x829D, RATIONAL, [(28, 10)]), (0x8827, SHORT, [100])]

# 1) GPS block written by a phone without a position fix (seen from Google Pixel 10 Pro XL, Nothing Phone (3a) Pro,
#    Samsung Galaxy A14 5G, Xiaomi, Motorola moto e13): refs NUL, every rational 0/0.
gps_placeholder = [(0x0000, BYTE, [2, 2, 0, 0]), (0x0001, ASCII, b'\x00\x00'), (0x0002, RATIONAL, [(0, 0)] * 3),
                   (0x0003, ASCII, b'\x00\x00'), (0x0004, RATIONAL, [(0, 0)] * 3), (0x0005, BYTE, [0]),
                   (0x0006, RATIONAL, [(0, 0)]), (0x0007, RATIONAL, [(0, 0)] * 3), (0x001D, ASCII, b'\x00' * 11)]
save('lc_gps_placeholder.jpg', tiff_exif([(0x010F, ASCII, s('Example')), (0x0110, ASCII, s('Phone 1'))], base_exif, gps_placeholder))

# 2) Model that repeats the make, as Canon (and others) write it.
save('lc_make_model.jpg', tiff_exif([(0x010F, ASCII, s('Canon')), (0x0110, ASCII, s('Canon IXUS 185'))], base_exif))

# 3) Long exposures on the standard third-stop scale.
for num, den in [(3, 10), (4, 10), (6, 10), (8, 10), (13, 10), (16, 10), (25, 10), (32, 10)]:
    ex = [e for e in base_exif if e[0] != 0x829A] + [(0x829A, RATIONAL, [(num, den)])]
    save('lc_exposure_%.1fs.jpg' % (num / den), tiff_exif([(0x010F, ASCII, s('Example')), (0x0110, ASCII, s('Camera 1'))], ex))
