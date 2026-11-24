from pathlib import Path
import json,re
R=Path(__file__).resolve().parent
Q={q['key']:q for p in (R.parent/'questions').glob('p[0-9][0-9][0-9].json') for q in json.loads(p.read_text())['records']}
records={}
def add(key,ti,ri,ci,value=None,text=False,label=None,note=None,override=False):
 original=Q[key]['tables'][ti]['rows'][ri][ci]
 item={'table_index':ti,'row_index':ri,'column_index':ci,'expected_original':original}
 if value is not None:item['answer_text' if text else 'answer_latex']=str(value)
 else:item.update(answer_latex=None,display_label=label,unresolved=True)
 if note:item['note']=note
 if override:item.update(allow_nonblank_override=True,override_reason=note)
 records.setdefault(key,{'table_final_answers':[]})['table_final_answers'].append(item)
# A symbolic digit stays a source variable in preceding subquestions, and is resolved only by part (3).
add('p055_s12',0,0,4,'1.24',note='依本小问第三名条件，十分位为2；表头已为米，不重复单位。',override=True)
means=[(0,1,4,70),(0,3,3,95),(1,1,5,90),(1,2,3,97),(1,3,4,84)]
for key in ['p076_s01','p076_s02']:
 for ti,ri,ci,val in means:add(key,ti,ri,ci,val)
for key,ti in [('p076_s02',2),('p076_s03',0)]:
 for ri,row in enumerate([[2,2,1,1],[2,3,1,0]]):
  for ci,val in enumerate(row,1):add(key,ti,ri,ci,val)
for key in ['p077_s07','p077_s08']:add(key,1,0,5,159,note='由本题上一小问已给B队平均157厘米求得；不提前回填第一小问尚无该条件的空。')
vision=[[2,3,5,11],[1,2,8,12],[3,5,13,23]]
for key in ['p080_s02','p080_s03','p080_s04']:
 for ri,row in enumerate(vision):
  for ci,v in enumerate(row,1):add(key,0,ri,ci,v)
add('p084_s03',0,1,1,22,note='两项共1014，桌125×6=750，椅总264，264÷12=22。仅替原污损单价空，不修改给定125/6/12/合计1014。',override=True)
# No invented unreadable digit in the girls' largest-size cell or derived totals.
combined=[[7,12,1,None,None],[3,12,7,2,24],[10,24,8,None,None]]
for ri,row in enumerate(combined):
 for ci,v in enumerate(row,1):
  add('p092_s01',2,ri,ci,v,label='待核' if v is None else None,note='女生特大号人数末位不清；依赖该数的合计也待核。'if v is None else None)
for ti,row in [(2,[1,3,9,11]),(3,[2,7,11,4])]:
 for ci,v in enumerate(row,1):add('p096_s04',ti,0,ci,v)
for ci,v in enumerate([36,23,7,3,3],1):add('p100_s05',0,0,ci,v)
for ci,v in enumerate([9,8,6,5],1):add('p108_s05',0,0,ci,v)
# Exact independent recounts for the statistical tables.
assert [sum(a<=x<=b for x in [37,28,26,23,32,39,28,34,45,41,26,46,37,25,57,27,55,33,34,27,52,42,24,50,48,34,40,51])for a,b in [(20,29),(30,39),(40,49),(50,59)]]==[9,8,6,5]
male=[157,159,150,148,128,157,148,125,146,102,149,154,116,138,161,154,149,155,141,143,122,156,154,168]
female=[118,120,145,136,117,148,136,115,137,100,139,144,106,128,161,145,162,148,131,126,102,153,152,112]
for vals,want in [(male,[1,3,9,11]),(female,[2,7,11,4])]:
 assert [sum(lo<=x<=hi for x in vals)for lo,hi in [(0,103),(104,127),(128,149),(150,999)]]==want
vm=[4.9,5.1,4.4,5.0,4.8,5.2,4.1,5.0,4.7,4.9,5.1,4.6,5.2,4.2,4.8,5.3,5.0,5.1,4.5,5.2,5.0]
vf=[5.1,4.8,4.7,5.2,4.9,5.3,4.3,5.1,4.9,5.0,5.2,4.2,4.8,5.1,4.7,5.3,5.0,4.6,5.2,4.9,5.0,5.2,4.8]
for vals,want in [(vm,[2,3,5,11]),(vf,[1,2,8,12])]:
 assert [sum(lo<=x<=hi for x in vals)for lo,hi in [(0,4.2),(4.3,4.6),(4.7,4.9),(5.0,9.9)]]==want
assert (65+70+66)//3==67 and (95+96+94)//3==95
assert (88+90+92)//3==90 and (93+95+97)//3==95 and (83+86+83)//3==84
scores=[58,95,86,75,84,87,59,90,77,98,93,87,58,62,77,86,98,68,90,87,96,95,98,88,90,77,95,84,99,67,78,88,90,91,86,93]
assert [sum(85<=x<=100 for x in scores),sum(70<=x<=84 for x in scores),sum(60<=x<=69 for x in scores),sum(x<60 for x in scores)]==[23,7,3,3]
for k,v in records.items():
 seen=set()
 for a in v['table_final_answers']:
  cell=(a['table_index'],a['row_index'],a['column_index']);assert cell not in seen;seen.add(cell)
  assert Q[k]['tables'][cell[0]]['rows'][cell[1]][cell[2]]==a['expected_original']
  assert not a['expected_original'] or a.get('allow_nonblank_override'),(k,a)
(R/'table_final_answers_tail.json').write_text(json.dumps({'schema_version':1,'records':records},ensure_ascii=False,indent=2))
print({'records':len(records),'cells':sum(len(v['table_final_answers'])for v in records.values()),'unknown':sum(a.get('unresolved',False)for v in records.values()for a in v['table_final_answers'])})
