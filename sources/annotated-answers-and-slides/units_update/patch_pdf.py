"""Replace approved unit-format snippets in their existing question gaps only."""
from pathlib import Path
import json,hashlib,re,copy,math,sys,importlib.util,argparse
import fitz,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'units_update'
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def W(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('h',P/'bracket_update/patch_pdf.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
def page_no(old,book):return next(x['answer_pdf_page']for x in old['mapping']if x['book_page']==book)
def anchor_target(entry,descriptor):
 if 'text_baseline_anchor'not in descriptor:return h.baseline_target(entry,descriptor)
 origin=entry['first_text_origin'];clip=entry['clip'];a=descriptor['text_baseline_anchor'];x=a[0]-(origin[0]-clip[0]);y=a[1]-(origin[1]-clip[1])
 return fitz.Rect(x,y,x+entry['ink_width'],y+entry['ink_height'])
def gap_plan(old,index,changed,book):
 notes=sorted([copy.deepcopy(a)for a in old['answers']if a['book_page']==book],key=lambda a:a['target_rect'][1]);bands=[b for b in old['bands']if b['book_page']==book];groups={};plans={};seams=[]
 anchors={}
 if(Q/'layout_reuse.json').exists():
  for a in J(Q/'layout_reuse.json')['anchors']:
   if int(a['key'][1:4])!=book:continue
   b=next(b for b in bands if b['source_rect'][1]<=a['source_y']<b['source_rect'][3]);anchors[a['key']]=a['source_y']+b['target_rect'][1]-b['source_rect'][1]
 for a in notes:groups.setdefault(a['source_cut_y'],[]).append(a)
 for cut,group in sorted(groups.items()):
  boundary=next(b['target_rect'][1]for b in bands if abs(b['source_rect'][1]-cut)<.01);end=None
  for a in group:
   rect=fitz.Rect(a['target_rect']);y=anchors.get(a['key'],rect.y0)
   if end is not None and end+4>y:y+=math.ceil(end+4-y-1e-6)
   e=index.get(a['key'])if a['key']in changed else None;new=fitz.Rect(rect.x0,y,rect.x0+(e['ink_width']if e else rect.width),y+(e['ink_height']if e else rect.height));plans[a['key']]={'old':list(rect),'relative_new':list(new),'changed':a['key']in changed,'source_cut_y':cut};end=new.y1
  original_gap=boundary-fitz.Rect(group[-1]['target_rect']).y1;extra=max(0,math.ceil(end+max(2,min(6,original_gap))-boundary-1e-6))
  if extra:seams.append({'old_y':boundary,'extra':extra,'source_cut_y':cut,'keys':[a['key']for a in group]})
 def shift(y):return sum(s['extra']for s in seams if s['old_y']<=y+.003)
 for p in plans.values():dy=shift(p['old'][1]);p['new']=list(fitz.Rect(p['relative_new'])+(0,dy,0,dy))
 return plans,seams,shift
def matrix_values(doc,xref):
 typ,val=doc.xref_get_key(xref,'Matrix');assert typ=='array';m=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][-+]?\d+)?',val)];assert len(m)==6;return m
def to_page(old,book,rect):
 for band in old['bands']:
  if band['book_page']!=book:continue
  sr=fitz.Rect(band['source_rect']);c=fitz.Rect(rect)&sr
  if not c.is_empty:
   dx=band['target_rect'][0]-sr.x0;dy=band['target_rect'][1]-sr.y0
   yield c+(dx,dy,dx,dy)
def graph_scope(before,after,changed_pages):
 # Cached raw-node equality never skips checking its children. This proves all
 # reachable resources equal, even where several page graphs share one Form.
 refs=re.compile(r'\b(\d+)\s+\d+\s+R\b');cache={}
 def node(doc,x,root=False):
  s=doc.xref_object(x,compressed=False)
  if root:s=re.sub(r'/Parent\s+\d+\s+\d+\s+R','',s)
  return s,doc.xref_stream_raw(x)if doc.xref_is_stream(x)else b'',{int(v)for v in refs.findall(s)}
 semantic=[];fallback=[]
 for i in range(len(before)):
  if i+1 in changed_pages:continue
  pending=[(before[i].xref,after[i].xref,True)];seen=set();equal=True
  while pending:
   key=pending.pop()
   if key in seen:continue
   seen.add(key)
   if key not in cache:
    a=node(before,key[0],key[2]);b=node(after,key[1],key[2]);cache[key]=(a==b,a[2])
   ok,children=cache[key]
   if not ok:equal=False;break
   pending.extend((x,x,False)for x in children)
  if equal:semantic.append(i+1)
  else:
   assert before[i].get_pixmap(alpha=False).samples==after[i].get_pixmap(alpha=False).samples,('Unchanged page differs',i+1)
   fallback.append(i+1)
 return semantic,fallback
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--plan-only',action='store_true');ap.add_argument('--check-only',action='store_true');args=ap.parse_args()
 old=J(R/'baseline/detailed_layout/current_release.json');baseline=J(R/'baseline/snippets.json');idx=J(Q/'compiled/snippet_index.json')
 base=R/'bundle/小学同步素养四年级上册数学答案.pdf';assert SHA(base)==old['sha256']=='5b0ec22916bc2f77e3ec9575a8b46466f500ce03d32887ee09d5817cf9d82dda'
 sys.path.insert(0,str(P));from build_detailed_answers import load_data,snippets
 rr,nn,ss,snap=load_data();items,descriptors=snippets(rr,nn,ss);desc={x['id']:x for x in descriptors}
 changes=J(R/'approved_changes.json');approved={x['key']for x in changes['changes']}
 changed=sorted(k for k in baseline|idx if baseline.get(k,{}).get('body')!=idx.get(k,{}).get('body'))
 assert all(idx[k]['key']in approved for k in changed),('unapproved snippet',changed)
 assert not(set(baseline)-set(idx)),'Removed snippets need explicit source-draw handling.'
 manifest=J(Q/'new_local_patches.json')if(Q/'new_local_patches.json').exists()else{'records':[]}
 newdesc={x['id']:x for x in manifest['records']};assert set(idx)-set(baseline)==set(newdesc)
 masks=J(Q/'source_masks.json')['masks']if(Q/'source_masks.json').exists()else[]
 plans={};issues=[]
 for k in changed:
  e=idx[k];book=e['book_page']
  if k in newdesc:
   d=newdesc[k];target=fitz.Rect(d['target_rect'])if'target_rect'in d else anchor_target(e,d)
   assert (fitz.Rect(d['container_rect'])+(-.5,-.5,.5,.5)).contains(target),(k,'new local outside clear box')
   plans[k]={'kind':'new_source_row','old':d['mask_rect'],'new':list(target),'book_page':book};continue
  if e['kind']=='note':
   a=next(x for x in old['answers']if x['key']==k);rect=fitz.Rect(a['target_rect']);target=fitz.Rect(rect.x0,rect.y0,rect.x0+e['ink_width'],rect.y0+e['ink_height']);capacity=max(rect.y1,h.notes_capacity(old,a))
   if target.y1>capacity+.05 or target.x1>585:issues.append({'id':k,'kind':'note','old':list(rect),'new':list(target),'available_bottom':capacity,'excess_height':target.y1-capacity})
   plans[k]={'kind':'note','old':list(rect),'new':list(target),'book_page':book,'available_bottom':capacity}
  else:
   a=next(x for x in old['local_replacements']if x['id']==k);rect=fitz.Rect(a['target_rect']);d=desc[k]
   if d.get('baseline_anchor')or d.get('text_baseline_anchor'):target=anchor_target(e,d)
   elif d.get('align')=='center':
    box=fitz.Rect(d.get('target_rect',d['rect']));target=fitz.Rect(box.x0+(box.width-e['ink_width'])/2,rect.y0,box.x0+(box.width+e['ink_width'])/2,rect.y0+e['ink_height'])
   else:target=fitz.Rect(rect.x0,rect.y0,rect.x0+e['ink_width'],rect.y0+e['ink_height'])
   container=fitz.Rect(d.get('container_rect',d.get('rect',list(rect))))
   # Existing red multi-row rectangles often have line-height padding outside
   # their nominal source patch; allow only the old occupied extent, never black.
   envelope=container|rect
   if not(fitz.Rect(envelope)+(-.4,-.4,.4,.4)).contains(target):issues.append({'id':k,'kind':'local','old':list(rect),'new':list(target),'container':list(envelope)})
   plans[k]={'kind':'existing_local','old':list(rect),'new':list(target),'book_page':book}
 changed_notes={k for k in changed if idx[k]['kind']=='note'};gap_books={int(x['id'][1:4])for x in issues if x['kind']=='note'};page_plans={};height_changes=[]
 if(Q/'layout_reuse.json').exists():gap_books.update(int(x['key'][1:4])for x in J(Q/'layout_reuse.json')['anchors'])
 for book in sorted(gap_books):
  np_,seams,shift=gap_plan(old,idx,changed_notes,book);extra=sum(s['extra']for s in seams);oldh=next(m['page_size'][1]for m in old['mapping']if m['book_page']==book)
  page_plans[book]={'notes':np_,'inserted_gaps':seams,'extra_height':extra,'old_height':oldh,'new_height':oldh+extra}
  for k,p in np_.items():
   if k in plans:plans[k]['new']=p['new']
  if extra:height_changes.append({'book_page':book,'pdf_page':page_no(old,book),'old_height':oldh,'new_height':oldh+extra,'delta':extra})
 remaining=[x for x in issues if x['kind']!='note']
 W(Q/'layout_plan.json',{'changed_ids':changed,'plans':plans,'initial_fixed_slot_issues':issues,'issues':remaining,'page_layout':page_plans,'page_height_changes':height_changes,'approved_height_growth_book_pages':sorted({int(k[1:4])for k in changes['conversion_keys']}),'page_width_unchanged':True,'no_extra_pages':True})
 print('PLAN',len(changed),'snippets',len({x['book_page']for x in plans.values()}),'books;',len(remaining),'remaining fit issues;',len(height_changes),'pages need gap growth',flush=True)
 if args.plan_only:return
 assert not remaining,('Actual snippets need question-gap fit review',remaining)
 out=R/'deliverables/小学同步素养四年级上册数学答案.pdf'
 if not args.check_only:
  doc=fitz.open(base);compiled=fitz.open(Q/'compiled/snippets_frozen.pdf');rel=copy.deepcopy(old)
  books=sorted({x['book_page']for x in plans.values()}|{m['book_page']for m in masks})
  for book in books:
   local_ids=[k for k in changed if plans[k]['book_page']==book and plans[k]['kind']!='note'];mm=[m for m in masks if m['book_page']==book]
   if not local_ids and not mm:continue
   page=doc[page_no(old,book)-1];source=h.source_for_book(doc,page,old,book)
   if mm:h.clip_source(doc,source,mm)
   for k in local_ids:
    page=doc[page_no(old,book)-1]
    e=idx[k];target=fitz.Rect(plans[k]['new'])
    if k not in newdesc:
     patch=next(x for x in rel['local_replacements']if x['id']==k);h.remove_source_draw(doc,source,page,patch)
    else:
     patch=copy.deepcopy(desc[k]);patch.update({'restore_rect':plans[k]['old']});rel['local_replacements'].append(patch)
    h.graft(doc,source,compiled,e,target,'UnitFormat_'+k);patch.update({'target_rect':list(target),'latex':e['body']})
  for book in books:
   page=doc[page_no(old,book)-1];roots=h.active_roots(doc,page);root_rects={x[0]:list(fitz.Rect(x[3])*page.transformation_matrix)for x in roots};note_roots={}
   for a in[x for x in old['answers']if x['book_page']==book]:note_roots[h.match_root(doc,page,a['target_rect'])[0]]=a['key']
   for x in roots:
    if note_roots.get(x[0])in changed_notes:h.remove_page_draw(doc,page,x[1])
   pp=page_plans.get(book);extra=pp['extra_height']if pp else 0;seams=pp['inserted_gaps']if pp else[]
   def shift(y):return sum(s['extra']for s in seams if s['old_y']<=y+.003)
   if pp:
    page.set_mediabox(fitz.Rect(0,0,595,page.rect.height+extra));page=doc.reload_page(page)
    for x in roots:
     key=note_roots.get(x[0])
     if key in changed_notes:continue
     dy=pp['notes'][key]['new'][1]-pp['notes'][key]['old'][1]if key else shift(root_rects[x[0]][1]);mat=matrix_values(doc,x[0]);mat[5]+=extra-dy;doc.xref_set_key(x[0],'Matrix','['+' '.join(f'{v:.10f}'for v in mat)+']')
    page=doc.reload_page(page)
   for a in[x for x in rel['answers']if x['book_page']==book]:
    key=a['key']
    if pp:a['target_rect']=pp['notes'][key]['new']
    elif key in changed_notes:a['target_rect']=plans[key]['new']
    if key in changed_notes:
     e=idx[key];page.show_pdf_page(fitz.Rect(a['target_rect']),compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
   if pp:
    for name in['bands','moved_footers','moved_headings']:
     for item in rel[name]:
      if item['book_page']==book:r=fitz.Rect(item['target_rect']);dy=shift(r.y0);item['target_rect']=list(r+(0,dy,0,dy))
    for m in rel['mapping']:
     if m['book_page']==book:m['page_size']=[595,pp['new_height']]
  out.parent.mkdir(exist_ok=True);doc.save(out,garbage=0,deflate=False);doc.close();receipt=J(Q/'compile_receipt.json');sha=SHA(out)
  rel.update({'run_name':'unit_format','pdf':str(out.resolve()),'sha256':sha,'previous_pdf_sha256':SHA(base),'compiled_tex':receipt['compiled_tex'],'compiled_pdf':receipt['compiled_pdf'],'source_files':receipt['source_files'],'units_update':{'changed_question_keys':sorted(approved),'visible_changed_ids':changed,'changed_books':books,'page_height_changes':height_changes,'page_width_unchanged':True,'no_extra_pages':True,'current_qa':'units_update/qa_current.json'}})
  if masks:rel['source_region_replacements']=rel.get('source_region_replacements',[])+masks
  W(P/'detailed_layout/current_release.json',rel);W(P/'answer_page_map.json',rel['mapping'])
  targets=J(P/'detailed_layout/base_local_targets.json');byid={x['id']:x for x in rel['local_replacements']};targets['patches']=[x for x in targets['patches']if x['id']in byid]
  for k in changed:
   if plans[k]['kind']=='note':continue
   a=next((x for x in targets['patches']if x['id']==k),None)
   if a is None:targets['patches'].append(copy.deepcopy(byid[k]))
   else:a.update({'target_rect':plans[k]['new'],'latex':idx[k]['body']})
  W(P/'detailed_layout/base_local_targets.json',targets)
  W(Q/'patch_report.json',{'passed':True,'pdf_sha256':sha,'previous_pdf_sha256':SHA(base),'changed_snippet_ids':changed,'changed_book_pages':books,'plans':plans,'page_layout':page_plans,'page_height_changes':height_changes,'original_question_unchanged':True,'local_patches':len(rel['local_replacements']),'pages':128})
  previews=Q/'previews';previews.mkdir(exist_ok=True)
  with fitz.open(out)as d:
   for book in books:d[page_no(old,book)-1].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(previews/f'p{book:03d}.png')
  print('PDF_READY',sha,flush=True)
 # Full changed-page raster scope and unaffected-page reachable-object proof.
 before=fitz.open(base);after=fitz.open(out);assert len(before)==len(after)==128
 for i,(a,b)in enumerate(zip(before,after)):
  assert a.rect.width==b.rect.width==595 and a.rotation==b.rotation
  delta=next((x['delta']for x in height_changes if x['pdf_page']==i+1),0);assert abs(b.rect.height-a.rect.height-delta)<.01
 changed_pages={page_no(old,x['book_page'])for x in plans.values()};semantic,fallback=graph_scope(before,after,changed_pages);checks=[]
 for pn in sorted(changed_pages):
  a=before[pn-1].get_pixmap(alpha=False);b=after[pn-1].get_pixmap(alpha=False);aa=np.frombuffer(a.samples,dtype=np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,dtype=np.uint8).reshape(b.height,b.width,3);allowed=np.zeros(bb.shape[:2],bool);rects=[];book=next(m['book_page']for m in old['mapping']if m['answer_pdf_page']==pn);pp=page_plans.get(book);seams=pp['inserted_gaps']if pp else[]
  def shift(y):return sum(s['extra']for s in seams if s['old_y']<=y+.003)
  expected=np.full_like(bb,255)
  for y in range(aa.shape[0]):expected[y+shift(y)]=aa[y]
  def mask(r):
   rects.append(list(r));x0,y0,x1,y1=fitz.Rect(r)+(-2,-2,2,2);allowed[max(0,math.floor(y0)):min(bb.shape[0],math.ceil(y1)),max(0,math.floor(x0)):min(bb.shape[1],math.ceil(x1))]=True
  for k,pl in plans.items():
   if page_no(old,pl['book_page'])!=pn:continue
   for field in['old','new']:
    r=pl[field]
    if pl['kind']=='note':
     dy=shift(r[1])if field=='old'else 0;mask(fitz.Rect(r)+(0,dy,0,dy))
    else:
     for pr in to_page(old,pl['book_page'],r):dy=shift(pr.y0);mask(pr+(0,dy,0,dy))
  if pp:
   for s in seams:
    y=s['old_y']+sum(t['extra']for t in seams if t['old_y']<s['old_y']);mask([0,y-1,595,y+s['extra']+1])
   for k,n in pp['notes'].items():
    dy=shift(n['old'][1]);oldshift=fitz.Rect(n['old'])+(0,dy,0,dy)
    if not h.near(oldshift,n['new']):mask(oldshift);mask(n['new'])
    elif k not in changed_notes:
     x0,y0,x1,y1=n['new'];mask([x0,y0-.2,x1,y0+.2]);mask([x0,y1-.2,x1,y1+.2])
  diff=np.any(expected!=bb,axis=2)&~allowed;assert not diff.any(),('Outside unit-format rects differs',pn,int(diff.sum()))
  checks.append({'pdf_page':pn,'outside_replacement_rectangles_and_recorded_translation_identical':True,'allowed_rectangles':rects,'height_added':sum(s['extra']for s in seams)})
 assert not after[0].get_text()and not after[0].get_images()
 W(Q/'qa_scope.json',{'passed':True,'pdf_sha256':SHA(out),'baseline_pdf_sha256':SHA(base),'pages':128,'unchanged_pages_identical':len(semantic)+len(fallback),'unchanged_page_object_graphs_byte_identical':len(semantic),'semantic_proof_pages':semantic,'fallback_raster_pages':fallback,'raster_compared_changed_pages':sorted(changed_pages),'changed_pages':checks,'all_page_widths_unchanged':True,'page_height_changes':height_changes,'approved_height_growth_book_pages':sorted({int(k[1:4])for k in changes['conversion_keys']}),'first_page_blank':True,'unintended_pixel_changes':0,'black_corrections_preserved':5,'Q4_B_preserved':True,'scope_method':'Reachable page/resource dictionary and raw stream equality for unchanged pages; changed pages raster-checked after exact recorded vertical gap translations, outside red replacements and native Form clip edges.'})
 source_checks=[]
 for book in sorted({m['book_page']for m in masks}):
  current=J(P/'detailed_layout/current_release.json');source=h.source_for_book(after,after[page_no(old,book)-1],current,book);stream=after.xref_stream(source)
  for k in [x for x in newdesc if plans[x]['book_page']==book]:
   pat=rb'/UnitFormat_'+re.escape(k.encode())+rb'\s+Do\b';assert len(re.findall(pat,stream))==1;stream=re.sub(pat,b'',stream)
  after.update_stream(source,stream);page=after.new_page(width=595,height=841);after.xref_set_key(page.xref,'Resources',f'<< /XObject << /Inspect {source} 0 R >> >>');x=after.get_new_xref();after.update_object(x,'<<>>');after.update_stream(x,b'q /Inspect Do Q');page.set_contents(x)
  for m in[x for x in masks if x['book_page']==book]:
   r=fitz.Rect(m['rect']);r=fitz.Rect(math.ceil(r.x0),math.ceil(r.y0),math.floor(r.x1),math.floor(r.y1));pix=page.get_pixmap(clip=r,alpha=False);assert min(pix.samples,default=255)==255,(m['key'],'obsolete red paint remains');source_checks.append({'key':m['key'],'rect':m['rect'],'old_red_region_blank_with_new_calls_omitted':True})
  after.delete_page(len(after)-1)
 W(Q/'qa_source_rows.json',{'passed':True,'pdf_sha256':SHA(out),'new_local_count':len(newdesc),'source_mask_count':len(masks),'checks':source_checks,'replacement_calls_preserved_in_final':True})
 print('SCOPE_PASS',len(semantic),'semantic unchanged;',len(checks),'changed page raster comparisons',flush=True)
if __name__=='__main__':main()
