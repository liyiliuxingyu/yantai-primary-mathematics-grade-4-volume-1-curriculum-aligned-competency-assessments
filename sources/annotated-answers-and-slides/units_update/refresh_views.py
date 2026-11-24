from pathlib import Path
import json,fitz,hashlib
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'units_update';J=lambda p:json.loads(p.read_text());W=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');rel=J(P/'detailed_layout/current_release.json');d=fitz.open(R/'deliverables/小学同步素养四年级上册数学答案.pdf');q=Q/'local_crops';q.mkdir(exist_ok=True);records=[];font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20);carry=[]
def emit(page,scale,rect,path,key,kind):
 old=Image.open(path).convert('RGB').tobytes()if path.exists()else None;oldsize=Image.open(path).size if path.exists()else None;pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),clip=rect,alpha=False);pix.save(path);new=Image.open(path).convert('RGB');carry.append({'key':key,'kind':kind,'path':str(path.relative_to(Q)),'same_pixels_as_preceding_reviewed_crops':old==new.tobytes()and oldsize==new.size})
for item in J(Q/'new_local_patches.json')['records']:
 a=next(x for x in rel['local_replacements']if x['id']==item['id']);book=a['book_page'];pn=next(m['answer_pdf_page']for m in rel['mapping']if m['book_page']==book);r=fitz.Rect(a['target_rect']);mapped=[]
 for b in[x for x in rel['bands']if x['book_page']==book]:
  sr=fitz.Rect(b['source_rect']);c=r&sr
  if not c.is_empty:dx=b['target_rect'][0]-sr.x0;dy=b['target_rect'][1]-sr.y0;mapped.append(c+(dx,dy,dx,dy))
 assert len(mapped)==1;(r,)=mapped;context=fitz.Rect(max(35,r.x0-90),max(0,r.y0-17),min(585,r.x1+65),min(d[pn-1].rect.height,r.y1+20));path=q/f'{a["id"]}.png';scale=3 if context.width<240 else 2;emit(d[pn-1],scale,context,path,a['id'],'local');records.append({'id':a['id'],'key':a['key'],'book_page':book,'pdf_page':pn,'actual_publication_target_rect':list(r),'context_rect':list(context),'path':str(path.resolve())})
for lo,hi in[(1,36),(37,72),(73,108)]:
 subset=[x for x in records if lo<=x['book_page']<=hi]
 for block in range(0,len(subset),6):
  batch=subset[block:block+6];canvas=Image.new('RGB',(1200,660),(248,248,248));draw=ImageDraw.Draw(canvas)
  for n,item in enumerate(batch):
   x=(n%2)*600;y=(n//2)*220;draw.text((x+8,y+7),f'{item["id"]} | book {item["book_page"]} / PDF {item["pdf_page"]}',font=font,fill='black');im=Image.open(item['path']);im.thumbnail((584,176));canvas.paste(im,(x+8,y+36))
  canvas.save(q/f'contact_{lo:03d}_{hi:03d}_{block//6+1:02d}.png')
W(Q/'local_crop_index.json',{'pdf_sha256':rel['sha256'],'actual_local_crops':len(records),'records':records});q2=Q/'crops';q2.mkdir(exist_ok=True)
for k in J(R/'approved_changes.json')['conversion_keys']:
 a=next(x for x in rel['answers']if x['key']==k);r=fitz.Rect(a['target_rect'])+(-3,-3,3,3);emit(d[a['pdf_page']-1],1.5,r,q2/f'{k}_note.png',k,'note')
W(Q/'qa_visual_carryforward.json',{'final_pdf_sha256':rel['sha256'],'previous_reviewed_pdf_sha256':'ead262667f6398e8027af765e6b9d9f2066418b0007a774b57bd1e4b10247c2b','crop_checks':carry,'identical_crops':sum(x['same_pixels_as_preceding_reviewed_crops']for x in carry),'changed_crops':[x for x in carry if not x['same_pixels_as_preceding_reviewed_crops']]});print('views refreshed',len(records),'local /',len(carry)-len(records),'note; same',sum(x['same_pixels_as_preceding_reviewed_crops']for x in carry))
