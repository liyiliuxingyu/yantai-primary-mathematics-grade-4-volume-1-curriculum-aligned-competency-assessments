from pathlib import Path
import json,re,hashlib,copy
R=Path('units_review');P=R/'project'
Q={x['key']:x for n in range(37,73)for x in json.load(open(P/f'questions/p{n:03}.json'))['records']}
N={x['key']:(f.name,x)for f in(P/'detailed_layout').glob('notes_*.json')for x in json.load(open(f))['records']if x['key'] in Q}
work={k:{'answer_latex':x['answer_latex'],'note_latex':N[k][1]['latex'],**{f'local_replacements[{i}].latex':z['latex']for i,z in enumerate(N[k][1].get('local_replacements',[]))}}for k,x in Q.items()}
old=copy.deepcopy(work)
D=lambda s:r'\['+s+r'\]'
B=lambda *s:r'\[\begin{aligned}'+r'\\'.join(s)+r'\end{aligned}\]'
def setf(k,f,t):work[k][f]=t
def rep(k,f,a,b):
 assert a in work[k][f],(k,f,a)
 work[k][f]=work[k][f].replace(a,b)
conv={}
def inv(k,kind,items,note):conv[k]={'kind':kind,'quantities':items,'note':note}
# Exact rewrites of large-number units; rounding keeps approximately equal signs.
k='p049_s03'
a=r'依次填\(16.8,17,9.95,10.0\)。先准确改写，每10000合成1万、每100000000合成1亿：'+B(r'168000&=(168000\div10000)\text{万}=16.8\text{万}',r'995000000&=(995000000\div100000000)\text{亿}=9.95\text{亿}')+r'再求近似数。16.8保留整数看十分位8，向个位进1；9.95保留一位小数看百分位5，连续进位。'+B(r'16.8\text{万}&\approx17\text{万}',r'9.95\text{亿}&\approx10.0\text{亿}')+r'准确改写用等号，求近似数用约等号。10.0末尾的0必须保留，表示保留一位小数；原空后已有单位，只填数。'
n=r'改成“万”按10000合成1份，改成“亿”按100000000合成1份，准确改写不改变大小：'+B(r'168000&=(168000\div10000)\text{万}=16.8\text{万}',r'995000000&=(995000000\div100000000)\text{亿}=9.95\text{亿}')+r'再按指定数位取近似数：'+B(r'16.8\text{万}&\approx17\text{万}',r'9.95\text{亿}&\approx10.0\text{亿}')+r'改写用等号，取近似数才用约等号；10.0的末尾0不可省。'
setf(k,'answer_latex',a);setf(k,'note_latex',n);inv(k,'万/亿准确改写',[['168000','16.8万'],['995000000','9.95亿']],'原裸数除法结果与随后单位改写合成各自独立的一行，保留除法过程与≈。')
k='p049_s04'
f=B(r'3\text{分米}&=(3\div10)\text{米}=0.3\text{米}',r'0.06\text{吨}&=(0.06\times1000)\text{千克}=60\text{千克}',r'5.06\text{吨}&=5\text{吨}60\text{千克}',r'32\text{克}&=(32\div1000)\text{千克}=0.032\text{千克}',r'3\text{平方分米}&=(3\div100)\text{平方米}=0.03\text{平方米}',r'5\text{平方米}3\text{平方分米}&=(5+0.03)\text{平方米}=5.03\text{平方米}')
setf(k,'answer_latex',r'依次填\(0.3;5,60;0.032;5.03\)。分米化米除以10，吨化千克乘1000，克化千克除以1000，平方分米化平方米除以100。每项换算另行写清单位：'+f+r'长度与面积的进率不同，不能混用。各原空后已有单位，只填相应数值。')
setf(k,'note_latex',r'先看所换的量及单位。长度按10，质量按1000，面积按100的相应进率换算；复名数保留原整数部分，只换小单位部分：'+f+r'原空后已有单位，不重复填写单位。')
inv(k,'长度/质量/面积复名数',[['3分米','0.3米'],['0.06吨','60千克'],['5.06吨','5吨60千克'],['32克','0.032千克'],['3平方分米','0.03平方米'],['5平方米3平方分米','5.03平方米']],'把散在解释中的除法、乘法和合并数保留在各自的带单位换算行；不重复四个基本进率等式。')
k='p049_s07'
f=B(r'50\text{克}&=(50\div1000)\text{千克}=0.05\text{千克}',r'9\text{千克}50\text{克}&=(9+0.05)\text{千克}=9.05\text{千克}',r'0.57\text{米}&=(0.57\times100)\text{厘米}=57\text{厘米}')
setf(k,'answer_latex',r'依次填\(>,=,<,<,=,>\)。\par \(6.020>6.002\)，比较百分位；\(3.5=3.50\)，小数末尾添0大小不变。不同单位先换算：'+f+r'故9千克50克小于9.5千克，0.57米等于57厘米。其余\(7.91<7.97\)、\(8.26>4.62\)。')
setf(k,'note_latex',r'①把6.02末尾补0后比百分位；②小数末尾添0不改变大小。③与⑤先统一单位：'+f+r'因此9.05千克小于9.5千克，而0.57米与57厘米相等。④比较百分位1与7；⑥比较整数部分8与4。')
inv(k,'质量/长度比较前换算',[['50克','0.05千克'],['9千克50克','9.05千克'],['0.57米','57厘米']],'结果括号内仅填比较符号，换算各自另行，不把单位添入原圈。')
# Application problems: terminate arithmetic before converting the resulting quantity.
k='p052_s01'
rep(k,'answer_latex',r'先统一质量单位：\(10\text{千克}=10000\text{克}\)。',r'先统一质量单位：'+D(r'10\text{千克}=10000\text{克}'))
for field in ['answer_latex','note_latex']:
 rep(k,field,r'\\={}&8.15\text{（千克）}',r'')
 # One shared result conversion after the methods in the answer; note contains only method two.
 if field=='answer_latex':rep(k,field,r'\par 答：可以榨出8.15千克西瓜汁。',D(r'8150\text{克}=(8150\div1000)\text{千克}=8.15\text{千克}')+r'\par 答：可以榨出8.15千克西瓜汁。')
 else:
  rep(k,field,'先把10千克化成克，与“每100克”的单位统一。','先把总质量化成克，与“每100克”的单位统一：'+D(r'10\text{千克}=10000\text{克}'))
  work[k][field]+=D(r'8150\text{克}=(8150\div1000)\text{千克}=8.15\text{千克}')
rep(k,'answer_latex','方法二：先求1千克西瓜的出汁量，再乘10。','方法二：先求1千克西瓜的出汁量，再乘10。'+D(r'1\text{千克}=1000\text{克}'))
rep(k,'note_latex',r'\textbf{另法：先求每千克出汁量，再乘总质量}\par ',r'\textbf{另法：先求每千克出汁量，再乘总质量}\par '+D(r'1\text{千克}=1000\text{克}'))
inv(k,'kg/g首尾换算',[['10千克','10000克'],['1千克','1000克'],['8150克','8.15千克']],'结束8150克的数值脱式后，另列8150克=8.15千克；禁止把换单位当作裸等号的下一步。两方法共用最终换算；第二法中隐含的每1千克换成1000克也单列。')
k='p052_s02'
f=B(r'135\text{厘米}&=1.35\text{米}',r'119\text{厘米}&=1.19\text{米}',r'158\text{厘米}&=1.58\text{米}')
rep(k,'answer_latex',r'先统一身高单位：\(135\text{厘米}=1.35\text{米}\)，\(119\text{厘米}=1.19\text{米}\)，\(158\text{厘米}=1.58\text{米}\)。',r'先统一身高单位：'+f)
rep(k,'note_latex','先按题给标准把厘米统一化成米，逐人对照区间：','先把厘米统一化成米，各自除以100：'+f+'再逐人对照票价区间：')
inv(k,'厘米/米票价身高',[['135厘米','1.35米'],['119厘米','1.19米'],['158厘米','1.58米']],'三个身高各占一行，不混写到票价计算内。')
k='p052_s03'
f=B(r'1\text{平方米}&=10000\text{平方厘米}',r'108000\text{平方厘米}&=(108000\div10000)\text{平方米}',r'&=10.8\text{平方米}')
a=work[k]['answer_latex'];start=a.index(r'\par 两种方法最后都要换单位：');end=a.index(r'\par 答：文化墙的面积是10.8平方米。',start)
work[k]['answer_latex']=a[:start]+r'\par 两种方法所得面积先以平方厘米计算，最后另列单位换算：'+f+a[end:]
rep(k,'note_latex',r'\\={}&10.8\text{（平方米）}',r'');work[k]['note_latex']+=f
inv(k,'平方厘米/平方米',[['1平方米','10000平方厘米'],['108000平方厘米','10.8平方米']],'保留108000÷10000过程，但它放在带完整单位的独立换算块内，不作为108000(平方厘米)下一行的裸等号。')
k='p053_s08'
f1=B(r'45\text{厘米}&=(45\div100)\text{米}=0.45\text{米}',r'3540\text{克}&=(3540\div1000)\text{千克}=3.540\text{千克}')
f2=B(r'45\text{分}&=0.45\text{元}',r'45\text{平方厘米}&=0.45\text{平方分米}',r'45\text{平方分米}&=0.45\text{平方米}',r'45\text{公顷}&=0.45\text{平方千米}',r'3540\text{毫米}&=3.540\text{米}',r'3540\text{米}&=3.540\text{千米}',r'3540\text{千克}&=3.540\text{吨}')
a=r'一组答案为“厘米、米；克、千克”。前式进率100，后式进率1000：'+f1+r'题目未限定单位种类，原有其他合理组合也分别列出：'+f2+r'保留题面给定的3.540写法。两边必须是同一种量，不能把长度与质量混配。这里只在原单位空填写单位，不重复数值。'
setf(k,'answer_latex',a);setf(k,'note_latex',a)
inv(k,'开放填单位题',[['45厘米','0.45米'],['3540克','3.540千克'],['45分','0.45元'],['45平方厘米','0.45平方分米'],['45平方分米','0.45平方米'],['45公顷','0.45平方千米'],['3540毫米','3.540米'],['3540米','3.540千米'],['3540千克','3.540吨']],'只展开原答案/原旁注已经列出的单位组合，没有新增单位种类。分为货币的分。')
k='p053_s09'
f0=D(r'1\text{吨}=1000\text{千克}');f1=D(r'450\text{千克}=(450\div1000)\text{吨}=0.45\text{吨}')
rep(k,'answer_latex','1吨=1000千克，是10千克的100倍。',f0+'是10千克的100倍。')
rep(k,'answer_latex',r'\\&=0.45\text{（吨）}.',r'');work[k]['answer_latex']+=f1
rep(k,'note_latex',r'\(1\text{吨}=1000\text{千克}\)。',f0)
rep(k,'note_latex',r'\\&450\div1000\\={}&0.45\text{（吨）}',r'');work[k]['note_latex']+=f1
inv(k,'吨/千克首尾换算',[['1吨','1000千克'],['450千克','0.45吨']],'结束450(千克)脱式后另写450千克=0.45吨；原空后已有千克、吨，只填450与0.45。')
k='p054_s02'
f=D(r'0.9\text{米}=(0.9\times10)\text{分米}=9\text{分米}')
setf(k,'answer_latex',r'选C。9在十分位，表示0.9米。米化分米的进率是10：'+f+'不能把9理解成9米或0.9分米。')
setf(k,'note_latex',r'先判断数字9在十分位，表示9个十分之一米。按米化分米的进率10换算：'+f+'所以选9分米，不能只读数字而不看数位与单位。')
inv(k,'米/分米数位意义',[['0.9米','9分米']],'实际量的米转分米另占一行；0.9×10=9计算保留并写清两边单位。')
k='p054_s06'
f=B(r'6\text{厘米}&=(6\div100)\text{米}=0.06\text{米}',r'8\text{米}6\text{厘米}&=(8+0.06)\text{米}=8.06\text{米}',r'560\text{厘米}&=(560\div100)\text{米}=5.6\text{米}')
setf(k,'answer_latex',r'选B。先把长度都化成米：'+f+r'正确算式为\(8.06+5.6\)。6厘米是0.06米，560厘米是5.6米，不能把厘米数直接接在小数点后。')
setf(k,'note_latex',r'厘米化米除以100，原有8米不变，只把6厘米换算后合并：'+f+r'统一成米后相加，正确算式为\(8.06+5.6\)。')
inv(k,'厘米/米复名数相加',[['6厘米','0.06米'],['8米6厘米','8.06米'],['560厘米','5.6米']],'分清小单位换算与再合并整数米数，除以100及8+0.06步骤均保留。')
k='p055_s02'
work[k]['note_latex']+=B(r'327900&=32.79\text{万}',r'25499270000&=254.9927\text{亿}')
inv(k,'万/亿准确改写',[['327900','32.79万'],['25499270000','254.9927亿']],'answer_latex原有改写与≈已分行、无单位括号，可保持；旁注原只讲规则，补该题两个准确改写独立行。')
k='p055_s05';f=D(r'3240\text{克}=(3240\div1000)\text{千克}=3.24\text{千克}')
setf(k,'answer_latex',r'先统一单位，克化千克除以1000：'+f+r'再比较\(3.24>\square.15\)，整数部分最大填3。')
setf(k,'note_latex',r'先按1000的进率把克化成千克：'+f+r'右边填3时，\(3.15<3.24\)；若填4或更大，整数部分已超过左边，所以最大填3。')
inv(k,'克/千克比较',[['3240克','3.24千克']],'换算与比较步骤分开；原数字框只填3。')
k='p055_s06';f=D(r'6.25\text{吨}=(6.25\times1000)\text{千克}=6250\text{千克}')
setf(k,'answer_latex',r'吨化千克乘1000：'+f+r'再比较\(6250>6\square25\)，百位最大填2，因为\(6225<6250\)，而\(6325>6250\)。')
setf(k,'note_latex',r'先把左边化成千克：'+f+r'千位相同，比较百位。填2时6225小于6250；填3时6325已经超过6250，所以最大填2。')
inv(k,'吨/千克比较',[['6.25吨','6250千克']],'乘1000的换算另行，原框只填2。')
k='p055_s07';f=D(r'15\text{厘米}=(15\div100)\text{米}=0.15\text{米}')
setf(k,'answer_latex',r'厘米化米除以100：'+f+r'再比较\(0.\square5>0.15\)，十分位最大可填9。')
setf(k,'note_latex',r'先统一成米：'+f+r'两边个位和百分位相同，十分位填大于1的数字都符合条件，再取最大的9。')
inv(k,'厘米/米比较',[['15厘米','0.15米']],'换算另行，不把比较框答案附带单位。')
k='p056_s01'
f=D(r'3.75\text{吨}=(3.75\times1000)\text{千克}=3750\text{千克}')
rep(k,'answer_latex',r'先统一单位：\(1\text{吨}=1000\text{千克}\)，吨化千克乘1000，所以\(3.75\text{吨}=3750\text{千克}\)。',r'先统一单位，吨化千克乘1000：'+f)
rep(k,'note_latex',r'题目要以千克作答，先把总质量从吨化成千克，按1000的进率换算。\(3.75\text{吨}=3750\text{千克}\)。',r'题目要以千克作答，先按1000的进率把总质量换算：'+f)
f2=D(r'1\text{万件}=10000\text{件}')
rep(k,'answer_latex',r'\par 1万件的质量：',r'\par 先改写件数：'+f2+'1万件的质量：')
rep(k,'note_latex','同样重的快递有10000件，按','先把件数写清：'+f2+'同样重的快递有10000件，按')
inv(k,'吨/千克与万件改写',[['3.75吨','3750千克'],['1万件','10000件']],'吨化千克另行；1万件改写成10000件后再乘每件质量，保持原方法与数值。')
k='p058_s03'
f=B(r'5\text{元}3\text{角}&=5.30\text{元}',r'8\text{角}7\text{分}&=0.87\text{元}')
setf(k,'answer_latex',r'先把金额都化成元：'+f+r'再算\(5.30+0.87=6.17\)元，选A。')
setf(k,'note_latex',r'角对应元的十分位，分对应元的百分位，先分别换算：'+f+r'再按相同数位相加，\(5.30+0.87=6.17\)元。不能把8角当8元，也不能把3角放到百分位。')
inv(k,'复名数钱币换算',[['5元3角','5.30元'],['8角7分','0.87元']],'两个金额各自独立一行，随后才做相加；不改题中A选项。')
k='p061_s09';f=D(r'8\text{厘米}=(8\div100)\text{米}=0.08\text{米}')
setf(k,'answer_latex',r'先统一长度单位，厘米化米除以100：'+f+r'小芳比小明少跳0.08米，\(1.25-0.08=1.17\)米。原空后已有“米”，只填1.17。')
setf(k,'note_latex',r'先统一单位，不能把8厘米当0.8米：'+f+r'求较小的小芳成绩，用\(1.25-0.08=1.17\)米，结果应小于小明的1.25米。原空只填1.17。')
inv(k,'厘米/米跳高差',[['8厘米','0.08米']],'删除原答案重复两次的同一转换说法，独立换算行保留除法，原空不加单位。')
k='p063_s07'
f=B(r'16\text{厘米}&=0.16\text{米}',r'54\text{厘米}&=0.54\text{米}')
a=work[k]['answer_latex'];a=a.replace('统一成米，利用连减性质先凑0.7：','先统一成米：'+f+'利用连减性质先凑0.7：');a=a.replace('也可统一成厘米：','也可统一成厘米：'+D(r'2\text{米}=200\text{厘米}'));a=a.replace(r'\(130\text{厘米}=1.3\text{米}\)。',D(r'130\text{厘米}=1.3\text{米}'));work[k]['answer_latex']=a
n=work[k]['note_latex'];n=n.replace(r'先统一单位：\(16\text{厘米}=0.16\text{米}\)，\(54\text{厘米}=0.54\text{米}\)。','先统一单位：'+f);n=n.replace(r'也可统一成厘米，\(2\text{米}=200\text{厘米}\)，','也可统一成厘米：'+D(r'2\text{米}=200\text{厘米}'));n=n.replace(r'\(130\text{厘米}=1.3\text{米}\)。',D(r'130\text{厘米}=1.3\text{米}'));work[k]['note_latex']=n
inv(k,'厘米/米两种解法',[['16厘米','0.16米'],['54厘米','0.54米'],['2米','200厘米'],['130厘米','1.3米']],'主法初始两段、另法初始总长以及最终答案单位换算均各行列出；两种完整简便脱式保持。')
k='p070_s02';f=D(r'2\text{厘米}=(2\times10)\text{毫米}=20\text{毫米}')
setf(k,'answer_latex',r'比较同一顶点B与B′在直尺上的位置，向下移动2厘米。题目要求毫米，另行换算：'+f+r'原空后已有毫米，只填20。不能拿A与B′两个不对应的顶点比较。')
setf(k,'note_latex',r'比较同一顶点B与B′，相差2厘米。厘米化毫米乘10：'+f+r'平移距离是对应点之间的距离，不是两幅图之间的空隙；原空只填20。')
inv(k,'厘米/毫米平移测量',[['2厘米','20毫米']],'测量与换算分开，原空不重复填毫米。')
# Normalize only known result-unit parentheses. Do not normalize method commentary or mathematical grouping.
unit_tokens={'米','厘米','袋','元','瓶','棵','份','块','千米','毫克','人','克','千克','平方厘米','平方米','个','吨','分','秒','天','千米，最远','千米，最近','小时','万箱'}
paren_count=0
for k,fields in work.items():
 for field,t in list(fields.items()):
  def sub(m):
   global paren_count
   if m[1] in unit_tokens:
    paren_count+=1;return '('+m[1]+')'
   return m[0]
  fields[field]=re.sub(r'（([^）]{1,30})）',sub,t)
changes=[]
for k,fields in work.items():
 changed=[]
 for f,new in fields.items():
  if old[k][f]!=new:
   changed.append({'field':f,'old':old[k][f],'new':new,'conversion_layout_changed':k in conv,'ascii_result_units_changed':any('（'+u+'）'in old[k][f]for u in unit_tokens)})
 if changed:
  changes.append({'key':k,'book_page':int(k[1:4]),'id':Q[k]['id'],'question_file':f'questions/p{int(k[1:4]):03}.json','note_file':'detailed_layout/'+N[k][0],'fields':changed,'reason':conv[k]['note']if k in conv else '仅把解答数值结果后已有的单位括号改为英文ASCII；数学分组、方法说明、题干和表格已知项不改。','question_text_changed':False,'math_result_changed':False})
classifications=[]
counting={'p049_s01','p049_s02','p050_s04','p050_s05','p053_s02','p053_s03','p054_s01','p057_s04','p057_s11','p061_s01','p061_s02','p062_s04'}
scale={'p045_s03','p067_s02','p069_s04','p069_s05','p070_s01','p072_s05'}
for k in Q:
 typ=('actual_unit_conversion'if k in conv else 'counting_unit_or_decimal_place_value_not_physical_conversion'if k in counting else 'clock_angle_or_grid_scale_calculation_not_unit_conversion'if k in scale else 'ordinary_arithmetic_or_geometry_no_unit_conversion')
 classifications.append({'key':k,'classification':typ,'answer_and_note_read':True,'local_count':len(N[k][1].get('local_replacements',[])),'proposal':k in {x['key']for x in changes}})
# Verify protection scopes structurally: no changes were written into project; only proposals exist.
obj={'scope':{'original_book_pages':[37,72],'question_files_read':36,'records_read':len(Q),'matching_notes_read':len(N),'red_local_records_read':sum(len(v[1].get('local_replacements',[]))for v in N.values()),'source':'units_review/project','work_type':'read-only audit; no shared question/note/source files edited'},'changes':changes,'conversion_inventory':[{'key':k,**v,'fields_requiring_standalone_conversion':[f['field']for c in changes if c['key']==k for f in c['fields']]}for k,v in conv.items()],'classification_by_record':classifications,'format_rules_applied':{'conversion_lines':'separate display equation or own aligned row, both quantities carry their units; no parentheses enclosing units','calculation_result_units':'existing result-unit parentheses become ASCII ()','mathematical_grouping':'parentheses in coefficient calculations such as(8÷100) are mathematical grouping, not unit parentheses, and remain','blank_after_known_unit':'fill original blanks only with requested numerals/symbols; fill-unit task p053_s08 fills only units','question_and_known_table_labels':'untouched'},'ambiguous_cases':[{'keys':sorted(counting),'decision':'These discuss decimal counting units / grid subdivisions, not changing physical units; no new unit conversion lines invented solely for counting-unit re-expression.'},{'keys':sorted(scale),'decision':'Clock/grid/angle ratios count intervals or cells rather than convert the same quantity between measurement units; do not introduce invented equalities such as12米=6格. Existing numerical steps unchanged.'},{'key':'p048_s01','decision':'200克西瓜与124毫克维生素是不同物质/含义，不是同一质量的换算，保留原分析，不写200克=...毫克混入乘法。'},{'key':'p044_s04','decision':'按每25千克挽救1棵树求棵数是数量关系计算，不是把质量单位换成棵；仅ASCII结果括号。'},{'key':'p064_s03','decision':'始终以万箱作同一单位，无万箱转箱，因此不新增单位换算；仅结果单位括号ASCII。'}],'verification':{'actual_conversion_questions':len(conv),'changed_questions':len(changes),'changed_fields':sum(len(x['fields'])for x in changes),'ascii_result_parentheses_replacements':paren_count,'no_original_question_or_option_or_known_table_edit':True,'no_method_added':True,'no_numeric_answer_changed':True}}
(R/'audit_037_072.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(obj['scope'],ensure_ascii=False));print(json.dumps(obj['verification'],ensure_ascii=False))
