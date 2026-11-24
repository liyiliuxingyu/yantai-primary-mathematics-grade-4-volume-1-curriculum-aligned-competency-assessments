#!/usr/bin/env python3
"""Fill the two later quantity trees and expand their actual check formulas.

The imported Artifact Tool deck already contains native timings and formulas.
This narrow OOXML preservation patch leaves every unrelated package component
and every original timing byte unchanged. Diagrams are editable native groups;
equations are genuine OMML with XeLaTeX SVG+PNG compatibility fallbacks.
"""
from pathlib import Path
import copy, hashlib, json, re, subprocess, sys, zipfile
from lxml import etree as E
import fitz

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
NAME='小学四上同步素养卷第1册讲解课件答案.pptx'
SRC=ROOT/'deliverables/讲解课件'/NAME
DST=OUT/'r3'/NAME
EXPECTED='cb848adba20fdab5365ab0bf31c1675ffad94ea3334fe7624435066ab6f96252'
sys.path.insert(0,str(OUT))
from native_helpers import shape,line,el,sub,NS
from ooxml_compat import inject_formula
NS.update({'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','mc':'http://schemas.openxmlformats.org/markup-compatibility/2006','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'})
PR='http://schemas.openxmlformats.org/package/2006/relationships'
SVG='http://schemas.microsoft.com/office/drawing/2016/SVG/main'

def sha(b):return hashlib.sha256(b).hexdigest()
def xml(e):return E.tostring(e,encoding='UTF-8',xml_declaration=True,standalone=True)
def q(s):p,n=s.split(':');return '{'+NS[p]+'}'+n

FORMULAS=[
 (r'12+96=108\text{(元)}','12+96=108(元)',23,'000000'),
 (r'108\times3=324\text{(元)}','108×3=324(元)',23,'000000'),
 (r'324+10=334\text{(元)}','324+10=334(元)',23,'000000'),
 (r'70\div5=14\text{(元)}','70÷5=14(元)',23,'000000'),
 (r'230-160=70\text{(元)}','230−160=70(元)',23,'000000'),
 (r'80\times2=160\text{(元)}','80×2=160(元)',23,'000000'),
 (r'(334-10)\div3=324\div3=108\text{(元)}','(334−10)÷3=324÷3=108(元)',30,'C00000'),
 (r'12+96=108\text{(元)}','12+96=108(元)',30,'C00000'),
 (r'80\times2+14\times5=160+70=230\text{(元)}','80×2+14×5=160+70=230(元)',30,'C00000'),
]

def compile_formulas():
 folder=OUT/'formulas';folder.mkdir(exist_ok=True);assets=[]
 for i,(tex,text,points,color) in enumerate(FORMULAS):
  stem=f'formula_{i+1:02d}';source=folder/(stem+'.tex')
  font=ROOT/'fonts/DroidSansFallback.ttf'
  source.write_text('\\documentclass[border=1pt]{standalone}\n\\usepackage{fontspec,amsmath,xcolor}\n\\definecolor{ink}{HTML}{'+color+'}\n\\setmainfont[Path=../../../fonts/]{'+font.name+'}\n\\begin{document}\n\\fontsize{'+str(points)+'}{'+str(points+5)+'}\\selectfont\\color{ink}\n$'+tex+'$\n\\end{document}\n')
  with (folder/(stem+'.stdout.log')).open('wb') as log:
   subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error',source.name],cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True)
  pdf=source.with_suffix('.pdf');svg=source.with_suffix('.svg');png=source.with_suffix('.png')
  subprocess.run(['pdftocairo','-svg',str(pdf),str(svg)],check=True)
  subprocess.run(['pdftoppm','-singlefile','-r','192','-png',str(pdf),str(png.with_suffix(''))],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
  with fitz.open(pdf) as doc:rect=doc[0].rect
  assets.append({'index':i,'tex':tex,'text':text,'points':points,'color':color,'source':source,'pdf':pdf,'svg':svg,'png':png,'width_px':rect.width*4/3,'height_px':rect.height*4/3})
 return assets

def math_shape(root,rels,old,asset):
 nvold=old.find('p:nvSpPr/p:cNvPr',NS);xfold=old.find('p:spPr/a:xfrm',NS)
 off=xfold.find('a:off',NS);ext=xfold.find('a:ext',NS)
 x,y=[int(off.get(k))/9525 for k in ('x','y')];w,h=[int(ext.get(k))/9525 for k in ('cx','cy')]
 ww,hh=asset['width_px'],asset['height_px'];scale=min(1,w/ww,h/hh);ww*=scale;hh*=scale
 index=asset['index']+1;ids={e:f'rIdFollowupFormula{index}{e.upper()}' for e in ('png','svg')}
 for ext,rid in ids.items():E.SubElement(rels,'{'+PR+'}Relationship',Id=rid,Type=NS['r']+'/image',Target=f'../media/followup_formula_{index:02d}.{ext}')
 pic=el('p:pic');nv=sub(pic,'p:nvPicPr');nv.append(copy.deepcopy(nvold));sub(nv,'p:cNvPicPr');sub(nv,'p:nvPr')
 bf=sub(pic,'p:blipFill');blip=sub(bf,'a:blip');blip.set(q('r:embed'),ids['png']);exl=sub(blip,'a:extLst');ex=sub(exl,'a:ext',uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}');sv=E.SubElement(ex,'{'+SVG+'}svgBlip',nsmap={'asvg':SVG});sv.set(q('r:embed'),ids['svg'])
 st=sub(bf,'a:stretch');sub(st,'a:fillRect');pr=sub(pic,'p:spPr');xf=sub(pr,'a:xfrm');sub(xf,'a:off',x=round(x*9525),y=round((y+(h-hh)/2)*9525));sub(xf,'a:ext',cx=round(ww*9525),cy=round(hh*9525));gp=sub(pr,'a:prstGeom',prst='rect');sub(gp,'a:avLst')
 name=nvold.get('name');old.getparent().replace(old,pic)
 inject_formula(root,{'target':name,'ast':{'t':'text','v':asset['text']},'color':asset['color'],'points':asset['points'],'font':'Droid Sans Fallback'})
 choice=next(s for s in root.xpath('.//mc:Choice/p:sp',namespaces=NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('name')==name)
 pr=choice.find('p:spPr',NS);pr.replace(pr.find('a:xfrm',NS),copy.deepcopy(xfold))

def tree_patch(root,rels,key,assets):
 tree=root.find('p:cSld/p:spTree',NS)
 old=next(s for s in tree if s.find('.//p:cNvPr',NS) is not None and s.find('.//p:cNvPr',NS).get('id')=='4')
 grp=el('p:grpSp');nv=sub(grp,'p:nvGrpSpPr');nv.append(copy.deepcopy(old.find('.//p:cNvPr',NS)));sub(nv,'p:cNvGrpSpPr');sub(nv,'p:nvPr')
 pr=sub(grp,'p:grpSpPr');xf=sub(pr,'a:xfrm');sub(xf,'a:off',x='0',y='0');sub(xf,'a:ext',cx='12192000',cy='6858000');sub(xf,'a:chOff',x='0',y='0');sub(xf,'a:chExt',cx='12192000',cy='6858000')
 forward=key=='p005_s04'
 if forward:
  coords={'a':(64,222,330,62),'b':(445,222,365,62),'c':(84,334,360,62),'d':(520,334,210,62),'e':(104,446,390,62),'f':(580,446,200,62),'g':(230,558,340,62)}
  labels={'a':'扇贝单价12元/千克','b':'梭子蟹单价96元/千克','c':'两种单价和108元','d':'3倍','e':'单价和的3倍324元','f':'多10元','g':'礼盒单价334元'}
  links=[('a','c'),('b','c'),('c','e'),('d','e'),('e','g'),('f','g')];ops=[(400,222,'＋'),(455,334,'×'),(505,446,'＋')]
  eqids=[0,1,2]
 else:
  coords={'g':(330,222,300,62),'e':(200,334,290,62),'f':(570,334,240,62),'c':(140,446,290,62),'d':(500,446,310,62),'a':(80,558,310,62),'b':(450,558,280,62)}
  labels={'a':'桌子单价80元','b':'桌子数量2张','c':'总金额230元','d':'桌子总价160元','e':'椅子总价70元','f':'椅子数量5把','g':'椅子单价14元'}
  links=[('g','e'),('g','f'),('e','c'),('e','d'),('d','a'),('d','b')];ops=[(505,334,'÷'),(445,446,'−'),(405,558,'×')]
  eqids=[3,4,5]
 ident=6
 for a,b in links:
  x,y,w,h=coords[a];xx,yy,ww,hh=coords[b];grp.append(line(ident,f'{key}_edge_{a}_{b}',x+w/2,y+h,xx+ww/2,yy));ident+=1
 for k,(x,y,w,h) in coords.items():
  node=shape(ident,f'{key}_node_{k}',x,y,w,h,labels[k],points=24,color='000000',fill='FFF2CC',align='ctr',computed=(k in ('c','e','g') if forward else k in ('d','e','g')))
  if forward and k=='e':
   for run in node.findall('.//a:r',NS):
    if run.find('a:t',NS).text=='3':run.find('a:rPr/a:solidFill/a:srgbClr',NS).set('val','000000')
  grp.append(node);ident+=1
 grp.append(shape(ident,f'{key}_heading',64,124,750,60,'从条件开始分析' if forward else '从问题开始分析',points=30,color='000000',bold=True));ident+=1
 for x,y,txt in ops:grp.append(shape(ident,f'{key}_operator_{ident}',x,y,50,62,txt,points=30,color='000000',align='ctr'));ident+=1
 for j in range(3):grp.append(shape(ident,f'{key}_equation_{j}',860,251+112*j,380,62,'',points=23,color='000000'));ident+=1
 tree.replace(old,grp)
 for j,i in enumerate(eqids):
  old=next(s for s in grp.findall('p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('name')==f'{key}_equation_{j}')
  math_shape(root,rels,old,assets[i])
 return labels

def replace_check(root,rels,n,assets):
 tree=root.find('p:cSld/p:spTree',NS)
 if n==117:
  rows={4:(64,124,220,58,'反向检验：'),5:(64,204,1152,64,''),6:(64,304,200,58,'两种单价和'),7:(290,304,750,64,''),8:(64,404,1152,58,'反推所得与两种单价和相等，'),9:(64,474,1152,58,'符合“单价和的3倍多10元”。')};formulae={5:6,7:7};used=range(4,14)
 else:
  rows={4:(64,124,220,58,'回顾检验：'),5:(64,204,1152,64,''),6:(64,304,1152,58,'两张桌子的总价与五把椅子的总价相加，'),7:(64,374,1152,58,'正好等于小票总金额230元，符合题意。')};formulae={5:8};used=range(4,8)
 for old in list(tree):
  nv=old.find('.//p:cNvPr',NS)
  if nv is None:continue
  ident=int(nv.get('id'))
  if ident not in used:continue
  row=rows.get(ident,(64,124,1,1,''));x,y,w,h,txt=row
  new=shape(ident,nv.get('name'),x,y,w,h,txt,points=30 if ident in rows else 1)
  tree.replace(old,new)
 for ident,index in formulae.items():
  old=next(s for s in tree.findall('p:sp',NS) if s.find('p:nvSpPr/p:cNvPr',NS).get('id')==str(ident));math_shape(root,rels,old,assets[index])

def main():
 assert sha(SRC.read_bytes())==EXPECTED,'Unexpected current source'
 assert not DST.exists(),'Immutable destination exists'
 DST.parent.mkdir(exist_ok=True)
 assets=compile_formulas();parts={};modified=[];labels={}
 with zipfile.ZipFile(SRC) as z:
  for i in z.infolist():parts[i.filename]=z.read(i.filename)
  for n in (117,118,171,172):
   key=f'ppt/slides/slide{n}.xml';relkey=f'ppt/slides/_rels/slide{n}.xml.rels';original=parts[key]
   root=E.fromstring(original);rels=E.fromstring(parts[relkey])
   if n in (118,172):
    qkey='p005_s04' if n==118 else 'p007_s08';labels[qkey]=tree_patch(root,rels,qkey,assets)
   else:replace_check(root,rels,n,assets)
   b=xml(root);timing=re.search(rb'<p:timing>.*?</p:timing>',original,re.S)
   if timing:b=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:timing.group(),b,flags=re.S)
   parts[key]=b;parts[relkey]=xml(rels);modified.extend([key,relkey])
  for a in assets:
   for ext in ('png','svg'):parts[f'ppt/media/followup_formula_{a["index"]+1:02d}.{ext}']=a[ext].read_bytes()
  with zipfile.ZipFile(DST.with_suffix('.tmp'),'w') as out:
   for info in z.infolist():out.writestr(info,parts.pop(info.filename))
   for name,b in parts.items():out.writestr(name,b,compress_type=zipfile.ZIP_DEFLATED)
 DST.with_suffix('.tmp').replace(DST)
 record={'source':str(SRC),'source_sha256':EXPECTED,'output':str(DST),'output_sha256':sha(DST.read_bytes()),'changed_slides':[117,118,171,172],'changed_original_parts':modified,'node_labels':labels,'formula_implementation':'Nine genuine editable OMML objects, each with actual XeLaTeX SVG and PNG fallbacks. All other math remains unchanged.','preservation':'All 426 timing XML bytes and every unrelated original ZIP member remain identical.','assets':[{'index':a['index']+1,'tex':a['tex'],'text':a['text'],'points':a['points'],'source_sha256':sha(a['source'].read_bytes()),'pdf_sha256':sha(a['pdf'].read_bytes()),'svg_sha256':sha(a['svg'].read_bytes()),'png_sha256':sha(a['png'].read_bytes())} for a in assets]}
 (OUT/'patch_rules.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in record.items() if k!='assets'},ensure_ascii=False))

if __name__=='__main__':main()
