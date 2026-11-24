from pathlib import Path
from fractions import Fraction
import json,re
ROOT=Path(__file__).resolve().parent
D=json.loads((ROOT/'oral_calculations.json').read_text())
# Independent shunting-yard parser: deliberately separate from the generator's AST evaluator.
def value(tex):
 s=tex.replace(r'\times','*').replace(r'\div','/').replace('[','(').replace(']',')')
 toks=re.findall(r'\d+(?:\.\d+)?|[()+*/-]',s)
 assert ''.join(toks)==re.sub(r'\s+','',s),tex
 ops=[];vals=[];pr={'+':1,'-':1,'*':2,'/':2}
 def pop():
  op=ops.pop();b=vals.pop();a=vals.pop()
  if op=='+':vals.append(a+b)
  elif op=='-':vals.append(a-b)
  elif op=='*':vals.append(a*b)
  elif op=='/':vals.append(a/b)
 for tok in toks:
  if tok[0].isdigit():vals.append(Fraction(tok))
  elif tok=='(':ops.append(tok)
  elif tok==')':
   while ops[-1]!='(':pop()
   ops.pop()
  else:
   while ops and ops[-1]!='(' and pr[ops[-1]]>=pr[tok]:pop()
   ops.append(tok)
 while ops:pop()
 assert len(vals)==1
 return vals[0]

allq={q['key']:q for p in sorted((ROOT.parent/'questions').glob('p*.json')) for q in json.loads(p.read_text())['records']}
checks=0;issues=[];equations=0;seen=[];estimates=[]
def ok(test,kind,key,detail=None):
 global checks
 checks+=1
 if not test:issues.append({'kind':kind,'key':key,'detail':detail})
for key,r in D['records'].items():
 q=allq[key]
 raw=[]
 for b in re.findall(r'\\\((.*?)\\\)',q['question_latex'],re.S):
  for s in re.split(r'\\(?:qquad|quad)\s*',b):
   s=s.strip()
   if s:raw.append(s.split('=')[0].split(r'\approx')[0].strip().rstrip('\\').strip())
 ok(len(raw)==len(r['subquestions']),'each original subquestion retained',key)
 ok(raw==[s['expression_latex'] for s in r['subquestions']],'source expression order exact',key)
 for sub in r['subquestions']:
  seen.append(sub['key']);exact=value(sub['expression_latex'])
  ok(value(sub['exact_result'])==exact,'independent exact result',sub['key'])
  ok(sub['steps'][0]==sub['expression_latex'],'first row equals original',sub['key'])
  ok(len(sub['relations'])==len(sub['steps'])-1,'every transition has relation',sub['key'])
  ok(len(sub['strategy'])>5,'individual explanation exists',sub['key'])
  for i,rel in enumerate(sub['relations']):
   if rel=='=':
    equations+=1
    ok(value(sub['steps'][i])==value(sub['steps'][i+1]),'every generated equality exact',sub['key'],sub['steps'][i:i+2])
   else:
    estimates.append(sub['key']);ok(rel=='≈' and sub['is_estimate'],'approx sign retained',sub['key'])
  if not sub['is_estimate']:ok(value(sub['steps'][-1])==exact,'last row exact',sub['key'])
  else:ok(r'\approx' in sub['answer_latex'],'typeset approximation visible',sub['key'])
  if any(t in sub['expression_latex'] for t in [r'2.4\times5',r'1.25\times8']):ok(bool(sub['scope_note']),'non-power-ten decimal multiplication flagged',sub['key'])
 ok(r['replacement_answer_latex'].count(r'\begin{aligned}')==len(raw),'each subquestion has complete derivation',key)
ok(len(set(seen))==len(seen),'stable child keys unique','all')
# Regression requested by user: independent operations on the same level happen together.
# This expression is not an oral source item, so test only the common reducer.
import importlib.util
sp=importlib.util.spec_from_file_location('oral_generator',ROOT/'build_oral_metadata.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
ok(g.ordinary_steps(r'125\times8+125\times4')[1]=='1000+500','independent multiplications simultaneous','reducer')
report={'records':len(D['records']),'subquestions':len(seen),'aggregated_records':sum(x['aggregated'] for x in D['records'].values()),'equality_transitions':equations,'approximation_transitions':len(estimates),'checks':checks,'issues':issues,'scope':'Every source oral expression and its original order, every generated exact equality, every approximation sign, grade-scope caution, child-key coverage and simultaneous independent calculation rule checked. This does not claim all possible mental strategies are exhausted.'}
(ROOT/'oral_metadata_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
if issues:raise SystemExit(1)
