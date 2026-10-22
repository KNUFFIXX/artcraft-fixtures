"""Fixture for pdfcraft: form_fill gives no warning when a value does not fit its field.

One page, four text fields (Helvetica):
  single_12pt          single line, 140 x 18 pt, DA 12 Tf   -> a long value is cut at the right edge
  multiline_12pt_short multiline,   140 x 18 pt, DA 12 Tf   -> the second line of a long value is outside the box
  single_auto          single line, 140 x 18 pt, DA 0 Tf    (control: auto size shrinks the text)
  wide_12pt            single line, 300 x 18 pt, DA 12 Tf   (control: the value fits)
Needs reportlab and pypdf.  Usage: python make_form_fill_value_overflow.py [out.pdf]
"""
import io
import sys

import pypdf
from pypdf.generic import NameObject, TextStringObject
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

out = sys.argv[1] if len(sys.argv) > 1 else 'form_fill_value_overflow.pdf'
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=A4, invariant=1)
c.setTitle('form_fill: values that do not fit')
c.setAuthor('artcraft-fixtures')
c.setFont('Helvetica', 11)
rows = [('single_12pt', 'single line, 12 pt, 140 pt wide', 140, ''),
        ('multiline_12pt_short', 'multiline, 12 pt, 140 x 18 pt', 140, 'multiline'),
        ('single_auto', 'single line, auto size (control)', 140, ''),
        ('wide_12pt', 'single line, 12 pt, 300 pt wide (control)', 300, '')]
y = 760
for name, label, width, flags in rows:
    c.drawString(40, y + 4, label)
    c.acroForm.textfield(name=name, x=260, y=y, width=width, height=18, fontName='Helvetica', fontSize=12,
                         borderWidth=1, forceBorder=True, fieldFlags=flags)
    y -= 60
c.save()
w = pypdf.PdfWriter(clone_from=pypdf.PdfReader(io.BytesIO(buf.getvalue())))
for a in w.pages[0]['/Annots']:
    a = a.get_object()
    if a.get('/T') == 'single_auto':
        a[NameObject('/DA')] = TextStringObject('/Helv 0 Tf 0 g')
w.add_metadata({'/Producer': 'artcraft-fixtures (reportlab + pypdf)'})
w.write(out)
print('written', out)
