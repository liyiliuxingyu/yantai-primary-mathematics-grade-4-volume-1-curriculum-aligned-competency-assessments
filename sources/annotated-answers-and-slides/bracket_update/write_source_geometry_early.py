from pathlib import Path
import json,re
import fitz
R=Path(__file__).resolve().parent;G=R/'geometry_early'
# Keys locate each visible red first continuation line in standalone original A4 form.
lookup={
'p003_s04':(3,'= 76 × (215 −140)'),
'p003_s05':(3,'= (396 ÷ 11) × 58'),
'p003_s06':(3,'= 184 ÷ (560 ÷ 70)'),
'p007_s02':(7,'= 3744 −38 × 6'),
'p007_s03':(7,'= 25 × (672 ÷ 32)'),
'p007_s04':(7,'= (275 ÷ 55) × 45'),
'p007_s05':(7,'= 73 × 93 −2876'),
'p007_s06':(7,'= 65 × (960 ÷ 12)'),
'p007_s07':(7,'= 336 ÷ (252 ÷ 36)'),
'p011_s06':(11,'= 1008 ÷ (105 ÷ 5)'),
'p015_s06':(15,'= 180 ÷ (72 ÷ 4)'),
'p015_s07':(15,'= 34 × (160 −45)'),
'p015_s08':(15,'= (288 ÷ 6) × 17'),
'p019_s12':(19,'= 80 × (200 −131)')
}
audit=json.loads((R/'audit_1_60.json').read_text());repls={}
for p in audit['patches']:
 if p['file'].startswith('questions/'):
  repls[p['key']]=p['replacements']
records=[]
for key,(book,text) in lookup.items():
 lines=json.loads((G/f'p{book:03d}_red.json').read_text())
 matches=[x for x in lines if x['text']==text];assert len(matches)==1,(key,matches)
 first=matches[0];origin=first['spans'][0]['origin'];x0,y0=origin
 group=[x for x in lines if abs(x['spans'][0]['origin'][0]-x0)<.01 and y0-.01<=x['spans'][0]['origin'][1]<=y0+32]
 assert len(group)==3,(key,group)
 group.sort(key=lambda x:x['spans'][0]['origin'][1]);rect=fitz.Rect(group[0]['bbox'])
 for x in group[1:]:rect|=fitz.Rect(x['bbox'])
 expanded=rect+(-.7,-.7,.7,.7)
 q=json.loads((R/f'project/questions/p{book:03d}.json').read_text());qr=next(x for x in q['records']if x['key']==key)
 block=re.search(r'\\begin\{aligned\}(.*?)\\end\{aligned\}',qr['answer_latex'],re.S).group(1)
 rows=block.split('\\\\');assert len(rows)==4
 newrows=[]
 for row in rows[1:]:
  for rr in repls[key]:
   if row==rr['old']:row=rr['new']
  expr=re.sub(r'^\s*(?:&=|=\{\}&|&)','',row)
  newrows.append('={}&'+expr)
 firstchanged=next((p for p in repls[key] if p['block_index_zero_based']==0),None);assert firstchanged
 records.append({'key':key,'book_page':book,'current_pdf_page_one_based':book+4,'a4_source_size_pt':[595,841],
 'visible_original_main_formula_needs_patch':True,'old_math_rect':list(expanded),'exact_span_union':list(rect),
 'first_equals_origin':origin,'input_font_size_pt':10,'observed_pdf_font_size_pt':first['spans'][0]['size'],
 'baseline_spacing_pt':[group[i+1]['spans'][0]['origin'][1]-group[i]['spans'][0]['origin'][1]for i in range(2)],
 'old_red_row_count':3,'original_black_first_row_should_be_omitted':True,
 'black_original_formula_is_raster_and_preserved':True,
 'old_red_rows':[x['text']for x in group],
 'new_red_latex_rows':newrows,'suggested_red_latex':r'\[\begin{aligned}'+r'\\'.join(newrows)+r'\end{aligned}\]',
 'geometry_evidence_png':str(G/f'p{book:03d}.png'),'red_spans':group,
 'note':'rect仅含原红三行续式；黑题干首式在上方，重新插入时不要重复。'} )
# p008 has no bracket mistake in actual original main solution; other methods live in explanation.
records.append({'key':'p008_s03','book_page':8,'current_pdf_page_one_based':12,'a4_source_size_pt':[595,841],
 'visible_original_main_formula_needs_patch':False,
 'old_red_row_count':4,'original_black_first_row_should_be_omitted':False,
 'reason':'实际A4主式是440÷(3+1)÷5→440÷4÷5→110÷5→22，无中括号提前消失。候选改动属于已有题旁解析中的方法二440÷[(3+1)×5]和方法三[440−440÷(3+1)×3]÷5，只需更新对应note公式，不改此原位主式。',
 'original_visible_main_rows':['440 ÷ (3 + 1) ÷ 5','= 440 ÷ 4 ÷ 5','= 110 ÷ 5','= 22（米）'],
 'first_equals_origin':[250.16000366210938,523.1610107421875],
 'input_font_size_pt':10,'observed_pdf_font_size_pt':9.9626,'baseline_spacing_pt':15.4425,
 'geometry_evidence_png':str(G/'p008.png')})
out={'input_pdf':'bracket_review/bundle/小学同步素养四年级上册数学答案.pdf','baseline_receipt':'bracket_review/pdf_baseline/current_release.json',
'coordinate_system':'所有old_math_rect及origin均为source_for_book提取的原A4页595×841坐标，非展开PDF页面坐标。',
'pages_actually_rendered_and_viewed':[3,7,8,11,15,19],
'questions_audited':len(records),'visible_main_patches_needed':sum(x['visible_original_main_formula_needs_patch']for x in records),
'records':records,
'additional_note':'p015_s07除了原位三行续式外，题旁简便提示中的两行外层中括号也需按audit_1_60.json更新；该提示由编译note处理，不要重复覆盖原位式。'}
(R/'source_geometry_early.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('wrote',len(records),'records; main patches',out['visible_main_patches_needed'])
