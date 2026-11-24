from pathlib import Path
import json,copy,re,shutil
R=Path(__file__).resolve().parent;P=R/'project';B=R/'baseline';Q=P/'recheck_update';Q.mkdir(exist_ok=True)
J=lambda p:json.loads(p.read_text())
def W(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
changes=[]
for f in ['reaudit_1_36.json','reaudit_37_72.json','reaudit_73_108.json']:
 for c in J(R/f)['changes']:
  c=copy.deepcopy(c);c['audit_file']=f;c['kind']='simplification';changes.append(c)
by={c['key']:c for c in changes};assert len(by)==34
by['p011_s08']['kind']='multiplication_mental_hint'
for f in ['new_note_latex','new_answer_latex']:
 by['p011_s08'][f]=by['p011_s08'][f].replace('简便提示（学完运算律后）','运算律口算提示（学完运算律后）').replace('只补充乘法部分的简便计算','补充乘法部分的口算过程')
# Preserve the two required analysis trees and the original first-unit solution.
c=by['p003_s07']
for f in ['new_note_latex','new_answer_latex']:
 s=c[f];start=s.index('另法：');end=s.index(r'\[',start)
 s=s[:start]+r'简便提示（学完运算律后）：将总量和已处理量分别平均分成4份，再求每份之差。利用乘除运算的性质，先算\(4\div4\)，同时算\(32\div4\)，避免先求72。'+s[end:]
 c[f]=s
# These are different quantity-analysis entrances to the same simplified chain.
# Do not repeat the already printed primary calculation in the PDF note.
shared={
 'p083_s04':('两车都行驶3小时，尚未相遇。可先把每小时两车接近的路程合并再乘时间，也可分别列出两车路程，再用乘法分配律提取共同的3；最后都要加上尚余193千米。','烟台和北京相距703千米。'),
 'p084_s01':('两种水果各35箱，可把一箱葡萄与一箱橙子配成一组，先求每组价钱。也可分别按单价乘箱数列出总价，再用乘法分配律把55与45凑成100。','一共花3500元。'),
 'p084_s02':('两种水果箱数相同，每箱价差乘35箱就是总价差。也可先列两种总价之差，再用乘法分配律把55减45凑成10。','葡萄比橙子多花350元。'),
 'p100_s02':('平台服务费只从下午核桃收入中扣除，上午收入不重复扣费。可先求每袋实收，再乘80袋；也可先列下午销售额减总服务费，利用乘法分配律合并共同的80。','全天实际收入4208元。'),
 'p104_s03':('足球和篮球各15个，可把各一个配成一套，先将每套单价108与92凑200。分别列两类球总价时，利用乘法分配律合并共同的15，也化为同一简便式。','一共需要3000元。'),
 'p104_s05':('第一次相距200千米表示尚未相遇，已行路程和要加尚余200千米。可先求两车速度和；分别列两车路程时，利用乘法分配律提取共同的2，将220与280凑500。','两地之间相距1200千米。'),
 'p108_s03':('每名学生各买一件上衣和一条裤子，可先把每套单价62与38凑100，再乘45套。分别列上衣、裤子总价时，用乘法分配律合并共同的45；人数不能因此变成90。','买这批合唱服一共需要4500元。')}
for k,(analysis,answer) in shared.items():
 c=by[k];formula=c['simple_latex'];inside=formula.split(r'\begin{aligned}',1)[1].split(r'\end{aligned}',1)[0];rows=inside.split(r'\\')
 first_two=r'\[\begin{aligned}'+r'\\'.join(rows[:2])+r'\end{aligned}\]'
 c['new_note_latex']=analysis+r'\par 另一列式可这样化为原位主式：'+first_two+'后续共用原位的完整简便脱式。'
 c['new_answer_latex']=analysis+r'\par '+formula+'答：'+answer
 c['same_simplified_chain_shared']=True
by['p075_s03']['original_answer_patch']={'source_rect':[263,338,406,380],'target_rect':[225,338,570,410],'latex':by['p075_s03']['simple_latex'],'clear_to_white':True,'reason':'保留左侧原答语；完整五行简算置于右侧，末行与答语横向分离。解析插入白缝同步移至410pt，避免截断公式和下一题标题。'}
by['p088_s03']['original_answer_patch']={'source_rect':[276,459,345,500],'target_rect':[245,459,565,522],'latex':by['p088_s03']['simple_latex'],'clear_to_white':True,'reason':'只换红色原位算式；原答语在左侧保留，四行简算不与答语相交。'}
qdocs={};records={};ndocs={};notes={}
for f in (B/'questions').glob('p*.json'):
 d=J(f);qdocs[P/'questions'/f.name]=d;records.update({x['key']:x for x in d['records']})
for L in 'ABCD':
 d=J(B/f'notes_{L}.json');ndocs[P/f'detailed_layout/notes_{L}.json']=d;notes.update({x['key']:x for x in d['records']})
assert len(records)==len(notes)==867
changes.append({'key':'p074_s04','book_page':74,'id':'二、4','kind':'source_answer_conflict_clarification','why':'原始JPEG明确平均15千克，加入39千克，故按题面C正确；补充书后A与数据冲突、若原平均45则A，不能无依据改题面。','new_note_latex':r'按当前题面15千克，\(39>15\)，加入后平均体重提高，应选C。书后A与当前数据不符；若原平均为45千克，\(39<45\)，加入后就会变轻，选A。判断增减只需比较新队员体重与原平均，不必先算总量。','new_answer_latex':r'按当前原始扫描的平均15千克，选C。因为\(39>15\)，加入后平均体重提高。\par 书后A与当前题面数据不符。若原平均体重应为45千克，则\(39<45\)，加入后平均体重降低，选A；实际原平均数需核实。','question_value_retained':15,'filled_answer_retained':'C','original_answer_needs_replacement':False})
k='p091_s03';note=notes[k]['latex'].replace('另法以每天100本比较','求出总量后，也可与每天100本比较作复核').replace('另法：以每天100本为基准，沿用原式已求总数784本。','基准复核：沿用主法已求出的总数784本，与每天100本比较。')
ans=records[k]['answer_latex'].replace('方法二：以每天100本为基准','基准复核：与每天100本比较').replace('8天若平均每天100本，共应借800本，实际784本少16本，每天应少2本。','主法已求得总量784本。8天若平均每天100本，共应借800本，少的16本平均到8天，每天少2本。')
changes.append({'key':k,'book_page':91,'id':records[k]['id'],'kind':'method_classification','why':'以100为基准的段落复用了主法总量784，改称基准复核，避免把相同总量的再处理冒称独立简法。','new_note_latex':note,'new_answer_latex':ans,'original_answer_needs_replacement':False})
patchkeys=[]
for c in changes:
 k=c['key'];n=notes[k];rec=records[k];n['latex']=c['new_note_latex'];n['reason']='本轮复核：'+c['why'];rec['answer_latex']=c['new_answer_latex']
 rec.setdefault('verification',{}).setdefault('changes',[]).append('本轮复核：'+c['why'])
 if k=='p074_s04':rec['verification']['uncertainties']=['书后A与原始扫描平均15千克不符；原平均若高于39则选A，例如45。尚未收到可据以改动题面数值的说明。']
 if c.get('original_answer_needs_replacement'):
  a=c['original_answer_patch'];patch={'rect':a['source_rect'],'target_rect':a.get('target_rect',a['source_rect']),'latex':a['latex'],'clear_to_white':True,'reason':a['reason']}
  arr=n.setdefault('local_replacements',[]);assert not arr,k;arr.append(patch);patchkeys.append(k)
for path,d in list(qdocs.items())+list(ndocs.items()):W(path,d)
for L in 'ABCD':
 src=P/f'inline_layout/slots_{L}.json';back=B/f'slots_{L}.json'
 if not back.exists():shutil.copy2(src,back)
 d=J(back)
 for pp in (d['pages'] if isinstance(d,dict) else d):
  if pp['book_page']==75:
   for s in pp['slots']:
    if s['keys']==['p075_s03']:s.update({'cut_y':410.0,'reason':'本轮实看A4源：新五行红式结束于404前，后续黑题从414后开始；410所在白缝像素检查通过，避免截断标题。'})
 W(src,d)
accepted={'records_reviewed':867,'book_pages_reviewed':108,'new_simplifications':33,'additional_multiplication_hint':1,'source_conflict_clarifications':1,'method_classification_corrections':1,'count':36,'changed_book_pages':sorted({c['book_page'] for c in changes}),'local_replacement_keys':patchkeys,'changes':changes}
W(R/'accepted_changes.json',accepted);W(Q/'accepted_changes.json',accepted)
for f in list(R.glob('reaudit*.json'))+list(R.glob('qa_math*.json'))+list(R.glob('qa_arithmetic*.json'))+list(R.glob('qa_p074*.json')):shutil.copy2(f,Q/f.name)
print(json.dumps({k:v for k,v in accepted.items() if k!='changes'},ensure_ascii=False),flush=True)
