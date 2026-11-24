"""Package the reviewed symmetry-axis terminology correction.

Run only after the parent has frozen the PDF, current QA entry, recovery proof,
and both changed PPTX files.  This script does not create or test mathematics.
It verifies the supplied current evidence and packages the reviewed files.
"""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

R=Path(__file__).resolve().parent
P=R/'project'
O=R/'deliverables'
S=R/'source_axis_precision_project'
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cp(p,q):
    q.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,q)

def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2))

def checked_zip(path,members):
    assert len({n for _,n in members})==len(members)
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for p,n in members:z.write(p,n)
    with zipfile.ZipFile(path)as z:
        assert z.testzip()is None
        assert len(z.infolist())==len(members)
        for p,n in members:
            assert hashlib.sha256(z.read(n)).hexdigest()==SHA(p),n
        assert all(x.flag_bits&0x800 for x in z.infolist()
                   if any(ord(c)>127 for c in x.filename))
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':SHA(path),
            'members':len(members),'crc_checked':True,'member_sha256_checked':True,
            'chinese_filenames_utf8_checked':True}

def source_allowed(p):
    rel=p.relative_to(P)
    if rel.as_posix()=='交付源码文件校验答案.json':return False
    if any(x in rel.parts for x in ['__pycache__','node_modules','previews',
                                    'actual_static_export','validated']):return False
    if rel.parts[0]=='axis_update'and any(x in rel.parts[1:]for x in
            ['compiled','recovered','recovered_final','portable','rendered','static']):return False
    if rel.parts[0]=='axis_update'and p.suffix=='.pdf':return False
    if p.suffix in ['.log','.aux','.xdv','.out','.tmp','.pptx']:return False
    return True

def copy_new_ppt_sources():
    root=R/'ppt'
    # Actual slide PNGs and full decks are reviewed outputs, not reusable source.
    blocked={'final','before_v4','before_v5','before_v4_font','before_v5_font',
             'after_v4','after_v5','node_modules','__pycache__'}
    for p in sorted(root.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(root)
        if any(x in blocked for x in rel.parts):continue
        if p.suffix in ['.log','.aux','.out','.xdv','.pptx']:continue
        if p.suffix in ['.png','.pdf','.svg']and rel.parts[0]!='formula':continue
        if p.suffix in ['.py','.mjs','.json','.md','.txt','.tex','.png','.pdf','.svg']:
            cp(p,S/'axis_update/ppt'/rel)

def main():
    # The current QA entry is distinct from all inherited historical QA files.
    qa_path=P/'axis_update/qa_current.json'
    qa=J(qa_path)
    assert qa['passed']is True
    rel=J(P/'detailed_layout/current_release.json')
    pdf=O/'小学同步素养四年级上册数学答案.pdf'
    h=SHA(pdf)
    assert h==rel['sha256']==qa['pdf_sha256']
    assert rel['pages']==128 and rel['first_page_blank']
    assert rel['separate_analysis_pages']==0
    assert len(rel['local_replacements'])==61
    assert qa['changed_book_pages']==[65,70,85]
    assert qa['unchanged_pdf_pages']==125
    scope=J(P/'axis_update/qa_scope.json')
    assert scope['passed']and scope['pdf_sha256']==h
    assert scope['unchanged_pdf_pages']==125
    recovery=J(P/'axis_update/qa_recovery.json')
    assert recovery['passed']and recovery['answer_sha256']==h
    assert recovery['local_patches_retained']==61
    records={q['key']:q for p in sorted((P/'questions').glob('p[0-9][0-9][0-9].json'))
             for q in J(p)['records']}
    notes={n['key']:n for L in'ABCD'
           for n in J(P/f'detailed_layout/notes_{L}.json')['records']}
    assert len(records)==len(notes)==867
    assert '\\times'in records['p070_s06']['answer_latex']
    assert '判断正确'not in notes['p070_s06']['latex']
    for name in ['final_answers.json','final_answers_c.json']:
        assert J(P/'ppt_builder'/name)['records']['p070_s06']['final_answers'][0]['answer_latex']==r'\times'

    # Parent copies the six final decks.  Never overwrite a changed deck here.
    inv=J(P/'ppt_builder/current_inventory.json')
    ppts=[]
    for v in inv['volumes']:
        p=O/'讲解课件'/v['pptx'];assert p.is_file(),p
        assert SHA(p)==v['sha256'],p
        with zipfile.ZipFile(p)as z:assert z.testzip()is None
        ppts.append(p)
    assert len(ppts)==6
    pq=J(R/'ppt/qa_package.json');assert pq['passed']
    for v in pq['volumes']:
        name=f'小学四上同步素养卷第{v["volume"]}册讲解课件答案.pptx'
        p=O/'讲解课件'/name
        assert SHA(p)==v['output_sha256']
        assert v['all_timing_xml_byte_identical']==v['slide_count']
        assert v['all_shape_id_sequences_identical']==v['slide_count']
        assert v['all_other_original_components_byte_identical']

    assert not S.exists(),'Choose a fresh staging directory before another run'
    S.mkdir()
    for p in sorted(P.rglob('*')):
        if p.is_file()and source_allowed(p):cp(p,S/p.relative_to(P))

    # Retain the previous version record as history before installing this one.
    if(S/'版本记录答案.json').exists():
        cp(S/'版本记录答案.json',S/'checks/history/20261102_版本记录答案.json')
    compiled=Path(rel['compiled_tex'])
    text=compiled.read_text().replace(str(P/'recovered/source/new_work'),'recovered/source/new_work')
    assert str(P)not in text,'Portable TeX still has a project absolute path'
    (S/'latex/详细题内答案.tex').write_text(text)
    portable=J(P/'axis_update/qa_portability.json')
    assert portable['passed']and portable['snippets']==917
    assert portable['portable_tex_sha256']==SHA(S/'latex/详细题内答案.tex')
    cp(Path(rel['compiled_pdf']).parent/'snippet_index.json',S/'detailed_layout/snippet_index.json')
    index=J(S/'detailed_layout/snippet_index.json');assert len(index)==917
    assert '原句应判错'in index['p070_s06']['body']
    assert index['p070_s06_local1']['body']==r'\(\times\)'

    # These are historical targeted patch sources; the active source above is
    # already modified. Their original input artifacts are intentionally omitted.
    for p in sorted(R.glob('*.py')):
        cp(p,S/'axis_update'/p.name)
    for name in ['audit.json','source_changes.json','pdf_patch_report.json',
                 'qa_pdf.json','qa_scope.json','qa_math_visual.json','qa_recovery.json',
                 'qa_portability.json','qa_current.json']:
        if(R/name).is_file():cp(R/name,S/'axis_update'/name)
    copy_new_ppt_sources()
    # Preserve the parent-created current QA entry and all current proof files.
    for p in sorted((P/'axis_update').glob('*.json')):cp(p,S/'axis_update'/p.name)
    assert J(S/'axis_update/qa_current.json')['pdf_sha256']==h

    for name in ['全套题目与课件对应索引答案.csv','口算逐式与课件对应索引答案.csv']:
        src=O/name
        if not src.exists():cp(R/'bundle'/name,src)
        cp(src,S/name)

    version={'date':'2026-11-03','previous_pdf_sha256':rel['previous_pdf_sha256'],
             'current_pdf_sha256':h,'changed_question_keys':
             ['p065_s05','p070_s06','p070_s11','p085_s11'],
             'changed_book_pages':[65,70,85],'unchanged_pdf_pages':125,
             'correction':'原书70页二4由√订正为×；对角线是线段，对称轴是直线，规范表述为对角线所在的直线。原书参考答案本来也是×。',
             'ppt_changes':{str(x['volume']):x['changed_slides']for x in pq['volumes']},
             'current_evidence':'axis_update/qa_current.json'}
    save(S/'版本记录答案.json',version)

    readme='''本版保留原题题内红笔答案版式，共128页，第一页空白，无新增解析续页。
本次订正原书第70页二、4（答案PDF第74页）：“正方形的对角线是它的对称轴”按严格术语判×。对角线是线段，对称轴是直线，正确说法是“正方形每条对角线所在的直线都是它的对称轴”。原书书后参考答案本来也是×，本次纠正的是此前制作的红笔答案。
原书第65页一、4、第70页三、4、第85页一、8的相关解析一并规范为“所在的直线”；这些题的轴数和选项不变。其余125个PDF页面保持原版像素，包含其余105个题页；本次没有重新验算全书其他题目。
第4册课件第374、375张的错判和回填同步改×；第5册第293张补充所在直线。三张受改页做了实际静态渲染核对，保留全部原动画时间线和对象编号；未在PowerPoint中放映测试。其余四册保持。
答案及公式采用实际数学排版。原题中的对称轴虚线、图形和中文提示保留；本次没有改变题目图形。已有长页仍按原宽度阅读，整页缩印到单张A4会使文字变小。
'''
    (O/'交付与使用说明答案.txt').write_text(readme)
    (S/'交付与使用说明答案.txt').write_text(readme)
    source_readme='''本包中的questions、detailed_layout/notes_A到D、ppt_builder/final_answers及latex源均为本次订正后的活动内容。
当前证据入口为axis_update/qa_current.json，分别记录本次数学、版面、源文件、像素保留及课件检查的实际范围。checks、style_patch和followup_style中的既有记录保留历史用途，不能当作本次对全书重新验算或重新人工审阅的证明。
latex/详细题内答案.tex含917个实际XeLaTeX片段（856段注释及61处局部替换），字体路径已改为包内相对路径。项目根目录运行：
  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex
从本次答案PDF恢复原题底层并重建当前答案内容：
  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf
  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf
恢复器使用当前detailed_layout/current_release.json核验图层位置；原书70页局部判断订正已写入原题A4底层，重建后不会恢复旧勾。重新导入图层可能产生极小的抗锯齿差异；本次发行实际保留其余125页的像素，不能把任意重建文件冒称字节或像素完全相同。
axis_update/update_sources.py、patch_pdf.py及ppt/patch_axis.py是本次从上一版到本版的历史定点修改程序，活动源已修改完成，不要重复执行这些一次性补丁。历史补丁还依赖上一版答案PDF或课件（未重复装入源包），其路径和环境见各脚本、ppt/REPRODUCTION.txt；标准内容重建使用上面的命令。
六册课件的生成源与既有定点修正保留在ppt_builder、style_patch和followup_style；本次新增修正在axis_update/ppt。重建时必须应用本次修正，不能直接用旧生成器覆盖交付PPTX。实际PPT公式回填为原生OMML并附实际XeLaTeX生成的SVG/PNG兼容分支。没有把静态渲染检查称为PowerPoint放映验证。
Python需要PyMuPDF和NumPy；公式编译需要XeLaTeX。包内保留原来284个真正TikZ图形源及必要原字形资产，图形源本次未改。
'''
    (S/'源码使用说明答案.txt').write_text(source_readme)
    freeze_files=['questions/p065.json','questions/p070.json','questions/p085.json',
                  'detailed_layout/notes_C.json','detailed_layout/notes_D.json',
                  'detailed_layout/current_release.json','detailed_layout/base_local_targets.json',
                  'detailed_layout/snippet_index.json','latex/详细题内答案.tex',
                  'ppt_builder/final_answers.json','ppt_builder/final_answers_c.json',
                  'ppt_builder/current_inventory.json']
    save(S/'axis_update/source_freeze.json',{'records':867,'local_patches':61,
         'compiled_snippets':917,'files':[{'file':n,'sha256':SHA(S/n)}for n in freeze_files],
         'scope':'Exact current source hashes; a source freeze is not a mathematical proof.'})
    files=[{'file':str(p.relative_to(S)),'bytes':p.stat().st_size,'sha256':SHA(p)}
           for p in sorted(S.rglob('*'))if p.is_file()]
    save(S/'交付源码文件校验答案.json',{'files':files})
    src=O/'小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    sm=checked_zip(src,[(p,str(p.relative_to(S)))for p in sorted(S.rglob('*'))if p.is_file()])
    overall=O/'小学四上同步素养卷全套答案.zip'
    base=[pdf,O/'全套题目与课件对应索引答案.csv',O/'口算逐式与课件对应索引答案.csv',
          O/'交付与使用说明答案.txt',src]
    om=checked_zip(overall,[(p,p.name)for p in base]+[(p,'讲解课件/'+p.name)for p in ppts])
    report={'pdf':{'file':pdf.name,'bytes':pdf.stat().st_size,'sha256':h},
            'source_zip':sm,'overall_zip':om,'source_file_count':len(files)+1,
            'pages':128,'records':867,'first_page_blank':True,'no_added_pages':True,
            'changed_book_pages':[65,70,85],'unchanged_pdf_pages':125,
            'pptx':[{'file':p.name,'bytes':p.stat().st_size,'sha256':SHA(p)}for p in ppts]}
    save(O/'delivery_manifest.json',report);save(R/'package_result.json',report)
    print(json.dumps(report,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
