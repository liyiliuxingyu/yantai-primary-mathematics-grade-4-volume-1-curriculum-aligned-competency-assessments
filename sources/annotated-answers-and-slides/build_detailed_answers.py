"""Detailed, non-repeating explanations within original question pages."""
from pathlib import Path
import argparse,json,hashlib,re,subprocess,math,os
import fitz,numpy as np
from answer_content import load_pages,aligned

R=Path(__file__).resolve().parent;C=R/'detailed_layout'
FONT=R/'fonts/DroidSansFallback.ttf'
J=lambda p:json.loads(p.read_text())
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
RED=(205/255,20/255,35/255)

def load_data():
    records={s['record']['key']:s['record']for p in load_pages()for s in p['sections']}
    notes={};snapshots={}
    for L in 'ABCD':
        path=C/f'notes_{L}.json';d=J(path);snapshots[str(path.relative_to(R))]=SHA(path)
        for n in d['records']:
            assert n['key']in records and n['key']not in notes
            notes[n['key']]=n
    assert set(notes)==set(records)and len(notes)==867
    slots={}
    for L in 'ABCD':
        path=R/f'inline_layout/slots_{L}.json';d=J(path);snapshots[str(path.relative_to(R))]=SHA(path)
        for p in d['pages']if isinstance(d,dict)else d:slots[p['book_page']]=p['slots']
    assert set(slots)==set(range(1,109))
    # These verified red-only source regions are deliberately omitted when the
    # complete replacement solution is typeset once in the adjacent question gap.
    for mask_path in [R/'average_update/source_masks.json',R/'average_update/layout_reuse.json',R/'bracket_update/source_masks.json',R/'p078_update/source_masks.json',R/'units_update/source_masks.json',R/'units_update/layout_reuse.json']:
        if mask_path.exists():snapshots[str(mask_path.relative_to(R))]=SHA(mask_path)
    return records,notes,slots,snapshots

def apply_source_answer_exclusions(base,path=None):
    """Retain original black problem content and clip only obsolete red answers.

    This is idempotent when the input is a recovered current publication, whose
    A4 Forms already retain the same exclusion clips. It also supports rebuilding
    from a pre-update annotated A4 input.
    """
    path=path or R/'average_update/source_masks.json'
    if not path.exists():return
    by_book={}
    for item in J(path)['masks']:by_book.setdefault(item['book_page'],[]).append(item)
    for book,items in by_book.items():
        page=base[book+3];content=page.read_contents()
        for item in items:
            x0,y0,x1,y1=item['rect']
            hole=f'{x0:.6f} {841-y1:.6f} {x1-x0:.6f} {y1-y0:.6f} re'.encode()
            content=b'q\n0 0 595 841 re\n'+hole+b'\nW* n\n'+content+b'\nQ\n'
        xref=base.get_new_xref();base.update_object(xref,'<<>>')
        base.update_stream(xref,b'% Average answer source exclusions\n'+content);page.set_contents(xref)

def snippets(records,notes,slots):
    out=[];locals=[]
    labels={}
    for book,ss in slots.items():
        for s in ss:
            nonempty=[k for k in s['keys']if notes[k]['latex'].strip()]
            for k in nonempty:labels[k]=len(nonempty)>1
    for k,n in notes.items():
        body=n['latex'].strip()
        prose_path=R/'threecols_update/original_prose.json'
        extras=[x['visible_text'] for x in J(prose_path)['records'] if x['key']==k] if prose_path.exists() else []
        if extras:
            extra_text=' '.join(extras).replace('∠',r'\ensuremath{\angle}').replace('−',r'\ensuremath{-}').replace('◦',r'\ensuremath{^\circ}')
            body=extra_text+r'\par '+body
        if body:
            prefix=(r'\textbf{'+records[k]['id']+r'：}\ 'if labels[k]else'')
            for name in n.get('extra_figures',[]):
                g=next(g for g in records[k].get('diagrams',[])if g['name']==name)
                body+=r'\par\begin{center}\sbox0{'+g['tikz']+r'}\ifdim\wd0>300bp\resizebox{300bp}{!}{\usebox0}\else\usebox0\fi\end{center}'
            out.append({'id':k,'key':k,'book_page':records[k]['book_page'],'body':prefix+aligned(body),'font':11.5,'leading':14,'width':505,'kind':'note'})
        patches=n.get('local_replacements',n.get('original_replacements',[]))
        for i,p in enumerate(patches):
            p=dict(p);p.update({'id':f'{k}_local{i+1}','key':k,'book_page':records[k]['book_page']})
            target=p.get('target_rect',p['rect'])
            if k=='p078_s04':target=[326,476,349,490.5];p['target_rect']=target;p['align']='center';p['font_size']=11.5
            out.append({'id':p['id'],'key':k,'book_page':p['book_page'],'body':aligned(p['latex']),'font':p.get('font_size',10.5),'leading':p.get('leading',12.8),'width':p.get('snippet_width',target[2]-target[0]-1),'kind':'local'})
            locals.append(p)
    return out,locals

def compile_fragments(items,out):
    # The approved typeset bodies retain balanced Kai columns and unscaled
    # equations. Never silently fall back to the historical single-column text.
    from threecols_update.build_threecols import PRE
    approved=J(R/'threecols_update/compiled/snippet_index.json')
    pre=PRE.replace(r'\begin{document}',r'''\newfontfamily\SourceSans[Path=fonts/,AutoFakeBold=1.2]{DroidSansFallback.ttf}
\begin{document}''')
    rendered=[]
    for n in items:
        if n['kind']=='note':
            assert n['id']in approved,('Missing approved three-column note',n['id'])
            entry=approved[n['id']]
            assert entry['body']==n['body'],('Recompile approved three-column source after editing note',n['id'])
            assert entry.get('typeset_body'),('Missing approved typeset body',n['id'])
            body=entry['typeset_body']
        else:
            body=r'\SourceSans\setlength{\mathindent}{2bp}'+re.sub(r'(\\[A-Za-z]+)(?=[\u3400-\u9fff])',r'\1 ',n['body'])
        rendered.append('% '+n['id']+'\n'+r'\begin{snippet}{'+str(n['width'])+'}{'+str(n['font'])+'}{'+str(n['leading'])+'}'+body+r'\end{snippet}')
    out.mkdir(parents=True,exist_ok=True)
    tex=out/'详细题内答案.tex';tex.write_text(pre+'\n'.join(rendered)+r'\end{document}')
    p=subprocess.run([os.environ.get('XELATEX','xelatex'),'-interaction=nonstopmode','-halt-on-error','-output-directory',str(out),str(tex)],cwd=R,capture_output=True,text=True)
    (out/'compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout[-5000:]
    assert 'Missing character:'not in p.stdout
    doc=fitz.open(tex.with_suffix('.pdf'));assert len(doc)==len(items)
    index={}
    for i,(n,page)in enumerate(zip(items,doc)):
        pix=page.get_pixmap(matrix=fitz.Matrix(3,3),alpha=True);a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,4);y,x=np.where(a[:,:,3]>0);assert len(x)
        clip=fitz.Rect(max(0,(x.min()-.5)/3),max(0,(y.min()-.5)/3),min(page.rect.width,(x.max()+1.5)/3),min(page.rect.height,(y.max()+1.5)/3))
        spans=[s for b in page.get_text('dict')['blocks']for line in b.get('lines',[])for s in line['spans']if s['text'].strip()]
        eq=[s for s in spans if s['text'].startswith('=')]
        index[n['id']]={**n,'page':i+1,'clip':list(clip),'ink_width':clip.width,'ink_height':clip.height,
                        **({'first_text_origin':list(spans[0]['origin'])}if spans else{}),
                        **({'first_equals_origin':list(eq[0]['origin'])}if eq else{})}
    (out/'snippet_index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2));return doc,index,tex

def make_pure(source):
    pure=fitz.open();images=[]
    for i,p in enumerate(source):
        q=pure.new_page(width=595,height=841)
        for info in p.get_images(full=True):
            raw=source.extract_image(info[0])['image'];h=hashlib.sha256(raw).hexdigest()
            for rect in p.get_image_rects(info[0]):
                if not rect.intersects(p.rect):continue
                q.insert_image(rect,stream=raw,keep_proportion=False)
                images.append({'base_page':i+1,'sha256':h,'rect':list(rect)})
    return pure,images

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run-name',default='draft');ap.add_argument('--books',type=int,nargs='+');ap.add_argument('--publish',action='store_true');ap.add_argument('--pure-source',type=Path);ap.add_argument('--input',type=Path,default=R/'recovered/annotated_a4_128.pdf');a=ap.parse_args()
    out=C/'runs'/a.run_name;out.mkdir(parents=True,exist_ok=True)
    records,notes,slots,snapshots=load_data();items,locals=snippets(records,notes,slots);compiled,index,tex=compile_fragments(items,out)
    source=fitz.open(a.input);assert len(source)==128;pure,original_images=make_pure(fitz.open(a.pure_source)if a.pure_source else source)
    if a.publish:original_images=[x for x in original_images if x['base_page']!=1]
    base=fitz.open();base.insert_pdf(source)
    # Remove outdated pointers and duplicate written originals, retaining the
    # original problem text and existing answers/diagrams at their positions.
    masks=J(R/'inline_layout/pointer_masks.json')['masks'];dups=J(C/'duplicate_formula_masks.json')['items'];legacy=J(C/'legacy_note_cleanup.json')['masks']
    headings=[]
    for L in 'ABCD':
        dd=J(R/f'inline_layout/slots_{L}.json')
        for pp in dd['pages']if isinstance(dd,dict)else dd:
            for h in pp.get('heading_relocations',[]):headings.append({**h,'book_page':pp['book_page']})
    heading_by={(h['book_page'],h['cut_y']):h for h in headings}
    overrides={x['book_page']:x for x in J(C/'footer_overrides.json')['overrides']}
    for m in masks+dups+legacy:
        p=base[m['book_page']+3];r=fitz.Rect(m['rect']);p.show_pdf_page(r,pure,m['book_page']+3,clip=r,keep_proportion=False)
    # Retain the original red row's baseline when a bracket-only correction is
    # grafted into its exact source position. Clip obsolete rows before painting
    # the replacement, so a future rebuild never clips its new formula.
    apply_source_answer_exclusions(base,R/'bracket_update/source_masks.json')
    apply_source_answer_exclusions(base,R/'p078_update/source_masks.json')
    apply_source_answer_exclusions(base,R/'units_update/source_masks.json')
    apply_source_answer_exclusions(base,R/'vertical_update/source_masks.json')
    previous_patches={p['id']:p for p in J(C/'base_local_targets.json')['patches']}
    patch_targets=[];fail=[]
    for p in locals:
        page=base[p['book_page']+3];r=fitz.Rect(p['rect'])
        previous=previous_patches.get(p['id'])
        if previous:r|=fitz.Rect(previous['target_rect']);p['previous_target_rect']=previous['target_rect']
        p['restore_rect']=list(r)
        if p.get('clear_to_white'):page.draw_rect(r,fill=(1,1,1),color=None)
        else:page.show_pdf_page(r,pure,p['book_page']+3,clip=r,keep_proportion=False)
        box=fitz.Rect(p.get('target_rect',p['rect']));e=index[p['id']];w=e['ink_width'];h=e['ink_height']
        if p.get('fit_to_rect'):
            # A verified source correction fits the original glyph or graphic
            # ink rectangle; its surrounding question text is never reflowed.
            target=box;page.show_pdf_page(target,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
            patch_targets.append({**p,'target_rect':list(target)});continue
        if w>box.width-.8 or h>box.height-.8:
            fail.append({'key':p['key'],'id':p['id'],'rect':list(box),'ink':[w,h]});continue
        x=box.x0+.4 if p.get('align')!='center'else box.x0+(box.width-w)/2
        yy=box.y0+(box.height-h)/2 if p.get('valign')=='center'else box.y0+.4
        if 'baseline_anchor'in p:
            anchor=e['first_equals_origin'];clip=e['clip']
            x=p['baseline_anchor'][0]-(anchor[0]-clip[0]);yy=p['baseline_anchor'][1]-(anchor[1]-clip[1])
        if 'text_baseline_anchor'in p:
            anchor=e['first_text_origin'];clip=e['clip']
            x=p['text_baseline_anchor'][0]-(anchor[0]-clip[0]);yy=p['text_baseline_anchor'][1]-(anchor[1]-clip[1])
        target=fitz.Rect(x,yy,x+w,yy+h);page.show_pdf_page(target,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
        patch_targets.append({**p,'target_rect':list(target)})
    (out/'local_fit_report.json').write_text(json.dumps({'failed':fail,'placed':patch_targets},ensure_ascii=False,indent=2))
    assert not fail,'Local replacements need layout adjustment: '+str(fail)
    apply_source_answer_exclusions(base,R/'threecols_update/source_masks.json')
    heading_source=fitz.open();heading_source.insert_pdf(base)
    for h in headings:base[h['book_page']+3].draw_rect(fitz.Rect(h['rect']),fill=(1,1,1),color=None)
    footers=J(R/'inline_layout/footer_crops.json')['crops'];footer_by={x['book_page']:x for x in footers}
    footer_source=fitz.open();footer_source.insert_pdf(base)
    for f in footers:base[f['book_page']+3].show_pdf_page(fitz.Rect(f['rect']),pure,f['book_page']+3,clip=fitz.Rect(f['rect']),keep_proportion=False)
    # The background scan contains the old page number too: cover only its tight
    # glyph crop after making a source for the relocation.
    for f in footers:base[f['book_page']+3].draw_rect(fitz.Rect(f['rect']),fill=(1,1,1),color=None)
    apply_source_answer_exclusions(base)
    cleanpath=out/'cleaned_a4.pdf';base.save(cleanpath,garbage=3,deflate=True)
    if cleanpath.stat().st_size==0:cleanpath.write_bytes(base.tobytes(garbage=3,deflate=True))
    assert cleanpath.stat().st_size>1000000
    reuse_path=R/'average_update/layout_reuse.json'
    reuse_anchors={x['key']:x['source_y']for x in J(reuse_path)['anchors']}if reuse_path.exists()else{}
    units_reuse_path=R/'units_update/layout_reuse.json'
    if units_reuse_path.exists():reuse_anchors.update({x['key']:x['source_y']for x in J(units_reuse_path)['anchors']})
    books=sorted(a.books or slots);result=fitz.open();maps=[];bands=[];answers=[];moved=[];moved_headings=[]
    if a.publish:
        assert books==list(range(1,109));result.new_page(width=595,height=841)
        result.insert_pdf(source,from_page=1,to_page=3)
    for book in books:
        qs=sorted(slots[book],key=lambda x:x['cut_y']);parts=[];prev=0
        pix=base[book+3].get_pixmap(matrix=fitz.Matrix(2,2));rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3);rows=(rgb[:,156:1170,:].min(axis=2)<235).any(axis=1)
        for s in qs:
            visible=[k for k in s['keys']if k in index];raw=sum(index[k]['ink_height']+4 for k in visible)+4 if visible else 0
            if(book,s['cut_y'])in heading_by:raw+=fitz.Rect(heading_by[(book,s['cut_y'])]['rect']).height+8
            end=min(len(rows),math.floor(s['cut_y']*2));start=end
            while start>math.ceil(prev*2)and not rows[start-1]:start-=1
            reuse=min(raw,max(0,(end-start)/2-2))
            # Verified original answer-only whitespace can be reused even when
            # a decorative binding line crosses the far-right page margin.
            if visible and visible[0]in reuse_anchors:
                reuse=max(reuse,min(raw,max(0,s['cut_y']-reuse_anchors[visible[0]]+2)))
            extra=math.ceil(raw-reuse);parts.append((s,visible,raw,reuse,extra));prev=s['cut_y']
        baseh=841+sum(x[4]for x in parts);last=max((s['cut_y']+sum(x[4]for x in parts[:i+1])-5 for i,(s,v,_,_,_)in enumerate(parts)if v),default=780+baseh-841)
        f=fitz.Rect(footer_by[book]['rect']);fy=max(baseh-38,last+10);height=max(baseh,math.ceil(fy+f.height+18));page=result.new_page(width=595,height=height);pn=len(result);offset=0;prev=0
        for s,visible,raw,reuse,extra in parts:
            cut=s['cut_y'];sr=fitz.Rect(0,prev,595,cut);tr=sr+(0,offset,0,offset)
            page.show_pdf_page(tr,base,book+3,clip=sr,keep_proportion=False);bands.append({'book_page':book,'pdf_page':pn,'source_rect':list(sr),'target_rect':list(tr)})
            y=cut+offset-reuse+2
            for k in visible:
                e=index[k];t=fitz.Rect(78,y,78+e['ink_width'],y+e['ink_height']);page.show_pdf_page(t,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
                answers.append({'key':k,'book_page':book,'pdf_page':pn,'target_rect':list(t),'source_cut_y':cut});y+=e['ink_height']+4
            if(book,cut)in heading_by:
                hh=heading_by[(book,cut)];hr=fitz.Rect(hh['rect']);ht=fitz.Rect(hr.x0,y+2,hr.x1,y+2+hr.height)
                page.show_pdf_page(ht,heading_source,book+3,clip=hr,keep_proportion=False)
                moved_headings.append({**hh,'pdf_page':pn,'source_rect':list(hr),'target_rect':list(ht)})
            offset+=extra;prev=cut
        sr=fitz.Rect(0,prev,595,841);tr=sr+(0,offset,0,offset);page.show_pdf_page(tr,base,book+3,clip=sr,keep_proportion=False);bands.append({'book_page':book,'pdf_page':pn,'source_rect':list(sr),'target_rect':list(tr)})
        ft=fitz.Rect(f.x0,fy,f.x1,fy+f.height);
        if book in overrides:
            label='• '+overrides[book]['label']+' •';page.insert_font(fontname='CorrectFooter',fontfile=str(FONT));fw=fitz.Font(fontfile=str(FONT)).text_length(label,fontsize=9);page.insert_text(((f.x0+f.x1-fw)/2,fy+9),label,fontname='CorrectFooter',fontsize=9,color=(0,0,0))
            ss=[sp for bl in page.get_text('dict')['blocks']for ln in bl.get('lines',[])for sp in ln['spans']if sp['text']==label];assert len(ss)==1;ft=fitz.Rect(ss[0]['bbox'])+(-.1,-.1,.1,.1)
        else:page.show_pdf_page(ft,footer_source,book+3,clip=f,keep_proportion=False)
        moved.append({'book_page':book,'pdf_page':pn,'source_rect':list(f),'target_rect':list(ft)})
        keys=[k for s in qs for k in s['keys']];maps.append({'book_page':book,'source_pdf_page':book+4,'input_pdf_page':J(R/'recovered/source/source_page_map.json')[str(book+4)]+1,'answer_pdf_page':pn,'analysis_pdf_pages':[],'record_pdf_pages':{k:[pn]for k in keys},'sections':[records[k]['id']for k in keys],'page_size':[595,height],'layout':'Detailed explanations and distinct additional methods within original question pages.'})
    if a.publish:
        result.insert_pdf(source,from_page=112,to_page=127)
        for i in range(len(result)-16,len(result)-4):
            p=result[i];p.draw_rect(fitz.Rect(35,823,590,841),fill=(1,1,1),color=None);p.insert_font(fontname='ConciseCJK',fontfile=str(FONT));p.insert_text((35,833),'原书参考答案影印；以本次题内红笔作答及条件说明为准。',fontsize=7.2,fontname='ConciseCJK',color=RED)
        result.set_toc([[1,'原书第%d页'%m['book_page'],m['answer_pdf_page']]for m in maps])
    result.set_metadata({'title':'小学同步素养四年级上册数学答案','subject':'详细题内答案，第一页空白','author':'数学教学资料'})
    path=out/'详细题内答案成品.pdf';result.save(path,garbage=3,deflate=True);result.close();doc=fitz.open(path);previews=out/'previews';previews.mkdir(exist_ok=True)
    for m in maps:doc[m['answer_pdf_page']-1].get_pixmap(matrix=fitz.Matrix(1,1)).save(previews/f'p{m["book_page"]:03}.png')
    report={'run_name':a.run_name,'pdf':str(path.resolve()),'sha256':SHA(path),'pages':len(doc),'question_pages':len(books),'record_coverage':867,'visible_note_blocks':len(answers),'local_replacements':patch_targets,'duplicate_formula_masks':dups,'pointer_masks':masks,'mapping':maps,'bands':bands,'answers':answers,'moved_footers':moved,'moved_headings':moved_headings,'legacy_note_cleanup':legacy,'footer_overrides':list(overrides.values()),'source_original_images':original_images,'source_files':snapshots,'compiled_tex':str(tex.resolve()),'compiled_pdf':str(tex.with_suffix('.pdf').resolve()),'cleaned_base_pdf':str(cleanpath.resolve()),'input_pdf':str(a.input.resolve()),'input_sha256':SHA(a.input),'note_font_pt':11.5,'local_math_font_pt':10.5,'first_page_blank':bool(a.publish),'extra_diagrams':sum(len(n.get('extra_figures',[]))for n in notes.values()),'separate_analysis_pages':0}
    source_exclusions=R/'average_update/source_masks.json'
    if source_exclusions.exists():report['source_masks']=J(source_exclusions)['masks']
    bracket_exclusions=R/'bracket_update/source_masks.json'
    if bracket_exclusions.exists():report['source_region_replacements']=J(bracket_exclusions)['masks']
    p78_exclusions=R/'p078_update/source_masks.json'
    if p78_exclusions.exists():report['source_region_replacements']=report.get('source_region_replacements',[])+J(p78_exclusions)['masks']
    (out/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if a.publish:
        assert len(doc)==128 and not doc[0].get_text() and not doc[0].get_images()
        dest=R/'deliverables/小学同步素养四年级上册数学答案.pdf';tmp=dest.with_suffix('.detailed.tmp.pdf');tmp.write_bytes(path.read_bytes());os.replace(tmp,dest);report['pdf']=str(dest.resolve());(C/'current_release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(R/'answer_page_map.json').write_text(json.dumps(maps,ensure_ascii=False,indent=2))
    print(json.dumps({k:report[k]for k in ['pages','record_coverage','visible_note_blocks','extra_diagrams','first_page_blank','sha256']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
