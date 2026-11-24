from pathlib import Path
import fitz,json,hashlib,re,shutil
R=Path(__file__).resolve().parent;P=R/'project';C=P/'detailed_layout';W=P/'axis_update';W.mkdir(exist_ok=True)
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=J(R/'baseline_receipt.json');original=R/'bundle/小学同步素养四年级上册数学答案.pdf';assert SHA(original)==rel['sha256']
out=R/'deliverables';out.mkdir(exist_ok=True);dest=out/original.name
compiled=fitz.open(W/'compiled/snippets_frozen.pdf');assert len(compiled)==917;index=J(W/'compiled/snippet_index.json');doc=fitz.open(original)
keys=['p065_s05','p070_s06','p070_s11','p085_s11'];changes=[]
for k in keys:
 a=next(a for a in rel['answers']if a['key']==k);page=doc[a['pdf_page']-1];old=fitz.Rect(a['target_rect']);e=index[k];assert e['ink_width']<=old.width+.01 and e['ink_height']<=old.height+.1,(k,old,e['ink_width'],e['ink_height'])
 roots=[x for x in page.get_xobjects()if not x[2]and max(abs(v-w)for v,w in zip(fitz.Rect(x[3])*page.transformation_matrix,old))<.002];assert len(roots)==1,(k,roots)
 name=roots[0][1];content=page.read_contents();pattern=rb'/'+name.encode()+rb'\s+Do\b';assert len(re.findall(pattern,content))==1
 content=re.sub(pattern,b'',content);xref=doc.get_new_xref();doc.update_object(xref,'<<>>');doc.update_stream(xref,content);page.set_contents(xref)
 target=fitz.Rect(old.x0,old.y0,old.x0+e['ink_width'],old.y0+e['ink_height']);page.show_pdf_page(target,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
 a['target_rect']=list(target);changes.append({'key':k,'old_note_rect':list(old),'new_note_rect':list(target),'pdf_page':a['pdf_page'],'font_pt':11.5})

# Patch only the common A4 source Form of book page70, so recovery retains
# this mark and rebuilding does not bring back the previous red check mark.
page=doc[73];refs=set()
# Delete the one old check mark's own drawing operation, using its source A4
# coordinates. Do not alter a shared font/glyph or the two neighboring checks.
deleted=[]
for f in page.get_fonts(full=True):
 if 'MSAM10'not in str(f):continue
 leaf=f[-1]
 if leaf in deleted:continue
 s=doc.xref_stream(leaf)or b''
 for m in re.finditer(rb'q\[\]0 d q 1 0 0 1 ([\d.]+) ([\d.]+) cm(.*?)ET Q Q',s,re.S):
  x,y=float(m[1])-72,841-float(m[2])-50.082
  if abs(x-500.006)<.002 and abs(y-231.87501)<.002 and b'[(X)]TJ'in m[3]:
   s=s[:m.start()]+s[m.end():];doc.update_stream(leaf,s);deleted.append(leaf);break
assert len(deleted)==1,'The one old check operation must be found exactly once.'
for b in rel['bands']:
 if b['book_page']!=70:continue
 tr=fitz.Rect(b['target_rect']);roots=[x for x in page.get_xobjects()if not x[2]and max(abs(v-w)for v,w in zip(fitz.Rect(x[3])*page.transformation_matrix,tr))<.002];assert len(roots)==1
 typ,value=doc.xref_get_key(roots[0][0],'Resources/XObject/fullpage');assert typ=='xref';refs.add(int(value.split()[0]))
assert len(refs)==1;source_xref=refs.pop()
num=lambda s:[float(x)for x in re.findall(r'[-+]?\d*\.?\d+',s)]
assert num(doc.xref_get_key(source_xref,'BBox')[1])==[0,0,595,841]
patch={'id':'p070_s06_local1','key':'p070_s06','book_page':70,'rect':[499.3,222.6,510.1,234.8],'restore_rect':[499.3,222.6,510.1,234.8],'latex':r'\(\times\)','font_size':10.5,'align':'center','valign':'center','clear_to_white':True,'kind':'judgment_correction','reason':'仅订正此题红勾，不改相邻题；黑色题干和括号均保留。'}
e=index[patch['id']];box=fitz.Rect(patch['rect']);target=fitz.Rect(box.x0+(box.width-e['ink_width'])/2,box.y0+(box.height-e['ink_height'])/2,box.x0+(box.width+e['ink_width'])/2,box.y0+(box.height+e['ink_height'])/2)
temp=doc.new_page(width=595,height=841);temp.draw_rect(box,color=None,fill=(1,1,1));temp.show_pdf_page(target,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
roots=[x for x in temp.get_xobjects()if not x[2]];assert len(roots)==1
stream=temp.read_contents().replace(('/'+roots[0][1]+' ').encode(),b'/AxisMark70 ')
owner=source_xref;prefix=''
for key in['Resources','XObject']:
 typ,val=doc.xref_get_key(owner,prefix+key)
 if typ=='xref':owner=int(val.split()[0]);prefix=''
 else:assert typ=='dict',(key,typ,val);prefix+=key+'/'
doc.xref_set_key(owner,prefix+'AxisMark70',str(roots[0][0])+' 0 R');doc.update_stream(source_xref,doc.xref_stream(source_xref)+b'\nq\n'+stream+b'\nQ\n');doc.delete_page(len(doc)-1)
patch['target_rect']=list(target);rel['local_replacements'].append(patch)
tempdest=dest.with_suffix('.tmp.pdf');doc.save(tempdest,garbage=3,deflate=True);doc.close();tempdest.replace(dest);d=fitz.open(dest);assert len(d)==128
for pg in[65,70,85]:d[pg+3].get_pixmap(matrix=fitz.Matrix(1,1)).save(R/f'p{pg:03}_after.png')
h=SHA(dest);rel.update({'run_name':'axis_line_precision','pdf':str(dest.resolve()),'sha256':h,'compiled_tex':str((W/'compiled/详细题内答案.tex').resolve()),'compiled_pdf':str((W/'compiled/snippets_frozen.pdf').resolve()),'previous_pdf_sha256':SHA(original),'source_files':{str(p.relative_to(P)):SHA(p)for p in[C/f'notes_{L}.json'for L in'ABCD']},'axis_precision_update':{'changed_book_pages':[65,70,85],'changed_note_keys':keys,'judgment_key':'p070_s06','judgment':'×','book_reference_agrees':True,'page_count_preserved':128}})
for k in ['lossless_optimization','raw_pdf_sha256','preservation']:rel.pop(k,None)
(C/'current_release.json').write_text(json.dumps(rel,ensure_ascii=False,indent=2));(P/'answer_page_map.json').write_text(json.dumps(rel['mapping'],ensure_ascii=False,indent=2))
bp=C/'base_local_targets.json';bt=J(bp);bt['patches'].append({'id':patch['id'],'target_rect':patch['target_rect']});bp.write_text(json.dumps(bt,ensure_ascii=False,indent=2))
(R/'pdf_patch_report.json').write_text(json.dumps({'pdf_sha256':h,'previous_pdf_sha256':SHA(original),'changed_notes':changes,'local_judgment_patch':patch,'old_check_drawing_operation_removed':True,'method':'Only four note Form placements replaced and one A4-local red judgment corrected; the old check drawing operation removed at its exact A4 coordinates; original question text, scans, all other page objects and page dimensions retained.','passed_fit_checks':True},ensure_ascii=False,indent=2))
print('Patched PDF',h,dest.stat().st_size,flush=True)
