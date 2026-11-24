from pathlib import Path
import json,copy,hashlib
R=Path(__file__).resolve().parent
P=R/'project'; B=R/'baseline'; O=P/'simplify_update'; O.mkdir(exist_ok=True)
def J(p):return json.loads(p.read_text())
def W(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
changes=[]
for f in ['audit_early.json','audit_25_44.json','audit_45_64.json','audit_65_84.json','audit_85_108.json']:
 for c in J(R/f)['changes']:
  c=copy.deepcopy(c);c['audit_file']=f
  c['note_latex']=c.get('new_note_latex',c.get('note_latex'))
  c['answer_latex']=c.get('new_answer_latex',c.get('answer_latex'))
  changes.append(c)
by={c['key']:c for c in changes};assert len(by)==56
c=by['p075_s04']
c['note_latex']=(r'原位主式以85分为基准：87多2、83少2，88多3、82少3，两对偏差正好抵消；只剩97多12与80少5，净多7分平均补给7份。'
 r'\par\textbf{另法：分组求总分再平均}\par 用加法交换律、结合律分组，再用总分除以7；各组互不依赖的计算同一步完成。'
 r'\[\begin{aligned}&(80+87+83+85+88+97+82)\div7\\={}&[(87+83)+(88+82)+(80+85+97)]\div7\\={}&[170+170+(165+97)]\div7\\={}&(340+262)\div7\\={}&602\div7\\={}&86\text{（分）}\end{aligned}\]答：七位裁判评分的平均分是86分。')
for field in ['note_latex','answer_latex']:
 by['p081_s02'][field]=by['p081_s02'][field].replace('4×4',r'\(4\times4\)')
for key,line,target in [
 ('p075_s01',r'(200+300+480)\div7',[195,83,565,144]),
 ('p079_s03',r'(340+440)\div5',[205,503,570,564])]:
 c=by[key];p=c['local_replacement'];p['target_rect']=target
 old=r'\\={}&'+('980' if key=='p075_s01' else '780')
 p['latex']=p['latex'].replace(old,r'\\={}&'+line+old)
for correction in J(R/'qa_crosscheck_early_mid.json')['required_corrections']:
 c=by[correction['key']]
 if c['book_page']==4:
  old=c['simple_latex'];c['simple_latex']=correction['replacement_simple_latex'];c['why']=correction['replacement_why']
  start=c['note_latex'].index('简便提示（学完运算律后）')
  end=c['note_latex'].index(old,start)+len(old)
  c['note_latex']=c['note_latex'][:start]+correction['replacement_explanation']+c['simple_latex']+c['note_latex'][end:]
 else:
  for field in ['simple_latex','note_latex','answer_latex']:
   c[field]=c[field].replace(r'120\times8\div(8-2)\\={}&120\div6',r'120\times8\div(8-2)\\={}&120\times8\div6\\={}&120\div6')
   c[field]=c[field].replace(r'120+120\times2\div(8-2)\\={}&120+120\div6',r'120+120\times2\div(8-2)\\={}&120+120\times2\div6\\={}&120+120\div6')
  c['original_answer_patch']['latex']=c['simple_latex']

notes={};documents={}
for L in 'ABCD':
 path=P/f'detailed_layout/notes_{L}.json';base=B/f'notes_{L}.json'
 if not base.exists():base=B/f'detailed_layout/notes_{L}.json'
 d=J(base);documents[path]=d
 notes.update({n['key']:n for n in d['records']})
records={};qs={}
for f in sorted((B/'questions').glob('p*.json')):
 d=J(f);qs[P/'questions'/f.name]=d;records.update({r['key']:r for r in d['records']})
assert len(records)==867
patchkeys=[]
for c in changes:
 k=c['key'];n=notes[k];rec=records[k]
 n['latex']=c['note_latex'];n['reason']='本次简便计算复核：'+c['why']
 if c['book_page']<=24:
  rec['answer_latex']+=r'\par\textbf{简便提示（学完运算律后）}\par '+c['simple_latex']
 else:rec['answer_latex']=c['answer_latex']
 rec.setdefault('verification',{}).setdefault('changes',[]).append('简便计算复核：'+c['why'])
 patch=None
 if c.get('original_answer_patch'):
  a=c['original_answer_patch'];patch={'rect':a['source_rect'],'target_rect':a['source_rect'],'latex':a['latex'],'clear_to_white':True,'reason':'简便计算复核；原位红主解更新，不修改黑色题面。'}
 elif c.get('local_replacement'):patch=copy.deepcopy(c['local_replacement'])
 elif c.get('local_latex'):
  patch={'latex':c['local_latex']}
 if patch:
  if k=='p043_s03':
   patch['rect']=[81,473,350,563];patch['target_rect']=[81,473,350,563]
  arr=n.setdefault('local_replacements',n.pop('original_replacements',[]))
  if arr:
   assert len(arr)==1,(k,len(arr));arr[0].update(patch)
  else:arr.append(patch)
  patchkeys.append(k)
for path,d in list(documents.items())+list(qs.items()):W(path,d)
W(R/'accepted_changes.json',{'scope':{'book_pages':108,'records':867,'start_fourth_unit':25,'early_only_marginal_hint':True},'change_count':len(changes),'changed_book_pages':sorted({c['book_page'] for c in changes}),'local_replacement_keys':patchkeys,'changes':changes})
W(O/'accepted_changes.json',J(R/'accepted_changes.json'))
for f in R.glob('audit*.json'): (O/f.name).write_bytes(f.read_bytes())
for f in R.glob('qa_crosscheck*.json'): (O/f.name).write_bytes(f.read_bytes())
print(json.dumps({'changes':len(changes),'books':sorted({c['book_page'] for c in changes}),'local_patches':patchkeys},ensure_ascii=False))
