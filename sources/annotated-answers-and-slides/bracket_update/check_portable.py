from pathlib import Path
import json,hashlib,subprocess,fitz
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'bracket_update';out=Q/'portable';out.mkdir(exist_ok=True)
j=json.loads((Q/'compile_receipt.json').read_text());s=Path(j['compiled_tex']).read_text().replace(str(P/'recovered/source/new_work'),'recovered/source/new_work');tex=out/'详细题内答案.tex';tex.write_text(s)
p=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(out),str(tex)],cwd=P,capture_output=True,text=True);(out/'compile.stdout.log').write_text(p.stdout+p.stderr)
assert p.returncode==0,p.stdout[-3000:]
for issue in ['Missing character:','Overfull \\hbox','Overfull \\vbox']:assert issue not in p.stdout,issue
doc=fitz.open(tex.with_suffix('.pdf'));assert len(doc)==j['snippets']
frozen=out/'snippets_frozen.pdf';frozen.write_bytes(doc.tobytes(garbage=3,deflate=True))
with fitz.open(frozen) as d:assert len(d)==j['snippets']
qa={'passed':True,'snippets':j['snippets'],'local_patches':j['local_patches'],'relative_font_path':True,'portable_tex_sha256':hashlib.sha256(s.encode()).hexdigest(),'missing_characters':0,'overfull_hbox':0,'overfull_vbox':0,'actual_xelatex_compile':True}
(Q/'qa_portability.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2));(P/'latex/详细题内答案.tex').write_text(s)
print('Portable',j['snippets'],'snippets compiled.',flush=True)
