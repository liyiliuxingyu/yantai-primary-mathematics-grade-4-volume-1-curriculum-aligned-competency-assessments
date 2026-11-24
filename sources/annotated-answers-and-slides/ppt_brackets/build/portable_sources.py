from pathlib import Path
import json,shutil,re,subprocess,concurrent.futures
R=Path(__file__).resolve().parents[1];P=R.parent if (R.parent/'ppt_builder').is_dir() else R.parent/'project';D=P/'ppt_brackets';A=D/'formulas';A.mkdir(parents=True,exist_ok=True)
items=json.loads((R/'used_formula_assets.json').read_text());mapped=[]
for a in items:
 out={k:v for k,v in a.items() if k not in ['source','pdf','png','svg']}
 for k,ext in [('source','.tex'),('pdf','.pdf'),('png','.png'),('svg','.svg')]:
  dest=A/(a['stem']+ext)
  if k=='source':dest.write_text(re.sub(r'Path=\{[^}]*\}',r'Path={fonts/}',Path(a[k]).read_text()))
  else:shutil.copy2(a[k],dest)
  out[k]='ppt_brackets/formulas/'+dest.name
 mapped.append(out)
(D/'used_formula_assets.json').write_text(json.dumps(mapped,ensure_ascii=False,indent=2)+'\n')
outdir=R/'portable_compile';outdir.mkdir(exist_ok=True)
def one(a):
 source=A/(a['stem']+'.tex')
 cp=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-output-directory',str(outdir.resolve()),str(source.resolve())],cwd=P,capture_output=True,text=True)
 (outdir/(a['stem']+'.stdout.txt')).write_text(cp.stdout+cp.stderr)
 assert cp.returncode==0 and 'Missing character' not in cp.stdout,(a['stem'],cp.returncode)
 return a['stem']
oldqa=json.loads((R/'qa_portable.json').read_text()) if (R/'qa_portable.json').exists() else {'sources':[]}
oldset=set(oldqa['sources']);pending=[a for a in items if a['stem'] not in oldset]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:compiled_now=list(pool.map(one,pending))
done=[a['stem'] for a in items];assert set(done)<=oldset|set(compiled_now)
qa={'passed':True,'source_sets':len(done),'all_sources_actually_xelatex_compiled_from_project_root':True,'font_path':'fonts/','missing_glyphs':0,'sources':done}
for p in [R/'qa_portable.json',D/'qa_portable.json']:p.write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
print('Portable sources compiled:',len(done),flush=True)
