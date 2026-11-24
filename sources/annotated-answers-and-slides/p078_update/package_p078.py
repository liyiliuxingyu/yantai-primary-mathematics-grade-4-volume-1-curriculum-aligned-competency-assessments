"""Package the frozen page-78 original-question correction. Run only after root READY."""
from pathlib import Path
import json, hashlib, shutil, zipfile, re

R = Path(__file__).resolve().parent
P, Q, O, S = R/'project', R/'project/p078_update', R/'deliverables', R/'source_p078_project'
INDEX_NAMES = ['全套题目与课件对应索引答案.csv', '口算逐式与课件对应索引答案.csv']
MEDIA = {'.pdf','.png','.svg','.jpg','.jpeg','.webp'}
FORMULA = {'formula','formulas','assets','math_assets','simplify_assets','recheck_assets','preserved_glyphs','average_assets','bracket_assets','brackets_assets'}
SKIP = {'__pycache__','node_modules','previews','validated','extracted','recovered_final','recovery','portable','compiled'}

def J(p): return json.loads(Path(p).read_text())
def W(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
def SHA(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()
def cp(a,b):
    b=Path(b); b.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(a,b)
def evidence(value):
    p=Path(value)
    for x in ([p] if p.is_absolute() else [P/p,R/p]):
        if x.is_file(): return x
    raise FileNotFoundError(value)
def proof(qa,key,default):
    p=evidence(qa.get(key,default)); j=J(p); assert j.get('passed') is True,p
    return p,j
def allowed(f):
    rel=f.relative_to(P)
    if rel.as_posix()=='交付源码文件校验答案.json': return False
    if any(x in SKIP or x.startswith(('before_','after_','render_','rendered_','actual_','reference_')) for x in rel.parts): return False
    if f.suffix.lower() in {'.log','.aux','.xdv','.out','.tmp','.pptx','.pyc','.fmt','.fls','.fdb_latexmk'} or f.name.endswith('.synctex.gz'): return False
    if rel.parts[:2]==('detailed_layout','runs'): return f.suffix.lower() in {'.tex','.json'}
    if f.suffix.lower() in MEDIA: return bool(set(rel.parts)&FORMULA) and f.stat().st_size<5*1024*1024
    return True
def approved_keys():
    d=J(R/'approved_changes.json')
    if isinstance(d,list): rows=d
    elif 'changes' in d: rows=d['changes']
    elif 'changed_keys' in d: return set(d['changed_keys'])
    elif 'changed_question_keys' in d: return set(d['changed_question_keys'])
    else: raise ValueError('approved_changes.json needs a changes list or changed_keys list')
    return {x if isinstance(x,str) else x['key'] for x in rows}
def source_scope(white):
    approved=J(R/'approved_changes.json');changes={x['key']:x for x in approved['changes']}
    assert approved==J(Q/'approved_changes.json')
    assert white==set(changes)=={'p078_s01','p078_s05','p078_s06'}
    oldzip=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip';cr=[];cn=[];nrec=0
    with zipfile.ZipFile(oldzip) as z:
        for name in sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json',n)):
            a=json.loads(z.read(name));b=J(P/name);assert len(a['records'])==len(b['records'])
            top_a={k:v for k,v in a.items() if k!='records'};top_b={k:v for k,v in b.items() if k!='records'}
            if a['book_page']==78:
                for heading_key in ['section_heading','section_heading_latex']:
                    if heading_key in top_b:assert top_b[heading_key]==approved['section_heading']
                    top_a.pop(heading_key,None);top_b.pop(heading_key,None)
            assert top_a==top_b,name
            for x,y in zip(a['records'],b['records']):
                nrec+=1;assert x['key']==y['key']
                if x==y:continue
                key=x['key'];assert key in white,key;cr.append(key)
                assert x==changes[key]['old_record'],key
                assert y==changes[key]['new_record'],key
        for L in 'ABCD':
            name=f'detailed_layout/notes_{L}.json';a=json.loads(z.read(name));b=J(P/name)
            assert len(a['records'])==len(b['records'])
            assert {k:v for k,v in a.items() if k!='records'}=={k:v for k,v in b.items() if k!='records'}
            for x,y in zip(a['records'],b['records']):
                assert x['key']==y['key']
                if x==y:continue
                key=x['key'];assert key in white,key;cn.append(key)
                assert x['latex']==changes[key]['old_note_latex'],key
                assert y['latex']==changes[key]['final_note_latex'],key
                assert {k:v for k,v in x.items() if k not in {'latex','reason','local_replacements','original_replacements'}}=={k:v for k,v in y.items() if k not in {'latex','reason','local_replacements','original_replacements'}},key
        for L in 'ABCD':
            name=f'inline_layout/slots_{L}.json';assert J(P/name)==json.loads(z.read(name)),name
    assert nrec==867 and set(cr)==white and set(cn)==white
    return {'passed':True,'records':nrec,'approved_keys':sorted(white),'changed_question_keys':cr,'changed_note_keys':cn,'unchanged_records':nrec-len(cr),'the_3_authorized_records_exactly_match_new_photo_approved_changes':True,'all_other_864_records_and_all_slots_preserved':True,'question4_wording_and_ambiguity_preserved':True}
def source_evidence():
    approved=J(R/'approved_changes.json');photo=P/approved['source_photo'];tikz=P/approved['diagram_source'];svg=P/approved['diagram_svg']
    assert SHA(photo)==approved['source_photo_sha256']
    record=next(c['new_record'] for c in approved['changes'] if c['key']=='p078_s05')
    normalize=lambda t:'\n'.join(line.split('%',1)[0].rstrip() for line in t.splitlines()).strip()
    assert normalize(tikz.read_text())==normalize(record['diagrams'][0]['tikz'])
    assert len(re.findall(r'\\fill\s*\([^\n]+?\)\s*circle',tikz.read_text()))==16
    assert re.search(r'\\foreach\s+\\y\s+in\s+\{0,1,2,3,4\}',tikz.read_text())
    assert '<svg' in svg.read_text() and '<image' not in svg.read_text()
    font=P/'fonts/DroidSansFallback.ttf';assert font.is_file()
    return {'passed':True,'approved_changes_sha256':SHA(R/'approved_changes.json'),'source_photo':str(photo.relative_to(P)),'source_photo_sha256':SHA(photo),'tikz_matches_authorized_record':True,'circles':16,'horizontal_boundaries':5,'svg_embedded_bitmap_images':0,'evidence_files':[{'file':str(x.relative_to(P)),'bytes':x.stat().st_size,'sha256':SHA(x)} for x in [photo,tikz,svg,font]]}
def checked_zip(dest,members):
    names=[n for _,n in members];assert len(names)==len(set(names))
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,name in members:
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            z.write(p,name)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None and len(z.infolist())==len(members)
        for p,name in members: assert hashlib.sha256(z.read(name)).hexdigest()==SHA(p),name
        assert all(i.flag_bits&0x800 for i in z.infolist() if any(ord(c)>127 for c in i.filename))
    return {'file':dest.name,'bytes':dest.stat().st_size,'sha256':SHA(dest),'members':len(members),'crc_checked':True,'member_sha256_checked':True,'chinese_filenames_utf8_checked':True}
def main():
    assert (R/'READY_TO_PACKAGE').is_file(),'Root READY gate absent'
    assert not S.exists(),'Use a fresh source_p078_project stage'
    white=approved_keys();assert white
    qa=J(Q/'qa_current.json');assert qa.get('passed') is True
    rel=J(P/'detailed_layout/current_release.json');pdf=O/'小学同步素养四年级上册数学答案.pdf';h=SHA(pdf)
    assert h==qa['pdf_sha256']==rel['sha256']
    assert rel['pages']==128 and rel['question_pages']==108 and rel['record_coverage']==867 and rel['separate_analysis_pages']==0
    import fitz
    with fitz.open(pdf) as d:
        assert len(d)==128 and not d[0].get_text() and not d[0].get_images() and not d[0].get_drawings()
    scope=source_scope(white);asset_proof=source_evidence()
    scope_path,scopeqa=proof(qa,'scope_qa','p078_update/qa_scope.json');assert scopeqa['pdf_sha256']==h
    black_path,blackqa=proof(qa,'black_source_qa','p078_update/qa_black_source_rows.json');assert blackqa['pdf_sha256']==h
    black_count=len(J(Q/'source_masks.json')['masks']);assert black_count==5
    assert blackqa['old_source_paint_excluded']==blackqa['new_black_corrected_local_calls_retained']==black_count
    recovery_path,recovery=proof(qa,'recovery_qa','p078_update/qa_recovery.json');assert recovery['answer_sha256']==h
    local_count=len(rel['local_replacements']);assert recovery['local_patches_retained']==local_count
    old_source_masks=J(P/'average_update/source_masks.json')['masks']
    source_masks=rel['source_masks']
    assert all(x in source_masks for x in old_source_masks)
    assert recovery['source_answer_exclusions_retained']==len(source_masks)
    portable_path,portable=proof(qa,'portability_qa','p078_update/qa_portability.json')
    assert portable.get('relative_font_path') and portable.get('missing_characters',0) in [0,[]] and portable.get('overfull_hbox',0) in [0,[]] and portable.get('overfull_vbox',0) in [0,[]]
    texpath=evidence(rel['compiled_tex']);compiled=evidence(rel['compiled_pdf']);idxpath=compiled.parent/'snippet_index.json';idx=J(idxpath)
    assert len(idx)==portable['snippets']
    tex=texpath.read_text().replace(str(P/'recovered/source/new_work'),'recovered/source/new_work')
    assert hashlib.sha256(tex.encode()).hexdigest()==portable['portable_tex_sha256']
    # The immediately preceding correction must survive this broader update.
    assert '(720\\times2)\\div(12+8)' in idx['p075_s03']['body']
    inv=J(P/'ppt_builder/current_inventory.json');decks={};changed_volumes=[]
    for v in inv['volumes']:
        n=int(v['volume']);f=O/'讲解课件'/v['pptx'];assert SHA(f)==v['sha256'];decks[n]=f
        if SHA(f)!=SHA(R/'bundle/讲解课件'/f.name):changed_volumes.append(n)
        with zipfile.ZipFile(f) as z:
            assert z.testzip() is None
            assert len([x for x in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',x)])==v['slides']
    assert sorted(decks)==list(range(1,7)) and changed_volumes==[5]
    paths=qa.get('ppt_qa_paths',qa.get('ppt_qa',['ppt_p078/qa_final.json']))
    paths=[paths] if isinstance(paths,str) else paths;pptproof=[];proved_volumes=set()
    for value in paths:
        path=evidence(value);j=J(path);assert j.get('passed') is True
        assert not j.get('native_powerpoint_playback_tested',j.get('powerpoint_playback_tested',False))
        vs=[]
        for v in j['volumes']:
            n=int(v['volume']); assert v['output_sha256']==SHA(decks[n]);vs.append(n);proved_volumes.add(n)
        relpath=path.relative_to(P) if path.is_relative_to(P) else path.relative_to(R)
        pptproof.append({'path':str(relpath),'sha256':SHA(path),'volumes':vs})
    assert set(changed_volumes)<=proved_volumes
    files=[f for f in sorted(P.rglob('*')) if f.is_file() and allowed(f)]
    before={str(f.relative_to(P)):SHA(f) for f in files};S.mkdir()
    for f in files: cp(f,S/f.relative_to(P))
    cp(P/'fonts/DroidSansFallback.ttf',S/'p078_update/assets/fonts/DroidSansFallback.ttf')
    for name in ['版本记录答案.json','交付与使用说明答案.txt','源码使用说明答案.txt']:
        if (S/name).exists():cp(S/name,S/'checks/history/20261106_before_p078'/name)
    for f in R.glob('*.py'):cp(f,S/'p078_update'/f.name)
    for f in [R/'approved_changes.json',R/'diagram_review.json']+[x for x in R.glob('audit_*.json')]:cp(f,S/'p078_update'/f.name)
    if (R/'diagram_read/build_diagram.py').is_file():cp(R/'diagram_read/build_diagram.py',S/'p078_update/diagram_read/build_diagram.py')
    cp(idxpath,S/'detailed_layout/snippet_index.json');(S/'latex/详细题内答案.tex').write_text(tex)
    for path in [scope_path,black_path,recovery_path,portable_path,Q/'qa_current.json']:cp(path,S/path.relative_to(P))
    for item in pptproof:cp(evidence(item['path']),S/item['path'])
    for name in INDEX_NAMES:
        if not (O/name).exists():cp(R/'bundle'/name,O/name)
        cp(O/name,S/name)
    W(S/'p078_update/package_source_scope.json',scope)
    W(S/'p078_update/package_source_evidence.json',asset_proof)
    books=sorted({int(k[1:4]) for k in white})
    extra_fix=''
    W(S/'版本记录答案.json',{'date':'2026-11-06','previous_pdf_sha256':rel['previous_pdf_sha256'],'current_pdf_sha256':h,'changed_question_keys':sorted(white),'changed_book_pages':[78],'change':'根据清晰原卷更正第78页：每题2分共12分；海盗船平均136厘米与140厘米限制；气温图重绘16圆点和5条横线；快板更正为秧歌。原第4题B、D措辞歧义保留。','current_evidence':'p078_update/qa_current.json','source_photo_sha256':J(R/'approved_changes.json')['source_photo_sha256'],'ppt_proofs':pptproof,'powerpoint_playback_tested':False})
    readme=('本版PDF共128页，第一页空白，答案及解析继续写在题内，无新增PDF续页。\n'
      '本次按清晰原卷更正原书第78页（PDF第82页）：选择题总分12分；海盗船平均136厘米、限制140厘米，仍选C；气温图按原图重绘16圆点、5条横线和22摄氏度竖虚线，仍选B；第6题活动名称改为秧歌，仍选A。\n'
      '第4题原卷B、D文字存在单选歧义，继续保留原文及提示，不擅自改题。\n'
      '当前检查入口为源码包p078_update/qa_current.json。本轮检查覆盖第78页及第5册相关幻灯片的实际静态渲染；动画结构核对，未在PowerPoint/WPS中实际放映。其他127个PDF页与另5册保持原版。此前bracket_update、average_update等记录为历史。\n'
      '前版第74页第4题原图平均15千克与书后A冲突的提示继续保留；本轮未改动该题的原始数据及按题面填写的C。\n'
      '长页整页缩印到单张A4时文字会变小。原书91页原扫描页脚模糊，按连续页序及题号索引定位。\n')
    (O/'交付与使用说明答案.txt').write_text(readme);(S/'交付与使用说明答案.txt').write_text(readme)
    (S/'源码使用说明答案.txt').write_text('当前入口：p078_update/qa_current.json。活动题源为questions，题内解析为detailed_layout/notes_A到D，当前课件哈希为ppt_builder/current_inventory.json。\n'
      f'latex/详细题内答案.tex含{len(idx)}个实际编译片段，含{local_count}个局部替换，使用相对字体路径。项目根目录编译：\n  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex\n'
      '从当前交付PDF恢复与重建：\n  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf\n  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf\n'
      '本次补丁与QA在p078_update，清晰原照、新TikZ和SVG在p078_update/assets，绘图坐标只用于忠实恢复照片相对位置，并非各点具体温度。课件源在ppt_p078。历史记录保留供追溯，活动源已应用更正，不应盲目重跑一次性旧补丁。重新组合图层可能有抗锯齿差异，不承诺重建文件字节或像素相同。Python需要PyMuPDF/NumPy，公式需要XeLaTeX。\n')
    assert before=={str(f.relative_to(P)):SHA(f) for f in files},'Source changed during packaging'
    inventory=[{'file':str(f.relative_to(S)),'bytes':f.stat().st_size,'sha256':SHA(f)} for f in sorted(S.rglob('*')) if f.is_file()]
    W(S/'交付源码文件校验答案.json',{'files':inventory})
    source=O/'小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    sm=checked_zip(source,[(f,str(f.relative_to(S))) for f in sorted(S.rglob('*')) if f.is_file()])
    full=O/'小学四上同步素养卷全套答案.zip'
    basic=[pdf]+[O/n for n in INDEX_NAMES]+[O/'交付与使用说明答案.txt',source]
    om=checked_zip(full,[(f,f.name) for f in basic]+[(decks[n],'讲解课件/'+decks[n].name) for n in sorted(decks)])
    assert om['members']==11
    approved=J(R/'approved_changes.json')
    report={'pdf':{'file':pdf.name,'sha256':h,'bytes':pdf.stat().st_size},'source_zip':sm,'overall_zip':om,'pages':128,'records':867,'changed_question_keys':sorted(white),'source_photo_sha256':approved['source_photo_sha256'],'compiled_snippets':len(idx),'local_patches':local_count,'source_answer_exclusions':len(source_masks),'ppt_changed_volumes':changed_volumes,'powerpoint_playback_tested':False,'pptx':[{'volume':n,'file':f.name,'sha256':SHA(f),'bytes':f.stat().st_size} for n,f in sorted(decks.items())]}
    W(O/'delivery_manifest.json',report);W(R/'package_result.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
