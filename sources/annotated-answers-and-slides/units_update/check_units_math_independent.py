"""Independent global source/quantity QA for the unit-format release."""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_HALF_UP
import argparse,ast,copy,hashlib,json,re,zipfile,collections
HERE=Path(__file__).resolve().parent
if (HERE/'project/questions').is_dir():R=HERE;P=HERE/'project';Q=P/'units_update';APPROVED=HERE/'approved_changes.json'
elif (HERE.parent/'questions').is_dir():P=HERE.parent;Q=HERE;R=HERE;APPROVED=HERE/'approved_changes.json'
else:raise RuntimeError('Current project not found.')
def J(p):return json.loads(Path(p).read_text())
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(r,path):
 for k,i in re.findall(r'([A-Za-z_]+)(?:\[(\d+)\])?',path):
  r=r[k]
  if i:r=r[int(i)]
 return r
def setfield(r,path,v):
 parts=re.findall(r'([A-Za-z_]+)(?:\[(\d+)\])?',path)
 for k,i in parts[:-1]:r=r[k][int(i)] if i else r[k]
 k,i=parts[-1]
 if i:r[k][int(i)]=copy.deepcopy(v)
 else:r[k]=copy.deepcopy(v)
RESULT_UNITS={'个','人','米','厘米','分米','毫米','千米','克','毫克','千克','吨','元','角','分','秒','时','小时','分钟','米/分','米/秒','千米/时','厘米/秒','元/千克','元/盒','元/本','元/条','平方米','平方分米','平方厘米','平方千米','件','袋','块','箱','万箱','盒','本','册','万册','页','台','天','名','棵','双','次','部','辆','套','瓶','把','张','组','份','升','毫升','下','段','场','大格','摄氏度','度','千瓦时'}
def result_payload(s):return s.split('，')[0] in RESULT_UNITS
parens=re.compile(r'（([^（）]+)）')
def unitfmt(s):return parens.sub(lambda m:'('+m[1]+')' if result_payload(m[1]) else m[0],s)
def sem(s):
 s=re.sub(r'\\(?:begin|end)\{aligned\}(?:\[t\])?','',s)
 s=s.replace('\\[','').replace('\\]','').replace('\\(','').replace('\\)','').replace('\\displaystyle','').replace('\\par','').replace('\\noindent','')
 s=s.replace('&','').replace('\\\\','');return re.sub(r'\s+','',s)
def arithmetic(s):
 s=s.replace('\\times','*').replace('\\div','/').replace('×','*').replace('÷','/').replace('−','-').replace('[','(').replace(']',')').strip()
 if re.search(r'[^0-9.+*/()\-\s]',s):raise ValueError(s)
 def e(n):
  if isinstance(n,ast.Expression):return e(n.body)
  if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):return Fraction(str(n.value))
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return e(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
  if isinstance(n,ast.BinOp):
   a,b=e(n.left),e(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  raise ValueError(s)
 return e(ast.parse(s,mode='eval'))
# A common unit is chosen separately for each dimension (cm, g, fen, cm², minute, count).
F={'厘米':Fraction(1),'米':Fraction(100),'千米':Fraction(100000),'分米':Fraction(10),'毫米':Fraction(1,10),'平方厘米':Fraction(1),'平方分米':Fraction(100),'平方米':Fraction(10000),'公顷':Fraction(100000000),'平方千米':Fraction(10000000000),'亿公顷':Fraction(10000000000000000),'克':Fraction(1),'千克':Fraction(1000),'吨':Fraction(1000000),'分':Fraction(1),'角':Fraction(10),'元':Fraction(100),'万':Fraction(10000),'亿':Fraction(100000000),'件':Fraction(1),'万件':Fraction(10000),'亩':Fraction(1),'亿亩':Fraction(100000000),'分钟':Fraction(1),'小时':Fraction(60),'时':Fraction(60)}
D={u:('length' if u in ['厘米','米','千米','分米','毫米'] else 'area' if u in ['平方厘米','平方分米','平方米','公顷','平方千米','亿公顷'] else 'mass' if u in ['克','千克','吨'] else 'money' if u in ['分','角','元'] else 'duration' if u in ['分钟','小时','时'] else 'count_items' if u in ['件','万件'] else 'area_mu' if u in ['亩','亿亩'] else 'number') for u in F}
UP='|'.join(map(re.escape,sorted(F,key=len,reverse=True)))
UR=re.compile(r'\\(?:text|mathrm)\{('+UP+r')\}')
QR=re.compile(r'(\([^()]*\)|\d+(?:\.\d+)?)\\(?:text|mathrm)\{('+UP+r')\}')
def quantity(s):
 s=s.replace('\\times','*').replace('\\div','/').replace('\\displaystyle','').replace('\\,','').replace('\\;','').replace('\\!','').replace('&','').replace('{}','').strip()
 s=s.replace(r'\text{半小时}','(30)')
 def repl(m):
  v=arithmetic(m[1])*F[m[2]];return '('+str(v.numerator)+'/'+str(v.denominator)+')'
 s=QR.sub(repl,s).replace(')(',')+(')
 return arithmetic(s)
def mathblocks(s,local=False):
 for m in re.finditer(r'\\\[(.*?)\\\]|\\\((.*?)\\\)',s,re.S):
  body=m[1] if m[1] is not None else m[2]
  before=s[:m.start()].rstrip();after=s[m.end():].lstrip()
  own=bool(m[1] is not None) or bool((not before or re.search(r'\\par\s*(?:\\noindent)?\s*$',before)) and (not after or after.startswith(r'\par')))
  if local and not before and (not after or after.startswith(r'\par')):own=True
  yield body,own,m.start(),m.end()
def source_fields(files):
 for name,d in files.items():
  if name.startswith('questions/'):
   for r in d['records']:yield(name,r['key'],'answer_latex',r['answer_latex'],False)
  elif name.startswith('detailed_layout/'):
   for n in d['records']:
    yield(name,n['key'],'latex',n['latex'],False)
    for ar in ['local_replacements','original_replacements']:
     for i,p in enumerate(n.get(ar,[])):
      if p.get('kind','').startswith('black') or r'\color{black}' in p['latex']:continue
      yield(name,n['key'],f'{ar}[{i}].latex',p['latex'],True)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-final',action='store_true');args=ap.parse_args();Q.mkdir(exist_ok=True)
 approved=J(APPROVED);conv=set(approved['conversion_keys']);already=set(approved['already_proper_conversion_keys']);clock=set(approved['clock_notation_keys']);assert(len(conv),len(already),len(conv|already),len(clock))==(42,1,43,2)
 archive=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip';snapshot=Q/'baseline_source_snapshot_independent.json'
 if archive.exists():
  assert SHA(archive)==approved['baseline_source_zip_sha256']=='f40bb760503aaaf563191e6b3115aab9a719ef715312ee27868353a2a75c6a70'
  with zipfile.ZipFile(archive) as z:
   names=sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json|detailed_layout/notes_[ABCD]\.json|inline_layout/slots_[ABCD]\.json|题源核对与条件说明\.json',n));base={n:json.loads(z.read(n)) for n in names}
  W(snapshot,{'archive_sha256':SHA(archive),'files':base})
 else:base=J(snapshot)['files']
 actual={n:J(P/n) for n in base};pred=copy.deepcopy(base)
 keys=set();allfields=[];scalar=[];aggregate=[];nonconversion_exact=[]
 for c in approved['changes']:
  k=c['key'];assert k not in keys;keys.add(k)
  for f in c['field_changes']:
   name,path=f['file'],f['field'];assert name in base
   assert name.startswith(('questions/','detailed_layout/'))
   if name.startswith('questions/'):assert path=='answer_latex'
   else:assert path=='latex' or re.fullmatch(r'(?:local_replacements|original_replacements)(?:\[\d+\]\.latex)?',path),path
   br=next(x for x in base[name]['records'] if x['key']==k);ar=next(x for x in actual[name]['records'] if x['key']==k);pr=next(x for x in pred[name]['records'] if x['key']==k)
   try:old=get(br,path)
   except KeyError:old=[] if path in ['local_replacements','original_replacements'] else None
   assert old==f['old'],('baseline mismatch',k,path)
   assert get(ar,path)==f['new'],('actual mismatch',k,path)
   setfield(pr,path,f['new']);allfields.append((name,k,path))
   if isinstance(f['old'],str):
    scalar.append((name,k,path))
    if k not in conv:
     assert sem(unitfmt(f['old']))==sem(f['new']),('nonconversion mathematical/prose change',k,path)
     nonconversion_exact.append((k,path))
   else:aggregate.append((name,k,path))
 assert len(keys)==237 and len(scalar)==437 and len(aggregate)==60 and len(allfields)==497
 for name in base:assert pred[name]==actual[name],('unapproved source change',name)
 oldrec={r['key']:r for n,d in base.items() if n.startswith('questions/') for r in d['records']};newrec={r['key']:r for n,d in actual.items() if n.startswith('questions/') for r in d['records']};assert len(oldrec)==len(newrec)==867
 for k in oldrec:assert {a:v for a,v in oldrec[k].items() if a!='answer_latex'}=={a:v for a,v in newrec[k].items() if a!='answer_latex'},k
 assert newrec['p078_s04']==oldrec['p078_s04'] and newrec['p078_s04']['answer_latex'].startswith('B。')
 # Check old black corrections and exact approved additions independently from the scalar text audit.
 oldnotes={n['key']:n for name,d in base.items() if name.startswith('detailed_layout/') for n in d['records']};newnotes={n['key']:n for name,d in actual.items() if name.startswith('detailed_layout/') for n in d['records']}
 manifest=J(Q/'new_local_patches.json');byid={x['id']:x for x in manifest['records']};assert len(byid)==66
 seen=[];blacks=0;legacy=0
 for k,n in newnotes.items():
  bn=oldnotes[k]
  for arr in ['local_replacements','original_replacements']:
   before=bn.get(arr,[]);after=n.get(arr,[])
   if arr=='original_replacements':legacy+=len(after)
   assert len(after)>=len(before)
   for i,b in enumerate(before):
    if b.get('kind','').startswith('black') or r'\color{black}' in b['latex']:
     blacks+=1;assert b==after[i],('black correction changed',k,arr,i)
   for i,p in enumerate(after[len(before):],start=len(before)):
    sid=f'{k}_local{i+1}';entry=byid[sid];seen.append(sid);assert p['latex']==entry['latex'] and entry['key']==k
 assert set(seen)==set(byid) and len(seen)==66 and blacks==5 and legacy==2
 before_count=sum(len(n.get('local_replacements',n.get('original_replacements',[]))) for n in oldnotes.values());after_count=sum(len(n.get('local_replacements',n.get('original_replacements',[]))) for n in newnotes.values());assert(before_count,after_count)==(92,158)
 residual=collections.Counter();where=collections.defaultdict(list)
 for fn,k,path,s,loc in source_fields(actual):
  for m in parens.finditer(s):residual[m[1]]+=1;where[m[1]].append((k,path))
 bad=[x for x in residual if result_payload(x)];assert not bad,bad
 ordinary_allowed={'学完运算律后','乘法分配律','在下一页','利用平行四边形对边相等','保留一位小数','包括与O重合的那个顶点','1','2','3','4','5','6','7','8',r'\(1\)',r'\(2\)','续','或4.2','不另计解法'}
 assert set(residual)<=ordinary_allowed,('unknown remaining parenthesis',set(residual)-ordinary_allowed)
 # Independently recompute every actual unit/number/clock conversion formula from the live source.
 equality=[];approximations=[];clocks=[];sameunit=[];seen_keys=set();units_in_parentheses_on_conversion=[]
 for fn,k,path,s,loc in source_fields(actual):
  previous=None
  for bi,(body,own,start,end) in enumerate(mathblocks(s,loc)):
   bare=UR.findall(body);named_half=r'\text{半小时}' in body
   isclock=any(x in body for x in [r'\text{晚上}',r'\text{下午}',r'{:}']) and k in clock
   if isclock:
    assert own,(k,path,'clock not own line');t=re.sub(r'\s+|&','',body.replace(r'\displaystyle',''))
    if k=='p010_s02':assert t==r'21\text{时}=\text{晚上}9\text{时}';instant=21*60;assert instant==(9+12)*60
    else:
     assert t in [r'\text{下午}1{:}00=13{:}00',r'\text{下午}1\text{时}=13\text{时}'];instant=13*60;assert instant==(1+12)*60
    clocks.append({'key':k,'file':fn,'field':path,'body':body,'same_instant_minutes_after_midnight':instant,'passed':True});seen_keys.add(k);previous=None;continue
   if '=' not in body and r'\approx' not in body:previous=None;continue
   core=re.sub(r'\\(?:begin|end)\{aligned\}(?:\[t\])?','',body);rows=re.split(r'\\\\',core)
   if len(bare)+(1 if named_half else 0)<2 and not any(u in ['万','亿','亿公顷','亿亩'] for u in bare) and not (previous is not None and core.strip().startswith('=')):previous=None;continue
   for ri,row in enumerate(rows):
    row=row.replace('&','').replace('{}','').replace(r'\displaystyle','').strip()
    if not row:continue
    us=UR.findall(row);mhalf=r'\text{半小时}' in row
    dims={D[u] for u in us}|({'duration'} if mhalf else set());assert len(dims)<=1,(k,path,'mixed dimensions',row,dims)
    if not us and not mhalf:previous=None;continue
    if r'\approx' in row:
     left,right=row.split(r'\approx');lv=quantity(left);rv=quantity(right);target=re.search(r'(\d+(?:\.\d+)?)\\(?:text|mathrm)\{('+UP+r')\}',right);assert target
     v,u=target[1],target[2];places=len(v.split('.')[1]) if '.' in v else 0
     with localcontext() as ctx:
      ctx.prec=60;coeff=Decimal(lv.numerator)/Decimal(lv.denominator)/Decimal(F[u].numerator)*Decimal(F[u].denominator);rounded=coeff.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP)
     assert rounded==Decimal(v),(k,row,coeff,rounded,v);assert own
     approximations.append({'key':k,'file':fn,'field':path,'row':row,'unrounded_coefficient':str(coeff),'rounded_display_coefficient':v,'display_decimal_places':places,'passed':True});seen_keys.add(k);previous=rv;continue
    unitset=set(us);kind='magnitude_reexpression' if any(u in ['万','亿','万件','亿亩','亿公顷'] for u in us) else 'unit_conversion' if len(unitset)>1 or mhalf else 'same_unit_arithmetic'
    if '=' not in row:previous=None;continue
    parts=row.split('=')
    if not parts[0].strip():
     if previous is None:continue
     vals=[previous]+[quantity(x) for x in parts[1:]]
    else:vals=[quantity(x) for x in parts]
    assert len(set(vals))==1,(k,path,row,vals);previous=vals[-1]
    proof={'key':k,'file':fn,'field':path,'row':row,'classification':kind,'common_unit_values':list(map(str,vals)),'own_line':own,'passed':True}
    if kind=='same_unit_arithmetic':sameunit.append(proof)
    else:
     assert own,(k,path,'unit conversion not on own line',body)
     assert not re.search(r'\\(?:text|mathrm)\{[（(](?:'+UP+r')[）)]\}',row)
     equality.append(proof);seen_keys.add(k)
 assert seen_keys==conv|already,('conversion coverage difference',seen_keys-(conv|already),(conv|already)-seen_keys)
 # Maintain internal distinction between format review and final document playback.
 result={'passed':True,'source_final_binding':bool(args.source_final),'scope':'Independent current-source audit for global conversion own-line formatting and ASCII result-unit parentheses; source/approved/baseline three-way comparison.',
 'source_records_compared':867,'approved_changed_keys':237,'actual_answer_records_changed':sum(oldrec[k]!=newrec[k] for k in oldrec),'approved_scalar_text_fields_reviewed':len(scalar),'scalar_text_field_changes':sum(isinstance(f['old'],str) and f['old']!=f['new'] for c in approved['changes'] for f in c['field_changes']),'approved_noop_restorations':[{'key':c['key'],'field':f['field']} for c in approved['changes'] for f in c['field_changes'] if f['old']==f['new']],'approved_aggregate_note_local_fields':len(aggregate),'total_approved_field_changes':len(allfields),
 'all_original_prompts_options_tables_diagrams_conditions_unchanged':True,'all_slots_and_condition_summary_unchanged':True,'all_unapproved_source_changes':0,'nonconversion_fields_exact_except_unit_parentheses_and_layout_wrappers':len(nonconversion_exact),
 'actual_conversion_case_count':43,'changed_conversion_case_count':42,'already_proper_conversion_case_count':1,'clock_notation_case_count':2,
 'exact_quantity_rows_verified':len(equality),'same_unit_arithmetic_rows_verified':len(sameunit),'rounding_rows_verified':len(approximations),'clock_notation_blocks_verified':len(clocks),'all_exact_quantity_equalities_passed':True,'all_recognized_actual_conversion_formulas_on_own_lines':True,
 'quantity_checks':equality,'same_unit_checks':sameunit,'rounding_checks':approximations,'clock_notation_checks':clocks,
 'remaining_result_unit_fullwidth_parentheses':0,'remaining_ordinary_fullwidth_parenthetical_payloads':dict(residual),'ordinary_parentheticals_preserved':True,
 'baseline_visible_local_count':92,'current_visible_local_count':158,'new_visible_local_patches_verified':66,'old_black_corrections_preserved':5,'legacy_original_replacement_fields_reviewed':legacy,'p078_Q4_B_preserved':True,
 'approved_changes_sha256':SHA(APPROVED),'new_local_manifest_sha256':SHA(Q/'new_local_patches.json'),'baseline_source_snapshot_sha256':SHA(snapshot),'source_files_sha256':{n:SHA(P/n) for n in actual},
 'limits':['Clock labels21时/晚上9时 and下午1时/13时 are notation of the same time, not elapsed-hour equalities21=9 or1=13.','Fractions are evaluated in a common unit for each dimension; original normal degree notation and natural answer prose are preserved.','This source audit is not native PowerPoint playback or full-page PDF layout signoff; those require their separate visual reports.'],
 'native_powerpoint_playback_tested':False,'pdf_layout_tested_in_this_report':False,'evidence':['check_units_math_independent.py','baseline_source_snapshot_independent.json','approved_changes.json','new_local_patches.json']}
 W(Q/'qa_math_independent.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ['quantity_checks','same_unit_checks','rounding_checks','clock_notation_checks','source_files_sha256','remaining_ordinary_fullwidth_parenthetical_payloads']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
