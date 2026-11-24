from pathlib import Path
import hashlib,json,math,sys
from PIL import Image,ImageChops,ImageDraw,ImageFont
import numpy as np
W=Path(__file__).resolve().parents[1];obj=json.loads((W/'modified_objects.json').read_text());pages=json.loads((W/'conversion_pages.json').read_text())['pages'];jobs=json.loads((W/'render_jobs.json').read_text())
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',16)
for v in map(int,sys.argv[1:]):
 job=next(j for j in jobs if j['volume']==v);folder=W/f'qa_contacts/volume{v:02d}';folder.mkdir(parents=True,exist_ok=True)
 assert hashlib.sha256(Path(job['source']).read_bytes()).hexdigest()==job['source_sha256']
 candidates=[o for o in obj['objects']if o['volume']==v and(o['native_math']or o['change_type']=='unit_parentheses')and o['text'].strip()not in('=','≈')]
 crops=[]
 for i,o in enumerate(candidates):
  image=Image.open(W/f'final_render/volume{v:02d}/slide-{o["slide"]}.png').convert('RGB');x,y,w,h=o['rect'];box=(max(0,math.floor(x)-12),max(0,math.floor(y)-12),min(image.width,math.ceil(x+w)+12),min(image.height,math.ceil(y+h)+12));c=image.crop(box);a=np.array(c)
  if o.get('color')=='000000':mask=(a[:,:,0]<145)&(a[:,:,1]<145)&(a[:,:,2]<145)
  else:mask=(a[:,:,0]>100)&(a[:,:,1]<140)&(a[:,:,2]<140)&(a[:,:,0]>a[:,:,1]+30)
  ys,xs=np.where(mask)
  if len(xs):
   bb=(max(0,int(xs.min())-10),max(0,int(ys.min())-10),min(c.width,int(xs.max())+11),min(c.height,int(ys.max())+11));c=c.crop(bb)
  crops.append((o,c))
 index=[];sheets=[]
 for off in range(0,len(crops),6):
  group=crops[off:off+6];heights=[max(c.height+36,88)for o,c in group];canvas=Image.new('RGB',(1280,40+sum(heights)),(255,255,255));d=ImageDraw.Draw(canvas);d.text((12,8),f'VOL {v}  final SHA256 {job["source_sha256"][:16]}  sheet {off//6+1}',font=font,fill='black');yy=40
  name=f'sheet-{off//6+1:03d}.png'
  for n,((o,c),hh)in enumerate(zip(group,heights)):
   label=f'{off+n+1:03d} | V{v} slide {o["slide"]} | {o["record_key"]} | {o["name"]}'
   d.text((12,yy+2),label,font=font,fill='black');canvas.paste(c,(12,yy+26));d.line((0,yy+hh-1,1279,yy+hh-1),fill=(210,210,210));index.append({**o,'sheet':str(folder/name),'row':n+1,'crop_width':c.width,'crop_height':c.height,'review_scope':'actual edited formula/unit region; conversion whole pages reviewed separately'});yy+=hh
  canvas.save(folder/name);sheets.append(str(folder/name))
 result={'volume':v,'final_pptx':job['source'],'final_pptx_sha256':job['source_sha256'],'sheets':sheets,'object_count':len(index),'objects':index,'modified_slides':job['modified_slides'],'all_conversion_whole_pages':[p for p in pages if p['volume']==v],'render_directory':job['output_directory']}
 (folder/'index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'volume':v,'objects':len(index),'sheets':len(sheets),'conversion_pages':[p['slide']for p in result['all_conversion_whole_pages']],'index':str(folder/'index.json')},ensure_ascii=False))
