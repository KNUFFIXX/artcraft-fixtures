# artcraft-fixtures

Small, contributor-original test documents behind bug reports to the [ArtCraft](https://getartcraft.com) projects (PdfCraft, GridCraft, LightCraft, FilmCraft), from the testing setup of Udo Funk ([@KNUFFIXX](https://github.com/KNUFFIXX)): real-world documents are used to *find* problems, and every problem that gets reported is rebuilt here as a synthetic file.

- Every PDF in `pdfcraft/` is written by a script in the same folder: [`make_fixtures.py`](pdfcraft/make_fixtures.py), [`make_mask_fixtures.py`](pdfcraft/make_mask_fixtures.py), [`make_tounicode_name.py`](pdfcraft/make_tounicode_name.py), [`make_jpx_cm_overflow.py`](pdfcraft/make_jpx_cm_overflow.py), [`make_fuzz_rebuilds.py`](pdfcraft/make_fuzz_rebuilds.py) (Python 3 + fontTools, Pillow). Fonts and images: the standard-14 Helvetica (never embedded), subsets of DejaVu Sans (Bitstream Vera licence), hand-drawn 8×14 bitmaps and bitmaps rendered from DejaVu Sans. No real-world content, no personal data.
- Every workbook in `gridcraft/` is written by a script in the same folder ([`make_fixtures.py`](gridcraft/make_fixtures.py), [`make_gc_legacy_to_array.py`](gridcraft/make_gc_legacy_to_array.py), [`make_gc_shared_image.py`](gridcraft/make_gc_shared_image.py)) (Python 3 + openpyxl 3.1; two files are hand-written OOXML packages). Expected values are the ones a Microsoft 365 Excel (de-DE) computes, measured through COM, and are written into each file next to the test cells. No real-world content, no personal data.
- Every JPEG in `lightcraft/` is written by [`make_lc_fixtures.py`](lightcraft/make_lc_fixtures.py) (Python 3; Pillow only for the pixels, the EXIF is built byte by byte so every tag value is explicit): 480×320 colour bars and a grey ramp drawn in code. No real-world content, no personal data.
- Licence: MIT OR Apache-2.0, at your option (`LICENSE-MIT`, `LICENSE-APACHE`), so each file can be taken into a project's regression tests as is.
- The reports are tested and written by Claude (Anthropic) on behalf of Udo Funk, who reviews every file and report before it is published.

## PdfCraft

| File | Reproduces | Report |
|---|---|---|
| `pdfcraft/double_letters_condensed_tz.pdf` | text extraction drops adjacent identical narrow glyphs in condensed text (`Tz` ≤ 80 %) | [storytold/pdfcraft#1467](https://github.com/storytold/pdfcraft/issues/1467) |
| `pdfcraft/symbolic_truetype_mac_cmap_no_tounicode.pdf` | non-ASCII characters lost: symbolic TrueType, (1,0) cmap only, no `/Encoding`, no `/ToUnicode` | [storytold/pdfcraft#1468](https://github.com/storytold/pdfcraft/issues/1468) |
| `pdfcraft/nonsymbolic_truetype_partial_tounicode.pdf` | non-ASCII characters lost: nonsymbolic TrueType, `/ToUnicode` covers 0x20–0x7E only | [storytold/pdfcraft#1468](https://github.com/storytold/pdfcraft/issues/1468) |
| `pdfcraft/type3_imagemask_tr2.pdf` (+ `type3tr_compare_150.png`) | Type 3 glyphs drawn bold under text rendering mode 2 | [storytold/pdfcraft#1469](https://github.com/storytold/pdfcraft/issues/1469) |
| `pdfcraft/flatten_orphan_field.pdf` | `doc_flatten` keeps a field whose widget is on no page | [storytold/pdfcraft#1470](https://github.com/storytold/pdfcraft/issues/1470) |
| `pdfcraft/tounicode_name_identity_h.pdf`, `type0_identity_no_tounicode.pdf` | no text from a Type 0 / Identity-H font with an embedded TrueType and no usable `/ToUnicode` (the name `/Identity-H`, or none) | [storytold/pdfcraft#1699](https://github.com/storytold/pdfcraft/issues/1699) |
| `pdfcraft/mask_downscale.pdf` (+ `mask_downscale_compare.png`) | 1-bit stencil masks, 1-bit images and Type 3 bitmap glyphs shrunk at render time; Type 3 glyphs lose strokes below 2:1 | [storytold/pdfcraft#1700](https://github.com/storytold/pdfcraft/issues/1700) |
| `pdfcraft/jpx_cm_i64max.pdf` (control: `jpx_cm_ok.pdf`) | a JPX image under `cm` with an out-of-range integer panics in hayro-jpeg2000 (divide by zero); found by fuzzing, rebuilt by [`make_jpx_cm_overflow.py`](pdfcraft/make_jpx_cm_overflow.py) | [storytold/pdfcraft#1761](https://github.com/storytold/pdfcraft/issues/1761) |
| `pdfcraft/rc4_r3_length256.pdf` (control: `rc4_r3_length128.pdf`) | Standard security handler V 2 / R 3 with `/Length 256` panics on open; found by fuzzing, rebuilt by [`make_fuzz_rebuilds.py`](pdfcraft/make_fuzz_rebuilds.py) | [storytold/pdfcraft#1769](https://github.com/storytold/pdfcraft/issues/1769) |
| `pdfcraft/tiling_bbox_wide.pdf` (control: `tiling_bbox_ok.pdf`) | tiling pattern with a /BBox far larger than its step panics in the renderer (0-px cell); found by fuzzing, rebuilt by [`make_fuzz_rebuilds.py`](pdfcraft/make_fuzz_rebuilds.py) | [storytold/pdfcraft#1770](https://github.com/storytold/pdfcraft/issues/1770) |

## GridCraft

Found in a run of GridCraft 0.5.0 over 663 real-world workbooks (12 Oct 2026), re-checked on 0.6.1; [storytold/gridcraft#891](https://github.com/storytold/gridcraft/issues/891) has the overview. Files whose bug is already fixed stay here as regression fixtures.

| File | Reproduces | Report |
|---|---|---|
| `gridcraft/gc_coerce_de.xlsx` | text-to-number/date coercion ignores the regional separators (de-DE) | [storytold/gridcraft#889](https://github.com/storytold/gridcraft/issues/889) |
| `gridcraft/gc_sort_collation.xlsx` | SORT/SORTBY order by code point instead of Excel's locale collation (regenerated 13 Oct with Excel's file syntax `_xlfn._xlws.SORT`/`_xlfn.SORTBY`; the first version opened in GridCraft but not in Excel) | [storytold/gridcraft#890](https://github.com/storytold/gridcraft/issues/890) |
| `gridcraft/gc_implicit_intersection.xlsx`, `gc_scoped_names.xlsx` | no implicit intersection for legacy formulas: whole-column names/ranges spill or take the first value | [storytold/gridcraft#410](https://github.com/storytold/gridcraft/issues/410) (comment) |
| `gridcraft/gc_table_thisrow.xlsx` | structured references saved as `[@col]`; Excel refuses (or crashes on) the saved file | [storytold/gridcraft#864](https://github.com/storytold/gridcraft/issues/864), fixed by #869 |
| `gridcraft/gc_normal_font_arial10.xlsx`, `gc_normal_font_aptos.xlsx` | the workbook's Normal style (cellXfs 0) is replaced by Calibri 11 on open | [storytold/gridcraft#805](https://github.com/storytold/gridcraft/issues/805), fixed by #823 |
| `gridcraft/gc_table_header_newline.xlsx` | line break in a table column name (`_x000a_`) became a space and overwrote the header cell (0.5.0) | fixed in 0.6.1, not reported |
| `gridcraft/gc_legacy_to_array.xlsx`, `gc_legacy_to_array_small.xlsx` | legacy formulas over whole-column names saved as dynamic arrays: Excel 365 grows to 19 GB or crashes on the saved file (writer side of #410) | [storytold/gridcraft#417](https://github.com/storytold/gridcraft/pull/417) (comment) |
| `gridcraft/gc_shared_image.xlsx` | a picture shared by four sheets is written four times on save | [storytold/gridcraft#985](https://github.com/storytold/gridcraft/issues/985) |

## LightCraft

Found in a run of LightCraft 0.7.1 over 600 real-world photos (13 Oct 2026); every finding is rebuilt by [`make_lc_fixtures.py`](lightcraft/make_lc_fixtures.py).

| File | Reproduces | Report |
|---|---|---|
| `lightcraft/lc_gps_placeholder.jpg` | an empty GPS block (refs NUL, every rational 0/0, as Android phones write it without a position fix) is read as 0° N 0° E and written into exports | [storytold/lightcraft#1617](https://github.com/storytold/lightcraft/issues/1617) |
| `lightcraft/lc_make_model.jpg` | export drops EXIF Make and writes Model as "Canon Canon IXUS 185"; also the landscape example for the export box size (Width & Height vs Dimensions) | [storytold/lightcraft#1618](https://github.com/storytold/lightcraft/issues/1618), [#1620](https://github.com/storytold/lightcraft/issues/1620) |
| `lightcraft/lc_exposure_0.3s.jpg` … `lc_exposure_3.2s.jpg` | shutter speeds between 1/4 s and 4 s rounded to whole steps, on display and in the exported EXIF/XMP | [storytold/lightcraft#1619](https://github.com/storytold/lightcraft/issues/1619) |

## FilmCraft

Found in a run of FilmCraft 0.7.2 (Windows x64) over 92 real-world video files (13 Oct 2026). Every file in `filmcraft/` is written by [`make_fixtures.sh`](filmcraft/make_fixtures.sh) from ffmpeg's built-in test sources (`testsrc2`, `aevalsrc`); no camera footage, no personal data.

| File | Reproduces | Report |
|---|---|---|
| `filmcraft/fps30_ms_timestamps.mp4`, `fps60_ms_timestamps.mp4` | frame times rounded to whole milliseconds in a 90 kHz track are read as 30.303 / 58.824 fps; New Sequence From Clip then drops frames | [storytold/filmcraft#1700](https://github.com/storytold/filmcraft/issues/1700) |
| `filmcraft/surround51_ac3.mp4`, `surround51_eac3.mp4`, `surround51side_aac_pce.mp4` (controls: `surround51_ac3.mov`, `surround51_ac3.mkv`) | 5.1 in MP4 read as stereo: centre, LFE and surrounds silent | [storytold/filmcraft#1701](https://github.com/storytold/filmcraft/issues/1701) |
| `filmcraft/av1_in_mp4.mp4`, `h264_in_mkv.mkv` | empty pixel format in Media File Properties | [storytold/filmcraft#1702](https://github.com/storytold/filmcraft/issues/1702) |
