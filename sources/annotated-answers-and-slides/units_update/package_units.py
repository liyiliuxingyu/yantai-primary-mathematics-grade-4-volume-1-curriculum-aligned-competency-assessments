"""Package the frozen unit-format correction. Run only after root READY."""
from pathlib import Path
import json, hashlib, shutil, zipfile, re

R = Path(__file__).resolve().parent
P, Q, O, S = R/'project', R/'project/units_update', R/'deliverables', R/'source_units_project'
INDEX_NAMES = ['全套题目与课件对应索引答案.csv', '口算逐式与课件对应索引答案.csv']
MEDIA = {'.pdf','.png','.svg','.jpg','.jpeg','.webp'}
FORMULA = {'formula','formulas','assets','math_assets','simplify_assets','recheck_assets','preserved_glyphs','average_assets','bracket_assets','brackets_assets'}
SKIP = {'__pycache__','node_modules','previews','validated','extracted','recovered_final','recovery','portable','compiled'}
APPROVED_HEIGHT_BOOKS = {10,16,17,22,24,49,52,53,54,55,56,58,61,63,70,75,79,81,82,93,97,100,101,104,105,106}

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
def field_patches(approved):
    rows=[]
    for name in ['patches','field_changes','field_patches']:
        if isinstance(approved.get(name),list):rows.extend(approved[name])
    for change in approved.get('changes',[]):
        if all(k in change for k in ['file','key','field','old','new']):rows.append(change)
        for name in ['patches','field_changes','field_patches']:
            for patch in change.get(name,[]):rows.append({'key':change['key'],**patch})
    result={}
    for patch in rows:
        if not all(k in patch for k in ['file','key','field','old','new']):continue
        token=(patch['file'],patch['key'],patch['field'])
        if token in result:assert result[token]['old']==patch['old'] and result[token]['new']==patch['new'],token
        result[token]=patch
    return result
def assert_field(patches,file,key,field,old,new):
    token=(file,key,field);assert token in patches,('Changed field absent from exact approval',token)
    patch=patches[token];assert patch['old']==old and patch['new']==new,token
def source_scope(white):
    approved=J(R/'approved_changes.json');assert approved==J(Q/'approved_changes.json')
    patches=field_patches(approved);assert patches,'Exact field patch approval is required'
    manifest=J(Q/'new_local_patches.json') if (Q/'new_local_patches.json').exists() else {'records':[]}
    new_by_id={x['id']:x for x in manifest['records']};actual_new_ids=set()
    oldzip=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip';cr=[];cn=[];nrec=0
    assert SHA(oldzip)=='f40bb760503aaaf563191e6b3115aab9a719ef715312ee27868353a2a75c6a70'
    with zipfile.ZipFile(oldzip) as z:
        for name in sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json',n)):
            a=json.loads(z.read(name));b=J(P/name);assert len(a['records'])==len(b['records'])
            assert {k:v for k,v in a.items() if k!='records'}=={k:v for k,v in b.items() if k!='records'},name
            for x,y in zip(a['records'],b['records']):
                nrec+=1;assert x['key']==y['key']
                if x==y:continue
                key=x['key'];assert key in white,key;cr.append(key)
                assert {k:v for k,v in x.items() if k not in {'answer_latex','verification'}}=={k:v for k,v in y.items() if k not in {'answer_latex','verification'}},key
                if x['answer_latex']!=y['answer_latex']:assert_field(patches,name,key,'answer_latex',x['answer_latex'],y['answer_latex'])
                if x['verification']!=y['verification']:
                    xv,yv=dict(x['verification']),dict(y['verification']);xc,yc=xv.pop('changes',[]),yv.pop('changes',[])
                    assert xv==yv and yc[:len(xc)]==xc,key
        for L in 'ABCD':
            name=f'detailed_layout/notes_{L}.json';a=json.loads(z.read(name));b=J(P/name)
            assert len(a['records'])==len(b['records'])
            assert {k:v for k,v in a.items() if k!='records'}=={k:v for k,v in b.items() if k!='records'}
            for x,y in zip(a['records'],b['records']):
                assert x['key']==y['key']
                if x==y:continue
                key=x['key'];assert key in white,key;cn.append(key)
                assert {k:v for k,v in x.items() if k not in {'latex','reason','local_replacements','original_replacements'}}=={k:v for k,v in y.items() if k not in {'latex','reason','local_replacements','original_replacements'}},key
                if x['latex']!=y['latex']:assert_field(patches,name,key,'latex',x['latex'],y['latex'])
                oldlocal=x.get('local_replacements',x.get('original_replacements',[]));newlocal=y.get('local_replacements',y.get('original_replacements',[]))
                assert len(newlocal)>=len(oldlocal),key
                local_field=('local_replacements' if 'local_replacements' in x else 'original_replacements' if 'original_replacements' in x else 'local_replacements' if 'local_replacements' in y else 'original_replacements')
                array_token=(name,key,local_field)
                if array_token in patches:
                    array_patch=patches[array_token];assert array_patch['new']==newlocal,array_token
                    intermediate=json.loads(json.dumps(oldlocal))
                    for i,node in enumerate(intermediate):
                        token=(name,key,f'{local_field}[{i}].latex')
                        if token in patches:
                            patch=patches[token];assert patch['old']==node['latex'],token;node['latex']=patch['new']
                    assert array_patch['old'] in [oldlocal,intermediate],array_token
                for i,oldnode in enumerate(oldlocal):
                    newnode=newlocal[i]
                    if oldnode==newnode:continue
                    assert oldnode['latex']!=newnode['latex'],('Unapproved local metadata-only change',key,i)
                    assert_field(patches,name,key,f'{local_field}[{i}].latex',oldnode['latex'],newnode['latex'])
                    geometry={'latex','reason','font_size','rect','target_rect','container_rect','align','valign','baseline_anchor','text_baseline_anchor'}
                    assert {k:v for k,v in oldnode.items() if k not in geometry}=={k:v for k,v in newnode.items() if k not in geometry},(key,i)
                for i,node in enumerate(newlocal[len(oldlocal):],len(oldlocal)):
                    identity=f'{key}_local{i+1}';assert identity in new_by_id,identity;actual_new_ids.add(identity)
                    descriptor=new_by_id[identity];assert descriptor['key']==key
                    assert array_token in patches,('New local missing complete approved source object',identity)
                    assert node['latex']==descriptor['latex'],identity
                    assert node.get('source_mask',node['rect'])==descriptor['mask_rect'],identity
                    for field in ['container_rect','text_baseline_anchor','baseline_anchor','target_rect']:
                        if field in descriptor and field in node:assert descriptor[field]==node[field],(identity,field)
        for L in 'ABCD':
            name=f'inline_layout/slots_{L}.json';assert J(P/name)==json.loads(z.read(name)),name
        assert actual_new_ids==set(new_by_id)
        # Unit formatting cannot undo the preceding Q4 or original-photo repairs.
        oldpage=json.loads(z.read('questions/p078.json'));newpage=J(P/'questions/p078.json')
        assert next(x for x in oldpage['records'] if x['key']=='p078_s04')==next(x for x in newpage['records'] if x['key']=='p078_s04')
        masks='p078_update/source_masks.json';assert J(P/masks)==json.loads(z.read(masks));assert len(J(P/masks)['masks'])==5
        preserved=[n for n in z.namelist() if n.startswith('p078_update/assets/') and not n.endswith('/')]
        for name in preserved:assert hashlib.sha256(z.read(name)).hexdigest()==SHA(P/name),name
    assert nrec==867 and set(cr)|set(cn)<=white
    return {'passed':True,'records':nrec,'approved_keys':sorted(white),'exact_field_patch_count':len(patches),'changed_question_keys':cr,'changed_note_keys':cn,'new_local_count':len(actual_new_ids),'unchanged_question_records':nrec-len(cr),'all_original_question_wording_options_tables_diagrams_and_slots_preserved':True,'Q4_B_and_5_black_repairs_preserved':True}
def page_geometry(pdf,scope):
    import fitz
    oldrel=J(R/'baseline/detailed_layout/current_release.json')
    page_books={x['answer_pdf_page']:x['book_page'] for x in oldrel['mapping']}
    allowed=scope.get('approved_height_growth_book_pages')
    assert allowed is not None,'Final scope must identify approved page-height growth books'
    assert set(allowed)<=APPROVED_HEIGHT_BOOKS
    declared=scope.get('page_height_changes',scope.get('page_height_deltas'))
    assert isinstance(declared,list),'Final scope must list actual page height deltas'
    bypage={x.get('pdf_page',x.get('answer_pdf_page',next((p for p,b in page_books.items() if b==x.get('book_page')),None))):x for x in declared}
    changes=[]
    with fitz.open(R/'bundle/小学同步素养四年级上册数学答案.pdf') as before,fitz.open(pdf) as after:
        assert len(before)==len(after)==128
        for i,(a,b) in enumerate(zip(before,after),1):
            assert abs(a.rect.width-b.rect.width)<.02,('Page width changed',i)
            delta=b.rect.height-a.rect.height;assert delta>=-.02,('Page height shrank',i)
            if delta<=.02:
                assert i not in bypage or abs(bypage[i].get('delta',0))<=.02,('False height change',i)
                continue
            book=page_books.get(i);assert book in allowed and book in APPROVED_HEIGHT_BOOKS,('Unapproved taller page',i,book)
            assert i in bypage,('Actual taller page absent from scope',i)
            row=bypage[i]
            oldheight=row.get('old_height',row.get('old_height_pt'))
            newheight=row.get('new_height',row.get('new_height_pt'))
            recorded_delta=row.get('delta',row.get('height_delta',row.get('delta_pt')))
            assert oldheight is not None and newheight is not None and recorded_delta is not None,('Incomplete height evidence',i)
            assert max(abs(oldheight-a.rect.height),abs(newheight-b.rect.height),abs(recorded_delta-delta))<.05,('Height evidence mismatch',i)
            changes.append({'pdf_page':i,'book_page':book,'old_height':a.rect.height,'new_height':b.rect.height,'delta':delta})
    assert {x['pdf_page'] for x in changes}=={p for p,x in bypage.items() if abs(x.get('delta',x.get('height_delta',x.get('delta_pt',0))))>.02}
    return {'passed':True,'all_page_widths_preserved':True,'pages':128,'approved_height_growth_book_pages':sorted(allowed),'actual_height_growth_book_pages':sorted(x['book_page'] for x in changes),'page_height_changes':changes,'all_other_page_heights_preserved':True}
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
    assert not S.exists(),'Use a fresh source_units_project stage'
    white=approved_keys();assert white
    qa=J(Q/'qa_current.json');assert qa.get('passed') is True
    rel=J(P/'detailed_layout/current_release.json');pdf=O/'小学同步素养四年级上册数学答案.pdf';h=SHA(pdf)
    assert h==qa['pdf_sha256']==rel['sha256']
    assert rel['pages']==128 and rel['question_pages']==108 and rel['record_coverage']==867 and rel['separate_analysis_pages']==0
    import fitz
    with fitz.open(pdf) as d:
        assert len(d)==128 and not d[0].get_text() and not d[0].get_images() and not d[0].get_drawings()
    scope=source_scope(white)
    scope_path,scopeqa=proof(qa,'scope_qa','units_update/qa_scope.json');assert scopeqa['pdf_sha256']==h
    geometry=page_geometry(pdf,scopeqa)
    recovery_path,recovery=proof(qa,'recovery_qa','units_update/qa_recovery.json');assert recovery['answer_sha256']==h
    local_count=len(rel['local_replacements']);assert recovery['local_patches_retained']==local_count
    old_source_masks=J(P/'average_update/source_masks.json')['masks']
    source_masks=rel['source_masks']
    assert all(x in source_masks for x in old_source_masks)
    assert recovery['source_answer_exclusions_retained']==len(source_masks)
    portable_path,portable=proof(qa,'portability_qa','units_update/qa_portability.json')
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
    assert sorted(decks)==list(range(1,7))
    paths=qa.get('ppt_qa_paths',qa.get('ppt_qa',['ppt_units/qa_final.json']))
    paths=[paths] if isinstance(paths,str) else paths;pptproof=[];proved_volumes=set();static_import_status={}
    for value in paths:
        path=evidence(value);j=J(path);assert j.get('passed') is True
        assert not j.get('native_powerpoint_playback_tested',j.get('powerpoint_playback_tested',False))
        vs=[]
        for v in j['volumes']:
            n=int(v['volume']); assert v['output_sha256']==SHA(decks[n]);vs.append(n);proved_volumes.add(n)
            if 'full_deck_import_succeeded' in v:
                assert isinstance(v['full_deck_import_succeeded'],bool)
                static_import_status[n]=v['full_deck_import_succeeded']
        relpath=path.relative_to(P) if path.is_relative_to(P) else path.relative_to(R)
        pptproof.append({'path':str(relpath),'sha256':SHA(path),'volumes':vs})
    assert set(changed_volumes)<=proved_volumes
    assert 1 in static_import_status,'Final PPT QA must state the actual final volume-1 full-deck import result'
    assert all(succeeded for n,succeeded in static_import_status.items() if n!=1)
    files=[f for f in sorted(P.rglob('*')) if f.is_file() and allowed(f)]
    before={str(f.relative_to(P)):SHA(f) for f in files};S.mkdir()
    for f in files: cp(f,S/f.relative_to(P))
    for name in ['版本记录答案.json','交付与使用说明答案.txt','源码使用说明答案.txt']:
        if (S/name).exists():cp(S/name,S/'checks/history/20261106_before_units'/name)
    for f in R.glob('*.py'):cp(f,S/'units_update'/f.name)
    for f in [R/'approved_changes.json']+[x for x in R.glob('audit_*.json')]:cp(f,S/'units_update'/f.name)
    cp(idxpath,S/'detailed_layout/snippet_index.json');(S/'latex/详细题内答案.tex').write_text(tex)
    for path in [scope_path,recovery_path,portable_path,Q/'qa_current.json']:cp(path,S/path.relative_to(P))
    for item in pptproof:cp(evidence(item['path']),S/item['path'])
    for name in INDEX_NAMES:
        if not (O/name).exists():cp(R/'bundle'/name,O/name)
        cp(O/name,S/name)
    W(S/'units_update/package_source_scope.json',scope)
    W(S/'units_update/package_page_geometry.json',geometry)
    books=sorted({int(k[1:4]) for k in white})
    extra_fix=''
    volume1_slides=next(int(v['slides']) for v in inv['volumes'] if int(v['volume'])==1)
    if static_import_status[1]:
        static_readme=(f'第1册完整保留{volume1_slides}张，本轮已整册导入所用静态渲染工具，并渲染、目视核对改动页。其他册也已整册导入该工具，实际渲染范围为改动页及另行标明的核查页。各册实际导入和渲染范围见ppt_units的最终QA。\n')
    else:
        static_readme=(f'第1册完整保留{volume1_slides}张；所用静态渲染工具未能完成该册整册导入，本轮依据最终实际幻灯片XML与递归依赖分批渲染并目视核对改动页。其他册已整册导入该工具，实际渲染范围为改动页及另行标明的核查页。各册实际导入和渲染范围见ppt_units的最终QA。\n')
    W(S/'版本记录答案.json',{'date':'2026-11-06','previous_pdf_sha256':rel['previous_pdf_sha256'],'current_pdf_sha256':h,'changed_question_keys':sorted(white),'changed_book_pages':books,'page_height_growth_book_pages':geometry['actual_height_growth_book_pages'],'change':'答案中的普通结果单位统一使用英文小括号；单位换算另起一行写清两端单位，换算行单位不套括号。原题、数量关系和结果保持，Q4仍只选B。','current_evidence':'units_update/qa_current.json','ppt_proofs':pptproof,'ppt_full_deck_static_import_succeeded':static_import_status,'powerpoint_playback_tested':False})
    readme=('本版PDF共128页，第一页空白，答案及解析继续写在题内，无新增PDF续页。\n'
      '本次统一答案书写：普通计算结果的单位使用英文小括号，如(米)；单位换算单独成行，换算两端单位写清，单位不套括号。题干、选项、已知表格、图形条件与数值结果不变。\n'
      '仅部分原页在题缝内增加高度以容纳换算分行，原页宽度、题序与全册页数保持。\n'
      '原书第78页选择题第4题仍按教学意图只选B：丙的年龄等于平均年龄，未据此推定具体岁数；原题各选项文字保留。前版第78页的5处黑字与图形修复继续保留。\n'
      '当前检查入口为源码包units_update/qa_current.json，实际数学、版面和课件静态检查范围见该记录；动画结构核对，未在PowerPoint/WPS中实际放映。此前q4_update、p078_update等记录为历史。\n'
      +static_readme+
      '长页整页缩印到单张A4时文字会变小。原书91页原扫描页脚模糊，按连续页序及题号索引定位。\n')
    (O/'交付与使用说明答案.txt').write_text(readme);(S/'交付与使用说明答案.txt').write_text(readme)
    (S/'源码使用说明答案.txt').write_text('当前入口：units_update/qa_current.json。活动题源为questions，题内解析为detailed_layout/notes_A到D，当前课件哈希为ppt_builder/current_inventory.json。\n'
      f'latex/详细题内答案.tex含{len(idx)}个实际编译片段，含{local_count}个局部替换，使用相对字体路径。项目根目录编译：\n  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex\n'
      '从当前交付PDF恢复与重建：\n  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf\n  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf\n'
      '本次补丁与QA在units_update，课件源在ppt_units。第78页原照片、新TikZ、SVG和字体继续保存在p078_update/assets。历史记录供追溯，课堂作答以当前questions及notes为准，不应盲目重跑旧补丁。重新组合图层可能有抗锯齿差异，不承诺重建文件字节或像素相同。Python需要PyMuPDF/NumPy，公式需要XeLaTeX。\n')
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
    report={'pdf':{'file':pdf.name,'sha256':h,'bytes':pdf.stat().st_size},'source_zip':sm,'overall_zip':om,'pages':128,'records':867,'page_height_growth_count':len(geometry['page_height_changes']),'page_height_changes':geometry['page_height_changes'],'changed_question_keys':sorted(white),'source_field_patch_count':scope['exact_field_patch_count'],'new_local_patches':scope['new_local_count'],'conversion_question_keys':approved.get('conversion_keys',[]),'baseline_source_zip_sha256':'f40bb760503aaaf563191e6b3115aab9a719ef715312ee27868353a2a75c6a70','compiled_snippets':len(idx),'local_patches':local_count,'source_answer_exclusions':len(source_masks),'ppt_changed_volumes':changed_volumes,'ppt_full_deck_static_import_succeeded':static_import_status,'powerpoint_playback_tested':False,'pptx':[{'volume':n,'file':f.name,'sha256':SHA(f),'bytes':f.stat().st_size} for n,f in sorted(decks.items())]}
    W(O/'delivery_manifest.json',report);W(R/'package_result.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
