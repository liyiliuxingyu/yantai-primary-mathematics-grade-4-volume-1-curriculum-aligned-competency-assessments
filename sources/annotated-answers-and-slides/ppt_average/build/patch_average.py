from pathlib import Path
import sys,json,copy,zipfile,re,importlib.util,hashlib
from lxml import etree as E
R=Path(__file__).resolve().parents[1];P=R.parent if (R.parent/'ppt_builder').is_dir() else R.parent/'project'
BASELINE=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else R.parent/'bundle/讲解课件'
sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
spec=importlib.util.spec_from_file_location('native_patch',R/'build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from ooxml_compat import TimingBuilder,validate_slide
J=lambda p:json.loads(p.read_text())
def W(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def find_any(root,name):
 ns=[n for n in m.visible_nodes(root) if n.get('name')==name];assert len(ns)==1,(name,len(ns))
 return next(a for a in ns[0].iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')])
def placeholder(root,name,parent=None):
 ident=max(int(n.get('id')) for n in m.visible_nodes(root))+1
 sp=m.el('p:sp');nv=m.sub(sp,'p:nvSpPr');m.sub(nv,'p:cNvPr',id=ident,name=name);m.sub(nv,'p:cNvSpPr',txBox='1');m.sub(nv,'p:nvPr');pr=m.sub(sp,'p:spPr');xf=m.sub(pr,'a:xfrm');m.sub(xf,'a:off',x='0',y='0');m.sub(xf,'a:ext',cx='9525',cy='9525')
 (parent if parent is not None else root.find('p:cSld/p:spTree',m.NS)).append(sp)
 return name
def asset(op):
 if op.get('rows'):
  return {'row_assets':[asset({**op,'rows':None,'tex':x}) for x in op['rows']],'equals_asset':asset({**op,'rows':None,'tex':'='})}
 a=m.compile_asset(op,R/'formulas',P/'fonts/DroidSansFallback.ttf');used[a['key']]=a;return a
def apply(root,rels,op,assets,extra):
 if op['type']=='text':return m.patch_text(root,op)
 if op['type']=='math':return (m.patch_rows if op.get('rows') else m.patch_math)(root,rels,op,assets,extra)
 if op['type']=='group_rows':
  group=find_any(root,op['name']);assert group.tag==m.q('p:grpSp')
  for nv in list(m.visible_nodes(group)):
   sp=next((a for a in nv.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')]),None)
   if sp is not None and sp.tag!=m.q('p:grpSp'):m.patch_text(root,{'name':nv.get('name'),'text':'','rect':[1,1,1,1]})
  name=placeholder(root,op['name']+'_average_rows',group)
  return m.patch_rows(root,rels,{**op,'name':name},assets,extra)
 raise ValueError(op['type'])

rules=J(R/'rules.json');adds=J(R/'additions.json');used={};assets={}
(R/'formulas').mkdir(exist_ok=True)
for x in rules:
 for op in x['ops']:
  if op['type']!='text':assets[id(op)]=asset(op)
for x in adds:assets[id(x)]=asset({'rows':x['rows'],'points':32})
reports=[]
for v in [5,6]:
 source=next(BASELINE.glob(f'*第{v}册*.pptx'));assert SHA(source)==next(x['sha256'] for x in J(R/'logical_inventory.json') if x['volume']==v),'Requires exact prior baseline; cannot run twice on patched PPT'
 dest=R/'draft'/source.name;dest.parent.mkdir(exist_ok=True)
 with zipfile.ZipFile(source) as z:
  original={i.filename:z.read(i.filename) for i in z.infolist()};infos=z.infolist()
 parts=dict(original);extra={};changes=[];added=[];footer_changed=[]
 for r in [q for q in rules if q['volume']==v]:
  name=f'ppt/slides/slide{r["slide"]}.xml';rn=f'ppt/slides/_rels/slide{r["slide"]}.xml.rels';b=parts[name];root=E.fromstring(b);rels=E.fromstring(parts[rn]);ids=m.logical_ids(root);ops=[]
  for op in r['ops']:ops.append(apply(root,rels,op,assets.get(id(op)),extra))
  m.assert_preserved_ids(ids,m.logical_ids(root));bb=m.xml(root);tt=m.timing(b)
  if tt:bb=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:tt,bb,flags=re.S)
  assert m.timing(bb)==tt
  parts[name]=bb;parts[rn]=m.xml(rels);changes.append({'key':r['key'],'original_slide':r['slide'],'ops':ops})

 # New calculation pages are inserted into presentation order, with their own
 # native row-by-row click animation and unchanged source-question conditions.
 pr='http://schemas.openxmlformats.org/package/2006/relationships';ct='http://schemas.openxmlformats.org/package/2006/content-types'
 presentation=E.fromstring(parts['ppt/presentation.xml']);presrels=E.fromstring(parts['ppt/_rels/presentation.xml.rels']);types=E.fromstring(parts['[Content_Types].xml']);lst=presentation.find('p:sldIdLst',m.NS)
 slide_count=len(lst);insertions=[a for a in adds if a['volume']==v]
 relmap={x.get('Target').removeprefix('/ppt/'):x.get('Id') for x in presrels}
 for num,a in enumerate(insertions):
  newpart=slide_count+num+1;anchor=a['after_original_slide'];sourcepart=f'ppt/slides/slide{anchor}.xml';root=E.fromstring(parts[sourcepart]);rels=E.fromstring(parts[f'ppt/slides/_rels/slide{anchor}.xml.rels']);tree=root.find('p:cSld/p:spTree',m.NS)
  for node in list(tree):
   if node.tag in [m.q('p:nvGrpSpPr'),m.q('p:grpSpPr')]:continue
   names=[x.get('name') for x in m.visible_nodes(node)]
   if not any(n in ['title','source','slide_number'] for n in names):tree.remove(node)
  oldtim=root.find('p:timing',m.NS)
  if oldtim is not None:root.remove(oldtim)
  # Remove notes relationships so this is a complete independent slide part.
  for rel in list(rels):
   if rel.get('Type','').endswith('/notesSlide'):rels.remove(rel)
  m.patch_text(root,{'name':'title','text':a['title'],'rect':[64,32,1152,64],'points':32,'color':'000000'})
  m.patch_text(root,{'name':'source','text':f'原书第{a["book_page"]}页　{a["question_id"]}　计算续讲','rect':[64,674,1060,26],'points':14,'color':'555555'})
  caption=placeholder(root,a['key']+'_average_caption');m.patch_text(root,{'name':caption,'text':a['caption'],'rect':[64,124,1152,64],'points':32})
  name=placeholder(root,a['key']+'_average_continued');op={'name':name,'rows':a['rows'],'rect':[64,205,1152,len(a['rows'])*60],'points':32,'first_equals':a.get('first_equals',False)}
  detail=m.patch_rows(root,rels,op,assets[id(a)],extra)
  ans=placeholder(root,a['key']+'_average_conclusion');m.patch_text(root,{'name':ans,'text':a['answer'],'rect':[64,605,1152,58],'points':32})
  clicks=[]
  for i in range(len(a['rows'])):
   names=[name+'_simplify_rhs'+str(i)]
   if i or a.get('first_equals'):names.insert(0,name+'_simplify_equals'+str(i))
   clicks.append({'label':'计算第'+str(i+1)+'步','effects':[{'type':'appear','target':n} for n in names]})
  clicks.append({'label':'结论与答语','effects':[{'type':'appear','target':ans}]})
  TimingBuilder(root,{'clicks':clicks}).add();qa=validate_slide(root,{'clicks':clicks});assert not qa['issues'],qa
  rid='rIdAverageNewSlide'+str(newpart);E.SubElement(presrels,'{'+pr+'}Relationship',Id=rid,Type=m.NS['r']+'/slide',Target=f'slides/slide{newpart}.xml')
  parentrid=relmap[f'slides/slide{anchor}.xml'];prev=next(x for x in lst if x.get(m.q('r:id'))==parentrid);newid=E.Element(m.q('p:sldId'));newid.set('id',str(max(int(x.get('id')) for x in lst)+1));newid.set(m.q('r:id'),rid);lst.insert(lst.index(prev)+1,newid)
  E.SubElement(types,'{'+ct+'}Override',PartName=f'/ppt/slides/slide{newpart}.xml',ContentType='application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
  parts[f'ppt/slides/slide{newpart}.xml']=m.xml(root);parts[f'ppt/slides/_rels/slide{newpart}.xml.rels']=m.xml(rels);added.append({**a,'part_number':newpart,'native_animation_clicks':len(clicks),'details':detail})

 # Update only the small numeric footer of shifted slides. Their original
 # teaching objects, source footer and timing bytes are otherwise unchanged.
 ordmap={r.get('Id'):r.get('Target') for r in presrels};position={int(re.search(r'slide(\d+)\.xml',ordmap[x.get(m.q('r:id'))])[1]):i+1 for i,x in enumerate(lst)}
 for part,pos in position.items():
  name=f'ppt/slides/slide{part}.xml';root=E.fromstring(parts[name]);sp=find_any(root,'slide_number');ts=sp.findall('.//a:t',m.NS);assert len(ts)==1
  if ts[0].text!=str(pos):
   before=parts[name];ts[0].text=str(pos);after=m.xml(root);tt=m.timing(before)
   if tt:after=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:tt,after,flags=re.S)
   parts[name]=after;footer_changed.append({'part_number':part,'slide':pos})
 for change in changes:change['slide']=position[change['original_slide']]
 for a in added:a['slide']=position[a['part_number']]
 if added:
  parts['ppt/presentation.xml']=m.xml(presentation);parts['ppt/_rels/presentation.xml.rels']=m.xml(presrels);parts['[Content_Types].xml']=m.xml(types)
  app=E.fromstring(parts['docProps/app.xml']);node=app.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides')
  if node is not None:node.text=str(len(lst))
  parts['docProps/app.xml']=m.xml(app)
 for name,b in original.items():
  if re.fullmatch(r'ppt/slides/slide\d+\.xml',name):
   assert m.timing(b)==m.timing(parts[name]);m.assert_preserved_ids(m.logical_ids(E.fromstring(b)),m.logical_ids(E.fromstring(parts[name])))
 parts.update(extra)
 with zipfile.ZipFile(dest,'w') as out:
  for info in infos:out.writestr(info,parts.pop(info.filename))
  for n,b in parts.items():out.writestr(n,b,compress_type=zipfile.ZIP_DEFLATED)
 reports.append({'volume':v,'source':str(source),'output':str(dest),'source_sha256':SHA(source),'output_sha256':SHA(dest),'total_slides':len(lst),'original_slides':slide_count,'changed_slides':[c['slide'] for c in changes],'changed_original_slides':[c['original_slide'] for c in changes],'added_slides':added,'changes':changes,'position_by_original_part':position,'footer_updates':footer_changed,'all_original_timing_xml_bytes_unchanged':True,'all_original_shape_ids_names_order_preserved':True})
W(R/'draft/qa_package.json',reports)
W(R/'used_formula_assets.json',[{k:str(a[k]) for k in ['key','stem','tex','source','pdf','svg','png']} for a in used.values()])
print(json.dumps([{'volume':r['volume'],'slides':r['total_slides'],'changed':r['changed_slides'],'added':[a['slide'] for a in r['added_slides']]} for r in reports],ensure_ascii=False),flush=True)
