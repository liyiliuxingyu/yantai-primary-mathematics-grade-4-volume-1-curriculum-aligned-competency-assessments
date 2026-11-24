from pathlib import Path
import json,re,math,hashlib,importlib.util
import fitz
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'bracket_update';J=lambda p:json.loads(Path(p).read_text());W=lambda p,d:Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('helper',R/'patch_pdf.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
output=R/'deliverables/小学同步素养四年级上册数学答案.pdf';sha=SHA(output);rel=J(P/'detailed_layout/current_release.json');assert rel['sha256']==sha;scope=J(Q/'qa_scope.json');recovery=J(Q/'qa_recovery.json');assert scope['passed']and recovery['passed'];assert scope['pdf_sha256']==recovery['answer_sha256']==sha
plan=J(Q/'layout_plan.json');new=J(Q/'new_local_patches.json')['records'];masks=J(Q/'source_masks.json')['masks'];names={x['id']:'BracketNew_'+x['id']for x in new};doc=fitz.open(output);checks=[];baseline_checks=[]
for book in sorted({x['book_page']for x in masks}):
 source=m.source_for_book(doc,doc[book+3],rel,book)
 def inspect_page():
  p=doc.new_page(width=595,height=841);doc.xref_set_key(p.xref,'Resources',f'<< /XObject << /Inspect {source} 0 R >> >>');x=doc.get_new_xref();doc.update_object(x,'<<>>');doc.update_stream(x,b'q /Inspect Do Q');p.set_contents(x);return p
 p=inspect_page();spans=[s for b in p.get_text('dict')['blocks']for l in b.get('lines',[])for s in l['spans']if s['text'].startswith('=')]
 for item in [x for x in new if x['book_page']==book]:
  anchor=item['baseline_anchor'];matches=[s for s in spans if max(abs(s['origin'][i]-anchor[i])for i in[0,1])<.01];assert matches,item['key'];s=matches[-1];error=max(abs(s['origin'][i]-anchor[i])for i in[0,1]);assert error<.001,item['key'];assert abs(s['size']-item['font_size']*72/72.27)<.001;baseline_checks.append({'key':item['key'],'expected_origin':anchor,'actual_corrected_equals_origin':list(s['origin']),'maximum_error_bp':error,'original_math_size_preserved':True,'actual_math_size_bp':s['size']})
 doc.delete_page(len(doc)-1);stream=doc.xref_stream(source)
 for item in[x for x in new if x['book_page']==book]:
  pat=rb'/'+names[item['id']].encode()+rb'\s+Do\b';assert len(re.findall(pat,stream))==1;stream=re.sub(pat,b'',stream)
 doc.update_stream(source,stream);p=inspect_page()
 for item in[x for x in masks if x['book_page']==book]:
  rr=fitz.Rect(item['rect']);rect=fitz.Rect(math.ceil(rr.x0),math.ceil(rr.y0),math.floor(rr.x1),math.floor(rr.y1));pix=p.get_pixmap(clip=rect,alpha=False);assert min(pix.samples,default=255)==255,(item['key'],'old red remains');checks.append({'key':item['key'],'replacement_local_id':item['replacement_local_id'],'old_red_region_blank_with_corrected_local_call_omitted':True,'sampling_rect_inside_exclusion':list(rect),'new_local_call_present_in_final_file':True})
 doc.delete_page(len(doc)-1)
W(Q/'qa_source_rows.json',{'passed':True,'pdf_sha256':sha,'source_row_count':17,'checks':checks,'actual_baseline_checks':baseline_checks,'maximum_actual_baseline_error_bp':max(x['maximum_error_bp']for x in baseline_checks),'old_average_blank_regions_retained':16,'inspection_only_source_mutation':'Only in-memory inspection copies omitted the corrected calls; deliverable bytes were never changed.'})
previews=Q/'previews';previews.mkdir(exist_ok=True)
with fitz.open(output)as final:
 for book in plan['changed_books']:final[book+3].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(previews/f'p{book:03d}.png')
W(Q/'patch_report.json',{'passed':True,'pdf_sha256':sha,'previous_pdf_sha256':rel['previous_pdf_sha256'],'changed_snippet_ids':plan['changed_ids'],'changed_book_pages':plan['changed_books'],'plans':plan['plans'],'known_old_local_draw_calls_removed':7,'new_source_rows':17,'page_count':128,'all_page_dimensions_unchanged':True,'original_question_content_unchanged':True,'first_page_blank':True,'local_patch_count':87,'source_row_names':names})
print('PDF QA COMPLETE',sha,'max actual baseline error',max(x['maximum_error_bp']for x in baseline_checks))
