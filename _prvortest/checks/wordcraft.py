#!/usr/bin/env python3
"""wordcraft.py (THV-AC03, 14.10.2026) - WordCraft fixture checks for the PR pre-test.
Linux port of the WordCraft part of Tools/ac_wc_ec_nachtest.py (same steps and thresholds), plus two extra aspects
of #1672 (PDF output, cached result after save). Call:
  python3 -I wordcraft.py <wordcraft-cli> <artcraft-fixtures/wordcraft> <out.json> [--work DIR]
Issues: storytold/wordcraft #1671 (nested fields lost on save), #1672 (DATE/TIME keep their stored result),
#1643 (second text box of a VML group lost on save), #1174 (legacy form fields lose w:ffData on save).
known_main = what WordCraft 0.6.1/0.7.0 (Windows x64 releases) did, as in the issues.
THV-AC04 (17.10.2026): #1672 (fix PR #1679 merged 15.10.) and #1174 are FIXED on main (eae2421 / fd0bb2f); known_main
starts with "FIXED on `main`" there, so prv_draft.py treats them as already fixed on main.
The saved .docx files stay in the work folder: an Office cross-check (open in Word) is still worth doing."""
import os
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prv_common as C  # noqa: E402

ck = C.Checker('wordcraft', sys.argv)
W = ck.work
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']


def wc(args, tag, timeout=180):
    return C.run([ck.cli] + args, timeout=timeout, cwd=W, log_prefix=os.path.join(W, tag))


def convert(src, out, tag):
    if os.path.exists(out):
        os.remove(out)
    rc, so, se = wc(['convert', ck.fx(src), out], tag)
    if not os.path.exists(out):
        raise RuntimeError('convert wrote nothing (rc=%s): %s' % (rc, se.strip()[-300:]))
    return out


def docxml(path):
    with zipfile.ZipFile(path) as z:
        return z.read('word/document.xml').decode('utf-8', 'replace')


def instr(x):
    """All field codes of a document.xml: complex-field instrText runs joined, plus fldSimple w:instr."""
    parts = re.findall(r'<w:instrText[^>]*>([^<]*)</w:instrText>', x) + re.findall(r'w:instr="([^"]*)"', x)
    return re.sub(r'\s+', ' ', ' '.join(parts).replace('&quot;', '"'))


def long_date(d):
    return '%s, %d %s %d' % (DAYS[d.weekday()], d.day, MONTHS[d.month - 1], d.year)


def date_verdict(text):
    """(verdict, DATE line, TIME line) for the two lines of date_time_fields.docx in plain text."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    dl = next((ln for ln in lines if ln.startswith('DATE field')), '')
    tl = next((ln for ln in lines if ln.startswith('TIME field')), '')
    days = C.today_strings()
    date_ok = any(d.isoformat() in dl for d in days)
    time_ok = any(long_date(d) in tl for d in days)
    date_old, time_old = '2020-01-01' in dl, '1 January 2020' in tl
    v = 'FIXED' if date_ok and time_ok else ('NOT FIXED' if date_old and time_old else 'CHANGED')
    return v, dl, tl


# ---------- #1671 ----------
def c1671():
    x = docxml(convert('nested_fields.docx', os.path.join(W, 'nested_out.docx'), 'c1671'))
    begins = x.count('w:fldCharType="begin"') + x.count('<w:fldSimple')
    code = instr(x)
    refs = code.count('REF amount')
    v = 'FIXED' if begins >= 4 and refs >= 2 else ('NOT FIXED' if refs == 0 else 'CHANGED')
    return ('%d fields after save, nested REF kept %d of 2 times' % (begins, refs)), v, {'fields': begins, 'ref_amount': refs, 'codes': code[:300]}


ck.check('nested_fields.docx', 'wordcraft#1671', 'field nested in a field code (IF { REF }, = { REF }) after save',
         '4 fields, both nested REF amount kept', '2 fields; nested REFs replaced by their result ("IF 0 = 0")', c1671,
         aspect='save')


# ---------- #1672 ----------
def c1672_text():
    rc, so, se = wc(['text', ck.fx('date_time_fields.docx')], 'c1672_text')
    if rc != 0 and not so.strip():
        raise RuntimeError('text failed (rc=%s): %s' % (rc, se.strip()[-300:]))
    v, dl, tl = date_verdict(so)
    return '%s / %s' % (dl, tl), v, {'stdout': so[:400]}


def c1672_pdf():
    pdf = convert('date_time_fields.docx', os.path.join(W, 'date_time_out.pdf'), 'c1672_pdf')
    if shutil.which('pdftotext'):
        rc, so, se = C.run(['pdftotext', '-layout', pdf, '-'], timeout=60)
    else:
        import pypdf  # noqa: PLC0415 - optional
        so = '\n'.join(p.extract_text() or '' for p in pypdf.PdfReader(pdf).pages)
    v, dl, tl = date_verdict(so)
    return 'PDF text: %s / %s' % (dl, tl), v, {'pdf_text': so[:400]}


def c1672_save():
    x = docxml(convert('date_time_fields.docx', os.path.join(W, 'date_time_out.docx'), 'c1672_save'))
    code = instr(x)
    kept = 'DATE \\@ "yyyy-MM-dd"' in code and 'TIME \\@ "dddd, d MMMM yyyy"' in code
    texts = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', x)
    joined = ' | '.join(texts)
    days = C.today_strings()
    new = any(d.isoformat() in joined for d in days) and any(long_date(d) in joined for d in days)
    old = '2020-01-01' in joined and '1 January 2020' in joined
    v = 'CHANGED' if not kept else ('FIXED' if new else ('NOT FIXED' if old else 'CHANGED'))
    lock = 'w:fldLock' in x
    return ('field codes %s; cached results: %s' % ('kept' if kept else 'CHANGED', ' | '.join(t for t in texts if ':' not in t)[:120])), v, \
        {'codes': code[:300], 'texts': texts[:10], 'fldLock': lock}


ck.check('date_time_fields.docx', 'wordcraft#1672', 'unlocked DATE/TIME in `wordcraft-cli text`',
         "today's date in both lines (DATE yyyy-MM-dd, TIME dddd, d MMMM yyyy)",
         'FIXED on `main` eae2421 (fix #1679); 0.7.0: stored result 2020-01-01 / Wednesday, 1 January 2020', c1672_text,  # main eae2421, 17.10.2026 THV-AC04
         aspect='text')
ck.check('date_time_fields.docx', 'wordcraft#1672', 'unlocked DATE/TIME in PDF output (convert to .pdf)',
         "today's date in both lines", 'FIXED on `main` eae2421 (fix #1679); 0.7.0: 2020-01-01 / Wednesday, 1 January 2020',  # main eae2421, 17.10.2026 THV-AC04
         c1672_pdf, aspect='pdf')
ck.check('date_time_fields.docx', 'wordcraft#1672', 'DATE/TIME after save (convert to .docx)',
         "field codes unchanged; cached result today's date (as Word writes it)", 'FIXED on `main` eae2421 (fix #1679)', c1672_save,  # main eae2421, 17.10.2026 THV-AC04
         role='extra', aspect='save')


# ---------- #1643 ----------
def c1643(name, box_b):
    def fn():
        x = docxml(convert(name, os.path.join(W, 'vml_' + name.split('_')[-1].replace('.docx', '') + '_out.docx'), 'c1643_' + name[:-5]))
        a, b = 'Box A (tall) line 1' in x, box_b in x
        v = 'FIXED' if a and b else ('NOT FIXED' if a and not b else 'CHANGED')
        return 'after save: box A %s, box B %s' % ('kept' if a else 'LOST', 'kept' if b else 'LOST'), v, {'box_a': a, 'box_b': b}
    return fn


ck.check('vml_group_textbox_control.docx', 'wordcraft#1643', 'second text box of a VML group after save (both boxes tall enough)',
         'both text boxes kept', 'box B lost', c1643('vml_group_textbox_control.docx', 'Box B (tall) line 1'), aspect='save')
ck.check('vml_group_textbox_overflow.docx', 'wordcraft#1643', 'second text box of a VML group after save (box B overflows)',
         'both text boxes kept', 'box B lost', c1643('vml_group_textbox_overflow.docx', 'Box B (short) line 1'), aspect='save')


# ---------- #1174 ----------
def c1174():
    x = docxml(convert('legacy_form_fields.docx', os.path.join(W, 'form_out.docx'), 'c1174'))
    n = x.count('<w:ffData')
    kinds = [k for k in ('textInput', 'checkBox', 'ddList') if '<w:' + k in x]
    v = 'FIXED' if n >= 3 else ('NOT FIXED' if n == 0 else 'CHANGED')
    return '%d of 3 w:ffData after save (%s)' % (n, ', '.join(kinds) or 'none'), v, {'ffData': n, 'kinds': kinds}


ck.check('legacy_form_fields.docx', 'wordcraft#1174', 'legacy form fields (FORMTEXT, FORMCHECKBOX, FORMDROPDOWN) after save',
         '3 of 3 w:ffData kept', 'FIXED on `main` fd0bb2f/eae2421; 0.7.0: 0 of 3 w:ffData', c1174, aspect='save')  # main eae2421, 17.10.2026 THV-AC04

ck.write({'known_main_label': 'WordCraft 0.7.0 / `main` eae2421',
          'known_main_source': 'WordCraft 0.6.1 / 0.7.0 Windows x64 releases (issue reports, ac_wc_ec_nachtest.py); #1672/#1174 main eae2421 (17.10.2026)',
          'office_crosscheck': 'saved .docx files in the work folder; open them in Word before posting a FIXED for a save issue'})
