#!/usr/bin/env python3
"""Targeted OOXML patch over an Artifact Tool export.

Reproduces the companion, compilable TikZ trees as editable native objects.
Keeps every original slide, relationship, and timing part except four slides.
No python-pptx, whole-deck re-export, or animation regeneration is used.
"""
from pathlib import Path
import copy, hashlib, json, re, zipfile
from lxml import etree as E

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT/'deliverables/讲解课件/小学四上同步素养卷第1册讲解课件答案.pptx'
DST = OUT/'.build/native_stage.pptx'
EXPECTED = 'bae9ace05a27c4178d32ad36ccdb2b5c9ee6bce943b16362377be4fdda92e16b'
NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
P,A = NS['p'],NS['a']
FONT = 'Droid Sans Fallback'
PX = 9525

def sha(b): return hashlib.sha256(b).hexdigest()
def q(s): p,n=s.split(':'); return '{'+NS[p]+'}'+n
def el(s,**kw): return E.Element(q(s),{k:str(v) for k,v in kw.items()})
def sub(parent,s,**kw): n=el(s,**kw);parent.append(n);return n
def geom(parent,x,y,w,h):
    xf=sub(parent,'a:xfrm');sub(xf,'a:off',x=round(x*PX),y=round(y*PX));sub(xf,'a:ext',cx=round(w*PX),cy=round(h*PX));return xf

def shape(ident,name,x,y,w,h,text='',points=30,color='C00000',fill=None,align='l',bold=False,computed=False):
    sp=el('p:sp');nv=sub(sp,'p:nvSpPr');sub(nv,'p:cNvPr',id=ident,name=name);sub(nv,'p:cNvSpPr',txBox='1');sub(nv,'p:nvPr')
    pr=sub(sp,'p:spPr');geom(pr,x,y,w,h)
    gp=sub(pr,'a:prstGeom',prst='roundRect' if fill else 'rect');av=sub(gp,'a:avLst')
    if fill:sub(av,'a:gd',name='adj',fmla='val 12000')
    if fill:sf=sub(pr,'a:solidFill');sub(sf,'a:srgbClr',val=fill)
    else:sub(pr,'a:noFill')
    ln=sub(pr,'a:ln');sub(ln,'a:noFill')
    tb=sub(sp,'p:txBody');sub(tb,'a:bodyPr',wrap='none',lIns='0',tIns='0',rIns='0',bIns='0',anchor='ctr');sub(tb,'a:lstStyle')
    p=sub(tb,'a:p');pp=sub(p,'a:pPr',algn=align);sub(pp,'a:lnSpc');pp[-1].append(el('a:spcPct',val='100000'))
    pieces = re.split(r'(\d+)',text) if computed else [text]
    for piece in pieces:
        if not piece:continue
        r=sub(p,'a:r');rp=sub(r,'a:rPr',lang='zh-CN',sz=round(points*100),b='1' if bold else '0')
        sf=sub(rp,'a:solidFill');sub(sf,'a:srgbClr',val='C00000' if computed and piece.isdigit() else color)
        sub(rp,'a:latin',typeface=FONT);sub(rp,'a:ea',typeface=FONT);sub(rp,'a:cs',typeface=FONT)
        sub(r,'a:t').text=piece
    sub(p,'a:endParaRPr',lang='zh-CN',sz=round(points*100))
    return sp

def line(ident,name,x1,y1,x2,y2):
    sp=el('p:cxnSp');nv=sub(sp,'p:nvCxnSpPr');sub(nv,'p:cNvPr',id=ident,name=name);sub(nv,'p:cNvCxnSpPr');sub(nv,'p:nvPr')
    pr=sub(sp,'p:spPr');xf=geom(pr,min(x1,x2),min(y1,y2),max(abs(x2-x1),.1),max(abs(y2-y1),.1))
    if x2<x1:xf.set('flipH','1')
    if y2<y1:xf.set('flipV','1')
    gp=sub(pr,'a:prstGeom',prst='line');sub(gp,'a:avLst')
    ln=sub(pr,'a:ln',w='15240');sf=sub(ln,'a:solidFill');sub(sf,'a:srgbClr',val='000000');sub(ln,'a:prstDash',val='solid');return sp

def plain_tex(s):return s.replace(r'\(', '').replace(r'\)', '')

def native_tree(root,forward,spec):
    tree=root.find('p:cSld/p:spTree',NS)
    old=next(s for s in tree if s.find('.//p:cNvPr',NS) is not None and s.find('.//p:cNvPr',NS).get('id')=='4')
    nvold=old.find('.//p:cNvPr',NS)
    grp=el('p:grpSp');nv=sub(grp,'p:nvGrpSpPr');nv.append(copy.deepcopy(nvold));sub(nv,'p:cNvGrpSpPr');sub(nv,'p:nvPr')
    pr=sub(grp,'p:grpSpPr');xf=sub(pr,'a:xfrm');sub(xf,'a:off',x='0',y='0');sub(xf,'a:ext',cx='12192000',cy='6858000');sub(xf,'a:chOff',x='0',y='0');sub(xf,'a:chExt',cx='12192000',cy='6858000')
    # Native geometry reproduces the dependency graph of the companion TikZ.
    coords={'a':(80,222,260,62),'b':(410,222,260,62),'c':(140,334,290,62),'d':(500,334,280,62),'e':(220,446,260,62),'f':(570,446,190,62),'g':(330,558,300,62)}
    labels={'a':'0','b':'1','c':'3','d':'4','e':'5','f':'6','g':'2'}
    connections=[('a','c'),('b','c'),('c','e'),('d','e'),('e','g'),('f','g')]
    if not forward:
        coords={'g':(330,222,300,62),'e':(200,334,270,62),'f':(570,334,210,62),'c':(140,446,290,62),'d':(500,446,280,62),'a':(80,558,260,62),'b':(410,558,260,62)}
        labels={'a':'12','b':'13','c':'9','d':'10','e':'7','f':'8','g':'11'}
        connections=[('g','e'),('g','f'),('e','c'),('e','d'),('c','a'),('c','b')]
    ident=6
    for a,b in connections:
        x,y,w,h=coords[a];xx,yy,ww,hh=coords[b]
        grp.append(line(ident,f'p003_s07_edge_{a}_{b}',x+w/2,y+h,xx+ww/2,yy));ident+=1
    for k,(x,y,w,h) in coords.items():
        grp.append(shape(ident,'p003_s07_node_'+k,x,y,w,h,plain_tex(spec['labels'][labels[k]]),points=24,color='000000',fill='FFF2CC',align='ctr',computed=k in ('c','e','g')));ident+=1
    header='从条件开始分析' if forward else '从问题开始分析'
    grp.append(shape(ident,'p003_s07_tree_heading',80,124,750,60,header,points=30,color='000000',bold=True));ident+=1
    ops=[(350,222,'×'),(445,334,'−'),(505,446,'÷')] if forward else [(490,334,'÷'),(445,446,'−'),(350,558,'×')]
    for x,y,txt in ops:
        grp.append(shape(ident,'p003_s07_operator_'+str(ident),x,y,50,62,txt,points=30,color='000000',align='ctr'));ident+=1
    equations=['4×18＝72(千克)','72−32＝40(千克)','40÷4＝10(千克)']
    if not forward:equations.reverse()
    for n,txt in enumerate(equations):
        grp.append(shape(ident,'p003_s07_equation_'+str(n),850,251+112*n,380,62,txt,points=23,color='000000'));ident+=1
    tree.replace(old,grp)

def replace_content(root,used,lines):
    tree=root.find('p:cSld/p:spTree',NS)
    for old in list(tree):
        nv=old.find('.//p:cNvPr',NS)
        if nv is None:continue
        ident=int(nv.get('id'))
        if ident not in used:continue
        item=lines.get(ident)
        if item:
            x,y,w,h,txt,pt=item
            new=shape(ident,nv.get('name'),x,y,w,h,txt,points=pt)
        else:
            # Keep all original animation targets valid. Empty shapes have no paint.
            new=shape(ident,nv.get('name'),64,124,1,1,'',points=1)
        tree.replace(old,new)

def slide_patch(n,b,spec):
    timing = re.search(rb'<p:timing>.*?</p:timing>',b,re.S)
    root=E.fromstring(b)
    if n==71:
        rows={4:(64,124,1152,58,'从条件出发：先求回收总量，再求剩余质量，',30),
              6:(64,194,1152,58,'最后求平均每批质量。',30),
              18:(64,274,1152,58,'从问题出发：求每批质量，需要剩余质量和批数；',30),
              19:(64,344,1152,58,'求剩余质量，需要回收总量和已处理质量；',30),
              21:(64,414,1152,58,'求回收总量，需要每班回收质量和班数。',30),
              25:(64,504,1152,58,'两幅图的分析方向不同，综合算式相同：',30),
              28:(64,574,1152,58,'（4×18−32）÷4＝10(千克)',30)}
        replace_content(root,range(4,31),rows)
    elif n==74:
        rows={4:(64,124,1152,58,'回顾检验：10×4＋32＝40＋32＝72(千克)',30),
              8:(64,204,1152,58,'送出的剩余量与已处理量之和是72千克，',30),
              9:(64,274,1152,58,'与回收总量4×18＝72(千克)一致，答案正确。',30)}
        replace_content(root,range(4,10),rows)
    elif n in (75,76):native_tree(root,n==75,spec)
    result=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
    if timing:
        result=re.sub(rb'<p:timing>.*?</p:timing>',lambda m:timing.group(),result,flags=re.S)
    return result

def main():
    assert sha(SRC.read_bytes())==EXPECTED,'Unexpected source package'
    assert not DST.exists(),'Immutable output already exists'
    DST.parent.mkdir(exist_ok=True)
    spec=json.loads((OUT/'p003_style_spec.json').read_text())
    changed=[]
    with zipfile.ZipFile(SRC) as src,zipfile.ZipFile(DST,'w') as dst:
        for info in src.infolist():
            b=src.read(info.filename)
            m=re.fullmatch(r'ppt/slides/slide(71|74|75|76)\.xml',info.filename)
            if m:
                b=slide_patch(int(m.group(1)),b,spec);changed.append(info.filename)
            dst.writestr(info,b)
    # Keep reusable sources next to the immutable patch.
    (OUT/'p003_style_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n')
    preamble='\\documentclass[border=3pt]{standalone}\n\\usepackage{fontspec,xcolor,tikz,amsmath,amssymb}\n\\setmainfont[Path=../../fonts/]{DroidSansFallback.ttf}\n\\begin{document}\n'
    for stem,key in [('p003_s07_a1','left_tikz'),('p003_s07_a2','right_tikz')]:
        (OUT/(stem+'.tex')).write_text(preamble+spec[key]+'\n\\end{document}\n')
    rules={'source':str(SRC),'source_sha256':EXPECTED,'output':str(DST),'output_sha256':sha(DST.read_bytes()),'changed_slides':[71,74,75,76],'changed_zip_parts':changed,'preservation':'All original package components other than the four slide XML parts are copied as identical uncompressed bytes. All original timing XML bytes are retained. The answer tree outer object IDs remain 4.','editable_tree':'Slides 75 and 76 use native editable grouped shapes and text, reproducing the companion compilable TikZ dependency trees. This is not a claim that the native group is an embedded TikZ SVG.','reference':'资料库4上-01-信息窗3-第1课时-用两步以上的四则混合运算解决问题，第6/7页，淡黄圆角节点、黑色已知量、红色求得数字。'}
    (OUT/'patch_rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(rules,ensure_ascii=False))

if __name__=='__main__':main()
