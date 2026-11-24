from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parents[1];P=R.parent/'project';D=P/'ppt_recheck/late';F=D/'formulas';F.mkdir(parents=True,exist_ok=True)
def J(p):return json.loads(p.read_text())
reports=J(R/'draft_late_r4/qa_package.json')[:1]+J(R/'draft_late_r2/qa_package.json')[1:]
used={Path(n).stem for rec in reports for n in rec['new_parts'] if n.endswith(('.svg','.png'))}
for stem in sorted(used):
 for ext in ['.tex','.pdf','.svg','.png']:
  src=R/'formulas'/(stem+ext);out=F/src.name
  if ext=='.tex':out.write_text(src.read_text().replace(str((P/'fonts').resolve())+'/','fonts/'))
  else:shutil.copy2(src,out)
def check(stem):
 src=(F/(stem+'.tex')).resolve()
 z=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-output-directory',str(F.resolve()),str(src)],cwd=P,capture_output=True,text=True)
 full=z.stdout+z.stderr
 assert z.returncode==0 and not any(x in full for x in ['Missing character:','Overfull \\hbox','Overfull \\vbox']),stem
 return {'stem':stem,'tex_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'compiled':True}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:items=list(ex.map(check,sorted(used)))
report={'passed':True,'actually_used_source_sets':len(used),'font_path':'fonts/','relative_font_path':True,'compile_cwd':'project root','missing_characters':0,'overfull_warnings':0,'items':items}
(R/'qa_portable_late.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(D/'qa_portable_late.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('Portable formula sets compiled',len(used),flush=True)
