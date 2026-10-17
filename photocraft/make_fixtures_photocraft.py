#!/usr/bin/env python3
"""Synthetic fixtures for PhotoCraft 0.9.0 findings (THV-AC04, 17.10.2026). Own pixels, own EXIF values.

exposure_fraction.jpg: 64x64 grey gradient, EXIF ExposureTime 31714/1000000 s (about 1/32 s),
  FNumber 1.9, ISO 400, Make "Example", Model "Fixture Cam". PhotoCraft File Info shows "0.03 s".
exposure_fraction_2.jpg: same, ExposureTime 215/10000 s (about 1/47 s). PhotoCraft shows "0.02 s".
Requires Pillow. Usage: python make_fixtures_photocraft.py [outdir]
"""
import os, sys
from PIL import Image
from PIL.TiffImagePlugin import IFDRational as R

out = sys.argv[1] if len(sys.argv) > 1 else '.'
os.makedirs(out, exist_ok=True)
im = Image.linear_gradient('L').resize((64, 64)).convert('RGB')


def exif(num, den):
    ex = Image.Exif()
    ex[0x010F] = 'Example'
    ex[0x0110] = 'Fixture Cam'
    e2 = ex.get_ifd(0x8769)
    e2[0x829A] = R(num, den)      # ExposureTime
    e2[0x829D] = R(19, 10)        # FNumber
    e2[0x8827] = 400              # ISOSpeedRatings
    return ex


im.save(os.path.join(out, 'exposure_fraction.jpg'), quality=90, exif=exif(31714, 1000000))
im.save(os.path.join(out, 'exposure_fraction_2.jpg'), quality=90, exif=exif(215, 10000))
print('ok')
