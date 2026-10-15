#!/usr/bin/env python3
"""Synthetic fixtures for DeckCraft issue reports.

Every package is written from scratch with the Python standard library (zipfile): minimal hand-written
PresentationML/SpreadsheetML parts, no template, nothing created or saved by Microsoft PowerPoint or Excel.
Images are drawn here (stdlib zlib PNG writer). Usage: python3 make_fixtures_deckcraft.py [outdir]
"""
import os
import struct
import sys
import zipfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ooxml_deck import (EMU, NS, STAMP, XML, esc, para, run, slide_xml, textbox, write_deck)  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)


def png_rgb(w, h, pixel):
    """tiny PNG writer: pixel(x, y) -> (r, g, b)"""
    raw = b''.join(b'\x00' + b''.join(bytes(pixel(x, y)) for x in range(w)) for y in range(h))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


# ----------------------------------------------------------------------------------------------------------------
# 1) dc_empty_line_height.pptx - empty lines inside a paragraph carry their own size:
#    an empty line made by two breaks takes the size of the second <a:br>, an empty last line takes <a:endParaRPr>.
#    Four boxes, Arial, top-anchored, no insets; each case ends with a reference line whose top position is measured.
def cases():
    A = [para(run('A1 40pt', sz=40, font='Arial') + '<a:br><a:rPr lang="en-US" sz="4000" dirty="0"><a:latin typeface="Arial"/></a:rPr></a:br>'
              + '<a:br><a:rPr lang="en-US" sz="1000" dirty="0"><a:latin typeface="Arial"/></a:rPr></a:br>' + run('A2 40pt', sz=40, font='Arial'))]
    B = ['<a:p>%s<a:br><a:rPr lang="en-US" sz="4000" dirty="0"><a:latin typeface="Arial"/></a:rPr></a:br>'
         '<a:endParaRPr lang="en-US" sz="1000" dirty="0"><a:latin typeface="Arial"/></a:endParaRPr></a:p>' % run('B1 40pt', sz=40, font='Arial'),
         para(run('B2 40pt', sz=40, font='Arial'))]
    C = [para(run('C1 20pt', sz=20, font='Arial') + '<a:br><a:rPr lang="en-US" sz="2000" dirty="0"><a:latin typeface="Arial"/></a:rPr></a:br>'
              + '<a:br><a:rPr lang="en-US" sz="6000" dirty="0"><a:latin typeface="Arial"/></a:rPr></a:br>' + run('C2 20pt', sz=20, font='Arial'))]
    D = [para(run('D1 40pt', sz=40, font='Arial')),
         '<a:p><a:endParaRPr lang="en-US" sz="1000" dirty="0"><a:latin typeface="Arial"/></a:endParaRPr></a:p>',
         para(run('D2 40pt', sz=40, font='Arial'))]
    return A, B, C, D


def box(sid, name, x, paras):
    return textbox(sid, name, x, 60, 220, 440, paras, line='9CA3AF', body_extra='').replace(
        'lIns="91440" tIns="45720" rIns="91440" bIns="45720"', 'lIns="0" tIns="0" rIns="0" bIns="0"')


A, B, C, D = cases()
s1 = slide_xml([box(2, 'Case A', 10, A), box(3, 'Case B', 250, B), box(4, 'Case C', 490, C), box(5, 'Case D', 730, D)])
write_deck(os.path.join(OUT, 'dc_empty_line_height.pptx'), [(s1, [])])

# ----------------------------------------------------------------------------------------------------------------
# 2) dc_ole_embedded_xlsx.pptx - an embedded Excel worksheet (OLE object, progId Excel.Sheet.12) with its preview picture.
#    The embedded workbook is a minimal hand-written SpreadsheetML package (A1 = 42, A2 = 58, A3 = SUM = 100).
CT_X = (XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>')
RELS_X = (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
          '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
          '</Relationships>')
WB = (XML + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
      '<sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
WB_RELS = (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
           '</Relationships>')
SHEET = (XML + '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
         '<row r="1"><c r="A1"><v>42</v></c></row><row r="2"><c r="A2"><v>58</v></c></row>'
         '<row r="3"><c r="A3"><f>SUM(A1:A2)</f><v>100</v></c></row></sheetData></worksheet>')


def xlsx_bytes():
    import io
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, d in (('[Content_Types].xml', CT_X), ('_rels/.rels', RELS_X), ('xl/workbook.xml', WB),
                     ('xl/_rels/workbook.xml.rels', WB_RELS), ('xl/worksheets/sheet1.xml', SHEET)):
            z.writestr(zipfile.ZipInfo(n, STAMP), d, zipfile.ZIP_DEFLATED)
    return b.getvalue()


def preview_png():
    # a 3-cell "table" preview: grey grid lines on white, darker bar for the sum row
    def px(x, y):
        if x % 60 == 0 or y % 30 == 0 or x == 179 or y == 89:
            return (128, 128, 128)
        if y > 60:
            return (219, 234, 254)
        return (255, 255, 255)
    return png_rgb(180, 90, px)


X, Y, W, H = 300, 180, 360, 180
pic = ('<p:pic><p:nvPicPr><p:cNvPr id="0" name=""/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>'
       '<p:blipFill><a:blip r:embed="rId3"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
       '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
       ) % (X * EMU, Y * EMU, W * EMU, H * EMU)
ole = ('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="4" name="Object 3"/><p:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/>'
       '</p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
       '<p:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></p:xfrm>'
       '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/presentationml/2006/ole">'
       '<p:oleObj name="Worksheet" r:id="rId2" imgW="%d" imgH="%d" progId="Excel.Sheet.12"><p:embed/>%s</p:oleObj>'
       '</a:graphicData></a:graphic></p:graphicFrame>') % (X * EMU, Y * EMU, W * EMU, H * EMU, W * EMU, H * EMU, pic)
s3 = slide_xml([textbox(2, 'Title', 60, 40, 840, 60, [para(run('Embedded worksheet (A3 = SUM(A1:A2) = 100)', sz=28))]), ole])
write_deck(os.path.join(OUT, 'dc_ole_embedded_xlsx.pptx'),
           [(s3, [('rId2', 'package', '../embeddings/Microsoft_Excel_Worksheet.xlsx'), ('rId3', 'image', '../media/image1.png')])],
           media={'ppt/media/image1.png': preview_png()},
           extra_parts={'ppt/embeddings/Microsoft_Excel_Worksheet.xlsx': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', xlsx_bytes())})
print('written to', OUT)
