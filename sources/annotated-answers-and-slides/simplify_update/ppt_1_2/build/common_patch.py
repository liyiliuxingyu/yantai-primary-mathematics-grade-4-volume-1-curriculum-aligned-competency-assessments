#!/usr/bin/env python3
"""Narrow native-math patches preserving the current teaching deck package.

Rules name exact existing shape IDs/names. Original timings and all unrelated
package members remain byte-identical. New math is genuine OMML and contains
dedicated compiled SVG/PNG compatibility pictures, never shared media edits.
"""
from pathlib import Path
import argparse, copy, hashlib, json, re, subprocess, sys, zipfile
from lxml import etree as E
import fitz

HERE=Path(__file__).resolve().parent
PROJECT=next(p for p in [HERE.parents[1]/'project', *HERE.parents] if (p/'followup_style/ppt/ooxml_compat.py').exists())
sys.path.insert(0,str(PROJECT/'followup_style/ppt'))
sys.path.insert(0,str(PROJECT/'ppt_builder'))
from ooxml_compat import NS, inject_formula, visible_nodes
from convert_inputs import MathParser, ast_plain
PR='http://schemas.openxmlformats.org/package/2006/relationships'
SVG='http://schemas.microsoft.com/office/drawing/2016/SVG/main'

def sha(b):return hashlib.sha256(b).hexdigest()
def q(s):p,n=s.split(':');return '{'+NS[p]+'}'+n
def el(s,**a):return E.Element(q(s),{k:str(v) for k,v in a.items()})
def sub(p,s,**a):n=el(s,**a);p.append(n);return n
def xml(e):return E.tostring(e,encoding='UTF-8',xml_declaration=True,standalone=True)
def logical_ids(r):return [(n.get('id'),n.get('name')) for n in visible_nodes(r)]
def timing(b):
 m=re.search(rb'<p:timing>.*?</p:timing>',b,re.S)
 return m.group() if m else None
def find_shape(root,name):
 found=[n for n in visible_nodes(root) if n.get('name')==name]
 assert len(found)==1,(name,len(found))
 return next(a for a in found[0].iterancestors() if a.tag in (q('p:sp'),q('p:pic')))
def container(shape):
 a=shape
 while a.getparent() is not None and a.getparent().tag in (q('mc:Choice'),q('mc:Fallback'),q('mc:AlternateContent')):a=a.getparent()
 return a
def c_nv(shape):return shape.find('.//p:cNvPr',NS)
def get_rect(shape):
 x=shape.find('.//a:xfrm',NS);o=x.find('a:off',NS);e=x.find('a:ext',NS)
 return [int(o.get('x'))/9525,int(o.get('y'))/9525,int(e.get('cx'))/9525,int(e.get('cy'))/9525]
def set_rect(shape,rect):
 xf=shape.find('.//a:xfrm',NS);o=xf.find('a:off',NS);e=xf.find('a:ext',NS)
 for key,v in zip(('x','y'),rect[:2]):o.set(key,str(round(v*9525)))
 for key,v in zip(('cx','cy'),rect[2:]):e.set(key,str(round(v*9525)))

def compile_asset(op,folder,font):
 key=sha(json.dumps({k:op.get(k) for k in ('tex','rows','points','color')},ensure_ascii=False,sort_keys=True).encode())[:24]
 stem='simplify_'+key;source=folder/(stem+'.tex');pdf=source.with_suffix('.pdf');svg=source.with_suffix('.svg');png=source.with_suffix('.png')
 points=op.get('points',32);color=op.get('color','C00000')
 tex=op.get('tex')
 if op.get('rows'):
  tex=r'\begin{array}{r@{\;}l}'+r'\\'.join(('&'+row if i==0 else '=&'+row) for i,row in enumerate(op['rows']))+r'\end{array}'
 if not svg.exists() or not png.exists():
  source.write_text('\\documentclass[border=1pt]{standalone}\n\\usepackage{fix-cm,fontspec,amsmath,amssymb,xcolor}\n\\setmainfont{'+font.name+'}[Path={'+font.parent.as_posix()+'/}]\n\\begin{document}\n{\\fontsize{'+str(points)+'pt}{'+str(points*1.25)+'pt}\\selectfont\\color[HTML]{'+color+'}$\\displaystyle '+tex+'$}\n\\end{document}\n')
  run=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape',source.name],cwd=folder,capture_output=True,text=True)
  (folder/(stem+'.log.txt')).write_text(run.stdout+run.stderr)
  assert run.returncode==0 and 'Missing character' not in run.stdout,source
  subprocess.run(['pdftocairo','-svg',str(pdf),str(svg)],check=True)
  subprocess.run(['pdftoppm','-singlefile','-r','192','-png',str(pdf),str(png.with_suffix(''))],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 with fitz.open(pdf) as d:w,h=d[0].rect.width*4/3,d[0].rect.height*4/3
 ast=op.get('ast')
 if ast is None:
  if op.get('rows'):
   ast={'t':'matrix','rows':[[{'t':'text','v':' ' if i==0 else '='},MathParser(row).parse()] for i,row in enumerate(op['rows'])]}
  else:ast=MathParser(tex).parse()
 return {'key':key,'stem':stem,'tex':tex,'svg':svg,'png':png,'pdf':pdf,'source':source,'width':w,'height':h,'ast':ast,'plain':ast_plain(ast),'points':points,'color':color}

def matrix_alignment(shape):
 for m in shape.findall('.//m:m',NS):
  pr=el('m:mPr');bj=sub(pr,'m:baseJc');bj.set(q('m:val'),'center')
  cs=sub(pr,'m:mcs');c=sub(cs,'m:mc');cp=sub(c,'m:mcPr');cnt=sub(cp,'m:count');cnt.set(q('m:val'),'2');jc=sub(cp,'m:mcJc');jc.set(q('m:val'),'left')
  m.insert(0,pr)

def assert_preserved_ids(before,after):
 assert len({i for i,n in after})==len(after),'duplicate logical shape ID'
 old=dict(before);assert [(i,n) for i,n in after if i in old]==before,'original shape IDs/names/order changed'

def patch_rows(root,rels,op,asset,extra):
 """Native single-line equations in one original animation-anchor group.

 Office readers vary in the alignment of OMML matrix columns. Explicit xfrm
 coordinates give every equality and every following first digit one column.
 """
 old=find_shape(root,op['name']);nv=copy.deepcopy(c_nv(old));x,y,w,h=op.get('rect',get_rect(old));count=len(op['rows']);rowh=h/count
 grp=el('p:grpSp');ng=sub(grp,'p:nvGrpSpPr');ng.append(nv);sub(ng,'p:cNvGrpSpPr');sub(ng,'p:nvPr')
 xf=sub(sub(grp,'p:grpSpPr'),'a:xfrm');sub(xf,'a:off',x='0',y='0');sub(xf,'a:ext',cx='12192000',cy='6858000');sub(xf,'a:chOff',x='0',y='0');sub(xf,'a:chExt',cx='12192000',cy='6858000')
 ident=max(int(n.get('id')) for n in visible_nodes(root))+1
 outer=container(old);outer.getparent().replace(outer,grp);reports=[]
 for i,row in enumerate(op['rows']):
  items=[('rhs',asset['row_assets'][i],x+42,w-42)]
  if i:items.insert(0,('equals',asset['equals_asset'],x,34))
  for label,a,xx,ww in items:
   name=op['name']+'_simplify_'+label+str(i);sp=el('p:sp');n=sub(sp,'p:nvSpPr');sub(n,'p:cNvPr',id=ident,name=name);ident+=1;sub(n,'p:cNvSpPr',txBox='1');sub(n,'p:nvPr');pr=sub(sp,'p:spPr');xxf=sub(pr,'a:xfrm');sub(xxf,'a:off',x=round(xx*9525),y=round((y+i*rowh)*9525));sub(xxf,'a:ext',cx=round(ww*9525),cy=round(rowh*9525));sub(sub(pr,'a:prstGeom',prst='rect'),'a:avLst');sub(pr,'a:noFill');grp.append(sp)
   reports.append(patch_math(root,rels,{'name':name,'rect':[xx,y+i*rowh,ww,rowh],'min_scale':op.get('min_scale',.72)},a,extra))
 return {'name':op['name'],'rect':[x,y,w,h],'native_group_anchor':nv.get('id'),'original_click_preserved':True,'rows':reports}

def patch_math(root,rels,op,asset,extra):
 old=find_shape(root,op['name']);nv=copy.deepcopy(c_nv(old));rect=op.get('rect',get_rect(old));x,y,w,h=rect
 ww,hh=asset['width'],asset['height'];scale=min(1,w/ww,h/hh);ww*=scale;hh*=scale
 assert scale>=op.get('min_scale',.72),(op['name'],'formula too small',scale)
 used={r.get('Id') for r in rels};ids={}
 for ext in ('png','svg'):
  rid='rIdSimplify'+asset['key']+ext
  assert rid not in used or any(r.get('Id')==rid and r.get('Target')=='../media/'+asset['stem']+'.'+ext for r in rels)
  if rid not in used:E.SubElement(rels,'{'+PR+'}Relationship',Id=rid,Type=NS['r']+'/image',Target='../media/'+asset['stem']+'.'+ext)
  ids[ext]=rid;extra['ppt/media/'+asset['stem']+'.'+ext]=asset[ext].read_bytes()
 pic=el('p:pic');n=sub(pic,'p:nvPicPr');n.append(nv);sub(n,'p:cNvPicPr');sub(n,'p:nvPr')
 bf=sub(pic,'p:blipFill');bl=sub(bf,'a:blip');bl.set(q('r:embed'),ids['png']);exl=sub(bl,'a:extLst');ex=sub(exl,'a:ext',uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}');sv=E.SubElement(ex,'{'+SVG+'}svgBlip',nsmap={'asvg':SVG});sv.set(q('r:embed'),ids['svg'])
 sub(sub(bf,'a:stretch'),'a:fillRect');pr=sub(pic,'p:spPr');xf=sub(pr,'a:xfrm');sub(xf,'a:off',x=round(x*9525),y=round((y+(h-hh)/2)*9525));sub(xf,'a:ext',cx=round(ww*9525),cy=round(hh*9525));sub(sub(pr,'a:prstGeom',prst='rect'),'a:avLst')
 outer=container(old);outer.getparent().replace(outer,pic)
 inject_formula(root,{'target':op['name'],'ast':asset['ast'],'color':asset['color'],'points':asset['points'],'font':'Droid Sans Fallback'})
 native=find_shape(root,op['name']);set_rect(native,rect);matrix_alignment(native)
 return {'name':op['name'],'rect':rect,'asset':asset['key'],'plain':asset['plain'],'fallback_scale':round(scale,5),'points':asset['points']}

def patch_text(root,op):
 old=find_shape(root,op['name']);rect=op.get('rect',get_rect(old));nv=copy.deepcopy(c_nv(old));points=op.get('points',32);color=op.get('color','C00000')
 sp=el('p:sp');n=sub(sp,'p:nvSpPr');n.append(nv);sub(n,'p:cNvSpPr',txBox='1');sub(n,'p:nvPr');pr=sub(sp,'p:spPr');xf=sub(pr,'a:xfrm');sub(xf,'a:off',x=round(rect[0]*9525),y=round(rect[1]*9525));sub(xf,'a:ext',cx=round(rect[2]*9525),cy=round(rect[3]*9525));sub(sub(pr,'a:prstGeom',prst='rect'),'a:avLst');sub(pr,'a:noFill')
 tx=sub(sp,'p:txBody');bp=sub(tx,'a:bodyPr',wrap='square',lIns='0',tIns='0',rIns='0',bIns='0',anchor='t');sub(bp,'a:noAutofit');sub(tx,'a:lstStyle')
 for line in op['text'].split('\n'):
  p=sub(tx,'a:p');sub(p,'a:pPr',algn='l');r=sub(p,'a:r');rp=sub(r,'a:rPr',lang='zh-CN',sz=round(points*100));sub(sub(rp,'a:solidFill'),'a:srgbClr',val=color);sub(rp,'a:latin',typeface='Droid Sans Fallback');sub(rp,'a:ea',typeface='Droid Sans Fallback');t=sub(r,'a:t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=line;sub(p,'a:endParaRPr',lang='zh-CN',sz=round(points*100))
 outer=container(old);outer.getparent().replace(outer,sp)
 return {'name':op['name'],'rect':rect,'text':op['text'],'points':points}

def patch_volume(source,dest,rules,assets,assetfolder):
 assert not dest.exists(),dest
 report=[]
 with zipfile.ZipFile(source) as z:
  original={i.filename:z.read(i.filename) for i in z.infolist()};parts=dict(original);extra={};changed=[]
  for s in rules:
   name=f'ppt/slides/slide{s["slide"]}.xml';rname=f'ppt/slides/_rels/slide{s["slide"]}.xml.rels';b=parts[name];root=E.fromstring(b);rels=E.fromstring(parts[rname]);ids=logical_ids(root);ops=[]
   for op in s['ops']:
    if op['type']=='math':ops.append((patch_rows if op.get('rows') else patch_math)(root,rels,op,assets[id(op)],extra))
    elif op['type']=='text':ops.append(patch_text(root,op))
    else:raise ValueError(op['type'])
   assert_preserved_ids(ids,logical_ids(root))
   nb=xml(root);t=timing(b)
   if t:nb=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:t,nb,flags=re.S)
   assert timing(nb)==t
   parts[name]=nb
   if xml(rels)!=parts[rname]:parts[rname]=xml(rels)
   changed.append(s['slide']);report.append({'key':s.get('key'),'slide':s['slide'],'ops':ops})
  for k,b in extra.items():parts[k]=b
  changedparts=[k for k in original if original[k]!=parts[k]]
  allowed={f'ppt/slides/slide{n}.xml' for n in changed}|{f'ppt/slides/_rels/slide{n}.xml.rels' for n in changed}
  assert set(changedparts)<=allowed
  total=0
  for k,b in original.items():
   if re.fullmatch(r'ppt/slides/slide\d+\.xml',k):
    total+=1;assert timing(parts[k])==timing(b);assert_preserved_ids(logical_ids(E.fromstring(b)),logical_ids(E.fromstring(parts[k])))
  tmp=dest.with_suffix('.tmp');dest.parent.mkdir(parents=True,exist_ok=True)
  with zipfile.ZipFile(tmp,'w') as out:
   for info in z.infolist():out.writestr(info,parts.pop(info.filename))
   for k,b in parts.items():out.writestr(k,b,compress_type=zipfile.ZIP_DEFLATED)
  tmp.replace(dest)
 return {'source':str(source),'source_sha256':sha(source.read_bytes()),'output':str(dest),'output_sha256':sha(dest.read_bytes()),'bytes':dest.stat().st_size,'total_slides':total,'changed_slides':changed,'changed_original_parts':changedparts,'new_parts':sorted(extra),'timing_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'changes':report}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rules',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--assets',type=Path,required=True);args=ap.parse_args()
 rules=json.loads(args.rules.read_text());args.assets.mkdir(parents=True,exist_ok=True);font=PROJECT/'fonts/DroidSansFallback.ttf';assets={}
 for s in rules:
  for op in s['ops']:
   if op['type']=='math':
    if op.get('rows'):
     a={'row_assets':[compile_asset({**op,'rows':None,'tex':row},args.assets,font) for row in op['rows']], 'equals_asset':compile_asset({**op,'rows':None,'tex':'='},args.assets,font)}
    else:a=compile_asset(op,args.assets,font)
    assets[id(op)]=a
 reports=[]
 for v in sorted(set(s['volume'] for s in rules)):
  src=next(args.source.glob('*第'+str(v)+'册*.pptx'));reports.append(patch_volume(src,args.out/src.name,[s for s in rules if s['volume']==v],assets,args.assets))
 args.out.mkdir(exist_ok=True);(args.out/'qa_package.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps([{k:r[k] for k in ('output','total_slides','changed_slides','output_sha256')} for r in reports],ensure_ascii=False))
if __name__=='__main__':main()
