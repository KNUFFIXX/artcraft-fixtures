#!/usr/bin/env python3
"""make_gc_scoreboard_fixtures.py (THV-AC03, 15.10.2026) - GridCraft fixtures from the corpus scoreboard; Python 3 standard
library only (zipfile): minimal hand-written SpreadsheetML packages, no template, nothing created or saved by Excel. All content
is synthetic. Expected values are the ones Excel for Microsoft 365 (de-DE) computes, measured through COM, and are written into
each workbook next to the test cells (EXPECTED dict below; None = not measured yet).

  gc_text_cr.xlsx            cell text with a carriage return: CR LF (Windows line end, as text pasted from other programs
                             carries it) and a lone CR, stored the way Excel stores them (escaped in the shared strings);
                             LF only as the control
  gc_cell_info_de.xlsx       CELL() with German info types as a German Excel 365 stores them in the file ("adresse", "zeile",
                             "spalte", "dateiname": the info type stays in the language it was typed in), English ones as control
  gc_formula_whitespace.xlsx formulas with line breaks and spaces as Excel stores them when they are typed with Alt+Enter and
                             indentation (multi-line IF/LET/SUM); the formula text should survive a save unchanged
  gc_spill_single.xlsx       dynamic-array formulas (cm, as Excel 365 writes them) whose current result is a single value, and
                             references to them with the spill operator (ANCHORARRAY / C1#); one spilling formula as control
  gc_sumproduct_if_da.xlsx   SUMPRODUCT(IF(ISERROR(range),0,range),weights) entered as a dynamic-array formula (cm, as Excel 365
                             stores it): without the dynamic-array flag Excel evaluates the IF with implicit intersection
  gc_text_codes_de.xlsx      TEXT() with German format codes as a German Excel 365 stores them (TT.MM.JJJJ, TTTT, MMMM,
                             #.##0,00), with the values a de-DE Excel caches
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
EXPECTED = {  # measured 15 Oct 2026: Excel for Microsoft 365 16.0.20601, de-DE, via COM, full recalculation
    'gc_text_cr.xlsx': {'B1': 14, 'B2': 13, 'B3': 13, 'C1': 13, 'C2': 13, 'C3': 10},
    'gc_cell_info_de.xlsx': {'B1': '$A$1', 'B2': 3, 'B3': 3, 'B4': 1234.5, 'B5': True, 'B6': 'Info', 'B7': '$A$1', 'B8': 'Info'},
    'gc_text_codes_de.xlsx': {'B1': '16.10.2023', 'B2': '2023-10-16', 'B3': 'Montag', 'B4': 'Oktober 2023', 'B5': '1.234,50',
                              'B6': '1234,5', 'B7': 'yyyy-00-dd'},
    'gc_formula_whitespace.xlsx': {'B1': 'positive', 'B2': 3, 'B3': 3, 'B4': 5, 'B5': 3},
    'gc_spill_single.xlsx': {'E1': 1, 'E2': 5, 'E3': 1, 'E5': 1, 'E9': 2},
    'gc_sumproduct_if_da.xlsx': {'A3': 210, 'A5': 300, 'A7': 7},
}
DA_META = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><metadata xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
           'xmlns:xda="http://schemas.microsoft.com/office/spreadsheetml/2017/dynamicarray"><metadataTypes count="1"><metadataType name="XLDAPR" '
           'minSupportedVersion="120000" copy="1" pasteAll="1" pasteValues="1" merge="1" splitFirst="1" rowColShift="1" clearFormats="1" '
           'clearComments="1" assign="1" coerce="1" cellMeta="1"/></metadataTypes><futureMetadata name="XLDAPR" count="1"><bk><extLst>'
           '<ext uri="{bdbb8cdc-fa1e-496e-a857-3c3f30c029c3}"><xda:dynamicArrayProperties fDynamic="1" fCollapsed="0"/></ext></extLst></bk>'
           '</futureMetadata><cellMetadata count="1"><bk><rc t="1" v="0"/></bk></cellMetadata></metadata>')
SPILL_REFS = [('E1', 'ROWS(_xlfn.ANCHORARRAY(C1))'), ('E2', 'SUM(_xlfn.ANCHORARRAY(C1))'), ('E3', 'ROWS(_xlfn.ANCHORARRAY(C3))'),
              ('E5', 'COUNT(_xlfn.ANCHORARRAY(C5))'), ('E9', 'ROWS(_xlfn.ANCHORARRAY(C9))')]
WS_CASES = [  # (cell, formula text as Excel stores it, cached value)
    ('B1', 'IF(A1>0,\n  "positive",\n  "not positive")', 'positive'),
    ('B2', '_xlfn.LET(\n  _xlpm.x, A1,\n  _xlpm.y, A2,\n  _xlpm.x + _xlpm.y\n)', 3),
    ('B3', 'SUM(\n  A1,\n  A2\n)', 3),
    ('B4', 'A1 + A2 * 2', 5),
    ('B5', 'SUM( A1:A2 )', 3),
]
CELL_CASES = [  # (cell, formula as stored by a de-DE Excel 365)
    ('B1', 'CELL("adresse",A1)'),
    ('B2', 'CELL("zeile",A3)'),
    ('B3', 'CELL("spalte",C1)'),
    ('B4', 'CELL("inhalt",A2)'),
    ('B5', 'ISNUMBER(FIND("]",CELL("dateiname",A1)))'),
    ('B6', 'MID(CELL("dateiname",A1),FIND("]",CELL("dateiname",A1))+1,31)'),
    ('B7', 'CELL("address",A1)'),
    ('B8', 'MID(CELL("filename",A1),FIND("]",CELL("filename",A1))+1,31)'),
]
TEXT_CASES = [
    ('B1', 'TEXT(A1,"TT.MM.JJJJ")'),
    ('B2', 'TEXT(A1,"JJJJ-MM-TT")'),
    ('B3', 'TEXT(A1,"TTTT")'),
    ('B4', 'TEXT(A1,"MMMM JJJJ")'),
    ('B5', 'TEXT(A2,"#.##0,00")'),
    ('B6', 'TEXT(A2,"0,0")'),
    ('B7', 'TEXT(A1,"yyyy-mm-dd")'),
]


def esc_x(s):
    """XML text with Excel's _xHHHH_ escape for control characters (CR -> _x000D_), as Excel writes shared strings"""
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '\r' or (o < 0x20 and ch not in '\n\t'):
            out.append('_x%04X_' % o)
        else:
            out.append(escape(ch))
    return ''.join(out)


def package(path, sheets, shared, extra_parts=None, app='make_gc_scoreboard_fixtures.py', date_style=False):
    """sheets: [(name, sheet_xml_body)], shared: list of shared strings (already escaped XML text)"""
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
          '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>',
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>']
    for i in range(len(sheets)):
        ct.append('<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % (i + 1))
    for name, ctype, _ in (extra_parts or []):
        ct.append('<Override PartName="/%s" ContentType="%s"/>' % (name, ctype))
    ct.append('</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    wbrels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
    for i in range(len(sheets)):
        wbrels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1))
    n = len(sheets)
    wbrels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % (n + 1))
    wbrels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>' % (n + 2))
    for k, (name, ctype, _) in enumerate(extra_parts or []):
        if name == 'xl/metadata.xml':
            wbrels.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sheetMetadata" Target="metadata.xml"/>' % (n + 3 + k))
    wbrels.append('</Relationships>')
    wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="%s" xmlns:r="%s"><sheets>' % (NS, NS_R)]
    for i, (name, _) in enumerate(sheets):
        wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name, {'"': '&quot;'}), i + 1, i + 1))
    wb.append('</sheets><calcPr calcId="191029"/></workbook>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="%s">'
              '<fonts count="1"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1"/></xf>'
              '<xf numFmtId="14" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>'
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>') % NS
    sst = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="%s" count="%d" uniqueCount="%d">' % (NS, len(shared), len(shared))]
    for s in shared:
        sst.append('<si><t xml:space="preserve">%s</t></si>' % s)
    sst.append('</sst>')
    appx = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>%s</Application></Properties>') % escape(app)
    z = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml', ''.join(ct))
    z.writestr('_rels/.rels', rels)
    z.writestr('docProps/app.xml', appx)
    z.writestr('xl/workbook.xml', ''.join(wb))
    z.writestr('xl/_rels/workbook.xml.rels', ''.join(wbrels))
    z.writestr('xl/styles.xml', styles)
    z.writestr('xl/sharedStrings.xml', ''.join(sst))
    for i, (_, body) in enumerate(sheets):
        z.writestr('xl/worksheets/sheet%d.xml' % (i + 1),
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="%s" xmlns:r="%s">%s</worksheet>' % (NS, NS_R, body))
    for name, _, data in (extra_parts or []):
        z.writestr(name, data)
    z.close()


def make_text_cr(path, exp):
    texts = ['Line 1\r\nLine 2', 'Part A\rPart B', 'Item 3\nItem 4']
    shared = [esc_x(t) for t in texts]
    note = ('Column A: text with CR LF (A1), a lone CR (A2) and LF only (A3), stored as Excel stores them (CR escaped in the shared strings). '
            'B = LEN(A), C = CODE of the 7th character (the first line-break character). Expected in Excel 365, also after a GridCraft save: ')
    if exp:
        note += 'B1=%s B2=%s B3=%s C1=%s C2=%s C3=%s' % tuple(exp[k] for k in ('B1', 'B2', 'B3', 'C1', 'C2', 'C3'))
    else:
        note += '(not measured yet)'
    shared.append(escape(note))
    rows = []
    cached = exp or {}
    for i in range(3):
        r = i + 1
        b = cached.get('B%d' % r)
        c = cached.get('C%d' % r)
        rows.append('<row r="%d"><c r="A%d" s="1" t="s"><v>%d</v></c>'
                    '<c r="B%d"><f>LEN(A%d)</f>%s</c>'
                    '<c r="C%d"><f>CODE(MID(A%d,7,1))</f>%s</c></row>'
                    % (r, r, i, r, r, ('<v>%s</v>' % b) if b is not None else '', r, r, ('<v>%s</v>' % c) if c is not None else ''))
    rows.append('<row r="5"><c r="A5" t="s"><v>3</v></c></row>')
    body = '<sheetData>%s</sheetData>' % ''.join(rows)
    package(path, [('Text', body)], shared)


def xml_value(v):
    """cached value as Excel stores it: (t attribute, v text)"""
    if isinstance(v, bool):
        return ' t="b"', '1' if v else '0'
    if isinstance(v, (int, float)):
        return '', repr(float(v)) if not float(v).is_integer() else str(int(v))
    if isinstance(v, str) and v.startswith('#'):
        return ' t="e"', escape(v)
    return ' t="str"', escape(str(v))


def make_cases(path, sheet, cases, exp, intro):
    """A1 date 16.10.2023 (a Monday), A2 1234.5, A3 7, C1 3; test formulas in column B with the de-DE Excel results cached"""
    shared = [escape(intro)]
    if exp:
        shared.append(escape('Excel 365 de-DE, measured via COM: ' + ' | '.join('%s=%s' % (c, exp[c]) for c, _ in cases)))
    cells = {}
    for c, f in cases:
        if exp and exp.get(c) is not None:
            ta, vv = xml_value(exp[c])
            cells[c] = '<c r="%s"%s><f>%s</f><v>%s</v></c>' % (c, ta, escape(f), vv)
        else:
            cells[c] = '<c r="%s"><f>%s</f></c>' % (c, escape(f))
    rows = []
    for r in range(1, len(cases) + 1):
        cs = {1: '<c r="A1" s="2"><v>45215</v></c>', 2: '<c r="A2"><v>1234.5</v></c>', 3: '<c r="A3"><v>7</v></c>'}.get(r, '')
        cs += cells.get('B%d' % r, '')
        if r == 1:
            cs += '<c r="C1"><v>3</v></c><c r="D1" t="s"><v>0</v></c>'
        if r == 2 and exp:
            cs += '<c r="D2" t="s"><v>1</v></c>'
        rows.append('<row r="%d">%s</row>' % (r, cs))
    package(path, [(sheet, '<sheetData>%s</sheetData>' % ''.join(rows))], shared, date_style=True)


def make_ws(path, exp):
    shared = [escape('Formulas typed in Excel with line breaks (Alt+Enter) and spaces; Excel stores and shows them exactly like this. '
                     'Expected after a GridCraft save: the same formula text (line breaks and spaces kept) and the same values.')]
    if exp:
        shared.append(escape('Excel 365: ' + ' | '.join('%s=%s' % (c, exp[c]) for c, _, _ in WS_CASES)))
    rows = []
    for i, (c, f, v) in enumerate(WS_CASES, start=1):
        cs = {1: '<c r="A1"><v>1</v></c>', 2: '<c r="A2"><v>2</v></c>'}.get(i, '')
        ta, vv = xml_value(v)
        cs += '<c r="%s"%s><f>%s</f><v>%s</v></c>' % (c, ta, escape(f), vv)
        if i == 1:
            cs += '<c r="D1" t="s"><v>0</v></c>'
        if i == 2 and exp:
            cs += '<c r="D2" t="s"><v>1</v></c>'
        rows.append('<row r="%d">%s</row>' % (i, cs))
    package(path, [('Formulas', '<sheetData>%s</sheetData>' % ''.join(rows))], shared)


def make_spill_single(path, exp):
    """A1:A5 = 1..5; C1 =FILTER(A1:A5,A1:A5>4) (one value), C3 =SORT(FILTER(A1:A5,A1:A5=3)) (one value),
    C5 =UNIQUE(B1:B5) over five equal numbers (one value), C9 =FILTER(A1:A5,A1:A5>3) (spills C9:C10, control);
    E = references with the spill operator; expected values measured in Excel 365"""
    shared = [escape('C1, C3 and C5 are dynamic-array formulas (as Excel 365 stores them) that currently return one value; '
                     'C9 spills two values. Column E refers to them with the spill operator (C1# etc.). Expected: the same values '
                     'as Excel (a one-value result is still a 1 x 1 spill range): ') ]
    if exp:
        shared[0] += escape(' | '.join('%s=%s' % (c, exp[c]) for c, _ in SPILL_REFS))
    cells = {}
    da = [('C1', '_xlfn._xlws.FILTER(A1:A5,A1:A5&gt;4)', 'C1', 5), ('C3', '_xlfn._xlws.SORT(_xlfn._xlws.FILTER(A1:A5,A1:A5=3))', 'C3', 3),
          ('C5', '_xlfn.UNIQUE(B1:B5)', 'C5', 7), ('C9', '_xlfn._xlws.FILTER(A1:A5,A1:A5&gt;3)', 'C9:C10', 4)]
    for c, f, ref, v in da:
        cells[c] = '<c r="%s" cm="1"><f t="array" ref="%s">%s</f><v>%s</v></c>' % (c, ref, f, v)
    cells['C10'] = '<c r="C10"><v>5</v></c>'
    for c, f in SPILL_REFS:
        if exp and exp.get(c) is not None:
            ta, vv = xml_value(exp[c])
            cells[c] = '<c r="%s"%s><f>%s</f><v>%s</v></c>' % (c, ta, escape(f), vv)
        else:
            cells[c] = '<c r="%s"><f>%s</f></c>' % (c, escape(f))
    rows = []
    for r in range(1, 11):
        cs = ''
        if r <= 5:
            cs += '<c r="A%d"><v>%d</v></c><c r="B%d"><v>7</v></c>' % (r, r, r)
        for col in ('C', 'E'):
            cs += cells.get('%s%d' % (col, r), '')
        if r == 1:
            cs += '<c r="G1" t="s"><v>0</v></c>'
        rows.append('<row r="%d">%s</row>' % (r, cs))
    package(path, [('Spill', '<sheetData>%s</sheetData>' % ''.join(rows))], shared,
            extra_parts=[('xl/metadata.xml', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheetMetadata+xml', DA_META)])


def make_sumproduct_if(path, exp):
    """L3:O3 = 1, 2, =1/0, 4; L9:O9 = 10, 20, 30, 40. A3 (dynamic-array formula) =SUMPRODUCT(IF(ISERROR(L3:O3),0,L3:O3),L$9:O$9);
    A5 (control, plain formula) =SUMPRODUCT(L5:O5,L$9:O$9) with L5:O5 = 1..4; A7 (dynamic) =SUM(IF(L5:O5>2,L5:O5))"""
    note = ('A3 and A7 were entered in Excel 365 (dynamic-array formulas, cm + t=array as Excel stores them); A5 is a plain control. '
            'Expected after a GridCraft save, recalculated in Excel 365: ')
    note += ('A3=%s A5=%s A7=%s' % (exp['A3'], exp['A5'], exp['A7'])) if exp else '(not measured yet)'
    shared = [escape(note)]
    def v(c, d):
        return ('<v>%s</v>' % (exp[c] if exp and exp.get(c) is not None else d)) if True else ''
    rows = [
        '<row r="1"><c r="C1" t="s"><v>0</v></c></row>',
        '<row r="3"><c r="A3" cm="1"><f t="array" ref="A3">SUMPRODUCT(IF(ISERROR(L3:O3),0,L3:O3),L$9:O$9)</f>%s</c>'
        '<c r="L3"><v>1</v></c><c r="M3"><v>2</v></c><c r="N3" t="e"><f>1/0</f><v>#DIV/0!</v></c><c r="O3"><v>4</v></c></row>' % v('A3', 210),
        '<row r="5"><c r="A5"><f>SUMPRODUCT(L5:O5,L$9:O$9)</f>%s</c><c r="L5"><v>1</v></c><c r="M5"><v>2</v></c><c r="N5"><v>3</v></c><c r="O5"><v>4</v></c></row>' % v('A5', 300),
        '<row r="7"><c r="A7" cm="1"><f t="array" ref="A7">SUM(IF(L5:O5&gt;2,L5:O5))</f>%s</c></row>' % v('A7', 7),
        '<row r="9"><c r="L9"><v>10</v></c><c r="M9"><v>20</v></c><c r="N9"><v>30</v></c><c r="O9"><v>40</v></c></row>',
    ]
    package(path, [('Calc', '<sheetData>%s</sheetData>' % ''.join(rows))], shared,
            extra_parts=[('xl/metadata.xml', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheetMetadata+xml', DA_META)])


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else HERE
    make_text_cr(os.path.join(out, 'gc_text_cr.xlsx'), EXPECTED['gc_text_cr.xlsx'])
    make_ws(os.path.join(out, 'gc_formula_whitespace.xlsx'), EXPECTED['gc_formula_whitespace.xlsx'])
    make_spill_single(os.path.join(out, 'gc_spill_single.xlsx'), EXPECTED['gc_spill_single.xlsx'])
    make_sumproduct_if(os.path.join(out, 'gc_sumproduct_if_da.xlsx'), EXPECTED['gc_sumproduct_if_da.xlsx'])
    make_cases(os.path.join(out, 'gc_cell_info_de.xlsx'), 'Info', CELL_CASES, EXPECTED['gc_cell_info_de.xlsx'],
               'CELL() as a German Excel 365 (de-DE) writes it into the file: the info type stays in the language it was typed in '
               '(B1:B6 German, B7:B8 English as control). Column B holds the values Excel cached. Expected: GridCraft computes the '
               'same values (check --json: 0 mismatches); B6 and B8 give the sheet name.')
    make_cases(os.path.join(out, 'gc_text_codes_de.xlsx'), 'Codes', TEXT_CASES, EXPECTED['gc_text_codes_de.xlsx'],
               'TEXT() as a German Excel 365 (de-DE) writes it into the file: the format codes stay in German (T day, J year, '
               ', decimal, . thousands). Column B holds the values Excel cached. Expected: GridCraft computes the same values '
               '(check --json: 0 mismatches). B7 shows how the same Excel reads English codes.')
    print('ok')


if __name__ == '__main__':
    main()
