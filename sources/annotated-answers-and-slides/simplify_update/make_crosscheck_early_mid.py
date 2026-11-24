from pathlib import Path
from fractions import Fraction
import ast,json,hashlib
r=Path('/workspace/scratch/1facfb035d44/simplify_review')
audit1=json.loads((r/'audit_early.json').read_text());audit2=json.loads((r/'audit_25_44.json').read_text())
allchanges=audit1['changes']+audit2['changes']

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
'p003_s03':(['592-(118*4-215)','592-(472-215)','592-472+215','120+215','335'],'335'),
'p003_s04':(['76*(215-(62+78))','76*75','19*4*75','19*(4*75)','19*300','5700'],'5700'),
'p004_s02':(['9000-(30*270+45*15)','9000-(8100+675)','9000-8100-675','900-675','225','9000-(30*(270+15)+(45-30)*15)'],'225'),
'p004_s03':(['16*3/(4*6)','16*3/24','16*3/(3*8)','16*3/3/8','16/8','2'],'2'),
'p004_s04':(['480*3/(4*6)','480*3/24','480*3/(3*8)','480*3/3/8','480/8','60'],'60'),
'p006_s02':(['(12*15-80)/5','12*15/5-80/5','12*(15/5)-80/5','12*3-16','36-16','20'],'20'),
'p006_s03':(['25*2*2','25*(2*2)','25*4','100'],'100'),
'p006_s06':(['25*8/25*8','(25/25)*(8*8)','1*64','64'],'64'),
'p007_s03':(['25*((160+512)/32)','25*21','25*(20+1)','500+25','525'],'525'),
'p008_s01':(['66*5*8-300','66*(5*8)-300','66*40-300','2640-300','2340','66*8*5-300'],'2340'),
'p008_s03':(['440/(1+3)/5','440/4/5','440/(4*5)','440/20','22'],'22'),
'p011_s07':(['966/(27+19)*45','21*45','(20+1)*45','900+45','945'],'945'),
'p015_s05':(['4000-15*(24+195)','4000-15*219','4000-15*(220-1)','4000-(3300-15)','4000-3300+15','700+15','715'],'715'),
'p015_s07':(['34*(160-(60-15))','34*(160-60+15)','34*(100+15)','34*100+34*15','3400+510','3910'],'3910'),
'p019_s12':(['80*((103+97)-131)','80*69','80*(70-1)','5600-80','5520'],'5520'),
'p019_s13':(['680-85*4/20','680-85*4/(4*5)','680-85*4/4/5','680-85/5','680-17','663'],'663'),
'p020_s02':(['60*4/3','60/3*4','20*4','80'],'80'),
'p023_s04':(['2+8*75','2+2*(4*75)','2+2*300','2+600','602'],'602'),
'p023_s11':(['(540/27+39)*17','59*17','(60-1)*17','1020-17','1003'],'1003'),
'p027_s11':(['25*(4*12)','(25*4)*12','100*12','1200'],'1200'),
'p028_s01':(['1500-665-135','1500-(665+135)','1500-800','700'],'700'),
'p028_s02':(['1200/(4*25)','1200/25/4','1200/(25*4)','1200/100','12'],'12'),
'p028_s03':(['53*16+47*16','(53+47)*16','100*16','1600'],'1600'),
'p028_s04':(['53*16-47*16','(53-47)*16','6*16','96'],'96'),
'p032_s01':(['58*120+42*120','(58+42)*120','100*120','12000'],'12000'),
'p032_s04':(['41*18+18*19','(41+19)*18','60*18','1080','18*(19+18)+(41-18)*18','18*37+23*18','(37+23)*18','41*(19+18)-(41-18)*19','41*19+41*18-(41*19-18*19)'],'1080'),
'p042_s01':(['24*6/8','24/8*6','3*6','18'],'18'),
'p043_s03':(['120*8/(8-2)','120*8/6','120/6*8','20*8','160','120+120*2/(8-2)','120+120*2/6','120+120/6*2','120+20*2','120+40'],'160'),
'p044_s03':(['6*20','6*24-6*(24/6)','6*24-6*4','6*(24-4)','6*20','120'],'120'),
'p044_s04':(['(275+(275*2-50))/25','(275+(550-50))/25','(275+500)/25','275/25+500/25','11+20','31','275/25*3-50/25','11*3-2','33-2','275/25+(275*2-50)/25','11+(550-50)/25','11+500/25'],'31'),
}
assert len(checks)==len(allchanges)==30
items=[]
for c in allchanges:
 expressions,result=checks[c['key']]
 values=[calc(s) for s in expressions]
 assert len(set(values))==1 and values[0]==calc(result),(c['key'],values)
 items.append({'key':c['key'],'book_page':c['book_page'],'id':c['id'],'arithmetic_equivalent':True,'exact_result':result,'checked_expressions':expressions,'grade_scope_ok':True,'grade_scope_condition':'前三单元仅作“学完运算律后”的旁注，保留当前单元原算法。' if c['book_page']<25 else '仅整数运算律、减法与乘除性质；未用小数乘除、分数算术、方程或比例。','multiplication_quantity_order_ok':True,'genuine_simplification':True,'disposition':'修正术语并补步骤后采用' if c['key'] in ['p004_s03','p004_s04'] else '补中间步骤后采用' if c['key']=='p043_s03' else '可采用'})
assert calc('25*8/(25*8)')==1
assert calc('12*18')==216
corrections=[{
 'key':'p004_s03','severity':'required_before_delivery','issue':'审核why用了“约去共同因数3”，正文用同时除以3说明，且从÷24直接跳到÷8；数学正确，但宜避免借用未学约分术语，并呈现先乘3再除3的依据。',
 'replacement_why':'24=3×8；除以24等于先除以3再除以8，先乘3又除3还原16，因此可直接16÷8。',
 'replacement_simple_latex':r'\[\begin{aligned}&16\times3\div(4\times6)\\={}&16\times3\div24\\={}&16\times3\div(3\times8)\\={}&16\times3\div3\div8\\={}&16\div8\\={}&2\text{（袋）}\end{aligned}\]',
 'replacement_explanation':'简便提示（学完运算律后）：24=3×8，除以24就是依次除以3和8。前面先乘3、这里再除以3，仍是每箱的16袋，只需再除以8。',
 'implementation':'仅替换原建议中的简便提示与对应脱式；保留其前面当前单元连续平均分原法和末尾答语。'
},{
 'key':'p004_s04','severity':'required_before_delivery','issue':'同p004_s03；审核why用了“约去共同因数3”，需改为除以积和先乘后除还原的已学语言。',
 'replacement_why':'24=3×8；除以24等于先除以3再除以8，先乘3又除3还原480，接着480÷8。',
 'replacement_simple_latex':r'\[\begin{aligned}&480\times3\div(4\times6)\\={}&480\times3\div24\\={}&480\times3\div(3\times8)\\={}&480\times3\div3\div8\\={}&480\div8\\={}&60\text{（块）}\end{aligned}\]',
 'replacement_explanation':'简便提示（学完运算律后）：24=3×8，除以24就是依次除以3和8。先乘3再除以3，还原为每箱480块，再除以8即可。',
 'implementation':'仅替换原建议中的简便提示与对应脱式；保留当前单元原法与完整答语。'
},{
 'key':'p043_s03','severity':'required_before_delivery','issue':'原建议从含(8−2)的式子直接跳到交换乘除，合并了括号求值与改变计算次序两层动作；主法和另法都应先显式代入6。',
 'replacement_simple_latex':r'\[\begin{aligned}&120\times8\div(8-2)\\={}&120\times8\div6\\={}&120\div6\times8\\={}&20\times8\\={}&160\text{（米）}\end{aligned}\]答：实际平均每天修160米。',
 'replacement_alternative_latex':r'\[\begin{aligned}&120+120\times2\div(8-2)\\={}&120+120\times2\div6\\={}&120+120\div6\times2\\={}&120+20\times2\\={}&120+40\\={}&160\text{（米）}\end{aligned}\]答：实际平均每天修160米。',
 'implementation':'对应改simple_latex、new_answer_latex、new_note_latex中的另法，以及原位红主式局部替换latex，保持全部交付一致。'
}]
observations=[
 {'key':'p032_s04','status':'pass','finding':'已实看原PDF图；顶宽18米、上段高19米、下段高18米、底长41米，与题面TikZ一致。横分、纵分、补形均为1080平方米，展开分配律只是计算变形，不是第四个几何方法。'},
 {'key':'p019_s13','status':'pass_with_optional_step','finding':'20已显式拆成4×5，正文已说明乘4与除4抵消，数学清楚；若要与p004更统一，可在680−85×4÷(4×5)之后添680−85×4÷4÷5，再写680−85÷5。此步可选，不是数值问题。'},
 {'key':'p006_s06','status':'pass','finding':'第一式64，带括号第二式1。只有第一式可以合并乘25与除25，未把第二个乘8误移进除数。'},
 {'key':'p006_s02','status':'pass','finding':'12×15按每盒12个乘15盒；分总数与已发数到5班的另思路只在整除情形展开，用具体数量说明即可，无需引入“除法分配律”名词。'},
 {'key':'p042_s01','status':'pass','finding':'袋数18；收入12×18=216元。12为每袋单价、18为袋数，顺序符合每份数×份数。'},
 {'key':'p044_s04','status':'pass','finding':'主式把275÷25与500÷25同一步得到11+20；三份法、两年级分别换算的数量分析保留，运算律写法不单独增算一种解题方法。'},
 {'keys':['p027_s11','p028_s03','p028_s04','p032_s01'],'status':'pass','finding':'“先合并每份量”与“先分别列总量”的数量分析可同时保留；简算归于同一计算结构这一限制已明确，不宜据此宣传新增独立方法。'},
 {'scope':'all_early_19','status':'pass_with_condition','finding':'所用补偿、结合、分配及连除仅作为“学完运算律后”的旁注；不得替换前三单元用来教学运算顺序的原解，更不能写成当时已学方法。'}
]
out={'scope':{'inputs':['audit_early.json','audit_25_44.json'],'input_sha256':{f:hashlib.sha256((r/f).read_bytes()).hexdigest() for f in ['audit_early.json','audit_25_44.json']},'early_changes':19,'mid_changes':11,'checked_count':30,'all_original_question_text_and_proposed_notes_answers_read':True,'independent_arithmetic':'30项全部用有理数精确算术独立核对，各列出的中间式等值。另验p006_s06第二空=1及p042_s01收入=216。','visual_scope':'本次二审额外实际打开p032完整原PDF渲染图，核对几何原图；其他项目读原题JSON及建议正文，不冒称再次逐页实看。'},'overall':{'mathematical_value_errors_found':0,'multiplication_quantity_order_errors_found':0,'required_corrections_count':3,'grade_terminology_corrections':['p004_s03','p004_s04'],'intermediate_step_corrections':['p043_s03'],'blockers_remaining_after_corrections':False,'no_master_changes_made':True},'items':items,'required_corrections':corrections,'observations':observations}
(r/'qa_crosscheck_early_mid.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(r/'qa_crosscheck_early_mid.json');print('checked',len(items),'required corrections',len(corrections),'math errors',0)
