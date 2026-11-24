from pathlib import Path
import json,zipfile,re,sys,hashlib,shutil,ast
from fractions import Fraction
from lxml import etree as E
HERE=Path(__file__).resolve().parent
PROJECT=next(q for p in HERE.parents for q in (p,p/'project') if (q/'ppt_builder').is_dir())
ROOT=next(p for p in HERE.parents if (p/'bundle/讲解课件').is_dir());WORK=HERE.parent
sys.path.insert(0,str(PROJECT/'simplify_update/ppt_1_2/build'));import common_patch as C
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,j):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
rules=J(WORK/'rules_v1.json');changed=sorted(s['slide'] for s in rules)
source=next((ROOT/'bundle/讲解课件').glob('*第1册*.pptx'));final=WORK/'validated'/source.name;candidate=WORK/'draft2'/source.name
receipt=J(WORK/'qa/finalizer_v1.json')
assert receipt['packageIntegrity']['status']=='pass' and not receipt['presentationLayout']['finding_count']
assert receipt['firstPartyImport']['passed'] and receipt['fontSelection']['passed']
assert SHA(final)==SHA(candidate)==receipt['finalSha256']
overlays=[];native_before=0;native_after=0;unrelated=0;click_groups={}
with zipfile.ZipFile(source) as a,zipfile.ZipFile(final) as z:
 assert z.testzip() is None
 allowed={f'ppt/slides/slide{s}.xml' for s in changed}|{f'ppt/slides/_rels/slide{s}.xml.rels' for s in changed}
 for name in a.namelist():
  old=a.read(name);now=z.read(name)
  if name not in allowed:assert old==now,name;unrelated+=1
  if re.fullmatch(r'ppt/slides/slide\d+\.xml',name):
   before=E.fromstring(old);after=E.fromstring(now)
   assert C.timing(old)==C.timing(now);C.assert_preserved_ids(C.logical_ids(before),C.logical_ids(after))
   native_before+=len(before.findall('.//m:oMath',C.NS));native_after+=len(after.findall('.//m:oMath',C.NS))
 manifest_path=PROJECT/'ppt_builder/current_metadata/volume01/manifest.json';manifest=J(manifest_path);assetfolder=manifest_path.parent/'recheck_assets';assetfolder.mkdir(exist_ok=True)
 for s in manifest['slides']:
  if s['slide'] not in changed:continue
  no=s['slide'];b=z.read(f'ppt/slides/slide{no}.xml');root=E.fromstring(b);rels=E.fromstring(z.read(f'ppt/slides/_rels/slide{no}.xml.rels'));relmap={r.get('Id'):r.get('Target') for r in rels};formulas=[];bindings=[];vectors=[];text=[]
  for nv in C.visible_nodes(root):
   shape=next((p for p in nv.iterancestors() if p.tag in (C.q('p:sp'),C.q('p:pic'))),None)
   if shape is None:continue
   name=nv.get('name');ms=shape.findall('.//a14:m',C.NS);plain=''.join(shape.xpath('.//*[local-name()="t"]/text()'))
   try:rect=C.get_rect(shape)
   except:continue
   text.append({'id':nv.get('id'),'name':name,'text':plain,'rect':rect,'native_math':bool(ms)})
   if not ms:continue
   assert len(ms)==1
   m=ms[0];assert not m.findall('.//m:f',C.NS) and not m.findall('.//m:m',C.NS)
   expr=''.join(t.text or '' for t in m.findall('.//m:t',C.NS));rp=m.find('.//a:rPr',C.NS)
   points=float(rp.get('sz','3200'))/100 if rp is not None else 32
   col=rp.find('a:solidFill/a:srgbClr',C.NS) if rp is not None else None;color=col.get('val') if col is not None else 'C00000'
   formulas.append({'target':name,'ast':{'t':'text','v':expr},'color':color,'points':points,'font':'Droid Sans Fallback'})
   bindings.append({'name':name,'rect':dict(zip(('left','top','width','height'),rect))})
   outer=C.container(shape);fallback=outer.find('mc:Fallback',C.NS)
   if fallback is not None:
    svg=fallback.find('.//{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip')
    if svg is not None:
     rid=svg.get(C.q('r:embed'));target=relmap[rid];path=target.lstrip('/') if target.startswith('/') else 'ppt/'+target.replace('../','');content=z.read(path);stem=hashlib.sha256(content).hexdigest()[:24]+'.svg';(assetfolder/stem).write_bytes(content)
     vectors.append({'target':name,'svg_path':f'ppt_builder/current_metadata/volume01/recheck_assets/{stem}'})
  s['formulas']=formulas;s['bindings']=bindings;s['vectors']=vectors
  s['arithmetic_recheck_revision']={'actual_native_omml_synced':True,'source_pptx_sha256':SHA(final),'overlay':'ppt_recheck/v1_2/post_export_overlay_v1.json'}
  overlays.append({'volume':1,'slide':no,'record_key':s['record_key'],'output_pptx_sha256':SHA(final),'slide_xml_sha256':hashlib.sha256(b).hexdigest(),'actual_objects':text})
  # Original click effects in 120 group the three replaced obsolete runs
  # with the meaningful new title and formula; no new empty click is added.
  if no==120:
   for n in root.findall('.//p:spTgt',C.NS):
    ctn=next(a for a in n.iterancestors() if a.tag==C.q('p:cTn'))
    click_groups[n.get('spid')]=ctn.get('id')
 manifest['arithmetic_recheck_revision']={'changed_slides':changed,'source_pptx_sha256':SHA(final),'formula_arrays_from_actual_native_omml':True,'overlay':'ppt_recheck/v1_2/post_export_overlay_v1.json'}
 if 'final_pptx_sha256' in manifest:manifest['final_pptx_sha256']=SHA(final)
 W(manifest_path,manifest)
 indexpath=manifest_path.with_name('manifest.index.json');index=J(indexpath)
 for row in index:
  if row['slide'] in changed:row['arithmetic_recheck_content_patch']='ppt_recheck/v1_2/post_export_overlay_v1.json'
 W(indexpath,index)
W(WORK/'post_export_overlay_v1.json',overlays)
def exact(tex):
 s=re.sub(r'\\text\{[^}]*\}','',tex).replace(r'\times','*').replace(r'\div','/').replace('{','(').replace('}',')')
 def go(n):
  if isinstance(n,ast.Expression):return go(n.body)
  if isinstance(n,ast.Constant):return Fraction(n.value)
  if isinstance(n,ast.BinOp):
   a,b=go(n.left),go(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  raise ValueError(ast.dump(n))
 return go(ast.parse(s,mode='eval'))
math_checks=[]
for s in rules:
 for op in s['ops']:
  if op['type'] not in ('math','note'):continue
  rows=op.get('rows') or [op['tex']];vals=[exact(x) for x in rows]
  assert len(set(vals))==1,(s['key'],rows,vals)
  math_checks.append({'key':s['key'],'slide':s['slide'],'rows':rows,'values':[str(v) for v in vals],'equal':True})
W(WORK/'qa_math_v1.json',{'passed':True,'exact_fraction_arithmetic':True,'checks':math_checks})
dest=ROOT/'deliverables/讲解课件'/source.name;dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(final,dest);assert SHA(dest)==SHA(final)
qa={'passed':True,'volumes':[{'volume':1,'output':str(dest.resolve()),'output_sha256':SHA(dest),'parent_sha256':SHA(source),'slides':426,'changed_slides':changed,'static_rendered_changed_slide_count':len(changed),'human_inspected_changed_slide_count':len(changed),'all_original_timing_xml_bytes_unchanged':True,'all_original_ids_names_order_preserved':True,'native_math_count_before':native_before,'native_math_count_after':native_after,'unrelated_zip_parts_byte_identical':unrelated,'package_finalizer':'qa/finalizer_v1.json','artifacttool_import_passed':True,'package_finalizer_passed':True}],'powerpoint_playback_tested':False,'wps_playback_tested':False,'actual_visual_review':{'before':'before_v1','final_render_source':'draft2','after':'after2_v1','slides':changed,'each_final_modified_slide_individually_viewed':True,'retained_methods':True,'original_trees_unchanged':True},'mathematics':'qa_math_v1.json','native_formula_implementation':'New calculations are real native OMML plus actual XeLaTeX SVG/PNG fallbacks. Equals and following expressions have explicit columns. Original early primary methods remain. p003_s07 optimizes only its second quantity analysis; p011_s08 is labelled an arithmetic-law oral-calculation hint, not a typical round-number shortcut.','obsolete_runs':'On slide120 three obsolete run objects remain as empty 1px animation anchors. They share the same original clickEffect with the meaningful new hint title/formulas, so there is no additional empty click.','click_group_evidence_slide120':click_groups,'limits':['Actual final-render PNGs were inspected in ArtifactTool, not in PowerPoint or WPS.','Untouched slides were verified by unchanged ZIP content and timing; they were not all visually rereviewed this round.']}
W(WORK/'qa_v1.json',qa)
W(WORK/'inventory_patch_v1.json',[{'volume':1,'sha256':SHA(dest),'parent_sha256':SHA(source),'arithmetic_recheck_revision':'ppt_recheck/v1_2/qa_final.json'}])
print(json.dumps({'output':str(dest),'sha256':SHA(dest),'changed_slides':changed,'native_math_added':native_after-native_before},ensure_ascii=False))
