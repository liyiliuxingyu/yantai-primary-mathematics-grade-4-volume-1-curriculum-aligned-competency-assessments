from pathlib import Path
import json,copy,hashlib,fitz
R=Path(__file__).resolve().parent;P=R/'project';C=P/'detailed_layout';O=R/'deliverables';O.mkdir(exist_ok=True)
def J(p):return json.loads(p.read_text())
def W(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'bundle/小学同步素养四年级上册数学答案.pdf';old=J(R/'baseline/detailed_layout/current_release.json')
assert SHA(base)==old['sha256']
run=C/'runs/simplify_20261104';new=J(run/'receipt.json');accepted=J(R/'accepted_changes.json');books=accepted['changed_book_pages'];bset=set(books)
assert [m['book_page'] for m in new['mapping']]==books
oldpdf=fitz.open(base);partial=fitz.open(new['pdf']);doc=fitz.open();bmap={m['book_page']:m['answer_pdf_page']-1 for m in new['mapping']}
for i in range(128):
 book=i-3
 if book in bset:doc.insert_pdf(partial,from_page=bmap[book],to_page=bmap[book],final=0)
 else:doc.insert_pdf(oldpdf,from_page=i,to_page=i,final=0)
doc.set_metadata(oldpdf.metadata);doc.set_toc(oldpdf.get_toc())
dest=O/base.name;tmp=dest.with_suffix('.tmp.pdf');doc.save(tmp,garbage=3,deflate=True);doc.close();tmp.replace(dest)
rel=copy.deepcopy(old)
for field in ['mapping','bands','answers','moved_footers','moved_headings']:
 arr=[v for v in old[field] if v['book_page'] not in bset]
 for item in new[field]:
  v=copy.deepcopy(item);pn=v['book_page']+4
  if field=='mapping':
   v['answer_pdf_page']=pn;v['analysis_pdf_pages']=[];v['record_pdf_pages']={k:[pn] for k in v['record_pdf_pages']}
  else:v['pdf_page']=pn
  arr.append(v)
 rel[field]=sorted(arr,key=lambda v:(v['book_page'],v.get('source_cut_y',0)))
rel.update({k:new[k] for k in ['local_replacements','source_files','compiled_tex','compiled_pdf','cleaned_base_pdf']})
rel.update({'run_name':'simplify_calculations','pdf':str(dest.resolve()),'sha256':SHA(dest),'previous_pdf_sha256':SHA(base),'pages':128,'question_pages':108,'visible_note_blocks':856,'first_page_blank':True,'input_pdf':str(base.resolve()),'input_sha256':SHA(base),'simplification_update':{'changed_book_pages':books,'changed_keys':[c['key'] for c in accepted['changes']],'local_replacement_keys':accepted['local_replacement_keys'],'early_primary_methods_preserved':True,'start_fourth_unit':25}})
for k in ['lossless_optimization','raw_pdf_sha256','preservation']:rel.pop(k,None)
W(C/'current_release.json',rel);W(P/'answer_page_map.json',rel['mapping'])
W(C/'base_local_targets.json',{'patches':[{'id':v['id'],'target_rect':v['target_rect']} for v in rel['local_replacements']]})
doc=fitz.open(dest);assert len(doc)==128 and not doc[0].get_text() and not doc[0].get_images()
assert len(rel['mapping'])==108 and len(rel['answers'])==856 and all(not v['analysis_pdf_pages'] for v in rel['mapping'])
assert len({v['key'] for v in rel['answers']})==856
W(P/'simplify_update/merge_report.json',{'passed':True,'pdf_sha256':SHA(dest),'previous_sha256':SHA(base),'changed_book_pages':books,'page_count':128,'first_page_blank':True,'separate_analysis_pages':0,'local_patch_count':len(rel['local_replacements'])})
print(SHA(dest),dest.stat().st_size,flush=True)
