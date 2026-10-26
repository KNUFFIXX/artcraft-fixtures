#!/usr/bin/env python3
"""Synthetic workbook for the GridCraft 0.12 sheet-element cap (stdlib only).

One sheet, a 5-column table "Data" starting at A3 with ROWS data rows of integers,
a header row, and three formulas in row 1 with cached values:
  A1 = SUBTOTAL(109,Data[Amount])   (structured reference)
  B1 = SUM(A4:A<last>)              (plain range)
  C1 = COUNTA(E4:E<last>)           (last column, last rows)
Every data cell is <c><v/></c> = 2 XML elements, so ROWS*5*2 elements sit in rows.
Usage: make_gc_xml_node_cap.py <out.xlsx> [rows]   (default 110000 -> 1.1 M elements)
"""
import sys, zipfile

out = sys.argv[1]
rows = int(sys.argv[2]) if len(sys.argv) > 2 else 110000
first, last = 4, 3 + rows
cols = ["Amount", "B", "C", "D", "E"]
letters = "ABCDE"
amount_sum = sum(i % 97 for i in range(rows))

ct = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>"""
rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
wb = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Big" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="191029"/></workbook>"""
wbrels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>"""
styles = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs></styleSheet>"""
sheetrels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" Target="../tables/table1.xml"/></Relationships>"""
tcols = "".join(f'<tableColumn id="{i+1}" name="{n}"/>' for i, n in enumerate(cols))
table = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="Data" displayName="Data" ref="A3:E{last}" totalsRowShown="0"><autoFilter ref="A3:E{last}"/><tableColumns count="5">{tcols}</tableColumns><tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>"""

def sheet():
    yield f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><dimension ref="A1:E{last}"/><sheetData>'
    yield (f'<row r="1"><c r="A1"><f>SUBTOTAL(109,Data[Amount])</f><v>{amount_sum}</v></c>'
           f'<c r="B1"><f>SUM(A{first}:A{last})</f><v>{amount_sum}</v></c>'
           f'<c r="C1"><f>COUNTA(E{first}:E{last})</f><v>{rows}</v></c></row>')
    yield '<row r="3">' + "".join(f'<c r="{letters[i]}3" t="inlineStr"><is><t>{n}</t></is></c>' for i, n in enumerate(cols)) + '</row>'
    for k in range(rows):
        r = first + k
        yield (f'<row r="{r}"><c r="A{r}"><v>{k % 97}</v></c><c r="B{r}"><v>{k % 7}</v></c>'
               f'<c r="C{r}"><v>{k % 11}</v></c><c r="D{r}"><v>{k % 13}</v></c><c r="E{r}"><v>1</v></c></row>')
    yield '</sheetData><tableParts count="1"><tablePart r:id="rId1"/></tableParts></worksheet>'

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct)
    z.writestr("_rels/.rels", rels)
    z.writestr("xl/workbook.xml", wb)
    z.writestr("xl/_rels/workbook.xml.rels", wbrels)
    z.writestr("xl/styles.xml", styles)
    z.writestr("xl/worksheets/sheet1.xml", "".join(sheet()))
    z.writestr("xl/worksheets/_rels/sheet1.xml.rels", sheetrels)
    z.writestr("xl/tables/table1.xml", table)
print(f"{out}: rows={rows} cells_in_rows={rows*5} elements_in_rows~{rows*10} expected A1=B1={amount_sum} C1={rows}")
