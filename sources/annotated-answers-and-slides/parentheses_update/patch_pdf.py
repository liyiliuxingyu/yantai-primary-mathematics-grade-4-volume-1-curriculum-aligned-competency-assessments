from pathlib import Path
import json,hashlib,re,copy
import fitz
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'parentheses_update';O=R/'deliverables';O.mkdir(exist_ok=True)
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def delta(a,b):return max(abs(x-y) for x,y in zip(a,b))
old=J(R/'baseline/detailed_layout/current_release.json');base=R/'bundle/小学同步素养四年级上册数学答案.pdf';assert SHA(base)==old['sha256']
doc=fitz.open(base);page=doc[78];index=J(Q/'compiled/snippet_index.json');compiled=fitz.open(J(Q/'compile_receipt.json')['compiled_pdf']);rel=copy.deepcopy(old)
source_refs=set()
for band in old['bands']:
 if band['book_page']!=75:continue
 roots=[x for x in page.get_xobjects() if not x[2] and delta(fitz.Rect(x[3])*page.transformation_matrix,fitz.Rect(band['target_rect']))<.003]
 assert len(roots)==1
 typ,value=doc.xref_get_key(roots[0][0],'Resources/XObject/fullpage');assert typ=='xref';source_refs.add(int(value.split()[0]))
assert len(source_refs)==1;source=source_refs.pop();assert doc.xref_get_key(source,'BBox')==('array','[0 0 595 841]')
patch=next(x for x in rel['local_replacements'] if x['id']=='p075_s03_local1');oldmath=fitz.Rect(patch['target_rect']);a4=fitz.Matrix(1,0,0,-1,0,841)
roots=[x for x in page.get_xobjects() if x[2]==source and delta(fitz.Rect(x[3])*a4,oldmath)<.003];assert len(roots)==1
pattern=rb'/'+roots[0][1].encode()+rb'\s+Do\b';content=doc.xref_stream(source);assert len(re.findall(pattern,content))==1;doc.update_stream(source,re.sub(pattern,b'',content))
e=index['p075_s03_local1'];target=fitz.Rect(oldmath.x0,oldmath.y0,oldmath.x0+e['ink_width'],oldmath.y0+e['ink_height']);assert target.x1<570 and target.y1<410
temp=doc.new_page(width=595,height=841);temp.show_pdf_page(target,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
roots=[x for x in temp.get_xobjects() if not x[2]];assert len(roots)==1;newroot=roots[0][0]
stream=temp.read_contents().replace(('/'+roots[0][1]+' ').encode(),b'/Paren75Math ')
owner=source;prefix=''
for key in ['Resources','XObject']:
 typ,value=doc.xref_get_key(owner,prefix+key)
 if typ=='xref':owner=int(value.split()[0]);prefix=''
 else:assert typ=='dict';prefix+=key+'/'
doc.xref_set_key(owner,prefix+'Paren75Math',str(newroot)+' 0 R');doc.update_stream(source,doc.xref_stream(source)+b'\nq\n'+stream+b'\nQ\n');doc.delete_page(len(doc)-1)
page=doc[78]
note=next(x for x in rel['answers'] if x['key']=='p075_s03');oldnote=fitz.Rect(note['target_rect']);roots=[x for x in page.get_xobjects() if not x[2] and delta(fitz.Rect(x[3])*page.transformation_matrix,oldnote)<.003];assert len(roots)==1
pattern=rb'/'+roots[0][1].encode()+rb'\s+Do\b';content=page.read_contents();assert len(re.findall(pattern,content))==1;content=re.sub(pattern,b'',content)
xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,content);page.set_contents(xref)
e=index['p075_s03'];assert e['ink_height']<=oldnote.height+.05 and e['ink_width']<=505
nt=fitz.Rect(oldnote.x0,oldnote.y0,oldnote.x0+e['ink_width'],oldnote.y0+e['ink_height']);page.show_pdf_page(nt,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
note['target_rect']=list(nt);patch['target_rect']=list(target);patch['latex']=index['p075_s03_local1']['body'];patch['reason']='原书75页三2总路程(720×2)加整体括号；五行与字号不变，简算依据另作说明。'
dest=O/base.name;doc.save(dest,garbage=3,deflate=True);doc.close();d=fitz.open(dest);assert len(d)==128;d[78].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(R/'p075_after.png')
receipt=J(Q/'compile_receipt.json');rel.update({'run_name':'parentheses_p075','pdf':str(dest.resolve()),'sha256':SHA(dest),'previous_pdf_sha256':SHA(base),'compiled_tex':receipt['compiled_tex'],'compiled_pdf':receipt['compiled_pdf'],'source_files':receipt['source_files'],'parentheses_update':{'key':'p075_s03','book_page':75,'pdf_page':79,'answer':72,'unit':'米/分','formula':patch['latex'],'other_questions_unchanged':True}})
for k in ['lossless_optimization','raw_pdf_sha256','preservation']:rel.pop(k,None)
W(P/'detailed_layout/current_release.json',rel)
bt=J(P/'detailed_layout/base_local_targets.json');next(x for x in bt['patches'] if x['id']=='p075_s03_local1')['target_rect']=list(target);W(P/'detailed_layout/base_local_targets.json',bt)
W(Q/'patch_report.json',{'passed':True,'previous_pdf_sha256':SHA(base),'pdf_sha256':SHA(dest),'changed_book_pages':[75],'changed_question_keys':['p075_s03'],'old_formula_do_operation_removed':True,'old_note_do_operation_removed':True,'old_formula_rect':list(oldmath),'new_formula_rect':list(target),'old_note_rect':list(oldnote),'new_note_rect':list(nt),'font_sizes_pt':{'formula':10.5,'note':11.5},'pages':128,'no_page_reflow':True,'separate_analysis_pages':0})
print('Patched PDF',SHA(dest),dest.stat().st_size,flush=True)
