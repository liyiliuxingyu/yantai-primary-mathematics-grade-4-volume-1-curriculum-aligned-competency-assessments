"""Independent Q4-only source/math audit for the classroom choice B."""
from pathlib import Path
from fractions import Fraction
import argparse, hashlib, json, re, zipfile
HERE=Path(__file__).resolve().parent
if (HERE/'project/questions').is_dir():
    R=HERE;P=HERE/'project';Q=P/'q4_update';APPROVED=HERE/'approved_changes.json'
elif (HERE.parent/'questions').is_dir():
    P=HERE.parent;Q=HERE;R=HERE;APPROVED=HERE/'approved_changes.json'
else:raise RuntimeError('Cannot locate the active source project.')
def J(p):return json.loads(Path(p).read_text())
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-final',action='store_true');args=ap.parse_args();assert args.source_final,'Wait for SOURCE_READY.'
    Q.mkdir(exist_ok=True)
    approved=J(APPROVED);assert len(approved['changes'])==1 and approved['changed_keys']==['p078_s04'];change=approved['changes'][0]
    snapshot=Q/'baseline_source_snapshot.json';archive=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    if archive.exists():
        assert SHA(archive)==approved['baseline_source_zip_sha256']=='db83eab16570dc571836352c0a18ca7daf176c0c8e80bb0fd991dd651567d032'
        with zipfile.ZipFile(archive) as z:
            names=sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json|detailed_layout/notes_[ABCD]\.json|inline_layout/slots_[ABCD]\.json|题源核对与条件说明\.json',n))
            baseline={n:json.loads(z.read(n)) for n in names}
        W(snapshot,{'source_archive_sha256':SHA(archive),'files':baseline})
    else:baseline=J(snapshot)['files']
    current={n:J(P/n) for n in baseline}
    for n in baseline:
        if n.startswith(('questions/','detailed_layout/')):
            assert {k:v for k,v in baseline[n].items() if k!='records'}=={k:v for k,v in current[n].items() if k!='records'},n
    old={r['key']:r for n,d in baseline.items() if n.startswith('questions/') for r in d['records']}
    now={r['key']:r for n,d in current.items() if n.startswith('questions/') for r in d['records']}
    assert len(old)==len(now)==867 and set(now)==set(old)
    assert [k for k in now if now[k]!=old[k]]==['p078_s04']
    before=old['p078_s04'];after=now['p078_s04']
    assert before==change['old_record'] and after==change['new_record']
    assert {k:v for k,v in before.items() if k not in ['answer_latex','verification']}=={k:v for k,v in after.items() if k not in ['answer_latex','verification']}
    assert after['question_latex']==before['question_latex']
    assert 'D.无法确定丙的年龄。' in after['question_latex']
    oldnotes={r['key']:r for n,d in baseline.items() if n.startswith('detailed_layout/') for r in d['records']}
    notes={r['key']:r for n,d in current.items() if n.startswith('detailed_layout/') for r in d['records']}
    assert set(oldnotes)==set(notes)==set(now)
    assert [k for k in notes if notes[k]!=oldnotes[k]]==['p078_s04']
    assert oldnotes['p078_s04']==change['old_note'] and notes['p078_s04']==change['new_note']
    n0,n1=oldnotes['p078_s04'],notes['p078_s04']
    assert len(n0['local_replacements'])==len(n1['local_replacements'])==1
    a,b=n0['local_replacements'][0],n1['local_replacements'][0]
    assert {k:v for k,v in a.items() if k not in ['latex','reason']}=={k:v for k,v in b.items() if k not in ['latex','reason']}
    assert a['latex']==r'\(\mathrm{B,D}\)' and b['latex']==r'\(\mathrm{B}\)'
    active_text=after['answer_latex']+'\n'+n1['latex']+'\n'+b['latex']
    assert after['answer_latex'].startswith('B。') and '因此选B' in after['answer_latex']
    assert all(t in active_text for t in ['多6岁','少6岁','补给乙','丙也必须等于平均年龄'])
    assert 'D' not in active_text and all(t not in active_text for t in ['不唯一','歧义','无法确定','16,4,10','26,14,20'])
    assert set(re.findall(r'\d+',active_text))<={'6'},'Do not invent a concrete mean or age.'
    assert after['verification']['status']=='verified_for_instructional_intent'
    assert '未据此推定任何具体岁数' in after['verification']['reason']
    slot_checks=[]
    for n in baseline:
        if n.startswith('inline_layout/'):
            assert baseline[n]==current[n],n
            slot_checks.append({'file':n,'unchanged':True,'sha256':SHA(P/n)})
    assert len(slot_checks)==4
    summary='题源核对与条件说明.json';bs,cs=baseline[summary],current[summary]
    assert len(bs)==len(cs)
    assert [x for x in bs if x['编号']!='p078_s04']==[x for x in cs if x['编号']!='p078_s04']
    updated=next(x for x in cs if x['编号']=='p078_s04')
    assert updated['核对状态']=='verified_for_instructional_intent'
    assert '只选B' in updated['依据'] and '不推定丙的具体岁数' in updated['依据']
    assert '原题D选项文字保留' in updated['同步修改']
    # An exact symbolic linear identity, rather than relying on the old key.
    # Represent an age as (coefficient of m, constant) with rational coefficients.
    sub=lambda p,q:(p[0]-q[0],p[1]-q[1])
    total=(Fraction(3),Fraction(0));jia=(Fraction(1),Fraction(6));yi=(Fraction(1),Fraction(-6))
    bing=sub(sub(total,jia),yi);assert bing==(Fraction(1),Fraction(0))
    # Internal semantic limitation only: two valid means yield distinct concrete ages.
    examples=[]
    for m in [Fraction(10),Fraction(20)]:
        ages=(m+6,m-6,m);assert sum(ages)/3==m and ages[0]-m==6 and ages[1]-m==-6
        examples.append({'mean':str(m),'ages':[str(x) for x in ages]})
    assert examples[0]['ages'][2]!=examples[1]['ages'][2]
    report={
      'passed':True,'scope':'Only original page78 choice4: classroom answer B for the intended comparison with the mean. All other866 records and all layout slots unchanged.',
      'source_records_compared':867,'changed_question_keys':['p078_s04'],'other_records_unchanged':866,'changed_note_keys':['p078_s04'],
      'all_question_wording_options_diagrams_tables_conditions_unchanged':True,'original_option_D_preserved':True,
      'classroom_answer':'B','positive_primary_reason':'甲相对平均年龄多6岁，乙少6岁，多少相抵后两人都为平均年龄，丙也必须等于平均年龄。',
      'exact_symbolic_proof':{'assumption':'A=m+6, B=m-6, A+B+C=3m','derived_C':'m','linear_coefficients_of_C':[str(x) for x in bing]},
      'concrete_age_invented_in_classroom_content':False,'old_BD_removed_from_active_answer_note_and_local':True,
      'internal_semantic_limit':{'relationship_determined':True,'concrete_age_determined':False,'D_unconditionally_false_claimed':False,'interpretation':'按本题判断与平均年龄关系的教学意图，课堂只作B；若D问具体岁数，其语言语义仍有讨论空间。此项仅为内部审校，不加入课堂解析。','internal_examples_of_distinct_valid_ages':examples},
      'slot_checks':slot_checks,'condition_summary_only_Q4_entry_changed':True,
      'approved_changes_sha256':SHA(APPROVED),'source_files_sha256':{n:SHA(P/n) for n in current},'baseline_source_snapshot_sha256':SHA(snapshot),
      'source_final':True,'pdf_layout_tested_in_this_report':False,'native_powerpoint_playback_tested':False,
      'evidence':['approved_changes.json','baseline_source_snapshot.json','check_q4_math_independent.py'],
    }
    W(Q/'qa_math_independent.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='source_files_sha256'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
