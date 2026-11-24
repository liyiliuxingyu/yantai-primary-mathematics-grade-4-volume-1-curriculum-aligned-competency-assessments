from pathlib import Path
import copy,sys,json,zipfile,hashlib,re
from lxml import etree as E

P=Path(__file__).resolve().parents[2];R=P.parent;W=Path(sys.argv[2]).resolve()
W.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P/'ppt_simplify/build'))
import patch_simplify as m

def J(p):return json.loads(p.read_text())
def WJ(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(p.read_bytes()).hexdigest()

source=Path(sys.argv[1]).resolve()
assert SHA(source)=='4aad33ca4bcceb8c1c0ffbdc6ba5c49f435ed75a555f7593a45cf119b84feaed','Requires exact preceding version; do not run twice on a patched deck'
out=W/'draft';out.mkdir(exist_ok=True);dest=out/source.name
assets_dir=W/'formulas';assets_dir.mkdir(exist_ok=True)
font=P/'fonts/DroidSansFallback.ttf'
ops=[
 {'type':'math','name':'p075_s03_b003_0','tex':r'(720\times2)\div(12+8)','rect':[106,120,1110,54],'points':32},
 {'type':'math','name':'p075_s03_b004_1_simplify_rhs0','tex':r'(720\times2)\div20','rect':[106,192,1110,54],'points':32},
 {'type':'math','name':'p075_s03_b004_1_simplify_rhs1','tex':r'720\times(2\div2)\div10','rect':[106,246,1110,54],'points':32}]
rules=[{'volume':5,'slide':53,'key':'p075_s03','ops':ops}]
WJ(W/'rules.json',rules)
assets={id(op):m.compile_asset(op,assets_dir,font) for op in ops}
report=m.patch_volume(source,dest,rules,assets,assets_dir)

# One native text caption belongs to the original calculation-click group.
# It explains the quantity grouping and the subsequent lawful simplification.
with zipfile.ZipFile(dest) as z:parts={i.filename:z.read(i.filename) for i in z.infolist()};infos=z.infolist()
name='ppt/slides/slide53.xml';before=parts[name];root=E.fromstring(before)
groups=[g for g in root.findall('.//p:grpSp',m.NS) if g.find('./p:nvGrpSpPr/p:cNvPr',m.NS) is not None and g.find('./p:nvGrpSpPr/p:cNvPr',m.NS).get('name')=='p075_s03_b004_1']
assert len(groups)==1
group=groups[0];old_ids=m.logical_ids(root)
template=m.find_shape(root,'p075_s03_b006_3_p0');caption=copy.deepcopy(template)
ident=max(int(n.get('id')) for n in root.findall('.//p:cNvPr',m.NS))+1
nv=m.c_nv(caption);nv.set('id',str(ident));nv.set('name','p075_s03_parentheses_explanation')
group.append(caption)
caption_op={'name':'p075_s03_parentheses_explanation','text':'先把总路程括成一个整体。\n简算用乘除性质：把20拆成2与10的积。','rect':[64,530,1152,116],'points':32}
m.patch_text(root,caption_op)
new_ids=m.logical_ids(root);m.assert_preserved_ids(old_ids,new_ids)
after=m.xml(root);original_timing=m.timing(before)
if original_timing:after=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:original_timing,after,flags=re.S)
assert m.timing(after)==original_timing
parts[name]=after
temp=dest.with_suffix('.caption.tmp')
with zipfile.ZipFile(temp,'w') as z:
 for info in infos:z.writestr(info,parts.pop(info.filename))
 for n,data in parts.items():z.writestr(n,data,compress_type=zipfile.ZIP_DEFLATED)
temp.replace(dest)
report.update({'output_sha256':SHA(dest),'bytes':dest.stat().st_size,'native_caption':caption_op,'new_caption_id':ident,'caption_original_group':'p075_s03_b004_1','reason':'总路程乘积加括号；随后以乘除性质简算，避免直接跳过原括号的误解。'})
WJ(out/'qa_package.json',[report])
WJ(W/'used_formula_assets.json',[{'tex':a['tex'],'stem':a['stem'],'source':str(a['source']),'pdf':str(a['pdf']),'svg':str(a['svg']),'png':str(a['png'])} for a in assets.values()])
print(json.dumps({'draft':str(dest),'sha256':SHA(dest),'changed_slides':[53],'native_formula_changes':3,'caption_in_original_click':True},ensure_ascii=False),flush=True)
