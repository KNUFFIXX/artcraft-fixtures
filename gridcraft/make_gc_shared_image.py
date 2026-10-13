#!/usr/bin/env python3
"""make_gc_shared_image.py (DRACO-AC03) - one 160 KB PNG (seeded noise) shown on four sheets through ONE media part:
every drawing's rels point to xl/media/image1.png, as Excel writes a picture copied between sheets."""
import io, random, re, zipfile, openpyxl
from openpyxl.drawing.image import Image as XLImage
from PIL import Image

def main(path):
    rnd = random.Random(7)
    im = Image.frombytes('RGB', (240, 240), bytes(rnd.randrange(256) for _ in range(240 * 240 * 3)))
    buf = io.BytesIO(); im.save(buf, format='PNG'); open('_logo.png', 'wb').write(buf.getvalue())
    wb = openpyxl.Workbook()
    for k in range(4):
        ws = wb.active if k == 0 else wb.create_sheet()
        ws.title = f'S{k + 1}'; ws['A1'] = f'Sheet {k + 1}'
        ws.add_image(XLImage('_logo.png'), 'C3')
    tmp = io.BytesIO(); wb.save(tmp)
    src = zipfile.ZipFile(tmp); out = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    for n in src.namelist():
        d = src.read(n)
        if re.match(r'xl/media/image[2-9]\.png$', n): continue
        if n.startswith('xl/drawings/_rels/'): d = re.sub(rb'image\d+\.png', b'image1.png', d)
        out.writestr(n, d)
    out.close()

if __name__ == '__main__':
    main('gc_shared_image.xlsx')
