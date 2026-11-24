#!/usr/bin/env python3
"""Native-object proposals for the approved conversion topics in volumes 5/6."""
from pathlib import Path
import importlib.util,json,re,sys
from PIL import ImageFont
BASE=Path(__file__).resolve().parents[2];P=BASE/'project';W=BASE/'ppt_units'
sys.path[:0]=[str(P/'ppt_builder')]
from convert_inputs import convert_latex,ast_plain
inv=json.loads((W/'logical_inventory.json').read_text());slides={(s['volume'],s['slide']):s for s in inv['slides']};opsets={}
font=ImageFont.truetype(str(P/'fonts/DroidSansFallback.ttf'),43)
records={r['key']:r for page in range(1,109) for r in json.loads((P/f'questions/p{page:03d}.json').read_text())['records']}
def ob(v,s,name):return next(o for o in slides[v,s]['objects'] if o['name']==name)
def add(v,s,op):
    opsets.setdefault((v,s),{'volume':v,'ui_slide':s,'key':slides[v,s]['record_key'],'ops':[]})['ops'].append(op)
def names(v,s,prefix):return [o['name']for o in slides[v,s]['objects']if o['name'].startswith(prefix) and o['kind']!='grpSp']
def blank(v,s,n):add(v,s,{'type':'blank','name':n})
def math(v,s,n,tex,rect=None):add(v,s,{'type':'math','name':n,'tex':tex,'rect':rect or ob(v,s,n)['rect'],'points':32})
def text(v,s,n,t,rect=None):add(v,s,{'type':'text','name':n,'text':t,'rect':rect or ob(v,s,n)['rect'],'points':32})
def move(v,s,n,dx=0,dy=0):add(v,s,{'type':'move','name':n,'dx':dx,'dy':dy})
def move_prefix(v,s,prefix,dy):
    for n in names(v,s,prefix):move(v,s,n,dy=dy)
def mr(tex,y,h=58,x=106,w=1110):return {'type':'math','tex':tex,'rect':[x,y,w,h],'points':32}
def tr(t,y,h=58):return {'type':'text','text':t,'rect':[64,y,1152,h],'points':32}
def rich(v,s,ns,rows):
    if isinstance(ns,str):ns=names(v,s,ns)
    assert ns
    add(v,s,{'type':'rich','name':ns[0],'rows':rows})
    for n in ns[1:]:blank(v,s,n)
def wrap(t,maxwidth=1140):
    result=[];cur=''
    for token in re.findall(r'\d+(?:\.\d+)?(?:亿)?|.',t):
        if cur and font.getlength(cur+token)>maxwidth:result.append(cur);cur=token
        else:cur+=token
    if cur:result.append(cur)
    return result
def approved_rest_rows(key,y):
    blocks=convert_latex(records[key]['answer_latex'],'answer');rows=[];first=True
    for b in blocks:
        if b['type']=='math':
            if first:first=False;continue
            rows.append(mr(b['latex'],y));y+=58
        elif b['type']=='paragraph':
            string=''.join(r['text'] if r['type']=='text' else ast_plain(r['ast'])for r in b['runs'])
            for line in wrap(string):rows.append(tr(line,y));y+=58
        else:raise ValueError(b['type'])
    return rows

# Height conversion: all intermediate arithmetic from the approved source.
math(5,50,'p075_s02_b002_5',r'2\text{米}=(100\times2)\text{厘米}',[106,494,1110,58])
math(5,50,'p075_s02_b003_6',r'200\text{厘米}',[106,562,1110,54])

# Potato estimate: independent rate and final conversion, retaining main math.
text(5,147,'p079_s04_b003_2_p0','个的质量。')
math(5,147,'p079_s04_b003_2_p1',r'1\text{千克}=1000\text{克}',[106,338,1110,58])
for n in ['p079_s04_b003_2_p2','p079_s04_b003_2_p3','p079_s04_b003_2_p4']:blank(5,147,n)
move(5,147,'p079_s04_b004_3',dy=54)
for n in ['p079_s04_b005_4_operator','p079_s04_b005_4']:move(5,147,n,dy=64)
blank(5,147,'p079_s04_b006_5_operator')
math(5,147,'p079_s04_b006_5',r'6240\text{克}=6.24\text{千克}',[106,554,1110,58])

rich(5,190,'p081_s07_b001_',[
    tr('面积单位进率为100：',202.5),mr(r'1\text{平方米}=100\text{平方分米}',266.5),
    mr(r'520\text{平方米}=(520\times100)\text{平方分米}',330.5),mr(r'=52000\text{平方分米}',394.5)])
move_prefix(5,190,'p081_s07_b002_',194)
rich(5,192,'p081_s08_b001_',[
    tr('先将角和分化成元：',202.5),mr(r'3\text{角}=0.3\text{元}',260.5),mr(r'5\text{分}=0.05\text{元}',318.5),
    tr('再合并钱数：',376.5),mr(r'587\text{元}3\text{角}5\text{分}=(587+0.3+0.05)\text{元}',434.5),mr(r'=587.35\text{元}',492.5)])
move_prefix(5,192,'p081_s08_b002_',206)
rich(5,194,'p081_s09_b001_',[
    tr('先分出整千克对应的克数：',202.5),mr(r'6260\text{克}=6000\text{克}+260\text{克}',266.5),
    mr(r'6000\text{克}=6\text{千克}',330.5),mr(r'6260\text{克}=6\text{千克}260\text{克}',394.5)])
move_prefix(5,194,'p081_s09_b002_',194)
rich(5,196,'p081_s10_b001_',[
    tr('厘米换米除以100：',202.5),mr(r'329.4\text{厘米}=(329.4\div100)\text{米}',266.5),mr(r'=3.294\text{米}',330.5)])
move_prefix(5,196,'p081_s10_b002_',130)
rich(5,198,'p081_s11_b001_',[
    tr('先分成整数吨与小数吨：',202.5),mr(r'275.09\text{吨}=275\text{吨}+0.09\text{吨}',260.5),tr('小数吨换成千克：',318.5),
    mr(r'0.09\text{吨}=(0.09\times1000)\text{千克}',376.5),mr(r'=90\text{千克}',434.5),mr(r'275.09\text{吨}=275\text{吨}90\text{千克}',492.5)])
move_prefix(5,198,'p081_s11_b002_',280)

rich(5,223,'p082_s07_b004_5_', [mr(r'4\text{厘米}=0.04\text{米}',498.5)])
math(5,223,'p082_s07_b004_6_p0',r'1.23-0.04=1.19\text{(米)}',[106,572.5,1110,58]);blank(5,223,'p082_s07_b004_6_p1')

rich(6,28,'p093_s01_b003_',[
    tr('按进率先换算：',124.5),mr(r'60\text{米}=0.06\text{千米}',186.5),mr(r'7\text{千米}60\text{米}=(7+0.06)\text{千米}=7.06\text{千米}',248.5),
    mr(r'1\text{平方米}=10000\text{平方厘米}',310.5),mr(r'800\text{平方厘米}=(800\div10000)\text{平方米}=0.08\text{平方米}',372.5),
    tr('依次填7.06、0.08，原空后的单位不重复填写。',434.5)])
rich(6,31,'p093_s02_b001_', [mr(r'240960000\text{公顷}=2.4096\text{亿公顷}',124.5),*approved_rest_rows('p093_s02',188.5)])
rich(6,154,'p097_s01_b003_', [mr(r'126339000\text{亩}=1.26339\text{亿亩}',124.5),*approved_rest_rows('p097_s01',188.5)])

rich(6,45,'p093_s06_b001_', [tr('白鸭比黑鸭重，先统一单位：',276.5),mr(r'700\text{克}=0.7\text{千克}',334.5)])
move(6,45,'p093_s06_b002_3',dy=400-ob(6,45,'p093_s06_b002_3')['rect'][1])
for n in ['p093_s06_b003_4_operator','p093_s06_b003_4']:move(6,45,n,dy=42)
for n in ['p093_s06_b004_5_operator','p093_s06_b004_5']:move(6,45,n,dy=33)
move(6,45,'p093_s06_b005_6_p0',dy=33)

for s,n in [(248,'p100_s03_b007_6_p0'),(249,'p100_s03_b013_6_p0')]:
    rich(6,s,[n],[mr(r'0.04\text{米}=4\text{厘米}',540),tr('答：重叠部分长4厘米。',600)])

# Two-row conversion/comment for each subquestion, preserving its own click.
rich(6,265,'p101_s03_b003_5_',[
    mr(r'\text{（2）}\quad7\text{角}5\text{分}=0.75\text{元}',482,43,x=64,w=1152),
    mr(r'0.75<0.8\text{，填}<\text{。}',525,43,x=106,w=1110)])
rich(6,265,'p101_s03_b004_6_',[
    mr(r'\text{（3）}\quad7\text{米}2\text{厘米}=7.02\text{米}',568,43,x=64,w=1152),
    mr(r'7.2>7.02\text{，填}>\text{。}',611,43,x=106,w=1110)])

math(6,351,'p104_s02_b012_1_p0',r'4.68\text{元}=468\text{分}',[106,195,1110,58])
text(6,351,'p104_s02_b012_1_p1','赠送双数：',[64,270,256,58])
math(6,351,'p104_s02_b012_1_p2',r'12\div(5+1)=2\text{(双)}',[320,270,876,58])
move(6,351,'p104_s02_b012_1_p3',dy=74);move(6,351,'p104_s02_b012_2_p0',dy=74)

math(6,366,'p105_s02_b002_4_p0',r'6\text{千克}50\text{克}=(6000+50)\text{克}=6050\text{克}',[64,428.5,1152,58])
for n in ['p105_s02_b002_4_p1','p105_s02_b003_5_p1','p105_s02_b004_6_p1']:blank(6,366,n)
blank(6,367,'p105_s02_b005_0_p1')

rich(6,390,'p106_s02_b005_',[
    tr('13.8吨中的8在十分位，表示0.8吨。',124.5),mr(r'0.8\text{吨}=(0.8\times1000)\text{千克}=800\text{千克}',198.5),
    tr('所以表示800千克，不是8千克或80千克。',272.5)])
move(6,390,'p106_s02_b006_2_p0',dy=74)

result=sorted(opsets.values(),key=lambda r:(r['volume'],r['ui_slide']))
(W/'conversion_ops_v5_6.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'questions':sorted({r['key'] for r in result}),'slides':len(result),'ops':sum(len(r['ops'])for r in result)},ensure_ascii=False))
