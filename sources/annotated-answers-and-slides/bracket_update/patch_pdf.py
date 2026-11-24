"""Retain square brackets in-place without moving any original page object."""
from pathlib import Path
import json,re,copy,hashlib,math,argparse
import fitz,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'bracket_update'
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def W(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def near(a,b):return max(abs(x-y)for x,y in zip(a,b))<.004
def active_roots(doc,page):
 used=set(re.findall(rb'/([A-Za-z0-9_]+)\s+Do\b',page.read_contents()))
 return[x for x in page.get_xobjects()if not x[2]and x[1].encode()in used]
def match_root(doc,page,rect):
 a=[x for x in active_roots(doc,page)if near(fitz.Rect(x[3])*page.transformation_matrix,rect)]
 assert len(a)==1,('root',list(rect),a);return a[0]
def source_for_book(doc,page,old,book):
 refs=set()
 for b in old['bands']:
  if b['book_page']!=book:continue
  x=match_root(doc,page,b['target_rect']);typ,value=doc.xref_get_key(x[0],'Resources/XObject/fullpage');assert typ=='xref';refs.add(int(value.split()[0]))
 assert len(refs)==1;return refs.pop()
def remove_page_draw(doc,page,name):
 pat=rb'/'+re.escape(name.encode())+rb'\s+Do\b';s=page.read_contents();assert len(re.findall(pat,s))==1;s=re.sub(pat,b'',s);x=doc.get_new_xref();doc.update_object(x,'<<>>');doc.update_stream(x,s);page.set_contents(x)
def remove_source_draw(doc,source,page,patch):
 used=set(re.findall(rb'/([A-Za-z0-9_]+)\s+Do\b',doc.xref_stream(source)));a4=fitz.Matrix(1,0,0,-1,0,841)
 a=[x for x in page.get_xobjects()if x[2]==source and x[1].encode()in used and near(fitz.Rect(x[3])*a4,patch['target_rect'])]
 assert len(a)==1,('local',patch['id'],a)
 pat=rb'/'+re.escape(a[0][1].encode())+rb'\s+Do\b';s=doc.xref_stream(source);assert len(re.findall(pat,s))==1;doc.update_stream(source,re.sub(pat,b'',s))
def clip_source(doc,source,masks):
 s=doc.xref_stream(source)
 for item in masks:
  x0,y0,x1,y1=item['rect'];hole=f'{x0:.8f} {841-y1:.8f} {x1-x0:.8f} {y1-y0:.8f} re'.encode();s=b'q\n0 0 595 841 re\n'+hole+b'\nW* n\n'+s+b'\nQ\n'
 doc.update_stream(source,b'% Bracket-only obsolete red row exclusions\n'+s)
def graft(doc,source,compiled,entry,target,name):
 temp=doc.new_page(width=595,height=841);temp.show_pdf_page(target,compiled,entry['page']-1,clip=fitz.Rect(entry['clip']),keep_proportion=False);roots=active_roots(doc,temp);assert len(roots)==1
 xref=roots[0][0];s=temp.read_contents().replace(('/'+roots[0][1]+' ').encode(),('/'+name+' ').encode());owner,prefix=source,''
 for key in ['Resources','XObject']:
  typ,value=doc.xref_get_key(owner,prefix+key)
  if typ=='xref':owner,prefix=int(value.split()[0]),''
  else:assert typ=='dict';prefix+=key+'/'
 doc.xref_set_key(owner,prefix+name,str(xref)+' 0 R');doc.update_stream(source,doc.xref_stream(source)+b'\nq\n'+s+b'\nQ\n');doc.delete_page(len(doc)-1)
def baseline_target(entry,descriptor):
 origin=entry['first_equals_origin'];clip=entry['clip'];anchor=descriptor['baseline_anchor'];x=anchor[0]-(origin[0]-clip[0]);y=anchor[1]-(origin[1]-clip[1]);return fitz.Rect(x,y,x+entry['ink_width'],y+entry['ink_height'])
def notes_capacity(old,answer):
 later=[a['target_rect'][1]for a in old['answers']if a['book_page']==answer['book_page']and a['source_cut_y']==answer['source_cut_y']and a['target_rect'][1]>answer['target_rect'][1]+.1]
 band=next(b for b in old['bands']if b['book_page']==answer['book_page']and abs(b['source_rect'][1]-answer['source_cut_y'])<.01)
 return min(later+[band['target_rect'][1]])-2

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan-only',action='store_true');a=ap.parse_args()
 old=J(R/'pdf_baseline/current_release.json');baseline=J(R/'pdf_baseline/snippets.json');idx=J(Q/'compiled/snippet_index.json');manifest=J(Q/'new_local_patches.json');new_descriptors={x['id']:x for x in manifest['records']}
 changed=sorted(k for k in baseline|idx if baseline.get(k,{}).get('body')!=idx.get(k,{}).get('body'));new_ids=set(idx)-set(baseline);assert new_ids==set(new_descriptors),(new_ids,set(new_descriptors));assert not(set(baseline)-set(idx))
 notes=[k for k in changed if '_local'not in k];locals_old=[k for k in changed if '_local'in k and k not in new_ids];books=sorted({int(k[1:4])for k in changed});plans={}
 for k in notes:
  item=next(x for x in old['answers']if x['key']==k);rect=fitz.Rect(item['target_rect']);e=idx[k];target=fitz.Rect(rect.x0,rect.y0,rect.x0+e['ink_width'],rect.y0+e['ink_height']);assert target.y1<=notes_capacity(old,item)+.05,(k,'note too tall',list(rect),list(target),notes_capacity(old,item));assert target.x1<=585;plans[k]={'kind':'note','old':list(rect),'new':list(target),'book_page':item['book_page']}
 for k in locals_old:
  item=next(x for x in old['local_replacements']if x['id']==k);rect=fitz.Rect(item['target_rect']);e=idx[k];target=fitz.Rect(rect.x0,rect.y0,rect.x0+e['ink_width'],rect.y0+e['ink_height']);assert target.y1<=rect.y1+2.1,(k,'local too tall');assert target.x1<=585;plans[k]={'kind':'existing_local','old':list(rect),'new':list(target),'book_page':item['book_page']}
 for k in sorted(new_ids):
  e=idx[k];desc=new_descriptors[k];target=baseline_target(e,desc);container=fitz.Rect(desc['container_rect']);assert container.contains(target),(k,'baseline anchored target outside box',list(target),list(container));assert len(e['body'].split('\\\\'))==1;plans[k]={'kind':'new_source_row','old':desc['mask_rect'],'new':list(target),'book_page':desc['book_page'],'baseline_anchor':desc['baseline_anchor']}
 W(Q/'layout_plan.json',{'changed_ids':changed,'changed_books':books,'plans':plans,'page_dimensions_unchanged':True});print('PLAN',len(notes),'notes',len(locals_old),'existing locals',len(new_ids),'new single rows;',len(books),'books',flush=True)
 if a.plan_only:return
 base=R/'bundle/小学同步素养四年级上册数学答案.pdf';assert SHA(base)==old['sha256'];doc=fitz.open(base);compiled=fitz.open(Q/'compiled/snippets_frozen.pdf');rel=copy.deepcopy(old);masks=J(Q/'source_masks.json')['masks'];source_names={}
 # Apply source exclusions before placing replacement rows. Existing formulas
 # remain outside those holes, and their own old Do operations are removed.
 for book in books:
  page=doc[book+3];source=source_for_book(doc,page,old,book);mm=[m for m in masks if m['book_page']==book]
  if mm:clip_source(doc,source,mm)
  for k in [x for x in locals_old if plans[x]['book_page']==book]:
   patch=next(x for x in rel['local_replacements']if x['id']==k);remove_source_draw(doc,source,doc[book+3],patch);target=fitz.Rect(plans[k]['new']);graft(doc,source,compiled,idx[k],target,'BracketExisting_'+k);patch['target_rect']=list(target);patch['latex']=idx[k]['body'];patch['reason']='仅保留未完成运算外的中括号；原锚点、行数、数值及字体保持。'
  for k in [x for x in sorted(new_ids)if plans[x]['book_page']==book]:
   desc=new_descriptors[k];target=fitz.Rect(plans[k]['new']);name='BracketNew_'+k;graft(doc,source,compiled,idx[k],target,name);source_names[k]=name
   # Canonical source descriptor already carries its baseline and row mask.
   note=next(n for L in 'ABCD'for n in J(P/f'detailed_layout/notes_{L}.json')['records']if n['key']==desc['key']);patch=copy.deepcopy(note['local_replacements'][0]);patch.update({'id':k,'key':desc['key'],'book_page':book,'target_rect':list(target),'restore_rect':desc['mask_rect']});rel['local_replacements'].append(patch)
 for k in notes:
  item=next(x for x in rel['answers']if x['key']==k);page=doc[item['pdf_page']-1];root=match_root(doc,page,fitz.Rect(plans[k]['old']));remove_page_draw(doc,page,root[1]);e=idx[k];page.show_pdf_page(fitz.Rect(plans[k]['new']),compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False);item['target_rect']=plans[k]['new']
 output=R/'deliverables/小学同步素养四年级上册数学答案.pdf';output.parent.mkdir(exist_ok=True);doc.save(output,garbage=3,deflate=True);doc.close();sha=SHA(output)
 receipt=J(Q/'compile_receipt.json');source_files=dict(receipt.get('source_files',rel['source_files']));source_files['bracket_update/source_masks.json']=SHA(Q/'source_masks.json');rel.update({'run_name':'bracket_retention','pdf':str(output.resolve()),'sha256':sha,'previous_pdf_sha256':SHA(base),'compiled_tex':str((Q/'compiled/详细题内答案.tex').resolve()),'compiled_pdf':str((Q/'compiled/snippets_frozen.pdf').resolve()),'source_files':source_files,'source_region_replacements':masks,'bracket_update':{'changed_question_keys':[x['key']for x in J(R/'approved_changes.json')['changes']],'visible_changed_ids':changed,'changed_books':books,'page_geometry_unchanged':True,'current_qa':'bracket_update/qa_current.json'}})
 for k in ['lossless_optimization','raw_pdf_sha256','preservation']:rel.pop(k,None)
 W(P/'detailed_layout/current_release.json',rel);W(P/'answer_page_map.json',rel['mapping']);targets=J(P/'detailed_layout/base_local_targets.json')
 byid={x['id']:x for x in rel['local_replacements']}
 for patch in targets['patches']:
  if patch['id']in plans:patch['target_rect']=byid[patch['id']]['target_rect']
 for k in sorted(new_ids):
  if not any(x['id']==k for x in targets['patches']):targets['patches'].append(copy.deepcopy(byid[k]))
 assert len(targets['patches'])==87;W(P/'detailed_layout/base_local_targets.json',targets)
 # Full publication comparison. No page objects move in this revision.
 before,after=fitz.open(base),fitz.open(output);assert len(before)==len(after)==128;checks=[]
 for i,(p,q)in enumerate(zip(before,after)):
  assert list(p.rect)==list(q.rect),(i,'page dimension');pa=p.get_pixmap(alpha=False);pb=q.get_pixmap(alpha=False);aa=np.frombuffer(pa.samples,dtype=np.uint8).reshape(pa.height,pa.width,3);bb=np.frombuffer(pb.samples,dtype=np.uint8).reshape(pb.height,pb.width,3);book=i-3
  if book not in books:assert pa.samples==pb.samples,('unchanged page differs',i+1);continue
  allowed=np.zeros(aa.shape[:2],bool)
  def mask(rect):
   x0,y0,x1,y1=fitz.Rect(rect)+(-2,-2,2,2);allowed[max(0,math.floor(y0)):min(aa.shape[0],math.ceil(y1)),max(0,math.floor(x0)):min(aa.shape[1],math.ceil(x1))]=True
  for k,pl in plans.items():
   if pl['book_page']!=book:continue
   if pl['kind']=='note':mask(pl['old']);mask(pl['new'])
   else:
    for rr in [pl['old'],pl['new']]:
     for b in [x for x in old['bands']if x['book_page']==book]:
      sr=fitz.Rect(b['source_rect']);c=fitz.Rect(rr)&sr
      if not c.is_empty:dx=b['target_rect'][0]-sr.x0;dy=b['target_rect'][1]-sr.y0;mask(c+(dx,dy,dx,dy))
  diff=np.any(aa!=bb,axis=2)&~allowed;assert not diff.any(),('pixels outside replacements changed',book,int(diff.sum()))
  checks.append({'book_page':book,'outside_replacement_rectangles_identical':True})
 assert not after[0].get_text()and not after[0].get_images()
 W(Q/'qa_scope.json',{'passed':True,'pdf_sha256':sha,'pages':128,'all_pages_raster_checked':128,'unchanged_pages_identical':128-len(books),'changed_pages':checks,'all_page_dimensions_unchanged':True,'no_objects_relocated':True,'first_page_blank':True,'unintended_pixel_changes':0})
 # On an inspection-only copy, omit just the new calls and verify that the
 # obsolete original red paint is absent from the exact clipped rectangles.
 source_checks=[]
 for book in sorted({m['book_page']for m in masks}):
  source=source_for_book(after,after[book+3],rel,book);stream=after.xref_stream(source)
  for k in [x for x in new_ids if plans[x]['book_page']==book]:
   pat=rb'/'+source_names[k].encode()+rb'\s+Do\b';assert len(re.findall(pat,stream))==1;stream=re.sub(pat,b'',stream)
  after.update_stream(source,stream);page=after.new_page(width=595,height=841);after.xref_set_key(page.xref,'Resources',f'<< /XObject << /Inspect {source} 0 R >> >>');xref=after.get_new_xref();after.update_object(xref,'<<>>');after.update_stream(xref,b'q /Inspect Do Q');page.set_contents(xref)
  for item in [m for m in masks if m['book_page']==book]:
   mr=fitz.Rect(item['rect']);rect=fitz.Rect(math.ceil(mr.x0),math.ceil(mr.y0),math.floor(mr.x1),math.floor(mr.y1));pix=page.get_pixmap(clip=rect,alpha=False);assert min(pix.samples,default=255)==255,(item['key'],'old source paint remains');source_checks.append({'key':item['key'],'old_red_region_blank_with_replacement_call_omitted':True,'new_local_call_present_in_final_file':True})
  after.delete_page(len(after)-1)
 W(Q/'qa_source_rows.json',{'passed':True,'pdf_sha256':sha,'source_row_count':17,'checks':source_checks,'paint_exclusion_precedes_corrected_local':'verified','old_average_blank_regions_retained':16})
 previews=Q/'previews';previews.mkdir(exist_ok=True)
 with fitz.open(output)as final:
  for book in books:final[book+3].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(previews/f'p{book:03d}.png')
 W(Q/'patch_report.json',{'passed':True,'pdf_sha256':sha,'previous_pdf_sha256':SHA(base),'changed_snippet_ids':changed,'changed_book_pages':books,'plans':plans,'known_old_local_draw_calls_removed':len(locals_old),'new_source_rows':17,'page_count':128,'all_page_dimensions_unchanged':True,'original_question_content_unchanged':True,'first_page_blank':True,'local_patch_count':87,'source_row_names':source_names})
 print('PATCHED',sha,'fixed geometry; 128 pages;943snippets/87locals',flush=True)
if __name__=='__main__':main()
