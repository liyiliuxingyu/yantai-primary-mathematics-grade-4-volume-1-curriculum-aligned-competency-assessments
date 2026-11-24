from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parents[2];P=R/'project';W=R/'ppt_parentheses';D=P/'ppt_parentheses';F=D/'formulas'
F.mkdir(parents=True,exist_ok=True)
used=json.loads((W/'used_formula_assets.json').read_text())
for a in used:
 for ext in ['.tex','.pdf','.svg','.png']:
  src=W/'formulas'/(a['stem']+ext);out=F/src.name
  if ext=='.tex':out.write_text(src.read_text().replace(str((P/'fonts').resolve())+'/','fonts/'))
  else:shutil.copy2(src,out)
def check(a):
 src=(F/(a['stem']+'.tex')).resolve()
 z=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-output-directory',str(F.resolve()),str(src)],cwd=P,capture_output=True,text=True)
 output=z.stdout+z.stderr
 assert z.returncode==0 and not any(x in output for x in ['Missing character:','Overfull \\hbox','Overfull \\vbox']),src
 return {'stem':a['stem'],'tex':a['tex'],'tex_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'compiled':True}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:items=list(ex.map(check,used))
report={'passed':True,'actually_used_source_sets':len(items),'font_path':'fonts/','relative_font_path':True,'compile_cwd':'project root','missing_characters':0,'overfull_warnings':0,'items':items}
for dest in [W/'qa_portable.json',D/'qa_portable.json']:dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False),flush=True)
