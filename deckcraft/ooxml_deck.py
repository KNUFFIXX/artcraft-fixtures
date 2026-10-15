#!/usr/bin/env python3
"""Minimal hand-written PresentationML packages (Python standard library only).

No template, nothing created or saved by Microsoft PowerPoint: every part below is written from the
ECMA-376 schema by hand. Used by make_fixtures_deckcraft.py.
"""
import os
import zipfile

STAMP = (2026, 10, 15, 0, 0, 0)  # fixed zip timestamps -> byte-for-byte reproducible output
NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
CT_MAIN = {
    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml',
    'potx': 'application/vnd.openxmlformats-officedocument.presentationml.template.main+xml',
    'ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml',
}
EMU = 12700  # per point


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def theme(font='Liberation Sans'):
    clr = ''.join('<a:%s><a:srgbClr val="%s"/></a:%s>' % (n, v, n) for n, v in (
        ('dk1', '000000'), ('lt1', 'FFFFFF'), ('dk2', '1F2937'), ('lt2', 'E5E7EB'), ('accent1', '2563EB'),
        ('accent2', 'DC2626'), ('accent3', '16A34A'), ('accent4', 'CA8A04'), ('accent5', '7C3AED'),
        ('accent6', '0891B2'), ('hlink', '1D4ED8'), ('folHlink', '6D28D9')))
    fills = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3
    lines = '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>' * 3
    effects = '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3
    return (XML + '<a:theme %s name="Fixture"><a:themeElements><a:clrScheme name="Fixture">%s</a:clrScheme>'
            '<a:fontScheme name="Fixture"><a:majorFont><a:latin typeface="%s"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
            '<a:minorFont><a:latin typeface="%s"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>'
            '<a:fmtScheme name="Fixture"><a:fillStyleLst>%s</a:fillStyleLst><a:lnStyleLst>%s</a:lnStyleLst>'
            '<a:effectStyleLst>%s</a:effectStyleLst><a:bgFillStyleLst>%s</a:bgFillStyleLst></a:fmtScheme>'
            '</a:themeElements></a:theme>') % (NS, clr, font, font, fills, lines, effects, fills)


MASTER = (XML + '<p:sldMaster %s><p:cSld><p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg><p:spTree>'
          '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
          '</p:spTree></p:cSld>'
          '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
          'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
          '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
          '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="3600"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill>'
          '<a:latin typeface="+mj-lt"/></a:defRPr></a:lvl1pPr></p:titleStyle>'
          '<p:bodyStyle><a:lvl1pPr><a:defRPr sz="2000"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill>'
          '<a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></p:bodyStyle>'
          '<p:otherStyle><a:lvl1pPr><a:defRPr sz="1800"><a:solidFill><a:schemeClr val="tx1"/></a:solidFill>'
          '<a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></p:otherStyle></p:txStyles></p:sldMaster>') % NS
LAYOUT = (XML + '<p:sldLayout %s type="blank" preserve="1"><p:cSld name="Blank"><p:spTree>'
          '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
          '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>') % NS


def rels(items):
    body = ''.join('<Relationship Id="%s" Type="%s" Target="%s"%s/>' % (
        i, t if t.startswith('http') else R + '/' + t, esc(tg), ' TargetMode="External"' if ext else '')
        for i, t, tg, ext in [(x + (False,))[:4] for x in items])
    return XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % body


def xfrm(x, y, w, h, tag='a:xfrm', extra=''):
    return '<%s%s><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></%s>' % (tag, extra, x * EMU, y * EMU, w * EMU, h * EMU, tag)


def run(text, sz=None, font=None, bold=False, color=None):
    attrs = ' lang="en-US"' + (' sz="%d"' % (sz * 100) if sz else '') + (' b="1"' if bold else '')
    inner = ''
    if color:
        inner += '<a:solidFill><a:srgbClr val="%s"/></a:solidFill>' % color
    if font:
        inner += '<a:latin typeface="%s"/>' % esc(font)
    return '<a:r><a:rPr%s dirty="0">%s</a:rPr><a:t>%s</a:t></a:r>' % (attrs, inner, esc(text))


def para(*runs, algn=None):
    ppr = '<a:pPr algn="%s"/>' % algn if algn else ''
    return '<a:p>%s%s</a:p>' % (ppr, ''.join(runs) or '<a:endParaRPr lang="en-US"/>')


def textbox(sid, name, x, y, w, h, paras, fill=None, line=None, geom='rect', anchor='t', body_extra=''):
    sp = '<a:prstGeom prst="%s"><a:avLst/></a:prstGeom>' % geom
    sp += '<a:solidFill><a:srgbClr val="%s"/></a:solidFill>' % fill if fill else '<a:noFill/>'
    sp += '<a:ln w="12700"><a:solidFill><a:srgbClr val="%s"/></a:solidFill></a:ln>' % line if line else ''
    return ('<p:sp><p:nvSpPr><p:cNvPr id="%d" name="%s"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            '<p:spPr>%s%s</p:spPr><p:txBody><a:bodyPr wrap="square" lIns="91440" tIns="45720" rIns="91440" bIns="45720" anchor="%s"%s>'
            '<a:noAutofit/></a:bodyPr><a:lstStyle/>%s</p:txBody></p:sp>') % (sid, esc(name), xfrm(x, y, w, h), sp, anchor, body_extra, ''.join(paras))


def picture(sid, name, rid, x, y, w, h):
    return ('<p:pic><p:nvPicPr><p:cNvPr id="%d" name="%s"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            '<p:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            '<p:spPr>%s<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>') % (sid, esc(name), rid, xfrm(x, y, w, h))


def group(sid, name, x, y, w, h, children):
    return ('<p:grpSp><p:nvGrpSpPr><p:cNvPr id="%d" name="%s"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/><a:chOff x="%d" y="%d"/><a:chExt cx="%d" cy="%d"/></a:xfrm></p:grpSpPr>'
            '%s</p:grpSp>') % (sid, esc(name), x * EMU, y * EMU, w * EMU, h * EMU, x * EMU, y * EMU, w * EMU, h * EMU, ''.join(children))


def table(sid, name, x, y, col_w, row_h, cells, font_sz=14):
    grid = ''.join('<a:gridCol w="%d"/>' % (c * EMU) for c in col_w)
    rows = ''
    for r in cells:
        tcs = ''.join('<a:tc><a:txBody><a:bodyPr/><a:lstStyle/>%s</a:txBody><a:tcPr>'
                      '<a:lnL w="12700"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:lnL>'
                      '<a:lnR w="12700"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:lnR>'
                      '<a:lnT w="12700"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:lnT>'
                      '<a:lnB w="12700"><a:solidFill><a:srgbClr val="000000"/></a:solidFill></a:lnB>'
                      '</a:tcPr></a:tc>' % para(run(t, sz=font_sz)) for t in r)
        rows += '<a:tr h="%d">%s</a:tr>' % (row_h * EMU, tcs)
    w, h = sum(col_w), row_h * len(cells)
    return ('<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="%d" name="%s"/><p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
            '%s<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1"/>'
            '<a:tblGrid>%s</a:tblGrid>%s</a:tbl></a:graphicData></a:graphic></p:graphicFrame>') % (sid, esc(name), xfrm(x, y, w, h, 'p:xfrm'), grid, rows)


def slide_xml(shapes, bg=None):
    bgx = '<p:bg><p:bgPr><a:solidFill><a:srgbClr val="%s"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>' % bg if bg else ''
    return (XML + '<p:sld %s><p:cSld>%s<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr/>%s</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>') % (NS, bgx, ''.join(shapes))


def write_deck(path, slides, size=(960, 540), kind='pptx', media=None, font='Liberation Sans', extra_parts=None, app='artcraft-fixtures (hand-written OOXML)'):
    """slides: list of (slide_xml_text, [(rId, rel_type, target)]) ; media: {part_name: bytes}"""
    media = media or {}
    extra_parts = extra_parts or {}
    ct_defaults = {'rels': 'application/vnd.openxmlformats-package.relationships+xml', 'xml': 'application/xml',
                   'png': 'image/png', 'jpeg': 'image/jpeg', 'jpg': 'image/jpeg', 'emf': 'image/x-emf', 'gif': 'image/gif', 'svg': 'image/svg+xml'}
    used_ext = sorted({'rels', 'xml'} | {n.rsplit('.', 1)[-1].lower() for n in media})
    overrides = [('/ppt/presentation.xml', CT_MAIN[kind]),
                 ('/ppt/slideMasters/slideMaster1.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml'),
                 ('/ppt/slideLayouts/slideLayout1.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml'),
                 ('/ppt/theme/theme1.xml', 'application/vnd.openxmlformats-officedocument.theme+xml'),
                 ('/docProps/app.xml', 'application/vnd.openxmlformats-officedocument.extended-properties+xml')]
    for i in range(len(slides)):
        overrides.append(('/ppt/slides/slide%d.xml' % (i + 1), 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml'))
    for name, (ctype, _) in extra_parts.items():
        overrides.append(('/' + name, ctype))
    ct = (XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          + ''.join('<Default Extension="%s" ContentType="%s"/>' % (e, ct_defaults[e]) for e in used_ext)
          + ''.join('<Override PartName="%s" ContentType="%s"/>' % o for o in overrides) + '</Types>')
    pres_rels = [('rId1', 'slideMaster', 'slideMasters/slideMaster1.xml'), ('rId2', 'theme', 'theme/theme1.xml')]
    sld_ids = ''
    for i in range(len(slides)):
        pres_rels.append(('rId%d' % (10 + i), 'slide', 'slides/slide%d.xml' % (i + 1)))
        sld_ids += '<p:sldId id="%d" r:id="rId%d"/>' % (256 + i, 10 + i)
    pres = (XML + '<p:presentation %s saveSubsetFonts="1"><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            '<p:sldIdLst>%s</p:sldIdLst><p:sldSz cx="%d" cy="%d"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>') % (
        NS, sld_ids, size[0] * EMU, size[1] * EMU)
    app_xml = (XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
               '<Application>%s</Application><Slides>%d</Slides></Properties>') % (esc(app), len(slides))
    parts = [('[Content_Types].xml', ct),
             ('_rels/.rels', rels([('rId1', 'officeDocument', 'ppt/presentation.xml'),
                                   ('rId2', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties', 'docProps/app.xml')])),
             ('docProps/app.xml', app_xml),
             ('ppt/presentation.xml', pres), ('ppt/_rels/presentation.xml.rels', rels(pres_rels)),
             ('ppt/slideMasters/slideMaster1.xml', MASTER),
             ('ppt/slideMasters/_rels/slideMaster1.xml.rels', rels([('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml'), ('rId2', 'theme', '../theme/theme1.xml')])),
             ('ppt/slideLayouts/slideLayout1.xml', LAYOUT),
             ('ppt/slideLayouts/_rels/slideLayout1.xml.rels', rels([('rId1', 'slideMaster', '../slideMasters/slideMaster1.xml')])),
             ('ppt/theme/theme1.xml', theme(font))]
    for i, (sx, srels) in enumerate(slides):
        parts.append(('ppt/slides/slide%d.xml' % (i + 1), sx))
        parts.append(('ppt/slides/_rels/slide%d.xml.rels' % (i + 1), rels([('rId1', 'slideLayout', '../slideLayouts/slideLayout1.xml')] + list(srels))))
    for name, (_, data) in extra_parts.items():
        parts.append((name, data))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts:
            z.writestr(zipfile.ZipInfo(name, STAMP), data, zipfile.ZIP_DEFLATED)
        for name, data in media.items():
            z.writestr(zipfile.ZipInfo(name, STAMP), data, zipfile.ZIP_STORED)
