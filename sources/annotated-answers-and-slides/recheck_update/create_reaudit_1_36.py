from pathlib import Path
import json,hashlib,re
R=Path(__file__).resolve().parent; P=R/'project'
J=lambda p:json.loads(p.read_text())
records={x['key']:x for b in range(1,37) for x in J(P/f'questions/p{b:03}.json')['records']}
notes={x['key']:x['latex'] for L in 'ABCD' for x in J(P/f'detailed_layout/notes_{L}.json')['records']}
def equation(lines):return r'\[\begin{aligned}&'+r'\\={}&'.join(lines)+r'\end{aligned}\]'
changes=[]
def early(key,why,explanation,lines,strength='clear_arithmetic_structure'):
 r=records[key];s=equation(lines)
 hint=r'\par\textbf{简便提示（学完运算律后）}\par '+explanation+s
 changes.append({'key':key,'book_page':r['book_page'],'id':r['id'],'why':why,'priority':strength,'simple_latex':s,'new_note_latex':notes[key]+hint,'new_answer_latex':r['answer_latex']+hint,'preserve_original_primary_method':True,'original_answer_needs_replacement':False,'new_value':None})
early('p002_s01','同速度式中的32、34都能先除2；把65乘32/34改成130乘16/17，后者可用整十数乘法口算，原按运算顺序求速度的主法仍保留。',
 '先求速度的主法保留。计算后段路程时，可用整数乘除的关系先算32除以2；若先合并总时间34分钟，也可先算34除以2。只调整数值计算的次序，没有把32分钟改成总时间。',
 [r'130+130\div2\times32',r'130+130\times(32\div2)',r'130+130\times16',r'130+2080',r'2210\text{（米）}'])
changes[-1]['alternative_simple_latex']=equation([r'130\div2\times(2+32)',r'130\div2\times34',r'130\times(34\div2)',r'130\times17',r'2210\text{（米）}'])
changes[-1]['new_note_latex']+=r'先合并时间的一路可简算为：'+changes[-1]['alternative_simple_latex']
changes[-1]['new_answer_latex']+=r'先合并时间的一路可简算为：'+changes[-1]['alternative_simple_latex']
early('p003_s05','现解析已提把58看成60−2，但缺对应简便脱式；补全可避免36乘58的两位数乘法，计算36乘60与36乘2后作差。',
 '前面的括号和除法仍按原顺序求得36。最后把58看成60少2，先多算两份36再减回；两个乘法在同一步完成。',
 [r'36\times58',r'36\times(60-2)',r'36\times60-36\times2',r'2160-72',r'2088'],'explicit_formula_missing_for_existing_hint')

k='p003_s07';r=records[k]
old=equation([r'4\times18\div4-32\div4',r'72\div4-8',r'18-8',r'10\text{（千克）}'])
new=equation([r'4\times18\div4-32\div4',r'(4\div4)\times18-32\div4',r'1\times18-8',r'18-8',r'10\text{（千克）}'])
explanation='总量和已处理量分别分成4份的另法，计算可先做4除以4，避免先求72。两个4虽然数值相同，分别表示每班回收千克数与分批数；这里是运算性质的数值整理，不是把数量含义混在一起。'
assert old in notes[k] and old in r['answer_latex']
label=r'简便提示（学完运算律后）：'+explanation
changes.append({'key':k,'book_page':3,'id':r['id'],'why':'已有另法4×18÷4−32÷4仍先算72；按乘除性质先乘4再除4还原18，并把32÷4同一步算8；保留原3页两树图与主法。','priority':'clear_arithmetic_structure','simple_latex':new,'new_note_latex':notes[k].replace(old,label+new),'new_answer_latex':r['answer_latex'].replace(old,label+new),'preserve_original_primary_method':True,'original_answer_needs_replacement':False,'new_value':10})
early('p005_s05','原解析文字已经指出14÷7=2，但唯一完整脱式仍先算7728；补上按乘法结合整数除法先求14÷7的脱式，避免大乘积及大除法。',
 '除以7只作用在前面整个乘积上，可先用14除以7得到2；括号内的减法与14除以7互不依赖，可同一步算完。',
 [r'(630-78)\times14\div7',r'(630-78)\times(14\div7)',r'552\times2',r'1104'],'explicit_formula_missing_for_existing_hint')
early('p007_s05','最终73×93可把93看成100−7，除乘100外只需求一个73×7，避免按93的十位和个位分别求两个非整百部分积。',
 '括号按原顺序算得93后，把93看成100少7。先多算7份73再减回；乘100与乘7在同一步完成。',
 [r'73\times93',r'73\times(100-7)',r'73\times100-73\times7',r'7300-511',r'6789'],'compensation_near_hundred')
early('p011_s08','现解析提到63拆60与3，却未列简便脱式。25×60先凑1500、25×3得75，可在旁边补全该口算，原除乘两部分同时算的主法保留。',
 '只补充乘法部分的简便计算：把63分成60与3，用乘法分配律分别求积。前面的28除以4仍得7，再与1575相加为1582。',
 [r'63\times25',r'(60+3)\times25',r'60\times25+3\times25',r'1500+75',r'1575'],'explicit_formula_missing_for_existing_hint')
early('p015_s08','48×17可用48=50−2作补偿，把两个因数均两位的乘法改成乘50减乘2。原48×(10+7)仅为常规分位口算；此补偿为可选较顺手结构，不宜把所有分位乘法都新增。',
 '括号与除法照常求得48，最后可把48看成50少2，按乘法分配律同时算50乘17与2乘17。',
 [r'48\times17',r'(50-2)\times17',r'50\times17-2\times17',r'850-34',r'816'],'optional_compensation_improvement')
early('p024_s03','第2季度30+31+30可交换加数让两个30先凑60，当前主解却先得到61。只补天数小算式，保留第三单元原完整应用步骤。',
 '计算季度天数时，两个30天可先合起来凑60，再加31天；这只是合计同样三个月的天数。',
 [r'30+31+30',r'(30+30)+31',r'60+31',r'91\text{（天）}'],'short_grouping_side_note')

k='p025_s17';r=records[k];simple=equation([r'8\times6-6',r'6\times(8-1)',r'6\times7',r'42'])
changes.append({'key':k,'book_page':25,'id':r['id'],'why':'已说少算7份6，却仍只写48减6；反用分配律直接由8份减1份得到7份，更贴合题目的运算律与数量分析。','priority':'minor_structural_consistency','simple_latex':simple,'new_note_latex':r'正确计算中括号内的6应取8份，错式只取1份；含方框的部分相同。因此差就是少算的7份6，反用乘法分配律，无须求方框的值。'+simple,'new_answer_latex':'正确式中的6应乘8，错式只有一份6；两结果相差7份6：'+simple,'preserve_original_primary_method':False,'original_answer_needs_replacement':False,'new_value':42})
k='p030_s10';r=records[k];simple=equation([r'(15+24)\times32',r'39\times32',r'(40-1)\times32',r'40\times32-1\times32',r'1280-32',r'1248\text{（平方米）}'])
changes.append({'key':k,'book_page':30,'id':r['id'],'why':'识图选D本身可不计算，但既然解析给出39×32的面积数值，39接近40，可补乘法分配律补偿法，避免普通两位数乘法。','priority':'clear_arithmetic_structure','simple_latex':simple,'new_note_latex':'先按图认数量：15与24是相邻两块地的宽，32是两块地共同的长。两宽相加后乘共同的长，求合并后长方形面积。豆角区域宽20没有进入算式，所以不在所求总量中，选D。若继续求面积，把39看成40少1：'+simple,'new_answer_latex':'选D。15与24是两块区域的宽，32是共同的长，求两块合并面积。豆角区域宽20不在式中。继续计算时可用39=40−1补偿：'+simple,'preserve_original_primary_method':False,'original_answer_needs_replacement':False,'new_value':1248})
k='p031_s08';r=records[k];simple=equation([r'8\times5\div8\times5',r'(8\div8)\times(5\times5)',r'1\times25',r'25'])
changes.append({'key':k,'book_page':31,'id':r['id'],'why':'与已修p006_s06的同类遗漏。乘8与除8还原，保留两个乘5，利用整数乘除性质直接算5×5，避免先求40；不可误写成末尾除5。','priority':'same_type_as_accepted_change','simple_latex':simple,'new_note_latex':'整数乘除可整理次序：先乘8、再除8会还原，余下两个5仍都是乘数。把8除以8与5乘5同一步算完；不要把末尾的乘5误改为除5。'+simple,'new_answer_latex':'先乘8又除8还原，两个5仍相乘：'+simple,'preserve_original_primary_method':False,'original_answer_needs_replacement':False,'new_value':25})
k='p032_s02';r=records[k]
old=equation([r'4\times(25\times12)',r'4\times300',r'1200\text{（本）}'])
# The saved answer has one literal space before the leading alignment mark.
old_note=old if old in notes[k] else old.replace('aligned}&','aligned} &')
assert old_note in notes[k]
new=equation([r'4\times(25\times12)',r'(4\times25)\times12',r'100\times12',r'1200\text{（本）}'])
an=r['answer_latex'].replace(old,new).replace(old.replace('aligned}&','aligned} &'),new)
assert an!=r['answer_latex']
changes.append({'key':k,'book_page':32,'id':r['id'],'why':'与已采纳p027_s11同类：先按总套数列式的数量思路可保留，但计算先凑4×25=100，避免先做25×12。这不另算第3种数量方法。','priority':'same_type_as_accepted_change','simple_latex':new,'new_note_latex':notes[k].replace('图书总量不变。','图书总量不变。第二种列式仍可按乘法结合律先凑4乘25等于100；只是计算次序优化，不增列新的解法。').replace(old_note,new),'new_answer_latex':an,'preserve_original_primary_method':True,'original_answer_needs_replacement':False,'new_value':1200})

coverage=[{'book_page':b,'record_count':len(J(P/f'questions/p{b:03}.json')['records']),'checked_keys':[x['key'] for x in J(P/f'questions/p{b:03}.json')['records']]} for b in range(1,37)]
assert len({k for c in coverage for k in c['checked_keys']})==len(records)
prior={x['key'] for x in J(P/'simplify_update/accepted_changes.json')['changes']}
assert all(c['key'] not in prior for c in changes)
qa={'scope':'原书1–36页全部canonical题干、答案及对应notes逐record核读；先核对已采纳56处以免重复。本轮只读审查，未修改主源，不处理74页题面争议。','reviewed_book_pages':list(range(1,37)),'record_count':len(records),'coverage':coverage,'new_candidate_count':len(changes),'changes':changes,'recommended_clear_keys':[c['key'] for c in changes if c['priority'] not in ['optional_compensation_improvement','minor_structural_consistency','short_grouping_side_note']],'optional_lower_priority_keys':[c['key'] for c in changes if c['priority'] in ['optional_compensation_improvement','minor_structural_consistency','short_grouping_side_note']],'independent_arithmetic':{'p002_s01':130+130//2*32,'p003_s05':36*58,'p003_s07':(4*18-32)//4,'p005_s05':(630-78)*14//7,'p007_s05':73*93,'p011_s08':63*25,'p015_s08':48*17,'p024_s03':30+31+30,'p025_s17':8*6-6,'p030_s10':39*32,'p031_s08':8*5//8*5,'p032_s02':4*25*12},'unchanged_scope_notes':['已包含完整简便步骤的旧56项全部保留，不因这次复查回滚。','明确要求列竖式、指定运算顺序、按计算器坏键输入的题，保留其题意；不把普通分位乘法在每题重复扩写为新简算。','整十数的自然乘除、已给出的更简便数量方法或直接凭结构判大小，不再为增加修订数量重复加式。','多数几何题只是用内角和等关系直接计算；不把普通加减的任意重排都列作必要修订。'],'visual_scope':'本轮主体是完整源文本核读；未声称将1–36所有现PDF页面重新逐张人工目视检查。候选均不需要修改题干、图形或原A4红主式。'}
(R/'reaudit_1_36.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'records':len(records),'pages':36,'candidates':len(changes),'clear':qa['recommended_clear_keys'],'optional':qa['optional_lower_priority_keys']},ensure_ascii=False))
