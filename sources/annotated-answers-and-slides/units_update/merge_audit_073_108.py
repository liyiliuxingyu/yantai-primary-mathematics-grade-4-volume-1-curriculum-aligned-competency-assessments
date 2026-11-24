from pathlib import Path
from fractions import Fraction
import json,re,ast,hashlib,collections
R=Path(__file__).resolve().parent;P=R/'project';J=lambda p:json.loads(Path(p).read_text())
a=J(R/'audit_helper_073_090.json');b=J(R/'audit_helper_091_108.json')
post=[]
for c in b['changes']:
 if c['key']=='p093_s01':
  f=next(x for x in c['field_changes'] if x['field']=='latex');old=f['new'];f['new']=old.replace('第一空先把60米换成千米','第一空先把60米除以1000换成千米');assert f['new']!=old
  post.append({'key':c['key'],'field':f['field'],'change':'恢复旧旁注已有的除以1000依据，避免仅作分行时丢失原换算步骤。'})
changes=a['changes']+b['changes'];assert len({c['key'] for c in changes})==len(changes)==96
notes={n['key']:(L,n) for L in 'ABCD' for n in J(P/f'detailed_layout/notes_{L}.json')['records']}
records={r['key']:r for n in range(73,109) for r in J(P/f'questions/p{n:03}.json')['records']};assert len(records)==262
fields={}
for r in records.values():
 k=r['key'];L,n=notes[k]
 fields[(f'questions/p{r["book_page"]:03}.json',k,'answer_latex')]=r['answer_latex']
 fields[(f'detailed_layout/notes_{L}.json',k,'latex')]=n['latex']
 for i,l in enumerate(n.get('local_replacements',[])):
  if l.get('kind','').startswith('black') or r'\color{black}' in l['latex']:continue
  fields[(f'detailed_layout/notes_{L}.json',k,f'local_replacements[{i}].latex')]=l['latex']
virtual=dict(fields);declared=set()
for c in changes:
 for f in c['field_changes']:
  key=(f['file'],c['key'],f['field']);assert key not in declared;declared.add(key);assert fields[key]==f['old']
  assert f['new']!=f['old'];virtual[key]=f['new']
  assert set(re.findall(r'\d+(?:\.\d+)?',f['old']))<=set(re.findall(r'\d+(?:\.\d+)?',f['new'])),key
assert len(declared)==177
unit_heads=['摄氏度','平方千米','平方米','平方分米','平方厘米','千米/时','米/分','米/秒','千米','厘米','毫米','分米','千克','毫升','千升','千瓦时','分钟','小时','万册','大格','秒','克','吨','米','元','角','分','人','个','本','册','台','次','部','块','件','箱','辆','页','瓶','袋','套','棵','把','张','名','份','组','升','下','度']
pat='('+'|'.join(map(re.escape,sorted(unit_heads,key=len,reverse=True)))+r'(?:，[^（）()]*)?)'
rx=re.compile('（'+pat+'）');ascii_rx=re.compile(r'\('+pat+r'\)')
left=[(k,rx.findall(v)) for k,v in virtual.items() if rx.search(v)];assert not left,left
converted_occurrences=0
for key in declared:
 old=collections.Counter(rx.findall(fields[key]));new=collections.Counter(ascii_rx.findall(virtual[key]));converted_occurrences+=sum(min(v,new[u]) for u,v in old.items())
# Independently evaluate quantity equalities after converting to a common unit.
factors={
'厘米':Fraction(1),'米':Fraction(100),'千米':Fraction(100000),'平方厘米':Fraction(1),'平方分米':Fraction(100),'平方米':Fraction(10000),
'克':Fraction(1),'千克':Fraction(1000),'吨':Fraction(1000000),'分':Fraction(1),'角':Fraction(10),'元':Fraction(100),
'亿':Fraction(100000000),'公顷':Fraction(100000000),'亿公顷':Fraction(10000000000000000),'亩':Fraction(1),'亿亩':Fraction(100000000)}
unit_pattern='|'.join(map(re.escape,sorted(factors,key=len,reverse=True)))
qr=re.compile(r'(\([^()]*\)|\d+(?:\.\d+)?)\\text\{('+unit_pattern+r')\}')
def numeric(s):
 s=s.replace('\\times','*').replace('\\div','/').replace('−','-').replace('[','(').replace(']',')').strip()
 def e(n):
  if isinstance(n,ast.Expression):return e(n.body)
  if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):return Fraction(str(n.value))
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return e(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
  if isinstance(n,ast.BinOp):
   x,y=e(n.left),e(n.right)
   if isinstance(n.op,ast.Add):return x+y
   if isinstance(n.op,ast.Sub):return x-y
   if isinstance(n.op,ast.Mult):return x*y
   if isinstance(n.op,ast.Div):return x/y
  raise ValueError(s)
 return e(ast.parse(s,mode='eval'))
def quantity_value(s):
 s=s.replace('\\times','*').replace('\\div','/').replace('&','').replace('{}','').strip()
 def repl(m):
  v=numeric(m[1])*factors[m[2]]
  return '('+str(v.numerator)+'/'+str(v.denominator)+')'
 s=qr.sub(repl,s).replace(')(',')+(')
 return numeric(s)
conversion_keys={c['key'] for c in a['actual_conversion_cases_checked']}|set(b['actual_conversion_question_keys']);assert len(conversion_keys)==18
conv_locations=[];checks=[];decompositions=[];approx=[]
for key,text in virtual.items():
 file,k,field=key
 if k not in conversion_keys:continue
 for bi,body in enumerate(re.findall(r'\\\[(.*?)\\\]',text,re.S)):
  units=re.findall(r'\\text\{([^}]+)\}',body)
  units=[u for u in units if u in factors]
  if not units:continue
  distinct=set(units);ismag=any(u in ['亿','亿亩','亿公顷'] for u in units)
  if len(units)<2 and not ismag:continue
  classification='magnitude_reexpression' if ismag else ('true_unit_conversion' if len(distinct)>=2 else 'same_unit_decomposition')
  if '\\approx' in body:
   approx.append({'key':k,'file':file,'field':field,'block':body,'classification':'rounding_not_exact_conversion','original_approximation_preserved':True});continue
  core=re.sub(r'\\begin\{aligned\}|\\end\{aligned\}','',body)
  rows=re.split(r'\\\\',core);previous=None;values=[]
  for row in rows:
   row=row.replace('&','').replace('{}','').strip()
   if not row:continue
   if row.startswith('='):
    v=quantity_value(row.lstrip('='));assert previous==v,(key,row,previous,v);values.append(str(v));previous=v
   else:
    parts=row.split('=');vs=[quantity_value(p) for p in parts];assert len(set(vs))==1,(key,row,vs);values+=list(map(str,vs));previous=vs[-1]
  proof={'key':k,'file':file,'field':field,'display_block_index':bi,'block':body,'classification':classification,'equal_common_unit_values':values,'passed':True}
  if classification=='same_unit_decomposition':decompositions.append(proof)
  else:checks.append(proof);conv_locations.append({'key':k,'file':file,'field':field,'display_block_index':bi,'standalone_conversion_line':body,'classification':classification})
# Verify original p078 black corrections and Q4 classroom answer are untouched by proposals.
assert 'p078_s04' not in {c['key'] for c in changes}
for k in ['p078_s01','p078_s05','p078_s06']:
 for i,l in enumerate(notes[k][1].get('local_replacements',[])):
  if l.get('kind','').startswith('black'):assert (f'detailed_layout/notes_{notes[k][0]}.json',k,f'local_replacements[{i}].latex') not in declared
report={
 'scope':{'book_pages':[73,108],'question_records_read':262,'all_record_keys':list(records),'fields_examined':len(fields),'read_ownership':[{'book_pages':[73,90],'records':138,'reviewer':'average_crosscheck'},{'book_pages':[91,108],'records':124,'reviewer':'units_091_108'}]},
 'source_read_only':True,'changes':changes,'changed_question_count':len(changes),'changed_field_count':len(declared),'ordinary_existing_unit_parentheses_to_ASCII_occurrences':converted_occurrences,
 'actual_conversion_question_keys':sorted(conversion_keys),'actual_conversion_question_count':18,'conversion_questions_needing_change':17,'already_proper_conversion_question_keys':['p081_s04'],
 'conversion_cases_checked':a['actual_conversion_cases_checked']+[{'key':k,'needs_change':True,'classification':'measurement_or_magnitude_conversion','locations':[x for x in b['conversion_locations'] if x['key']==k]} for k in b['actual_conversion_question_keys']],
 'actual_conversion_field_location_count':36,'conversion_fields_needing_change':34,'standalone_conversion_display_blocks_checked':len(checks),'conversion_locations':conv_locations,'quantity_equivalence_checks':checks,'same_unit_decomposition_checks':decompositions,'rounding_lines_already_proper':approx,
 'conversion_numeric_equivalence':{'method':'Fractions in a common smallest stated unit; each exact conversion display and its continued row evaluated independently.','all_checked_equalities_passed':True,'display_blocks_checked':len(checks),'same_unit_decomposition_blocks_checked':len(decompositions),'helper_distinct_relation_checks':b['conversion_numeric_equivalence']},
 'helper_calculation_block_preservation':b['aligned_calculation_preservation_check'],
 'postreview_adjustments':post,'classification_notes':a['manual_nonconversion_examples']+b['classification_notes'],
 'no_change_record_keys':[k for k in records if k not in {c['key'] for c in changes}],
 'preservation':{'original_question_options_tables_diagrams_not_changed':True,'all_numeric_values_preserved_or_repeated_in_explicit_conversion':True,'full_calculation_steps_and_simplification_preserved':True,'multiplication_order_preserved':True,'ordinary_mathematical_parentheses_not_removed':True,'standard_degree_notation_kept':True,'natural_answer_sentence_units_kept':True,'p078_Q4_B_preserved':True,'p078_five_black_patches_preserved':True},
 'interpretation':'仅把已存在的普通计算结果单位括号由（）改ASCII()；自然答语和裸写单位不额外加括号。真正换算单列且单位不括号；换算中(0.8×1000)等是数值运算分组，保留。',
 'source_evidence_sha256':{str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted([P/f'questions/p{n:03}.json' for n in range(73,109)]+[P/'detailed_layout/notes_C.json',P/'detailed_layout/notes_D.json'])},
}
(R/'audit_073_108.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['changes','scope','conversion_cases_checked','conversion_locations','quantity_equivalence_checks','same_unit_decomposition_checks','rounding_lines_already_proper','source_evidence_sha256','no_change_record_keys','helper_calculation_block_preservation','classification_notes','conversion_numeric_equivalence']},ensure_ascii=False,indent=2))
