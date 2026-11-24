"""Correct only original book page 78 from its newly supplied clear photograph."""
from pathlib import Path
import json,re,copy,hashlib,math,argparse,importlib.util
import fitz,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'p078_update'
J=lambda p:json.loads(Path(p).read_text());SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def W(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
sp=importlib.util.spec_from_file_location('geometry_helpers',P/'bracket_update/patch_pdf.py');h=importlib.util.module_from_spec(sp);sp.loader.exec_module(h)
def capacity(old,answer):
 later=[a['target_rect'][1]for a in old['answers']if a['book_page']==78 and a['source_cut_y']==answer['source_cut_y']and a['target_rect'][1]>answer['target_rect'][1]+.1]
 band=next(b for b in old['bands']if b['book_page']==78 and abs(b['source_rect'][1]-answer['source_cut_y'])<.01)
 return min(later+[band['target_rect'][1]])-2

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan-only',action='store_true');a=ap.parse_args()
 old=J(R/'pdf_baseline/current_release.json');baseline=J(R/'pdf_baseline/snippets.json');idx=J(Q/'compiled/snippet_index.json');manifest=J(Q/'new_local_patches.json');new={x['id']:x for x in manifest['records']};new_ids=set(idx)-set(baseline)
 assert new_ids==set(new)and len(new_ids)==5;assert not(set(baseline)-set(idx));changed=sorted(k for k in baseline|idx if baseline.get(k,{}).get('body')!=idx.get(k,{}).get('body'));assert all(k.startswith('p078_')for k in changed),changed
 notes=[k for k in changed if '_local'not in k];assert not[k for k in changed if '_local'in k and k not in new_ids],'Existing answer/diagram local unexpectedly changed.'
 plans={}
 for k in notes:
  item=next(x for x in old['answers']if x['key']==k);rect=fitz.Rect(item['target_rect']);e=idx[k];target=fitz.Rect(rect.x0,rect.y0,rect.x0+e['ink_width'],rect.y0+e['ink_height']);limit=capacity(old,item)
  assert target.x1<=585;assert target.y1<=limit+.05,(k,'note needs concise wording',list(rect),list(target),limit)
  plans[k]={'kind':'note','old':list(rect),'new':list(target),'book_page':78}
 for k,desc in new.items():plans[k]={'kind':'black_source_correction','old':desc['mask_rect'],'new':desc['target_rect'],'book_page':78,'semantic_kind':desc['kind']}
 W(Q/'layout_plan.json',{'changed_ids':changed,'plans':plans,'book_page':78,'pdf_page':82,'page_dimensions_unchanged':True});print('PLAN',len(notes),'notes +5 black corrections; fixed page82 geometry',flush=True)
 if a.plan_only:return
 base=R/'bundle/小学同步素养四年级上册数学答案.pdf';assert SHA(base)==old['sha256'];compiled=fitz.open(Q/'compiled/snippets_frozen.pdf');doc=fitz.open(base);rel=copy.deepcopy(old);page=doc[81];source=h.source_for_book(doc,page,old,78);masks=J(Q/'source_masks.json')['masks'];assert len(masks)==5
 h.clip_source(doc,source,masks);names={};vector_checks=[]
 note_data={x['key']:x for L in'ABCD'for x in J(P/f'detailed_layout/notes_{L}.json')['records']}
 for k in sorted(new_ids):
  e=idx[k];assert not compiled[e['page']-1].get_images(),(k,'new correction must be vector');colors={s['color']for b in compiled[e['page']-1].get_text('dict')['blocks']for line in b.get('lines',[])for s in line['spans']};assert colors<={0},(k,colors)
  target=fitz.Rect(plans[k]['new']);name='P078Prompt_'+k;h.graft(doc,source,compiled,e,target,name);names[k]=name
  desc=new[k];ordinal=int(k.rsplit('_local',1)[1]);patch=copy.deepcopy(note_data[desc['key']]['local_replacements'][ordinal-1]);patch.update({'id':k,'key':desc['key'],'book_page':78,'target_rect':list(target),'restore_rect':desc['mask_rect']});rel['local_replacements'].append(patch);vector_checks.append({'id':k,'raster_images':0,'paint_color':'black','target_rect':list(target),'fit_to_original_ink_or_graph_rect':True})
 for k in notes:
  item=next(x for x in rel['answers']if x['key']==k);page=doc[81];root=h.match_root(doc,page,fitz.Rect(plans[k]['old']));h.remove_page_draw(doc,page,root[1]);e=idx[k];page.show_pdf_page(fitz.Rect(plans[k]['new']),compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False);item['target_rect']=plans[k]['new']
 output=R/'deliverables/小学同步素养四年级上册数学答案.pdf';output.parent.mkdir(exist_ok=True);doc.save(output,garbage=3,deflate=True);doc.close();sha=SHA(output);receipt=J(Q/'compile_receipt.json');source_files=dict(receipt.get('source_files',rel['source_files']));source_files['p078_update/source_masks.json']=SHA(Q/'source_masks.json')
 rel.update({'run_name':'p078_clear_photo_correction','pdf':str(output.resolve()),'sha256':sha,'previous_pdf_sha256':SHA(base),'compiled_tex':str((Q/'compiled/详细题内答案.tex').resolve()),'compiled_pdf':str((Q/'compiled/snippets_frozen.pdf').resolve()),'source_files':source_files,'source_region_replacements':old.get('source_region_replacements',[])+masks,'p078_update':{'book_page':78,'pdf_page':82,'changed_snippet_ids':changed,'black_corrections':manifest['records'],'photo_sha256':manifest['source_photo_sha256'],'page_dimensions_unchanged':True,'current_qa':'p078_update/qa_current.json'}})
 for k in ['lossless_optimization','raw_pdf_sha256','preservation']:rel.pop(k,None)
 W(P/'detailed_layout/current_release.json',rel);W(P/'answer_page_map.json',rel['mapping']);targets=J(P/'detailed_layout/base_local_targets.json');byid={x['id']:x for x in rel['local_replacements']}
 for k in sorted(new_ids):
  previous=next((x for x in targets['patches']if x['id']==k),None)
  if previous is None:targets['patches'].append(copy.deepcopy(byid[k]))
  else:previous.update(copy.deepcopy(byid[k]))
 assert len(targets['patches'])==92;W(P/'detailed_layout/base_local_targets.json',targets)
 # All unchanged pages remain identical; only the five source rectangles and
 # the explicitly changed red note objects may alter page 82.
 before,after=fitz.open(base),fitz.open(output);assert len(before)==len(after)==128;allowed_rects=[]
 for p,q in zip(before,after):assert list(p.rect)==list(q.rect)
 for i,(p,q)in enumerate(zip(before,after)):
  pa=p.get_pixmap(alpha=False);pb=q.get_pixmap(alpha=False)
  if i!=81:assert pa.samples==pb.samples,('unchanged page differs',i+1);continue
  aa=np.frombuffer(pa.samples,dtype=np.uint8).reshape(pa.height,pa.width,3);bb=np.frombuffer(pb.samples,dtype=np.uint8).reshape(pb.height,pb.width,3);allowed=np.zeros(aa.shape[:2],bool)
  def mask(rect):
   allowed_rects.append(list(rect));x0,y0,x1,y1=fitz.Rect(rect)+(-2,-2,2,2);allowed[max(0,math.floor(y0)):min(aa.shape[0],math.ceil(y1)),max(0,math.floor(x0)):min(aa.shape[1],math.ceil(x1))]=True
  for pl in plans.values():
   if pl['kind']=='note':mask(pl['old']);mask(pl['new'])
   else:
    for rr in[pl['old'],pl['new']]:
     for b in[x for x in old['bands']if x['book_page']==78]:
      sr=fitz.Rect(b['source_rect']);c=fitz.Rect(rr)&sr
      if not c.is_empty:dx=b['target_rect'][0]-sr.x0;dy=b['target_rect'][1]-sr.y0;mask(c+(dx,dy,dx,dy))
  diff=np.any(aa!=bb,axis=2)&~allowed;assert not diff.any(),('unexpected page82 pixels',int(diff.sum()))
 assert not after[0].get_text()and not after[0].get_images();W(Q/'qa_scope.json',{'passed':True,'pdf_sha256':sha,'pages':128,'all_pages_raster_checked':128,'unchanged_pages_identical':127,'changed_pages':[82],'book_page':78,'all_page_dimensions_unchanged':True,'first_page_blank':True,'no_extra_pages':True,'outside_authorized_replacements_unintended_pixels':0,'allowed_page82_rectangles':allowed_rects,'black_source_corrections_authorized_by_clear_photo':5})
 # Inspect a temporary in-memory A4 view without the five new paint calls.
 # Their exact former source regions must be blank, while the final file keeps
 # the corrected black vector objects. Historical 16 blank masks are unchanged.
 source=h.source_for_book(after,after[81],rel,78);stream=after.xref_stream(source)
 for k in sorted(new_ids):
  pat=rb'/'+names[k].encode()+rb'\s+Do\b';assert len(re.findall(pat,stream))==1;stream=re.sub(pat,b'',stream)
 after.update_stream(source,stream);page=after.new_page(width=595,height=841);after.xref_set_key(page.xref,'Resources',f'<< /XObject << /Inspect {source} 0 R >> >>');xref=after.get_new_xref();after.update_object(xref,'<<>>');after.update_stream(xref,b'q /Inspect Do Q');page.set_contents(xref);checks=[]
 for item in masks:
  rr=fitz.Rect(item['rect']);rect=fitz.Rect(math.ceil(rr.x0),math.ceil(rr.y0),math.floor(rr.x1),math.floor(rr.y1));pix=page.get_pixmap(clip=rect,alpha=False);assert min(pix.samples,default=255)==255,(item['replacement_local_id'],'old source paint remains');checks.append({'replacement_local_id':item['replacement_local_id'],'old_source_region_blank_when_new_call_omitted':True,'sampling_rect_inside_mask':list(rect),'corrected_call_present_in_final_file':True})
 W(Q/'qa_black_source_rows.json',{'passed':True,'pdf_sha256':sha,'checks':checks,'vector_checks':vector_checks,'old_source_paint_excluded':5,'new_black_corrected_local_calls_retained':5,'temporary_source_mutation_is_inspection_only':True})
 previews=Q/'previews';previews.mkdir(exist_ok=True)
 with fitz.open(output)as final:final[81].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(previews/'p078.png')
 W(Q/'patch_report.json',{'passed':True,'pdf_sha256':sha,'previous_pdf_sha256':SHA(base),'book_page':78,'pdf_page':82,'plans':plans,'changed_snippet_ids':changed,'source_names':names,'black_corrections':manifest['records'],'pages':128,'page82_size':old['mapping'][77]['page_size'],'other127_pages_identical':True,'first_page_blank':True,'local_patch_count':92,'source_region_replacements':22})
 print('PATCHED',sha,'only page82;948 snippets/92locals',flush=True)
if __name__=='__main__':main()
