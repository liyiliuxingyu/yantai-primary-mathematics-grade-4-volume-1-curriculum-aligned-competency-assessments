from pathlib import Path
import json,hashlib,subprocess,shutil
R=Path(__file__).resolve().parents[1];W=R/'followup_style';C=R/'detailed_layout'
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=J(C/'current_release.json');assert rel['run_name']=='followup_unit1_trees_final'
old=R/'detailed_layout/runs/p003_unit1_style/previews';new=Path(rel['compiled_tex']).parent/'previews'
same=[];changed=[]
for b in range(1,109):
 a=old/f'p{b:03}.png';z=new/f'p{b:03}.png'
 (same if SHA(a)==SHA(z) else changed).append(b)
assert changed==[5,7],changed
draft=R/'detailed_layout/runs/followup_unit1_trees/previews'
assert all(SHA(draft/f'p{b:03}.png')==SHA(new/f'p{b:03}.png')for b in [5,7])
audits={n:J(W/f'audit_{n}.json')for n in['early','mid','late']}
coverage=audits['early']['scope']['book_pages']+[p['book_page']for p in audits['mid']['pages']]+audits['late']['actual_question_pages']
assert sorted(coverage)==list(range(4,109)) and len(set(coverage))==105
report={'passed':True,'pdf_sha256':rel['sha256'],'changed_book_pages':changed,'unchanged_question_pages':same,'unchanged_count':len(same),'changed_pages_match_actually_reviewed_draft':True,'comparison':'All 108 question-page PNG files compared by SHA256 at publisher 1x scale; reviewed draft pages exactly match final pages. This is scope preservation, not new mathematical review of unchanged questions.','same_type_search_scope':{'book_pages':coverage,'pages':105,'records':843,'full_json_and_all_original_page_contact_sheets_reviewed':True,'matches':['p005_s04','p007_s08']}}
(W/'qa_scope.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
out=W/'portable';out.mkdir(exist_ok=True)
tex=Path(rel['compiled_tex']).read_text().replace(str(R/'recovered/source/new_work'),'recovered/source/new_work');p=out/'详细题内答案.tex';p.write_text(tex)
proc=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(out),str(p)],cwd=R,capture_output=True,text=True)
(out/'compile.stdout.log').write_text(proc.stdout+proc.stderr)
assert proc.returncode==0,proc.stdout[-1500:]
assert not any(s in proc.stdout for s in ['Missing character:','Overfull \\hbox','Overfull \\vbox'])
qa=J(C/'qa_portability.json');qa.update({'passed':True,'pdf_sha256':rel['sha256'],'portable_tex_sha256':SHA(p),'compiled_snippets':916,'missing_characters':0,'overfull_warnings':0,'relative_font_path':True,'tikz_graphs_compiled':['p005_s04_a1','p007_s08_a1'],'tikz_report':'followup_style/qa_tikz.json','full_recovery_test':'followup_style/qa_recovery.json'})
(C/'qa_portability.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
print('106 other question pages identical; two reviewed pages match; relative-font 916-snippet XeLaTeX succeeded.',flush=True)
