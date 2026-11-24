import sys,json
from pathlib import Path
import fitz
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R.parent/'average_review'))
from patch_pdf import source_for_book
old=json.loads((R/'pdf_baseline/current_release.json').read_text());d=fitz.open(R/'bundle/小学同步素养四年级上册数学答案.pdf');out=fitz.open();root=R/'geometry_early';root.mkdir(exist_ok=True)
for book in [3,7,8,11,15,19]:
 source=source_for_book(d,d[book+3],old,book)
 p=d.new_page(width=595,height=841);d.xref_set_key(p.xref,'Resources',f'<< /XObject << /BrkAuditSource {source} 0 R >> >>');x=d.get_new_xref();d.update_object(x,'<<>>');d.update_stream(x,b'q /BrkAuditSource Do Q');p.set_contents(x)
 out.insert_pdf(d,from_page=len(d)-1,to_page=len(d)-1);d.delete_page(len(d)-1)
 i=len(out)-1;p=out[i];p.get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(root/f'p{book:03d}.png')
 print('\nPAGE',book)
 rows=[]
 for b in p.get_text('dict')['blocks']:
  if 'lines'not in b:continue
  for l in b['lines']:
   red=[s for s in l['spans'] if s['color'] in [16711680,13440035]]
   if red:
    tx=''.join(s['text']for s in red);print(tuple(round(a,2)for a in l['bbox']),repr(tx),[(tuple(round(a,3)for a in s['origin']),round(s['size'],5)) for s in red])
    rows.append({'bbox':l['bbox'],'text':tx,'spans':red})
 (root/f'p{book:03d}_red.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
out.save(root/'source_a4_early.pdf',garbage=3,deflate=True)
