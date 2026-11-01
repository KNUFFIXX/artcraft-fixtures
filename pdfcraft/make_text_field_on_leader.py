# make_text_field_on_leader.py - synthetic fixture for storytold/pdfcraft: an AcroForm text field whose 8 pt value sits on a 10 pt dot leader.
# Standard-14 Helvetica only (not embedded), no real data.
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def fx_space_overlay(path):
    c = canvas.Canvas(path, pagesize=A4, invariant=1)
    c.setTitle('pdfcraft fixture: space glyphs drawn over a line of smaller text')
    line = 'The quick brown fox jumps over the lazy dog'
    y = 700
    c.setFont('Helvetica', 8); c.drawString(72, y, line)
    w = c.stringWidth(line, 'Helvetica', 8)
    n = int(w / c.stringWidth(' ', 'Helvetica', 11)) + 1
    c.setFont('Helvetica', 11); c.drawString(72, y + 1.5, ' ' * n)
    c.setFont('Helvetica', 8); c.drawString(72, 660, 'Control line without anything on top of it')
    c.showPage(); c.save()

def fx_value_on_leader(path, widget=False):
    c = canvas.Canvas(path, pagesize=A4, invariant=1)
    c.setTitle('pdfcraft fixture: field value drawn on a dot leader')
    y = 700
    c.setFont('Helvetica', 10)
    label = 'Name: '
    c.drawString(72, y, label + '.' * 60)
    x0 = 72 + c.stringWidth(label, 'Helvetica', 10)
    if widget:
        c.acroForm.textfield(name='name', value='Walter Example', x=x0, y=y - 2, width=200, height=12,
                             fontName='Helvetica', fontSize=8, borderWidth=0, fillColor=None, forceBorder=False)
    else:
        c.setFont('Helvetica', 8); c.drawString(x0 + 2, y + 1, 'Walter Example')
    c.setFont('Helvetica', 10); c.drawString(72, 660, 'Control line without anything on top of it')
    c.showPage(); c.save()

fx_value_on_leader('text_field_on_leader.pdf', widget=True)
print('ok')
