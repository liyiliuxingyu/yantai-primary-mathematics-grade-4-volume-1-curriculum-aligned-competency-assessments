from pathlib import Path
import json
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
inv=json.loads((ROOT/'ppt/inventory.json').read_text()); rules=[]
def shp(v,n,i):return next(x for s in inv if s['volume']==v and s['slide']==n for x in s['shapes'] if x['id']==str(i))
def op(v,n,i,typ,**kw):return {'type':typ,'name':shp(v,n,i)['name'],**kw}
def add(v,n,key,ops):rules.append({'volume':v,'slide':n,'key':key,'ops':ops})
def rows_from_tex(s):
 body=s.split(r'\begin{aligned}')[1].split(r'\end{aligned}')[0]
 return [x.replace('={}&','').lstrip('& ').strip() for x in body.split(r'\\')]
# Early-unit efficient methods are added beside, without replacing any existing method.
config={
'p003_s03':(1,64,13,620,220,570,26,'减去差：先减前项，再加后项。'),
'p003_s04':(1,65,13,620,220,570,26,'把76拆成19与4的积，先凑300。'),
'p004_s02':(1,82,10,650,140,550,24,'减去和可连减，先用9000减8100。'),
'p004_s03':(1,88,8,650,150,550,26,'总袋数与班数同时除以3。'),
'p004_s04':(1,93,8,650,150,550,26,'总块数与班数同时除以3。'),
'p006_s02':(1,136,14,720,265,490,24,'乘除调换次序，先算15除以5。'),
'p006_s03':(1,139,25,650,430,550,24,'先把两个2相乘，与25凑100。'),
'p006_s06':(1,147,19,490,215,710,26,'第一式：乘25与除25相互抵消。'),
'p007_s03':(1,160,13,620,220,570,28,'把21拆成20加1，先得500。'),
'p008_s01':(1,176,25,650,335,550,24,'先把5与8相乘，再求优惠前总价。'),
'p011_s07':(1,255,13,620,220,570,28,'把21拆成20加1，先得900。'),
'p015_s05':(1,336,13,620,215,580,25,'219看作220少1，乘积少算15。'),
'p015_s07':(1,338,13,620,215,580,25,'减去差后，先把160减60凑100。'),
'p019_s12':(2,22,14,650,220,550,28,'69看作70少1，再少算一份80。'),
'p019_s13':(2,23,14,620,215,580,26,'20拆成4乘5，乘4与除4抵消。'),
'p020_s02':(2,33,8,760,160,440,26,'60先除以3，再乘4。'),
'p023_s04':(2,114,10,650,335,550,25,'8拆成2乘4，让4与75先凑300。'),
'p023_s11':(2,129,13,620,220,570,28,'59看作60少1，最后减去一个17。'),
}
for a in json.loads((ROOT/'audit_early.json').read_text())['changes']:
 if a['key']=='p008_s03':continue
 v,n,i,x,y,w,pt,note=config[a['key']];rr=rows_from_tex(a['simple_latex'])
 if a['key'] in ('p004_s03','p004_s04'):
  num='16' if a['key']=='p004_s03' else '480';note='24是3乘8；先乘3再除以3还原。';rr.insert(2,num+r'\times3\div3\div8')
 rowh=38 if a['key']=='p006_s03' else (44 if len(rr)>4 else 48)
 add(v,n,a['key'],[op(v,n,i,'note',title='简便提示（学完运算律后）',text=note,rect=[x,y,w,70+len(rr)*rowh],points=pt,rows=rr,title_points=24,note_points=20,row_height=rowh)])
# Fourth unit onward: retain quantity reasoning and use efficient arithmetic.
# Expand the old middle RHS by one new row in its original click group.
def replace_middle(v,n,key,i,rr,answer_ids):
 ops=[op(v,n,i,'math',rows=rr,rect=[64,190,1130,138],points=32)]
 for oid,rect in answer_ids:ops.append(op(v,n,oid,'move',rect=rect))
 add(v,n,key,ops)
replace_middle(2,249,'p027_s11',6,[r'(25\times4)\times12',r'100\times12'],[(5,[64,197.5,34,54]),(7,[64,330,34,54]),(8,[106,336.166719160105,1000,54]),(9,[64,405,1150,58])])
replace_middle(2,254,'p028_s02',6,[r'1200\div(25\times4)',r'1200\div100'],[(5,[64,197.5,34,54]),(7,[64,330,34,54]),(8,[106,336.166719160105,1000,54]),(9,[64,405,1150,58])])
replace_middle(2,257,'p028_s03',6,[r'(53+47)\times16',r'100\times16'],[(5,[64,197.5,34,54]),(7,[64,330,34,54]),(8,[106,336.166719160105,1000,54]),(9,[64,405,1150,58])])
replace_middle(2,260,'p028_s04',6,[r'(53-47)\times16',r'6\times16'],[(5,[64,197.5,34,54]),(7,[64,330,34,54]),(8,[106,336.166719160105,1000,54]),(9,[64,405,1150,58])])
replace_middle(2,350,'p032_s01',6,[r'(58+42)\times120',r'100\times120'],[(5,[64,197.5,34,54]),(7,[64,330,34,54]),(8,[106,336.166719160105,1000,54]),(9,[64,405,1150,58])])
# Subtraction: a missing intermediate group is inserted into original middle RHS.
add(2,251,'p028_s01',[
 op(2,251,8,'math',rows=[r'1500-(665+135)',r'1500-800'],rect=[64,338,1130,138],points=32),
 op(2,251,7,'move',rect=[64,345.5,34,54]),op(2,251,9,'move',rect=[64,478,34,54]),op(2,251,10,'move',rect=[106,485.49333333333,1000,54]),op(2,251,11,'move',rect=[64,552,1150,58]),
 op(2,251,5,'text',text='方法二：从连续扣除列式，合并支出凑整',rect=[64,198,1150,58],points=32)])
# Titles identify each alternative quantity analysis, without claiming new math methods.
for n,key,i,txt in [(248,'p027_s11',10,'另一数量思路：先求小组数，计算用结合律'),(253,'p028_s02',10,'另一数量思路：分两层平均分，计算合并除数'),(256,'p028_s03',10,'另一数量思路：两队路程相加，计算先凑100'),(259,'p028_s04',10,'另一数量思路：两队路程相减，计算先求差'),(349,'p032_s01',10,'另一数量思路：分别计价，计算先凑100')]:
 add(2,n,key,[op(2,n,i,'text',text=txt,rect=[64,405,1150,58],points=30)])
# L-shaped area: three geometric paths, each with distributive simplification.
add(2,358,'p032_s04',[
 op(2,358,9,'math',tex=r'(41+19)\times18',rect=[106,414,1000,54],points=32),
 op(2,358,11,'math',rows=[r'60\times18',r'1080\text{(平方米)}'],rect=[64,483,1130,110],points=32),
 op(2,358,12,'move',rect=[64,604,1150,44])])
add(2,359,'p032_s04',[
 op(2,359,9,'math',tex=r'(37+23)\times18',rect=[106,335,1000,54],points=32),
 op(2,359,11,'math',rows=[r'60\times18',r'1080\text{(平方米)}'],rect=[64,404,1130,110],points=32),
 op(2,359,12,'move',rect=[64,525,1150,50]),op(2,359,13,'move',rect=[64,596,1150,50])])
add(2,360,'p032_s04',[
 op(2,360,6,'math',tex=r'41\times19+41\times18-(41\times19-18\times19)',rect=[106,192,1090,54],points=28),
 op(2,360,8,'math',tex=r'41\times18+18\times19',rect=[106,261,1000,54],points=32),
 op(2,360,10,'math',tex=r'(41+19)\times18',rect=[106,330,1000,54],points=32),
 op(2,360,11,'text',text='先展开括号，再消去相同的面积。',rect=[64,400,1150,58],points=30),
 op(2,360,12,'text',text='方法三（续）：合并共同因数，先凑整',rect=[64,474,1150,58],points=30)])
add(2,361,'p032_s04',[
 op(2,361,4,'math',tex=r'(41+19)\times18',rect=[106,124,1000,54],points=32),
 op(2,361,6,'math',tex=r'60\times18',rect=[106,192,1000,54],points=32),
 op(2,361,8,'math',tex=r'1080\text{(平方米)}',rect=[106,261,1000,54],points=32),
 op(2,361,9,'text',text='',rect=[64,330,1,1],points=1),
 op(2,361,10,'text',text='补形法也归到横向分割的计算结构。',rect=[64,330,1150,58],points=30),
 op(2,361,12,'text',text='横分、纵分、补形是三种几何思路；',rect=[64,474,1150,58],points=30),
 op(2,361,13,'text',text='运算律变形不另算第四种几何方法。',rect=[64,548,1150,58],points=30)])
for ss in rules:
 if ss['key'] in ('p004_s03','p004_s04'):
  ss['ops'][0]['rect'][3]=306;ss['ops'][0]['row_height']=48
rules.sort(key=lambda x:(x['volume'],x['slide']))
(BASE/'rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n')
print({v:[r['slide'] for r in rules if r['volume']==v] for v in [1,2]})
