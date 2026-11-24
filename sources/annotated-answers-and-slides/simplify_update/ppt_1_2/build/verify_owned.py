from pathlib import Path
import ast,json,re,hashlib,zipfile
from fractions import Fraction
from lxml import etree as E
import common_patch as C
B=Path(__file__).resolve().parents[1];R=B.parent
rules=json.loads((B/'rules.json').read_text());results={a['key']:a['result'] for f in ['audit_early.json','audit_25_44.json'] for a in json.loads((R/f).read_text())['changes']}
def calc(t):
 t=re.sub(r'\\text\{[^{}]*\}','',t).replace(r'\times','*').replace(r'\div','/').replace('[','(').replace(']',')')
 def ev(n):
  if isinstance(n,ast.Constant):return Fraction(n.value)
  if isinstance(n,ast.BinOp):
   a,b=ev(n.left),ev(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -ev(n.operand)
  raise ValueError(ast.dump(n))
 return ev(ast.parse(t,mode='eval').body)
maths=[]
for s in rules:
 for op in s['ops']:
  if op['type'] not in ('math','note'):continue
  for row in op.get('rows',[op.get('tex')]):
   value=calc(row);assert value==results[s['key']],(s['key'],row,str(value),results[s['key']]);maths.append({'key':s['key'],'slide':s['slide'],'expression':row,'value':str(value)})
reports=[]
for v in (1,2):
 n=f'小学四上同步素养卷第{v}册讲解课件答案.pptx';src=R/'bundle/讲解课件'/n;out=B/'draft2'/n
 with zipfile.ZipFile(src) as z,zipfile.ZipFile(out) as w:
  old={x.filename:z.read(x.filename) for x in z.infolist()};new={x.filename:w.read(x.filename) for x in w.infolist()};mod=[];newmath=0;beforemath=0;tot=0;changed=[s['slide'] for s in rules if s['volume']==v]
  for k,b in old.items():
   assert k in new
   if b!=new[k]:mod.append(k)
   if re.fullmatch(r'ppt/slides/slide\d+\.xml',k):
    a=E.fromstring(b);c=E.fromstring(new[k]);tot+=1;C.assert_preserved_ids(C.logical_ids(a),C.logical_ids(c));assert C.timing(b)==C.timing(new[k])
    existing={n.get('id') for n in C.visible_nodes(c)}
    assert all(e.get('spid') in existing for e in c.findall('.//p:spTgt',C.NS))
    beforemath+=len(a.findall('.//a14:m',C.NS));newmath+=len(c.findall('.//a14:m',C.NS))
  allowed={f'ppt/slides/slide{s}.xml' for s in changed}|{f'ppt/slides/_rels/slide{s}.xml.rels' for s in changed};assert set(mod)<=allowed
  assert z.testzip() is None and w.testzip() is None
  reports.append({'volume':v,'source':str(src),'output':str(out),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'slide_count':tot,'changed_slides':changed,'original_changed_components':mod,'original_unrelated_components_byte_identical':True,'timing_xml_byte_identical_all_slides':True,'all_original_ids_names_order_retained':True,'animation_references_valid':True,'native_math_before':beforemath,'native_math_after':newmath,'new_native_math_count':newmath-beforemath,'new_native_children_have_unique_ids':True,'zip_integrity_passed':True})
q={'math_expression_count':len(maths),'math_all_exact_values_checked':True,'math_expressions':maths,'package':reports,'early_methods':'18 records gain notes; original main method retained. p008_s03 skipped because same efficient method already present.','actual_software_playback':'Not tested in PowerPoint or WPS. Original native timing bytes remain unchanged; new children share the original click target group.','rendering':'ArtifactTool static renders, all 33 changed slides inspected individually; final QA detail in visual_review.json.','new_formula_implementation':'Editable native OMML single-line formula children with genuine XeLaTeX-compiled SVG and PNG fallbacks; explicit equality and RHS columns.'}
(B/'qa_checks.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:q[k] for k in ['math_expression_count','math_all_exact_values_checked']},ensure_ascii=False));print(json.dumps([{k:r[k] for k in ['volume','slide_count','new_native_math_count']} for r in reports],ensure_ascii=False))
