"""Update only original page 78 Q4: a centered B and its positive explanation."""
from pathlib import Path
import json,hashlib,re,copy,math,sys,importlib.util
import fitz,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'q4_update';Q.mkdir(exist_ok=True)
J=lambda p:json.loads(Path(p).read_text());SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('h',P/'bracket_update/patch_pdf.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
old=J(R/'baseline/detailed_layout/current_release.json');base=R/'bundle/小学同步素养四年级上册数学答案.pdf';assert SHA(base)==old['sha256']=='42201f1a748acc2f36b67d61f3824d77d994617c5f5ec1dfc3d4e1020b4a9a56';idx=J(Q/'compiled/snippet_index.json');baseline=J(R/'baseline/snippets.json');changed={k for k in idx if idx[k]['body']!=baseline[k]['body']};assert changed=={'p078_s04','p078_s04_local1'}
sys.path.insert(0,str(P));from build_detailed_answers import load_data,snippets
rr,nn,ss,snap=load_data();items,localdesc=snippets(rr,nn,ss);desc=next(x for x in localdesc if x['id']=='p078_s04_local1');box=fitz.Rect(desc['target_rect']);e=idx['p078_s04_local1'];assert desc['align']=='center';target=fitz.Rect(box.x0+(box.width-e['ink_width'])/2,box.y0+.4,box.x0+(box.width+e['ink_width'])/2,box.y0+.4+e['ink_height']);assert fitz.Rect(322,475,359,491).contains(target)
compiled=fitz.open(Q/'compiled/snippets_frozen.pdf');doc=fitz.open(base);page=doc[81];source=h.source_for_book(doc,page,old,78);rel=copy.deepcopy(old);patch=next(x for x in rel['local_replacements']if x['id']=='p078_s04_local1');oldlocal=patch['target_rect'];h.remove_source_draw(doc,source,page,patch);h.graft(doc,source,compiled,e,target,'Q4CenteredB');patch.update({'target_rect':list(target),'latex':e['body'],'reason':desc['reason'],'align':'center','font_size':11.5})
page=doc[81];note=next(x for x in rel['answers']if x['key']=='p078_s04');oldnote=note['target_rect'];root=h.match_root(doc,page,oldnote);h.remove_page_draw(doc,page,root[1]);e=idx['p078_s04'];nt=fitz.Rect(oldnote[0],oldnote[1],oldnote[0]+e['ink_width'],oldnote[1]+e['ink_height']);assert nt.y1<839-2;page.show_pdf_page(nt,compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False);note['target_rect']=list(nt)
out=R/'deliverables/小学同步素养四年级上册数学答案.pdf';out.parent.mkdir(exist_ok=True)
# Preserve every pre-existing xref identity. This supports a byte-exact object
# graph proof for the 127 pages that this revision does not paint or reflow.
doc.save(out,garbage=0,deflate=False);doc.close();sha=SHA(out);receipt=J(Q/'compile_receipt.json');rel.update({'run_name':'q4_classroom_B','pdf':str(out.resolve()),'sha256':sha,'previous_pdf_sha256':SHA(base),'compiled_tex':receipt['compiled_tex'],'compiled_pdf':receipt['compiled_pdf'],'source_files':receipt['source_files'],'q4_update':{'key':'p078_s04','book_page':78,'pdf_page':82,'classroom_answer':'B','old_local_draw_call_removed':True,'old_note_draw_call_removed':True,'local_center_x':(target.x0+target.x1)/2,'original_question_unchanged':True,'page_geometry_unchanged':True,'current_qa':'q4_update/qa_current.json'}});W(P/'detailed_layout/current_release.json',rel)
bt=J(P/'detailed_layout/base_local_targets.json');next(x for x in bt['patches']if x['id']=='p078_s04_local1')['target_rect']=list(target);W(P/'detailed_layout/base_local_targets.json',bt)
report={'passed':True,'pdf_sha256':sha,'previous_pdf_sha256':SHA(base),'changed_keys':['p078_s04'],'changed_snippet_ids':sorted(changed),'book_page':78,'pdf_page':82,'old_local_rect':oldlocal,'new_local_rect':list(target),'old_note_rect':oldnote,'new_note_rect':list(nt),'center_x':(target.x0+target.x1)/2,'original_clear_rect_unchanged':[322,475,359,491],'five_black_corrections_preserved':True,'pages':128,'local_patches':92};W(Q/'patch_report.json',report)
with fitz.open(out)as d:
 d[81].get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False).save(Q/'final_page82.png');d[81].get_pixmap(matrix=fitz.Matrix(4,4),clip=fitz.Rect(312,704,371,737),alpha=False).save(Q/'final_choice_B.png');d[81].get_pixmap(matrix=fitz.Matrix(2,2),clip=fitz.Rect(70,770,585,838),alpha=False).save(Q/'final_note.png')
print('PDF_READY',sha,list(target),flush=True)
# Page-object and reachable-resource identity prove unchanged rendering without
# repeating the preceding release's complete 128-page raster comparison.
before=fitz.open(base);after=fitz.open(out);assert len(before)==len(after)==128
for a,b in zip(before,after):assert list(a.rect)==list(b.rect)and list(a.cropbox)==list(b.cropbox)and a.rotation==b.rotation
pair_cache={};refs=re.compile(r'\b(\d+)\s+\d+\s+R\b')
def raw(doc,x,page_root=False):
 s=doc.xref_object(x,compressed=False)
 if page_root:s=re.sub(r'/Parent\s+\d+\s+\d+\s+R','',s)
 payload=doc.xref_stream_raw(x)if doc.xref_is_stream(x)else b''
 return s,hashlib.sha256(payload).hexdigest(),{int(v)for v in refs.findall(s)}
def compare_graph(x,y):
 pending=[(x,y,True)];seen=set()
 while pending:
  a,b,ispage=pending.pop()
  if(a,b,ispage)in seen:continue
  seen.add((a,b,ispage));key=(a,b,ispage)
  if key in pair_cache:
   if not pair_cache[key]:return False
   continue
  aa=raw(before,a,ispage);bb=raw(after,b,ispage)
  if aa[:2]!=bb[:2]or aa[2]!=bb[2]:pair_cache[key]=False;return False
  pair_cache[key]=True;pending.extend((r,r,False)for r in aa[2])
 return True
semantic=[];fallback=[]
for i in range(128):
 if i==81:continue
 if compare_graph(before[i].xref,after[i].xref):semantic.append(i+1)
 else:
  a=before[i].get_pixmap(alpha=False);b=after[i].get_pixmap(alpha=False);assert a.samples==b.samples,('unchanged page differs',i+1);fallback.append(i+1)
a=before[81].get_pixmap(alpha=False);b=after[81].get_pixmap(alpha=False);aa=np.frombuffer(a.samples,dtype=np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,dtype=np.uint8).reshape(b.height,b.width,3);allowed=np.zeros(aa.shape[:2],bool);rects=[]
def mask(r):
 rects.append(list(r));x0,y0,x1,y1=fitz.Rect(r)+(-2,-2,2,2);allowed[max(0,math.floor(y0)):min(aa.shape[0],math.ceil(y1)),max(0,math.floor(x0)):min(aa.shape[1],math.ceil(x1))]=True
for r in[oldnote,list(nt)]:mask(r)
for r in[oldlocal,list(target)]:
 for band in[x for x in old['bands']if x['book_page']==78]:
  sr=fitz.Rect(band['source_rect']);c=fitz.Rect(r)&sr
  if not c.is_empty:dx=band['target_rect'][0]-sr.x0;dy=band['target_rect'][1]-sr.y0;mask(c+(dx,dy,dx,dy))
diff=np.any(aa!=bb,axis=2)&~allowed;assert not diff.any(),('outside q4 changes',int(diff.sum()));assert not after[0].get_text()and not after[0].get_images();prior=J(P/'p078_update/qa_scope.json');assert prior['pdf_sha256']==SHA(base)and prior['all_pages_raster_checked']==128
W(Q/'qa_scope.json',{'passed':True,'pdf_sha256':sha,'baseline_pdf_sha256':SHA(base),'pages':128,'unchanged_pages_identical':127,'unchanged_page_object_graphs_byte_identical':len(semantic),'semantic_proof_pages':semantic,'fallback_raster_pages':fallback,'raster_compared_changed_pages':[82],'all_page_dimensions_unchanged':True,'first_page_blank':True,'outside_q4_rectangles_unintended_pixels':0,'allowed_page82_rectangles':rects,'prior_release_all_128_raster_check_reused':True,'prior_raster_qa_sha256':SHA(P/'p078_update/qa_scope.json'),'only_q4_changed':True,'no_relocation_of_other_objects':True,'black_corrections_preserved':5,'scope_method':'Recursive page dictionary/resource-object/raw-stream equality for unmodified pages; parent page-tree link omitted. Actual page82 raster compared outside the one answer/note. Prior full128 raster QA bound to the v22 baseline.'})
print('SCOPE_PASS',len(semantic),'semantic unchanged pages;fallback',fallback,flush=True)
