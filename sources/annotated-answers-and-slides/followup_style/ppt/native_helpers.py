import re
from lxml import etree as E
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

