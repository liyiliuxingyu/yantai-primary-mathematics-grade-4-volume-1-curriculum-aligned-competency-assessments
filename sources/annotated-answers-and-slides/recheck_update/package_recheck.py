"""Freeze already-reviewed artifacts after the parent's explicit READY message.

This program packages files and checks their identities; it neither solves math
nor renders presentations, and it never uploads. Historical QA stays historical.
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
B = R / 'baseline'
O = R / 'deliverables'
S = R / 'source_recheck_project'
Q = P / 'recheck_update'
AUDITS = [('reaudit_1_36.json', 1, 36, 327),
          ('reaudit_37_72.json', 37, 72, 278),
          ('reaudit_73_108.json', 73, 108, 262)]
INDEX_NAMES = ['全套题目与课件对应索引答案.csv', '口算逐式与课件对应索引答案.csv']
FORMULA_PARTS = {'formula', 'formulas', 'assets', 'math_assets',
                 'simplify_assets', 'recheck_assets', 'preserved_glyphs'}
MEDIA_SUFFIXES = {'.pdf', '.png', '.svg', '.jpg', '.jpeg', '.webp'}
SKIP_PARTS = {'__pycache__', 'node_modules', 'previews', 'validated', 'extracted',
              'actual_static_export', 'recovered_final', 'recovery', 'portable'}


def J(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def W(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def SHA(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def cp(src, dest):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def evidence(value):
    path = Path(value)
    candidates = [path] if path.is_absolute() else [P / path, R / path]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f'Current evidence missing: {value}')


def proof(qa, field, default):
    path = evidence(qa.get(field, default))
    data = J(path)
    assert data.get('passed') is True, f'Current proof not passed: {path}'
    return path, data


def zero(value):
    return value == 0 or value == []


def permitted(path, root):
    rel = path.relative_to(root)
    if rel.as_posix() == '交付源码文件校验答案.json':
        return False
    if any(part in SKIP_PARTS or part.startswith(('before_', 'after_', 'render_',
                                                'rendered_', 'reference_', 'actual_'))
           for part in rel.parts):
        return False
    if path.suffix.lower() in {'.log', '.aux', '.xdv', '.out', '.tmp', '.pptx', '.pyc'}:
        return False
    if path.name.endswith('.log.txt'):
        return False
    if len(rel.parts) >= 3 and rel.parts[:2] == ('detailed_layout', 'runs'):
        return path.suffix.lower() in {'.tex', '.json'}
    if path.suffix.lower() in MEDIA_SUFFIXES:
        return bool(set(rel.parts) & FORMULA_PARTS) and path.stat().st_size < 5 * 1024 * 1024
    return True


def audit_coverage(records):
    all_keys, reports, proposed = [], [], set()
    for name, lo, hi, count in AUDITS:
        data = J(R / name)
        pages, keys = [], []
        for row in data['coverage']:
            pages.append(row['book_page'])
            covered = next(row[k] for k in ['checked_keys', 'record_keys', 'reviewed_keys'] if k in row)
            assert len(covered) == row['record_count']
            assert all(int(k[1:4]) == row['book_page'] for k in covered)
            keys.extend(covered)
        assert sorted(pages) == list(range(lo, hi + 1)), name
        assert len(keys) == len(set(keys)) == count, name
        assert set(keys) == {k for k in records if lo <= int(k[1:4]) <= hi}, name
        proposed.update(c['key'] for c in data['changes'])
        all_keys.extend(keys)
        reports.append({'file': name, 'sha256': SHA(R / name), 'book_pages': [lo, hi],
                        'records_read': count, 'candidates': len(data['changes'])})
    assert len(all_keys) == len(set(all_keys)) == 867
    return reports, proposed


def source_scope(records, notes, accepted):
    """Exact baseline scope check, without pretending to be mathematical review."""
    old_records = {q['key']: q for f in sorted((B / 'questions').glob('p[0-9][0-9][0-9].json'))
                   for q in J(f)['records']}
    old_notes = {n['key']: n for letter in 'ABCD' for n in J(B / f'notes_{letter}.json')['records']}
    keys = set(accepted)
    assert records.keys() == old_records.keys() == notes.keys() == old_notes.keys()
    changed_r = {k for k in records if records[k] != old_records[k]}
    changed_n = {k for k in notes if notes[k] != old_notes[k]}
    assert changed_r == changed_n == keys, ('Source scope differs from adoption', changed_r ^ keys, changed_n ^ keys)
    for k in keys:
        old, new = old_records[k], records[k]
        assert {f: v for f, v in old.items() if f not in {'answer_latex', 'verification'}} == \
               {f: v for f, v in new.items() if f not in {'answer_latex', 'verification'}}, k
        ov, nv = old.get('verification', {}), new.get('verification', {})
        allowed_v = {'changes'} | ({'uncertainties'} if k == 'p074_s04' else set())
        assert {f: v for f, v in ov.items() if f not in allowed_v} == \
               {f: v for f, v in nv.items() if f not in allowed_v}, k
        assert nv.get('changes', [])[:len(ov.get('changes', []))] == ov.get('changes', []), k
        allowed_n = {'latex', 'reason', 'local_replacements'}
        assert {f: v for f, v in old_notes[k].items() if f not in allowed_n} == \
               {f: v for f, v in notes[k].items() if f not in allowed_n}, k
    old_count = sum(len(v.get('local_replacements', v.get('original_replacements', []))) for v in old_notes.values())
    new_count = sum(len(v.get('local_replacements', v.get('original_replacements', []))) for v in notes.values())
    assert old_count == 68 and new_count == 73
    changed_slots = []
    for letter in 'ABCD':
        old, new = J(B / f'slots_{letter}.json'), J(P / f'inline_layout/slots_{letter}.json')
        old_pages = old['pages'] if isinstance(old, dict) else old
        new_pages = new['pages'] if isinstance(new, dict) else new
        assert len(old_pages) == len(new_pages)
        for a, z in zip(old_pages, new_pages):
            if a != z:
                assert a['book_page'] == z['book_page'] == 75
                changed_slots.append(75)
                assert {f: v for f, v in a.items() if f != 'slots'} == {f: v for f, v in z.items() if f != 'slots'}
                for s, t in zip(a['slots'], z['slots']):
                    if s != t:
                        assert s['keys'] == t['keys'] == ['p075_s03'] and s['cut_y'] == 400 and t['cut_y'] == 410
                        assert {f: v for f, v in s.items() if f not in {'cut_y', 'reason'}} == \
                               {f: v for f, v in t.items() if f not in {'cut_y', 'reason'}}
    assert changed_slots == [75]
    return {'passed': True, 'records': 867, 'changed_question_keys': sorted(keys),
            'changed_note_keys': sorted(keys), 'unchanged_records': 867 - len(keys),
            'question_text_options_tables_diagrams_units_metadata_preserved': True,
            'local_patches_before': old_count, 'local_patches_after': new_count,
            'slot_change_book_page': 75,
            'scope': 'Exact source/baseline comparison only; not arithmetic, geometry, visual layout or animation proof.'}


def ppt_proofs(qa, decks):
    values = qa.get('ppt_qa_paths', qa.get('ppt_qa'))
    assert values, 'Current QA must identify PPT proofs'
    if isinstance(values, str):
        values = [values]
    if isinstance(values, dict):
        values = list(values.values())
    out, covered = [], set()
    for value in values:
        path = evidence(value)
        data = J(path)
        assert data.get('passed') is True, path
        assert data.get('powerpoint_playback_tested', False) is False
        items = data.get('volumes', [])
        if isinstance(items, dict):
            items = [dict(v, volume=int(k)) for k, v in items.items()]
        for item in items:
            number = int(item.get('volume', item.get('volume_number', 0)))
            assert number in decks, (path, number)
            h = item.get('output_sha256', item.get('sha256', item.get('pptx_sha256')))
            assert h and h == SHA(decks[number]), (path, number, 'PPT proof hash mismatch')
            covered.add(number)
        out.append({'path': str(path.relative_to(R)), 'sha256': SHA(path),
                    'volumes': sorted(int(x.get('volume', x.get('volume_number', 0))) for x in items)})
    assert covered == set(range(1, 7)), ('PPT proof coverage', covered)
    return out


def checked_zip(path, members):
    names = [name for _, name in members]
    assert len(names) == len(set(names)), 'Duplicate archive members'
    assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for src, name in members:
            z.write(src, name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.infolist()) == len(members)
        for src, name in members:
            h = hashlib.sha256()
            with z.open(name) as f:
                for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
                    h.update(block)
            assert h.hexdigest() == SHA(src), name
        assert all(i.flag_bits & 0x800 for i in z.infolist() if any(ord(c) > 127 for c in i.filename))
    return {'file': path.name, 'bytes': path.stat().st_size, 'sha256': SHA(path),
            'members': len(members), 'crc_checked': True, 'member_sha256_checked': True,
            'chinese_filenames_utf8_checked': True}


def main():
    assert not S.exists(), 'A fresh source_recheck_project stage is required'
    qa = J(Q / 'qa_current.json')
    assert qa.get('passed') is True, 'Current QA is not frozen/passed; wait for READY'
    assert qa.get('powerpoint_playback_tested', False) is False
    accepted_data = J(R / 'accepted_changes.json')
    changes = accepted_data['changes']
    accepted = sorted(c['key'] for c in changes)
    assert len(accepted) == len(set(accepted)) == 36
    kinds = Counter(c['kind'] for c in changes)
    assert kinds == {'simplification': 33, 'multiplication_mental_hint': 1,
                     'source_answer_conflict_clarification': 1, 'method_classification': 1}, kinds
    books = sorted({int(k[1:4]) for k in accepted})
    assert len(books) == 32 and books == sorted(qa['changed_book_pages'])
    release = J(P / 'detailed_layout/current_release.json')
    pdf = O / '小学同步素养四年级上册数学答案.pdf'
    pdf_sha = SHA(pdf)
    assert pdf_sha == release['sha256'] == qa['pdf_sha256']
    assert release['pages'] == 128 and release['question_pages'] == 108 and release['record_coverage'] == 867
    assert release['first_page_blank'] is True and release['separate_analysis_pages'] == 0
    assert len(release['local_replacements']) == 73
    import fitz
    with fitz.open(pdf) as doc:
        assert len(doc) == 128 and not doc[0].get_images() and not doc[0].get_text() and not doc[0].get_drawings()
    records = {q['key']: q for f in sorted((P / 'questions').glob('p[0-9][0-9][0-9].json')) for q in J(f)['records']}
    notes = {n['key']: n for letter in 'ABCD' for n in J(P / f'detailed_layout/notes_{letter}.json')['records']}
    assert len(records) == len(notes) == 867
    audits, proposed = audit_coverage(records)
    assert set(accepted) - proposed == {'p074_s04', 'p091_s03'}
    scope_source = source_scope(records, notes, accepted)
    assert '平均体重是15千克' in records['p074_s04']['question_latex']
    assert '选C' in records['p074_s04']['answer_latex']
    assert r'\times' in records['p070_s06']['answer_latex']
    scope_path, scope = proof(qa, 'scope_qa', 'recheck_update/qa_scope.json')
    assert scope['pdf_sha256'] == pdf_sha
    recovery_path, recovery = proof(qa, 'recovery_qa', 'recheck_update/qa_recovery.json')
    assert recovery['answer_sha256'] == pdf_sha and recovery['local_patches_retained'] == 73
    portable_path, portable = proof(qa, 'portability_qa', 'recheck_update/qa_portability.json')
    relative = portable.get('relative_font_path')
    assert relative is True or (isinstance(relative, str) and relative and not Path(relative).is_absolute())
    assert zero(portable.get('missing_characters', 0)) and zero(portable.get('overfull_hbox', 0))
    assert portable.get('local_patches', 73) == 73
    compiled_tex = evidence(release['compiled_tex'])
    compiled_pdf = evidence(release['compiled_pdf'])
    index_path = compiled_pdf.parent / 'snippet_index.json'
    index = J(index_path)
    assert len(index) == portable['snippets'] == 929 == release['visible_note_blocks'] + 73
    tex = compiled_tex.read_text(encoding='utf-8').replace(str(P / 'recovered/source/new_work'), 'recovered/source/new_work')
    assert str(P) not in tex
    assert hashlib.sha256(tex.encode()).hexdigest() == portable['portable_tex_sha256']
    inventory = J(P / 'ppt_builder/current_inventory.json')
    decks = {}
    for row in inventory['volumes']:
        number = int(row['volume']);deck = O / '讲解课件' / row['pptx']
        assert SHA(deck) == row['sha256']
        with zipfile.ZipFile(deck) as z:
            assert z.testzip() is None
            assert len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]) == row['slides']
        decks[number] = deck
    assert sorted(decks) == list(range(1, 7))
    ppt = ppt_proofs(qa, decks)
    # The numerical data and filled C remain unchanged while the conflict is clarified.
    with zipfile.ZipFile(R / 'bundle/讲解课件' / decks[5].name) as old, zipfile.ZipFile(decks[5]) as new:
        for slide in [33, 35]:
            part = f'ppt/slides/slide{slide}.xml'
            assert old.read(part) == new.read(part), f'p074_s04 protected slide {slide} changed'

    # All authoring is finished; the remaining writes only create the frozen package.
    roots = [P] + ([R / 'ppt_recheck'] if (R / 'ppt_recheck').is_dir() else [])
    snapshots = {(str(root), str(f.relative_to(root))): SHA(f) for root in roots
                 for f in sorted(root.rglob('*')) if f.is_file() and permitted(f, root)}
    S.mkdir()
    for f in sorted(P.rglob('*')):
        if f.is_file() and permitted(f, P):
            cp(f, S / f.relative_to(P))
    for name in ['版本记录答案.json', '交付与使用说明答案.txt', '源码使用说明答案.txt']:
        if (S / name).is_file():
            cp(S / name, S / 'checks/history/20261105_before_recheck' / name)
    for f in sorted(R.glob('*.py')):
        cp(f, S / 'recheck_update' / f.name)
    for f in sorted(R.glob('*.json')):
        if f.name.startswith(('reaudit_', 'qa_')) or f.name == 'accepted_changes.json':
            cp(f, S / 'recheck_update' / f.name)
    if (R / 'ppt_recheck').is_dir():
        for f in sorted((R / 'ppt_recheck').rglob('*')):
            if f.is_file() and permitted(f, R / 'ppt_recheck'):
                cp(f, S / 'ppt_recheck' / f.relative_to(R / 'ppt_recheck'))
    # Keep each current evidence path resolvable inside the source archive.
    for item in ppt:
        cp(R / item['path'], S / item['path'])
    for path in [scope_path, recovery_path, portable_path, Q / 'qa_current.json']:
        cp(path, S / path.relative_to(P))
    (S / 'latex').mkdir(exist_ok=True)
    (S / 'latex/详细题内答案.tex').write_text(tex, encoding='utf-8')
    cp(index_path, S / 'detailed_layout/snippet_index.json')
    save_scope = dict(scope_source, pdf_sha256=pdf_sha)
    W(S / 'recheck_update/package_source_scope.json', save_scope)
    for name in INDEX_NAMES:
        if not (O / name).is_file():
            cp(R / 'bundle' / name, O / name)
        cp(O / name, S / name)
    version = {'date': '2026-11-05', 'previous_pdf_sha256': release.get('previous_pdf_sha256'),
               'current_pdf_sha256': pdf_sha, 'changed_keys': accepted, 'changed_book_pages': books,
               'changes_by_kind': dict(kinds), 'audit_coverage': audits,
               'current_evidence': 'recheck_update/qa_current.json', 'ppt_evidence': ppt,
               'powerpoint_playback_tested': False,
               'source_conflict': '74页二4原图平均15千克，加入39千克，当前按题面保留C；若原平均为45千克则A。未据书后字母擅改原题。'}
    W(S / '版本记录答案.json', version)
    readme = (
        '本版共128页，第一页空白，红笔答案及解析继续写在题间，无新增解析续页。\n'
        '本轮再次核读原书1—108页867条记录，新增33处简算、1处乘法口算提示，并澄清74页题面/答案冲突、'
        '将91页复用主法总量的段落改称基准复核。前三单元保留原主法，在旁边补充学完运算律后的提示；第四单元从原书25页起优先简算。\n'
        '74页选择题第4题当前原扫描明确平均15千克，加入者39千克，按此条件应选C。若原平均应为45千克，则选A；原题15未被擅改。\n'
        '本轮检查范围见源码包recheck_update/qa_current.json及其引用证据。此前simplify_update、axis_update等检查保留为历史，不能当成本轮重新检查的证明。\n'
        '课件修改页已做实际静态渲染及对象/动画结构检查，未在PowerPoint或WPS中实际放映；长页整页缩印到单张A4时文字会变小。\n'
        '原书91页的原扫描页脚模糊，当前保留原图；该页按连续页序和题号索引定位，不据模糊字形改动题面数据。\n')
    (O / '交付与使用说明答案.txt').write_text(readme, encoding='utf-8')
    (S / '交付与使用说明答案.txt').write_text(readme, encoding='utf-8')
    (S / '源码使用说明答案.txt').write_text(
        '本次当前检查入口是recheck_update/qa_current.json。活动题源在questions，题内解析在detailed_layout/notes_A到D，'
        '当前课件哈希在ppt_builder/current_inventory.json；本轮课件补丁、公式兼容资产和QA在ppt_recheck及其metadata引用位置。\n'
        '此前simplify_update、axis_update、followup_style、style_patch及checks中的QA属于历史，除当前入口明确引用外不得冒称本轮结果。\n'
        'latex/详细题内答案.tex含929个实际编译片段（856段非空解析与73个局部替换），字体使用包内相对路径。项目根目录编译：\n'
        '  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex\n'
        '从当前交付答案PDF恢复源页并重建：\n'
        '  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf\n'
        '  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf\n'
        '重建源已包含本轮更正，重新组合图层可能出现细微抗锯齿差异，不承诺与交付PDF字节或像素完全相同。'
        '一次性升级脚本依赖对应旧PDF/PPTX，活动源已经更新，不要盲目再次执行旧补丁。\n'
        '公式采用真实数学排版；课件原生OMML及XeLaTeX生成的SVG/PNG兼容分支以当前PPT QA和实际导出的对象记录为准。'
        '必要的原字形图片保留于preserved_glyphs；本轮不改几何题图。Python需要PyMuPDF/NumPy，公式需要XeLaTeX。\n', encoding='utf-8')
    # Refuse a mixed snapshot if another worker wrote source after READY.
    after = {(str(root), str(f.relative_to(root))): SHA(f) for root in roots
             for f in sorted(root.rglob('*')) if f.is_file() and permitted(f, root)}
    assert snapshots == after, 'Source changed while packaging; do not deliver a mixed snapshot'
    files = [{'file': str(f.relative_to(S)), 'bytes': f.stat().st_size, 'sha256': SHA(f)}
             for f in sorted(S.rglob('*')) if f.is_file()]
    W(S / '交付源码文件校验答案.json', {'files': files})
    source_zip = O / '小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    sm = checked_zip(source_zip, [(f, str(f.relative_to(S))) for f in sorted(S.rglob('*')) if f.is_file()])
    full_zip = O / '小学四上同步素养卷全套答案.zip'
    basics = [pdf] + [O / n for n in INDEX_NAMES] + [O / '交付与使用说明答案.txt', source_zip]
    om = checked_zip(full_zip, [(f, f.name) for f in basics] +
                     [(decks[n], '讲解课件/' + decks[n].name) for n in sorted(decks)])
    assert om['members'] == 11
    report = {'pdf': {'file': pdf.name, 'bytes': pdf.stat().st_size, 'sha256': pdf_sha},
              'source_zip': sm, 'overall_zip': om, 'source_file_count': len(files) + 1,
              'pages': 128, 'records': 867, 'first_page_blank': True, 'no_added_pages': True,
              'accepted_changes': 36, 'changes_by_kind': dict(kinds), 'changed_book_pages': books,
              'local_patches': 73, 'compiled_snippets': 929, 'powerpoint_playback_tested': False,
              'pptx': [{'volume': n, 'file': f.name, 'bytes': f.stat().st_size, 'sha256': SHA(f)}
                       for n, f in sorted(decks.items())]}
    W(O / 'delivery_manifest.json', report);W(R / 'package_result.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
