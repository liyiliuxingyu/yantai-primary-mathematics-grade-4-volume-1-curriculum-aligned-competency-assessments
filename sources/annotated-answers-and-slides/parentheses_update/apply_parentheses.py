from pathlib import Path
import json,shutil,sys
R=Path(__file__).resolve().parent;P=R/'project';B=R/'baseline';Q=P/'parentheses_update';B.mkdir(exist_ok=True);Q.mkdir(exist_ok=True)
J=lambda p:json.loads(p.read_text())
def W(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
paths=['questions/p075.json','detailed_layout/notes_C.json','detailed_layout/current_release.json','detailed_layout/base_local_targets.json','ppt_builder/current_inventory.json']
for name in paths:
 f=B/name
 if not f.exists():f.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(P/name,f)
formula=r'\[\begin{aligned}&(720\times2)\div(12+8)\\={}&(720\times2)\div20\\={}&720\times(2\div2)\div10\\={}&720\div10\\={}&72\text{（米/分）}\end{aligned}\]'
note=r'列式先把总路程括成整体，再除以总时间。用时\(12+8=20\)分钟；简算时把\(20\)拆成\(2\times10\)，按乘除运算的性质先算\(2\div2\)，再用720除以10。两程用时不同，不能直接平均两段速度。'
d=J(B/'questions/p075.json');rec=next(x for x in d['records'] if x['key']=='p075_s03')
rec['answer_latex']=r'\textbf{总路程括成整体，再除以总时间}\par 来回总路程按每程720米乘2程列式，并用括号表示整体。简算时利用\(20=2\times10\)和乘除运算的性质，先算\(2\div2\)，再除以10。'+formula+'答：来回平均每分钟走72米。'
rec['verification']['changes'].append('按小学数量分析书写，将总路程(720×2)括成整体；简算按乘除运算性质写清变形依据。')
W(P/'questions/p075.json',d)
d=J(B/'detailed_layout/notes_C.json');n=next(x for x in d['records'] if x['key']=='p075_s03');n['latex']=note;n['reason']='本次仅补总路程整体括号并明确简算变形依据。';assert len(n['local_replacements'])==1
n['local_replacements'][0]['latex']=formula;n['local_replacements'][0]['reason']='总路程(720×2)加括号；原五行、字号及410pt插入白缝保留。'
W(P/'detailed_layout/notes_C.json',d)
W(Q/'change.json',{'key':'p075_s03','book_page':75,'id':'三、2','answer_pdf_page':79,'new_formula':formula,'new_note':note,'answer_unchanged':72,'unit':'米/分','clarification':'无括号的原式按乘除同级从左到右与加括号等值；本次依小学数量分析格式将总路程括成整体，随后明确运算性质的简算变形。','only_one_question_changed':True})
sys.path.insert(0,str(P));from build_detailed_answers import load_data,snippets,compile_fragments
records,notes,slots,snap=load_data();items,locals=snippets(records,notes,slots);out=Q/'compiled';out.mkdir(exist_ok=True)
compiled,index,tex=compile_fragments(items,out)
frozen=out/'snippets_frozen.pdf';frozen.write_bytes(compiled.tobytes(garbage=3,deflate=True))
import fitz
with fitz.open(frozen) as check:assert len(check)==len(items)
W(Q/'compile_receipt.json',{'snippets':len(items),'local_patches':len(locals),'compiled_tex':str(tex),'compiled_pdf':str(frozen),'source_files':snap})
print('Compiled',len(items),'snippets;',len(locals),'local patches',flush=True)
