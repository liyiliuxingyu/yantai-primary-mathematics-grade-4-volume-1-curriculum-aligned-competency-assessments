from pathlib import Path
import json,copy
R=Path(__file__).resolve().parents[1]
I=json.loads((R/'full_inventory.json').read_text())
S={(v['volume'],s['slide']):s for v in I for s in v['slides']}
rules={}
def add(v,s,op):
 rules.setdefault((v,s),{'volume':v,'slide':s,'key':S[v,s]['record_key'],'ops':[]})['ops'].append(op)
def rect(v,s,n):return next(x['rect'] for x in S[v,s]['shapes'] if x['name']==n)
def t(v,s,n,text,r=None,pt=32):add(v,s,{'type':'text','name':n,'text':text,'points':pt,'rect':r or rect(v,s,n)})
def m(v,s,n,tex,r=None):add(v,s,{'type':'math','name':n,'tex':tex,'points':32,'rect':r or rect(v,s,n)})
def rows(v,s,n,rs,r):add(v,s,{'type':'math','name':n,'rows':rs,'points':32,'rect':r})
def blank(v,s,n):t(v,s,n,'',[1,1,1,1])
def move(v,s,n,y):
 r=rect(v,s,n).copy();r[1]=y;targ=next(x for x in S[v,s]['shapes'] if x['name']==n)
 if targ['has_native_math']:raise AssertionError('Use explicit m to move maths')
 t(v,s,n,targ['text'],r)

# 73: preserve two quantity paths; baseline is now the first click and total
# method is the second click. Obsolete fragments share those nonempty clicks.
v,s,k=5,15,'p073_s07'
t(v,s,k+'_b001_2_p0','以80为基准，甲、乙的合量正好是2份80。\n丙比80少30，将这30平均从3份中扣除。',[64,276,1152,116])
rows(v,s,k+'_b001_2_p1',[r'80-(80-50)\div3',r'80-30\div3',r'80-10',r'70'],[64,408,660,216])
for x in S[v,s]['shapes']:
 if x['name'].startswith(k+'_b001') and x['name'] not in [k+'_b001_2_p0',k+'_b001_2_p1']:blank(v,s,x['name'])
t(v,s,k+'_b002_5_p0','总量法复核：',[760,408,456,58])
rows(v,s,k+'_b002_5_p1',[r'(80\times2+50)\div3',r'(160+50)\div3',r'210\div3',r'70'],[760,468,456,192])
blank(v,s,k+'_b002_5_p2')

# 74: current source genuinely says 15. This clarifies the discrepancy without
# changing a printed condition or mislabelling a heavier entrant as lighter.
rules.update({(x['volume'],x['slide']):x for x in json.loads((R/'rules_p74.json').read_text())})

# 75 average speed: retain every original click while adding the explicit
# division-by-a-product reduction.
v,s,k=5,53,'p075_s03'
rows(v,s,k+'_b004_1',[r'720\times2\div20',r'720\times2\div2\div10',r'720\div10'],[64,192,1152,162])
t(v,s,k+'_b005_2_operator','=',[64,369,34,54]);m(v,s,k+'_b005_2',r'72\text{(米/分)}',[106,369,1000,54])
for suf in ['p0','p1','p2']:
 n=k+'_b006_3_'+suf;r=rect(v,s,n).copy();r[1]+=108
 if suf=='p1':m(v,s,n,r'72',r)
 else:t(v,s,n,next(x['text'] for x in S[v,s]['shapes'] if x['name']==n),r)

# 75 scoring: direct restoration, followed by a substantive explanation click.
v,s,k=5,62,'p075_s05'
m(v,s,k+'_b015_1',r'85\text{(分)}',[106,192,1000,54])
t(v,s,k+'_b016_2_operator','说明：',[64,261,140,58])
t(v,s,k+'_b016_2','先乘5再除以5，还原为原数85。',[220,261,996,58])

# 77 A-team heights: table remains untouched. The total calculation is grouped;
# a following existing slide supplies the independent 155 baseline method.
v,s,k=5,100,'p077_s06'
t(v,s,k+'_b003_2_p0','另法：分组求总身高再平均。',[64,373.5,1152,58])
rows(v,s,k+'_b003_3_p0',[r'[(156+154)+(151+159)+160]\div5',r'(310+310+160)\div5',r'(620+160)\div5',r'780\div5',r'156\text{(厘米)}'],[64,438,730,225])
t(v,s,k+'_b003_3_p1','两组都是310厘米。',[820,438,396,58])
t(v,s,k+'_b003_4_p0','不表示每名队员都高',[820,505,396,58])
m(v,s,k+'_b003_4_p1',r'156',[820,575,110,54]);t(v,s,k+'_b003_4_p2','厘米。',[930,575,150,58])
v,s=5,101
t(v,s,k+'_b004_0_p0','简便方法：以155厘米为基准',[64,124,1152,58])
rows(v,s,k+'_b004_0_p1',[r'155+5\div5',r'155+1',r'156\text{(厘米)}'],[64,340,1152,198])
t(v,s,k+'_b004_0_p2','156多1、154少1，151少4、159多4，两对偏差抵消。\n只剩160多5厘米，平均分给5人，每人多1厘米。',[64,194,1152,116])

def entry4(v,s,k,blocks,common,alt,reason,answer_names,heading):
 """Turn former duplicate calculation into two entry expressions and a law."""
 for num,(opn,rhsn) in enumerate(blocks):
  y=rect(v,s,opn)[1];label=['入口二：','整理：','依据：'][num]
  t(v,s,opn,label,[64,y,210,58])
  if num==0:m(v,s,rhsn,alt,[290,y,926,54])
  elif num==1:m(v,s,rhsn,common,[290,y,926,54])
  else:t(v,s,rhsn,reason,[290,y,926,58])
 first,*others=answer_names
 t(v,s,first,'两种列式化为同一简算结构，后续只计算一次。',[64,rect(v,s,first)[1],1152,58])
 for n in others:blank(v,s,n)
 t(v,s,heading,'下一页：共用的简算过程')

# 83: entrances on 243, complete shared computation on 244.
v,s,k=5,243,'p083_s04'
t(5,242,k+'_b003_4','入口一：先求每小时两车接近的路程')
entry4(v,s,k,[(k+'_b005_1_operator',k+'_b005_1'),(k+'_b006_2_operator',k+'_b006_2'),(k+'_b007_3_operator',k+'_b007_3')],r'(95+75)\times3+193',r'95\times3+75\times3+193','乘法分配律，合并共同的3。',[k+'_b008_4_p0',k+'_b008_4_p1',k+'_b008_4_p2'],k+'_b009_5')
m(5,244,k+'_b010_0',r'(95+75)\times3+193',[106,120,1110,54]);m(5,244,k+'_b011_1',r'170\times3+193',[106,192,1110,54])

# 84 total-price entrances, then one shared simplified computation.
v,s,k=5,252,'p084_s01';t(v,s,k+'_b003_0','入口一：先求各一箱的总价')
entry4(v,s,k,[(k+'_b005_2_operator',k+'_b005_2'),(k+'_b006_3_operator',k+'_b006_3')],r'(55+45)\times35',r'55\times35+45\times35','',[k+'_b007_4_p0',k+'_b007_4_p1',k+'_b007_4_p2'],k+'_b008_5')
m(5,253,k+'_b009_0',r'(55+45)\times35',[106,120,1110,54]);m(5,253,k+'_b010_1',r'100\times35',[106,192,1110,54])

# 84 price-difference entrances end in the same expression; next slide computes.
v,s,k=5,254,'p084_s02';t(v,s,k+'_b002_3','入口一：每箱价差乘箱数')
t(v,s,k+'_b004_5_operator','入口二：',[64,485,210,58]);m(v,s,k+'_b004_5',r'55\times35-45\times35',[290,485,926,54])
t(v,s,k+'_b005_6_operator','整理：',[64,554,210,58]);m(v,s,k+'_b005_6',r'(55-45)\times35',[290,554,926,54])
v,s=5,255;t(v,s,k+'_b006_0_p0','列式入口已合并，接着凑整计算。',[64,124.5,1152,58]);blank(v,s,k+'_b006_0_p1');blank(v,s,k+'_b006_0_p2')
t(v,s,k+'_b007_1','共用简算：先把每箱价差凑成10元')
m(v,s,k+'_b008_2',r'(55-45)\times35',[106,267,1110,54]);m(v,s,k+'_b009_3',r'10\times35',[106,337,1110,54])

# 88: keep initial quantity order; simplify by dividing 6 by 3 first.
v,s,k=5,382,'p088_s03';rows(v,s,k+'_b004_1',[r'6\div3\times4',r'2\times4'],[64,192,1152,108])
t(v,s,k+'_b005_2_operator','=',[64,315,34,54]);m(v,s,k+'_b005_2',r'8\text{(厘米)}',[106,315,1110,54])
for suf in ['p0','p1','p2']:
 n=k+'_b006_3_'+suf;r=rect(v,s,n).copy();r[1]+=54
 if suf=='p1':m(v,s,n,r'8',r)
 else:t(v,s,n,next(x['text'] for x in S[v,s]['shapes'] if x['name']==n),r)

# 89: baseline steps first; original explanation click now also provides the
# independent total-score verification rather than repeating the same formula.
v,s,k=5,396,'p089_s07'
m(v,s,k+'_b002_0',r'96+(2-1-1)\div5',[106,120,1110,54]);m(v,s,k+'_b003_1',r'96+0\div5',[106,192,1110,54])
t(v,s,k+'_b005_3_p0','以96为基准，98多2，两次95各少1，正好抵消。\n另用剩余总分复核：',[64,331.5,1152,116])
rows(v,s,k+'_b005_3_p1',[r'(98+95+96+95+96)\div5',r'480\div5',r'96\text{(分)}'],[64,456,1152,162])
for x in S[v,s]['shapes']:
 if x['name'].startswith(k+'_b005') and x['name'] not in [k+'_b005_3_p0',k+'_b005_3_p1']:blank(v,s,x['name'])
t(v,s,k+'_b006_6_p0','填',[980,615,46,58]);m(v,s,k+'_b006_6_p1',r'96',[1028,615,80,54]);t(v,s,k+'_b006_6_p2','。',[1110,615,46,58])

# 91: explicitly reuse the already-calculated 784 as a check, not a fresh method.
v,k=6,'p091_s03';t(v,11,k+'_b008_5','基准复核：沿用主法已求出的总本数')
t(v,12,k+'_b009_0_p0','主法已求出8天共784本。与每天100本比较，',[64,124.5,1152,58])
t(v,12,k+'_b009_1_p0','8天应有800本，实际少16本，每天少2本。',[64,198.5,1152,58])
for name,tex in [(k+'_b010_0',r'100-(100\times8-784)\div8'),(k+'_b011_1',r'100-(800-784)\div8'),(k+'_b012_2',r'100-16\div8'),(k+'_b013_3',r'100-2'),(k+'_b014_4',r'98\text{(本)}')]:
 r=rect(v,13,name).copy();r[2]=1110;m(v,13,name,tex,r)
t(v,13,k+'_b015_5_operator','核对：',[64,468,160,58]);t(v,13,k+'_b015_5','与主法结果一致，所用总量来自主法。',[240,468,976,58])

# 98: consolidate the divisible factor 8 first; keep knockout reasoning intact.
v,s,k=6,182,'p098_s02'
rows(v,s,k+'_b004_3',[r'7\times(8\div2)',r'7\times4'],[64,340,1152,108])
t(v,s,k+'_b005_4_operator','=',[64,463,34,54]);m(v,s,k+'_b005_4',r'28\text{(场)}',[106,463,1110,54])
for n in [k+'_b006_5_p0',k+'_b006_5_p1',k+'_b006_5_p2',k+'_b006_6_p0']:
 r=rect(v,s,n).copy();r[1]+=54
 if n.endswith('5_p1'):m(v,s,n,r'8-1=7',r)
 else:t(v,s,n,next(x['text'] for x in S[v,s]['shapes'] if x['name']==n),r)

# 100 income entrances and one shared simplified calculation.
v,s,k=6,244,'p100_s02'
entry4(v,s,k,[(k+'_b004_1_operator',k+'_b004_1'),(k+'_b005_2_operator',k+'_b005_2'),(k+'_b006_3_operator',k+'_b006_3')],r'768+(45-2)\times80',r'768+45\times80-2\times80','乘法分配律，合并共同的80。',[k+'_b007_4_p0'],k+'_b008_5')
m(6,245,k+'_b010_2',r'768+(45-2)\times80',[106,270,1110,54]);m(6,245,k+'_b011_3',r'768+43\times80',[106,340,1110,54]);m(6,245,k+'_b012_4',r'768+3440',[106,409,1110,54])

# 104 ball-price entrances. Complete common calculation is on the next slide.
v,s,k=6,353,'p104_s03';t(v,s,k+'_b001_2','入口一：先求一套足球和篮球的价钱')
t(v,s,k+'_b004_5_operator','入口二：',[64,485,210,58]);m(v,s,k+'_b004_5',r'108\times15+92\times15',[290,485,926,54])
t(v,s,k+'_b005_6_operator','整理：',[64,554,210,58]);m(v,s,k+'_b005_6',r'(108+92)\times15',[290,554,926,54])
v,s=6,354;t(v,s,k+'_b006_0_p0','共用简算：先凑出整百单价。',[64,124.5,1152,58]);t(v,s,k+'_b007_1','两种列式入口的共同计算')
t(v,s,k+'_b008_2_p0','一个足球与一个篮球合为一套，各15个就是15套。',[64,269.5,1152,58]);t(v,s,k+'_b008_3_p0','利用乘法分配律，把108与92先凑成200。',[64,343.5,1152,58])
m(v,s,k+'_b009_4',r'(108+92)\times15',[106,415,1110,54]);m(v,s,k+'_b010_5',r'200\times15',[106,485,1110,54])

# 104 travel entrances, then one shared chain to 1200 km.
v,s,k=6,361,'p104_s05'
entry4(v,s,k,[(k+'_b004_1_operator',k+'_b004_1'),(k+'_b005_2_operator',k+'_b005_2'),(k+'_b006_3_operator',k+'_b006_3')],r'(220+280)\times2+200',r'220\times2+280\times2+200','乘法分配律，合并共同的2。',[k+'_b007_4_p0'],k+'_b008_5')
v,s=6,362;t(v,s,k+'_b009_0_p0','两种列式都先合并220与280，凑成500。',[64,124.5,1152,58]);t(v,s,k+'_b009_1_p0','再乘共同的2小时，并加尚余200千米。',[64,198.5,1152,58])
m(v,s,k+'_b010_2',r'(220+280)\times2+200',[106,270,1110,54]);m(v,s,k+'_b011_3',r'500\times2+200',[106,340,1110,54])

# 108 clothing-price entrances, then a single complete common calculation.
v,s,k=6,453,'p108_s03'
t(v,s,k+'_b004_1_operator','入口二：',[64,192,210,58]);m(v,s,k+'_b004_1',r'62\times45+38\times45',[290,192,926,54])
t(v,s,k+'_b005_2_operator','整理：',[64,261,210,58]);m(v,s,k+'_b005_2',r'(62+38)\times45',[290,261,926,54])
t(v,s,k+'_b006_3_p0','上衣和裤子各45份，可合并共同的45。',[64,331.5,1152,58]);t(v,s,k+'_b007_4','两种列式，共用后续简算')
t(v,s,k+'_b008_5_p0','两种列式都先把62与38凑成100元，',[64,476.5,1152,58]);t(v,s,k+'_b008_6_p0','然后求45套的总价。',[64,550.5,1152,58])
m(6,454,k+'_b009_0',r'(62+38)\times45',[106,120,1110,54]);m(6,454,k+'_b010_1',r'100\times45',[106,192,1110,54])

# Classroom wording stays direct; old fragment anchors contain no old text.
for s in rules.values():
 for op in s['ops']:
  if op['type']=='text':
   op['text']=(op['text'].replace('列式入口已合并，接着凑整计算。','两种列式已统一，接着凑整计算。')
    .replace('两种列式入口的共同计算','两种列式整理后的共同计算')
    .replace('入口一','列式一').replace('入口二','列式二')
    .replace('两种列式化为同一简算结构，后续只计算一次。','用乘法分配律整理成相同的算式，接着简算。')
    .replace('下一页：共用的简算过程','统一列式后，继续简算。')
    .replace('两种列式，共用后续简算','统一列式后，继续简算。'))
  if s['volume']==5 and s['slide']==100 and op['name']=='p077_s06_b003_2_p0':op['text']='A队：分组求总身高再平均。'
  if s['volume']==5 and s['slide']==396 and op['name']=='p089_s07_b006_6_p2':op['rect']=[1080,615,46,58]
t(5,254,'p084_s02_b001_1_p0','两种水果箱数相同，可把每箱价差乘35；',[64,198.5,1152,58])
t(5,254,'p084_s02_b001_2_p0','也可先分别列出总价，再相减。',[64,272.5,1152,58])
for suffix in ['p1','p2','p3','p4']:blank(5,254,'p084_s02_b001_1_'+suffix)
# 74 comparison needs no crowded mixed inline arithmetic. The original one
# analysis click remains, with two separate native comparison equations.
rules[5,34]['ops']=[]
v,s,k=5,34,'p074_s04'
used={k+'_b001_0_p0',k+'_b001_0_p1',k+'_b001_0_p2',k+'_b001_0_p3',k+'_b001_0_p4',k+'_b001_1_p0',k+'_b001_1_p1'}
t(v,s,k+'_b001_0_p0','按当前题面，原平均为15千克，新队员重39千克。',[64,124,1152,58])
m(v,s,k+'_b001_0_p1',r'39>15',[106,196,1110,58])
t(v,s,k+'_b001_0_p2','加入的队员比原平均重，所以平均体重提高，选C。',[64,268,1152,58])
t(v,s,k+'_b001_0_p3','书后A与当前15千克不符，需要核对题面。',[64,342,1152,58])
t(v,s,k+'_b001_0_p4','如果原平均为45千克，新队员仍重39千克：',[64,416,1152,58])
m(v,s,k+'_b001_1_p0',r'39<45',[106,490,1110,58])
t(v,s,k+'_b001_1_p1','加入的队员比原平均轻，平均体重降低，应选A。',[64,564,1152,58])
for x in S[v,s]['shapes']:
 if x['name'].startswith(k+'_b001') and x['name'] not in used:blank(v,s,x['name'])
out=sorted(rules.values(),key=lambda s:(s['volume'],s['slide']))
(R/'rules_late.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print([(v,len([s for s in out if s['volume']==v])) for v in [5,6]])
