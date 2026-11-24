"""Compare current simplification edits with the frozen previous source.

This is a read-only content-scope check, not an arithmetic or visual review.
"""
from pathlib import Path
import copy
import hashlib
import json
from package_simplify import audit_coverage

R = Path(__file__).resolve().parent
P = R / 'project'
B = R / 'baseline'
OUT = R / 'qa_source_scope.json'


def J(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def without(data, *fields):
    return {k: v for k, v in data.items() if k not in fields}


def read_questions(root):
    pages, records, order = {}, {}, {}
    for path in sorted((root / 'questions').glob('p[0-9][0-9][0-9].json')):
        data = J(path)
        pages[path.name] = data
        keys = [item['key'] for item in data['records']]
        assert len(keys) == len(set(keys))
        order[path.name] = keys
        records.update({item['key']: item for item in data['records']})
    return pages, records, order


def read_notes(root):
    files, records, order = {}, {}, {}
    for letter in 'ABCD':
        path = root / f'detailed_layout/notes_{letter}.json'
        data = J(path)
        files[letter] = data
        keys = [item['key'] for item in data['records']]
        assert len(keys) == len(set(keys))
        order[letter] = keys
        records.update({item['key']: item for item in data['records']})
    return files, records, order


def local_entries(notes):
    return {key: copy.deepcopy(note.get('local_replacements', note.get('original_replacements', [])))
            for key, note in notes.items()}


def main():
    accepted_document = J(R / 'accepted_changes.json')
    accepted = {item['key']: item for item in accepted_document['changes']}
    assert len(accepted) == accepted_document['change_count'] == 56
    old_files, old_records, old_order = read_questions(B)
    new_files, new_records, new_order = read_questions(P)
    old_note_files, old_notes, old_note_order = read_notes(B)
    new_note_files, new_notes, new_note_order = read_notes(P)
    assert len(old_files) == len(new_files) == 108
    assert old_order == new_order
    assert old_note_order == new_note_order
    assert len(old_records) == len(new_records) == len(old_notes) == len(new_notes) == 867
    assert set(old_records) == set(new_records) == set(old_notes) == set(new_notes)
    audits, _ = audit_coverage(new_records)
    for name in old_files:
        assert without(old_files[name], 'records') == without(new_files[name], 'records'), name
    for letter in 'ABCD':
        assert without(old_note_files[letter], 'records') == without(new_note_files[letter], 'records'), letter
    question_changes = sorted(key for key in old_records if old_records[key] != new_records[key])
    answer_changes = sorted(key for key in old_records
                            if old_records[key]['answer_latex'] != new_records[key]['answer_latex'])
    note_changes = sorted(key for key in old_notes if old_notes[key] != new_notes[key])
    latex_note_changes = sorted(key for key in old_notes
                               if old_notes[key]['latex'] != new_notes[key]['latex'])
    assert question_changes == answer_changes == note_changes == latex_note_changes == sorted(accepted)
    patch_keys = set(accepted_document['local_replacement_keys'])
    changed_fields, early_preserved = {}, []
    for key in sorted(accepted):
        change = accepted[key]
        before, after = old_records[key], new_records[key]
        assert without(before, 'answer_latex', 'verification') == without(after, 'answer_latex', 'verification'), key
        bv, av = before.get('verification', {}), after.get('verification', {})
        assert without(bv, 'changes') == without(av, 'changes'), key
        assert av.get('changes', []) == bv.get('changes', []) + ['简便计算复核：' + change['why']], key
        assert new_notes[key]['latex'] == change['note_latex'], key
        assert new_notes[key]['reason'] == '本次简便计算复核：' + change['why'], key
        fields = {f for f in old_notes[key].keys() | new_notes[key].keys()
                  if old_notes[key].get(f) != new_notes[key].get(f)}
        allowed = {'latex', 'reason'}
        if key in patch_keys:
            allowed |= {'local_replacements', 'original_replacements'}
        assert fields <= allowed, (key, fields - allowed)
        changed_fields[key] = sorted(fields)
        if int(key[1:4]) < 25:
            expected = before['answer_latex'] + r'\par\textbf{简便提示（学完运算律后）}\par ' + change['simple_latex']
            assert after['answer_latex'] == expected, key
            early_preserved.append(key)
        else:
            assert after['answer_latex'] == change['answer_latex'], key
    old_local, new_local = local_entries(old_notes), local_entries(new_notes)
    actual_patch_keys = {key for key in old_notes if old_local[key] != new_local[key]}
    assert actual_patch_keys == patch_keys
    old_local_count = sum(len(v) for v in old_local.values())
    new_local_count = sum(len(v) for v in new_local.values())
    assert old_local_count == 61 and new_local_count == 68
    assert len(patch_keys) == 9
    assert len(early_preserved) == 19
    unchanged = set(old_records) - set(accepted)
    assert all(old_records[key] == new_records[key] and old_notes[key] == new_notes[key]
               for key in unchanged)
    inputs = [B / 'questions' / name for name in sorted(old_files)]
    inputs += [P / 'questions' / name for name in sorted(new_files)]
    inputs += [root / f'detailed_layout/notes_{letter}.json' for root in [B, P] for letter in 'ABCD']
    inputs.append(R / 'accepted_changes.json')
    report = {'passed': True, 'scope': 'Read-only comparison of all canonical question/answer records and in-question note records with the previous frozen version; not an arithmetic proof or visual QA.',
              'book_pages': 108, 'records': 867, 'audit_coverage': audits,
              'changed_book_pages': sorted({int(key[1:4]) for key in accepted}),
              'accepted_keys': sorted(accepted), 'accepted_change_count': len(accepted),
              'canonical_changed_keys': question_changes, 'answer_latex_changed_keys': answer_changes,
              'notes_changed_keys': note_changes, 'note_latex_changed_keys': latex_note_changes,
              'canonical_record_nonanswer_fields_unchanged_except_verification_changes_append': True,
              'verification_changes_exactly_one_append_per_accepted_key': True,
              'question_file_metadata_and_record_order_unchanged': True,
              'notes_file_metadata_and_record_order_unchanged': True,
              'unaccepted_811_canonical_and_note_records_deep_equal': len(unchanged) == 811,
              'early_original_answers_preserved_exactly': early_preserved,
              'early_original_answer_preservation_count': len(early_preserved),
              'changed_note_field_names': changed_fields,
              'old_local_replacement_count': old_local_count,
              'new_local_replacement_count': new_local_count,
              'changed_local_replacement_keys': sorted(actual_patch_keys),
              'local_replacement_count_increase': new_local_count - old_local_count,
              'input_files': [{'file': str(path.relative_to(R)), 'sha256': sha(path)} for path in inputs],
              'limitations': 'Does not assert that all answers are correct or all pages were visually inspected; mathematical, PDF layout and PPT animation checks are separate.'}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    dest = P / 'simplify_update/qa_source_scope.json'
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(OUT.read_bytes())
    print(json.dumps({k: report[k] for k in ['passed', 'book_pages', 'records', 'accepted_change_count',
          'early_original_answer_preservation_count', 'old_local_replacement_count',
          'new_local_replacement_count', 'local_replacement_count_increase']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
