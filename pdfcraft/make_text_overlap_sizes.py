# make_text_overlap_sizes.py - synthetic fixture for storytold/pdfcraft text extraction: glyph runs of a different size
# drawn over a line, shifted vertically by -3 .. +3 pt. Rows A: 8 pt value on a 10 pt dot leader. Rows B: 11 pt space
# glyphs over an 8 pt line. Standard-14 Helvetica only (not embedded), invented text. Needs reportlab.
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
c = canvas.Canvas('text_overlap_sizes.pdf', pagesize=A4, invariant=1)
y = 780
for dy in (-3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 3):
    # dot leader 10 pt + value 8 pt shifted by dy
    c.setFont('Helvetica', 10); lab = 'A%+.1f: ' % dy
    c.drawString(72, y, lab + '.' * 40)
    x0 = 72 + c.stringWidth(lab, 'Helvetica', 10)
    c.setFont('Helvetica', 8); c.drawString(x0 + 2, y + dy, 'Walter Example')
    y -= 24
y -= 10
for dy in (-3, -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2, 3):
    line = 'B%+.1f quick brown fox jumps' % dy
    c.setFont('Helvetica', 8); c.drawString(72, y, line)
    w = c.stringWidth(line, 'Helvetica', 8)
    c.setFont('Helvetica', 11); c.drawString(72, y + dy, ' ' * (int(w / c.stringWidth(' ', 'Helvetica', 11)) + 1))
    y -= 24
c.showPage(); c.save()
