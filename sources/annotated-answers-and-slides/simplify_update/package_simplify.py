"""Package the frozen, reviewed simplification edition; never run before READY.

This program verifies the parent's current evidence and packages already-made
files. It does not solve questions, render slides, rewrite release receipts, or
upload anything. The first run requires a fresh source_simplify_project folder.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

R = Path(__file__).resolve().parent
P = R / 'project'
O = R / 'deliverables'
S = R / 'source_simplify_project'
AUDITS = [('audit_early.json', 1, 24, 203),
          ('audit_25_44.json', 25, 44, 183),
          ('audit_45_64.json', 45, 64, 158),
          ('audit_65_84.json', 65, 84, 146),
          ('audit_85_108.json', 85, 108, 177)]
INDEX_NAMES = ['全套题目与课件对应索引答案.csv', '口算逐式与课件对应索引答案.csv']


def J(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def SHA(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def cp(src, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def evidence_path(value):
    """Resolve a current proof path without silently reusing historical proofs."""
    path = Path(value)
    candidates = [path] if path.is_absolute() else [P / path, R / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f'Current evidence is missing: {value}')


def proof(qa, field, default=None):
    value = qa.get(field, default)
    assert value, f'qa_current must identify {field}'
    path = evidence_path(value)
    data = J(path)
    assert data.get('passed') is True, f'Current proof not passed: {path}'
    return path, data


def checked_zip(path, members):
    names = [name for _, name in members]
    assert len(names) == len(set(names)), 'Duplicate ZIP members'
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for src, name in members:
            z.write(src, name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None, f'ZIP CRC failure: {path}'
        assert len(z.infolist()) == len(members)
        for src, name in members:
            with z.open(name) as f:
                h = hashlib.sha256()
                for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(chunk)
            assert h.hexdigest() == SHA(src), name
        assert all(info.flag_bits & 0x800 for info in z.infolist()
                   if any(ord(c) > 127 for c in info.filename)), 'Non-UTF8 Chinese ZIP name'
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': SHA(path),
            'members': len(members), 'crc_checked': True,
            'member_sha256_checked': True, 'chinese_filenames_utf8_checked': True}


def audit_coverage(records):
    """The audits have different schemas; all name their exact reviewed keys."""
    all_keys = []
    audit_info = []
    proposed = []
    for filename, lo, hi, count in AUDITS:
        data = J(R / filename)
        coverage = data.get('coverage', [])
        if coverage:
            keys, pages = [], []
            for item in coverage:
                pages.append(item['book_page'])
                row = next((item[k] for k in ['checked_keys', 'record_keys', 'reviewed_keys']
                            if k in item), None)
                assert row is not None, f'Missing audit record-key list in {filename}'
                assert len(row) == item['record_count']
                assert all(int(k[1:4]) == item['book_page'] for k in row)
                keys.extend(row)
        else:
            keys = data['covered_keys']
            pages = data['covered_pages']
        assert sorted(pages) == list(range(lo, hi + 1)), filename
        assert len(keys) == len(set(keys)) == count, filename
        expected = {k for k in records if lo <= int(k[1:4]) <= hi}
        assert set(keys) == expected, f'Audit missing or extra record: {filename}'
        all_keys.extend(keys)
        changes = data.get('changes', [])
        proposed.extend(item['key'] for item in changes)
        audit_info.append({'file': filename, 'sha256': SHA(R / filename),
                           'first_book_page': lo, 'last_book_page': hi,
                           'records_read': len(keys), 'proposed_changes': len(changes)})
    assert len(all_keys) == len(set(all_keys)) == 867
    assert set(all_keys) == set(records), 'Audits do not cover current canonical 867 records'
    return audit_info, set(proposed)


def accepted_changes():
    data = J(R / 'accepted_changes.json')
    if isinstance(data, list):
        items = data
    else:
        items = next((data[k] for k in ['changes', 'accepted_changes', 'records']
                      if k in data), None)
        if items is None:
            assert all(re.fullmatch(r'p\d{3}_s\d+', k) for k in data), 'Unknown adoption schema'
            items = data
        if isinstance(items, dict):
            items = [dict(value, key=key) for key, value in items.items()]
    assert isinstance(items, list) and items, 'Empty accepted change list'
    assert all(isinstance(item, dict) and 'key' in item for item in items)
    keys = [item['key'] for item in items]
    assert len(keys) == len(set(keys)), 'Duplicate accepted keys'
    return items


def source_allowed(path):
    rel = path.relative_to(P)
    if rel.as_posix() == '交付源码文件校验答案.json':
        return False
    if any(part in {'__pycache__', 'node_modules', 'previews', 'actual_static_export',
                    'validated'} for part in rel.parts):
        return False
    if path.suffix.lower() in {'.log', '.aux', '.xdv', '.out', '.tmp', '.pptx', '.pyc'}:
        return False
    if path.name.endswith('.log.txt'):
        return False
    # Keep current compiled TeX/receipt/index provenance, never large run PDFs.
    if len(rel.parts) >= 3 and rel.parts[:2] == ('detailed_layout', 'runs'):
        return path.suffix.lower() in {'.tex', '.json'}
    # Formula compatibility assets remain; large source PDFs and previews do not.
    if rel.parts[0] in {'axis_update', 'simplify_update'}:
        if any(part in {'compiled', 'recovered', 'recovered_final', 'recovery',
                        'portable', 'rendered', 'static'}
               or part.startswith(('before_', 'after_', 'render_', 'reference_',
                                   'actual_', 'compiled_'))
               for part in rel.parts[1:]):
            return False
        if path.suffix.lower() in {'.pdf', '.png', '.svg'}:
            return any(part in {'formula', 'formulas', 'assets', 'math_assets'} for part in rel.parts)
    return True


def new_ppt_source_allowed(path, root):
    rel = path.relative_to(root)
    if any(part in {'__pycache__', 'node_modules', 'validated', 'extracted'}
           or part.startswith(('before_', 'after_', 'render_', 'reference_', 'actual_'))
           for part in rel.parts):
        return False
    if path.suffix.lower() in {'.log', '.aux', '.out', '.xdv', '.tmp', '.pptx', '.pyc'}:
        return False
    if path.name.endswith('.log.txt'):
        return False
    if path.suffix.lower() in {'.png', '.pdf', '.svg', '.jpg', '.jpeg'}:
        return any(part in {'formula', 'formulas', 'assets', 'math_assets'} for part in rel.parts)
    return path.suffix.lower() in {'.py', '.mjs', '.js', '.json', '.md', '.txt', '.tex', '.ndjson'}


def copy_new_ppt_sources():
    for name in ['ppt', 'ppt_1_2']:
        root = R / name
        assert root.is_dir(), root
        for path in sorted(root.rglob('*')):
            if path.is_file() and new_ppt_source_allowed(path, root):
                cp(path, S / 'simplify_update' / name / path.relative_to(root))


def validate_ppt_evidence(qa, decks):
    """Package actual worker claims; never manufacture animation/playback proof."""
    values = qa.get('ppt_qa_paths', qa.get('ppt_qa'))
    assert values, 'qa_current must identify current PPT proof(s)'
    if isinstance(values, str):
        values = [values]
    elif isinstance(values, dict):
        values = list(values.values())
    assert isinstance(values, list)
    result = []
    checked_volumes = set()
    for value in values:
        path = evidence_path(value)
        data = J(path)
        assert data.get('passed') is True, path
        assert data.get('powerpoint_playback_tested', False) is False, \
            'This edition has not been played in PowerPoint; reconcile evidence'
        volumes = data.get('volumes', [])
        if isinstance(volumes, dict):
            volumes = [dict(v, volume=int(k)) for k, v in volumes.items()]
        for item in volumes:
            volume = int(item.get('volume', item.get('volume_number', 0)))
            assert volume in decks, (path, volume)
            h = item.get('output_sha256', item.get('sha256', item.get('pptx_sha256')))
            if h:
                assert h == SHA(decks[volume]), f'PPT proof hash mismatch: {path}, volume {volume}'
            checked_volumes.add(volume)
        result.append({'file': str(path.relative_to(R)), 'sha256': SHA(path),
                       'volumes': sorted(int(v.get('volume', v.get('volume_number', 0))) for v in volumes)})
    return result, checked_volumes


def main():
    assert not S.exists(), 'Fresh source stage required; do not overwrite a previous frozen stage'
    qa_path = P / 'simplify_update/qa_current.json'
    qa = J(qa_path)
    assert qa.get('passed') is True, 'Current simplification QA not frozen/passed'
    assert qa.get('powerpoint_playback_tested', False) is False
    release = J(P / 'detailed_layout/current_release.json')
    pdf = O / '小学同步素养四年级上册数学答案.pdf'
    h = SHA(pdf)
    assert h == release['sha256'] == qa['pdf_sha256'], 'Current PDF identity mismatch'
    assert release['pages'] == 128 and release['question_pages'] == 108
    assert release['record_coverage'] == 867
    assert release['first_page_blank'] is True and release['separate_analysis_pages'] == 0
    local_count = len(release['local_replacements'])
    records = {q['key']: q for p in sorted((P / 'questions').glob('p[0-9][0-9][0-9].json'))
               for q in J(p)['records']}
    notes = {n['key']: n for letter in 'ABCD'
             for n in J(P / f'detailed_layout/notes_{letter}.json')['records']}
    assert len(records) == len(notes) == 867
    assert '\\times' in records['p070_s06']['answer_latex']
    assert '判断正确' not in notes['p070_s06']['latex']
    for filename in ['final_answers.json', 'final_answers_c.json']:
        assert J(P / 'ppt_builder' / filename)['records']['p070_s06']['final_answers'][0]['answer_latex'] == r'\times'
    audits, proposed = audit_coverage(records)
    accepted = accepted_changes()
    accepted_keys = sorted(item['key'] for item in accepted)
    assert set(accepted_keys) <= set(records)
    assert set(accepted_keys) <= proposed, 'Accepted item outside supplied audit proposals'
    changed_pages = sorted({int(key[1:4]) for key in accepted_keys})
    assert sorted(qa['changed_book_pages']) == changed_pages
    for field in ['changed_question_keys', 'changed_note_keys', 'accepted_keys']:
        if field in qa:
            assert sorted(qa[field]) == accepted_keys, f'qa_current {field} differs from adoption list'
    source_scope_path, source_scope = proof(qa, 'source_scope_qa', 'simplify_update/qa_source_scope.json')
    assert source_scope['accepted_keys'] == accepted_keys
    for item in source_scope['input_files']:
        assert SHA(R / item['file']) == item['sha256'], f'Source changed after source-scope check: {item["file"]}'
    scope_path, scope = proof(qa, 'scope_qa', 'simplify_update/qa_scope.json')
    assert scope['pdf_sha256'] == h
    recovery_path, recovery = proof(qa, 'recovery_qa', 'simplify_update/qa_recovery.json')
    assert recovery['answer_sha256'] == h
    assert recovery['local_patches_retained'] == local_count
    portable_path, portable = proof(qa, 'portability_qa', 'simplify_update/qa_portability.json')
    if 'local_patches' in portable:
        assert portable['local_patches'] == local_count
    assert portable.get('relative_font_path') is True
    assert portable.get('missing_characters', 0) == 0
    assert portable.get('overfull_hbox', 0) == 0

    inventory = J(P / 'ppt_builder/current_inventory.json')
    decks = {}
    for volume in inventory['volumes']:
        number = int(volume['volume'])
        deck = O / '讲解课件' / volume['pptx']
        assert SHA(deck) == volume['sha256'], f'Current deck identity mismatch: {deck}'
        with zipfile.ZipFile(deck) as z:
            assert z.testzip() is None, f'Invalid PPTX ZIP: {deck}'
            actual_slides = [n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        assert len(actual_slides) == volume['slides'], deck
        decks[number] = deck
    assert sorted(decks) == list(range(1, 7))
    ppt_proofs, ppt_qa_volumes = validate_ppt_evidence(qa, decks)

    compiled_tex = evidence_path(release['compiled_tex'])
    compiled_pdf = evidence_path(release['compiled_pdf'])
    index_path = compiled_pdf.parent / 'snippet_index.json'
    index = J(index_path)
    snippet_count = len(index)
    assert snippet_count == portable['snippets']
    assert snippet_count == release['visible_note_blocks'] + local_count
    tex_text = compiled_tex.read_text(encoding='utf-8')
    tex_text = tex_text.replace(str(P / 'recovered/source/new_work'), 'recovered/source/new_work')
    assert str(P) not in tex_text, 'Portable TeX retains an absolute project path'
    assert hashlib.sha256(tex_text.encode()).hexdigest() == portable['portable_tex_sha256']
    assert '原句应判错' in index['p070_s06']['body']
    assert index['p070_s06_local1']['body'] == r'\(\times\)'

    # All checks above are read-only. Start the fresh source stage only now.
    S.mkdir()
    for path in sorted(P.rglob('*')):
        if path.is_file() and source_allowed(path):
            cp(path, S / path.relative_to(P))
    if (S / '版本记录答案.json').exists():
        cp(S / '版本记录答案.json', S / 'checks/history/20261103_版本记录答案.json')
    (S / 'latex/详细题内答案.tex').write_text(tex_text, encoding='utf-8')
    cp(index_path, S / 'detailed_layout/snippet_index.json')
    for path in sorted(R.glob('*.py')):
        cp(path, S / 'simplify_update' / path.name)
    for path in sorted(R.glob('*.json')):
        if (path.name.startswith(('audit_', 'qa_'))
                or path.name in {'accepted_changes.json', 'source_changes.json', 'pdf_patch_report.json'}):
            cp(path, S / 'simplify_update' / path.name)
    copy_new_ppt_sources()
    # Keep current QA's work-root-relative PPT proof links resolvable without
    # changing any original evidence bytes or duplicating the whole worker tree.
    for item in ppt_proofs:
        relative = Path(item['file'])
        if relative.parts[0] in {'ppt', 'ppt_1_2'}:
            cp(R / relative, S / relative)
            assert SHA(S / relative) == item['sha256']
    # Parent-authored final current QA/receipt files prevail over audit copies.
    for path in sorted((P / 'simplify_update').glob('*.json')):
        cp(path, S / 'simplify_update' / path.name)
    assert J(S / 'simplify_update/qa_current.json')['pdf_sha256'] == h
    for name in INDEX_NAMES:
        path = O / name
        if not path.is_file():
            cp(R / 'bundle' / name, path)
        cp(path, S / name)

    early_count = sum(int(key[1:4]) < 25 for key in accepted_keys)
    late_count = len(accepted_keys) - early_count
    version = {'date': '2026-11-04', 'previous_pdf_sha256': release.get('previous_pdf_sha256'),
               'current_pdf_sha256': h, 'changed_question_keys': accepted_keys,
               'changed_book_pages': changed_pages, 'accepted_changes': len(accepted_keys),
               'early_side_notes': early_count, 'unit4_onward_changes': late_count,
               'audit_coverage': audits, 'current_evidence': 'simplify_update/qa_current.json',
               'ppt_evidence': ppt_proofs, 'powerpoint_playback_tested': False,
               'scope': '本次遍历108页867条活动题目、答案及解析，专项检查简便计算；不能代替全册逐题重新综合数学复核或逐页人工排版检查。'}
    save(S / '版本记录答案.json', version)
    readme = (
        '本版保留原题题内红笔答案版式，共128页，第一页空白，无新增解析续页。\n'
        f'本次按原书页码检查第1—108页共867条题目、答案及解析，专项核对简便计算，采纳{len(accepted_keys)}条修订。'
        f'前三单元（原书1—24页）{early_count}条在原方法旁加简便提示；第四单元从原书25页开始，'
        f'之后{late_count}条优先采用合适的凑整、运算律、补偿或移多补少方法，并同步合理的另法。\n'
        '各题保留原书页码和题号；PDF文件页序、原书页码与PPT位置以两份题号索引为准。'
        '红笔答案和解析继续放在对应题目的间隙。题干、原图、对称轴虚线及前版已确认的更正保留。\n'
        '本次数学核读、实际查看PDF修改页和PPT静态渲染的范围分别记录在源码包simplify_update/qa_current.json及其引用文件。'
        '未在PowerPoint中放映测试，静态渲染与OOXML检查不能替代实际课堂软件中的动画播放测试。'
        '历史检查记录保留供追溯，不能当作本轮重新检查全册排版的证明。\n'
        '已有长页按原宽度阅读，整页缩印到单张A4时文字会变小。\n')
    for path in [O / '交付与使用说明答案.txt', S / '交付与使用说明答案.txt']:
        path.write_text(readme, encoding='utf-8')
    source_readme = f'''本包的questions、detailed_layout/notes_A到D、ppt_builder/final_answers、当前索引及latex为本次简便计算修订后的活动源文件。
本次检查的唯一当前入口是simplify_update/qa_current.json。其中ppt_qa_paths引用的两份QA在源码根目录保留同路径、同字节副本；两组完整课件修订源仍在simplify_update/ppt及simplify_update/ppt_1_2。axis_update、followup_style、style_patch及checks下的QA为此前版本历史，除当前入口明确引用外，不得当成本次重新测试的结果。
latex/详细题内答案.tex有{snippet_count}个实际编译片段（{release['visible_note_blocks']}段非空注释及{local_count}处局部替换），使用包内相对字体路径。项目根目录编译：
  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex
从本次交付答案PDF恢复原题底层并重建当前答案内容：
  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf
  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf
恢复器根据当前detailed_layout/current_release.json校验图层、题目位置及局部替换，当前活动源已包含本次修订。重新组合PDF图层可能出现细微抗锯齿差异；精确复现本次发行保留页面像素还依赖此前答案PDF及当前定点合成程序，历史输入大PDF未在源码包重复装入。不要声称任意重建文件与交付文件字节或像素完全相同。
simplify_update内包含本轮应用、合成、恢复、检查与打包程序、5份审查、采纳清单及独立复核。其余历史定点脚本用于从其对应旧版本升级到新版本，活动源已应用这些修改，不应盲目重复运行；个别一次性补丁仍依赖此前PDF或PPTX，输入路径和具体参数以各程序为准。
课件源与历史修正分别在ppt_builder、style_patch、followup_style、axis_update；本次两组课件修订源和公式资产在simplify_update/ppt及simplify_update/ppt_1_2。当前交付PPTX以本次inventory哈希为准，不能直接用旧生成器覆盖。普通文字保持可编辑，数学公式采用原生OMML及实际LaTeX生成的SVG/PNG兼容分支，具体保留范围见课件QA。实际做过静态渲染核对，未在PowerPoint中播放。
Python需要PyMuPDF和NumPy，公式需要XeLaTeX；包内保留284个真正TikZ图形源及必要原字形资产。本次简便计算不改变几何原图。
'''
    (S / '源码使用说明答案.txt').write_text(source_readme, encoding='utf-8')
    core = [str(path.relative_to(S)) for path in sorted(S.rglob('*')) if path.is_file()
            and (path.parts[len(S.parts)] in {'questions', 'detailed_layout', 'latex', 'ppt_builder'}
                 or path == S / 'simplify_update/qa_current.json')]
    save(S / 'simplify_update/package_source_freeze.json', {
        'records': 867, 'local_patches': local_count, 'compiled_snippets': snippet_count,
        'files': [{'file': name, 'sha256': SHA(S / name)} for name in core],
        'scope': 'Exact packaged active source hashes; this is not a mathematical proof.'})
    source_files = [{'file': str(path.relative_to(S)), 'bytes': path.stat().st_size, 'sha256': SHA(path)}
                    for path in sorted(S.rglob('*')) if path.is_file()]
    save(S / '交付源码文件校验答案.json', {'files': source_files})
    source_zip = O / '小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    sm = checked_zip(source_zip, [(path, str(path.relative_to(S)))
                                 for path in sorted(S.rglob('*')) if path.is_file()])
    full_zip = O / '小学四上同步素养卷全套答案.zip'
    base = [pdf] + [O / n for n in INDEX_NAMES] + [O / '交付与使用说明答案.txt', source_zip]
    om = checked_zip(full_zip, [(path, path.name) for path in base]
                     + [(decks[number], '讲解课件/' + decks[number].name) for number in sorted(decks)])
    report = {'pdf': {'file': pdf.name, 'bytes': pdf.stat().st_size, 'sha256': h},
              'source_zip': sm, 'overall_zip': om, 'source_file_count': len(source_files) + 1,
              'pages': 128, 'records': 867, 'first_page_blank': True, 'no_added_pages': True,
              'accepted_changes': len(accepted_keys), 'changed_book_pages': changed_pages,
              'early_side_notes': early_count, 'unit4_onward_changes': late_count,
              'local_patches': local_count, 'compiled_snippets': snippet_count,
              'ppt_qa_volumes': sorted(ppt_qa_volumes), 'powerpoint_playback_tested': False,
              'pptx': [{'volume': n, 'file': p.name, 'bytes': p.stat().st_size, 'sha256': SHA(p)}
                       for n, p in sorted(decks.items())]}
    save(O / 'delivery_manifest.json', report)
    save(R / 'package_result.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
