from pathlib import Path
import json,hashlib,sys,time
import fitz
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'recheck_update';O=R/'deliverables';O.mkdir(exist_ok=True)
sys.path.insert(0,str(P/'detailed_layout'))
from deduplicate_identical_jpegs import image_groups
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
started=time.time();raw=R/'raw_composite.pdf';rel=J(P/'detailed_layout/current_release.json');assert SHA(raw)==rel['sha256']
dest=O/'小学同步素养四年级上册数学答案.pdf';d=fitz.open(raw);groups,nimages=image_groups(d);replacements=[]
for key,entries in groups.items():
 if len(entries)<2:continue
 entries.sort(key=lambda row:(row['color_space']!=('name','/DeviceRGB'),row['xref']));keep=entries[0]
 for dup in entries[1:]:d.xref_copy(keep['xref'],dup['xref']);replacements.append({'jpeg_sha256':key[0],'keep':keep['xref'],'replace':dup['xref']})
temp=dest.with_suffix('.tmp.pdf');d.save(temp,garbage=4,deflate=True);d.close();temp.replace(dest)
rawdoc=fitz.open(raw);final=fitz.open(dest);base=fitz.open(R/'bundle'/dest.name);partial=fitz.open(P/'detailed_layout/runs/recheck_20261105/详细题内答案成品.pdf')
pr=J(P/'detailed_layout/runs/recheck_20261105/receipt.json');bm={m['book_page']:m['answer_pdf_page']-1 for m in pr['mapping']};books=set(bm);rows=[]
assert len(rawdoc)==len(final)==len(base)==128
for i in range(128):
 b=i-3;ref=partial[bm[b]] if b in books else base[i];f=final[i];assert f.rect==rawdoc[i].rect==ref.rect
 a=rawdoc[i].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);z=f.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);c=ref.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
 assert a.samples==z.samples,('optimization changed RGB',i+1)
 assert c.samples==z.samples,('scope changed RGB',i+1)
 assert rawdoc[i].get_text()==f.get_text(),('optimization text changed',i+1)
 rows.append({'pdf_page':i+1,'book_page':b if 1<=b<=108 else None,'rgb_identical_to_raw_composite':True,'rgb_identical_to_expected_reference':True,'reference':'reviewed partial export' if b in books else 'previous published page'})
 if (i+1)%16==0:print('Final PDF comparison',i+1,flush=True)
assert not final[0].get_images() and not final[0].get_text() and not final[0].get_drawings()
for a in rel['answers']:assert fitz.Rect(a['target_rect']) in final[a['pdf_page']-1].rect,a['key']
assert all(m['answer_pdf_page']==m['book_page']+4 and not m['analysis_pdf_pages'] for m in rel['mapping'])
h=SHA(dest);rel['sha256']=h;rel['raw_pdf_sha256']=SHA(raw);rel['lossless_optimization']='recheck_update/qa_optimization.json'
W(P/'detailed_layout/current_release.json',rel)
W(Q/'qa_optimization.json',{'passed':True,'source_sha256':SHA(raw),'candidate_sha256':h,'source_bytes':raw.stat().st_size,'candidate_bytes':dest.stat().st_size,'identical_jpeg_replacements':replacements,'all_128_pages_rgb_and_text_identical_at_scale_1':True,'elapsed_seconds':time.time()-started})
W(Q/'qa_scope.json',{'passed':True,'pdf_sha256':h,'pages':128,'question_pages':108,'changed_book_pages':sorted(books),'changed_question_keys':[c['key'] for c in J(R/'accepted_changes.json')['changes']],'unchanged_pdf_pages':128-len(books),'first_page_blank':True,'separate_analysis_pages':0,'all_notes_within_pages':True,'render_scale':1,'comparison':rows,'limits':'This machine check verifies the published scope and lossless image deduplication, not independent mathematics or human visual review.'})
print('PDF final',h,dest.stat().st_size,'modified book pages',len(books),flush=True)
