from pathlib import Path
import sys,json,re,shutil,hashlib,zipfile,csv,copy,importlib.util
from lxml import etree as E
R=Path(__file__).resolve().parents[1];W=R.parent;P=W/'project';D=P/'ppt_average';D.mkdir(exist_ok=True)
sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
spec=importlib.util.spec_from_file_location('native_patch',R/'build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
J=lambda p:json.loads(p.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
def put(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def content(sp):return bool(''.join(sp.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)).strip() or sp.xpath('.//a:blip',namespaces=m.NS))
def empties(root):
 nodes={x.get('id'):x for x in m.visible_nodes(root)};out=[]
 for c in root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=m.NS):
  values=[]
  for target in c.xpath('.//p:spTgt/@spid',namespaces=m.NS):
   assert target in nodes
   sp=next((a for a in nodes[target].iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp'),m.q('p:graphicFrame'),m.q('p:cxnSp')]),None)
   if sp is not None:values.append(content(sp) or sp.tag==m.q('p:cxnSp'))
  if values and not any(values):out.append(c.get('id'))
 return out
def objects(root):
 out=[]
 for n in m.visible_nodes(root):
  sp=next((a for a in n.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')]),None)
  if sp is None:continue
  try:rect=m.get_rect(sp)
  except (AttributeError,ValueError):rect=None
  out.append({'id':n.get('id'),'name':n.get('name'),'rect':rect,'text':''.join(sp.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)),'native_math':bool(sp.findall('.//m:oMath',m.NS)),'group':sp.tag==m.q('p:grpSp')})
 return out
reports=J(R/'draft/qa_package.json');rules=J(R/'rules.json');overlays=[];volumes=[];deltas=[];indices={}
assert J(R/'qa_math_rows.json')['passed'] and J(R/'qa_portable.json')['passed']
deliver=W/'deliverables/讲解课件';deliver.mkdir(parents=True,exist_ok=True)
for v in range(1,7):
 base=next((W/'bundle/讲解课件').glob(f'*第{v}册*.pptx'))
 if v<5:shutil.copy2(base,deliver/base.name);continue
 report=next(x for x in reports if x['volume']==v);final=R/'validated_r3'/base.name;receipt=J(R/f'qa_r3/finalizer_v{v}.json');assert receipt['finalSha256']==sha(final.read_bytes())==sha((R/'draft'/base.name).read_bytes())
 assert receipt['packageIntegrity']['status']=='pass' and receipt['firstPartyImport']['passed'] and not receipt['presentationLayout']['findings']
 imp=J(R/f'after_v{v}/qa_import.json');assert imp['import_succeeded'] and imp['slides']==report['total_slides']
 contentparts=set(report['changed_original_slides']);newparts={a['part_number'] for a in report['added_slides']};position={int(k):n for k,n in report['position_by_original_part'].items()}
 with zipfile.ZipFile(base) as z0,zipfile.ZipFile(final) as z1:
  old={n:z0.read(n) for n in z0.namelist()};new={n:z1.read(n) for n in z1.namelist()};assert set(old)<=set(new)
  footers={x['part_number'] for x in report['footer_updates']};changed=[];native0=native1=0
  for name,b in old.items():
   mt=re.fullmatch(r'ppt/slides/slide(\d+)\.xml',name)
   if not mt:continue
   part=int(mt[1]);a=E.fromstring(b);f=E.fromstring(new[name]);assert m.timing(b)==m.timing(new[name]);m.assert_preserved_ids(m.logical_ids(a),m.logical_ids(f));assert not set(empties(f))-set(empties(a)),(v,part,'empty click')
   native0+=len(a.findall('.//m:oMath',m.NS));native1+=len(f.findall('.//m:oMath',m.NS))
   if b!=new[name]:changed.append(part)
   if part not in contentparts:
    # Any permitted difference here must be only the numeric page footer.
    for root in [a,f]:
     nv=next(n for n in m.visible_nodes(root) if n.get('name')=='slide_number');sp=next(x for x in nv.iterancestors() if x.tag==m.q('p:sp'));sp.find('.//a:t',m.NS).text='FOOTER'
    assert E.tostring(a)==E.tostring(f),(v,part,'unrelated content')
  for part in sorted(contentparts|newparts):
   root=E.fromstring(new[f'ppt/slides/slide{part}.xml']);pos=position[part];assert pos in imp['rendered'];assert (R/f'after_v{v}/slide-{pos}.png').exists()
   key=next(o['name'][:8] for o in objects(root) if re.match(r'p\d{3}_s\d{2}',o['name']))
   overlays.append({'volume':v,'slide':pos,'part_number':part,'record_key':key,'xml_sha256':sha(new[f'ppt/slides/slide{part}.xml']),'actual_objects':objects(root),'is_new_calculation_slide':part in newparts})
  for a in report['added_slides']:
   root=E.fromstring(new[f'ppt/slides/slide{a["part_number"]}.xml']);assert len(root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=m.NS))==a['native_animation_clicks'];assert not empties(root)
  changedparts=[n for n,b in old.items() if b!=new[n]]
  allowed={f'ppt/slides/slide{p}.xml' for p in set(changed)}|{f'ppt/slides/_rels/slide{p}.xml.rels' for p in contentparts}
  if newparts:allowed|={'ppt/presentation.xml','ppt/_rels/presentation.xml.rels','[Content_Types].xml','docProps/app.xml'}
  assert set(changedparts)<=allowed,(v,set(changedparts)-allowed)
 # Update every shifted structural location, and the semantic content only
 # where this task modified a teaching calculation.
 folder=P/f'ppt_builder/current_metadata/volume{v:02d}';mf=J(folder/'manifest.json');idx=J(folder/'manifest.index.json');oldindex=copy.deepcopy(idx);byold={x['slide']:x for x in mf['slides']};ixold={x['slide']:x for x in idx}
 for x in mf['slides']:x['original_part_number']=x['slide'];x['slide']=position[x['slide']]
 for x in idx:x['original_part_number']=x['slide'];x['slide']=position[x['slide']]
 for overlay in [x for x in overlays if x['volume']==v]:
  part=overlay['part_number'];pos=overlay['slide'];ob=overlay['actual_objects']
  if part in newparts:
   a=next(x for x in report['added_slides'] if x['part_number']==part);prior=next(x for x in oldindex if x['record_key']==a['key']);entry={**copy.deepcopy(prior),'slide':pos,'original_part_number':part,'continuation':'新增计算续讲','click_count':a['native_animation_clicks'],'calculation_continuation':True,'semantic_overlay':'ppt_average/post_export_overlay.json'};idx.append(entry)
   slide={'slide':pos,'record_key':a['key'],'book_page':a['book_page'],'source_page':prior['source_page'],'input_pdf_page':prior.get('input_pdf_page'),'continuation':'新增计算续讲','bindings':[],'formulas':[],'vectors':[],'tables':[],'clicks':[],'answer_slots':[],'table_answers':[]};mf['slides'].append(slide)
  else:slide=byold[part]
  slide['bindings']=[{'name':o['name'],'rect':dict(zip(['left','top','width','height'],o['rect']))} for o in ob if o['rect']]
  slide['formulas']=[{'target':o['name'],'ast':{'t':'text','v':o['text']},'points':32,'color':'C00000','font':'Droid Sans Fallback','implementation':'native OMML in delivered PPTX'} for o in ob if o['native_math'] and not o['group']]
  slide['post_export_semantic_overlay']='ppt_average/post_export_overlay.json';slide['native_omml_source']='actual_objects within overlay, authoritative current content'
  for x in idx:
   if x['slide']==pos:x['metadata_role']='structural_location_index';x['post_export_content_patched']=True;x['semantic_overlay']='ppt_average/post_export_overlay.json'
 mf['slides'].sort(key=lambda x:x['slide']);idx.sort(key=lambda x:x['slide']);assert [x['slide'] for x in idx]==list(range(1,report['total_slides']+1))
 mf['final_pptx_sha256']=sha(final.read_bytes());mf['post_export_authority']='ppt_average/post_export_overlay.json for this revision; previous overlays remain historical and apply by original part number, not shifted UI slide position';mf['average_revision']={'qa':'ppt_average/qa_final.json','original_part_to_current_slide':position,'new_slides':[{'slide':a['slide'],'key':a['key']} for a in report['added_slides']]};mf['regenerate_from_this_manifest']=False
 put(folder/'manifest.json',mf);put(folder/'manifest.index.json',idx);indices[v]=idx
 shutil.copy2(final,deliver/final.name)
 entry={'volume':v,'filename':final.name,'output':str(deliver/final.name),'parent_sha256':sha(base.read_bytes()),'output_sha256':sha(final.read_bytes()),'slides':report['total_slides'],'changed_slides':report['changed_slides'],'added_slides':[a['slide'] for a in report['added_slides']],'new_native_clicks':sum(a['native_animation_clicks'] for a in report['added_slides']),'original_timing_xml_bytes_unchanged':True,'original_shape_ids_names_order_preserved':True,'unrelated_content_byte_identical_except_shifted_numeric_footers':True,'numeric_footer_updates':len(report['footer_updates']),'new_empty_click_targets':[],'native_math_count_before':native0,'native_math_count_after':native1,'static_rendered':imp['rendered'],'individually_visually_inspected':imp['rendered'],'package_finalizer_passed':True,'artifacttool_import_passed':True,'original_part_to_current_slide':position}
 volumes.append(entry);deltas.append({'volume':v,'pptx':final.name,'sha256':entry['output_sha256'],'parent_sha256':entry['parent_sha256'],'slides':entry['slides'],'average_revision':'ppt_average/qa_final.json','original_part_to_current_slide':position,'added_slides':[{'slide':a['slide'],'record_key':a['key']} for a in report['added_slides']]})
 shutil.copy2(R/f'qa_r3/finalizer_v{v}.json',D/f'finalizer_v{v}.json');shutil.copy2(R/f'after_v{v}/qa_import.json',D/f'qa_import_v{v}.json')

for filename in ['全套题目与课件对应索引答案.csv','口算逐式与课件对应索引答案.csv']:
 src=W/'bundle'/filename
 with src.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
 for row in rows:
  mt=re.search(r'第(\d+)册',row['课件文件'])
  if not mt or int(mt[1])<5:continue
  v=int(mt[1]);report=next(x for x in reports if x['volume']==v);pos={int(k):x for k,x in report['position_by_original_part'].items()}
  if filename.startswith('全套'):
   row['幻灯片序号']=','.join(str(x['slide']) for x in indices[v] if x['record_key']==row['稳定编号'])
  else:row['幻灯片序号']=','.join(str(pos[int(n)]) for n in row['幻灯片序号'].split(',') if n)
 for dest in [W/'deliverables'/filename,P/'ppt_average'/filename]:
  with dest.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

approved=J(W/'approved_changes.json');changedkeys={r['key'] for r in rules};unchanged=[x['key'] for x in approved['changes'] if x['key'] not in changedkeys]
qa={'passed':True,'approved_records':len(approved['changes']),'modified_question_keys':sorted(changedkeys),'already_complete_question_keys':unchanged,'volumes':volumes,'native_editable_math':'OMML, with actual XeLaTeX-compiled SVG/PNG compatibility branches','editable_ordinary_text':True,'native_powerpoint_playback_tested':False,'native_wps_playback_tested':False,'math_row_match':{'passed':True,'records':J(R/'qa_math_rows.json')['records'],'rows':J(R/'qa_math_rows.json')['rows']},'source_sets_portably_compiled':J(R/'qa_portable.json')['source_sets'],'static_visual_scope':'All 33 modified original slides and 3 new calculation slides individually visually inspected at full size, plus two already-complete checks; unchanged teaching content verified by package comparison. Numeric footers alone were updated after insertions.','preexisting_geometry_warnings_preserved':[{'volume':6,'slides':[107,409]}],'scope_note':'PDF has no extra page; these three new pages are PPT calculation continuations only.'}
for name,data in [('qa_final.json',qa),('inventory_patch.json',deltas),('post_export_overlay.json',overlays),('rules.json',rules),('additions.json',J(R/'additions.json')),('qa_math_rows.json',J(R/'qa_math_rows.json'))]:put(R/name,data);put(D/name,data)
(D/'build').mkdir(exist_ok=True)
for name in ['native_patch.py','make_rules.py','patch_average.py','portable_sources.py','freeze.py','render_inspect.mjs','finalize_r3.mjs']:shutil.copy2(R/'build'/name,D/'build'/name)
for name in ['logical_inventory.json','question_slides.json']:shutil.copy2(R/name,D/name)
(D/'README.txt').write_text('本轮同步第九单元及以后平均数相关计算。33题完整答案的245行显示公式均已与课件内OMML核对。第5册433张，第6册464张；新增第5册89、102、399张为同题计算续讲，原题干保留一次。\n原PPT既有对象ID、名称、顺序及全部timing字节保留，插入后的数字页脚已更新。新增三张均有真实逐行原生点击。普通文字可编辑，公式为原生OMML，并带独立XeLaTeX编译SVG/PNG兼容分支。\n全部33张内容修改页及3张新增页已逐张查看实际渲染。未在PowerPoint/WPS中实际放映，不能把结构保留等同于播放测试。\n当前内容以交付PPT与post_export_overlay.json为准。current_metadata索引已更新所有后续位置；旧覆盖文件按原part编号保留为历史资料，不可按旧UI张号直接定位。\nformulas中的150套.tex从工程根目录实际编译通过，字体路径为fonts/；可在工程根目录运行xelatex ppt_average/formulas/文件.tex。\n')
print(json.dumps({'passed':True,'volumes':deltas,'modified_questions':len(changedkeys),'already_complete':unchanged,'slides':sum(v['slides'] for v in volumes)},ensure_ascii=False),flush=True)
