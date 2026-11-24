from pathlib import Path
import fitz,json,hashlib,os
R=Path(__file__).resolve().parents[1];W=R/'followup_style';C=R/'detailed_layout'
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=J(W/'before/detailed_layout/current_release.json');new=J(C/'current_release.json')
assert new['run_name']=='followup_unit1_trees_final'
full=Path(new['pdf']);raw=Path(new['compiled_tex']).parent/'详细题内答案成品.pdf'
before=fitz.open(W/'before/previous.pdf');draft=fitz.open(R/'detailed_layout/runs/followup_unit1_trees/详细题内答案成品.pdf')
for i,book in enumerate([5,7]):
 pn=book+3;before.delete_page(pn);before.insert_pdf(draft,from_page=i,to_page=i,start_at=pn)
before.set_metadata({'title':'小学同步素养四年级上册数学答案','subject':'详细题内答案，第一页空白','author':'数学教学资料'})
out=W/'preserved_raw.pdf';before.save(out,garbage=3,deflate=True);before.close();draft.close()
for field in ['mapping','bands','answers','moved_footers','moved_headings','local_replacements']:
 new[field]=[x for x in old[field]if x['book_page']not in[5,7]]+[x for x in new[field]if x['book_page']in[5,7]]
 new[field].sort(key=lambda x:x['book_page'])
new['preservation']={'baseline_pdf_sha256':SHA(W/'before/previous.pdf'),'changed_book_pages':[5,7],'unchanged_question_pages':106,'method':'Original published pages directly retained; only original book pages 5 and 7 replaced using the actually reviewed two-page draft. This avoids incidental footer/antialias changes from reimporting 106 untouched pages.'}
out.replace(raw);full.write_bytes(raw.read_bytes());new['sha256']=SHA(full)
(C/'current_release.json').write_text(json.dumps(new,ensure_ascii=False,indent=2))
(R/'answer_page_map.json').write_text(json.dumps(new['mapping'],ensure_ascii=False,indent=2))
doc=fitz.open(full);previews=Path(new['compiled_tex']).parent/'previews'
for book in range(1,109):doc[book+3].get_pixmap(matrix=fitz.Matrix(1,1)).save(previews/f'p{book:03}.png')
print('Only two reviewed pages replaced; 106 original published question pages retained.',new['sha256'],flush=True)
