# artcraft-fixtures

Small, contributor-original test documents behind bug reports to the [ArtCraft](https://getartcraft.com) projects (PdfCraft, GridCraft, LightCraft, FilmCraft, WordCraft, EffectCraft, DeckCraft), from the testing setup of Udo Funk ([@KNUFFIXX](https://github.com/KNUFFIXX)): real-world documents are used to *find* problems, and every problem that gets reported is rebuilt here as a synthetic file.

- Every PDF in `pdfcraft/` is written by a script in the same folder: [`make_fixtures.py`](pdfcraft/make_fixtures.py), [`make_mask_fixtures.py`](pdfcraft/make_mask_fixtures.py), [`make_tounicode_name.py`](pdfcraft/make_tounicode_name.py), [`make_jpx_cm_overflow.py`](pdfcraft/make_jpx_cm_overflow.py), [`make_fuzz_rebuilds.py`](pdfcraft/make_fuzz_rebuilds.py) (Python 3 + fontTools, Pillow). Fonts and images: the standard-14 Helvetica (never embedded), subsets of DejaVu Sans (Bitstream Vera licence), hand-drawn 8×14 bitmaps and bitmaps rendered from DejaVu Sans. No real-world content, no personal data.
- Every workbook in `gridcraft/` is written by a script in the same folder ([`make_fixtures.py`](gridcraft/make_fixtures.py), [`make_gc_legacy_to_array.py`](gridcraft/make_gc_legacy_to_array.py), [`make_gc_shared_image.py`](gridcraft/make_gc_shared_image.py)) (Python 3 + openpyxl 3.1; two files are hand-written OOXML packages). Expected values are the ones a Microsoft 365 Excel (de-DE) computes, measured through COM, and are written into each file next to the test cells. No real-world content, no personal data.
- Every JPEG in `lightcraft/` is written by [`make_lc_fixtures.py`](lightcraft/make_lc_fixtures.py) (Python 3; Pillow only for the pixels, the EXIF is built byte by byte so every tag value is explicit): 480×320 colour bars and a grey ramp drawn in code. No real-world content, no personal data.
- Licence: MIT OR Apache-2.0, at your option (`LICENSE-MIT`, `LICENSE-APACHE`), so each file can be taken into a project's regression tests as is.
- The reports are tested and written by Claude (Anthropic) and posted for Udo Funk, emotional support human, who reads every report after it goes out; code pull requests still go out only after his review.

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
| `pdfcraft/inline_image_ei_lookahead.pdf` (+ `inline_image_ei_lookahead_p1_compare.png`, page 1 in PdfCraft 0.8.0 and pdftoppm; written by [`make_inline_image_ei.py`](pdfcraft/make_inline_image_ei.py)) | after an inline image, a byte above 0x7F followed by a later "EI" hides the rest of the page (not drawn, no text) | [storytold/pdfcraft#2456](https://github.com/storytold/pdfcraft/issues/2456) |
| `pdfcraft/condensed_tz_ocr.pdf` (written by [`make_condensed_tz.py`](pdfcraft/make_condensed_tz.py)) | text extraction drops doubled and repeated letters in text condensed to `Tz` 20 % or less (OCR text layers) | [storytold/pdfcraft#2457](https://github.com/storytold/pdfcraft/issues/2457) |
| `pdfcraft/mask_downscale_edge.pdf` (+ `mask_downscale_edge_compare.png`; generator `make_mask_fixtures.py --edge`) | ruler glyphs of 25 px drawn 21.5 px wide: a size pair where the averaging in PR #2288 falls back to picking (control: 24 px) | [storytold/pdfcraft#1700](https://github.com/storytold/pdfcraft/issues/1700) (comment on [PR #2288](https://github.com/storytold/pdfcraft/pull/2288)) |

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
| `gridcraft/gc_text_cr.xlsx` | a carriage return in cell text (CR LF, lone CR; `_x000D_` in the shared strings) is saved as a raw CR, so Excel and GridCraft read it back as LF | [storytold/gridcraft#1488](https://github.com/storytold/gridcraft/issues/1488) |
| `gridcraft/gc_cell_info_de.xlsx` | `CELL("filename")` is empty and German info types (`"dateiname"`, `"adresse"`, `"zeile"` …, kept as typed by a German Excel) give `#VALUE!`; the sheet-name formula fails | [storytold/gridcraft#1489](https://github.com/storytold/gridcraft/issues/1489) |
| `gridcraft/gc_text_codes_de.xlsx` | `TEXT` format codes of a German Excel (`TT.MM.JJJJ`, `TTTT`, `#.##0,00`) are read with the English codes | [storytold/gridcraft#889](https://github.com/storytold/gridcraft/issues/889) (comment) |
| `gridcraft/gc_formula_whitespace.xlsx` | line breaks and spaces inside formulas (Alt+Enter layout, `LET` one name per line) are removed on save; values unchanged | [storytold/gridcraft#1490](https://github.com/storytold/gridcraft/issues/1490) |
| `gridcraft/gc_spill_single.xlsx` | the spill operator on a dynamic-array formula that currently returns one value (`ROWS(C1#)`, `SUM(C1#)`) gives `#REF!` | [storytold/gridcraft#1491](https://github.com/storytold/gridcraft/issues/1491) |
| `gridcraft/gc_sumproduct_if_da.xlsx` | `SUMPRODUCT(IF(ISERROR(…)))` stored as a dynamic array is saved without `cm`, so Excel inserts `@` and shows `#VALUE!` | [storytold/gridcraft#64](https://github.com/storytold/gridcraft/issues/64) (comment) |

## LightCraft

Found in a run of LightCraft 0.7.1 over 600 real-world photos (13 Oct 2026); every finding is rebuilt by [`make_lc_fixtures.py`](lightcraft/make_lc_fixtures.py). Findings from public CC0 raw samples (raw.pixls.us) link those files directly, e.g. [storytold/lightcraft#1671](https://github.com/storytold/lightcraft/issues/1671).

| File | Reproduces | Report |
|---|---|---|
| `lightcraft/lc_gps_placeholder.jpg` | an empty GPS block (refs NUL, every rational 0/0, as Android phones write it without a position fix) is read as 0° N 0° E and written into exports | [storytold/lightcraft#1617](https://github.com/storytold/lightcraft/issues/1617) |
| `lightcraft/lc_make_model.jpg` | export drops EXIF Make and writes Model as "Canon Canon IXUS 185"; also the opaque example for the export box size (Width & Height vs Dimensions) and for the always-present alpha channel of 8-bit PNG/TIFF/WebP exports | [storytold/lightcraft#1618](https://github.com/storytold/lightcraft/issues/1618), [#1620](https://github.com/storytold/lightcraft/issues/1620), [#1670](https://github.com/storytold/lightcraft/issues/1670) |
| `lightcraft/lc_exposure_0.3s.jpg` … `lc_exposure_3.2s.jpg` | shutter speeds between 1/4 s and 4 s rounded to whole steps, on display and in the exported EXIF/XMP | [storytold/lightcraft#1619](https://github.com/storytold/lightcraft/issues/1619) |
| `lightcraft/lc_exposure_3-100s.jpg`, `lc_exposure_6-100s.jpg`, `lc_exposure_8-100s.jpg`, `lc_exposure_49-1000s.jpg` (control: `lc_exposure_1-30s.jpg`) | short decimal exposure times (3/100 s, 6/100 s, 8/100 s, 49/1000 s) rounded to the nearest 1/N on import, in the catalog and in the exported EXIF/XMP | [storytold/lightcraft#1619](https://github.com/storytold/lightcraft/issues/1619) (comment) |
| `lightcraft/lc_mpo_two_images.jpg` | MPO with two different images: checked, LightCraft imports the primary image (no bug found) | — |
| `lightcraft/lc_icc_gamma18.png`, `lc_icc_gamma18_rgba.png`, `lc_icc_gamma18.jpg` | embedded display profile (gamma 1.8, sampled curves, D65 white point with `chad`): checked, applied exactly for colours inside sRGB (no bug found) | — |

## FilmCraft

Found in a run of FilmCraft 0.7.2 (Windows x64) over 92 real-world video files (13 Oct 2026). Every file in `filmcraft/` is written by [`make_fixtures.sh`](filmcraft/make_fixtures.sh) from ffmpeg's built-in test sources (`testsrc2`, `aevalsrc`); no camera footage, no personal data.

| File | Reproduces | Report |
|---|---|---|
| `filmcraft/fps30_ms_timestamps.mp4`, `fps60_ms_timestamps.mp4` | frame times rounded to whole milliseconds in a 90 kHz track are read as 30.303 / 58.824 fps; New Sequence From Clip then drops frames | [storytold/filmcraft#1700](https://github.com/storytold/filmcraft/issues/1700) |
| `filmcraft/surround51_ac3.mp4`, `surround51_eac3.mp4`, `surround51side_aac_pce.mp4` (controls: `surround51_ac3.mov`, `surround51_ac3.mkv`) | 5.1 in MP4 read as stereo: centre, LFE and surrounds silent | [storytold/filmcraft#1701](https://github.com/storytold/filmcraft/issues/1701) |
| `filmcraft/av1_in_mp4.mp4`, `h264_in_mkv.mkv` | empty pixel format in Media File Properties | [storytold/filmcraft#1702](https://github.com/storytold/filmcraft/issues/1702) |
| `filmcraft/scc_tight.srt`, `scc_timing.srt`, `de_test.srt` (+ `scc_tight_filmcraft-0.7.2.scc`, the 0.7.2 output) | SCC/MCC export: a caption that follows the previous one closely pops on late; German text through all caption formats | [storytold/filmcraft#1791](https://github.com/storytold/filmcraft/issues/1791) |
| `filmcraft/edl/clipA.mov`, `clipB.mov`, `seq25.edl` (written by [`edl/make_edl_fixture.sh`](filmcraft/edl/make_edl_fixture.sh)) | FilmCraft EDL of a 25 fps sequence re-imports at 24 fps | [storytold/filmcraft#1792](https://github.com/storytold/filmcraft/issues/1792) |

## WordCraft

Found in a run of WordCraft 0.6.1 (Windows x64) over 499 real-world Word documents, compared with Word for Microsoft 365 (14 Oct 2026); re-checked on 0.7.0. Every file in `wordcraft/` is written by [`make_fixtures_wordcraft.py`](wordcraft/make_fixtures_wordcraft.py) with Python's standard library only: minimal hand-written OOXML, no template, nothing created or saved by Word. No real-world content, no personal data.

| File | Reproduces | Report |
|---|---|---|
| `wordcraft/nested_fields.docx` | a field nested in another field's code (`IF { REF }`, `= { REF }`) is replaced by its cached result on save | [storytold/wordcraft#1671](https://github.com/storytold/wordcraft/issues/1671) |
| `wordcraft/date_time_fields.docx` | unlocked `DATE`/`TIME` fields keep their stored result in text and PDF output | [storytold/wordcraft#1672](https://github.com/storytold/wordcraft/issues/1672) |
| `wordcraft/vml_group_textbox_control.docx`, `vml_group_textbox_overflow.docx` | the second text box of a VML group is not drawn and is lost on save | [storytold/wordcraft#1643](https://github.com/storytold/wordcraft/issues/1643) (comment) |
| `wordcraft/legacy_form_fields.docx` | legacy form fields (`FORMTEXT`, `FORMCHECKBOX`, `FORMDROPDOWN`) lose their `w:ffData` on save | [storytold/wordcraft#1174](https://github.com/storytold/wordcraft/issues/1174) (comment) |

## EffectCraft

Found while testing EffectCraft 0.9.2 (Windows x64) with real-world phone and camera clips (14 Oct 2026). The files are written by [`make_ms_timescale_fixtures.sh`](effectcraft/make_ms_timescale_fixtures.sh) from ffmpeg's built-in test source (`testsrc2`); no camera footage, no personal data.

| File | Reproduces | Report |
|---|---|---|
| `effectcraft/ec_fps30_ms_timescale.mp4`, `ec_fps60_ms_timescale.mp4` | frame times rounded to whole milliseconds are read as 30.303 / 58.824 fps; new comps and renders run at that rate | [storytold/effectcraft#1442](https://github.com/storytold/effectcraft/issues/1442) |

## DeckCraft

Found in a run of DeckCraft 0.7.0 (Windows x64) over 12 real-world PowerPoint decks, with every saved deck re-opened in PowerPoint for Microsoft 365 (15 Oct 2026); [storytold/deckcraft#781](https://github.com/storytold/deckcraft/issues/781) has the overview. Every deck in `deckcraft/` is written by [`make_fixtures_deckcraft.py`](deckcraft/make_fixtures_deckcraft.py) (with [`ooxml_deck.py`](deckcraft/ooxml_deck.py)) using Python's standard library only: hand-written PresentationML, no template, nothing created or saved by PowerPoint; the embedded workbook is hand-written SpreadsheetML and the preview a PNG drawn in code. No real-world content, no personal data.

| File | Reproduces | Report |
|---|---|---|
| `deckcraft/dc_empty_line_height.pptx` (+ `dc_empty_line_height_deckcraft-0.7.0.png`, the 0.7.0 render) | an empty line inside a paragraph takes the first run's size instead of its own `a:br`/`a:endParaRPr` size | [storytold/deckcraft#780](https://github.com/storytold/deckcraft/issues/780) |
| `deckcraft/dc_ole_embedded_xlsx.pptx` | an embedded Excel worksheet (`p:oleObj`, `package` part) is saved as a plain picture | [storytold/deckcraft#203](https://github.com/storytold/deckcraft/issues/203) (re-test after 0.7.0) |
