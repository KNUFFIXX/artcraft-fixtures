"""Fixture for pdfcraft: doc_flatten keeps empty text fields that have no appearance stream.

One page, four text fields (Helvetica 12 pt):
  filled      value "Jane Doe", with appearance stream
  empty_ap    no value, with an (empty) appearance stream  -> control, removed by flatten today
  empty_no_ap_1, empty_no_ap_2   no value, no /AP           -> stay after flatten (the issue)
Needs reportlab and pypdf.  Usage: python make_flatten_empty_field_no_ap.py [out.pdf]
"""
import io
import sys

import pypdf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

out = sys.argv[1] if len(sys.argv) > 1 else 'flatten_empty_field_no_ap.pdf'
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=A4, invariant=1)
c.setTitle('flatten: empty fields without appearance')
c.setAuthor('artcraft-fixtures')
c.setFont('Helvetica', 11)
rows = [('filled', 'filled, with appearance', 'Jane Doe'),
        ('empty_ap', 'empty, with appearance (control)', ''),
        ('empty_no_ap_1', 'empty, no appearance', ''),
        ('empty_no_ap_2', 'empty, no appearance', '')]
y = 760
for name, label, value in rows:
    c.drawString(60, y + 4, label)
    c.acroForm.textfield(name=name, value=value, x=300, y=y, width=200, height=18, fontName='Helvetica',
                         fontSize=12, borderWidth=1, forceBorder=True)
    y -= 60
c.save()
w = pypdf.PdfWriter(clone_from=pypdf.PdfReader(io.BytesIO(buf.getvalue())))
for a in w.pages[0]['/Annots']:
    a = a.get_object()
    if str(a.get('/T', '')).startswith('empty_no_ap'):
        del a['/AP']
w.add_metadata({'/Producer': 'artcraft-fixtures (reportlab + pypdf)'})
w.write(out)
print('written', out)
