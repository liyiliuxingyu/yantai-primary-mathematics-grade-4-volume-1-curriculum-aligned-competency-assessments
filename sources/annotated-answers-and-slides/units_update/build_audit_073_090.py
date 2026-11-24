from pathlib import Path
import json,re,collections,hashlib
R=Path(__file__).resolve().parent;P=R/'project'
J=lambda p:json.loads(Path(p).read_text())
notes={n['key']:(L,n) for L in 'ABCD' for n in J(P/f'detailed_layout/notes_{L}.json')['records']}
records=[r for pg in range(73,91) for r in J(P/f'questions/p{pg:03}.json')['records']]
unit_heads=['摄氏度','平方千米','平方米','平方分米','平方厘米','千米/时','米/分','米/秒','千米','厘米','毫米','分米','千克','毫升','千升','千瓦时','分钟','小时','万册','大格','秒','克','吨','米','元','角','分','人','个','本','册','台','次','部','块','件','箱','辆','页','瓶','袋','套','棵','把','张','名','份','组','升','下','度']
rx=re.compile('（('+'|'.join(map(re.escape,sorted(unit_heads,key=len,reverse=True)))+r'(?:，[^（）]*)?)）')
def ascii_units(s):return rx.sub(lambda m:'('+m.group(1)+')',s)
manual={}
def put(k,field,new):manual[(k,field)]=new
k='p075_s02';r=next(x for x in records if x['key']==k);n=notes[k][1]
old=r['answer_latex'];start=old.index(r'\[\begin{aligned}');end=old.index(r'\end{aligned}\]',start)+len(r'\end{aligned}\]')
conv=r'\[\begin{aligned}2\text{米}&=(100\times2)\text{厘米}\\&=200\text{厘米}\end{aligned}\]'
put(k,'answer_latex',old[:start]+conv+old[end:])
put(k,'latex',r'先统一身高与水深的单位：\[2\text{米}=200\text{厘米}\]'+n['latex'])
k='p079_s04';r=next(x for x in records if x['key']==k);n=notes[k][1]
old=r['answer_latex'];old=old.replace(r'；\(1\)千克\(=1000\)克。',r'。\[1\text{千克}=1000\text{克}\]')
a=r'\[\begin{aligned}&156\times40\\&=6240\text{（克）}\\&=6.24\text{（千克）}\end{aligned}\]'
b=r'\[\begin{aligned}&156\times40\\&=6240\text{(克)}\end{aligned}\]\[6240\text{克}=6.24\text{千克}\]'
assert a in old;put(k,'answer_latex',old.replace(a,b))
put(k,'latex',n['latex']+r'\[6240\text{克}=6.24\text{千克}\]')
k='p081_s07';r=next(x for x in records if x['key']==k);n=notes[k][1]
put(k,'answer_latex',r'填\(52000\)。面积单位进率为100：\[1\text{平方米}=100\text{平方分米}\]\[\begin{aligned}520\text{平方米}&=(520\times100)\text{平方分米}\\&=52000\text{平方分米}\end{aligned}\]')
put(k,'latex',n['latex']+r'\[520\text{平方米}=52000\text{平方分米}\]')
k='p081_s08';r=next(x for x in records if x['key']==k);n=notes[k][1]
put(k,'answer_latex',r'填\(587.35\)。先将角和分化成元：\[3\text{角}=0.3\text{元}\]\[5\text{分}=0.05\text{元}\]再合并钱数：\[\begin{aligned}587\text{元}3\text{角}5\text{分}&=(587+0.3+0.05)\text{元}\\&=587.35\text{元}\end{aligned}\]')
put(k,'latex',r'将角和分分别化成元：\[1\text{角}=0.1\text{元}\]\[1\text{分}=0.01\text{元}\]把587元、\(0.3\)元、\(0.05\)元合并，角对应十分位、分对应百分位。\[587\text{元}3\text{角}5\text{分}=587.35\text{元}\]不能把3角5分写成\(0.035\)元，或把元数也跟着缩小。')
k='p081_s09';r=next(x for x in records if x['key']==k);n=notes[k][1]
put(k,'answer_latex',r'依次填\(6\)、\(260\)。先分出整千克对应的克数：\[6260\text{克}=6000\text{克}+260\text{克}\]\[6000\text{克}=6\text{千克}\]所以\[6260\text{克}=6\text{千克}260\text{克}\]')
put(k,'latex',r'\[1000\text{克}=1\text{千克}\]先从6260克中取出6个1000克。剩下260克不足1千克，作为第二个单位的零头保留。\[6260\text{克}=6\text{千克}260\text{克}\]因此两空分别写整千克数与余下克数，不能把余数再当成小数千克填在克的位置。')
k='p081_s10';r=next(x for x in records if x['key']==k);n=notes[k][1]
put(k,'answer_latex',r'填\(3.294\)。厘米换米除以\(100\)：\[\begin{aligned}329.4\text{厘米}&=(329.4\div100)\text{米}\\&=3.294\text{米}\end{aligned}\]')
put(k,'latex',r'\[1\text{米}=100\text{厘米}\]由厘米化米是小单位化大单位，应除以100。把\(329.4\)的小数点向左移动两位，注意原小数位仍保留。\[329.4\text{厘米}=3.294\text{米}\]不能只移动一位，也不能向右移使数反而更大。')
k='p081_s11';r=next(x for x in records if x['key']==k);n=notes[k][1]
put(k,'answer_latex',r'依次填\(275\)、\(90\)。先分成整数吨与小数吨：\[275.09\text{吨}=275\text{吨}+0.09\text{吨}\]小数吨换成千克：\[\begin{aligned}0.09\text{吨}&=(0.09\times1000)\text{千克}\\&=90\text{千克}\end{aligned}\]所以\[275.09\text{吨}=275\text{吨}90\text{千克}\]')
put(k,'latex',r'先将\(275.09\)吨分成整数部分275吨与小数部分\(0.09\)吨。整数吨数直接保留，小数吨按下列进率换算：\[1\text{吨}=1000\text{千克}\]\[0.09\text{吨}=90\text{千克}\]所以\[275.09\text{吨}=275\text{吨}90\text{千克}\]\(0.09\)吨不是9千克，换算时不能漏掉进率中的一个10。')
k='p082_s07';r=next(x for x in records if x['key']==k);n=notes[k][1]
put(k,'answer_latex',r'选C。先统一单位：\[4\text{厘米}=0.04\text{米}\]王兵比张宇高\(0.04\)米，故张宇\(1.23-0.04=1.19\)米。')
put(k,'latex',r'两个成绩的单位不同，先统一单位：\[4\text{厘米}=0.04\text{米}\]再与1.23米比较。王兵的成绩比张宇高，因此求张宇时要从王兵的成绩中减去差，不能反而加上4厘米。')

conversion_cases=[
 {'key':'p075_s02','class':'length','identities':['2米=200厘米'],'rate_or_numeric_calculation_preserved':'100×2=200','fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'应用选择风险说明，无数字填空；题旁换算单列。'},
 {'key':'p079_s04','class':'mass','identities':['1千克=1000克','6240克=6.24千克'],'fields':['answer_latex','latex'],'needs_change':True,'separate_from_calculation':'156×40=6240(克)完成后，独立下一行6240克=6.24千克；不保留纯数字6240=6.24的伪连等。'},
 {'key':'p081_s04','class':'number_rewrite_in_亿_and_rounding','identities':['331000000=3.31亿','331000000≈3亿'],'fields':['answer_latex','latex'],'needs_change':False,'reason':'两式原已独立显示且亿不加括号；准确改写用=，近似数仍用≈。两空已印亿，填数值3.31、3。'},
 {'key':'p081_s07','class':'area','identities':['1平方米=100平方分米','520平方米=52000平方分米'],'fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'题目空格后已印平方分米，填52000不带单位。'},
 {'key':'p081_s08','class':'money_compound_to_元','identities':['3角=0.3元','5分=0.05元','587元3角5分=587.35元','1角=0.1元','1分=0.01元'],'fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'题目空格后已印元，填587.35不带单位。'},
 {'key':'p081_s09','class':'mass_single_to_compound','identities':['1000克=1千克','6000克=6千克','6260克=6千克260克'],'same_unit_decomposition':'6260克=6000克+260克','fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'两空后已印千克、克，只填6和260。'},
 {'key':'p081_s10','class':'length','identities':['1米=100厘米','329.4厘米=3.294米'],'fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'空格后已印米，填3.294不带单位。'},
 {'key':'p081_s11','class':'mass_decimal_to_compound','identities':['1吨=1000千克','0.09吨=90千克','275.09吨=275吨90千克'],'same_unit_decomposition':'275.09吨=275吨+0.09吨','fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'两空后已印吨、千克，只填275和90。'},
 {'key':'p082_s07','class':'length_in_application','identities':['4厘米=0.04米'],'fields':['answer_latex','latex'],'needs_change':True,'printed_answer_unit':'选择仍只选C，换算行在解析中，不重复改题目选项。'},
]
changes=[];examined_fields=0;black_preserved=[];ordinary_count=0;conversion_count=0
for r in records:
 k=r['key'];L,n=notes[k];fields=[(f'questions/p{r["book_page"]:03}.json','answer_latex',r['answer_latex']),(f'detailed_layout/notes_{L}.json','latex',n['latex'])]
 for i,v in enumerate(n.get('local_replacements',[])):
  if v.get('kind','').startswith('black') or r'\color{black}' in v['latex']:
   black_preserved.append({'key':k,'field':f'local_replacements[{i}].latex','kind':v.get('kind'),'sha256':hashlib.sha256(v['latex'].encode()).hexdigest()});continue
  fields.append((f'detailed_layout/notes_{L}.json',f'local_replacements[{i}].latex',v['latex']))
 fc=[]
 for file,field,old in fields:
  examined_fields+=1
  new=ascii_units(manual.get((k,field),old))
  if new==old:continue
  isconv=(k,field) in manual
  if isconv:conversion_count+=1
  else:ordinary_count+=1
  # Original numbers must not be lost; added conversion identities may repeat them.
  if not isconv:assert re.sub(r'[（）()]','',old)==re.sub(r'[（）()]','',new)
  else:assert set(re.findall(r'\d+(?:\.\d+)?',old))<=set(re.findall(r'\d+(?:\.\d+)?',new)),k
  fc.append({'file':file,'field':field,'old':old,'new':new,'classification':'conversion_own_display_line_no_unit_parentheses' if isconv else 'existing_result_unit_parentheses_to_ASCII','reason':'实际单位换算另起行，换算行单位不括号；保留计算、单位进率及数值。' if isconv else '只将计算结果单位已有中文括号改为英文ASCII()；题号、班级、数学分组与自然答语单位不改。'})
 if fc:changes.append({'key':k,'book_page':r['book_page'],'id':r['id'],'field_changes':fc})
report={'scope':{'book_pages':[73,90],'record_count':len(records),'records_read':[r['key'] for r in records],'fields_examined':examined_fields,'red_fields_include_answer_note_and_existing_red_locals':True},'changes':changes,'changed_question_count':len(changes),'changed_field_count':sum(len(x['field_changes']) for x in changes),'ordinary_result_unit_format_field_count':ordinary_count,'conversion_field_count':conversion_count,'actual_conversion_cases_checked':conversion_cases,'actual_conversion_case_count':len(conversion_cases),'conversion_cases_needing_change':sum(x['needs_change'] for x in conversion_cases),'unchanged_record_keys':[r['key'] for r in records if r['key'] not in {c['key'] for c in changes}],'black_locals_preserved':black_preserved,'rules':{'original_question_options_tables_diagrams_not_touched':True,'existing_mathematical_grouping_preserved':True,'existing_angle_degree_notation_preserved':True,'natural_answer_sentence_units_preserved':True,'numerical_meaning_explanations_not_misclassified':True,'q4_classroom_answer_B_preserved':True,'p78_five_black_patches_preserved':len(black_preserved)==5,'source_read_only':True},'manual_nonconversion_examples':[{'key':'p081_s12','reason':'数的小数点移动与扩大缩小不是单位换算，保持纯数公式。'},{'key':'p085_s12','reason':'按钟面格数与每格5分钟求时长是数量关系计算，不是时分单位换算；仅现有(大格)/(分钟)括号改ASCII。'},{'key':'p086_s03','reason':'角度70°/100°保留规范度符号，未做单位转换。'},{'key':'p076_s02','reason':'表格已知等级/人数列头、四（1）班等不是结果单位括号，不改。'}]}
W=lambda p,d:p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
W(R/'audit_helper_073_090.json',report)
print(json.dumps({k:v for k,v in report.items() if k not in ['changes','actual_conversion_cases_checked','unchanged_record_keys','black_locals_preserved']},ensure_ascii=False,indent=2))
