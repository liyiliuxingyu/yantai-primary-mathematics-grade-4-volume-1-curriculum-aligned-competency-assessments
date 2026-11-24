import json,re,ast
from pathlib import Path
from fractions import Fraction
p=Path(__file__).resolve().parent/'audit_73_81.json';d=json.loads(p.read_text())
def ev(n):
 if isinstance(n,ast.Constant):return Fraction(str(n.value))
 if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -ev(n.operand)
 if isinstance(n,ast.BinOp):
  a,b=ev(n.left),ev(n.right)
  if isinstance(n.op,ast.Add):return a+b
  if isinstance(n.op,ast.Sub):return a-b
  if isinstance(n.op,ast.Mult):return a*b
  if isinstance(n.op,ast.Div):return a/b
 raise ValueError(ast.dump(n))
results=[]
for patch in d['patches']:
 fields={k:v for k,v in patch.items() if k in ['answer_latex','note_latex','main_formula_latex']}
 for i,x in enumerate(patch.get('local_replacement_latex',[])):fields[f'local_{i}']=x['latex']
 for field,s in fields.items():
  for block in re.findall(r'\\begin\{aligned\}(.*?)\\end\{aligned\}',s,re.S):
   vals=[]
   for row in block.split('\\\\'):
    row=row.replace('={}&','').replace('&=','').replace('&','')
    row=re.sub(r'\\text\{.*?\}','',row)
    row=row.replace(r'\times','*').replace(r'\div','/').replace('[','(').replace(']',')').replace('{','(').replace('}',')')
    if '=' in row:raise ValueError((patch['key'],field,row))
    vals.append(ev(ast.parse(row,mode='eval').body))
   assert all(v==vals[0] for v in vals),(patch['key'],field,vals)
   results.append({'key':patch['key'],'field':field,'rows':len(vals),'value':str(vals[0])})
d['independent_numeric_validation']={'arithmetic':'Fraction exact rational evaluation via AST, independent of rendered result strings','blocks_validated':len(results),'all_rows_equal':True,'details':results}
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('exact evaluated blocks',len(results))
