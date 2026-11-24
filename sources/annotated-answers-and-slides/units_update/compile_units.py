"""Compile the approved unit-format source without touching publication geometry."""
from pathlib import Path
import os,sys,json,shutil,hashlib

R=Path(__file__).resolve().parent;P=R/'project';Q=P/'units_update'
os.environ['PATH']=str(R.parent/'p78_review/tex_bin')+os.pathsep+os.environ['PATH']
sys.path.insert(0,str(P))
from build_detailed_answers import load_data,snippets,compile_fragments
assert (R/'approved_changes.json').exists(),'Wait for SOURCE_READY and approved_changes.'
rr,nn,ss,snap=load_data();items,desc=snippets(rr,nn,ss)
out=Q/'compiled';out.mkdir(exist_ok=True,parents=True)
compiled,index,tex=compile_fragments(items,out);compiled.close()
frozen=out/'snippets_frozen.pdf';shutil.copyfile(tex.with_suffix('.pdf'),frozen)
d={'snippets':len(items),'local_patches':len(desc),'compiled_tex':str(tex.resolve()),'compiled_pdf':str(frozen.resolve()),'source_files':snap,'tex_engine':'XeTeX0.999996 TeXLive2025/dev','task_local_format_used':True}
(Q/'compile_receipt.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'compiled':len(items),'locals':len(desc),'sha256':hashlib.sha256(frozen.read_bytes()).hexdigest()}),flush=True)
