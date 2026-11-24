from pathlib import Path
import fitz,json,hashlib,copy
R=Path(__file__).resolve().parent;P=R/'project';C=P/'detailed_layout';O=R/'deliverables';O.mkdir(exist_ok=True)
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
base=R/'bundle/小学同步素养四年级上册数学答案.pdf';old=J(R/'baseline/current_release.json');assert SHA(base)==old['sha256']
run=C/'runs/recheck_20261105';new=J(run/'receipt.json');acc=J(R/'accepted_changes.json');books=set(acc['changed_book_pages']);assert books=={m['book_page'] for m in new['mapping']}
orig=fitz.open(base);partial=fitz.open(new['pdf']);out=fitz.open();bm={m['book_page']:m['answer_pdf_page']-1 for m in new['mapping']}
for i in range(128):
 b=i-3
 if b in books:out.insert_pdf(partial,from_page=bm[b],to_page=bm[b],final=0)
 else:out.insert_pdf(orig,from_page=i,to_page=i,final=0)
out.set_metadata(orig.metadata);out.set_toc(orig.get_toc());raw=R/'raw_composite.pdf';out.save(raw,garbage=3,deflate=True);out.close()
rel=copy.deepcopy(old)
for field in ['mapping','bands','answers','moved_footers','moved_headings']:
 arr=[x for x in old[field] if x['book_page'] not in books]
 for item in new[field]:
  x=copy.deepcopy(item);pn=x['book_page']+4
  if field=='mapping':x.update({'answer_pdf_page':pn,'analysis_pdf_pages':[],'record_pdf_pages':{k:[pn] for k in x['record_pdf_pages']}})
  else:x['pdf_page']=pn
  arr.append(x)
 rel[field]=sorted(arr,key=lambda x:(x['book_page'],x.get('source_cut_y',0)))
for k in ['local_replacements','source_files','compiled_tex','compiled_pdf','cleaned_base_pdf']:rel[k]=new[k]
for k in ['lossless_optimization','raw_pdf_sha256','preservation']:rel.pop(k,None)
rel.update({'run_name':'recheck_20261105','pdf':str((O/base.name).resolve()),'sha256':SHA(raw),'previous_pdf_sha256':SHA(base),'pages':128,'question_pages':108,'record_coverage':867,'visible_note_blocks':856,'first_page_blank':True,'input_pdf':str(base.resolve()),'input_sha256':SHA(base),'recheck_update':{'changed_book_pages':sorted(books),'changed_keys':[c['key'] for c in acc['changes']],'simplifications':33,'multiplication_hint':1,'source_conflict_note':'p074_s04','method_reclassification':'p091_s03','p074_question_average_retained':15,'p074_choice_retained':'C','no_extra_analysis_pages':True}})
assert len(rel['mapping'])==108 and len(rel['answers'])==856 and len(rel['local_replacements'])==73
W(C/'current_release.json',rel);W(P/'answer_page_map.json',rel['mapping']);W(C/'base_local_targets.json',{'patches':[{'id':v['id'],'target_rect':v['target_rect']} for v in rel['local_replacements']]})
print('Raw PDF',SHA(raw),raw.stat().st_size,flush=True)
