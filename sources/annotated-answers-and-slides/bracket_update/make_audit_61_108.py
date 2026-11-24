from pathlib import Path
import json,re
R=Path('bracket_review');P=R/'project'
records={x['key']:x for n in range(61,109) for x in json.loads((P/f'questions/p{n:03}.json').read_text())['records']}
notes={}
for file in (P/'detailed_layout').glob('notes_*.json'):
 for x in json.loads(file.read_text()).get('records',[]):notes[x['key']]=(file.name,x)
S={
'p073_s03':[(r'(32+32)\div4',r'[32+32]\div4')],
'p075_s01':[(r'(500+480)\div7',r'[500+480]\div7'),(r'100+(100+160+90-70)\div7',r'100+[100+160+90-70]\div7'),(r'100+(260+20)\div7',r'100+[260+20]\div7')],
'p075_s04':[(r'(340+262)\div7',r'[340+262]\div7')],
'p076_s01':[(r'95+(1-1)\div3',r'95+[1-1]\div3')],
'p077_s01':[(r'(34+34+34)\div6',r'[34+34+34]\div6'),(r'(34\times3)\div(3\times2)',r'[34\times3]\div(3\times2)')],
'p077_s05':[(r'(56+48)\div2',r'[56+48]\div2')],
'p077_s06':[(r'(310+310+160)\div5',r'[310+310+160]\div5'),(r'(620+160)\div5',r'[620+160]\div5')],
'p077_s07':[(r'785-(310+316)',r'785-[310+316]')],
'p079_s03':[(r'(340+440)\div5',r'[340+440]\div5'),(r'150+(40+22-32)\div5',r'150+[40+22-32]\div5'),(r'150+(62-32)\div5',r'150+[62-32]\div5')],
'p083_s03':[(r'246\div(96\div16)',r'246\div[96\div16]')],
'p088_s02':[(r'(24+26)\times2',r'[24+26]\times2')],
'p089_s03':[(r'(20+20)\div4',r'[20+20]\div4')],
'p089_s07':[(r'96+(2-2)\div5',r'96+[2-2]\div5'),(r'(98+192+190)\div5',r'[98+192+190]\div5'),(r'(290+190)\div5',r'[290+190]\div5')],
'p091_s01':[(r'(184+180)\div4',r'[184+180]\div4'),(r'88+(8+4)\div4',r'88+[8+4]\div4'),(r'(184+100)\div4',r'[184+100]\div4')],
'p091_s03':[(r'100-(800-784)\div8',r'100-[800-784]\div8')],
'p091_s04':[(r'2500+(300-200)',r'2500+[300-200]')],
'p095_s01':[(r'40\times(175-75-67)',r'40\times[175-75-67]'),(r'40\times(100-67)',r'40\times[100-67]')],
'p096_s03':[(r'(260+1\times100)\div3',r'[260+1\times100]\div3'),(r'(260+100)\div3',r'[260+100]\div3')],
'p099_s05':[(r'960\div(48\div4)',r'960\div[48\div4]')],
'p104_s02':[(r'4.68\times(5\times2)',r'4.68\times[5\times2]'),(r'468\times12-468\times(12\div6)',r'468\times12-468\times[12\div6]')],
'p107_s08':[(r'840\div(15\times4)',r'840\div[15\times4]')]
}
changes=[];field_n=0;row_n=0
for k,repls in S.items():
 rec=records[k];filename,note=notes[k];fields=[]
 sources=[('answer_latex',rec['answer_latex']) ,('note_latex',note.get('latex',''))]+[(f'local_replacements[{i}].latex',loc.get('latex','')) for i,loc in enumerate(note.get('local_replacements',[]))]
 for field,old in sources:
  if k=='p091_s03' and field=='note_latex':continue
  new=old;used=[]
  for a,b in repls:
   if a in new:
    count=new.count(a);new=new.replace(a,b);used.append({'old':a,'new':b,'occurrences':count})
  if new!=old:
   # Typesetting only: bracket type changes cannot alter mathematical content or row count.
   norm=lambda s:s.replace('[','(').replace(']',')')
   assert norm(old)==norm(new),(k,field)
   assert old.count(r'\\')==new.count(r'\\'),(k,field)
   fields.append({'field':field,'old':old,'new':new,'row_replacements':used})
   field_n+=1;row_n+=sum(x['occurrences'] for x in used)
 assert any(f['field']=='answer_latex' for f in fields)
 reason='原外层中括号内仍有加减乘除运算，续行保留同一中括号；括号内算成一个数时再去掉。'
 if k=='p077_s01':reason+='把三份34写成34×3后，整体仍作被除数，故仍保留[]；随后利用乘除运算性质拆成34×(3÷3)÷2时，原整体结构已被合法变形，可以去掉该外括号。'
 if k=='p095_s01':reason+='内层减去和变为连续减法后，外层40仍乘整个差，因此外[]不能随内层展开改成()。'
 if k=='p099_s05':reason+='下一行960÷48×4是利用除法性质真正拆开原除数整体，说明已有，可去掉该外括号。'
 changes.append({'key':k,'book_page':int(k[1:4]),'id':rec['id'],'pdf_page':int(k[1:4])+4,'question_file':f'questions/p{int(k[1:4]):03}.json','note_file':f'detailed_layout/{filename}','fields':fields,'reason':reason,'new_steps':0,'results_changed':False,'question_text_changed':False,'original_pdf_formula_needs_attention': k in ['p083_s03','p088_s02','p095_s01','p099_s05','p104_s02','p107_s08']})
obj={'scope':{'book_pages':[61,108],'question_record_count':len(records),'active_questions_read':48,'active_notes_read':len([k for k in notes if k in records]),'source':'bracket_review/project','pdf':'bracket_review/bundle/小学同步素养四年级上册数学答案.pdf','review_kind':'只读源码逐行括号形式审核，不重新改题意/解法/结果；题干和首行给定算式保留原样。'},'changes':changes,'unchanged_or_exceptions':[{'key':'p101_s02','reason':'只给出一个综合算式240×[(128+147)÷25]，没有后续计算行，不存在外[]提前替换。'},{'key':'p091_s03','field':'note_latex','reason':'旁注复核直接引用已算出的784，总式从100−(100×8−784)÷8开始，本身没有外[]承接；本次只改answer_latex中确实承接前行外[]的100−(800−784)÷8，不强制把独立起式的()统一成[]。'}],'verification':{'changed_questions':len(changes),'changed_fields':field_n,'replacement_occurrences':row_n,'only_bracket_types_changed':True,'no_rows_added_or_removed':True,'optional_parameters_excluded':True,'all_question_latex_untouched':True}}
(R/'audit_61_108.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(obj['verification'],ensure_ascii=False))
for x in changes:print(x['key'],[(z['field'],len(z['row_replacements'])) for z in x['fields']])
