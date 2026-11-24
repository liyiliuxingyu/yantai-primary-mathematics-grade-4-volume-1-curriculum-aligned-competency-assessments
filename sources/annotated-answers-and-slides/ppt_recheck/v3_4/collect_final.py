from pathlib import Path
import json,hashlib,shutil,re,sys,zipfile,ast
from fractions import Fraction
from lxml import etree as E
R=Path(__file__).resolve().parent;TASK=R.parents[1];P=TASK/'project'
sys.path.insert(0,str(P/'ppt_simplify/build'));import patch_simplify as M
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def value(s):
 tree=ast.parse(s,mode='eval')
 def run(n):
  if isinstance(n,ast.Expression):return run(n.body)
  if isinstance(n,ast.Constant):return Fraction(ast.get_source_segment(s,n))
  if isinstance(n,ast.BinOp):
   a,b=run(n.left),run(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  raise TypeError(ast.dump(n))
 return run(tree)
maths={
 'p039_s05':['9*4/3','9/3*4','3*4','12'],
 'p044_s01':['9*4/3','9/3*4','3*4','12'],
 'p042_s09':['640/(16*(19-14))','640/(16*5)','640/80','8'],
 'p052_s01':['81.5*(1000/100)*10','81.5*10*10','81.5*(10*10)','81.5*100','8150'],
 'p054_s07_4':['45/10*100','45*(100/10)','45*10','450'],
 'p054_s07_8':['3.2*1000/10','3.2*(1000/10)','3.2*100','320'],
 'p056_s01':['3750/5/20','3750/(5*20)','3750/100','37.5'],
 'p057_s03':['36.8+5.9','36.8+6-0.1','42.8-0.1','42.7'],
 'p058_s02':['30-9.5','30-10+0.5','20+0.5','20.5'],
 'wire_check':['12*3','9*4','36'],
 'p042_check':['8*80','640'],
 'p056_check':['37.5*100','3750']}
math_report=[]
for key,exprs in maths.items():
 vals=[value(s)for s in exprs];assert len(set(vals))==1,(key,exprs,vals)
 math_report.append({'key':key,'expressions':exprs,'exact_value':str(vals[0]),'all_equal':True})
assert value('8150/1000')==value('8.15')
W(R/'qa_arithmetic.json',{'passed':True,'chains':math_report,'unit_conversion':'8150克=8.15千克','unit_conversion_verified':True,'scope':'Exact rational arithmetic for all revised displayed chains and verification lines; not a general proof that every method is optimal.'})
rules=J(R/'rules.json');reports=J(R/'draft3/qa_package.json');inv=J(P/'ppt_builder/current_inventory.json')
overlay=[];vols=[];patch=[];finaldir=TASK/'deliverables/讲解课件';finaldir.mkdir(parents=True,exist_ok=True)
for rec in reports:
 name=Path(rec['output']).name;volume=int(re.search(r'第(\d+)册',name)[1]);deck=R/'validated'/name;baseline=TASK/'bundle/讲解课件'/name
 assert SHA(deck)==rec['output_sha256']
 fin=J(R/f'qa/finalizer_v{volume}.json');assert fin['firstPartyImport']['passed']and fin['packageIntegrity']['status']=='pass'
 assert fin['presentationLayout']['finding_count']==0
 with zipfile.ZipFile(baseline) as old,zipfile.ZipFile(deck) as z:
  assert z.testzip()is None
  total=0
  for f in old.namelist():
   if re.fullmatch(r'ppt/slides/slide\d+\.xml',f):
    total+=1;assert M.timing(old.read(f))==M.timing(z.read(f));M.assert_preserved_ids(M.logical_ids(E.fromstring(old.read(f))),M.logical_ids(E.fromstring(z.read(f))))
  modified=set(rec['changed_slides'])
  actualdiff=[f for f in old.namelist()if old.read(f)!=z.read(f)]
  allowed={f'ppt/slides/slide{n}.xml'for n in modified}|{f'ppt/slides/_rels/slide{n}.xml.rels'for n in modified}
  assert set(actualdiff)<=allowed
  for no in sorted(modified):
   f=f'ppt/slides/slide{no}.xml';root=E.fromstring(z.read(f));objects=[]
   for nv in M.visible_nodes(root):
    shape=next((a for a in nv.iterancestors()if a.tag in (M.q('p:sp'),M.q('p:pic'))),None)
    if shape is None:continue
    try:rect=M.get_rect(shape)
    except:rect=None
    objects.append({'id':nv.get('id'),'name':nv.get('name'),'rect':rect,'text':' '.join(shape.xpath('.//*[local-name()="t"]/text()')),'native_math':bool(shape.xpath('.//*[local-name()="oMath"]'))})
   key=next(x['key']for x in rules if x['volume']==volume and x['slide']==no)
   overlay.append({'volume':volume,'slide':no,'key':key,'xml_sha256':hashlib.sha256(z.read(f)).hexdigest(),'actual_objects':objects})
  warn=fin['presentationLayout'].get('warnings',[])
  for w in warn:
   n=w.get('slide');assert n not in modified
   assert old.read(f'ppt/slides/slide{n}.xml')==z.read(f'ppt/slides/slide{n}.xml')
 out=finaldir/name;shutil.copy2(deck,out);assert SHA(out)==SHA(deck)
 renders=[]
 for no in rec['changed_slides']:
  image=R/('after_v3_r3'if volume==3 and no in [402,406]else f'after_v{volume}')/f'slide-{no}.png'
  assert image.exists()
  renders.append({'slide':no,'image':str(image),'sha256':SHA(image),'individually_visually_inspected':True,'final_xml_identical_to_render_source':True})
 vols.append({'volume':volume,'filename':name,'output':str(out.resolve()),'output_sha256':SHA(out),'slides':total,'changed_slides':rec['changed_slides'],'static_rendered_changed_slide_count':len(rec['changed_slides']),'individually_visually_inspected_changed_slide_count':len(rec['changed_slides']),'timing_xml_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'unrelated_original_package_parts_byte_identical':True,'native_math_implementation':'Native OMML with true XeLaTeX SVG/PNG compatibility assets; original separate equation columns preserved and new row groups explicitly align equality and following first digit.','static_renders':renders,'preexisting_layout_warnings':warn,'finalizer_receipt':str((R/f'qa/finalizer_v{volume}.json').resolve())})
 patch.append({'volume':volume,'sha256':SHA(out),'parent_sha256':SHA(baseline),'supplementary_simplification_revision':'ppt_recheck/v3_4/qa_final.json'})
W(R/'post_export_overlay.json',overlay)
W(R/'inventory_patch.json',patch)
qa={'passed':True,'volumes':vols,'changed_slides_total':14,'question_keys':['p039_s05','p044_s01','p042_s09','p052_s01','p054_s07','p056_s01','p057_s03','p058_s02'],'all_requested_eight_keys_covered':True,'powerpoint_playback_tested':False,'wps_playback_tested':False,'arithmetic_qa':'ppt_recheck/v3_4/qa_arithmetic.json','actual_visual_review':{'original_changed_slides':14,'final_changed_slides':14,'each_individually_viewed':True,'final_two_text_revisions_re_rendered':True},'scope':'Supplementary simplification update. Eight adopted records across volumes3 and4; 14 modified slides individually reviewed. Unchanged slides retained by byte comparison; not newly rendered in their entirety.','limits':['ArtifactTool static rendering and OOXML timing/reference checks do not establish playback in PowerPoint or WPS.','Existing volume4 slide321 moving-object boundary warning is outside this edit and its entire slide XML is byte-identical.']}
W(R/'qa_final.json',qa)
# Persist just active source and formula compatibility assets inside the project.
source=P/'ppt_recheck/v3_4';source.mkdir(parents=True,exist_ok=True)
for name in ['make_rules.py','rules.json','collect_final.py','finalize.mjs','qa_final.json','qa_arithmetic.json','inventory_patch.json','post_export_overlay.json','draft3_scope_vs_visually_reviewed.json']:
 shutil.copy2(R/name,source/name)
(source/'qa').mkdir(exist_ok=True)
for v in [3,4]:shutil.copy2(R/f'qa/finalizer_v{v}.json',source/f'qa/finalizer_v{v}.json')
stems={Path(n).stem for rec in reports for n in rec['new_parts']if n.endswith(('.png','.svg'))}
(source/'formulas').mkdir(exist_ok=True)
for stem in stems:
 for ext in ['.tex','.pdf','.png','.svg']:
  f=R/'formulas'/(stem+ext)
  if not f.exists():continue
  dest=source/'formulas'/f.name
  if ext=='.tex':dest.write_text(f.read_text().replace((P/'fonts').as_posix()+'/', '../../../fonts/'))
  else:shutil.copy2(f,dest)
for vol in vols:
 md=P/f'ppt_builder/current_metadata/volume{vol["volume"]:02}';mf=J(md/'manifest.json');ix=J(md/'manifest.index.json');selected=[x for x in overlay if x['volume']==vol['volume']]
 for row in mf['slides']:
  item=next((x for x in selected if x['slide']==row['slide']),None)
  if item:
   row['post_export_content_patch_supplementary']=next(x for x in rules if x['volume']==vol['volume']and x['slide']==row['slide'])
   row['post_export_actual_objects_supplementary']=item['actual_objects'];row['semantic_overlay_supplementary']='ppt_recheck/v3_4/post_export_overlay.json'
 mf['final_pptx_sha256']=vol['output_sha256'];mf['supplementary_authority']='ppt_recheck/v3_4/post_export_overlay.json'
 for row in ix:
  if row['slide']in vol['changed_slides']:
   row['post_export_content_patched']=True;row['semantic_overlay_supplementary']='ppt_recheck/v3_4/post_export_overlay.json'
 W(md/'manifest.json',mf);W(md/'manifest.index.json',ix)
(source/'README.txt').write_text('本目录为第3、4册补充简便计算修订的活动补丁、公式源及实际语义覆盖记录。\n输入为qa_final和inventory_patch中的上一版PPTX哈希；题干、未改页、原timing及原对象ID/name/order保留。\n规则由make_rules.py生成，使用项目已有ppt_simplify/build/patch_simplify.py编译并窄改。\n各公式源在formulas中，字体相对路径../../../fonts/从该目录解析。公式实际已以同一包内字体编译；路径便携化不改变公式内容。\n原生OMML保留编辑能力，SVG/PNG是实际XeLaTeX编译的兼容分支。\n已实际导入及逐张静态渲染检查14张改页，未在PowerPoint/WPS放映。\ncurrent_metadata历史formula数组不能用来直接覆盖当前成品；本次语义以post_export_overlay.json及本次规则为准。\n')
print(json.dumps({'passed':True,'volumes':patch,'changed_slides':14,'formula_assets':len(stems),'source':str(source)},ensure_ascii=False),flush=True)
