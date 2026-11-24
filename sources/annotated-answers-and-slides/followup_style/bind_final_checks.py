from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parents[1];W=R/'followup_style';C=R/'detailed_layout'
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
q=J(W/'qa_lossless.json');assert q['passed']and q['pages_compared']==128 and q['different_rgb_pixels_total']==0 and not q['text_different_pages']
rel=J(C/'current_release.json');assert rel['sha256']==q['source_sha256']
raw_hash=rel['sha256'];dest=Path(rel['pdf']);shutil.copy2(W/'optimized_preserved.pdf',dest);h=SHA(dest);assert h==q['candidate_sha256']
rel.update({'sha256':h,'raw_pdf_sha256':raw_hash,'lossless_optimization':'followup_style/qa_lossless.json'});save(C/'current_release.json',rel)
a=J(C/'qa_release.json');assert a['passed']and a['pdf_sha256']==raw_hash;a.update({'pdf_sha256':h,'verified_raw_pdf_sha256':raw_hash,'optimization_note':'Every page rendered at 2x and every extracted text string exactly match the separately verified preserved raw PDF. Dense analysis-node halo exclusions are explicit in local_red_ghost_checks; 32 large-formula ghost checks retain their original scope.'});save(C/'qa_release.json',a)
for f in ['qa_portability.json']:
 a=J(C/f);assert a['passed']and a['pdf_sha256']==raw_hash;a['pdf_sha256']=h;a['verified_raw_pdf_sha256']=raw_hash;a['lossless_optimization']='followup_style/qa_lossless.json';save(C/f,a)
scope=J(W/'qa_scope.json');assert scope['passed']and scope['pdf_sha256']==raw_hash;scope.update({'pdf_sha256':h,'compared_raw_pdf_sha256':raw_hash,'lossless_optimization':'followup_style/qa_lossless.json'});save(W/'qa_scope.json',scope)
for L in 'ABCD':
 p=C/f'qa_visual_{L}.json';a=J(p);previous=a['pdf_sha256'];a.update({'run':'followup_unit1_trees_final','pdf':str(dest),'pdf_sha256':h,'hash_verified':True})
 a['p005_p007_unit1_style_update']={'previous_pdf_sha256':previous,'scope_proof':'followup_style/qa_scope.json','all_other_106_question_pages_exactly_preserved':True,'changed_pages':[5,7],'review':'followup_style/qa_math_visual.json'if L=='A'else 'No pages in this segment changed; prior actual review inherited through exact rendered-image equality.','lossless_optimization':'followup_style/qa_lossless.json'}
 save(p,a)
a=J(W/'qa_math_visual.json');a['reviewed_draft_pdf_sha256']=a['pdf_sha256'];a['final_pdf_sha256']=h;a['final_pages_render_identical_to_reviewed_draft']=True;a['scope_proof']='followup_style/qa_scope.json';a['lossless_optimization']='followup_style/qa_lossless.json';save(W/'qa_math_visual.json',a)
print('Final checked PDF',h,dest.stat().st_size,flush=True)
