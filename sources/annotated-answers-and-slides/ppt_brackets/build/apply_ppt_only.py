from pathlib import Path
import json,sys,importlib.util,copy,shutil
R=Path(__file__).resolve().parents[1];P=R.parent/'project';sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
spec=importlib.util.spec_from_file_location('m',P/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
J=lambda p:json.loads(p.read_text())
def put(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
inventory=J(R/'baseline_inventory.json');rules=J(R/'rules.json');matches=J(R/'match_report.json');assets={};iv=next(x for x in inventory if x['volume']==6)
for ch in J(R.parent/'approved_changes.json')['changes']:
 for change in ch.get('ppt_only_row_replacements',[]):
  op=m.ast_plain(m.MathParser(change['old']).parse());np=m.ast_plain(m.MathParser(change['new']).parse());found=[]
  for s in iv['slides']:
   for sh in s['shapes']:
    if sh['name'].startswith(ch['key']) and sh['native_math'] and not sh['group'] and sh['text']==op:found.append((s,sh))
  assert len(found)==1;slide,shape=found[0]
  rule=next(r for r in rules if r['volume']==6 and r['slide']==slide['part_number']);rule['ops'].append({'type':'math','name':shape['name'],'tex':change['new'],'points':32,'color':'C00000','rect':shape['rect'],'expected_old_plain':op,'expected_new_plain':np,'ppt_only':True})
  matches.append({'key':ch['key'],'old_tex':change['old'],'new_tex':change['new'],'old_plain':op,'new_plain':np,'exact':[[6,slide['slide'],slide['part_number'],shape['name']]],'partial':[],'correct':[],'ppt_only':True,'reason':change['reason']})
selected=[r for r in rules if r['volume']==6];used=J(R/'used_formula_assets.json');stems={x['stem'] for x in used}
for rule in selected:
 for op in rule['ops']:
  a=m.compile_asset(op,R/'formulas',P/'fonts/DroidSansFallback.ttf');assets[id(op)]=a
  if a['stem'] not in stems:used.append({k:str(a[k]) for k in ['key','stem','tex','source','pdf','svg','png']});stems.add(a['stem'])
source=R.parent/'bundle/讲解课件'/iv['filename'];out=R/'draft_r2';out.mkdir(exist_ok=True)
report=m.patch_volume(source,out/source.name,selected,assets,R/'formulas');report.update({'volume':6,'changed_ui_slides':[r['ui_slide'] for r in selected],'changed_keys':sorted({r['key'] for r in selected}),'formula_count':sum(len(r['ops']) for r in selected)})
shutil.copy2(out/source.name,R/'draft'/source.name);report['output']=str(R/'draft'/source.name)
reports=J(R/'draft/qa_package.json');reports=[report if x['volume']==6 else x for x in reports]
for p,d in [(R/'rules.json',rules),(R/'match_report.json',matches),(R/'used_formula_assets.json',used),(R/'draft/qa_package.json',reports)]:put(p,d)
print('PPT-only rows added; total',sum(r['formula_count'] for r in reports),flush=True)
