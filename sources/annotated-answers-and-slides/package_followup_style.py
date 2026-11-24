"""Package the reviewed two-question analysis-tree follow-up.

This command is intentionally one-shot: it refuses to reuse a source stage.
Run only after the PDF, all associated QA, and PPT inventory are final.
"""
from pathlib import Path
import csv
import hashlib
import json
import shutil
import zipfile

R=Path(__file__).resolve().parent
C=R/'detailed_layout'
O=R/'deliverables'
F=R/'followup_style'
S=R/'source_followup_style_project'
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def cp(p,q):
    q.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(p,q)

def zip_checked(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,n in files:
            z.write(p,n)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
        for p,n in files:
            assert hashlib.sha256(z.read(n)).hexdigest()==SHA(p),(path,n)
        assert all(not any(ord(c)>127 for c in x.filename)or x.flag_bits&0x800
                   for x in z.infolist())
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':SHA(path)}

def copy_patch_sources(source,target):
    """Keep reproducible code/assets, excluding complete decks and QA renders."""
    blocked={'before','actual_static_export','validated','__pycache__','node_modules','r2'}
    allowed={'.py','.mjs','.json','.tex','.svg','.png','.pdf','.md','.txt'}
    for p in source.rglob('*'):
        rel=p.relative_to(source)
        if not p.is_file()or any(part in blocked for part in rel.parts):
            continue
        if p.suffix in allowed and not p.name.endswith('.stdout.log'):
            cp(p,target/rel)

def main():
    rel=J(C/'current_release.json')
    pdf=O/'小学同步素养四年级上册数学答案.pdf'
    h=SHA(pdf)
    assert h==rel['sha256'] and rel['first_page_blank']
    assert rel['pages']==128 and rel['separate_analysis_pages']==0
    assert len(rel['local_replacements'])==60
    for name in ['qa_release.json','qa_portability.json']+[f'qa_visual_{L}.json'for L in 'ABCD']:
        q=J(C/name)
        assert q['passed'] and q['pdf_sha256']==h,(name,q.get('pdf_sha256'))
    notes={n['key']:n for L in 'ABCD'for n in J(C/f'notes_{L}.json')['records']}
    assert len(notes)==867
    records={q['key']:q for p in sorted((R/'questions').glob('p[0-9][0-9][0-9].json'))
             for q in J(p)['records']}
    assert len(records)==867
    spec=J(F/'style_spec.json')
    assert set(spec['changed_keys'])=={'p005_s04','p007_s08'}
    for name in ['audit_early.json','audit_mid.json','audit_late.json','qa_math_visual.json','qa_scope.json','qa_tikz.json','qa_recovery.json']:
        assert (F/name).is_file(),name
    early=J(F/'audit_early.json');mid=J(F/'audit_mid.json');late=J(F/'audit_late.json')
    audited_pages=early['scope']['book_pages']+[x['book_page']for x in mid['pages']]+late['actual_question_pages']
    assert len(audited_pages)==len(set(audited_pages))==105
    assert set(audited_pages)==set(range(4,109))
    assert early['scope']['records_count']+mid['scope']['records']+late['record_count']==843
    assert sum(q['book_page']>=4 for q in records.values())==843

    idx=O/'全套题目与课件对应索引答案.csv'
    rows=list(csv.DictReader(idx.open(encoding='utf-8-sig')))
    assert len(rows)==867
    for row in rows:
        k=row['稳定编号'];target=notes[k].get('covered_by')or k
        row['该题解法所在PDF页序']=str(records[target]['book_page']+4)
        row['原扫描页脚读数（异常时）']={66:'96',70:'20',77:'27'}.get(records[k]['book_page'],'')
    with idx.open('w',encoding='utf-8-sig',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

    inv=J(R/'ppt_builder/current_inventory.json')
    ppts=[]
    for v in inv['volumes']:
        p=O/'讲解课件'/v['pptx']
        assert SHA(p)==v['sha256'],p
        ppts.append(p)
        with zipfile.ZipFile(p)as z:
            assert z.testzip()is None
    assert len(ppts)==6
    pptqa=J(F/'ppt/qa_ppt.json')
    assert pptqa['output_sha256']==SHA(ppts[0])
    assert pptqa['native_omml_formula_count']==9
    assert pptqa['all_426_timing_xml_byte_identical']
    assert pptqa['all_422_other_slide_xml_byte_identical']
    changed_slides=pptqa.get('changed_slides',pptqa.get('changed_slide_numbers'))
    if changed_slides is None:
        # The exact list may be recorded beneath the package-preservation QA.
        for key in ['scope','package','package_preservation','preservation']:
            part=pptqa.get(key,{})
            if isinstance(part,dict):
                changed_slides=part.get('changed_slides',part.get('changed_slide_numbers'))
                if changed_slides is not None:break
    assert isinstance(changed_slides,list)and changed_slides,'PPT QA must identify actual changed slides'
    slides='、'.join(map(str,changed_slides))

    freeze_path=C/'source_freeze.json'
    freeze=J(freeze_path)
    self_entry=next(x for x in freeze['files']if x['file']=='package_followup_style.py')
    self_entry['sha256']=SHA(Path(__file__).resolve())
    freeze_path.write_text(json.dumps(freeze,ensure_ascii=False,indent=2))

    assert not S.exists(),'Choose a fresh source stage'
    S.mkdir()
    for folder in ['questions','figures','tikz','preserved_glyphs','fonts','ppt_builder']:
        for p in sorted((R/folder).rglob('*')):
            if p.is_file()and '__pycache__'not in p.parts:
                cp(p,S/p.relative_to(R))
    for p in (R/'recovered/source').rglob('*'):
        if p.is_file():cp(p,S/p.relative_to(R))
    for name in ['answer_content.py','build_detailed_answers.py','recover_detailed_base.py',
                 'answer_page_map.json','package_unit1_style.py','package_followup_style.py']:
        cp(R/name,S/name)
    for p in R.glob('*.json'):
        if p.name not in ['交付源码文件校验答案.json','版本记录答案.json','answer_page_map.json']:
            cp(p,S/p.name)
    for name in ['slots_A.json','slots_B.json','slots_C.json','slots_D.json','pointer_masks.json','footer_crops.json']:
        cp(R/'inline_layout'/name,S/'inline_layout'/name)
    for name in ['notes_A.json','notes_B.json','notes_C.json','notes_D.json',
                 'duplicate_formula_masks.json','base_local_targets.json','source_freeze.json',
                 'legacy_note_cleanup.json','footer_overrides.json','current_release.json']:
        cp(C/name,S/'detailed_layout'/name)
    for p in C.glob('qa*.json'):
        if p.name not in ['qa_recovery.json','qa_recovery_final.json','qa_lossless_optimization.json','qa_final_lossless_optimization.json']:
            cp(p,S/'checks/detailed_layout'/p.name)
    for p in (R/'checks/ppt').rglob('*'):
        if p.is_file():cp(p,S/p.relative_to(R))
    # Preserve the complete preceding p003 revision and this follow-up source.
    for name in ['p003_style_spec.json','qa_p003_math_visual.json','qa_pdf_scope.json',
                 'qa_tikz.json','qa_lossless_optimization.json','qa_recovery.json','reference_summary.json']:
        cp(R/'style_patch'/name,S/'style_patch'/name)
    copy_patch_sources(R/'style_patch/ppt_final_r3',S/'style_patch/ppt_final_r3')
    for name in ['audit_early.json','audit_mid.json','audit_late.json','style_spec.json',
                 'detected_boxes.json','apply_followup.py','preserve_unchanged_pages.py',
                 'check_scope_portable.py','bind_final_checks.py','qa_math_visual.json',
                 'qa_scope.json','qa_recovery.json','qa_tikz.json']:
        cp(F/name,S/'followup_style'/name)
    for name in ['qa_lossless.json','qa_lossless_optimization.json','qa_portability.json']:
        if(F/name).exists():cp(F/name,S/'followup_style'/name)
    cp(F/'before/detailed_layout/current_release.json',
       S/'followup_style/before/detailed_layout/current_release.json')
    copy_patch_sources(F/'ppt',S/'followup_style/ppt')
    cp(C/'verify_detailed.py',S/'detailed_layout/verify_detailed.py')
    cp(R/'concise_layout/deduplicate_identical_jpegs.py',S/'detailed_layout/deduplicate_identical_jpegs.py')
    cp(Path(rel['compiled_pdf']).parent/'snippet_index.json',S/'detailed_layout/snippet_index.json')
    tex=Path(rel['compiled_tex']).read_text().replace(str(R/'recovered/source/new_work'),'recovered/source/new_work')
    tp=S/'latex/详细题内答案.tex';tp.parent.mkdir();tp.write_text(tex)
    assert SHA(tp)==J(C/'qa_portability.json')['portable_tex_sha256']
    for name in ['全套题目与课件对应索引答案.csv','口算逐式与课件对应索引答案.csv']:
        cp(O/name,S/name)
    for name in ['图形索引答案.csv','保留原字形说明答案.json']:
        if(R/name).exists():cp(R/name,S/name)

    readme=f'''本版沿用题内红笔答案版式，第一页空白，共128页，无新增解析续页。本次检查原书第4—108页共105页、843条题记录，确认另有两题属于同类数量关系分析树：第5页一3（答案PDF第9页）、第7页四1（答案PDF第11页）。这两题按第一单元信息窗三补齐框内数量名称、数据、单位，配齐列式与回顾检验；前版第3页四1的修改保留。其他106个题页与上一版保持。线段图、赛程树等保留各自原题形式。
详细解析说明推理依据、数量关系、运算律及各方法思路；原处已有的完整脱式、答语、图形不重复抄写。自然跨原书页的同一道题只在完整题处展开，详见总索引的“该题解法所在PDF页序”。
新增解析正文11.5pt，既有局部脱式10.5pt，分析框标注根据原框空间排版；公式实际由LaTeX编译。原题595pt宽及原字形保持，题间空间不足时仍纵向加长，按宽度阅读；缩印整张长页到单张A4会使字变小。
六册PPTX共2667张。本次同步第1册第{slides}张，原生可编辑分析树配齐数量名称、数据、单位；其余题目保持。既有p003更正版保留，已知量与求得量按教学顺序区分；受改页共有9个真正OMML公式，并附实际LaTeX编译的SVG/PNG兼容分支。第1册全部426张的timing保持原字节。受改页实际经LibreOffice静态导出检查，未在PowerPoint逐项放映验证。
原题模糊或矛盾仍保留条件说明，包括第78页二4按字面B成立、D在具体岁数未给时也成立的限定，不能删去限定而当作唯一确定值。
本次数学复核集中在两道受改题；其他题目沿用此前检查。题型存在性筛查、数学复核、自动位置检查和人工版面审阅分别记录，不承诺绝对无误。原书末尾参考答案影印保留，与本次题内条件说明不一致时应结合题源核对使用。原扫描第66、70、77对应位置的页脚分别显示96、20、27，本版按已核对的连续对应表显示66、70、77，原扫描字节保留可追溯。第42、46页大题标题裁片按1:1移至上一题详解之后，避免前题解析越过下一道题。
'''
    (O/'交付与使用说明答案.txt').write_text(readme)
    (S/'交付与使用说明答案.txt').write_text(readme)
    source_readme='''源码以本次详细题内解析为活动版本。
1. detailed_layout/notes_A到D对应867条原题记录；latex/详细题内答案.tex为解析及局部脱式的XeLaTeX片段源，使用包内相对字体路径。项目根目录运行 xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex。
2. 从本次答案PDF恢复并重建：
   python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf
   python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf
恢复器核验原题条带并提取共同A4图层，新增详细解析不带回底本；保留原红答案及累计60处局部替换（32处既有规范脱式、前轮p003的14个数量标签、本轮p005/p007的14个数量标签）。同时把两处大题标题裁片恢复原位；扫描异常页码重建时由footer_overrides再次规范显示。base_local_targets记录既有局部对象位置，重建时先复原底本再放置当前答案，避免同一笔画重复叠加。
3. figures与tikz中的284个图形源均为真正TikZ；保留原字形的3张图位于preserved_glyphs。索引区分原书页、原底本页、答案PDF页及PPT幻灯片序号。本次两题的原题图不改，答案图源补齐数量标记。
4. Python依赖PyMuPDF和NumPy，公式编译需要XeLaTeX。源包附带已使用字体。源码检查中的绝对路径用于追溯实际工作环境；重建命令应在解压后的项目根目录执行。
5. 可用 detailed_layout/deduplicate_identical_jpegs.py 减少重复JPEG资源；该脚本必须独立比较所有页面。实际测试范围见checks/detailed_layout及followup_style；题型筛查、数学审阅、版面、编译与无损优化分别记录。
6. 六册PPT沿用当前版本，原生成器与既有定点更正脚本位于ppt_builder；上轮p003改动的实现位于style_patch/ppt_final_r3；本轮p005/p007的实现及兼容公式资产位于followup_style/ppt。重新生成需要对应Artifact Tool/Node环境，直接使用交付PPTX不需要这些开发工具。没有把LibreOffice静态检查称为PowerPoint放映验证。
7. followup_style/apply_followup.py是记录上一版到本版变更的一次性历史补丁；本包的questions、notes、TikZ已是补丁后的活动源，不要再次应用该补丁。第2条是当前内容的标准重建路径，重新导入页面时可能产生极小的非内容抗锯齿差异。
8. 本次为使其余106个题页逐像素保持上一版，发行时只替换已审阅的第5、7页。历史发布步骤见followup_style/preserve_unchanged_pages.py；小型基线receipt已保留在followup_style/before/detailed_layout/current_release.json。该步骤还依赖上一版答案PDF（SHA-256见版本记录），源包不重复包含此大文件，必须另行提供到followup_style/before/previous.pdf。没有上一版PDF时可按第2条重建当前内容，不能声称精确重现本次106旧页的像素保留。该历史脚本还要求按原步骤分别生成followup_unit1_trees两页草稿、followup_unit1_trees_final全书记录后再运行，不能在任意运行名称下直接调用。
'''
    (S/'源码使用说明答案.txt').write_text(source_readme)
    version={'previous_pdf_sha256':spec['baseline_pdf_sha256'],'current_pdf_sha256':h,
             'change':'检查后续105页，原书5页一3及7页四1按信息窗三补齐数量分析树、列式与检验，保留p003前轮修改；其余106题页保持。',
             'changed_question_keys':spec['changed_keys'],'ppt_volume':1,'ppt_changed_slides':changed_slides}
    (S/'版本记录答案.json').write_text(json.dumps(version,ensure_ascii=False,indent=2))
    files=[{'file':str(p.relative_to(S)),'bytes':p.stat().st_size,'sha256':SHA(p)}
           for p in sorted(S.rglob('*'))if p.is_file()]
    (S/'交付源码文件校验答案.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2))
    src=O/'小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    sm=zip_checked(src,[(p,str(p.relative_to(S)))for p in sorted(S.rglob('*'))if p.is_file()])
    overall=O/'小学四上同步素养卷全套答案.zip'
    om=zip_checked(overall,[(p,p.name)for p in [pdf,idx,O/'口算逐式与课件对应索引答案.csv',
                    O/'交付与使用说明答案.txt',src]]+[(p,'讲解课件/'+p.name)for p in ppts])
    out={'pdf':{'file':pdf.name,'bytes':pdf.stat().st_size,'sha256':h},
         'source_zip':sm,'overall_zip':om,'pages':128,'records':867,
         'detailed_notes':rel['visible_note_blocks'],'first_page_blank':True,
         'no_continuation_pages':True,'changed_question_keys':spec['changed_keys'],
         'pptx':[{'file':p.name,'sha256':SHA(p)}for p in ppts]}
    (O/'delivery_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':
    main()
