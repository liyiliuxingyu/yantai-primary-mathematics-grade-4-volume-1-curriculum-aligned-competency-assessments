"""Package the frozen page-78 question-4 answer correction. Run only after root READY."""
from pathlib import Path
import json, hashlib, shutil, zipfile, re

R = Path(__file__).resolve().parent
P, Q, O, S = R/'project', R/'project/q4_update', R/'deliverables', R/'source_q4_project'
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
    approved=J(R/'approved_changes.json');assert approved==J(Q/'approved_changes.json')
    changes={x['key']:x for x in approved['changes']};assert white==set(changes)=={'p078_s04'}
    oldzip=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip';cr=[];cn=[];nrec=0
    assert SHA(oldzip)==approved['baseline_source_zip_sha256']
    with zipfile.ZipFile(oldzip) as z:
        for name in sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json',n)):
            a=json.loads(z.read(name));b=J(P/name);assert len(a['records'])==len(b['records'])
            assert {k:v for k,v in a.items() if k!='records'}=={k:v for k,v in b.items() if k!='records'},name
            for x,y in zip(a['records'],b['records']):
                nrec+=1;assert x['key']==y['key']
                if x==y:continue
                key=x['key'];assert key in white,key;cr.append(key)
                assert x==changes[key]['old_record'] and y==changes[key]['new_record'],key
                assert {k:v for k,v in x.items() if k not in {'answer_latex','verification'}}=={k:v for k,v in y.items() if k not in {'answer_latex','verification'}},key
        for L in 'ABCD':
            name=f'detailed_layout/notes_{L}.json';a=json.loads(z.read(name));b=J(P/name)
            assert len(a['records'])==len(b['records'])
            assert {k:v for k,v in a.items() if k!='records'}=={k:v for k,v in b.items() if k!='records'}
            for x,y in zip(a['records'],b['records']):
                assert x['key']==y['key']
                if x==y:continue
                key=x['key'];assert key in white,key;cn.append(key)
                assert x==changes[key]['old_note'] and y==changes[key]['new_note'],key
        for L in 'ABCD':
            name=f'inline_layout/slots_{L}.json';assert J(P/name)==json.loads(z.read(name)),name
        # The five original-question repairs and their supporting assets survive unchanged.
        masks='p078_update/source_masks.json';assert J(P/masks)==json.loads(z.read(masks))
        assert len(J(P/masks)['masks'])==5
        preserved=[n for n in z.namelist() if n.startswith('p078_update/assets/') and not n.endswith('/')]
        assert preserved
        for name in preserved:assert hashlib.sha256(z.read(name)).hexdigest()==SHA(P/name),name
        oldrel=json.loads(z.read('detailed_layout/current_release.json'));newrel=J(P/'detailed_layout/current_release.json')
        oldpatch={x['id']:x for x in oldrel['local_replacements']};newpatch={x['id']:x for x in newrel['local_replacements']}
        assert set(oldpatch)==set(newpatch) and len(oldpatch)==92
        for key,x in oldpatch.items():
            if x['key']!='p078_s04':assert x==newpatch[key],key
    assert nrec==867 and cr==cn==['p078_s04']
    assert '因此选B' in changes['p078_s04']['new_record']['answer_latex']
    return {'passed':True,'records':nrec,'approved_keys':sorted(white),'changed_question_keys':cr,'changed_note_keys':cn,'unchanged_records':866,'all_original_question_wording_and_all_slots_preserved':True,'original_D_option_untouched':True,'answer_B_by_instructional_intent_without_assigning_specific_ages':True,'previous_5_black_repairs_and_assets_unchanged':True}
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
    assert not S.exists(),'Use a fresh source_q4_project stage'
    white=approved_keys();assert white
    qa=J(Q/'qa_current.json');assert qa.get('passed') is True
    rel=J(P/'detailed_layout/current_release.json');pdf=O/'小学同步素养四年级上册数学答案.pdf';h=SHA(pdf)
    assert h==qa['pdf_sha256']==rel['sha256']
    assert rel['pages']==128 and rel['question_pages']==108 and rel['record_coverage']==867 and rel['separate_analysis_pages']==0
    import fitz
    with fitz.open(pdf) as d:
        assert len(d)==128 and not d[0].get_text() and not d[0].get_images() and not d[0].get_drawings()
    scope=source_scope(white)
    scope_path,scopeqa=proof(qa,'scope_qa','q4_update/qa_scope.json');assert scopeqa['pdf_sha256']==h
    recovery_path,recovery=proof(qa,'recovery_qa','q4_update/qa_recovery.json');assert recovery['answer_sha256']==h
    local_count=len(rel['local_replacements']);assert recovery['local_patches_retained']==local_count
    old_source_masks=J(P/'average_update/source_masks.json')['masks']
    source_masks=rel['source_masks']
    assert all(x in source_masks for x in old_source_masks)
    assert recovery['source_answer_exclusions_retained']==len(source_masks)
    portable_path,portable=proof(qa,'portability_qa','q4_update/qa_portability.json')
    assert portable.get('relative_font_path') and portable.get('missing_characters',0) in [0,[]] and portable.get('overfull_hbox',0) in [0,[]] and portable.get('overfull_vbox',0) in [0,[]]
    texpath=evidence(rel['compiled_tex']);compiled=evidence(rel['compiled_pdf']);idxpath=compiled.parent/'snippet_index.json';idx=J(idxpath)
    assert len(idx)==portable['snippets']
    tex=texpath.read_text().replace(str(P/'recovered/source/new_work'),'recovered/source/new_work')
    assert hashlib.sha256(tex.encode()).hexdigest()==portable['portable_tex_sha256']
    # The immediately preceding correction must survive this broader update.
    assert '(720\\times2)\\div(12+8)' in idx['p075_s03']['body']
    assert r'\mathrm{B}' in idx['p078_s04_local1']['body']
    assert 'D' not in idx['p078_s04_local1']['body'] and 'D' not in idx['p078_s04']['body']
    inv=J(P/'ppt_builder/current_inventory.json');decks={};changed_volumes=[]
    for v in inv['volumes']:
        n=int(v['volume']);f=O/'讲解课件'/v['pptx'];assert SHA(f)==v['sha256'];decks[n]=f
        if SHA(f)!=SHA(R/'bundle/讲解课件'/f.name):changed_volumes.append(n)
        with zipfile.ZipFile(f) as z:
            assert z.testzip() is None
            assert len([x for x in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',x)])==v['slides']
    assert sorted(decks)==list(range(1,7)) and changed_volumes==[5]
    paths=qa.get('ppt_qa_paths',qa.get('ppt_qa',['ppt_q4/qa_final.json']))
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
    for name in ['版本记录答案.json','交付与使用说明答案.txt','源码使用说明答案.txt']:
        if (S/name).exists():cp(S/name,S/'checks/history/20261106_before_q4'/name)
    for f in R.glob('*.py'):cp(f,S/'q4_update'/f.name)
    for f in [R/'approved_changes.json']+[x for x in R.glob('audit_*.json')]:cp(f,S/'q4_update'/f.name)
    cp(idxpath,S/'detailed_layout/snippet_index.json');(S/'latex/详细题内答案.tex').write_text(tex)
    for path in [scope_path,recovery_path,portable_path,Q/'qa_current.json']:cp(path,S/path.relative_to(P))
    for item in pptproof:cp(evidence(item['path']),S/item['path'])
    for name in INDEX_NAMES:
        if not (O/name).exists():cp(R/'bundle'/name,O/name)
        cp(O/name,S/name)
    W(S/'q4_update/package_source_scope.json',scope)
    books=sorted({int(k[1:4]) for k in white})
    extra_fix=''
    W(S/'版本记录答案.json',{'date':'2026-11-06','previous_pdf_sha256':rel['previous_pdf_sha256'],'current_pdf_sha256':h,'changed_question_keys':['p078_s04'],'changed_book_pages':[78],'change':'第78页二、4按平均数数量关系的教学意图只选B，用移多补少说明丙的年龄等于平均年龄；不据此确定具体岁数，原题全部选项保留。','current_evidence':'q4_update/qa_current.json','ppt_proofs':pptproof,'powerpoint_playback_tested':False})
    readme=('本版PDF共128页，第一页空白，答案及解析继续写在题内，无新增PDF续页。\n'
      '本次只更正原书第78页二、4（PDF第82页）：按平均数数量关系的教学意图只选B。甲多出的6岁正好补给乙，两人都等于平均年龄，丙也必须等于平均年龄；题目未给出具体岁数。原题各选项文字全部保留。\n'
      '当前检查入口为源码包q4_update/qa_current.json。该题PDF版面与第5册相关幻灯片已作实际静态渲染核对；动画结构核对，未在PowerPoint/WPS中实际放映。其余127个PDF页、另外5册、原第78页的5处黑字与图形修复保持前版。此前p078_update、bracket_update、average_update等记录为历史。\n'
      '长页整页缩印到单张A4时文字会变小。原书91页原扫描页脚模糊，按连续页序及题号索引定位。\n')
    (O/'交付与使用说明答案.txt').write_text(readme);(S/'交付与使用说明答案.txt').write_text(readme)
    (S/'源码使用说明答案.txt').write_text('当前入口：q4_update/qa_current.json。活动题源为questions，题内解析为detailed_layout/notes_A到D，当前课件哈希为ppt_builder/current_inventory.json。\n'
      f'latex/详细题内答案.tex含{len(idx)}个实际编译片段，含{local_count}个局部替换，使用相对字体路径。项目根目录编译：\n  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex\n'
      '从当前交付PDF恢复与重建：\n  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf\n  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf\n'
      '本次补丁与QA在q4_update，当前答案只列B。第78页原照片、新TikZ、SVG和字体继续保存在p078_update/assets；课件源在ppt_q4，前版课件修复源也保留。历史记录供追溯，课堂作答以当前questions及notes为准，不应盲目重跑旧补丁。重新组合图层可能有抗锯齿差异，不承诺重建文件字节或像素相同。Python需要PyMuPDF/NumPy，公式需要XeLaTeX。\n')
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
    report={'pdf':{'file':pdf.name,'sha256':h,'bytes':pdf.stat().st_size},'source_zip':sm,'overall_zip':om,'pages':128,'records':867,'changed_question_keys':sorted(white),'baseline_source_zip_sha256':approved['baseline_source_zip_sha256'],'compiled_snippets':len(idx),'local_patches':local_count,'source_answer_exclusions':len(source_masks),'ppt_changed_volumes':changed_volumes,'powerpoint_playback_tested':False,'pptx':[{'volume':n,'file':f.name,'sha256':SHA(f),'bytes':f.stat().st_size} for n,f in sorted(decks.items())]}
    W(O/'delivery_manifest.json',report);W(R/'package_result.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
