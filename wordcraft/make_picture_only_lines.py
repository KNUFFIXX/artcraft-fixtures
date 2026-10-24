"""Synthetic WordCraft fixtures: paragraphs that hold only an inline picture (picture-only lines).
Standard library only (zipfile, zlib, struct); hand-written OOXML, no template, nothing created or saved by Word.
The picture is a flat grey 60x24 PNG drawn here, shown 360 x 100-140 pt. Body font Calibri 11 pt (docDefaults).
Measured in Word for Microsoft 365 (Windows 11, ExportAsFixedFormat): every picture starts exactly the paragraph's
space after (18 pt) below the previous one, i.e. a picture-only line keeps no descent under the picture,
in single, 1.15 (auto) and at-least spacing and with a 20 pt paragraph mark; with text on the picture's line
the text's descent stays (about 2.95 pt for Calibri 11 pt).
Exact and at-least spacing probes (*_exact*, *_atleast160*): no paragraph before, so the first picture line starts
at the top margin (70.85 pt) and every line is exactly / at least its spacing value tall; the measurement is where
the picture's bottom sits above the line's bottom edge.
Usage: python3 make_picture_only_lines.py [output folder]"""
import zipfile, zlib, struct, sys

def png(w, h, grey=128):
    raw = b''.join(b'\x00' + bytes([grey]) * w for _ in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 0, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

EMU = 12700
def pic(i, w_pt, h_pt):
    cx, cy = int(w_pt * EMU), int(h_pt * EMU)
    return ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="%d" cy="%d"/>'
            '<wp:docPr id="%d" name="Picture %d"/><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="%d" name="block.png"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImg"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>'
            % (cx, cy, i, i, i, cx, cy))

PPR = '<w:pPr><w:spacing w:after="360" w:line="240" w:lineRule="auto"/></w:pPr>'
def para(inner, ppr=PPR): return '<w:p>' + ppr + inner + '</w:p>'
def text(t): return '<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % t

def build(path, n=4, h_pt=140, ppr=None, mark_sz=None, with_text=False, lead=True):
    # lead=False: the first picture line starts at the top margin (absolute positions measurable)
    body = para(text('Paragraph before the pictures.'), '<w:pPr><w:spacing w:after="360"/></w:pPr>') if lead else ''
    ppr = ppr or PPR
    def line(i):
        r = pic(i + 1, 360, h_pt)
        if mark_sz:
            r = r.replace('<w:r><w:drawing>', '<w:r><w:rPr><w:sz w:val="%d"/></w:rPr><w:drawing>' % mark_sz)
        if with_text:
            r += text(' x')
        return para(r, ppr)
    body += ''.join(line(i) for i in range(n))
    body += para(text('Paragraph after the pictures.'))
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body>' + body +
           '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:rPrDefault>'
              '<w:pPrDefault><w:pPr><w:spacing w:after="200" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rIdSt" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rIdImg" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/block.png"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels)
        z.writestr('word/document.xml', doc); z.writestr('word/styles.xml', styles)
        z.writestr('word/_rels/document.xml.rels', drels); z.writestr('word/media/block.png', png(60, 24))

VARIANTS = {
    'picture_only_lines_single.docx': dict(n=4, h_pt=140),
    'picture_only_lines_auto115.docx': dict(n=3, h_pt=100, ppr='<w:pPr><w:spacing w:after="360" w:line="276" w:lineRule="auto"/></w:pPr>'),
    'picture_only_lines_atleast.docx': dict(n=3, h_pt=100, ppr='<w:pPr><w:spacing w:after="360" w:line="240" w:lineRule="atLeast"/></w:pPr>'),
    'picture_only_lines_mark20.docx': dict(n=3, h_pt=100, ppr='<w:pPr><w:spacing w:after="360" w:line="240" w:lineRule="auto"/><w:rPr><w:sz w:val="40"/></w:rPr></w:pPr>', mark_sz=40),
    'picture_lines_with_text.docx': dict(n=3, h_pt=100, with_text=True),
    'picture_only_lines_exact160.docx': dict(n=3, h_pt=100, lead=False, ppr='<w:pPr><w:spacing w:after="360" w:line="3200" w:lineRule="exact"/></w:pPr>'),
    'picture_only_lines_exact12.docx': dict(n=3, h_pt=100, lead=False, ppr='<w:pPr><w:spacing w:after="360" w:line="240" w:lineRule="exact"/></w:pPr>'),
    'picture_only_lines_atleast160.docx': dict(n=3, h_pt=100, lead=False, ppr='<w:pPr><w:spacing w:after="360" w:line="3200" w:lineRule="atLeast"/></w:pPr>'),
    'picture_lines_with_text_exact160.docx': dict(n=3, h_pt=100, lead=False, with_text=True, ppr='<w:pPr><w:spacing w:after="360" w:line="3200" w:lineRule="exact"/></w:pPr>'),
}

if __name__ == '__main__':
    import os
    out = sys.argv[1] if len(sys.argv) > 1 else '.'
    only = sys.argv[2:]  # optional: build only these names
    for name, kw in VARIANTS.items():
        if not only or name in only:
            build(os.path.join(out, name), **kw)
