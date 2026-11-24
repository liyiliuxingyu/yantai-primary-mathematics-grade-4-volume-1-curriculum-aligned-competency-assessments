"""Package the reviewed detailed PDF, unchanged decks and reproducible sources."""
from pathlib import Path
import json,hashlib,zipfile,shutil,csv
R=Path(__file__).resolve().parent; C=R/'detailed_layout'; O=R/'deliverables'; S=R/'source_unit1_style_project'
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cp(p,q):
    q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
def zip_checked(path,files):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,n in files:z.write(p,n)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
        for p,n in files:assert hashlib.sha256(z.read(n)).hexdigest()==SHA(p)
        assert all(not any(ord(c)>127 for c in x.filename)or x.flag_bits&0x800 for x in z.infolist())
    return {'file':path.name,'bytes':path.stat().st_size,'sha256':SHA(path)}
def main():
    rel=J(C/'current_release.json'); pdf=O/'小学同步素养四年级上册数学答案.pdf';h=SHA(pdf)
    assert h==rel['sha256'] and rel['first_page_blank'] and rel['pages']==128 and rel['separate_analysis_pages']==0
    for f in ['qa_release.json','qa_portability.json']+[f'qa_visual_{L}.json'for L in 'ABCD']:
        q=J(C/f);assert q['passed'] and q['pdf_sha256']==h,(f,q.get('pdf_sha256'))
    notes={n['key']:n for L in 'ABCD' for n in J(C/f'notes_{L}.json')['records']};assert len(notes)==867
    records={q['key']:q for p in sorted((R/'questions').glob('p[0-9][0-9][0-9].json'))for q in J(p)['records']}
    idx=O/'全套题目与课件对应索引答案.csv'; rows=list(csv.DictReader(idx.open(encoding='utf-8-sig')));assert len(rows)==867
    for row in rows:
        k=row['稳定编号']; target=notes[k].get('covered_by')or k
        row['该题解法所在PDF页序']=str(records[target]['book_page']+4)
        row['原扫描页脚读数（异常时）']={66:'96',70:'20',77:'27'}.get(records[k]['book_page'],'')
    with idx.open('w',encoding='utf-8-sig',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    inv=J(R/'ppt_builder/current_inventory.json'); ppts=[]
    for v in inv['volumes']:
        p=O/'讲解课件'/v['pptx']; assert SHA(p)==v['sha256'];ppts.append(p)
        with zipfile.ZipFile(p)as z:assert z.testzip()is None
    assert not S.exists(),'Choose a fresh source stage'
    S.mkdir()
    for folder in ['questions','figures','tikz','preserved_glyphs','fonts','ppt_builder']:
        for p in sorted((R/folder).rglob('*')):
            if p.is_file()and '__pycache__'not in p.parts:cp(p,S/p.relative_to(R))
    for p in (R/'recovered/source').rglob('*'):
        if p.is_file():cp(p,S/p.relative_to(R))
    for name in ['answer_content.py','build_detailed_answers.py','recover_detailed_base.py','answer_page_map.json','package_unit1_style.py']:
        cp(R/name,S/name)
    for p in R.glob('*.json'):
        if p.name not in ['交付源码文件校验答案.json','版本记录答案.json','answer_page_map.json']:cp(p,S/p.name)
    for name in ['slots_A.json','slots_B.json','slots_C.json','slots_D.json','pointer_masks.json','footer_crops.json']:
        cp(R/'inline_layout'/name,S/'inline_layout'/name)
    for name in ['notes_A.json','notes_B.json','notes_C.json','notes_D.json','duplicate_formula_masks.json','base_local_targets.json','source_freeze.json','legacy_note_cleanup.json','footer_overrides.json','current_release.json']:
        cp(C/name,S/'detailed_layout'/name)
    for p in C.glob('qa*.json'):
        if p.name not in ['qa_recovery.json','qa_recovery_final.json','qa_lossless_optimization.json','qa_final_lossless_optimization.json']:cp(p,S/'checks/detailed_layout'/p.name)
    for p in (R/'checks/ppt').rglob('*'):
        if p.is_file():cp(p,S/p.relative_to(R))
    for name in ['p003_style_spec.json','qa_p003_math_visual.json','qa_pdf_scope.json','qa_tikz.json','qa_lossless_optimization.json','qa_recovery.json','reference_summary.json']:
        cp(R/'style_patch'/name,S/'style_patch'/name)
    pp=R/'style_patch/ppt_final_r3'
    for p in pp.rglob('*'):
        if not p.is_file()or any(x in p.parts for x in ['actual_static_export','validated','__pycache__']):continue
        if p.suffix in ['.py','.mjs','.json','.tex','.svg','.png','.pdf','.md','.txt']and not p.name.endswith('.stdout.log'):
            cp(p,S/'style_patch/ppt_final_r3'/p.relative_to(pp))
    cp(C/'verify_detailed.py',S/'detailed_layout/verify_detailed.py')
    cp(R/'concise_layout/deduplicate_identical_jpegs.py',S/'detailed_layout/deduplicate_identical_jpegs.py')
    cp(Path(rel['compiled_pdf']).parent/'snippet_index.json',S/'detailed_layout/snippet_index.json')
    tex=Path(rel['compiled_tex']).read_text().replace(str(R/'recovered/source/new_work'),'recovered/source/new_work')
    tp=S/'latex/详细题内答案.tex';tp.parent.mkdir();tp.write_text(tex)
    assert SHA(tp)==J(C/'qa_portability.json')['portable_tex_sha256']
    for name in ['全套题目与课件对应索引答案.csv','口算逐式与课件对应索引答案.csv']:cp(O/name,S/name)
    for name in ['图形索引答案.csv','保留原字形说明答案.json']:
        if(R/name).exists():cp(R/name,S/name)
    readme='''本版沿用题内红笔答案版式，第一页空白，共128页，无新增解析续页。本次仅将原书第3页四1（答案PDF第7页）按第一单元信息窗三改写：两幅分析图填写数量名称、数据和单位，保留原式与另法，补回顾检验。其他107个题页图像与上一版完全相同。
详细解析说明每空、每题的推理依据、数量关系、运算律及各方法思路；原处已有的完整脱式、答语、图形不再复制一遍。自然跨原书页的同一道题只在完整题处展开，详见总索引的“该题解法所在PDF页序”。
新增解析正文11.5pt，局部脱式10.5pt，本题原框内名称与单位8.5pt；公式实际由LaTeX编译。原题595pt宽及原字形保持，题间空间不足时仍纵向加长，按宽度阅读；缩印整张长页到单张A4会使字变小。
六册PPTX共2667张。本次同步第1册71、74、75、76张，依原课件形式改为原生可编辑树形图，已知量黑色、求得量红色；其余课件不变。完整算式为原生OMML并附实际LaTeX编译的SVG/PNG兼容分支。第1册全部426页timing保持原字节，受改4页实际经LibreOffice静态导出检查；未在PowerPoint逐项放映验证。
原题模糊或矛盾仍保留条件说明，包括第78页二4按字面B成立、D在具体岁数未给时也成立的限定，不能删去限定而当作唯一确定值。
数学推理及新增文字按分段记录核对；版面实际审阅范围和自动源文件/位置检查范围分别记录，不承诺绝对无误。原书末尾参考答案影印保留，与本次题内条件说明不一致时应结合题源核对使用。原扫描第66、70、77对应位置的页脚分别显示96、20、27，与前后连续页序不符，本版按已核对对应表显示66、70、77，原扫描图字节保留可追溯。第42、46页大题标题裁片按1:1移至上一题详解之后，避免前题解析越过下一道题。
'''
    (O/'交付与使用说明答案.txt').write_text(readme);(S/'交付与使用说明答案.txt').write_text(readme)
    source_readme='''源码以本次详细题内解析为活动版本。
1. detailed_layout/notes_A到D对应867条原题记录；latex/详细题内答案.tex为解析及局部脱式的XeLaTeX片段源，使用包内相对字体路径。项目根目录运行 xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex。
2. 从本次答案PDF恢复并重建：
   python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf
   python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf
恢复器核验原题条带并提取共同A4图层，新增详细解析不带回底本；保留原红答案和32处既有局部规范脱式、本题14个框内数量标注；同时把两处大题标题裁片恢复到原位。扫描异常页码按原图恢复，重建时由footer_overrides再次规范显示。base_local_targets记录这些既有局部公式的位置，重建时先恢复其纯底，避免同一笔画重复叠加。
3. figures与tikz中的284个图形源均为真正TikZ；保留原字形的3张图位于preserved_glyphs。索引区分原书页、原底本页、答案PDF页及PPT幻灯片序号。
4. Python依赖PyMuPDF和NumPy，公式编译需要XeLaTeX。源包附带已使用字体。源码检查中的绝对路径用于追溯实际工作环境；重建命令应在解压后的项目根目录执行。
5. 可用 detailed_layout/deduplicate_identical_jpegs.py 减少重复JPEG资源；该脚本必须独立比较所有页面。实际测试范围见checks/detailed_layout，编译、数学审阅、版面及无损优化分别记录。
6. 六册PPT沿用当前版本，相关原生成器及定点更正脚本仍位于ppt_builder。重新生成PPT需要相应Artifact Tool/Node环境；直接使用交付PPTX不需要这些开发工具。没有把LibreOffice静态检查称为PowerPoint放映验证。
'''
    (S/'源码使用说明答案.txt').write_text(source_readme)
    (S/'版本记录答案.json').write_text(json.dumps({'previous_pdf_sha256':'30e8400bcd5791a92149cb925072c7a06b123c74eb194ac764ee43e0768af60b','current_pdf_sha256':h,'change':'仅原书第3页四1按第一单元信息窗三的树形分析形式填写数量名称、数据、单位，并补回顾检验；第1册71/74/75/76同步，其他107题页不变。'},ensure_ascii=False,indent=2))
    files=[{'file':str(p.relative_to(S)),'bytes':p.stat().st_size,'sha256':SHA(p)}for p in sorted(S.rglob('*'))if p.is_file()]
    (S/'交付源码文件校验答案.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2))
    src=O/'小学四上同步素养卷LaTeX与TikZ源码答案.zip';sm=zip_checked(src,[(p,str(p.relative_to(S)))for p in sorted(S.rglob('*'))if p.is_file()])
    overall=O/'小学四上同步素养卷全套答案.zip';om=zip_checked(overall,[(p,p.name)for p in [pdf,idx,O/'口算逐式与课件对应索引答案.csv',O/'交付与使用说明答案.txt',src]]+[(p,'讲解课件/'+p.name)for p in ppts])
    out={'pdf':{'file':pdf.name,'bytes':pdf.stat().st_size,'sha256':h},'source_zip':sm,'overall_zip':om,'pages':128,'records':867,'detailed_notes':rel['visible_note_blocks'],'first_page_blank':True,'no_continuation_pages':True,'pptx':[{'file':p.name,'sha256':SHA(p)}for p in ppts]}
    (O/'delivery_manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
if __name__=='__main__':main()
