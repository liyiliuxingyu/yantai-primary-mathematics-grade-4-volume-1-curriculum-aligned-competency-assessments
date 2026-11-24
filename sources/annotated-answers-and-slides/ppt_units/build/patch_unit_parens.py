#!/usr/bin/env python3
"""Approved result-unit parentheses only; all original question parts protected."""
from pathlib import Path
import concurrent.futures, hashlib, importlib.util, json, os, re, shutil, subprocess, sys
import fitz

BASE=Path(__file__).resolve().parents[2];PROJECT=BASE/'project';WORK=BASE/'ppt_units';ASSETS=PROJECT/'ppt_units/assets/formulas'
sys.path[:0]=[str(PROJECT/'followup_style/ppt'),str(PROJECT/'ppt_builder')]
spec=importlib.util.spec_from_file_location('units_native',PROJECT/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
audit=json.loads((WORK/'audit.json').read_text());ASSETS.mkdir(parents=True,exist_ok=True)
pairforms={p['raw']:p['unit'] for c in audit['result_unit_fullwidth_candidates'] for p in c['pairs'] if p['recognized_unit']}
def replace_units(s):
    return re.sub(r'（([^（）]{1,20})）',lambda x:'('+x[1]+')' if x[0] in pairforms else x[0],s)
def tex_plain(s):
    out='';i=0;ops={'×':r'\times ','÷':r'\div ','−':'-','≈':r'\approx ','≤':r'\leq ','≥':r'\geq ','…':r'\ldots ','□':r'\square '}
    while i<len(s):
        if '\u3400'<=s[i]<='\u9fff':
            j=i+1
            while j<len(s) and '\u3400'<=s[j]<='\u9fff':j+=1
            out+=r'\text{'+s[i:j]+'}';i=j;continue
        c=s[i];out+=ops.get(c,({'%':r'\%','&':r'\&','_':r'\_','#':r'\#'}.get(c,c)));i+=1
    return out
def key_for(op):return m.sha(json.dumps({k:op.get(k) for k in ('tex','rows','points','color')},ensure_ascii=False,sort_keys=True).encode())[:24]

rules={};allops=[]
manifests={v:json.loads((PROJECT/f'ppt_builder/current_metadata/volume{v:02d}/manifest.json').read_text()) for v in range(1,7)}
formulas={(v,s['slide'],f['target'].removeprefix('alt:')):f for v,man in manifests.items() for s in man['slides'] for f in s.get('formulas',[])}
for c in audit['result_unit_fullwidth_candidates']+audit.get('additional_black_solution_candidates',[]):
    old=c['text'];new=replace_units(old);assert old!=new
    assert re.findall(r'\d+(?:\.\d+)?',old)==re.findall(r'\d+(?:\.\d+)?',new)
    op={'type':'math' if c['native_math'] else'text','name':c['name'],'old_text':old,'new_text':new,'rect':c['rect'],'points':c.get('points',32),'color':c['color'] if c.get('classification')=='black_solution_equation_in_answer_analysis_tree' else'C00000'}
    if c['native_math']:
        op['points']=formulas.get((c['volume'],c['slide'],c['name']),{}).get('points',c.get('points',32))
        op['tex']=tex_plain(new)
        check=lambda value:re.sub(r'\s+','',value).replace('−','-')
        assert check(m.ast_plain(m.MathParser(op['tex']).parse()))==check(new),(c['name'],repr(new),repr(op['tex']))
        op['ast']={'t':'seq','items':[{'t':'text','v':new}]}
        op['min_scale']=.60
    else:op['text']=new
    k=(c['volume'],c['slide']);rules.setdefault(k,{'volume':c['volume'],'ui_slide':c['slide'],'slide':c['part_number'],'key':c['record_key'],'ops':[]})['ops'].append(op);allops.append(op)
uniq={key_for(op):op for op in allops if op['type']=='math'}

def environment():
    os.environ['TEXMF']='{/usr/share/texlive/texmf-dist,/usr/share/texmf}'
    fmt=WORK/'toolchain';fmt.mkdir(exist_ok=True)
    if not (fmt/'xelatex.fmt').exists():
        previous=BASE.parent/'p78_review/diagram_source/xelatex.fmt'
        if previous.exists():shutil.copy2(previous,fmt/'xelatex.fmt')
        else:
            run=subprocess.run(['xelatex','-ini','-etex','-jobname=xelatex','-progname=xelatex','*xelatex.ini'],cwd=fmt,capture_output=True,text=True)
            (fmt/'format.log.txt').write_text(run.stdout+run.stderr);assert run.returncode==0
    os.environ['TEXFORMATS']=str(fmt)+':'

def compile_batches():
    environment();pending=[(key,op)for key,op in uniq.items() if not all((ASSETS/('simplify_'+key+ext)).exists() for ext in ('.pdf','.svg','.png','.tex'))]
    font=PROJECT/'fonts/DroidSansFallback.ttf'
    for off in range(0,len(pending),100):
        items=pending[off:off+100];folder=WORK/f'compile_batch_{off//100:02d}';folder.mkdir(exist_ok=True)
        preamble=r'''\documentclass{article}
\usepackage{fix-cm,fontspec,amsmath,amssymb,xcolor}
\usepackage[active,tightpage]{preview}
\setlength\PreviewBorder{1pt}
\pagestyle{empty}
'''+r'\setmainfont{'+font.name+'}[Path={'+str(font.parent)+'/}]\n'+r'\begin{document}'+'\n'
        pages=[]
        for key,op in items:
            pts=op['points'];pages.append(r'\begin{preview}{\fontsize{'+str(pts)+'pt}{'+str(pts*1.25)+r'pt}\selectfont\color[HTML]{'+op['color']+r'}\hbox{$\displaystyle '+op['tex']+r'$}}\end{preview}')
        source=folder/'batch.tex';source.write_text(preamble+'\n'.join(pages)+'\n'+r'\end{document}'+'\n')
        run=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape',source.name],cwd=folder,capture_output=True,text=True)
        (folder/'compile.stdout.txt').write_text(run.stdout+run.stderr);assert run.returncode==0 and 'Missing character' not in run.stdout,(folder,run.stdout[-2000:])
        with fitz.open(folder/'batch.pdf') as doc:
            assert len(doc)==len(items)
            for i,(key,op) in enumerate(items):
                stem=ASSETS/('simplify_'+key);single=fitz.open();single.insert_pdf(doc,from_page=i,to_page=i);single.save(stem.with_suffix('.pdf'));single.close()
                doc[i].get_pixmap(matrix=fitz.Matrix(192/72,192/72),alpha=False).save(stem.with_suffix('.png'))
                relfont=os.path.relpath(font.parent,ASSETS).replace(os.sep,'/')+'/'
                pts=op['points'];standalone=r'\documentclass[border=1pt]{standalone}'+'\n'+r'\usepackage{fix-cm,fontspec,amsmath,amssymb,xcolor}'+'\n'+r'\setmainfont{'+font.name+'}[Path={'+relfont+'}]\n'+r'\begin{document}'+'\n'+r'{\fontsize{'+str(pts)+'pt}{'+str(pts*1.25)+r'pt}\selectfont\color[HTML]{'+op['color']+r'}$\displaystyle '+op['tex']+'$}\n'+r'\end{document}'+'\n'
                stem.with_suffix('.tex').write_text(standalone)
        def svg(item):
            key,_=item;stem=ASSETS/('simplify_'+key)
            subprocess.run(['pdftocairo','-svg',str(stem.with_suffix('.pdf')),str(stem.with_suffix('.svg'))],check=True,capture_output=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(svg,items))
        print(json.dumps({'compiled_batch':off//100,'formula_count':len(items)},ensure_ascii=False),flush=True)

def main():
    compile_batches();assets={id(op):m.compile_asset(op,ASSETS,PROJECT/'fonts/DroidSansFallback.ttf')for op in allops if op['type']=='math'}
    staging=WORK/'phase_units';staging.mkdir(exist_ok=True);reports=[]
    for v in range(1,7):
        source=next((BASE/'bundle/讲解课件').glob(f'*第{v}册*.pptx'));dest=staging/source.name
        vr=sorted([r for k,r in rules.items()if k[0]==v],key=lambda r:r['ui_slide'])
        if dest.exists():dest.unlink()
        reports.append(m.patch_volume(source,dest,vr,assets,ASSETS))
    WORK.mkdir(exist_ok=True)
    (WORK/'rules_units.json').write_text(json.dumps(sorted(rules.values(),key=lambda r:(r['volume'],r['ui_slide'])),ensure_ascii=False,indent=2)+'\n')
    (WORK/'qa_phase_units.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'changed_objects':len(allops),'changed_slides':len(rules),'unique_assets':len(uniq),'outputs':[r['output']for r in reports]},ensure_ascii=False))
if __name__=='__main__':main()
