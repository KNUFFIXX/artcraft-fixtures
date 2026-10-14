#!/usr/bin/env python3
"""Synthetic fixtures for WordCraft issue reports.

Every package is written from scratch with the Python standard library (zipfile): minimal
hand-written OOXML parts, no template, nothing created or saved by Microsoft Word.
Usage: python3 make_fixtures_wordcraft.py [outdir]
"""
import os
import sys
import zipfile

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
STAMP = (2026, 10, 14, 0, 0, 0)  # fixed zip timestamps, so the output is byte-for-byte reproducible
CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')
DOCRELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
           '</Relationships>')
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<w:styles xmlns:w="%s"><w:docDefaults>'
          '<w:rPrDefault><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
          '<w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
          '<w:pPrDefault><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
          '</w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
          '</w:styles>') % W
SECT = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1417" w:right="1417" w:bottom="1134" w:left="1417" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>')
ROOT_NS = ('xmlns:w="%s" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
           'xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" '
           'xmlns:w10="urn:schemas-microsoft-com:office:word"') % W


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def t(s):
    return '<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % esc(s)


def fc(kind):
    return '<w:r><w:fldChar w:fldCharType="%s"/></w:r>' % kind


def it(s):
    return '<w:r><w:instrText xml:space="preserve">%s</w:instrText></w:r>' % esc(s)


def p(*parts, ppr=''):
    return '<w:p>%s%s</w:p>' % (('<w:pPr>%s</w:pPr>' % ppr) if ppr else '', ''.join(parts))


def save(name, body):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<w:document %s><w:body>%s%s</w:body></w:document>') % (ROOT_NS, body, SECT)
    with zipfile.ZipFile(os.path.join(OUT, name), 'w', zipfile.ZIP_DEFLATED) as z:
        for part, data in (('[Content_Types].xml', CT), ('_rels/.rels', RELS),
                           ('word/_rels/document.xml.rels', DOCRELS), ('word/styles.xml', STYLES),
                           ('word/document.xml', doc)):
            z.writestr(zipfile.ZipInfo(part, STAMP), data, zipfile.ZIP_DEFLATED)


# 1) nested fields: a field inside another field's instruction (bookmark "amount" holds 0)
bm = '<w:bookmarkStart w:id="1" w:name="amount"/>' + t('0') + '<w:bookmarkEnd w:id="1"/>'
save('nested_fields.docx',
     p(t('Amount: '), bm)
     + p(t('IF with nested REF: '), fc('begin'), it(' IF '), fc('begin'), it(' REF amount '), fc('separate'), t('0'), fc('end'),
         it(' = 0 "amount is zero" "amount is not zero" '), fc('separate'), t('amount is zero'), fc('end'))
     + p(t('Formula with nested REF: '), fc('begin'), it(' = '), fc('begin'), it(' REF amount '), fc('separate'), t('0'), fc('end'),
         it(' + 5 '), fc('separate'), t('5'), fc('end')))

# 2) DATE / TIME fields (not locked) whose cached result is an old date
save('date_time_fields.docx',
     p(t('DATE field: '), fc('begin'), it(' DATE \\@ "yyyy-MM-dd" '), fc('separate'), t('2020-01-01'), fc('end'))
     + p(t('TIME field: '), fc('begin'), it(' TIME \\@ "dddd, d MMMM yyyy" '), fc('separate'), t('Wednesday, 1 January 2020'), fc('end')))

# 3) space after of one paragraph meets space before of the next
body = ''
for name, after, before in [('A', 12, 12), ('B', 12, 0), ('C', 0, 12), ('D', 24, 12), ('E', 6, 18)]:
    body += p(t('%s1 first paragraph, space after %d pt' % (name, after)), ppr='<w:spacing w:after="%d"/>' % (after * 20))
    body += p(t('%s2 second paragraph, space before %d pt' % (name, before)), ppr='<w:spacing w:before="%d" w:after="0"/>' % (before * 20))
    body += p(t('%s3 spacer' % name))
save('spacing_after_before.docx', body)

# 4) a DOCX package saved under a .doc name (common when files are renamed or exported by other tools)
save('docx_named_as.doc', p(t('This is an OOXML package with a .doc file name.')))

# 5) RTF with A4 paper size
rtf = (r'{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times New Roman;}}' '\r\n'
       r'\paperw11906\paperh16838\margl1417\margr1417\margt1417\margb1134' '\r\n'
       r'\pard\plain\f0\fs24 A4 page, 210 x 297 mm (\\paperw11906 \\paperh16838).\par' '\r\n}')
with open(os.path.join(OUT, 'rtf_a4_paper.rtf'), 'w', newline='') as f:
    f.write(rtf)

# 6) two text boxes inside an inline VML group (overflow: box B shorter than its text; control: both tall enough)
SHAPETYPE = ('<v:shapetype id="_x0000_t202" coordsize="21600,21600" o:spt="202" path="m,l,21600r21600,l21600,xe">'
             '<v:stroke joinstyle="miter"/><v:path gradientshapeok="t" o:connecttype="rect"/></v:shapetype>')


def box(left, top, w, h, label, n):
    paras = ''.join(p(t('%s line %d' % (label, i + 1))) for i in range(n))
    return ('<v:shape style="position:absolute;left:%d;top:%d;width:%d;height:%d" type="#_x0000_t202" filled="false" stroked="true">'
            '<v:textbox inset="0,0,0,0"><w:txbxContent>%s</w:txbxContent></v:textbox></v:shape>') % (left, top, w, h, paras)


def group(h_b, label_b):
    return ('<w:r><w:pict>' + SHAPETYPE
            + '<v:group style="width:400pt;height:100pt;mso-position-horizontal-relative:char;mso-position-vertical-relative:line" '
              'coordorigin="0,0" coordsize="8000,2000">'
            + box(100, 100, 3500, 1600, 'Box A (tall)', 3) + box(4200, 100, 3500, h_b, label_b, 3)
            + '</v:group></w:pict></w:r>')


save('vml_group_textbox_overflow.docx',
     p(t('Paragraph before the group.')) + p(group(400, 'Box B (short)')) + p(t('Paragraph after the group.')))
save('vml_group_textbox_control.docx',
     p(t('Paragraph before the group.')) + p(group(1600, 'Box B (tall)')) + p(t('Paragraph after the group.')))
# 7) legacy form fields (FORMTEXT, FORMCHECKBOX, FORMDROPDOWN) with their w:ffData definitions
def ff_begin(inner):
    return '<w:r><w:fldChar w:fldCharType="begin"><w:ffData>%s</w:ffData></w:fldChar></w:r>' % inner


save('legacy_form_fields.docx',
     p(t('Name: '), ff_begin('<w:name w:val="Text1"/><w:enabled/><w:calcOnExit w:val="0"/><w:textInput><w:maxLength w:val="40"/></w:textInput>'),
       it(' FORMTEXT '), fc('separate'), t('Sample text'), fc('end'))
     + p(t('Agreed: '), ff_begin('<w:name w:val="Check1"/><w:enabled/><w:calcOnExit w:val="0"/><w:checkBox><w:sizeAuto/><w:default w:val="1"/></w:checkBox>'),
         it(' FORMCHECKBOX '), fc('end'))
     + p(t('Choice: '), ff_begin('<w:name w:val="Dropdown1"/><w:enabled/><w:calcOnExit w:val="0"/><w:ddList><w:result w:val="1"/>'
                                 '<w:listEntry w:val="first"/><w:listEntry w:val="second"/><w:listEntry w:val="third"/></w:ddList>'),
         it(' FORMDROPDOWN '), fc('separate'), t('second'), fc('end')))
print('fixtures written to', OUT)
