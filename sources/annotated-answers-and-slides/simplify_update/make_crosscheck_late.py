from pathlib import Path
from fractions import Fraction
import ast,json,hashlib
r=Path('/workspace/scratch/1facfb035d44/simplify_review')
files=['audit_65_84.json','audit_85_108.json']
changes=[c for fn in files for c in json.loads((r/fn).read_text())['changes']]
def calc(s):
 def f(n):
  if isinstance(n,ast.Expression): return f(n.body)
  if isinstance(n,ast.Constant): return Fraction(str(n.value))
  if isinstance(n,ast.BinOp):
   a,b=f(n.left),f(n.right)
   if isinstance(n.op,ast.Add): return a+b
   if isinstance(n.op,ast.Sub): return a-b
   if isinstance(n.op,ast.Mult): return a*b
   if isinstance(n.op,ast.Div): return a/b
  raise ValueError(ast.dump(n))
 return f(ast.parse(s,mode='eval'))
checks={
'p073_s01':[['(112+105+119)/3','112+(7-7)/3','112+0/3','112']],
'p073_s03':[['(8+15+24+17)/4','((8+24)+(15+17))/4','(32+32)/4','64/4','16']],
'p073_s04':[['30*3-24-16','30*3-(24+16)','90-40','50']],
'p073_s10':[['20*4-18*3','20+(20-18)*3','20+2*3','20+6','26']],
'p075_s01':[['(70+120+170+240+190+130+60)/7','((70+130)+(240+60)+(120+170+190))/7','(200+300+(290+190))/7','(200+300+480)/7','980/7','140','100+((70+30)+(20+140)+90-(30+40))/7','100+(100+160+90-70)/7','100+(260+20)/7','100+280/7','100+40']],
'p075_s04':[['(80+87+83+85+88+97+82)/7','((87+83)+(88+82)+(80+85+97))/7','(170+170+(165+97))/7','(340+262)/7','602/7','85+(12-5)/7','85+7/7','85+1','86']],
'p076_s01':[['67*3-65-66','67+(67-65)+(67-66)','67+2+1','67+3','70'],['(95+96+94)/3','(95+(96+94))/3','(95+190)/3','285/3','95'],['90*3-(88+92)','270-180','90'],['95*3-93-95','95+(95-93)','95+2','97'],['(83+86+83)/3','83+(86-83)/3','83+3/3','83+1','84']],
'p077_s01':[['(16+15+20+18+14+19)/6','((16+18)+(15+19)+(20+14))/6','(34*3)/(3*2)','34*3/3/2','34/2','17']],
'p077_s04':[['12*3-11*2','12+(12-11)*2','12+1*2','12+2','14']],
'p077_s05':[['(56+56-8)/2','56-8/2','56-4','52']],
'p077_s07':[['157*5-(150+159+157+160)','157*5-((150+160)+(159+157))','785-(310+316)','785-626','159']],
'p079_s03':[['(123+145+156+172+184)/5','((156+184)+(123+145+172))/5','(340+(268+172))/5','(340+440)/5','780/5','150+((6+34)+22-(27+5))/5','150+(40+22-32)/5','150+(62-32)/5','150+30/5','150+6','156']],
'p080_s02':[['1+2+8+12','(1+2)+(8+12)','3+20','23']],
'p081_s02':[['512/16*4','512/(16/4)','512/4','128']],
'p083_s05':[['79.5+(79.5+23.9)','(79.5+79.5)+23.9','159+23.9','182.9']],
'p083_s06':[['362-(158*2-68)','362+68-158*2','430-316','114']],
'p094_s05':[['140+(150-140)*4/(6+4)','140+10*4/10','140+40/10','140+4','144','(140*6+150*4)/(6+4)','(840+600)/10','1440/10']],
'p104_s02':[['468*12-468*(12/(5+1))','468*12-468*(12/6)','468*12-468*2','468*(12-2)','468*10','4680']],
'p107_s08':[['840/(15*(81-77))','840/(15*4)','840/60','14']],
'p108_s02':[['40*11/(11-3)','40*11/8','40/8*11','5*11','55','40+(40*3)/(11-3)','40+120/8','40+15']]
}
assert len(checks)==len(changes)==20
items=[]
for c in changes:
 groups=checks[c['key']]
 for g in groups:
  vals=[calc(s) for s in g]
  assert len(set(vals))==1,(c['key'],vals)
 items.append({'key':c['key'],'book_page':c['book_page'],'id':c['id'],'math_equivalence':'通过','exact_results':[str(calc(g[0])) for g in groups],'checked_expressions':groups,'stage_knowledge':'通过：整数运算律、连减连除/乘除关系、平均数先总后分与移多补少；小数部分仅加减和乘10。','multiplication_quantity_order':'通过；涉及单价/每份量/差额的乘法，均按每份量×份数。','simplification_reason':'通过；通过交换结合配对、合并同类份数、凑整、移多补少或减少大数运算体现易算，未仅因得数为整数而判简便。','substantive_issue':None})
# Independently validate all four interval counts from the source question's raw values.
boys=[4.9,5.1,4.4,5.0,4.8,5.2,4.1,5.0,4.7,4.9,5.1,4.6,5.2,4.2,4.8,5.3,5.0,5.1,4.5,5.2,5.0]
girls=[5.1,4.8,4.7,5.2,4.9,5.3,4.3,5.1,4.9,5.0,5.2,4.2,4.8,5.1,4.7,5.3,5.0,4.6,5.2,4.9,5.0,5.2,4.8]
def count(values): return [sum(x<=4.2 for x in values),sum(4.3<=x<=4.6 for x in values),sum(4.7<=x<=4.9 for x in values),sum(x>=5 for x in values)]
assert count(boys)==[2,3,5,11] and count(girls)==[1,2,8,12]
assert calc('16*(128/4)')==512
assert calc('4.68*(5*(12/(5+1)))')==Fraction('46.8')
assert calc('4680/100')==Fraction('46.8')
focus=[
 {'key':'p075_s01','finding':'100厘米基准法独立使用各观测值的偏差：多出20+70+140+90+30=350，少30+40=70，净多280；280÷7=40，再加100=140。没有复用未知总和980，不存在循环论证。各减法中间量非负，未引入负数。'},
 {'key':'p075_s04','finding':'85分基准：87与83是±2，88与82是±3，先抵消；85本身偏差0，只剩97多12与80少5，净多7，分7份补1得86。评分表确为80、87、83、85、88、97、82。'},
 {'key':'p079_s03','finding':'150克基准：多出6+22+34=62，不足27+5=32，净多30，平均补6得156。表中原称量123、145、156、172、184均对应，不把样本平均强认成每个土豆实重。'},
 {'key':'p081_s02','finding':'先把已知16拆成4×4，与括号内除以4的运算相互抵消，原式等于所填数×4；再求512÷4=128，最后代回128检验。求数过程未先假设128，无循环；未用方程、分数或一般小数乘除。'},
 {'key':'p094_s05','finding':'加权平均的数量逻辑正确，课内表达仍用移多补少：6人组平均140，总量等于6份140；4人组总量比4份140多(150−140)×4=40。多出的40分摊给总人数10，基准每份补4，得144。没有假定每个原个体恰为组平均，也没有直接把140、150平均。'},
 {'key':'p076_s01','finding':'逐列核对原评分表，五空按原表位置分别为四(1)4号李老师70、四(1)3号平均95、四(2)5号李老师90、四(2)3号刘老师97、四(2)4号平均84；基准思路与表格对应无错位。'},
 {'key':'p080_s02','finding':'从原题全部21名男生、23名女生数据独立重新计数，四区间分别2/3/5/11与1/2/8/12，班级44人，表格及凑20求女生人数均正确。'},
 {'key':'p083_s05','finding':'79.5与79.5的0.5部分凑成1，先合成159再加23.9减少一次小数加法；这是利用小数加法结合律的易算结构，不是单凭最终得数是否为整数。'},
 {'key':'p104_s02','finding':'主法4.68仅乘10，按点位移动可用；另法先换为468分再做整数运算，未借用未学的一般小数乘法。两组买五送一付10双，46.8元正确。'}
]
out={'scope':{'inputs':files,'input_sha256':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in files},'checked_count':20,'count_65_84':16,'count_85_108':4,'all_original_questions_and_proposed_notes_answers_read':True,'original_tables_read':['p075_s04','p076_s01','p077_s07','p079_s03'],'options_read':['p094_s05'],'curriculum_scope_read':'project/curriculum_scope.json','mathematics_check':'全部中间式用精确有理数独立核对；统计数据另独立计数。','visual_check':'本次只读文字、表格及建议，不声称再次实看PDF页面。'},'conclusion':{'substantive_math_issues_found':0,'stage_knowledge_issues_found':0,'quantity_order_issues_found':0,'required_corrections':[],'blocking_issue':False,'all_20_suggestions_mathematically_usable':True,'master_files_changed':False},'items':items,'focused_findings':focus}
(r/'qa_crosscheck_late.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(r/'qa_crosscheck_late.json');print('checked',len(items),'substantive issues',0)
