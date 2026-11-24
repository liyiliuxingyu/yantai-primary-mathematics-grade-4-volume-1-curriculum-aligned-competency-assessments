from pathlib import Path
import json,copy
from fractions import Fraction
R=Path(__file__).resolve().parent;P=R/'project'
J=lambda p:json.loads(p.read_text())
records={x['key']:x for n in range(37,73) for x in J(P/f'questions/p{n:03}.json')['records']}
notes={x['key']:x for L in 'BC' for x in J(P/f'detailed_layout/notes_{L}.json')['records']}
sub=J(R/'reaudit_55_72_sub.json')
changes=[]
for key in ['p039_s05','p044_s01']:
 simple=r'\[\begin{aligned}&9\times4\div3\\={}&9\div3\times4\\={}&3\times4\\={}&12\text{（厘米）}\end{aligned}\]'
 why='已在第四单元之后；原红主法先求36再除3，旁注已有先9除3的方法。主法列式仍按边长9乘4条边，再利用乘除性质先9÷3得3，避免较大中间数36。两种数量理解最终同式，只写一遍脱式，旁注改为解释两种理解。'
 note=('同一根铁丝改围图形，总长度不变。按正方形每边9厘米乘4条边列出总长，再平均分成3条边；计算时利用乘除运算的性质，先算9除以3得3，再乘4。'
       '另一种理解是把每条原边都平均分成3小份，四条原边共12小份，每条新边取4小份。两种理解得到同一个简算式，原位已经写出，不在旁边重抄。')
 answer='铁丝总长度不变，先按正方形每边9厘米乘4条边列式，再按等边三角形的3条边平均分。计算时先除以3，再乘4，更便于口算。'+simple+'答：等边三角形的边长是12厘米。'+r'\par 另一数量理解：每条原边平均分成3小份，共12小份，每条新边取4小份，直接得到\(9\div3\times4\)。它与上面的简算式一致，不重复列第二遍脱式。'
 rect=[80,664,440,758] if key=='p039_s05' else [70,92,430,178]
 changes.append({'key':key,'book_page':records[key]['book_page'],'id':records[key]['id'],'why':why,'priority':'recommended_existing_shortcut_to_primary','simple_latex':simple,'new_note_latex':note,'new_answer_latex':answer,'result':12,'original_answer_needs_replacement':True,'original_answer_patch':{'source_rect':rect,'latex':simple+'答：等边三角形的边长是12厘米。','clear_to_white':True,'reason':'已实际看当前PDF主式、红答语与相邻空白，矩形只含原红计算和红答语；需重排题间notes以免新主式和旧负向复用空隙重叠。','coordinate_system':'原A4源坐标，单位pt；39页当前原红主式最终y810.5起，减offset145；44页该处offset0。'},'verification':{'old_value':12,'new_value':12,'intermediate_values':[12,12,12],'quantity_order_preserved':True}})
key='p042_s09'
simple=r'\[\begin{aligned}&640\div[16\times(19-14)]\\={}&640\div(16\times5)\\={}&640\div80\\={}&8\end{aligned}\]'
changes.append({'key':key,'book_page':42,'id':records[key]['id'],'why':'16×5先凑成整十除数80，640÷80可直接求8；现解拆成÷16÷5，反而多一道除法。与前版已订正的p107_s08(15×4先凑60)同型，应统一。简便依据是整十除数与减少运算，不是结果8为整数。','priority':'strong','simple_latex':simple,'new_note_latex':'先算最内层小括号，19减14得5；再把16与5相乘凑成整十除数80，直接用640除以80。这里先求易算的积，比拆成先除16再除5更简便。除数是16与5的积，不是它们的和。','new_answer_latex':'先求最内层的差，再把16与5相乘凑成整十除数80，直接相除。'+simple,'result':8,'original_answer_needs_replacement':True,'original_answer_patch':{'source_rect':[73,596,250,649],'latex':r'\[\begin{aligned}={}&640\div(16\times5)\\={}&640\div80\\={}&8\end{aligned}\]','clear_to_white':True,'reason':'原黑算式保留，红步骤从等号开始。实际当前PDF第46页红步骤y1033.69–1079.44，源offset436，故为源597.69–643.44；框不含上方黑原题及右侧计算题。','coordinate_system':'原A4源坐标，单位pt；当前PDF坐标减436。','alignment_note':'现原黑式首数及旧红等号后首数x约84.29；新局部等号独列，等号后首数须继续落在这个x附近。'},'verification':{'intermediate_values':[8,8,8],'grade_scope':'整数运算顺序与凑整除数；不使用未学知识'}})
# Already uses only powers of ten, but source/second-path steps still move twice.
key='p052_s01';old=r'81.5\times10\times10\\&=815\times10';new=r'81.5\times10\times10\\={}&81.5\times(10\times10)\\={}&81.5\times100'
answer=records[key]['answer_latex'].replace(old,new)
oldnote=r'81.5\times10\times10\\&=815\times10'
note=notes[key]['latex'].replace(oldnote,new)
assert answer!=records[key]['answer_latex'] and note!=notes[key]['latex']
changes.append({'key':key,'book_page':52,'id':records[key]['id'],'why':'另一数量路径先求每千克出汁量后乘10，现仍顺次81.5×10×10，已学小数点变化可先合并10×10=100，一次右移两位；避免中间815。保留每千克数量分析，只把相同的十倍放大合并。','priority':'source_note_consistency','simple_latex':r'\[\begin{aligned}&81.5\times(1000\div100)\times10\\={}&81.5\times10\times10\\={}&81.5\times(10\times10)\\={}&81.5\times100\\={}&8150\text{（克）}\\={}&8.15\text{（千克）}\end{aligned}\]','new_note_latex':note.replace('两种方法的中间结果都是克','第二法在计算时可先把两个10结合成100，一次移动小数点；两种方法的中间结果都是克'),'new_answer_latex':answer,'result':'8.15千克','original_answer_needs_replacement':False,'verification':{'new_value':'8150克=8.15千克','grade_scope':'仅乘10、100与乘法结合律，不用一般小数乘法'}})
key='p054_s07';answer=records[key]['answer_latex']
answer=answer.replace(r'45\div10\times100=4.5\times100=450',r'45\div10\times100=45\times(100\div10)=45\times10=450').replace(r'3.2\times1000\div10=3200\div10=320',r'3.2\times1000\div10=3.2\times(1000\div10)=3.2\times100=320')
note=notes[key]['latex'].replace('④先左移一位再右移两位，合起来右移一位。',r'④先合并变化倍数，\(100\div10=10\)，所以直接算\(45\times10=450\)，小数点只右移一位。').replace('⑧先右移三位再左移一位，合起来右移两位。',r'⑧先合并变化倍数，\(1000\div10=100\)，直接算\(3.2\times100=320\)，小数点只右移两位。')
assert answer!=records[key]['answer_latex'] and note!=notes[key]['latex']
changes.append({'key':key,'book_page':54,'id':records[key]['id'],'why':'第4、8小题notes已说明合并变化，但canonical仍显示先4.5×100及3200÷10的顺次算法。应同步为先合并变化倍数，分别直接乘10或100。前版51页同型已如此写，避免课件源继续逐次搬移。','priority':'source_note_consistency','simple_latex':r'\(45\div10\times100=45\times(100\div10)=45\times10=450\)；\(3.2\times1000\div10=3.2\times(1000\div10)=3.2\times100=320\)。','new_note_latex':note,'new_answer_latex':answer,'result':[450,320],'original_answer_needs_replacement':False,'verification':{'subitems':[4,8],'exact_values_unchanged':True,'grade_scope':'仅小数点移动与合并整数变化倍数'}})
# Subreview read all149 records; inspect its three proposed formulas independently here.
for c in sub['changes']:
 changes.append(c)
coverage=[]
for n in range(37,73):
 rr=[r for r in records.values() if r['book_page']==n]
 coverage.append({'book_page':n,'record_count':len(rr),'checked_keys':[r['key'] for r in rr]})
report={'scope':'当前最新版简便计算二次专项核读，原书37–72页；不复做几何结论。','reviewed_book_pages':list(range(37,73)),'record_count':len(records),'coverage':coverage,'previous_accepted_keys':[x['key'] for x in J(P/'simplify_update/accepted_changes.json')['changes'] if 37<=x['book_page']<=72],'changes':changes,'change_count':len(changes),'root_actual_visual_reviewed_book_pages':[39,42,44],'visual_scope':'仅3张当前PDF页逐张实际view_image核看红主式及空隙；其他题主要读当前题干、答案、notes记录，不冒称本轮全部版面逐页实看。','subreview_report':'reaudit_55_72_sub.json','unchanged_reasons':['几何识别、画高、数图等无简算任务，保留现有结论。','角度一般扣除两角时，没有清楚凑整结构，不强行换括号增加步骤。','已有凑100/1000、分配律、连减先求和、补偿等简算者不重复提出。','比较题已有相同部分/共同因数比较时，不再要求完整求左右结果。','52页瓷砖面积两种路径已产生整百、整十乘积；不为拆而拆改成更长式子。'],'limits':['主式局部坐标基于当前PDF与其receipt逆变换，实际编译仍须量尺寸并检查与notes的复用空隙。','不声称穷尽无限代数写法；只检出本阶段内有实用计算收益的结构。']}
(R/'reaudit_37_72.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(len(records),'records',len(changes),'changes',[c['key'] for c in changes])
