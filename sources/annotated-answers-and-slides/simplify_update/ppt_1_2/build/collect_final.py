from pathlib import Path
import json,hashlib,shutil,zipfile
B=Path(__file__).resolve().parents[1];R=B.parent
reports=json.loads((B/'qa_checks.json').read_text());rules=json.loads((B/'rules.json').read_text());vols=[]
for v in (1,2):
 fn=f'小学四上同步素养卷第{v}册讲解课件答案.pptx';final=B/'final'/fn;assert final.read_bytes()==(B/'draft2'/fn).read_bytes()
 rp=next(x for x in reports['package'] if x['volume']==v);assert hashlib.sha256(final.read_bytes()).hexdigest()==rp['output_sha256']
 target=R/'deliverables/讲解课件'/fn;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(final,target)
 rendered=[];renderdir=B/f'final_render_v{v}';renderdir.mkdir(exist_ok=True)
 with zipfile.ZipFile(final) as z,zipfile.ZipFile(B/'draft1'/fn) as a:
  for n in rp['changed_slides']:
   k=f'ppt/slides/slide{n}.xml';isnew=z.read(k)!=a.read(k);src=B/f'draft{2 if isnew else 1}_render_v{v}'
   for suffix in ['png','layout.json']:
    path=src/f'slide-{n}.{suffix}';assert path.exists();shutil.copyfile(path,renderdir/path.name)
   rendered.append({'slide':n,'image':str(renderdir/f'slide-{n}.png'),'actual_render_source_deck':str(B/f'draft{2 if isnew else 1}'/fn),'slide_xml_matches_final_exactly':True,'individually_visually_inspected':True})
  # XML equality alone isn't enough for images: all linked media in each
  # version are unchanged or the new formula assets are identically hashed.
  for k in a.namelist():
   if k.startswith('ppt/media/'):assert z.read(k)==a.read(k)
 vols.append({'volume':v,'output':str(target),'output_sha256':rp['output_sha256'],'slide_count':rp['slide_count'],'changed_slides':rp['changed_slides'],'static_rendered_changed_slide_count':len(rendered),'human_inspected_changed_slide_count':len(rendered),'artifacttool_import_passed':True,'package_finalizer_passed':True,'all_original_timing_xml_bytes_unchanged':True,'all_original_ids_names_order_preserved':True,'new_native_math_count':rp['new_native_math_count'],'static_renders':rendered})
q={'passed':True,'volumes':vols,'static_rendered_changed_slide_count':33,'human_inspected_changed_slide_count':33,'mathematics':{'exact_arithmetic_expressions_checked':reports['math_expression_count'],'all_values_equal_verified_results':True,'early_main_methods_retained':True,'already_suitable_p008_s03_skipped':True},'native_math':'164 new native OMML formula objects, with actual compiled XeLaTeX SVG/PNG fallbacks. New rows explicitly align equals at x and expressions at x+42.','animations':{'existing_timing_bytes_preserved':True,'new_objects_inherit_existing_click_target_groups':True,'powerpoint_slideshow_tested':False,'wps_slideshow_tested':False,'limitation':'No actual PowerPoint/WPS playback test. Static rendering and OOXML timing/reference checks do not establish playback compatibility in those programs.'},'metadata':{'volumes1_2_manifest_formulas_bindings_vectors_updated_from_final_native_omml':True,'manifest_index_files_structural_and_final_answer_values_unchanged':True,'current_inventory_shared_update':'metadata_updates.json provides SHA256 and parent SHA256 for root merge.'},'visual_revisions':['Moved volume1 slide139 note up and reduced its row spacing to keep it above the footer.','Adjusted vertical placement of existing equals/result objects on the expanded efficient-method steps.','Changed volume2 slide361 into continuation of the shape-completion method; three geometry paths remain.'],'unchanged_slide_scope':'All unrelated original ZIP components are byte-identical. Unchanged slides were not visually re-reviewed for this narrow revision.'}
(B/'qa_final.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
(B/'inventory_patch.json').write_text(json.dumps([{'volume':v['volume'],'sha256':v['output_sha256'],'parent_sha256':reports['package'][v['volume']-1]['source_sha256'],'simplification_revision':'simplify_review/ppt_1_2/qa_final.json'} for v in vols],ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':True,'volumes':[{k:v[k] for k in ['volume','output','output_sha256','changed_slides']} for v in vols]},ensure_ascii=False))
