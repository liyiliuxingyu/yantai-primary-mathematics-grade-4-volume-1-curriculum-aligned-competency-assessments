from pathlib import Path
import json,math,re,importlib.util
import fitz,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'bracket_update';Q.mkdir(exist_ok=True)
J=lambda p:json.loads(Path(p).read_text())
W=lambda p,d:Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
geo=J(R/'source_geometry_early.json');items=[]
for rec in geo['records']:
 if not rec['visible_original_main_formula_needs_patch']:continue
 row=rec['red_spans'][0];text=rec['new_red_latex_rows'][0]
 expression=text.replace('={}&','').replace('&=','').lstrip('=& ')
 items.append({'key':rec['key'],'book_page':rec['book_page'],'old_bbox':row['bbox'],'baseline_anchor':rec['first_equals_origin'],'font_size':rec['input_font_size_pt'],'old_visible_row':row['text'],'new_expression':expression,'evidence':rec['geometry_evidence_png'],'old_row_count_preserved':1})
for book,key,yy,font,expression in [(44,'p044_s02',318.9,9,r'5\times[24\div6]'),(46,'p046_s09',653.6,10,r'45\times[240\div24]')]:
 rows=J(R/f'pdf_baseline/source_previews/p{book:03d}_redspans.json');row=next(x for x in rows if yy<x['bbox'][1]<yy+1 and x['text'].startswith('=')and((font!=11)or x['spans'][0]['size']>10))
 if book==46:row=next(x for x in rows if yy<x['bbox'][1]<yy+1 and x['bbox'][0]>260)
 origin=next(s['origin']for s in row['spans']if s['text'].startswith('='))
 items.append({'key':key,'book_page':book,'old_bbox':row['bbox'],'baseline_anchor':origin,'font_size':font,'old_visible_row':row['text'],'new_expression':expression,'evidence':str((R/f'pdf_baseline/source_previews/p{book:03d}.png').resolve()),'old_row_count_preserved':1})
late=J(R/'source_geometry_late.json')['new_source_replacements'][0]
items.append({'key':late['key'],'book_page':88,'old_bbox':late['wrong_row_bbox'],'baseline_anchor':late['first_equals_origin'],'font_size':9,'old_visible_row':'=(24+26)×2','new_expression':r'[24+26]\times2','evidence':'actual A4 source rendered below','old_row_count_preserved':1})
assert len(items)==17
# Render all involved current A4 sources once; retain only inspection PNGs.
sp=importlib.util.spec_from_file_location('helper',R.parent/'average_review/patch_pdf.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
old=J(R/'pdf_baseline/current_release.json');doc=fitz.open(R/'bundle/小学同步素养四年级上册数学答案.pdf');imgs={}
for book in sorted({x['book_page']for x in items}):
 src=m.source_for_book(doc,doc[book+3],old,book);page=doc.new_page(width=595,height=841);doc.xref_set_key(page.xref,'Resources',f'<< /XObject << /Inspect {src} 0 R >> >>');xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,b'q /Inspect Do Q');page.set_contents(xref);pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False);imgs[book]=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3).copy();pix.save(R/f'pdf_baseline/source_previews/p{book:03d}.png');doc.delete_page(len(doc)-1)
notes={};files={}
for L in 'ABCD':
 path=P/f'detailed_layout/notes_{L}.json';d=J(path);files[L]=(path,d)
 for n in d['records']:notes[n['key']]=(L,n)
masks=[];added=[]
L,n=notes['p042_s09'];old42=n['local_replacements'][0]['latex'];new42=old42.replace(r'640\div(16\times5)',r'640\div[16\times5]');assert new42!=old42;n['local_replacements'][0]['latex']=new42
existing_sync=[{'key':'p042_s09','id':'p042_s09_local1','old':old42,'new':new42,'reason':'原黑题首式含外中括号，原位local片段只有续行，源码初筛未包含首式故漏检；实际PDF核对同步。'}]
for item in items:
 key=item['key'];L,n=notes[key];assert not n.get('local_replacements'),key
 x0,y0,x1,y1=item['old_bbox'];mask=[x0-.8,y0-.8,x1+.8,y1+.8]
 a=imgs[item['book_page']][math.floor(mask[1]*2):math.ceil(mask[3]*2),math.floor(mask[0]*2):math.ceil(mask[2]*2)].astype(int)
 neutral=(a.max(2)-a.min(2)<30)&(a.max(2)<200);red=(a[:,:,0]>130)&(a[:,:,0]>a[:,:,1]+40)&(a[:,:,0]>a[:,:,2]+40)
 assert neutral.sum()==0,(key,'black pixels',int(neutral.sum()));assert red.sum()>0,(key,'not visible')
 container=[mask[0]-1,mask[1]-1,mask[2]+8,mask[3]+1]
 latex=r'\(\displaystyle='+item['new_expression']+r'\)'
 patch={'rect':mask,'target_rect':container,'latex':latex,'font_size':item['font_size'],'leading':12.8,'baseline_anchor':item['baseline_anchor'],'clear_to_white':True,'kind':'bracket_retention_single_row','align':'left','reason':'仅把该原红续行的外括号保留为中括号；黑首式、后续红行、数值、答语和原基线保持。'}
 n['local_replacements']=[patch];lid=key+'_local1'
 row={**item,'id':lid,'latex':latex,'mask_rect':mask,'container_rect':container,'black_or_neutral_dark_pixels_at_2x':0,'red_pixels_at_2x':int(red.sum()),'question_black_first_row_unchanged':True,'other_red_rows_unchanged':True}
 added.append(row);masks.append({'key':key,'book_page':item['book_page'],'rect':mask,'replacement_local_id':lid,'kind':'replace_one_red_math_row','black_or_neutral_dark_pixels_at_2x':0,'red_pixels_at_2x':int(red.sum()),'new_paint_is_added_after_exclusion':True})
for path,d in files.values():W(path,d)
W(Q/'source_masks.json',{'masks':masks,'mode':'clip_obsolete_red_row_then_paint_baseline_anchored_replacement','page_geometry_unchanged':True,'original_black_first_rows_preserved':True})
W(Q/'new_local_patches.json',{'added_local_patch_count':17,'added_snippet_count':17,'old_math_rows_replaced':17,'records':added,'existing_local_sync':existing_sync,'no_extra_rows':True,'no_numeric_changes':True,'no_original_question_changes':True})
print('Added',len(added),'single-row source patches; all masks0black; expected943snippets/87locals')
