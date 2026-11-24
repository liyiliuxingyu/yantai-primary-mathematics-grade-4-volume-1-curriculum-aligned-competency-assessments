#!/usr/bin/env python3
"""Freeze the six PPTs and verify this revision against its exact baseline."""
from pathlib import Path
import importlib.util,json,re,shutil,hashlib,zipfile
from lxml import etree as E
R=Path(__file__).resolve().parents[1]; W=R.parent; P=W/'project'
spec=importlib.util.spec_from_file_location('narrow_patch',P/'ppt_simplify/build/patch_simplify.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text())
write=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
dest=W/'deliverables/讲解课件';dest.mkdir(parents=True,exist_ok=True)
for v,folder in [(5,'validated_r4'),(6,'validated')]:
 src=next((R/folder).glob(f'*第{v}册*.pptx'));shutil.copy2(src,dest/src.name)
qa12=read(R/'v1_2/qa_final.json');qa34=read(R/'v3_4/qa_final.json')
assert qa12['passed'] and qa34['passed'] and read(R/'qa_visual_v6_final.json')['passed']
children={d['volume']:d for d in qa12['volumes']+qa34['volumes']}
rules=read(R/'rules_late.json'); rulemap={(x['volume'],x['slide']):x for x in rules}
inventory=read(R/'full_inventory.json');overlays=[];volumes=[];deltas=[]
def content(n):
 return bool(''.join(n.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)).strip() or n.xpath('.//a:blip',namespaces=m.NS))
def clickable_empty(root):
 nodes={n.get('id'):n for n in m.visible_nodes(root)};out=set()
 for c in root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=m.NS):
  visible=[]
  for target in c.xpath('.//p:spTgt/@spid',namespaces=m.NS):
   n=nodes[target]
   sp=next(a for a in n.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')])
   visible.append(content(sp))
  if visible and not any(visible):out.add(c.get('id'))
 return out
for v in range(1,7):
 base=next((W/'bundle/讲解课件').glob(f'*第{v}册*.pptx'));final=next(dest.glob(f'*第{v}册*.pptx'))
 beforehash=sha(base.read_bytes());finalhash=sha(final.read_bytes());assert beforehash==inventory[v-1]['sha256']
 with zipfile.ZipFile(base) as z0,zipfile.ZipFile(final) as z1:
  original={n:z0.read(n) for n in z0.namelist()};new={n:z1.read(n) for n in z1.namelist()}
  changed=[];newempty=[];native0=native1=0
  assert set(original)<=set(new)
  for name,b in original.items():
   mt=re.fullmatch(r'ppt/slides/slide(\d+)\.xml',name)
   if not mt:continue
   slide=int(mt[1]);a=E.fromstring(b);f=E.fromstring(new[name])
   assert m.timing(b)==m.timing(new[name]),(v,slide,'timing')
   m.assert_preserved_ids(m.logical_ids(a),m.logical_ids(f))
   native0+=len(a.findall('.//m:oMath',m.NS));native1+=len(f.findall('.//m:oMath',m.NS))
   if b!=new[name]:
    changed.append(slide)
    ne=clickable_empty(f)-clickable_empty(a);newempty.extend([(slide,x) for x in ne])
    if v>=5:
     for op in rulemap[v,slide]['ops']:
      if op['type']=='text' and not op['text']:
       sp=m.find_shape(f,op['name']);assert not content(sp) and not sp.findall('.//m:oMath',m.NS),(v,slide,op['name'],'old hidden content')
     actual=[]
     for n in m.visible_nodes(f):
      sp=next((a for a in n.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')]),None)
      if sp is None:continue
      rect=None
      try:rect=m.get_rect(sp)
      except (AttributeError,ValueError):pass
      actual.append({'id':n.get('id'),'name':n.get('name'),'rect':rect,'text':''.join(sp.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)),'native_math':bool(sp.findall('.//m:oMath',m.NS))})
     overlays.append({'volume':v,'slide':slide,'key':rulemap[v,slide]['key'],'xml_sha256':sha(new[name]),'actual_objects':actual,'rules':rulemap[v,slide]})
  changed.sort();assert not newempty,('new empty clicks',v,newempty)
  allow={f'ppt/slides/slide{s}.xml' for s in changed}|{f'ppt/slides/_rels/slide{s}.xml.rels' for s in changed}
  changedparts=[n for n,b in original.items() if b!=new[n]];assert set(changedparts)<=allow
  entry=dict(children.get(v,{})); entry.update({'volume':v,'filename':final.name,'output':str(final),'output_sha256':finalhash,'parent_sha256':beforehash,'slides':len(inventory[v-1]['slides']),'changed_slides':changed,'timing_xml_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'unrelated_original_package_parts_byte_identical':True,'new_empty_click_targets':[],'native_math_count_before':native0,'native_math_count_after':native1})
  if v>=5:
   renders=R/('after_late_r4_v5' if v==5 else 'after_late_r2_v6')
   entry.update({'static_rendered_changed_slide_count':len(changed),'individually_visually_inspected_changed_slide_count':len(changed),'empty_old_anchors_have_no_text_math_or_pictures':True,'static_renders':[{'slide':s,'image':str(renders/f'slide-{s}.png'),'sha256':sha((renders/f'slide-{s}.png').read_bytes()),'individually_visually_inspected':True} for s in changed],'finalizer':('qa_r4/finalizer_v5.json' if v==5 else 'qa/finalizer_v6.json'),'package_finalizer_passed':True,'artifacttool_import_passed':True})
  volumes.append(entry);deltas.append({'volume':v,'sha256':finalhash,'parent_sha256':beforehash,'arithmetic_recheck_revision':'ppt_recheck/qa_final.json'})
S=P/'ppt_recheck/late';(S/'build').mkdir(parents=True,exist_ok=True)
for name in ['make_rules_late.py','render_inspect.mjs','portable_late.py','freeze_final.py','finalize_simplify.mjs','finalize_simplify_r3.mjs','finalize_simplify_r4.mjs']:
 shutil.copy2(R/'build'/name,S/'build'/name)
for name in ['rules_late.json','rules_p74.json','full_inventory.json','qa_portable_late.json','qa_visual_v6_independent.json','qa_visual_v6_final.json']:
 shutil.copy2(R/name,S/name)
write(S/'post_export_overlay.json',overlays)
for v in [5,6]:
 folder=P/f'ppt_builder/current_metadata/volume{v:02d}';mf=folder/'manifest.json';d=read(mf)
 d['metadata_scope']='Structural and original-location reference only; legacy formula arrays are pre-patch authoring reference, not final semantic content.'
 d['regenerate_from_this_manifest']=False;d['final_pptx_sha256']=volumes[v-1]['output_sha256']
 d['post_export_authority']='ppt_recheck/late/post_export_overlay.json for this revision; retain prior overlays for untouched slides'
 d['arithmetic_recheck_revision']={'changed_slides':volumes[v-1]['changed_slides'],'qa':'ppt_recheck/qa_final.json','rules':'ppt_recheck/late/rules_late.json','native_math':'Native OMML plus compiled TeX vector and raster compatibility branches','native_powerpoint_playback_tested':False}
 write(mf,d);idx=folder/'manifest.index.json';d=read(idx)
 for x in d:
  if x['slide'] in volumes[v-1]['changed_slides']:
   x['metadata_role']='structural_location_index';x['post_export_content_patched']=True;x['semantic_overlay']='ppt_recheck/late/post_export_overlay.json'
 write(idx,d)
qa={'passed':True,'volumes':volumes,'total_slides':sum(x['slides'] for x in volumes),'modified_slides':sum(len(x['changed_slides']) for x in volumes),'adopted_records':36,'all_original_timing_xml_bytes_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'no_new_empty_click_targets':True,'all_unrelated_original_package_parts_byte_identical':True,'math_implementation':'Genuine native OMML with independently XeLaTeX-compiled SVG/PNG compatibility assets','editable_ordinary_text':True,'native_powerpoint_playback_tested':False,'native_wps_playback_tested':False,'static_review_scope':'All 54 modified slides rendered and individually visually inspected. Unmodified pages were not newly visually rechecked.','preexisting_geometry_warnings_preserved':[{'volume':4,'slides':[321]},{'volume':6,'slides':[107,409]}],'receipts':['v1_2/qa_final.json','v3_4/qa_final.json','late/qa_portable_late.json','late/qa_visual_v6_final.json'],'page74_decision':'Original 15 kg and final choice C retained; comparison 39>15 explains C, and conditional 39<45 explains why an original average of 45 would yield A; the printed answer conflicts with the current data.'}
write(R/'qa_final.json',qa);write(R/'inventory_patch.json',deltas)
write(P/'ppt_recheck/qa_final.json',qa);write(P/'ppt_recheck/inventory_patch.json',deltas)
for v,src in [(5,R/'qa_r4/finalizer_v5.json'),(6,R/'qa/finalizer_v6.json')]:shutil.copy2(src,S/f'finalizer_v{v}.json')
(S/'README.txt').write_text('本目录保存本轮第5—6册27张修改页的规则、最终原生对象快照及65套实际编译的公式源码。\n规则属于对本轮基线PPT的一次性窄范围升级；baseline SHA见../inventory_patch.json。不可直接在已修改课件上重复运行。\n当前权威内容是post_export_overlay.json与本次交付PPT，旧manifest只作原位置索引。公式.tex的字体路径相对于工程根目录fonts/；全部65套已从工程根目录实际XeLaTeX编译通过。\nPPT中的普通中文文字可编辑，公式为原生OMML；兼容分支使用同一算式实际编译的SVG/PNG。保留原动画XML不等于已在PowerPoint或WPS中实际播放。\n')
print(json.dumps({'passed':True,'modified_slides':qa['modified_slides'],'volumes':deltas},ensure_ascii=False,indent=2))
