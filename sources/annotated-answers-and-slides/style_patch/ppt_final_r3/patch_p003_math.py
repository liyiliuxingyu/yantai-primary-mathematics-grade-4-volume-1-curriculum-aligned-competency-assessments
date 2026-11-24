#!/usr/bin/env python3
"""Add true OMML formulas with actual LaTeX SVG/PNG fallback to p003 trees.

Run after ../ppt_final/patch_p003_native.py. The first patch preserves all source
timing. This second patch preserves that timing and makes only math semantics
and the requested removal of a duplicate formula change.
"""
from pathlib import Path
import copy,hashlib,json,re,subprocess,sys,zipfile
from lxml import etree as E
import fitz

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BASE=OUT/'.build/native_stage.pptx'
DST=OUT/'小学四上同步素养卷第1册讲解课件答案.pptx'
sys.path.insert(0,str(OUT))
from ooxml_compat import inject_formula
from patch_p003_native_stage import shape
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
PR='http://schemas.openxmlformats.org/package/2006/relationships'
SVG='http://schemas.microsoft.com/office/drawing/2016/SVG/main'
P,A,R=[NS[k] for k in ('p','a','r')]
def sha(x):return hashlib.sha256(x).hexdigest()
def q(s):p,n=s.split(':');return '{'+NS[p]+'}'+n
def el(s,**kw):return E.Element(q(s),{k:str(v) for k,v in kw.items()})
def sub(p,s,**kw):n=el(s,**kw);p.append(n);return n
def xml(r):return E.tostring(r,encoding='UTF-8',xml_declaration=True,standalone=True)

def compile_formulas():
    folder=OUT/'formulas';folder.mkdir(exist_ok=True)
    formulas=[(r'4\times18=72\text{(千克)}','4×18=72(千克)',23),(r'72-32=40\text{(千克)}','72−32=40(千克)',23),(r'40\div4=10\text{(千克)}','40÷4=10(千克)',23),(r'10\times4+32=40+32=72\text{(千克)}','10×4+32=40+32=72(千克)',30),(r'4\times18=72\text{(千克)}','4×18=72(千克)',30)]
    assets=[]
    for i,(tex,text,points) in enumerate(formulas):
        stem=f'formula_{i+1}';source=folder/f'{stem}.tex'
        source.write_text('\\documentclass[border=1pt]{standalone}\n\\usepackage{fontspec,amsmath,xcolor}\n\\definecolor{answer}{HTML}{C00000}\n\\setmainfont[Path=../../../fonts/]{DroidSansFallback.ttf}\n\\begin{document}\n\\fontsize{'+str(points)+'}{'+str(points+5)+'}\\selectfont\n'+('\\color{answer}\n' if points==30 else '')+'$'+tex+'$\n\\end{document}\n')
        with (folder/f'{stem}.stdout.log').open('wb') as log:
            subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error',source.name],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
        pdf=folder/f'{stem}.pdf';svg=folder/f'{stem}.svg';png=folder/f'{stem}.png'
        subprocess.run(['pdftocairo','-svg',str(pdf),str(svg)],check=True)
        subprocess.run(['pdftoppm','-singlefile','-r','192','-png',str(pdf),str(png.with_suffix(''))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        d=fitz.open(pdf);rect=d[0].rect
        assets.append({'index':i,'text':text,'tex':tex,'points':points,'source':source,'pdf':pdf,'svg':svg,'png':png,'width_px':rect.width*4/3,'height_px':rect.height*4/3})
    return assets

def picture(old,asset,rid_png,rid_svg):
    nvold=old.find('p:nvSpPr/p:cNvPr',NS);xfold=old.find('p:spPr/a:xfrm',NS)
    off=xfold.find('a:off',NS);ext=xfold.find('a:ext',NS)
    x,y=[int(off.get(k))/9525 for k in ('x','y')];w,h=[int(ext.get(k))/9525 for k in ('cx','cy')]
    ww,hh=asset['width_px'],asset['height_px'];scale=min(1,w/ww,h/hh);ww*=scale;hh*=scale
    pic=el('p:pic');nv=sub(pic,'p:nvPicPr');nv.append(copy.deepcopy(nvold));sub(nv,'p:cNvPicPr');sub(nv,'p:nvPr')
    bf=sub(pic,'p:blipFill');blip=sub(bf,'a:blip');blip.set(q('r:embed'),rid_png);exl=sub(blip,'a:extLst');ex=sub(exl,'a:ext',uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}');sv=E.SubElement(ex,'{'+SVG+'}svgBlip',nsmap={'asvg':SVG});sv.set(q('r:embed'),rid_svg)
    st=sub(bf,'a:stretch');sub(st,'a:fillRect')
    pr=sub(pic,'p:spPr');xf=sub(pr,'a:xfrm');sub(xf,'a:off',x=round(x*9525),y=round((y+(h-hh)/2)*9525));sub(xf,'a:ext',cx=round(ww*9525),cy=round(hh*9525));g=sub(pr,'a:prstGeom',prst='rect');sub(g,'a:avLst')
    return pic

def make_math(root,rels,old,a):
    index=a['index'];name=old.find('p:nvSpPr/p:cNvPr',NS).get('name')
    ids={ext:f'rIdP003Formula{index+1}{ext.upper()}' for ext in ('png','svg')}
    for ext,rid in ids.items():E.SubElement(rels,'{'+PR+'}Relationship',Id=rid,Type=R+'/image',Target=f'../media/p003_formula_{index+1}.{ext}')
    fallback=picture(old,a,ids['png'],ids['svg']);old.getparent().replace(old,fallback)
    inject_formula(root,{'target':name,'ast':{'t':'text','v':a['text']},'color':'000000' if a['points']==23 else 'C00000','points':a['points'],'font':'Droid Sans Fallback'})
    choice=next(s for s in root.xpath('.//*[local-name()="Choice"]/*[local-name()="sp"]') if s.find('p:nvSpPr/p:cNvPr',NS).get('name')==name)
    pr=choice.find('p:spPr',NS);pr.replace(pr.find('a:xfrm',NS),copy.deepcopy(old.find('p:spPr/a:xfrm',NS)))
    # Red verification formulas use red real SVG/PNG fallbacks as well.
    return choice

def main():
    assert not DST.exists(),'Immutable output already exists'
    if not BASE.exists():subprocess.run([sys.executable,str(OUT/'patch_p003_native_stage.py')],check=True)
    assert sha(BASE.read_bytes())=='5de72b9c3dd9755944757fce029e0697be2ae5d6a3c6238835632fb68fd4812a'
    assets=compile_formulas();parts={};changes=[]
    with zipfile.ZipFile(BASE) as z:
        for info in z.infolist():parts[info.filename]=z.read(info.filename)
    root=E.fromstring(parts['ppt/slides/slide71.xml'])
    for sp in root.findall('p:cSld/p:spTree/p:sp',NS):
        ident=sp.find('p:nvSpPr/p:cNvPr',NS).get('id')
        if ident=='25':
            ts=sp.findall('.//a:t',NS);ts[0].text='两幅图分析方向不同，得到的综合算式相同。'
        if ident=='28':
            for t in sp.findall('.//a:t',NS):t.text=''
    parts['ppt/slides/slide71.xml']=xml(root);changes.append('ppt/slides/slide71.xml')
    for a in assets:
        for ext in ('png','svg'):
            parts[f'ppt/media/p003_formula_{a["index"]+1}.{ext}']=a[ext].read_bytes()
    spath='ppt/slides/slide74.xml';rpath='ppt/slides/_rels/slide74.xml.rels'
    root=E.fromstring(parts[spath]);rels=E.fromstring(parts[rpath]);tree=root.find('p:cSld/p:spTree',NS)
    replacements={4:(64,124,210,58,'回顾检验：'),5:(280,124,900,58,''),6:(64,274,240,58,'与回收总量'),7:(310,274,415,58,''),9:(750,274,466,58,'一致，答案正确。')}
    for old in list(tree):
        nv=old.find('p:nvSpPr/p:cNvPr',NS)
        if nv is None:continue
        ident=int(nv.get('id'))
        if ident in replacements:
            x,y,w,h,txt=replacements[ident];tree.replace(old,shape(ident,nv.get('name'),x,y,w,h,txt,points=30))
    for ident,a in [(5,assets[3]),(7,assets[4])]:
        old=next(s for s in tree.findall('p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('id')==str(ident));make_math(root,rels,old,a)
    parts[spath]=xml(root);parts[rpath]=xml(rels);changes.extend([spath,rpath])
    for n in (75,76):
        spath=f'ppt/slides/slide{n}.xml';rpath=f'ppt/slides/_rels/slide{n}.xml.rels'
        root=E.fromstring(parts[spath]);rels=E.fromstring(parts[rpath]);group=root.find('p:cSld/p:spTree/p:grpSp',NS)
        for j in range(3):
            index=j if n==75 else 2-j;a=assets[index];name=f'p003_s07_equation_{j}'
            old=next(s for s in group.findall('p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('name')==name)
            make_math(root,rels,old,a)
        parts[spath]=xml(root);parts[rpath]=xml(rels);changes.extend([spath,rpath])
    # Preserve source timing bytes even if serializer settings change.
    with zipfile.ZipFile(BASE) as z:
        for n in (71,74,75,76):
            key=f'ppt/slides/slide{n}.xml';m=re.search(rb'<p:timing>.*?</p:timing>',z.read(key),re.S)
            if m:parts[key]=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:m.group(),parts[key],flags=re.S)
        with zipfile.ZipFile(DST,'w') as out:
            for info in z.infolist():out.writestr(info,parts.pop(info.filename))
            for name,b in parts.items():out.writestr(name,b,compress_type=zipfile.ZIP_DEFLATED)
    record={'input':str(BASE),'output':str(DST),'output_sha256':sha(DST.read_bytes()),'relative_to_first_patch_changed_parts':changes,'new_media':[f'ppt/media/p003_formula_{i}.{ext}' for i in (1,2,3,4,5) for ext in ('png','svg')],'formula_implementation':'Eight genuine OMML formula objects in mc:Choice Requires=a14, each with a real LaTeX-compiled SVG and PNG picture fallback in mc:Fallback. Native nodes, units and single operators remain editable slide objects.','formula_assets':[{'text':a['text'],'points':a['points'],'tex_source':str(a['source']),'tex_sha256':sha(a['source'].read_bytes()),'pdf_sha256':sha(a['pdf'].read_bytes()),'svg_sha256':sha(a['svg'].read_bytes()),'png_sha256':sha(a['png'].read_bytes())} for a in assets]}
    (OUT/'patch_rules_math.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':main()
