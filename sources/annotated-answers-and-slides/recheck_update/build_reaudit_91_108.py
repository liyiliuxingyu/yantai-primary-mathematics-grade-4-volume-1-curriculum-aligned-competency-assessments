from pathlib import Path
import json,re,hashlib
R=Path('p74_review');P=R/'project'
J=lambda p:json.loads(p.read_text())
notes={n['key']:n['latex'] for L in 'CD' for n in J(P/f'detailed_layout/notes_{L}.json')['records']}
records={q['key']:q for b in range(91,109) for q in J(P/f'questions/p{b:03}.json')['records']}
def aligned(rows):return r'\[\begin{aligned}&'+r'\\={}&'.join(rows)+r'\end{aligned}\]'
def replace_math(body,token,new):
 matches=[m for m in re.finditer(r'\\\[.*?\\\]',body,re.S) if token in m.group().replace(' ','')]
 assert len(matches)==1,(token,len(matches));m=matches[0]
 return body[:m.start()]+new+body[m.end():]
changes=[]
def add(k,why,rows,note_replaces=(),answer_intro='',priority='recommended'):
 q=records[k];formula=aligned(rows);token=rows[0];na=replace_math(q['answer_latex'],token,formula);nn=replace_math(notes[k],token,formula)
 for a,b in note_replaces:
  assert a in nn,(k,a);nn=nn.replace(a,b)
 if answer_intro:
  spot=na.index(formula);na=na[:spot]+answer_intro+na[spot:]
 changes.append({'key':k,'book_page':q['book_page'],'id':q['id'],'why':why,'priority':priority,'simple_latex':formula,'new_note_latex':nn,'new_answer_latex':na,'original_answer_needs_replacement':False,'pdf_action':'本次更新题间notes中的计算及对应canonical/PPT；原位填值或已简便的主法均保持。','verification':{'all_rows_equal':True,'result':{'p100_s02':4208,'p104_s03':3000,'p104_s05':1200,'p108_s03':4500,'p098_s02':28}[k],'quantity_order_preserved':True,'no_new_grade_method':True}})
add('p100_s02','另法同乘80的两项仍分别算3600、160，再与768混合相减。利用乘法分配律先合并成43×80，减少一个乘积及一次三数加减；保留先列销售额减服务费的数量分析，不新增第三种解法。',[r'768+45\times80-2\times80',r'768+(45-2)\times80',r'768+43\times80',r'768+3440',r'4208\text{（元）}'],note_replaces=[('另法先算核桃销售总额，再扣80袋各2元的总服务费；','另法先按核桃销售总额减总服务费列式，计算时用乘法分配律把共同的80合并，只求每袋实收43元的80倍；')],answer_intro='列出总销售额减总服务费后，利用乘法分配律先合并同乘80的两项，再计算。')
add('p104_s03','另一数量思路仍先算108×15和92×15两个大积；共同乘15，可先把108与92凑成200，明显减少计算量。主法原本已简便，保留。',[r'108\times15+92\times15',r'(108+92)\times15',r'200\times15',r'3000\text{（元）}'],note_replaces=[('另法分别用各自单价乘15，求两类球的总价再相加，两种方法是同一批球的两种分组。','另法先按两类球分别列出总价式，再用乘法分配律合并共同的15，把108与92先凑成200；保留两种数量分析，不把相同的简算结构再计作新方法。'),('另法：分别求足球、篮球总价再相加。','另法：分别列两种球的总价，再合并共同份数简算。')],answer_intro='分别列出两类球的总价后，用乘法分配律把108与92先凑200，不必先求两个大积。')
add('p104_s05','另法两车路程同乘2，仍先算440与560；利用分配律先把220与280凑500，更直接。第一次尚未相遇的判断与尚余200均不改变。',[r'220\times2+280\times2+200',r'(220+280)\times2+200',r'500\times2+200',r'1000+200',r'1200\text{（千米）}'],note_replaces=[('另法分别求两车2小时的路程，再加中间未行段，不能把尚余段从已行路程中减去。','另法先分别列两车2小时的路程，计算时把同乘2的两项用乘法分配律合并，220与280先凑500，最后加中间未行的200千米。'),('另法：分别求甲、乙两车路程，再加尚余距离。','另法：分别列两车已行路程，再提取共同的2简算。')],answer_intro='分别列两车已行路程后，用乘法分配律把220与280先凑500，再加尚余距离。')
add('p108_s03','另一数量思路仍先求62×45、38×45两个大积。两项同乘45，先把62与38凑100，只需100×45，明显比2790+1710简便。',[r'62\times45+38\times45',r'(62+38)\times45',r'100\times45',r'4500\text{（元）}'],note_replaces=[('另法按上衣单价乘45件、裤子单价乘45条，求两项总价再相加；','另法先按上衣单价乘45件、裤子单价乘45条列出两项总价，计算时用乘法分配律把62与38先凑成100；'),('方法二：分别求两种衣物总价','方法二：分别列两种衣物总价，再合并简算')],answer_intro='分别列出上衣与裤子总价后，利用乘法分配律合并共同的45，先凑整百单价100。')
add('p098_s02','循环赛原7×8÷2先求56再除2，可利用8能被2整除，先算8÷2=4，再算7×4；保持每场重复统计两次的理由和淘汰赛7场不变。因数很小，属可采用的次要简化，优先级低于四处明显凑整漏项。',[r'7\times8\div2',r'7\times(8\div2)',r'7\times4',r'28\text{（场）}'],note_replaces=[('所以最后除以2。','所以要除以2。列式后利用8能被2整除，可先算8除以2再乘7，减少中间数。')],answer_intro='列式后先算8除以2，再乘7，运用整数乘除运算的性质。',priority='secondary')
coverage=[{'book_page':b,'record_count':len(J(P/f'questions/p{b:03}.json')['records']),'checked_keys':[q['key'] for q in J(P/f'questions/p{b:03}.json')['records']]} for b in range(91,109)]
out={'scope':{'book_pages':list(range(91,109)),'record_count':len(records),'read_all_questions_answers_notes':True,'source_root':str(P),'old56_change_keys_in_range':['p094_s05','p104_s02','p107_s08','p108_s02'],'not_reproposing_old56':True},'coverage':coverage,'changes':changes,'change_count':len(changes),'actually_visually_checked_book_pages':[98], 'separate_quality_finding':[{'key':'p091_s03','issue':'题间所称另法以100作基准，直接沿用原式总数784；此法实际依赖主法求和，没有独立展现净差的求法。不是数值错误，也不是本次五条简算变更之一。','optional_independent_baseline_latex':aligned([r'100-[(100\times6-464)-(160-100)\times2]\div8',r'100-[(600-464)-60\times2]\div8',r'100-(136-120)\div8',r'100-16\div8',r'100-2',r'98\text{（本）}']),'explanation':'后6天比每天100本少136本，前2天比每天100本多120本，净少16本，再平均到8天。这能独立完成基准法，但操作较多，不应冒称比总数法更简便。'}], 'no_change_rationale':[{'keys':['p091_s01','p091_s02','p091_s04'],'reason':'原有移多补少方法已经给出，保持原题扫描疑读条件；未将稍换分组或数值读法当新增简法。'},{'keys':['p094_s02','p095_s01','p095_s02','p095_s03','p099_s03','p099_s04','p099_s05','p103_s08','p103_s09','p103_s10','p107_s05','p107_s06','p107_s07','p107_s08'],'reason':'现计算题均有合法凑整、乘法分配/结合、减法性质或除以商等结构；p099_s05先960÷48得20也是合适易算结构，不为少一行而强换。'},{'keys':['p093_s06','p095_s06','p095_s07','p096_s01','p100_s01','p100_s03','p100_s04','p104_s01','p104_s04','p108_s01','p108_s04'],'reason':'其余顺算数量关系已清楚或已有基准/换算另法；没有能显著凑整、减少复杂乘除的可确认新变换，不能只因结果为整数或同一式换序就强改。'},{'keys':['p094_s09','p103_s04','p103_s05','p103_s06','p103_s07','p107_s02','p107_s03','p107_s04'],'reason':'原题明确要求竖式/验算，应保留这种指定算法；不拿口算补偿替代指定竖式。'}]}
(R/'reaudit_91_108_sub.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print({'records':len(records),'changes':len(changes),'file':str(R/'reaudit_91_108_sub.json')})
