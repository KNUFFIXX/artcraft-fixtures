# artcraft-fixtures

Small, contributor-original test documents behind bug reports to the [ArtCraft](https://getartcraft.com) projects (PdfCraft, GridCraft), from the testing setup of Udo Funk ([@KNUFFIXX](https://github.com/KNUFFIXX)): real-world documents are used to *find* problems, and every problem that gets reported is rebuilt here as a synthetic file.

- Every PDF in `pdfcraft/` is written by a script in the same folder: [`make_fixtures.py`](pdfcraft/make_fixtures.py), [`make_mask_fixtures.py`](pdfcraft/make_mask_fixtures.py), [`make_tounicode_name.py`](pdfcraft/make_tounicode_name.py) (Python 3 + fontTools, Pillow). Fonts and images: the standard-14 Helvetica (never embedded), subsets of DejaVu Sans (Bitstream Vera licence), hand-drawn 8×14 bitmaps and bitmaps rendered from DejaVu Sans. No real-world content, no personal data.
- Every workbook in `gridcraft/` is written by [`gridcraft/make_fixtures.py`](gridcraft/make_fixtures.py) (Python 3 + openpyxl 3.1; two files are hand-written OOXML packages). Expected values are the ones a Microsoft 365 Excel (de-DE) computes, measured through COM, and are written into each file next to the test cells. No real-world content, no personal data.
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
