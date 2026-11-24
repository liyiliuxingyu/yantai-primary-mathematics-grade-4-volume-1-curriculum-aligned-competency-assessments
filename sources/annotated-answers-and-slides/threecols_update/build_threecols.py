"""Reflow current per-question red explanations into three Kai columns.

Mathematics is retained verbatim. Equations too wide for one column occupy an
unscaled full-width row between three-column prose sections.
"""
from pathlib import Path
import json,re,subprocess,hashlib,sys,copy,math,os
import fitz,numpy as np

R=Path(__file__).resolve().parents[1]
Q=R/'threecols_update'; C=Q/'compiled'
ROOT=R.parent
J=lambda p:json.loads(Path(p).read_text())
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ENGINE=os.environ.get('XELATEX','xelatex')
MATH=re.compile(r'\\\[(.*?)\\\]|\\\((.*?)\\\)',re.S)
def math_segments(body):
    return [m for m in MATH.finditer(body) if m.group(1) is not None or r'\begin{aligned}' in m.group(2) or r'\begin{array}' in m.group(2)]
PRE=r'''\documentclass[multi=snippet,border={5bp 20bp 5bp 5bp}]{standalone}
\usepackage{fontspec,amssymb,array,graphicx,xcolor,tikz,enumitem,booktabs,multicol}
\usepackage[fleqn]{amsmath}
\usetikzlibrary{calc,arrows.meta,angles,quotes,decorations.pathreplacing,patterns,positioning,intersections}
\setmainfont[Path=fonts/,AutoFakeBold=1.2]{FandolKai-Regular.otf}
\definecolor{answerred}{RGB}{205,20,35}
\newenvironment{snippet}[3]{\begin{minipage}{#1bp}\color{answerred}\fontsize{#2}{#3}\selectfont\raggedright}{\end{minipage}}
\setlength{\parindent}{0pt}\setlength{\parskip}{2bp}
\setlength{\abovedisplayskip}{3bp}\setlength{\belowdisplayskip}{3bp}
\setlength{\abovedisplayshortskip}{2bp}\setlength{\belowdisplayshortskip}{2bp}
\setlength{\mathindent}{0bp}\setlength\jot{1pt}\setlist{nosep,leftmargin=*}
\setlength{\columnsep}{11bp}\setlength{\columnseprule}{0.18bp}
\def\columnseprulecolor{\color{answerred!45}}
\setlength{\multicolsep}{0bp}\setlength{\premulticols}{0bp}\setlength{\postmulticols}{0bp}
\setcounter{unbalance}{0}\setcounter{minrows}{1}
\XeTeXlinebreaklocale "zh"\XeTeXlinebreakskip=0pt plus 1pt\emergencystretch=3em\sloppy
\begin{document}
'''

def run(tex):
    p=subprocess.run([ENGINE,'-interaction=nonstopmode','-halt-on-error','-output-directory',str(C),str(tex)],cwd=R,capture_output=True,text=True)
    tex.with_suffix('.stdout.log').write_text(p.stdout+p.stderr)
    assert p.returncode==0,p.stdout[-5000:]
    return tex.with_suffix('.log').read_text()

def compile_notes():
    sys.path.insert(0,str(R))
    from build_detailed_answers import load_data,snippets
    rr,nn,ss,snap=load_data();all_items,_=snippets(rr,nn,ss)
    W(Q/'items.json',all_items)
    items=[x for x in all_items if x['kind']=='note']
    maths=[]
    for n in items:
        for i,m in enumerate(math_segments(n['body'])):
            maths.append((n['id'],i,m.group(1) or m.group(2)))
    tex=C/'measure.tex'
    tex.write_text(PRE+'\n'.join(r'\fontsize{11.5}{14}\selectfont\sbox0{$\displaystyle '+s+r'$}\typeout{MEASURE:'+k+':'+str(i)+r':\the\wd0}' for k,i,s in maths)+r'\begin{snippet}{5}{11.5}{14}x\end{snippet}\end{document}')
    log=run(tex)
    widths={(k,int(i)):float(w)*72/72.27 for k,i,w in re.findall(r'MEASURE:([^:]+):(\d+):([\d.]+)pt',log)}
    assert len(widths)==len(maths)
    def cols(s):
        return r'\begin{multicols}{3}\raggedcolumns '+s+r'\end{multicols}' if s.strip() else ''
    rendered=[];wide=[]
    for n in items:
        cursor=0;piece='';parts=[]
        for i,m in enumerate(math_segments(n['body'])):
            piece+=n['body'][cursor:m.start()]
            expr=m.group(1) or m.group(2)
            if widths[n['id'],i]>159:
                parts.extend([cols(piece),r'\['+expr+r'\]']);piece=''
                wide.append({'key':n['id'],'math_index':i,'width':widths[n['id'],i]})
            else:piece+=r'\['+expr+r'\]'
            cursor=m.end()
        piece+=n['body'][cursor:];parts.append(cols(piece))
        body=''.join(parts)
        body=re.sub(r'\\\((.*?)\\\)', lambda m:r'\('+m.group(1).replace(',',r',\allowbreak ')+r'\)\allowbreak ',body,flags=re.S)
        body=re.sub(r'(\\[A-Za-z]+)(?=[\u3400-\u9fff])',r'\1 ',body)
        n['typeset_body']=body
        rendered.append('% '+n['id']+'\n'+r'\typeout{SNIPPET:'+n['id']+r'}\begin{snippet}{505}{11.5}{14}'+body+r'\end{snippet}')
    tex=C/'threecols.tex';tex.write_text(PRE+'\n'.join(rendered)+r'\end{document}')
    log=run(tex)
    warnings=[];key=None
    for line in log.splitlines():
        if line.startswith('SNIPPET:'):key=line.split(':')[1]
        if any(s in line for s in ['Overfull','Missing character','Package multicol Warning']):warnings.append({'key':key,'message':line})
    W(Q/'compile_warnings.json',warnings)
    doc=fitz.open(tex.with_suffix('.pdf'));assert len(doc)==len(items)
    index={}
    for n,page in zip(items,doc):
        pix=page.get_pixmap(matrix=fitz.Matrix(3,3),alpha=True)
        aa=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,4)
        yy,xx=np.where(aa[:,:,3]>0);assert len(xx)
        assert yy.min()>1 and yy.max()<pix.height-2,(n['id'],'standalone ink touches edge')
        # Preserve all three column positions, including sparse last columns.
        clip=fitz.Rect(0,max(0,(yy.min()-1)/3),page.rect.width,min(page.rect.height,(yy.max()+2)/3))
        index[n['id']]={**n,'page':page.number+1,'clip':list(clip),'ink_width':page.rect.width,'ink_height':clip.height,'columns':3,'font_family':'FandolKai-Regular','font_pt':11.5,'body_sha256':hashlib.sha256(n['body'].encode()).hexdigest()}
    W(C/'snippet_index.json',index);W(Q/'wide_math.json',wide)
    print('COMPILED',len(index),'notes;',len(wide),'wide unscaled equations;',len(warnings),'warnings',flush=True)
    return index

def patch_pdf():
    sys.path.insert(0,str(R))
    from bracket_update.patch_pdf import active_roots,match_root,remove_page_draw
    old=J(Q/'baseline_release.json') if (Q/'baseline_release.json').exists() else J(R/'detailed_layout/current_release.json');baseline=ROOT/'downloads/小学同步素养四年级上册数学答案.pdf'
    assert SHA(baseline)==old['sha256']
    idx=J(C/'snippet_index.json');assert set(idx)=={a['key']for a in old['answers']}
    doc=fitz.open(baseline);compiled=fitz.open(C/'threecols.pdf');rel=copy.deepcopy(old);pageplans=[]
    for book in range(1,109):
        pn=next(m['answer_pdf_page']for m in old['mapping']if m['book_page']==book)
        page=doc[pn-1];oldheight=page.rect.height
        roots=active_roots(doc,page)
        rootrect={x[0]:list(fitz.Rect(x[3])*page.transformation_matrix)for x in roots}
        notes=sorted([a for a in old['answers']if a['book_page']==book],key=lambda a:a['target_rect'][1])
        note_roots={match_root(doc,page,a['target_rect'])[0]:a['key']for a in notes}
        groups={};plans={};seams=[]
        for a in notes:groups.setdefault(a['source_cut_y'],[]).append(a)
        for cut,group in sorted(groups.items()):
            boundary=next(b['target_rect'][1]for b in old['bands']if b['book_page']==book and abs(b['source_rect'][1]-cut)<.01)
            end=0
            for a in group:
                oldrect=fitz.Rect(a['target_rect']);e=idx[a['key']]
                y=max(oldrect.y0,end+4)
                plans[a['key']]=[73,y,73+e['ink_width'],y+e['ink_height']];end=y+e['ink_height']
            extra=max(0,math.ceil(end+4-boundary))
            if extra:seams.append({'old_y':boundary,'extra':extra,'source_cut_y':cut})
        shift=lambda y:sum(s['extra']for s in seams if s['old_y']<=y+.003)
        extra=sum(s['extra']for s in seams)
        for x in roots:
            if x[0]in note_roots:remove_page_draw(doc,page,x[1])
        page.set_mediabox(fitz.Rect(0,0,595,oldheight+extra));page=doc.reload_page(page)
        for x in roots:
            if x[0]in note_roots:continue
            typ,val=doc.xref_get_key(x[0],'Matrix');assert typ=='array'
            matrix=[float(v)for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][-+]?\d+)?',val)]
            matrix[5]+=extra-shift(rootrect[x[0]][1])
            doc.xref_set_key(x[0],'Matrix','['+' '.join(f'{v:.10f}'for v in matrix)+']')
        page=doc.reload_page(page)
        prose_rows=J(Q/'original_prose.json')['records'] if (Q/'original_prose.json').exists() else []
        for row in [x for x in prose_rows if x['book_page']==book]:
            rect=fitz.Rect(row['mask_rect']);dy=shift(rect.y0)
            page.draw_rect(rect+(0,dy,0,dy),fill=(1,1,1),color=None,overlay=True)
        for a in [a for a in rel['answers']if a['book_page']==book]:
            e=idx[a['key']];t=fitz.Rect(plans[a['key']]);dy=shift(a['target_rect'][1]);t+=(0,dy,0,dy)
            page.show_pdf_page(t,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
            a.update({'target_rect':list(t),'columns':3,'font_family':'FandolKai-Regular'})
        for name in ['bands','moved_footers','moved_headings']:
            for item in rel[name]:
                if item['book_page']==book:
                    t=fitz.Rect(item['target_rect']);dy=shift(t.y0);item['target_rect']=list(t+(0,dy,0,dy))
        for m in rel['mapping']:
            if m['book_page']==book:m['page_size']=[595,oldheight+extra];m['layout']='Three-column Kai red explanations within original question gaps.'
        pageplans.append({'book_page':book,'pdf_page':pn,'old_height':oldheight,'new_height':oldheight+extra,'seams':seams,'notes':plans})
    out=ROOT/'output/pdf/小学同步素养四年级上册数学答案.pdf';doc.save(out,garbage=3,deflate=True)
    rel.update({'run_name':'three_columns_kai','pdf':str(out),'sha256':SHA(out),'previous_pdf_sha256':SHA(baseline),'note_font_pt':11.5,'explanation_columns':3,'explanation_font':'FandolKai-Regular','compiled_tex':'threecols_update/compiled/threecols.tex','compiled_pdf':'threecols_update/compiled/threecols.pdf','threecols_update':{'notes':856,'relocated_prose_rows':42,'columns':3,'font':'FandolKai-Regular','font_pt':11.5,'wide_equations_unscaled':len(J(Q/'wide_math.json')),'no_additional_pages':True,'current_qa':'threecols_update/qa.json'}})
    W(Q/'baseline_release.json',old);W(R/'detailed_layout/current_release.json',rel);W(R/'answer_page_map.json',rel['mapping']);W(Q/'layout_plan.json',pageplans)
    print('PDF_READY',SHA(out),'growing pages',sum(bool(p['seams'])for p in pageplans),flush=True)

if __name__=='__main__':
    if len(sys.argv)<2 or sys.argv[1]=='compile':compile_notes()
    elif sys.argv[1]=='patch':patch_pdf()
