import json,copy
from pathlib import Path
from scan_answer_slots import scan_slots
R=Path(__file__).resolve().parent
records={}
for ch in 'abcd':
 d=json.loads((R/f'final_answers_{ch}.json').read_text())
 for k,v in d['records'].items():
  assert k not in records,k
  records[k]=v

def setv(key,slot,value,math=False,note=None):
 a=next(x for x in records[key]['final_answers'] if x['slot_index']==slot)
 a.pop('answer_text',None);a.pop('answer_latex',None)
 a['answer_latex' if math else 'answer_text']=value
 if note:a['note']=note
 return a

def variant(key,label,updates):
 arr=copy.deepcopy(records[key]['final_answers'])
 for slot,value,math in updates:
  a=next(x for x in arr if x['slot_index']==slot)
  a.pop('answer_text',None);a.pop('answer_latex',None)
  a['answer_latex' if math else 'answer_text']=value
 records[key].setdefault('variants',[]).append({'label':label,'final_answers':arr})

setv('p004_s05',0,r'3\times(9+1)-6',True,'合法示例一；以下分别回填不同结构。不以简单交换乘数或加数的顺序另计一法。')
for i,s in enumerate([r'9+3\times(6-1)',r'(9-1)\times(6-3)',r'6+9\times(3-1)',r'6\times(1+9\div3)'],2):variant('p004_s05',f'另一结构{i}',[(0,s,True)])
setv('p005_s01',0,'乘');setv('p005_s01',1,'除')
variant('p005_s01','两空交换填写顺序',[(0,'除',False),(1,'乘',False)])
setv('p018_s09',0,'A、C',False,'两式都符合数量关系，原单选题不唯一。')
setv('p025_s03',0,r'87\times100-87',True,'合法输入示例，不需按9键。')
variant('p025_s03','另一输入方法',[(0,r'(88+11)\times87',True)])
variant('p025_s03','因数分解输入方法',[(0,r'87\times33\times3',True)])
setv('p026_s03',1,'C、D',False,'C先783−283凑500；D先256+244凑500，均为合理简便计算。')
setv('p093_s05',0,'120',True,'两种长度都用且48厘米竹条至少两根时；题干未限定两种都用，等边也是等腰，另有72或144厘米的材料条件方案。')
variant('p093_s05','只用三根24厘米竹条',[(0,'72',True)])
variant('p093_s05','只用三根48厘米竹条',[(0,'144',True)])
setv('p102_s01',0,'至少B、C',False,'B、C均可围成三角形；A末长首位待核，完整选项集合尚不能确定。')
labels={('p022_s01',0):'条件不足',('p058_s04',0):'需约定',('p068_s04',1):'见说明',('p068_s05',1):'见说明',('p074_s03',0):'条件不足',('p085_s06',0):'待核',('p085_s12',1):'待核',('p085_s12',2):'待核',('p092_s02',0):'待核'}
for (k,s),label in labels.items():
 a=next(x for x in records[k]['final_answers'] if x['slot_index']==s)
 a['display_label']=label
 a['unresolved']=True

questions={q['key']:q for p in sorted((R.parent/'questions').glob('p[0-9][0-9][0-9].json')) for q in json.loads(p.read_text())['records']}
for name in ['table_final_answers_a.json','table_final_answers_tail.json']:
 for key,value in json.loads((R/name).read_text())['records'].items():
  records.setdefault(key,{'final_answers':[]}).update(value)

counts={'records':0,'candidates':0,'answered':0,'unresolved':0,'ignored':0,'variants':0}
for k,q in questions.items():
 slots=scan_slots(q.get('question_latex',''))
 if not slots:continue
 assert k in records,('missing',k)
 v=records[k];by={}
 for a in v.get('final_answers',[]):
  assert a['slot_index'] not in by,(k,'duplicate')
  by[a['slot_index']]=a
 for a in v.get('ignored_slots',[]):
  ix=a['slot_index'];assert ix not in by,(k,'ignore duplicate')
  by[ix]={'slot_index':ix,'skip':True,'note':a['reason'],'expected_placeholder':a.get('expected_placeholder',slots[ix]['placeholder']),'source':'question_latex'}
 assert len(by)==len(slots),(k,len(by),len(slots))
 for s in slots:
  a=by[s['slot_index']]
  assert a['expected_placeholder']==s['placeholder'],(k,s,a)
  if a.get('skip'):counts['ignored']+=1
  elif a.get('unresolved'):assert a.get('note') and a.get('display_label');counts['unresolved']+=1
  else:assert a.get('answer_text') is not None or a.get('answer_latex') is not None,(k,a);counts['answered']+=1
 v['final_answers']=[by[i] for i in sorted(by)];v.pop('ignored_slots',None)
 counts['records']+=1;counts['candidates']+=len(slots);counts['variants']+=len(v.get('variants',[]))
counts['table_records']=sum(bool(v.get('table_final_answers'))for v in records.values())
counts['table_cells']=sum(len(v.get('table_final_answers',[]))for v in records.values())
output={'schema_version':1,'records':records,'coverage':counts,'notes':'实际题目空位逐槽核对；多解采用联动方案；display_label仅为源题待核说明，不是编造的数值答案。'}
(R/'final_answers.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
(R/'final_answers_audit.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2))
print(counts)
