from pathlib import Path
import json
R=Path('p74_review');P=R/'project'
J=lambda p:json.loads(p.read_text())
notes={n['key']:n for L in 'CD' for n in J(P/f'detailed_layout/notes_{L}.json')['records']}
recs={r['key']:r for b in range(73,91) for r in J(P/f'questions/p{b:03}.json')['records']}
accepted={x['key'] for x in J(P/'simplify_update/accepted_changes.json')['changes']}
def A(*rows):return r'\[\begin{aligned}&'+r'\\={}&'.join(rows)+r'\end{aligned}\]'
changes=[]
def add(k,why,new_note,new_answer,formula,local=False,scope='主解及旁注'):
 r=recs[k];changes.append(dict(key=k,book_page=r['book_page'],id=r['id'],why=why,new_note_latex=new_note,new_answer_latex=new_answer,simple_latex=formula,original_answer_needs_replacement=local,scope=scope,already_changed_in_previous_56=k in accepted,checked_exact_value=True))
# New average baseline: original 80 represents two data, not one.
k='p073_s07';f=A('80-(80-50)\\div3','80-30\\div3','80-10','70')
old=A('(80\\times2+50)\\div3','(160+50)\\div3','210\\div3','70')
n='以80为基准，甲、乙的总量正好是2份80；若丙也为80，三数平均仍为80。丙实际少30，应把这30平均从3份中扣去，所以先用30除以3得10，再从80减10，避免先求210。'+f+'原“先求总量再平均”的数量思路也成立，但不能把代表两份的80和代表一份的50直接平均。'
a='填\\(70\\)。\\textbf{方法一：以80为基准移多补少}\\par '+n+'\\par\\textbf{方法二：先求总量再平均}'+old
add(k,'甲乙已平均为80，丙低30；从基准80扣去30÷3即可，避免160+50与210÷3。',n,a,f)
# 720×2÷20: inverse multiplication/division first.
k='p075_s03';f=A('720\\times2\\div(12+8)','720\\times2\\div20','720\\times2\\div2\\div10','720\\div10','72\\text{（米/分）}')
n='平均速度仍按来回总路程除以来回总用时。两程各720米，总时间12加8等于20分钟；20是2与10的积，除以20可先除以2再除以10。前面的乘2与接着除2互相还原，直接用720除以10，免算1440。两程用时不同，不能把两段速度直接相加除以2。'
a='\\textbf{总路程除以总时间，先整理乘除}\\par 来回路程按每程720米乘2程列式。利用除以积等于连续除以两个因数，先乘2再除2还原720。'+f+'答：来回平均每分钟走72米。'
add(k,'20=2×10，720×2÷20可先乘2再除2还原，只算720÷10，比先算1440÷20更便捷。',n,a,f,True)
# Existing equalized-five method does not need to multiply 85 by5 then divide5.
k='p075_s05';old= r'\[\begin{aligned}&85\times5\div5\\={}&425\div5\\={}&85\text{（分）}\end{aligned}\]';f=A('85\\times5\\div5','85\\text{（分）}')
n=notes[k]['latex'].replace(old,f)+'先乘5又除以5，回到原数85，无须先算425；移多补少后五个评分相同，平均数也就是每个评分85。'
a=recs[k]['answer_latex'].replace(r'\[\begin{aligned}&85\times5\div5\\&=425\div5\\&=85\text{（分）}\end{aligned}\]',f)
assert n!=notes[k]['latex'] and f in a
add(k,'现有移多补少法已把五个评分化成85，却又求425再除5；按先乘后除同一个非零数直接还原85。',n,a,f,False,'仅简化方法二中85×5÷5的末段；不改方法一与题意')
# A-team: two symmetrical pairs about155, one remaining160.
k='p077_s06';f=A('155+5\\div5','155+1','156\\text{（厘米）}')
old=notes[k]['latex'][notes[k]['latex'].index(r'\['):]
n='以155厘米为基准：156多1、154少1，151少4、159多4，两对多、少部分分别抵消。只剩160比155多5厘米，平均补到5人，每人多1厘米。'+f+'\\par\\textbf{另法：分组求总身高再平均}\\par 两对身高分别合为310厘米，与160厘米合计后除以5。'+old+'平均数反映整体水平，不表示每位队员都高156厘米。'
a='填\\(156\\)。\\textbf{方法一：以155厘米为基准移多补少}\\par '+n
add(k,'当前分组仍求310+310+160=780再除5；155基准下±1、±4两对抵消，只需155+5÷5。',n,a,f)
# Separate quantity analysis may use the same distribution-law arithmetic.
for k,oldf,newf,why,label in [
 ('p083_s04',A('95\\times3+75\\times3+193','285+225+193','510+193','703\\text{（千米）}'),A('95\\times3+75\\times3+193','(95+75)\\times3+193','170\\times3+193','510+193','703\\text{（千米）}'),'两车路程分别列式后同乘3，先提取共同3求速度和170，避免分别算285与225。','分别列出两车路程，再合并简算'),
 ('p084_s01',A('55\\times35+45\\times35','1925+1575','3500\\text{（元）}'),A('55\\times35+45\\times35','(55+45)\\times35','100\\times35','3500\\text{（元）}'),'两种水果各35箱，另法仍分别算大乘积；乘法分配律先将55与45凑100。','先分别列费用，再用分配律简算'),
 ('p084_s02',A('55\\times35-45\\times35','1925-1575','350\\text{（元）}'),A('55\\times35-45\\times35','(55-45)\\times35','10\\times35','350\\text{（元）}'),'价差算式有共同35，先算55−45=10，避免另算1925、1575及它们的差。','先分别列费用差，再用分配律简算')]:
 oldans=recs[k]['answer_latex'];oldnote=notes[k]['latex'];newans=oldans.replace(oldf, newf)
 # Old canonical uses &=; normalize just the exact old block for substitution.
 oldalt=oldf.replace(r'\\={}&',r'\\&=')
 if newans==oldans:newans=oldans.replace(oldalt,newf)
 assert newans!=oldans,k
 newans=newans.replace('分别求两车的路程',label).replace('分别求总价再相加',label).replace('分别求费用再相减',label)
 if k=='p083_s04':
  newnote=oldnote.replace(oldf,newf).replace(oldalt,newf).replace('分别求已行路程',label)
 elif k=='p084_s01':
  newnote=oldnote.replace(oldf,newf).replace(oldalt,newf).replace('另法：分别求两种水果总价。','另法：先分别列出两种水果的费用，再合并简算。')
 else:
  tiny=A('1925-1575','350\\text{（元）}')
  newnote=oldnote.replace(tiny,newf).replace('另法用上问分别求出的葡萄、橙子总价相减','另法先分别列出两种水果的费用，再相减').replace('另法：用上一问已求的两种总价相减。','另法：先分别列费用差，再用乘法分配律合并简算。')
 newnote+='先分别列出的数量分析可以保留，计算再用乘法分配律合并；与原方法归为同一简算结构，不增加一种新方法。'
 assert newnote!=oldnote,k
 add(k,why,newnote,newans,newf,False,'只改另法计算，保留原有数量分析起点，不增算第三法')
# Integer product divided by3: reduce6 before multiplying4.
k='p088_s03';f=A('6\\times4\\div3','6\\div3\\times4','2\\times4','8\\text{（厘米）}')
n='同一根铁丝重新围图形，总长不变，先按正方形边长6厘米乘4条边列总长，再平均分给等边三角形的3条边。计算时6能被3整除，可先算6除以3得2，再乘4；这是乘除性质的简便整理，不能把原来的6厘米只除以3而漏乘4。'
a='\\textbf{总长不变，列式后先算能整除的一组}\\par 按每边6厘米乘4条边求原总长，再除以3。乘积除以3可先用6除以3，再乘4。'+f+'答：等边三角形的边长是8厘米。'
add(k,'6可被3整除，先6÷3再乘4，比先算24再除3更直接，保留每份数×份数列式顺序。',n,a,f,True)
# Current text has equalization but expression still sums five numbers.
k='p089_s07';f=A('96+(2-1-1)\\div5','96+0\\div5','96\\text{（分）}')
old=A('(98+95+96+95+96)\\div5','480\\div5','96\\text{（分）}')
n='按规则只去掉一个最高分99和一个最低分92，留下5个评分，除数应为5。以96为基准：98多2，两次95各少1，多、少正好抵消，两个96不变。'+f+'也可将98多出的2分各补1分给两个95，五份都成96，总分不变。\\par\\textbf{另法：求剩余总分再平均}'+old+'答：张梦最后得分是96分。'
a='填\\(96\\)。\\textbf{方法一：以96分为基准移多补少}\\par '+n
add(k,'原说明已有移多补少，但脱式仍先求480；以96为基准，+2与−1−1抵消，直接确认平均96。',n,a,f)
coverage=[]
for b in range(73,91):
 rr=J(P/f'questions/p{b:03}.json')['records'];coverage.append({'book_page':b,'record_count':len(rr),'checked_keys':[r['key'] for r in rr]})
qa={'scope':'73–90页全部活动题干、答案、题旁注释逐record简便运算复核；不替代全册其他数学或全页人工排版检查','record_count':len(recs),'coverage':coverage,'prior_56_read':True,'changes':changes,'change_count':len(changes),'p074_s04':'按root已独立实看原图15千克，加入39千克，C正确；本审查不改题意或答案。','not_forced':['p073_s06三项98/125/149没有天然凑整配对，现算法正确，不强拆','p073_s02、p089_s02两数整十相加后除2已易算，不为添加基准法而改','p081_s05先求25×12=300再减25本身已凑整，提取25得到11未更省算，不强改','p081_s14小数三项没有自然凑整，调整次序无明显收益','p084_s03两种桌椅数量路径现有整数运算均便于计算，不强改','p090_s03旁注已用平均差×6，不重复提出原有简算','指定列竖式的90页题按题型保留竖式，不以简算替代要求']}
(R/'reaudit_73_90_sub.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print('reviewed',len(recs),'changes',len(changes),[c['key'] for c in changes])
