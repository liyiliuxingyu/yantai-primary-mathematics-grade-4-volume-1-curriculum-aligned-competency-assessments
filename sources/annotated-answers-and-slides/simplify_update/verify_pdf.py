from pathlib import Path
import fitz,json,hashlib
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'simplify_update'
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=J(P/'detailed_layout/current_release.json');pdf=R/'deliverables/小学同步素养四年级上册数学答案.pdf';old=fitz.open(R/'bundle'/pdf.name);new=fitz.open(pdf)
accepted=J(R/'accepted_changes.json');books=set(accepted['changed_book_pages']);rows=[];changed=[];same=[]
assert len(new)==len(old)==128
for i in range(128):
 b=i-3
 if b in books:
  m=next(x for x in J(P/'detailed_layout/runs/simplify_20261104/receipt.json')['mapping'] if x['book_page']==b)
  partial=fitz.open(P/'detailed_layout/runs/simplify_20261104/详细题内答案成品.pdf');reference=partial[m['answer_pdf_page']-1]
  label='exact reviewed modified-page export';changed.append(b)
 else:reference=old[i];label='previous publication unchanged';same.append(i+1)
 assert reference.rect==new[i].rect,(i+1,'dimensions')
 a=reference.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);z=new[i].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
 assert a.samples==z.samples,(i+1,'raster mismatch')
 rows.append({'pdf_page':i+1,'book_page':b if 1<=b<=108 else None,'reference':label,'rgb_pixels_identical_at_1x':True})
 if b in books:partial.close()
 if (i+1)%16==0:print('Scope comparison',i+1,flush=True)
assert set(changed)==books
assert not new[0].get_images() and not new[0].get_text() and not new[0].get_drawings()
for a in rel['answers']:
 assert fitz.Rect(a['target_rect']) in new[a['pdf_page']-1].rect,a['key']
assert all(not m['analysis_pdf_pages'] and m['answer_pdf_page']==m['book_page']+4 for m in rel['mapping'])
out={'passed':True,'pdf_sha256':SHA(pdf),'pages':128,'changed_book_pages':sorted(books),'changed_question_keys':[c['key'] for c in accepted['changes']],'unchanged_pdf_pages':same,'unchanged_pdf_page_count':len(same),'changed_pages_match_actually_exported_previews':True,'actual_visual_review':'See qa_visual_early.json, qa_visual_late.json and qa_visual_final_corrections.json. This script only compares pixels and positions.','render_scale':1,'all_notes_within_pages':True,'separate_analysis_pages':0,'first_page_blank':True,'pages_compared':rows}
(Q/'qa_scope.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('128 pages checked, modified',len(books),'unchanged',len(same),flush=True)
