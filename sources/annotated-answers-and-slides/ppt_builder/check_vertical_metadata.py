from pathlib import Path
from decimal import Decimal
import json
ROOT=Path(__file__).resolve().parent
D=json.loads((ROOT/'vertical_calculations.json').read_text())
checks=[];issues=[]

def ensure(ok,key,check,detail=None):
 checks.append({'key':key,'check':check,'passed':bool(ok)})
 if not ok:issues.append({'key':key,'check':check,'detail':detail})

def val(c,row,division=False):
    n=c['column_count'];dot=c.get('decimal_column')
    ans=Decimal(0)
    for item in row['cells']:
        col=item['column'];s=item['text']
        if not s.isdigit() or col<0:continue
        power=(n-1-col) if dot is None else (dot-col-1 if col<dot else dot-col)
        ans+=Decimal(s)*(Decimal(10)**power)
    return ans

for key,record in D['records'].items():
 for c in record['calculations']:
  ident=c['id'];op=c['op'];a,b=map(Decimal,c['operands']);rows=c['rows']
  ensure(all(len(x['text'])==1 for row in rows for x in row['cells']),ident,'one editable character per cell')
  ensure(all(len({x['column'] for x in row['cells']})==len(row['cells']) for row in rows),ident,'no colliding cell columns')
  ensure(all(x['column']<c['column_count'] for row in rows for x in row['cells']),ident,'all numeric cells within declared columns')
  if op in '+-':
   ensure(val(c,rows[0])==a,ident,'first operand reconstructs from columns')
   ensure(val(c,rows[1])==b,ident,'second operand reconstructs from columns')
   target=a+b if op=='+' else a-b
   ensure(Decimal(c['result'])==target,ident,'exact Decimal result')
   if c['show_result']:ensure(val(c,rows[-1])==target,ident,'result reconstructs from columns')
   if c.get('decimal_column') is not None:
    ensure(all(next(x['column'] for x in row['cells'] if x['text']=='.')==c['decimal_column'] for row in rows),ident,'all decimal points align')
   ensure(bool(rows[1].get('rule_after')),ident,'operation has horizontal rule')
  elif op=='×':
   ensure(val(c,rows[0])==a,ident,'multiplicand reconstructs from columns')
   ensure(val(c,rows[1])==b,ident,'multiplier reconstructs from columns')
   ensure(Decimal(c['result'])==a*b,ident,'integer product exact')
   partials=[row for row in rows if row['kind']=='partial_product']
   ensure(sum((val(c,row) for row in partials),Decimal(0))==a*b,ident,'shifted partial products sum to result')
   ensure(all(val(c,row)==Decimal(row['numeric_value']) for row in partials),ident,'each partial product place shift correct')
   if c['show_result']:ensure(val(c,rows[-1])==a*b,ident,'product result reconstructs from columns')
   ensure(bool(rows[1].get('rule_after')) and bool(partials[-1].get('rule_after')),ident,'both multiplication rules exist')
  else:
   q,rem=map(int,[c['quotient'],c['remainder']]);ia,ib=int(a),int(b)
   ensure(ia==ib*q+rem and 0<=rem<ib,ident,'division quotient/remainder identity')
   ensure(val(c,rows[0])==q,ident,'quotient digit positions correct')
   ensure(val(c,rows[1])==a,ident,'dividend positions correct')
   ensure(''.join(x['text'] for x in rows[1]['cells'] if x['column']<0)==str(ib),ident,'divisor preserved on left')
   ensure(val(c,rows[-1])==rem,ident,'final remainder positions correct')
   trials=[r for r in rows if r['kind']=='trial_product']
   ensure(len(trials)==len(c['division_steps']),ident,'one trial product per quotient step')
   for row,step in zip(trials,c['division_steps']):
    shift=c['column_count']-1-step['end_column']
    ensure(val(c,row)==Decimal(step['trial_product'])*(Decimal(10)**shift),ident,'trial product columns correct',step)
    ensure(step['input_partial_dividend']-step['trial_product']==step['remainder'],ident,'step subtraction exact',step)
    ensure(step['trial_product']==ib*step['quotient_digit'],ident,'step trial product exact',step)
    ensure(step['remainder']<ib,ident,'step remainder less than divisor',step)
    ensure(bool(row.get('rule_after')),ident,'division subtraction rule exists')

report={'records':len(D['records']),'calculations':sum(len(x['calculations']) for x in D['records'].values()),'checks':len(checks),'issues':issues,'scope':'independent reconstruction of every digit grid, decimal point, shifted partial product, quotient placement, trial product, remainder, and required rule. This is metadata validation, not a PowerPoint visual or playback test.'}
(ROOT/'vertical_metadata_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
if issues:raise SystemExit(1)
