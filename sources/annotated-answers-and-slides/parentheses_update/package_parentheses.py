"""Package the frozen p075_s03 parentheses correction only after root READY."""
from pathlib import Path
import json,hashlib,shutil,zipfile,re
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'parentheses_update';O=R/'deliverables';S=R/'source_parentheses_project'
INDEX_NAMES=['全套题目与课件对应索引答案.csv','口算逐式与课件对应索引答案.csv']
MEDIA={'.pdf','.png','.svg','.jpg','.jpeg','.webp'}
FORMULA={'formula','formulas','assets','math_assets','simplify_assets','recheck_assets','preserved_glyphs'}
SKIP={'__pycache__','node_modules','previews','validated','extracted','recovered_final','recovery','portable','compiled'}
def J(p):return json.loads(Path(p).read_text())
def W(p,j):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def SHA(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def cp(a,b):
 b=Path(b);b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
def evidence(v):
 p=Path(v)
 for x in ([p] if p.is_absolute() else [P/p,R/p]):
  if x.is_file():return x
 raise FileNotFoundError(v)
def proof(qa,key,default):
 p=evidence(qa.get(key,default));j=J(p);assert j.get('passed') is True,p;return p,j
def allowed(f):
 rel=f.relative_to(P)
 if rel.as_posix()=='交付源码文件校验答案.json':return False
 if any(x in SKIP or x.startswith(('before_','after_','render_','rendered_','actual_','reference_')) for x in rel.parts):return False
 if f.suffix.lower() in {'.log','.aux','.xdv','.out','.tmp','.pptx','.pyc'}:return False
 if rel.parts[:2]==('detailed_layout','runs'):return f.suffix.lower() in {'.tex','.json'}
 if f.suffix.lower() in MEDIA:return bool(set(rel.parts)&FORMULA) and f.stat().st_size<5*1024*1024
 return True
def source_scope():
 oldzip=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip';cr=[];cn=[];nrec=0
 with zipfile.ZipFile(oldzip) as z:
  for name in sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json',n)):
   a=json.loads(z.read(name));b=J(P/name);assert len(a['records'])==len(b['records'])
   for x,y in zip(a['records'],b['records']):
    nrec+=1;assert x['key']==y['key']
    if x==y:continue
    assert x['key']=='p075_s03';cr.append(x['key'])
    assert {k:v for k,v in x.items() if k not in {'answer_latex','verification'}}=={k:v for k,v in y.items() if k not in {'answer_latex','verification'}}
    xv,yv=dict(x['verification']),dict(y['verification']);xc=xv.pop('changes');yc=yv.pop('changes');assert xv==yv and yc[:len(xc)]==xc and len(yc)==len(xc)+1
  for L in 'ABCD':
   name=f'detailed_layout/notes_{L}.json';a=json.loads(z.read(name));b=J(P/name)
   assert len(a['records'])==len(b['records'])
   for x,y in zip(a['records'],b['records']):
    assert x['key']==y['key']
    if x==y:continue
    assert x['key']=='p075_s03';cn.append(x['key'])
    assert {k:v for k,v in x.items() if k not in {'latex','reason','local_replacements'}}=={k:v for k,v in y.items() if k not in {'latex','reason','local_replacements'}}
    assert len(x['local_replacements'])==len(y['local_replacements'])==1
    assert {k:v for k,v in x['local_replacements'][0].items() if k not in {'latex','reason'}}=={k:v for k,v in y['local_replacements'][0].items() if k not in {'latex','reason'}}
  for L in 'ABCD':
   name=f'inline_layout/slots_{L}.json';assert J(P/name)==json.loads(z.read(name))
 assert nrec==867 and cr==cn==['p075_s03']
 return {'passed':True,'records':nrec,'changed_question_keys':cr,'changed_note_keys':cn,'unchanged_records':866,'all_question_text_tables_diagrams_units_and_slots_preserved':True}
def checked_zip(dest,members):
 names=[n for _,n in members];assert len(names)==len(set(names))
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p,name in members:assert not Path(name).is_absolute() and '..' not in Path(name).parts;z.write(p,name)
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None and len(z.infolist())==len(members)
  for p,name in members:assert hashlib.sha256(z.read(name)).hexdigest()==SHA(p),name
  assert all(i.flag_bits&0x800 for i in z.infolist() if any(ord(c)>127 for c in i.filename))
 return {'file':dest.name,'bytes':dest.stat().st_size,'sha256':SHA(dest),'members':len(members),'crc_checked':True,'member_sha256_checked':True,'chinese_filenames_utf8_checked':True}
def main():
 assert not S.exists(),'Use a fresh source_parentheses_project stage'
 qa=J(Q/'qa_current.json');assert qa.get('passed') is True
 rel=J(P/'detailed_layout/current_release.json');pdf=O/'小学同步素养四年级上册数学答案.pdf';h=SHA(pdf);assert h==qa['pdf_sha256']==rel['sha256']
 assert rel['pages']==128 and rel['question_pages']==108 and rel['record_coverage']==867 and rel['visible_note_blocks']==856 and rel['separate_analysis_pages']==0 and len(rel['local_replacements'])==73
 import fitz
 with fitz.open(pdf) as d:assert len(d)==128 and not d[0].get_text() and not d[0].get_images() and not d[0].get_drawings()
 scope=source_scope();scope_path,scopeqa=proof(qa,'scope_qa','parentheses_update/qa_scope.json');assert scopeqa['pdf_sha256']==h
 recovery_path,recovery=proof(qa,'recovery_qa','parentheses_update/qa_recovery.json');assert recovery['answer_sha256']==h and recovery['local_patches_retained']==73
 portable_path,portable=proof(qa,'portability_qa','parentheses_update/qa_portability.json');assert portable.get('relative_font_path') and portable['snippets']==929 and portable.get('missing_characters',0) in [0,[]] and portable.get('overfull_hbox',0) in [0,[]]
 texpath=evidence(rel['compiled_tex']);compiled=evidence(rel['compiled_pdf']);idxpath=compiled.parent/'snippet_index.json';idx=J(idxpath);assert len(idx)==929
 tex=texpath.read_text().replace(str(P/'recovered/source/new_work'),'recovered/source/new_work');assert hashlib.sha256(tex.encode()).hexdigest()==portable['portable_tex_sha256']
 assert '(720\\times2)\\div(12+8)' in idx['p075_s03_local1']['body'] and '720\\times(2\\div2)\\div10' in idx['p075_s03_local1']['body']
 inv=J(P/'ppt_builder/current_inventory.json');decks={}
 for v in inv['volumes']:
  n=int(v['volume']);f=O/'讲解课件'/v['pptx'];assert SHA(f)==v['sha256'];decks[n]=f
  if n!=5:assert SHA(f)==SHA(R/'bundle/讲解课件'/f.name)
  with zipfile.ZipFile(f) as z:assert z.testzip() is None;assert len([x for x in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',x)])==v['slides']
 assert sorted(decks)==list(range(1,7))
 paths=qa.get('ppt_qa_paths',qa.get('ppt_qa',['ppt_parentheses/qa_final.json']));paths=[paths] if isinstance(paths,str) else paths;pptproof=[]
 for value in paths:
  path=evidence(value);j=J(path);assert j.get('passed') is True and not j.get('native_powerpoint_playback_tested',j.get('powerpoint_playback_tested',False))
  for v in j['volumes']:assert int(v['volume'])==5 and v['output_sha256']==SHA(decks[5])
  pptproof.append({'path':str(path.relative_to(R)),'sha256':SHA(path),'volumes':[5]})
 files=[f for f in sorted(P.rglob('*')) if f.is_file() and allowed(f)];before={str(f.relative_to(P)):SHA(f) for f in files};S.mkdir()
 for f in files:cp(f,S/f.relative_to(P))
 for name in ['版本记录答案.json','交付与使用说明答案.txt','源码使用说明答案.txt']:
  if (S/name).exists():cp(S/name,S/'checks/history/20261105_before_parentheses'/name)
 for f in R.glob('*.py'):cp(f,S/'parentheses_update'/f.name)
 cp(idxpath,S/'detailed_layout/snippet_index.json');(S/'latex/详细题内答案.tex').write_text(tex)
 for path in [scope_path,recovery_path,portable_path,Q/'qa_current.json']:cp(path,S/path.relative_to(P))
 for item in pptproof:cp(R/item['path'],S/item['path'])
 for name in INDEX_NAMES:
  if not (O/name).exists():cp(R/'bundle'/name,O/name)
  cp(O/name,S/name)
 W(S/'parentheses_update/package_source_scope.json',scope)
 W(S/'版本记录答案.json',{'date':'2026-11-05','previous_pdf_sha256':rel['previous_pdf_sha256'],'current_pdf_sha256':h,'changed_question_keys':['p075_s03'],'book_page':75,'pdf_page':79,'change':'总路程(720×2)括成整体，随后依据乘除性质简算；答案72米/分不变。','current_evidence':'parentheses_update/qa_current.json','ppt_proofs':pptproof,'powerpoint_playback_tested':False})
 readme=('本版共128页，第一页空白，答案及解析继续写在题内，无新增续页。\n'
 '本次只修改原书75页三、2（PDF第79页）：总路程写成(720×2)，再除以总时间(12+8)。随后利用20=2×10及乘除运算性质简算，结果仍为72米/分。第5册53张同步更新，其他题与另5册保持。\n'
 '当前检查入口为源码包parentheses_update/qa_current.json。此轮检查覆盖该题PDF版面及第5册52、53张实际静态渲染；动画结构保留并核对，未在PowerPoint/WPS中实际放映。此前recheck_update、simplify_update等记录为历史。\n'
 '前版第74页第4题原图平均15千克与书后A冲突的提示继续保留；本轮未改动该题的原始数据及按题面填写的C。\n'
 '长页整页缩印到单张A4时文字会变小。原书91页原扫描页脚模糊，按连续页序及题号索引定位。\n')
 (O/'交付与使用说明答案.txt').write_text(readme);(S/'交付与使用说明答案.txt').write_text(readme)
 (S/'源码使用说明答案.txt').write_text('当前入口：parentheses_update/qa_current.json。活动题源为questions，题内解析为detailed_layout/notes_A到D，当前课件哈希为ppt_builder/current_inventory.json。\n'
 'latex/详细题内答案.tex含929个实际编译片段（856条非空解析、73个局部替换），使用相对字体路径。项目根目录编译：\n  xelatex -interaction=nonstopmode -halt-on-error -output-directory latex latex/详细题内答案.tex\n'
 '从当前交付PDF恢复与重建：\n  python recover_detailed_base.py /path/to/小学同步素养四年级上册数学答案.pdf --output recovered/annotated_a4_128.pdf --pure-output recovered/pure_source_128.pdf\n  python build_detailed_answers.py --run-name rebuild --publish --input recovered/annotated_a4_128.pdf --pure-source recovered/pure_source_128.pdf\n'
 '本次补丁与QA在parentheses_update，课件公式及真实OMML/矢量兼容源在ppt_parentheses；历史记录保留供追溯，活动源已应用更正，不应盲目重跑一次性旧补丁。重新组合图层可能有抗锯齿差异，不承诺重建文件字节或像素相同。Python需要PyMuPDF/NumPy，公式需要XeLaTeX。\n')
 assert before=={str(f.relative_to(P)):SHA(f) for f in files},'Source changed during packaging'
 inventory=[{'file':str(f.relative_to(S)),'bytes':f.stat().st_size,'sha256':SHA(f)} for f in sorted(S.rglob('*')) if f.is_file()];W(S/'交付源码文件校验答案.json',{'files':inventory})
 source=O/'小学四上同步素养卷LaTeX与TikZ源码答案.zip';sm=checked_zip(source,[(f,str(f.relative_to(S))) for f in sorted(S.rglob('*')) if f.is_file()])
 full=O/'小学四上同步素养卷全套答案.zip';basic=[pdf]+[O/n for n in INDEX_NAMES]+[O/'交付与使用说明答案.txt',source];om=checked_zip(full,[(f,f.name) for f in basic]+[(decks[n],'讲解课件/'+decks[n].name) for n in sorted(decks)])
 assert om['members']==11
 report={'pdf':{'file':pdf.name,'sha256':h,'bytes':pdf.stat().st_size},'source_zip':sm,'overall_zip':om,'pages':128,'records':867,'changed_question_keys':['p075_s03'],'compiled_snippets':929,'local_patches':73,'ppt_changed_volume':5,'powerpoint_playback_tested':False,'pptx':[{'volume':n,'file':f.name,'sha256':SHA(f),'bytes':f.stat().st_size} for n,f in sorted(decks.items())]}
 W(O/'delivery_manifest.json',report);W(R/'package_result.json',report);print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
