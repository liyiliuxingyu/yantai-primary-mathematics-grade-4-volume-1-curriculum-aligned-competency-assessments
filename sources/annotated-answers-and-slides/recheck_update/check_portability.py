from pathlib import Path
import hashlib,json,re,subprocess

R=Path(__file__).resolve().parent;P=R/'project';Q=P/'recheck_update';D=P/'detailed_layout/runs/recheck_20261105'
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
J=lambda p:json.loads(Path(p).read_text())
out=Q/'portable';out.mkdir(parents=True,exist_ok=True)
source=D/'详细题内答案.tex';source_sha=SHA(source)
index=J(D/'snippet_index.json');assert len(index)==929 and sum(x['kind']=='local' for x in index.values())==73
receipt=J(D/'receipt.json');assert receipt['sha256']=='729967db796d78605ca15b24eebb0b880ec8dbd13c84ef1e1744d1c11d33bff1'
absolute=str(P/'recovered/source/new_work');tex=source.read_text().replace(absolute,'recovered/source/new_work')
assert absolute not in tex and str(P) not in tex
portable=out/'详细题内答案.tex';portable.write_text(tex)
cmd=['xelatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(out),str(portable)]
proc=subprocess.run(cmd,cwd=P,capture_output=True,text=True)
(out/'compile.stdout.log').write_text(proc.stdout+proc.stderr)
log=portable.with_suffix('.log');log_text=log.read_text(errors='replace') if log.exists() else ''
messages={name:[line for line in (proc.stdout+'\n'+proc.stderr+'\n'+log_text).splitlines() if marker in line]
          for name,marker in [('missing_character_messages','Missing character:'),('overfull_hbox_messages','Overfull \\hbox'),('overfull_vbox_messages','Overfull \\vbox'),('latex_error_messages','! LaTeX Error:'),('font_error_messages','Package fontspec Error:')]}
import fitz
result=portable.with_suffix('.pdf');pdf_pages=len(fitz.open(result)) if result.exists() else 0
passed=(proc.returncode==0 and not any(messages.values()) and pdf_pages==929 and SHA(source)==source_sha)
report={'passed':passed,'snippets':929,'compiled_snippets':929,'local_patches':73,'relative_font_path':True,
        'font_path':'recovered/source/new_work/','font_sha256':SHA(P/'recovered/source/new_work/DroidSansFallback.ttf'),
        'portable_tex_sha256':SHA(portable),'original_compiled_tex_sha256':source_sha,
        'source_partial_pdf_sha256':receipt['sha256'],'missing_characters':len(messages['missing_character_messages']),
        'overfull_hbox':len(messages['overfull_hbox_messages']),'overfull_vbox':len(messages['overfull_vbox_messages']),
        **messages,'output_pdf_pages':pdf_pages,'compiler_exit_code':proc.returncode,
        'compiler':next((line for line in proc.stdout.splitlines() if line.startswith('This is XeTeX')),None),
        'compile_cwd':'project','command':'xelatex -interaction=nonstopmode -halt-on-error -output-directory=recheck_update/portable recheck_update/portable/详细题内答案.tex',
        'portable_tex':'recheck_update/portable/详细题内答案.tex','output_pdf_sha256':SHA(result) if result.exists() else None,
        'checks_scope':'Actually compiled all929 mathematical/explanatory snippets, including73 local patches, with the project root as cwd and a relative bundled-font path. This verifies compilation, missing characters and overflow; it is not independent mathematical, diagram or PDF-page visual review.'}
(Q/'qa_portability.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False),flush=True)
assert passed,'Portable compilation failed; see actual report and log'
