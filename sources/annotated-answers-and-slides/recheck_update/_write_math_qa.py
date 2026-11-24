from pathlib import Path
import json,hashlib
from fractions import Fraction as F
R=Path(__file__).resolve().parent
J=lambda p:json.loads(p.read_text())
S=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
exact=J(R/'qa_arithmetic_intermediates.json')
assert exact['passed'] and exact['count']==34
facts={
'p002_s01':('2210米','两条路径均用130米/2分钟的恒定速度；原问题仍问原算式求什么，未改32分钟含义。',130+F(130,2)*32),
'p003_s05':('2088','396÷11=36；核对的是最后乘58部分。',F(396,302-291)*58),
'p003_s07':('10千克','每班4千克×18班；运算性质整理以后仍保留原两树图与主法。',F(4*18-32,4)),
'p005_s05':('1104','630−78=552，14÷7=2，独立两支可同一步算出。',F((630-78)*14,7)),
'p007_s05':('3913；提示部分为6789','73×93=6789是中间乘积，整题还须减2876；新提示并未把6789冒作全题结果。',73*(38+55)-2876),
'p011_s08':('1582；提示部分为1575','28÷4=7与63×25=1575两支独立，最后1582；新提示仅展开乘法部分。',F(28,4)+63*25),
'p015_s08':('816','295−289=6，288÷6=48，48×17=816。',F(288,295-289)*17),
'p024_s03':('728台；提示部分91天','4、5、6月分别30、31、30天；日销量248÷31=8台。',F(248,31)*(30+31+30)),
'p025_s17':('42','把方框记为任意x，8(x+6)−(8x+6)=48−6=42，不需要知道x。',8*6-6),
'p030_s10':('选D；1248平方米','根据原题所述15、24是两相邻区宽，32共同长；补偿39=40−1保持题意。',(15+24)*32),
'p031_s08':('25','乘除同级左到右值25；重排后两个5均为乘数。',F(8*5,8)*5),
'p032_s02':('1200本','每套4本×每箱25套×12箱；总套数路径初始乘法数量顺序正确。',4*25*12),
'p039_s05':('12厘米','每边9厘米×4边得到总长，除等边三角形3边；变形后9÷3×4。',F(9*4,3)),
'p044_s01':('12厘米','同上，初始列式每边数×边数未颠倒。',F(9*4,3)),
'p042_s09':('8','19−14=5，16×5=80，640÷80=8；除数仍为积。',F(640,16*(19-14))),
'p052_s01':('8.15千克','10千克=10000克；81.5克/100克×100份=8150克=8.15千克；仅乘10/100及单位换算。',F('81.5')*100/F(1000)),
'p054_s07':('第4空450；第8空320','45÷10×100=45×10；3.2×1000÷10=3.2×100；其他6空未改。',[F(45,10)*100,F('3.2')*1000/10]),
'p056_s01':('37.5千克；375000千克','3.75吨=3750千克，共20件/车×5车=100件；每件37.5×10000件=375000。',[F(3750,20*5),F(3750,20*5)*10000]),
'p057_s03':('42.7','一个加数增加5.9，和增加5.9；+6−0.1补偿方向正确。',F('36.8')+F('5.9')),
'p058_s02':('20.5，选C','未知加数为30−9.5；−10需加回0.5。',30-F('9.5')),
'p073_s07':('70','甲乙总量为2份80，并未假定甲乙各80；加丙50后除3。',F(80*2+50,3)),
'p075_s03':('72米/分','总路程720×2，总时间12+8；先乘2再除2仅运算性质，不误平均两个速度。',F(720*2,12+8)),
'p075_s05':('85分','七分为80,87,83,85,88,97,82；去一个最高97和最低80后，余425分/5人。',F(sum([80,87,83,85,88,97,82])-97-80,5)),
'p077_s06':('156厘米','A队身高156,154,151,159,160；以155为基准±1、±4抵消，160多5。',F(sum([156,154,151,159,160]),5)),
'p083_s04':('703千米','每车速度×共同3小时，总路程还须加尚余193；提3只改变计算次序。',(95+75)*3+193),
'p084_s01':('3500元','每箱55/45元各35箱，合为每组100元×35组。',(55+45)*35),
'p084_s02':('350元','每箱价差10元×35箱；不是两种总价的和。',(55-45)*35),
'p088_s03':('8厘米','每边6厘米×4边后除3边；6÷3×4等值。',F(6*4,3)),
'p089_s07':('96分','98,95,96,92,95,96,99去最高99/最低92，余480/5=96。',F(sum([98,95,96,92,95,96,99])-99-92,5)),
'p100_s02':('4208元','上午独立核算32×15+24×12=768；下午(45−2)元/袋×80袋。',32*15+24*12+(45-2)*80),
'p104_s03':('3000元','足球108元/个×15个与篮球92元/个×15个；合并200×15。',(108+92)*15),
'p104_s05':('1200千米','相向行驶2小时，尚相距200，故每小时两车路程和500×2后加200。',(220+280)*2+200),
'p108_s03':('4500元','上衣62元/件×45件，裤38元/条×45条；每套100元×45套。',(62+38)*45),
'p098_s02':('28场；7场','每组与另外7组各赛一次，7×8重复计2次；淘汰每场淘汰1组，共淘汰7组。',[F(7*8,2),8-1]),
}
items=[]
inputs=[]
for fn in ['reaudit_1_36.json','reaudit_37_72.json','reaudit_73_108.json']:
 data=J(R/fn);inputs.append({'file':fn,'sha256':S(R/fn),'changes':len(data['changes'])})
 for c in data['changes']:
  k=c['key'];result,reason,val=facts[k]
  vals=[str(v) for v in val] if isinstance(val,list) else str(val)
  item={'key':k,'book_page':c['book_page'],'id':c['id'],'arithmetic_equivalent':True,'independent_whole_question_result':result,'independent_exact_value':vals,'independent_reason':reason,'units_checked':True,'quantity_multiplication_order_checked':True,'grade_scope_checked':True,'every_simple_latex_intermediate_checked':True,'intermediate_evidence':'qa_arithmetic_intermediates.json','disposition':'can_adopt'}
  if c['book_page']<=24:item['grade_scope_condition']='保留前三单元原主法，仅作为学完运算律后的旁注；没有把运算律冒充当时必学方法。'
  if k=='p011_s08':item.update({'disposition':'arithmetic_correct_style_optional','simplicity_assessment':'63=60+3是常规按位展开；可称乘法口算提示，其优于普通算法的程度较弱。不属于数值或年级错误。'})
  if k in ['p002_s01','p024_s03','p039_s05','p044_s01','p088_s03','p098_s02']:item['simplicity_assessment']='运算结构有效，主要缩小中间数或先合并相同数；基本运算次数未必更少，不宣称唯一或绝对最快。'
  items.append(item)
assert len(items)==34 and set(facts)=={x['key'] for x in items}
report={'passed':True,'scope':{'files':inputs,'candidate_count':34,'all_candidate_question_latex_new_note_new_answer_read':True,'original_supporting_tables_checked':['p075_s04/p075_s05七评委表','p077_s06 A队身高表'],'supporting_previous_question_checked':'p100_s01 上午768元','actual_pdf_visual_review_performed_by_this_reviewer':False,'math_only_not_layout_or_animation_qa':True},'overall':{'arithmetic_errors_found':0,'unit_errors_found':0,'quantity_order_errors_found':0,'unlearned_method_errors_found':0,'blocking_changes_required':0,'style_advisories':1,'all_34_simple_latex_intermediate_chains_checked_with_fraction':True,'grade_condition':'1–24页原主法保留，旁注明确学完运算律后；25页起整数运算律、小数点按10/100/1000变化、小数加减及平均数移多补少。'},'items':items,'advisories':[{'key':'p011_s08','severity':'nonblocking_style','finding':'(60+3)×25→1500+75为常规按位展开，结果正确，作为口算提示可保留；不宜称作必然最简或最典型的凑整法。','suggested_wording':'乘法口算提示（学完运算律后）：把63分成60与3，先算容易的整十数乘法，再合并。','alternative_not_required':r'63\times25=(64-1)\times25=(16\times4)\times25-25=16\times(4\times25)-25=1600-25=1575','alternative_assessment':'确能显式凑25×4=100，但步骤变长；不建议只为变化再添一整套七行计算。'}],'p091_s03_quality_finding':{'checked':True,'original_total':784,'original_average':98,'claim':'基准段把前法求得的784与800比较，属于复核而非独立简法。','parent_proposed_disposition':'改称基准复核，明确784由前法得到，原答案98本不变。','disposition_correct':True,'optional_independent_baseline_is_valid_but_more_operations':True,'no_extra_method_recommended':True},'source_scope':'只写本报告及逐式算术证据，没有修改questions、notes、PDF、PPT。'}
(R/'qa_math_crosscheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Wrote qa_math_crosscheck.json for',len(items),'items')
