from pathlib import Path
import sys,json,zipfile,copy,importlib.util,concurrent.futures,shutil
from lxml import etree as E
R=Path(__file__).resolve().parents[1];P=R.parent/'project'
sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
spec=importlib.util.spec_from_file_location('m',P/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
J=lambda p:json.loads(p.read_text())
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
matches=J(R/'match_report.json');inventory=J(R/'baseline_inventory.json');rules={};assets_dir=R/'formulas';assets_dir.mkdir(exist_ok=True)
for row in matches:
 assert len(row['exact'])==1 and not row['partial']
 v,slide,part,name=row['exact'][0];iv=next(x for x in inventory if x['volume']==v);ss=next(x for x in iv['slides'] if x['part_number']==part);sh=next(x for x in ss['shapes'] if x['name']==name)
 src=R.parent/'bundle/讲解课件'/iv['filename']
 with zipfile.ZipFile(src) as z:root=E.fromstring(z.read(f'ppt/slides/slide{part}.xml'))
 sp=m.find_shape(root,name);points={int(r.get('sz'))/100 for r in sp.findall('.//a:rPr',m.NS) if r.get('sz')};colors={c.get('val') for c in sp.findall('.//a:rPr/a:solidFill/a:srgbClr',m.NS)}
 assert len(points)==1 and len(colors)==1,(name,points,colors)
 color=colors.pop();assert color in ['C00000','FF0000'],(name,'must be a red answer',color)
 assert row['old_plain'].translate(str.maketrans('','','()[]'))==row['new_plain'].translate(str.maketrans('','','()[]'))
 op={'type':'math','name':name,'tex':row['new_tex'],'points':points.pop(),'color':color,'rect':sh['rect'],'expected_old_plain':row['old_plain'],'expected_new_plain':row['new_plain']}
 rules.setdefault((v,part),{'volume':v,'slide':part,'ui_slide':slide,'key':row['key'],'ops':[]})['ops'].append(op)
rules=sorted(rules.values(),key=lambda r:(r['volume'],r['ui_slide']));put(R/'rules.json',rules)
unique={m.sha(json.dumps({k:o.get(k) for k in ['tex','points','color']},sort_keys=True).encode()):o for r in rules for o in r['ops']}
def compile_one(item):
 key,op=item;return key,m.compile_asset(op,assets_dir,P/'fonts/DroidSansFallback.ttf')
if __name__=='__main__':
 with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:compiled=dict(pool.map(compile_one,unique.items()))
 used=[];assets={}
 for r in rules:
  for op in r['ops']:
   key=m.sha(json.dumps({k:op.get(k) for k in ['tex','points','color']},sort_keys=True).encode());assets[id(op)]=compiled[key]
 for a in compiled.values():used.append({k:str(a[k]) for k in ['key','stem','tex','source','pdf','svg','png']})
 out=R/'draft';out.mkdir(exist_ok=True);reports=[]
 for v in range(1,7):
  iv=next(x for x in inventory if x['volume']==v);src=R.parent/'bundle/讲解课件'/iv['filename'];assert m.sha(src.read_bytes())==iv['sha256'];selected=[r for r in rules if r['volume']==v]
  if selected:
   report=m.patch_volume(src,out/src.name,selected,assets,assets_dir);report.update({'volume':v,'changed_ui_slides':[r['ui_slide'] for r in selected],'changed_keys':sorted({r['key'] for r in selected}),'formula_count':sum(len(r['ops']) for r in selected)})
  else:
   shutil.copy2(src,out/src.name);report={'volume':v,'source':str(src),'output':str(out/src.name),'source_sha256':iv['sha256'],'output_sha256':iv['sha256'],'total_slides':len(iv['slides']),'changed_ui_slides':[],'changed_slides':[],'changed_keys':[],'formula_count':0,'unchanged_copy':True}
  reports.append(report)
 put(out/'qa_package.json',reports);put(R/'used_formula_assets.json',used)
 print(json.dumps([{'volume':r['volume'],'slides':r['total_slides'],'changed':r['changed_ui_slides'],'formulas':r['formula_count']} for r in reports],ensure_ascii=False),flush=True)
