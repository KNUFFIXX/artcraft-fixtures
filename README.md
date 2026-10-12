# artcraft-fixtures

Small, contributor-original test documents behind bug reports to the [ArtCraft](https://getartcraft.com) projects (PdfCraft, later GridCraft), from the testing setup of Udo Funk ([@KNUFFIXX](https://github.com/KNUFFIXX)): real-world documents are used to *find* problems, and every problem that gets reported is rebuilt here as a synthetic file.

- Every PDF in `pdfcraft/` is written by [`pdfcraft/make_fixtures.py`](pdfcraft/make_fixtures.py) (Python 3 + fontTools). Fonts: the standard-14 Helvetica (never embedded), a subset of DejaVu Sans (Bitstream Vera licence), and hand-drawn 8×14 bitmaps. No real-world content, no personal data.
- Licence: MIT OR Apache-2.0, at your option (`LICENSE-MIT`, `LICENSE-APACHE`), so each file can be taken into a project's regression tests as is.
- The reports are tested and written by Claude (Anthropic) on behalf of Udo Funk, who reviews every file and report before it is published.

| File | Reproduces | Report |
|---|---|---|
| `pdfcraft/double_letters_condensed_tz.pdf` | text extraction drops adjacent identical narrow glyphs in condensed text (`Tz` ≤ 80 %) | see issue link in commit history |
| `pdfcraft/symbolic_truetype_mac_cmap_no_tounicode.pdf` | non-ASCII characters lost: symbolic TrueType, (1,0) cmap only, no `/Encoding`, no `/ToUnicode` | |
| `pdfcraft/nonsymbolic_truetype_partial_tounicode.pdf` | non-ASCII characters lost: nonsymbolic TrueType, `/ToUnicode` covers 0x20–0x7E only | |
| `pdfcraft/type3_imagemask_tr2.pdf` (+ `type3tr_compare_150.png`) | Type 3 glyphs drawn bold under text rendering mode 2 | |
| `pdfcraft/flatten_orphan_field.pdf` | `doc_flatten` keeps a field whose widget is on no page | |
