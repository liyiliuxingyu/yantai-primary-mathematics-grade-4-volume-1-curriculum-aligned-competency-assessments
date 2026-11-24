#!/usr/bin/env python3
"""Volumes 1–2 narrow OOXML edit, with preserved original animation anchors.

Efficient-method side notes on early units are grouped with the unchanged
original concluding object. Original timing bytes and original ID/name order
remain unchanged; all new children have fresh unique IDs.
"""
from pathlib import Path
import argparse,copy,json,re,zipfile
from lxml import etree as E
import common_patch as C
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
NS=C.NS

def blank(root,ident,name,rect):
 sp=C.el('p:sp');nv=C.sub(sp,'p:nvSpPr');C.sub(nv,'p:cNvPr',id=ident,name=name);C.sub(nv,'p:cNvSpPr',txBox='1');C.sub(nv,'p:nvPr')
 pr=C.sub(sp,'p:spPr');xf=C.sub(pr,'a:xfrm');C.sub(xf,'a:off',x=round(rect[0]*9525),y=round(rect[1]*9525));C.sub(xf,'a:ext',cx=round(rect[2]*9525),cy=round(rect[3]*9525));C.sub(C.sub(pr,'a:prstGeom',prst='rect'),'a:avLst');C.sub(pr,'a:noFill')
 return sp

def nextid(root):return max(int(n.get('id')) for n in C.visible_nodes(root))+1

def note(root,rels,op,assets,extra):
 old=C.find_shape(root,op['name']);outer=C.container(old);nv=copy.deepcopy(C.c_nv(old));ident=nextid(root)
 # Keep the exact original formula/text in a nested object. The group keeps
 # the original ID/name, which is the unmodified animation target.
 grp=C.el('p:grpSp');ng=C.sub(grp,'p:nvGrpSpPr');ng.append(nv);C.sub(ng,'p:cNvGrpSpPr');C.sub(ng,'p:nvPr')
 xf=C.sub(C.sub(grp,'p:grpSpPr'),'a:xfrm');C.sub(xf,'a:off',x=0,y=0);C.sub(xf,'a:ext',cx=12192000,cy=6858000);C.sub(xf,'a:chOff',x=0,y=0);C.sub(xf,'a:chExt',cx=12192000,cy=6858000)
 outer.getparent().replace(outer,grp)
 for n in outer.findall('.//p:cNvPr',NS):n.set('id',str(ident));n.set('name',op['name']+'_retained_original');n.set('descr',op['name']+'_retained_original')
 ident+=1;grp.append(outer)
 x,y,w,h=op['rect'];names=[]
 for suffix,txt,yy,hh,pt in [('title',op['title'],y,36,op['title_points']),('explain',op['text'],y+38,32,op['note_points'])]:
  name=op['name']+'_simplify_'+suffix;grp.append(blank(root,ident,name,[x,yy,w,hh]));ident+=1
  C.patch_text(root,{'name':name,'text':txt,'rect':[x,yy,w,hh],'points':pt});names.append(name)
 name=op['name']+'_simplify_steps';rect=[x,y+70,w,h-70];grp.append(blank(root,ident,name,rect))
 report=C.patch_rows(root,rels,{'name':name,'rows':op['rows'],'rect':rect,'points':op['points']},assets,extra)
 return {'name':op['name'],'type':'side_note','original_content_retained':True,'animation_anchor_id':nv.get('id'),'note_title':op['title'],'note_text':op['text'],'math':report}

def move(root,op):
 # Preserve dimensions of existing native/fallback formula objects; only shift
 # by one common delta so formula glyphs and their existing equals stay aligned.
 old=C.find_shape(root,op['name']);orig=C.get_rect(old);dx=op['rect'][0]-orig[0];dy=op['rect'][1]-orig[1]
 for nv in root.findall('.//p:cNvPr',NS):
  if nv.get('name')!=op['name']:continue
  shape=next((a for a in nv.iterancestors() if a.tag in (C.q('p:sp'),C.q('p:pic'))),None)
  if shape is None:continue
  r=C.get_rect(shape);C.set_rect(shape,[r[0]+dx,r[1]+dy,r[2],r[3]])
 return {'name':op['name'],'type':'move','delta':[dx,dy]}

def patch_volume(source,dest,rules,assets):
 assert not dest.exists(),dest
 report=[]
 with zipfile.ZipFile(source) as z:
  original={i.filename:z.read(i.filename) for i in z.infolist()};parts=dict(original);extra={};changed=[]
  for s in rules:
   name=f'ppt/slides/slide{s["slide"]}.xml';rname=f'ppt/slides/_rels/slide{s["slide"]}.xml.rels';b=parts[name];root=E.fromstring(b);rels=E.fromstring(parts[rname]);ids=C.logical_ids(root);ops=[]
   for op in s['ops']:
    if op['type']=='note':ops.append(note(root,rels,op,assets[id(op)],extra))
    elif op['type']=='math':ops.append((C.patch_rows if op.get('rows') else C.patch_math)(root,rels,op,assets[id(op)],extra))
    elif op['type']=='text':ops.append(C.patch_text(root,op))
    elif op['type']=='move':ops.append(move(root,op))
    else:raise ValueError(op['type'])
   C.assert_preserved_ids(ids,C.logical_ids(root));nb=C.xml(root);t=C.timing(b)
   if t:nb=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:t,nb,flags=re.S)
   assert C.timing(nb)==t;parts[name]=nb
   if C.xml(rels)!=parts[rname]:parts[rname]=C.xml(rels)
   changed.append(s['slide']);report.append({'key':s['key'],'slide':s['slide'],'ops':ops})
  parts.update(extra);changedparts=[k for k in original if original[k]!=parts[k]]
  assert set(changedparts)<={f'ppt/slides/slide{n}.xml' for n in changed}|{f'ppt/slides/_rels/slide{n}.xml.rels' for n in changed}
  total=0
  for k,b in original.items():
   if re.fullmatch(r'ppt/slides/slide\d+\.xml',k):
    total+=1;assert C.timing(parts[k])==C.timing(b);C.assert_preserved_ids(C.logical_ids(E.fromstring(b)),C.logical_ids(E.fromstring(parts[k])))
  dest.parent.mkdir(parents=True,exist_ok=True);tmp=dest.with_suffix('.tmp')
  with zipfile.ZipFile(tmp,'w') as out:
   for info in z.infolist():out.writestr(info,parts.pop(info.filename))
   for k,b in parts.items():out.writestr(k,b,compress_type=zipfile.ZIP_DEFLATED)
  tmp.replace(dest)
 return {'source':str(source),'source_sha256':C.sha(source.read_bytes()),'output':str(dest),'output_sha256':C.sha(dest.read_bytes()),'total_slides':total,'changed_slides':changed,'changed_original_parts':changedparts,'new_parts':sorted(extra),'timing_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'original_early_methods_retained':True,'changes':report}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rules',type=Path,default=BASE/'rules.json');ap.add_argument('--out',type=Path,required=True);ap.add_argument('--source',type=Path,default=BASE.parent/'bundle/讲解课件');args=ap.parse_args()
 rules=json.loads(args.rules.read_text());folder=BASE/'formulas';folder.mkdir(exist_ok=True);font=C.PROJECT/'fonts/DroidSansFallback.ttf';assets={}
 for s in rules:
  for op in s['ops']:
   if op['type'] not in ('note','math'):continue
   if op.get('rows'):a={'row_assets':[C.compile_asset({**op,'rows':None,'tex':row},folder,font) for row in op['rows']],'equals_asset':C.compile_asset({**op,'rows':None,'tex':'='},folder,font)}
   else:a=C.compile_asset(op,folder,font)
   assets[id(op)]=a
 reports=[]
 for v in (1,2):
  src=next(args.source.glob('*第'+str(v)+'册*.pptx'));reports.append(patch_volume(src,args.out/src.name,[s for s in rules if s['volume']==v],assets))
 (args.out/'qa_package.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n');print(json.dumps([{k:r[k] for k in ('output','total_slides','changed_slides','output_sha256')} for r in reports],ensure_ascii=False))
if __name__=='__main__':main()
