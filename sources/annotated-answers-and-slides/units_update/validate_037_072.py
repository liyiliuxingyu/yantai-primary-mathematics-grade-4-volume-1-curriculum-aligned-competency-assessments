import json,re
from pathlib import Path
from fractions import Fraction
R=Path('units_review');p=R/'audit_037_072.json';d=json.loads(p.read_text())
u={
 '平方千米':('area',1000000),'平方米':('area',1),'平方分米':('area',Fraction(1,100)),'平方厘米':('area',Fraction(1,10000)),'公顷':('area',10000),
 '千米':('length',1000),'米':('length',1),'分米':('length',Fraction(1,10)),'厘米':('length',Fraction(1,100)),'毫米':('length',Fraction(1,1000)),
 '吨':('mass',1000),'千克':('mass',1),'克':('mass',Fraction(1,1000)),
 '元':('money',1),'角':('money',Fraction(1,10)),'分':('money',Fraction(1,100)),
 '万件':('pieces',10000),'件':('pieces',1),'万':('number',10000),'亿':('number',100000000)}
units='|'.join(sorted(u,key=len,reverse=True));pat=re.compile(r'(\d+(?:\.\d+)?)(?:('+units+r'))?')
def quantity(s):
 total=Fraction(0);kind=None;end=0
 for m in pat.finditer(s):
  assert m.start()==end,s
  name=m[2];kd,fac=u[name]if name else('number',1)
  assert kind in [None,kd],(s,kind,kd)
  kind=kd;total+=Fraction(m[1])*fac;end=m.end()
 assert end==len(s),(s,end)
 return kind,total
checks=[]
for x in d['conversion_inventory']:
 for a,b in x['quantities']:
  A,B=quantity(a),quantity(b);assert A==B,(x['key'],a,b,A,B)
  checks.append({'key':x['key'],'source':a,'target':b,'equal':True})
new_math=0;changed=0;unit_paren_only=0
for x in d['changes']:
 for f in x['fields']:
  new=f['new'];old=f['old'];changed+=1
  assert new.count(r'\[')==new.count(r'\]'),(x['key'],f['field'],'display')
  assert new.count('{')==new.count('}'),(x['key'],f['field'],'braces')
  assert not re.search(r'（(?:米|厘米|千米|千克|克|元|分|平方米|平方厘米|毫克|吨|小时|天|秒|万箱|个|人|份|块|瓶|棵|袋)(?:，最远|，最近)?）',new),(x['key'],f['field'])
  if not f['conversion_layout_changed']:
   tokens={'米','厘米','袋','元','瓶','棵','份','块','千米','毫克','人','克','千克','平方厘米','平方米','个','吨','分','秒','天','千米，最远','千米，最近','小时','万箱'}
   norm=lambda s:re.sub(r'（([^）]{1,30})）',lambda m:'('+m[1]+')'if m[1]in tokens else m[0],s)
   assert norm(old)==new,(x['key'],f['field'],'nonformat change')
   unit_paren_only+=1
receipt={'conversion_equalities_verified':len(checks),'all_quantity_equalities_exact':True,'changed_fields_syntax_checked':changed,'fields_only_ascii_parenthesis_changes':unit_paren_only,'all_new_display_delimiters_and_braces_balanced':True,'remaining_Chinese_result_unit_parentheses':0,'checks':checks}
(R/'audit_037_072_validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items()if k!='checks'},ensure_ascii=False))
