from pathlib import Path
import fitz,json,hashlib,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';W=P/'axis_update';J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=fitz.open(R/'bundle/小学同步素养四年级上册数学答案.pdf');newpath=R/'deliverables/小学同步素养四年级上册数学答案.pdf';new=fitz.open(newpath);assert len(old)==len(new)==128
spec=J(R/'pdf_patch_report.json');areas={}
for x in spec['changed_notes']:areas.setdefault(x['pdf_page'],[]).append(list(fitz.Rect(x['old_note_rect'])|fitz.Rect(x['new_note_rect'])))
areas[74].append([499.3,375.6,510.1,387.8]);changed=[];same=[];details=[]
for i in range(128):
 assert old[i].rect==new[i].rect
 a=old[i].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);b=new[i].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
 aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);diff=np.any(aa!=bb,2)
 if not diff.any():same.append(i+1);continue
 changed.append(i+1);assert i+1 in areas
 yy,xx=np.indices(diff.shape);outside=diff.copy()
 for q in areas[i+1]:
  r=fitz.Rect(q)+(-1,-1,1,1);outside&=~((xx+.5>=r.x0)&(xx+.5<r.x1)&(yy+.5>=r.y0)&(yy+.5<r.y1))
 assert not outside.any(),(i+1,int(outside.sum()))
 details.append({'pdf_page':i+1,'changed_pixels':int(diff.sum()),'changed_pixels_outside_four_notes_and_one_judgment':int(outside.sum())})
assert changed==[69,74,89]and len(same)==125
p=new[0].get_pixmap();assert min(p.samples)==255
out={'passed':True,'pdf_sha256':SHA(newpath),'pages':128,'changed_pdf_pages':changed,'changed_book_pages':[65,70,85],'unchanged_pdf_pages':125,'unchanged_pages':same,'render_scale':1,'same_page_dimensions':True,'all_differences_restricted_to_exactly_four_note_areas_and_one_judgment':True,'page_details':details,'first_page_blank':True,'source_stem_retained':True,'limits':'This is a raster scope and location check. Independent mathematical and visual review is recorded separately; no PowerPoint slideshow test.'}
(W/'qa_scope.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('128 pages compared; 125 exactly identical; remaining differences confined to four notes and one mark.',flush=True)
