#!/usr/bin/env python3
"""make_gc_table_dynamic_array.py (THV-AC08, 23.10.2026) - GridCraft fixture from the corpus scoreboard; Python 3 standard
library only (zipfile): a minimal hand-written SpreadsheetML package, no template, nothing created or saved by Excel. All
content is synthetic.

  gc_table_filter_da.xlsx   a table column whose calculated formula is a dynamic-array formula (FILTER over another table with
                            a [#This Row] criterion), stored the way Excel 365 stores it: calculatedColumnFormula array="1",
                            every cell cm="1" + t="array" with a one-cell ref and the cached one-value result. Each row's
                            FILTER returns exactly one value, so Excel shows the value (no #SPILL!). Controls: the same FILTER
                            as a plain dynamic-array formula outside the table (Main!F2), and a non-dynamic calculated column
                            (COUNTIF) in the same table.
Expected values are the ones Excel for Microsoft 365 (de-DE) computes after a full recalculation, measured through COM
(EXPECTED below) and cached in the cells.
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
DATA = [('K1', 'North'), ('K2', 'South'), ('K3', 'East')]
MAIN = ['K2', 'K3', 'K1']
FILTER = '_xlfn._xlws.FILTER(T_Data[Owner],T_Data[Key]=T_Main[[#This Row],[Key]])'
COUNT = 'COUNTIF(T_Data[Key],T_Main[[#This Row],[Key]])'
EXPECTED = {'B2': 'South', 'B3': 'East', 'B4': 'North', 'C2': 1, 'C3': 1, 'C4': 1, 'F2': 'South'}
DA_META = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><metadata xmlns="%s" '
           'xmlns:xda="http://schemas.microsoft.com/office/spreadsheetml/2017/dynamicarray"><metadataTypes count="1"><metadataType name="XLDAPR" '
           'minSupportedVersion="120000" copy="1" pasteAll="1" pasteValues="1" merge="1" splitFirst="1" rowColShift="1" clearFormats="1" '
           'clearComments="1" assign="1" coerce="1" cellMeta="1"/></metadataTypes><futureMetadata name="XLDAPR" count="1"><bk><extLst>'
           '<ext uri="{bdbb8cdc-fa1e-496e-a857-3c3f30c029c3}"><xda:dynamicArrayProperties fDynamic="1" fCollapsed="0"/></ext></extLst></bk>'
           '</futureMetadata><cellMetadata count="1"><bk><rc t="1" v="0"/></bk></cellMetadata></metadata>') % NS
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'


def table_xml(tid, name, ref, cols):
    tc = ''.join('<tableColumn id="%d" name="%s"%s' % (i + 1, h, ('><calculatedColumnFormula%s>%s</calculatedColumnFormula></tableColumn>'
                 % (' array="1"' if arr else '', escape(f))) if f else '/>') for i, (h, f, arr) in enumerate(cols))
    return (XML + '<table xmlns="%s" id="%d" name="%s" displayName="%s" ref="%s" totalsRowShown="0"><autoFilter ref="%s"/>'
            '<tableColumns count="%d">%s</tableColumns><tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" '
            'showRowStripes="1" showColumnStripes="0"/></table>') % (NS, tid, name, name, ref, ref, len(cols), tc)


def sheet_xml(rows):
    return (XML + '<worksheet xmlns="%s" xmlns:r="%s"><sheetData>%s</sheetData><tableParts count="1"><tablePart r:id="rId1"/></tableParts>'
            '</worksheet>') % (NS, NS_R, ''.join('<row r="%d">%s</row>' % (r, c) for r, c in rows))


def s(ref, text):
    return '<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, escape(text))


def build(path):
    data_rows = [(1, s('A1', 'Key') + s('B1', 'Owner'))]
    for i, (k, o) in enumerate(DATA):
        data_rows.append((i + 2, s('A%d' % (i + 2), k) + s('B%d' % (i + 2), o)))
    note = ('T_Main[Owner] is a calculated column with a dynamic-array formula (FILTER over T_Data with a [#This Row] criterion), '
            'stored as Excel 365 stores it; each row returns one value. F2 is the same FILTER outside the table (control), '
            'T_Main[Count] a plain calculated column (control). Expected (Excel 365, full recalculation): '
            + ' '.join('%s=%s' % kv for kv in EXPECTED.items()))
    main_rows = [(1, s('A1', 'Key') + s('B1', 'Owner') + s('C1', 'Count') + s('E1', 'Control outside the table')
                  + s('H1', note))]
    for i, k in enumerate(MAIN):
        r = i + 2
        cells = s('A%d' % r, k)
        cells += '<c r="B%d" t="str" cm="1"><f t="array" ref="B%d">%s</f><v>%s</v></c>' % (r, r, escape(FILTER), EXPECTED['B%d' % r])
        cells += '<c r="C%d"><f>%s</f><v>%s</v></c>' % (r, escape(COUNT), EXPECTED['C%d' % r])
        if r == 2:
            cells += s('E2', 'K2') + ('<c r="F2" t="str" cm="1"><f t="array" ref="F2">%s</f><v>%s</v></c>'
                                      % (escape('_xlfn._xlws.FILTER(T_Data[Owner],T_Data[Key]=E2)'), EXPECTED['F2']))
        main_rows.append((r, cells))
    ct = (XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
          '<Override PartName="/xl/metadata.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheetMetadata+xml"/>'
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
          '<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
          '<Override PartName="/xl/tables/table2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
    rels = (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>')
    wbrels = (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
              '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
              '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
              '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
              '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sheetMetadata" Target="metadata.xml"/></Relationships>')
    wb = (XML + '<workbook xmlns="%s" xmlns:r="%s"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/><sheet name="Main" sheetId="2" r:id="rId2"/>'
          '</sheets><calcPr calcId="191029"/></workbook>') % (NS, NS_R)
    styles = (XML + '<styleSheet xmlns="%s"><fonts count="1"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>'
              '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
              '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>') % NS
    trel = (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table%d.xml"/></Relationships>')
    appx = (XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
            '<Application>make_gc_table_dynamic_array.py</Application></Properties>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct)
        z.writestr('_rels/.rels', rels)
        z.writestr('docProps/app.xml', appx)
        z.writestr('xl/workbook.xml', wb)
        z.writestr('xl/_rels/workbook.xml.rels', wbrels)
        z.writestr('xl/styles.xml', styles)
        z.writestr('xl/metadata.xml', DA_META)
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml(data_rows))
        z.writestr('xl/worksheets/sheet2.xml', sheet_xml(main_rows))
        z.writestr('xl/worksheets/_rels/sheet1.xml.rels', trel % 1)
        z.writestr('xl/worksheets/_rels/sheet2.xml.rels', trel % 2)
        z.writestr('xl/tables/table1.xml', table_xml(1, 'T_Data', 'A1:B4', [('Key', None, False), ('Owner', None, False)]))
        z.writestr('xl/tables/table2.xml', table_xml(2, 'T_Main', 'A1:C4', [('Key', None, False), ('Owner', FILTER, True), ('Count', COUNT, False)]))


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else HERE
    build(os.path.join(out, 'gc_table_filter_da.xlsx'))
    print('ok')
