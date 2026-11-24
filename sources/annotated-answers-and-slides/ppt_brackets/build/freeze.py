from pathlib import Path
import json,zipfile,sys,importlib.util,hashlib,shutil,re
from lxml import etree as E
R=Path(__file__).resolve().parents[1];W=R.parent;P=W/'project';D=P/'ppt_brackets';D.mkdir(exist_ok=True)
sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
spec=importlib.util.spec_from_file_location('m',P/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
J=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def snapshot(root):
 out=[]
 for n in m.visible_nodes(root):
  sp=next((a for a in n.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')]),None)
  if sp is None:continue
  try:rect=m.get_rect(sp)
  except (AttributeError,ValueError):rect=None
  out.append({'id':n.get('id'),'name':n.get('name'),'rect':rect,'text':''.join(sp.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)),'native_math':bool(sp.findall('.//m:oMath',m.NS)),'group':sp.tag==m.q('p:grpSp')})
 return out
reports=J(R/'draft/qa_package.json');rules=J(R/'rules.json');assert J(R/'qa_scope.json')['passed'];assert J(R/'qa_portable.json')['passed'];overlays=[];volumes=[];deltas=[]
deliver=W/'deliverables/讲解课件';deliver.mkdir(parents=True,exist_ok=True)
for rec in reports:
 v=rec['volume'];base=Path(rec['source']);selected=[r for r in rules if r['volume']==v]
 if selected:
  final=R/'validated'/base.name;receipt=J(R/f'qa/finalizer_v{v}.json');assert receipt['finalSha256']==sha(final)==sha(Path(rec['output']));assert receipt['packageIntegrity']['status']=='pass' and not receipt['presentationLayout']['findings'];assert not receipt['firstPartyImport']['performed']
  imp=J(R/f'after_v{v}/qa_import.json');assert imp['import_succeeded'] and sorted(imp['rendered'])==sorted(rec['changed_ui_slides']);assert imp['source_sha256']==sha(final)
  with zipfile.ZipFile(final) as z:
   for rule in selected:
    root=E.fromstring(z.read(f'ppt/slides/slide{rule["slide"]}.xml'));ob=snapshot(root);by={o['name']:o for o in ob}
    for op in rule['ops']:assert by[op['name']]['text']==op['expected_new_plain'] and by[op['name']]['native_math'] and by[op['name']]['rect']==op['rect']
    overlays.append({'volume':v,'slide':rule['ui_slide'],'part_number':rule['slide'],'record_key':rule['key'],'slide_xml_sha256':hashlib.sha256(z.read(f'ppt/slides/slide{rule["slide"]}.xml')).hexdigest(),'actual_objects':ob,'exact_changes':[{'name':o['name'],'old':o['expected_old_plain'],'new':o['expected_new_plain']} for o in rule['ops']]})
  folder=P/f'ppt_builder/current_metadata/volume{v:02d}';mf=J(folder/'manifest.json');idx=J(folder/'manifest.index.json')
  for rule in selected:
   s=next(s for s in mf['slides'] if s['slide']==rule['ui_slide']);opmap={o['name']:o for o in rule['ops']};found=set()
   for f in s['formulas']:
    if f['target'] in opmap:
     o=opmap[f['target']];f.update({'ast':m.MathParser(o['tex']).parse(),'implementation':'native OMML in delivered PPTX','color':o['color'],'points':o['points'],'font':'Droid Sans Fallback'});found.add(f['target'])
   for name,o in opmap.items():
    if name not in found:s['formulas'].append({'target':name,'ast':m.MathParser(o['tex']).parse(),'implementation':'native OMML in delivered PPTX','color':o['color'],'points':o['points'],'font':'Droid Sans Fallback'})
   s['post_export_semantic_overlay']='ppt_brackets/post_export_overlay.json'
   for x in idx:
    if x['slide']==rule['ui_slide']:x['metadata_role']='structural_location_index';x['post_export_content_patched']=True;x['semantic_overlay']='ppt_brackets/post_export_overlay.json'
  mf['final_pptx_sha256']=sha(final);mf['post_export_authority']='ppt_brackets/post_export_overlay.json for this pure bracket revision; retain previous overlays for other content.';mf['bracket_continuation_revision']={'changed_slides':rec['changed_ui_slides'],'qa':'ppt_brackets/qa_final.json','rules':'ppt_brackets/rules.json','native_powerpoint_playback_tested':False};mf['regenerate_from_this_manifest']=False
  put(folder/'manifest.json',mf);put(folder/'manifest.index.json',idx)
  shutil.copy2(R/f'qa/finalizer_v{v}.json',D/f'finalizer_v{v}.json');shutil.copy2(R/f'after_v{v}/qa_import.json',D/f'qa_subset_import_v{v}.json')
 else:final=Path(rec['output']);assert sha(final)==sha(base)
 shutil.copy2(final,deliver/final.name)
 entry={'volume':v,'filename':final.name,'output':str(deliver/final.name),'parent_sha256':sha(base),'output_sha256':sha(final),'slides':rec['total_slides'],'changed_slides':rec['changed_ui_slides'],'changed_question_keys':rec['changed_keys'],'changed_formula_count':rec['formula_count'],'unchanged_copy':not selected,'timing_xml_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'other_original_package_parts_byte_identical':True,'geometry_fonts_colors_and_ordinary_text_unchanged':True,'package_and_layout_validation_passed':True,'static_rendered_and_individually_visually_inspected':rec['changed_ui_slides'],'full_deck_artifacttool_import_passed':False if selected else None,'subset_artifacttool_import_passed':True if selected else None}
 volumes.append(entry);deltas.append({'volume':v,'pptx':final.name,'sha256':sha(final),'parent_sha256':sha(base),'slides':rec['total_slides'],'bracket_continuation_revision':'ppt_brackets/qa_final.json','changed_slides':rec['changed_ui_slides']})
for fn in ['全套题目与课件对应索引答案.csv','口算逐式与课件对应索引答案.csv']:shutil.copy2(W/'bundle'/fn,W/'deliverables'/fn)
qa={'passed':True,'scope':'Only bracket glyphs in unfinished square-bracket calculation groups; all 41 questions and 62 exact PPT rows (60 source corrections plus two existing PPT expression variants) synchronized. No new page, step, digit or operator.','volumes':volumes,'approved_question_count':41,'changed_formula_rows':62,'source_changed_formula_rows':60,'ppt_only_changed_formula_rows':2,'changed_slide_count':sum(len(x['changed_slides']) for x in volumes),'source_sets_portably_compiled':J(R/'qa_portable.json')['source_sets'],'formulas':'Genuine editable OMML with independently XeLaTeX-compiled SVG/PNG compatibility branches','editable_ordinary_text':True,'native_powerpoint_playback_tested':False,'native_wps_playback_tested':False,'full_deck_artifacttool_import_limitation':'Full volume 1 import attempted twice and failed with WASM memory access out of bounds. Full package integrity/layout and all timing/shape scope checks passed for the full decks. Static views used exact selected-slide XML subsets with original relationships, themes, masters and media retained; successful subset import is not claimed as successful full-deck import.','static_visual_scope':'All49 affected slides actually rendered from exact selected-slide subsets and individually inspected at full size; no fresh visual audit of unaffected slides claimed.','all_original_timing_xml_bytes_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'slide_counts_and_all_existing_indices_unchanged':True,'preexisting_layout_warnings_preserved':{'6':[107,409]}}
for name,data in [('qa_final.json',qa),('inventory_patch.json',deltas),('post_export_overlay.json',overlays),('rules.json',rules),('qa_scope.json',J(R/'qa_scope.json')),('match_report.json',J(R/'match_report.json'))]:put(R/name,data);put(D/name,data)
(D/'build').mkdir(exist_ok=True)
for name in ['patch_brackets.py','apply_ppt_only.py','check_scope.py','finalize_structural.mjs','finalize_r2.mjs','make_subsets.py','render_subset.mjs','portable_sources.py','freeze.py']:shutil.copy2(R/'build'/name,D/'build'/name)
shutil.copy2(R/'baseline_inventory.json',D/'baseline_inventory.json')
shutil.copy2(R/'qa_equals338.json',D/'qa_equals338.json')
(D/'README.txt').write_text('本轮41题、62行（60条源改式和2条PPT既有表达变体）仅统一括号：外层中括号内还有运算时，保留中括号，整组化为一个数后才去掉。数字、运算符、行数、结果、普通文字及图形均不改变。六册426/479/406/462/433/464张，原所有动画timing字节和对象ID/名称/顺序保留，未增加页面。\n49张受影响页已用原slide XML及其关系、主题、母版和媒体不变的临时子集实际渲染并逐张查看。整册第1册在Artifact Tool中两次导入遇WASM内存越界，因此未声称整册静态导入成功；全册包结构、版面几何及scope检查已过。交付仍是完整六册，临时子集不交付。未在PowerPoint/WPS中实际放映。\n普通文字可编辑，62行新公式为原生OMML，附实际XeLaTeX编译SVG/PNG兼容分支。formulas中的62套.tex已从工程根目录以fonts/相对路径实际编译通过。\n当前权威内容为本次交付PPT和post_export_overlay.json；current_metadata的原页序索引不变，仅更新本轮公式与语义覆盖。历史覆盖文件作为历史记录保留。\n')
print(json.dumps({'passed':True,'volumes':[{'volume':v['volume'],'sha256':v['output_sha256'],'changed':len(v['changed_slides'])} for v in volumes]},ensure_ascii=False),flush=True)
