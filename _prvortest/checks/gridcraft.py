#!/usr/bin/env python3
"""gridcraft.py (DRACO-AC05, 15.10.2026) - GridCraft fixture checks for the PR pre-test.
Linux port of the GridCraft part of Scheduled_Scripts/ac-nachtest/ac_nachtest.py (same steps), plus the fixtures posted on
15.10.2026 (#1488 #1489 #1490 #1491, comments #889 and #64). Expected values = Excel for Microsoft 365 de-DE via COM, as written
into the fixtures (make_fixtures.py, make_gc_scoreboard_fixtures.py); German fixtures (*_de.xlsx) are read with
`--region de-DE` when the CLI has that option (27.10.2026). Call:
  python3 -I gridcraft.py <gridcraft-cli> <artcraft-fixtures/gridcraft> <out.json> [--work DIR]
Values come from `gridcraft-cli cat --range --csv` (engine values); saves from `gridcraft-cli run --in --out`. The saved .xlsx
files stay in the work folder for the Excel cross-check on the PC (a FIXED for a save issue needs it before posting).
known_main = GridCraft 0.7.0 (Windows x64 release, AC Nachtest / scoreboard 15.10.2026) or the issue report."""
import csv
import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('gridcraft', sys.argv)
W = ck.work


def gc(args, tag, timeout=180):
    return C.run([ck.cli] + args, timeout=timeout, cwd=W, log_prefix=os.path.join(W, tag))


_REGION = None


def region_args(path):
    """['--region', 'de-DE'] for the German fixtures (*_de.xlsx) when this gridcraft-cli has the option (PR #1886, 27.10.2026):
    their expected values are Excel de-DE, so the CLI reads text the same way. Older CLIs have no flag (en-US only)."""
    global _REGION
    if _REGION is None:
        rc, so, se = C.run([ck.cli, '--help'], timeout=30, cwd=W, log_prefix=os.path.join(W, 'help'))
        _REGION = '--region' in (so + se)
    return ['--region', 'de-DE'] if _REGION and os.path.basename(path).endswith('_de.xlsx') else []


def region_note(name):
    return ' (with `--region de-DE`)' if region_args(name) else ''


def cat(path, rng, tag):
    rc, so, se = gc(['cat', path, '--range', rng, '--csv'] + region_args(path), tag)
    if rc != 0 and not so.strip():
        raise RuntimeError('cat failed (rc=%s): %s' % (rc, se.strip()[-300:]))
    return [row for row in csv.reader(io.StringIO(so))]


def cells(path, rng, tag):
    """{'B1': 'text', ...} for a range like B1:C5 (rows/cols as cat prints them)"""
    m = re.match(r'([A-Z]+)(\d+):([A-Z]+)(\d+)$', rng)
    c0, r0, c1, r1 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
    cols = [chr(x) for x in range(ord(c0), ord(c1) + 1)]
    rows = cat(path, rng, tag)
    out = {}
    for i, r in enumerate(range(r0, r1 + 1)):
        for j, c in enumerate(cols):
            out['%s%d' % (c, r)] = rows[i][j] if i < len(rows) and j < len(rows[i]) else ''
    return out


def same(got, exp):
    if isinstance(exp, bool):
        return str(got).strip().upper() in (('TRUE', 'WAHR', '1') if exp else ('FALSE', 'FALSCH', '0'))
    if isinstance(exp, (int, float)):
        try:
            return abs(float(str(got).replace(',', '.') if re.match(r'^-?\d+,\d+$', str(got)) else got) - exp) < 1e-6
        except ValueError:
            return False
    return str(got) == str(exp)


def compare(path, exp, tag, rng):
    got = cells(path, rng, tag)
    bad = [k for k in exp if not same(got.get(k, ''), exp[k])]
    return got, bad


def save(name, tag):
    out = os.path.join(W, 'rt_' + name)
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = gc(['run', '--in', ck.fx(name), '--out', out, '--quiet'], tag)
    if not os.path.exists(out):
        raise RuntimeError('save wrote nothing (rc=%s): %s' % (rc, se.strip()[-300:]))
    return out


def part(path, name):
    with zipfile.ZipFile(path) as z:
        return z.read(name).decode('utf-8', 'replace') if name in z.namelist() else ''


def values_check(name, exp, rng, known_main_bad):
    def fn():
        got, bad = compare(ck.fx(name), exp, 'v_' + name[:-5], rng)
        n = len(exp)
        v = 'FIXED' if not bad else ('NOT FIXED' if set(bad) == set(known_main_bad) else 'CHANGED')
        return ('%d/%d cells like Excel' % (n - len(bad), n)) + ('' if not bad else '; differs: ' + ', '.join('%s=%s' % (k, got.get(k)) for k in bad)) \
            + region_note(name), v, {'got': got, 'bad': bad}
    return fn


# ================= reported 12./13.10. =================
def g889():
    exp = {'B1': 107.689, 'B2': 665, 'B3': 1, 'B4': '#VALUE!', 'C1': 107.689, 'C2': 1330, 'C3': 107.689, 'C4': 0, 'C5': 1330}
    got, bad = compare(ck.fx('gc_coerce_de.xlsx'), exp, 'g889', 'B1:C5')
    v = 'FIXED' if not bad else ('NOT FIXED' if len(bad) >= 6 else 'CHANGED')
    return ('all 9 cells like Excel' if not bad else 'differs: ' + ', '.join('%s=%s' % (k, got[k]) for k in bad)) + region_note('gc_coerce_de.xlsx'), v, \
        {'got': got}


ck.check('gc_coerce_de.xlsx', 'gridcraft#889', 'text-to-number/date coercion with de-DE separators',
         'all 9 cells like Excel', '8 of 9 differ (0.7.0)', g889, aspect='values')

SORT_EXP = '_x | 1 | 10 | 2 | a c | ab | AB | a-b | ac | a-c | apfel | Apfel | Ärger | JO30-WE01-EGH | JO30-WE-1- | x_ | x01 | x-1 | Zebra'.split(' | ')


def g890():
    got = [r[0] if r else '' for r in cat(ck.fx('gc_sort_collation.xlsx'), 'C1:C19', 'g890')]
    n = sum(1 for a, b in zip(got, SORT_EXP) if a == b)
    v = 'FIXED' if got == SORT_EXP else ('NOT FIXED' if n <= 4 else 'CHANGED')
    return 'SORT %d/19 rows like Excel' % n, v, {'got': got}


ck.check('gc_sort_collation.xlsx', 'gridcraft#890', 'SORT/SORTBY with Excel collation', '19/19 rows like Excel',
         '4/19 (0.7.0)', g890, aspect='values')


def g410():
    rows = cat(ck.fx('gc_implicit_intersection.xlsx'), 'H9:L10', 'g410')
    r9 = rows[0][:5] if rows else []
    ok = [same(a, b) for a, b in zip(r9, [450, 1800, 901, 5500, 900])]
    r10_empty = len(rows) < 2 or not rows[1] or rows[1][0] in ('', None)
    v = 'FIXED' if len(ok) == 5 and all(ok) and r10_empty else ('NOT FIXED' if sum(ok) <= 2 else 'CHANGED')
    return 'row 9 = ' + ','.join(r9), v, {'rows': rows}


ck.check('gc_implicit_intersection.xlsx', 'gridcraft#410', 'implicit intersection for legacy formulas on read',
         'row 9 = 450,1800,901,5500,900, no spill', '450,200,101,5500,#SPILL! (0.7.0)', g410, aspect='values')


def g417():
    out = save('gc_legacy_to_array_small.xlsx', 'g417')
    x = part(out, 'xl/worksheets/sheet1.xml')
    arr = len(re.findall(r't="array"', x))
    m = re.search(r'<c r="H2"[^>]*>.*?<v>([^<]*)</v>', x)
    val = m.group(1) if m else ''
    v = 'FIXED' if arr == 0 and val.startswith('4.10958') else ('NOT FIXED' if arr > 0 else 'CHANGED')
    return '%d array formulas after save, H2 cache %s' % (arr, val), v, {'array': arr, 'h2': val}


ck.check('gc_legacy_to_array_small.xlsx', 'gridcraft#410/#417', 'legacy formulas stay legacy on save (no t="array")',
         '0 array formulas, H2 = 4.10958...', '25 array formulas, H2 #VALUE! (0.7.0)', g417, aspect='save')


def g985():
    out = save('gc_shared_image.xlsx', 'g985')
    with zipfile.ZipFile(out) as z:
        n = len([p for p in z.namelist() if p.startswith('xl/media/')])
    return '%d media part(s) after save' % n, 'FIXED' if n == 1 else ('NOT FIXED' if n == 4 else 'CHANGED'), {'media': n}


ck.check('gc_shared_image.xlsx', 'gridcraft#985', 'a picture shared by four sheets is written once', '1 media part',
         '4 (0.7.0)', g985, aspect='save')


def g864():
    out = save('gc_table_thisrow.xlsx', 'g864')
    with zipfile.ZipFile(out) as z:
        n = sum(len(re.findall(r'\[@', z.read(p).decode('utf-8', 'replace'))) for p in z.namelist()
                if p.startswith(('xl/worksheets/sheet', 'xl/tables/')))
    return '%d [@...] shorthands written' % n, 'FIXED' if n == 0 else 'CHANGED', {'shorthands': n}


ck.check('gc_table_thisrow.xlsx', 'gridcraft#864', 'structured references not saved as [@col] (regression control)',
         '0 shorthands', '0 (fixed by #869)', g864, role='control', aspect='save')


def g805():
    out = save('gc_normal_font_arial10.xlsx', 'g805')
    st = part(out, 'xl/styles.xml')
    f0 = re.search(r'<fonts[^>]*>\s*<font>(.*?)</font>', st, re.S)
    f0 = f0.group(1) if f0 else ''
    nm = re.search(r'<name val="([^"]*)"', f0)
    sz = re.search(r'<sz val="([^"]*)"', f0)
    nm, sz = (nm.group(1) if nm else '?'), (sz.group(1) if sz else '?')
    return 'Normal font %s %s' % (nm, sz), 'FIXED' if (nm, sz) == ('Arial', '10') else 'CHANGED', {'name': nm, 'size': sz}


ck.check('gc_normal_font_arial10.xlsx', 'gridcraft#805', 'Normal style font kept on save (regression control)',
         'Arial 10', 'Arial 10 (fixed by #823)', g805, role='control', aspect='save')


# ================= reported 15.10. =================
TEXT_CR = {'B1': 14, 'B2': 13, 'B3': 13, 'C1': 13, 'C2': 13, 'C3': 10}


def g1488_read():
    got, bad = compare(ck.fx('gc_text_cr.xlsx'), TEXT_CR, 'g1488r', 'B1:C3')
    v = 'FIXED' if not bad else 'CHANGED'
    return ('LEN/CODE like Excel' if not bad else 'differs: ' + ', '.join('%s=%s' % (k, got[k]) for k in bad)), v, {'got': got}


def g1488_save():
    out = save('gc_text_cr.xlsx', 'g1488s')
    sst = part(out, 'xl/sharedStrings.xml')
    sh = part(out, 'xl/worksheets/sheet1.xml')
    blob = sst + sh
    esc = len(re.findall(r'_x000[dD]_|&#13;|&#x[dD];', blob))
    raw = blob.count('\r')
    got, bad = compare(out, {k: TEXT_CR[k] for k in ('B1', 'B2', 'C1', 'C2')}, 'g1488s_cat', 'B1:C2')
    v = 'FIXED' if esc >= 2 and raw == 0 and not bad else ('NOT FIXED' if esc == 0 else 'CHANGED')
    return '%d escaped CR, %d raw CR in the saved file; re-read %s' % (esc, raw, 'like Excel' if not bad else 'differs: ' + ', '.join(
        '%s=%s' % (k, got[k]) for k in bad)), v, {'escaped': esc, 'raw': raw, 'reread': got}


ck.check('gc_text_cr.xlsx', 'gridcraft#1488', 'carriage return in cell text: LEN/CODE on read', 'B1=14 B2=13 B3=13 C1=13 C2=13 C3=10',
         'not measured on read (issue is the save side)', g1488_read, role='extra', aspect='values')
ck.check('gc_text_cr.xlsx', 'gridcraft#1488', 'carriage return kept on save (escaped as _x000D_)', 'CR escaped twice, re-read B1=14 B2=13',
         'raw CR written, re-read as LF (0.7.0)', g1488_save, aspect='save')

ck.check('gc_cell_info_de.xlsx', 'gridcraft#1489', 'CELL() with German info types and CELL("filename")',
         "B1=$A$1 B2=3 B3=3 B4=1234.5 B5=TRUE B6=Info B7=$A$1 B8=Info", 'German types #VALUE!, filename empty (0.7.0)',
         values_check('gc_cell_info_de.xlsx', {'B1': '$A$1', 'B2': 3, 'B3': 3, 'B4': 1234.5, 'B5': True, 'B6': 'Info', 'B7': '$A$1', 'B8': 'Info'},
                      'B1:B8', ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B8']), aspect='values')
ck.check('gc_text_codes_de.xlsx', 'gridcraft#889', 'TEXT() with German format codes (comment on #889)',
         'B1=16.10.2023 B2=2023-10-16 B3=Montag B4=Oktober 2023 B5=1.234,50 B6=1234,5 B7=yyyy-00-dd', 'English codes used (0.7.0)',
         values_check('gc_text_codes_de.xlsx', {'B1': '16.10.2023', 'B2': '2023-10-16', 'B3': 'Montag', 'B4': 'Oktober 2023', 'B5': '1.234,50',
                                                'B6': '1234,5', 'B7': 'yyyy-00-dd'}, 'B1:B7', ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']),
         aspect='values')
# THV-SYS43 28.10.2026: Excel truth measured on THV (de-DE, DateOrder=1, DateSep='.'), probe from DRACO-AC17
ck.check('gc_probe_dates_de.xlsx', 'gridcraft#889', 'German date text in YEAR/DATEVALUE/TIMEVALUE/MONTH and Text+0',
         'B1=2021 C1=44227 D1=44227 B2=45215 C2=0.604166667 D2=10', 'German date text not parsed (main without --region)',
         values_check('gc_probe_dates_de.xlsx', {'B1': 2021, 'C1': 44227, 'D1': 44227, 'B2': 45215, 'C2': 0.604166667, 'D2': 10},
                      'B1:D2', ['B1', 'C1', 'D1', 'B2', 'C2', 'D2']), aspect='values')

WS_F = {'B1': 'IF(A1>0,\n  "positive",\n  "not positive")', 'B2': '_xlfn.LET(\n  _xlpm.x, A1,\n  _xlpm.y, A2,\n  _xlpm.x + _xlpm.y\n)',
        'B3': 'SUM(\n  A1,\n  A2\n)', 'B4': 'A1 + A2 * 2', 'B5': 'SUM( A1:A2 )'}


def g1490():
    import html  # noqa: PLC0415
    out = save('gc_formula_whitespace.xlsx', 'g1490')
    x = part(out, 'xl/worksheets/sheet1.xml')
    kept = []
    found = {}
    for c, f in WS_F.items():
        m = re.search(r'<c r="%s"[^>]*>\s*<f[^>]*>(.*?)</f>' % c, x, re.S)
        g = html.unescape(m.group(1)).replace('&#10;', '\n') if m else None
        found[c] = g
        if g == f:
            kept.append(c)
    got, bad = compare(out, {'B1': 'positive', 'B2': 3, 'B3': 3, 'B4': 5, 'B5': 3}, 'g1490_cat', 'B1:B5')
    v = 'FIXED' if len(kept) == 5 and not bad else ('NOT FIXED' if len(kept) == 0 and not bad else 'CHANGED')
    return '%d/5 formula texts kept on save; values %s' % (len(kept), 'unchanged' if not bad else 'differ: ' + ','.join(bad)), v, \
        {'kept': kept, 'formulas': found}


ck.check('gc_formula_whitespace.xlsx', 'gridcraft#1490', 'line breaks and spaces inside formulas kept on save',
         '5/5 formula texts unchanged, values unchanged', '0/5 (whitespace removed, values unchanged; 0.7.0)', g1490, aspect='save')


def g1491():
    exp = {'E1': 1, 'E2': 5, 'E3': 1, 'E5': 1}
    got = cells(ck.fx('gc_spill_single.xlsx'), 'E1:E9', 'g1491')
    bad = [k for k in exp if not same(got.get(k), exp[k])]
    v = 'FIXED' if not bad else ('NOT FIXED' if len(bad) == 4 else 'CHANGED')
    return ('E1/E2/E3/E5 like Excel' if not bad else 'differs: ' + ', '.join('%s=%s' % (k, got[k]) for k in bad)), v, {'got': got}


def g1491_ctl():
    got = cells(ck.fx('gc_spill_single.xlsx'), 'E9:E9', 'g1491c')
    ok = same(got.get('E9'), 2)
    return 'E9 = %s' % got.get('E9'), 'FIXED' if ok else 'CHANGED', {'got': got}


ck.check('gc_spill_single.xlsx', 'gridcraft#1491', 'spill operator on a dynamic array that returns one value (ROWS/SUM/COUNT of C1#)',
         'E1=1 E2=5 E3=1 E5=1', '#REF! (0.7.0)', g1491, aspect='values')
ck.check('gc_spill_single.xlsx', 'gridcraft#1491', 'spill operator on a spilling formula (control)', 'E9=2', '2 (0.7.0)',
         g1491_ctl, role='control', aspect='values, control E9')


def g64():
    out = save('gc_sumproduct_if_da.xlsx', 'g64')
    x = part(out, 'xl/worksheets/sheet1.xml')
    cm = [c for c in ('A3', 'A7') if re.search(r'<c r="%s"[^>]*\bcm="\d+"' % c, x)]
    meta = bool(part(out, 'xl/metadata.xml'))
    got, bad = compare(out, {'A3': 210, 'A5': 300, 'A7': 7}, 'g64_cat', 'A3:A7')
    v = 'FIXED' if len(cm) == 2 and meta and not bad else ('NOT FIXED' if 'A3' not in cm else 'CHANGED')
    return 'dynamic-array flag (cm) kept on %d/2 cells, metadata part %s; values %s' % (
        len(cm), 'kept' if meta else 'missing', 'like Excel' if not bad else 'differ: ' + ','.join(bad)), v, {'cm': cm, 'metadata': meta}


ck.check('gc_sumproduct_if_da.xlsx', 'gridcraft#64', 'SUMPRODUCT(IF(...)) entered as dynamic array keeps cm on save (comment on #64)',
         'cm on A3 and A7, xl/metadata.xml kept', 'cm dropped on A3 (kept on A7), Excel shows #VALUE! in A3 (0.7.0)', g64, aspect='save')

ck.write({'known_main_label': 'GridCraft 0.7.0', 'known_main_source': 'GridCraft 0.7.0 Windows x64 release (AC Nachtest 15.10.2026) and the issue reports',
          'office_crosscheck': 'saved .xlsx files (rt_*.xlsx) in the work folder; open them in Excel before posting a FIXED for a save issue'})
