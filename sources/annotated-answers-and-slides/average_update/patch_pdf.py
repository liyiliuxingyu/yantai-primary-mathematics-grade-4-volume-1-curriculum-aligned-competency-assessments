"""Precisely update changed answer objects, enlarging only existing page gaps."""
from pathlib import Path
import argparse, copy, hashlib, json, math, re
import fitz
import numpy as np

R = Path(__file__).resolve().parent
P = R / 'project'
Q = P / 'average_update'
J = lambda p: json.loads(Path(p).read_text())
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def near(a, b):
    return max(abs(x-y) for x, y in zip(a, b)) < .004


def root_objects(doc, page):
    used = set(re.findall(rb'/([A-Za-z0-9]+)\s+Do\b', page.read_contents()))
    return [x for x in page.get_xobjects() if x[2] == 0 and x[1].encode() in used]


def matching_root(doc, page, rect):
    matches = [x for x in root_objects(doc, page)
               if near(fitz.Rect(x[3])*page.transformation_matrix, rect)]
    assert len(matches) == 1, ('root match', list(rect), matches)
    return matches[0]


def remove_root_draw(doc, page, name):
    pattern = rb'/' + re.escape(name.encode()) + rb'\s+Do\b'
    content = page.read_contents()
    assert len(re.findall(pattern, content)) == 1, ('draw occurrence', name)
    content = re.sub(pattern, b'', content)
    x = doc.get_new_xref()
    doc.update_object(x, '<<>>')
    doc.update_stream(x, content)
    page.set_contents(x)


def source_for_book(doc, page, old, book):
    refs = set()
    for b in old['bands']:
        if b['book_page'] != book:
            continue
        root = matching_root(doc, page, fitz.Rect(b['target_rect']))
        typ, value = doc.xref_get_key(root[0], 'Resources/XObject/fullpage')
        assert typ == 'xref', (book, typ, value)
        refs.add(int(value.split()[0]))
    assert len(refs) == 1, (book, refs)
    return refs.pop()


def inject_source_patch(doc, source, old_patch, entry, compiled, new_name):
    """Drop the old invocation, then graft the newly compiled formula into A4."""
    a4 = fitz.Matrix(1, 0, 0, -1, 0, 841)
    old_rect = fitz.Rect(old_patch['target_rect'])
    page = doc[old_patch['book_page']+3]
    matches = [x for x in page.get_xobjects() if x[2] == source
               and near(fitz.Rect(x[3])*a4, old_rect)]
    assert len(matches) == 1, ('local match', old_patch['id'], matches)
    pattern = rb'/' + re.escape(matches[0][1].encode()) + rb'\s+Do\b'
    stream = doc.xref_stream(source)
    assert len(re.findall(pattern, stream)) == 1
    doc.update_stream(source, re.sub(pattern, b'', stream))
    if entry is None:
        return None
    new_rect = fitz.Rect(old_rect.x0, old_rect.y0,
                         old_rect.x0+entry['ink_width'], old_rect.y0+entry['ink_height'])
    assert new_rect.x0 >= 50 and new_rect.x1 <= 585, (old_patch['id'], list(new_rect))
    # Local formula growth must remain inside the original source band.
    # Bigger solutions should be placed in the adjacent extensible explanation gap.
    assert new_rect.y1 <= old_rect.y1 + .1, ('local formula too tall', old_patch['id'], list(old_rect), list(new_rect))
    temp = doc.new_page(width=595, height=841)
    temp.show_pdf_page(new_rect, compiled, entry['page']-1,
                       clip=fitz.Rect(entry['clip']), keep_proportion=False)
    roots = root_objects(doc, temp)
    assert len(roots) == 1
    inserted_root = roots[0][0]
    graft = temp.read_contents().replace(('/'+roots[0][1]+' ').encode(), ('/'+new_name+' ').encode())
    owner, prefix = source, ''
    for key in ['Resources', 'XObject']:
        typ, value = doc.xref_get_key(owner, prefix+key)
        if typ == 'xref':
            owner, prefix = int(value.split()[0]), ''
        else:
            assert typ == 'dict'
            prefix += key+'/'
    doc.xref_set_key(owner, prefix+new_name, str(inserted_root)+' 0 R')
    doc.update_stream(source, doc.xref_stream(source)+b'\nq\n'+graft+b'\nQ\n')
    doc.delete_page(len(doc)-1)
    return new_rect


def matrix_values(doc, xref):
    typ, val = doc.xref_get_key(xref, 'Matrix')
    assert typ == 'array'
    nums = [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][-+]?\d+)?', val)]
    assert len(nums) == 6
    return nums


def clip_source_regions(doc, source, masks):
    """Exclude each old red-answer rectangle from the source's painted content.

    The original Form tree is retained for exact original-image recovery, but
    its paint path no longer includes these verified red-only rectangles.
    Compiled replacement solutions are painted once in the question gap.
    """
    content=doc.xref_stream(source)
    for item in masks:
        x0,y0,x1,y1=item['rect']
        hole=f'{x0:.6f} {841-y1:.6f} {x1-x0:.6f} {y1-y0:.6f} re'.encode()
        content=b'q\n0 0 595 841 re\n'+hole+b'\nW* n\n'+content+b'\nQ\n'
    doc.update_stream(source,b'% Average answer source exclusions\n'+content)


def plan_page(old, index, changed, book):
    notes = sorted([copy.deepcopy(a) for a in old['answers'] if a['book_page'] == book], key=lambda a:a['target_rect'][1])
    bands = [b for b in old['bands'] if b['book_page'] == book]
    groups = {}
    for a in notes:
        groups.setdefault(a['source_cut_y'], []).append(a)
    reuse={}
    reuse_path=Q/'layout_reuse.json'
    if reuse_path.exists():
        for anchor in J(reuse_path)['anchors']:
            if int(anchor['key'][1:4])!=book:continue
            source_y=anchor['source_y']
            band=next(b for b in bands if b['source_rect'][1]<=source_y<b['source_rect'][3])
            reuse[anchor['key']]=source_y+band['target_rect'][1]-band['source_rect'][1]
    plans, seams = {}, []
    for cut, group in sorted(groups.items()):
        nxt = [b for b in bands if abs(b['source_rect'][1]-cut) < .01]
        assert len(nxt) == 1
        boundary = nxt[0]['target_rect'][1]
        prev_end = None
        for a in group:
            old_rect = fitz.Rect(a['target_rect'])
            y = reuse.get(a['key'],old_rect.y0)
            if prev_end is not None and prev_end+4 > y:
                y += math.ceil(prev_end+4-y-1e-6)
            if a['key'] in changed:
                entry = index.get(a['key'])
                if entry:
                    rect = fitz.Rect(old_rect.x0, y, old_rect.x0+entry['ink_width'], y+entry['ink_height'])
                else:
                    rect = None
            else:
                rect = old_rect + (0, y-old_rect.y0, 0, y-old_rect.y0)
            plans[a['key']] = {'old':list(old_rect), 'relative_new':list(rect) if rect else None,
                               'source_cut_y':cut, 'changed':a['key'] in changed}
            if rect is not None:
                assert rect.x1 <= 585, (a['key'], list(rect))
                prev_end = rect.y1
        extra = max(0, math.ceil((prev_end or boundary)+6-boundary-1e-6))
        if extra:
            seams.append({'old_y':boundary, 'extra':extra, 'source_cut_y':cut,
                          'keys':[a['key'] for a in group]})
    def shift(y):
        return sum(s['extra'] for s in seams if s['old_y'] <= y+.003)
    for key, plan in plans.items():
        if plan['relative_new'] is not None:
            d = shift(plan['old'][1])
            plan['new'] = list(fitz.Rect(plan['relative_new'])+(0,d,0,d))
        else:
            plan['new'] = None
    return plans, seams, shift


def pixel_check(before_path, after_path, old, rel, page_reports, local_changes, report_path):
    before, after = fitz.open(before_path), fitz.open(after_path)
    assert len(before) == len(after) == 128
    by_book = {p['book_page']:p for p in page_reports}
    changed_page_idxs = {b+3 for b in by_book}
    checked, maxdiff = [], 0
    for i in range(128):
        p, q = before[i], after[i]
        aa, bb = p.get_pixmap(alpha=False), q.get_pixmap(alpha=False)
        a = np.frombuffer(aa.samples,dtype=np.uint8).reshape(aa.height,aa.width,3)
        b = np.frombuffer(bb.samples,dtype=np.uint8).reshape(bb.height,bb.width,3)
        if i not in changed_page_idxs:
            assert a.shape == b.shape and np.array_equal(a,b), ('unchanged page differs',i+1)
            continue
        book = i-3
        report = by_book[book]
        seams = report['inserted_gaps']
        expected = np.full_like(b,255)
        for y in range(a.shape[0]):
            ny = y+sum(x['extra'] for x in seams if x['old_y'] <= y)
            expected[ny] = a[y]
        allowed = np.zeros(b.shape[:2],bool)
        def mask(rect,padding=2):
            if rect is None:
                return
            x0,y0,x1,y1 = fitz.Rect(rect)+(-padding,-padding,padding,padding)
            allowed[max(0,math.floor(y0)):min(b.shape[0],math.ceil(y1)),
                    max(0,math.floor(x0)):min(b.shape[1],math.ceil(x1))] = True
        for s in seams:
            sy = s['old_y']+sum(t['extra'] for t in seams if t['old_y'] < s['old_y'])
            mask([0,sy-2,595,sy+s['extra']+2])
        for key, n in report['notes'].items():
            if n['changed'] or (n['new'] is not None and not near(n['old'],n['relative_new'])):
                dy = sum(s['extra'] for s in seams if s['old_y'] <= n['old'][1]+.003)
                mask(list(fitz.Rect(n['old'])+(0,dy,0,dy)))
                mask(n['new'])
            elif n['new'] is not None:
                # At an original Form's exact clip boundary, a page-height
                # change can make MuPDF cover the adjacent one-pixel row.
                # Compare its complete interior and tolerate only that edge.
                x0,y0,x1,y1=n['new']
                mask([x0,y0-.2,x1,y0+.2],padding=.8)
                mask([x0,y1-.2,x1,y1+.2],padding=.8)
        for c in local_changes:
            if c['book_page'] != book:
                continue
            for field in ['old_rect','new_rect']:
                rr = c[field]
                if rr is None:
                    continue
                for band in [x for x in old['bands'] if x['book_page']==book]:
                    sr=fitz.Rect(band['source_rect']); clipped=fitz.Rect(rr)&sr
                    if clipped.is_empty:
                        continue
                    dx=band['target_rect'][0]-sr.x0
                    dy=band['target_rect'][1]-sr.y0
                    shift=sum(s['extra'] for s in seams if s['old_y'] <= band['target_rect'][1]+.003)
                    mask(list(clipped+(dx,dy+shift,dx,dy+shift)))
        mismatch = np.any(expected != b,axis=2) & ~allowed
        count = int(mismatch.sum())
        maxdiff = max(maxdiff,count)
        if count:
            yy,xx=np.where(mismatch)
            raise AssertionError(('unexpected pixels',book,count,[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]))
        checked.append({'book_page':book,'outside_changed_objects_new_gaps_and_form_clip_edges_identical':True,'height_added_pt':report['extra_height']})
    assert not after[0].get_text() and not after[0].get_images()
    write(report_path,{'passed':True,'pdf_sha256':SHA(after_path),'pages':128,'all_pages_raster_checked':128,
                       'unchanged_pages_identical':128-len(changed_page_idxs),'changed_pages':checked,
                       'first_page_blank':True,'native_form_clip_edge_tolerance_pt':1,
                       'max_unexpected_pixels':maxdiff})


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--compiled-dir',type=Path,default=Q/'compiled')
    ap.add_argument('--compiled-pdf',type=Path)
    ap.add_argument('--output',type=Path,default=R/'deliverables/小学同步素养四年级上册数学答案.pdf')
    ap.add_argument('--plan-only',action='store_true')
    a=ap.parse_args()
    old=J(R/'pdf_baseline/current_release.json')
    base=R/'bundle/小学同步素养四年级上册数学答案.pdf'
    assert SHA(base)==old['sha256']
    index=J(a.compiled_dir/'snippet_index.json')
    baseline=J(R/'pdf_baseline/snippets.json')
    changed=set(k for k in baseline|index if baseline.get(k,{}).get('body')!=index.get(k,{}).get('body'))
    assert changed and all(73<=int(k[1:4])<=108 for k in changed), changed
    assert not(set(index)-set(baseline)), 'New note/local ids require explicit placement policy.'
    keys=sorted(set(baseline.get(k,index.get(k))['key'] for k in changed))
    books=sorted(set(int(k[1:4])for k in changed))
    notes_changed={k for k in changed if '_local' not in k}
    local_ids={k for k in changed if '_local' in k}
    source_masks=J(Q/'source_masks.json')['masks'] if (Q/'source_masks.json').exists() else []
    plans={}
    for book in books:
        n,s,_=plan_page(old,index,notes_changed,book)
        plans[book]={'notes':n,'inserted_gaps':s,'extra_height':sum(x['extra']for x in s)}
    write(Q/'layout_plan.json',{'changed_keys':keys,'changed_ids':sorted(changed),'pages':plans})
    print(json.dumps({'changed_ids':len(changed),'keys':keys,'extra_height_by_book':{b:p['extra_height']for b,p in plans.items()}},ensure_ascii=False),flush=True)
    if a.plan_only:
        return
    compiled_path=a.compiled_pdf or a.compiled_dir/'snippets_frozen.pdf'
    compiled=fitz.open(compiled_path)
    doc=fitz.open(base)
    rel=copy.deepcopy(old)
    local_changes=[]
    for book in books:
        for lid in sorted(local_ids):
            if int(lid[1:4]) != book:
                continue
            patch=next(x for x in rel['local_replacements']if x['id']==lid)
            page=doc[book+3]
            source=source_for_book(doc,page,old,book)
            before_rect=patch['target_rect']
            target=inject_source_patch(doc,source,patch,index.get(lid),compiled,'Average_'+lid)
            local_changes.append({'book_page':book,'id':lid,'old_rect':before_rect,'new_rect':list(target)if target else None})
            if target is None:
                rel['local_replacements'].remove(patch)
            else:
                patch['target_rect']=list(target)
                patch['latex']=index[lid]['body']
                patch['reason']='平均数题补齐脱式计算或移多补少简算，原源页位置保持。'
        masks=[m for m in source_masks if m['book_page']==book]
        if masks:
            page=doc[book+3]
            source=source_for_book(doc,page,old,book)
            clip_source_regions(doc,source,masks)
            for i,item in enumerate(masks):
                local_changes.append({'book_page':book,'id':item['key']+'_source_mask_'+str(i+1),
                                      'kind':'source_mask','old_rect':item['rect'],'new_rect':None})
    page_reports=[]
    for book in books:
        page=doc[book+3]
        nplans,seams,shift=plan_page(old,index,notes_changed,book)
        extra=sum(s['extra']for s in seams)
        roots=root_objects(doc,page)
        root_rects={x[0]:list(fitz.Rect(x[3])*page.transformation_matrix)for x in roots}
        note_roots={}
        for key,np_ in nplans.items():
            note_roots[matching_root(doc,page,fitz.Rect(np_['old']))[0]]=key
        for x in roots:
            key=note_roots.get(x[0])
            if key in notes_changed:
                remove_root_draw(doc,page,x[1])
        old_height=page.rect.height
        page.set_mediabox(fitz.Rect(0,0,595,old_height+extra))
        page=doc.reload_page(page)
        for x in roots:
            key=note_roots.get(x[0])
            if key in notes_changed:
                continue
            if key:
                dy=nplans[key]['new'][1]-nplans[key]['old'][1]
            else:
                dy=shift(root_rects[x[0]][1])
            mat=matrix_values(doc,x[0]);mat[5]+=extra-dy
            doc.xref_set_key(x[0],'Matrix','['+' '.join(format(v,'.10f').rstrip('0').rstrip('.')if v else'0'for v in mat)+']')
        page=doc.reload_page(page)
        for key,np_ in nplans.items():
            record=next(x for x in rel['answers']if x['key']==key)
            if np_['new'] is None:
                rel['answers'].remove(record)
            else:
                record['target_rect']=np_['new']
                if key in notes_changed:
                    e=index[key]
                    page.show_pdf_page(fitz.Rect(np_['new']),compiled,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
        for name in ['bands','moved_footers','moved_headings']:
            for item in rel[name]:
                if item['book_page']==book:
                    rect=fitz.Rect(item['target_rect']);dy=shift(rect.y0)
                    item['target_rect']=list(rect+(0,dy,0,dy))
        for m in rel['mapping']:
            if m['book_page']==book:
                m['page_size']=[595,old_height+extra]
        page_reports.append({'book_page':book,'pdf_page':book+4,'old_height':old_height,'new_height':old_height+extra,
                             'extra_height':extra,'inserted_gaps':seams,'notes':nplans})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    doc.save(a.output,garbage=3,deflate=True)
    doc.close()
    receipt=J(Q/'compile_receipt.json')if(Q/'compile_receipt.json').exists()else{}
    source_files=dict(receipt.get('source_files',rel['source_files']))
    for path in [Q/'source_masks.json',Q/'layout_reuse.json']:
        if path.exists():source_files[str(path.relative_to(P))]=SHA(path)
    rel.update({'run_name':'average_complete_steps','pdf':str(a.output.resolve()),'sha256':SHA(a.output),
                'previous_pdf_sha256':SHA(base),'compiled_pdf':str(compiled_path.resolve()),
                'compiled_tex':str((a.compiled_dir/'详细题内答案.tex').resolve()),
                'source_files':source_files,
                'source_masks':source_masks,
                'layout_reuse':J(Q/'layout_reuse.json')if(Q/'layout_reuse.json').exists()else{},
                'average_update':{'changed_keys':keys,'changed_book_pages':books,
                                  'pages':128,'same_original_question_page':True,'current_qa':'average_update/qa_current.json'}})
    for k in ['lossless_optimization','raw_pdf_sha256','preservation']:
        rel.pop(k,None)
    write(P/'detailed_layout/current_release.json',rel)
    write(P/'answer_page_map.json',rel['mapping'])
    targets=J(P/'detailed_layout/base_local_targets.json')
    for c in local_changes:
        if c.get('kind')=='source_mask':
            continue
        pp=next((x for x in targets['patches']if x['id']==c['id']),None)
        if c['new_rect'] is None:
            if pp is not None:targets['patches'].remove(pp)
        else:
            assert pp is not None,c['id']
            pp['target_rect']=c['new_rect']
    write(P/'detailed_layout/base_local_targets.json',targets)
    write(Q/'patch_report.json',{'passed':True,'pdf_sha256':SHA(a.output),'previous_pdf_sha256':SHA(base),
                                'changed_book_pages':books,'changed_question_keys':keys,'changed_snippet_ids':sorted(changed),
                                'page_layout':page_reports,'local_changes':local_changes,
                                'known_old_local_drawing_operations_removed':True,
                                'old_original_red_regions_excluded_from_painting':len(source_masks),
                                'pages':128,'separate_analysis_pages':0,
                                'font_sizes_pt':{'note':11.5,'local_math':10.5}})
    pixel_check(base,a.output,old,rel,page_reports,local_changes,Q/'qa_scope.json')
    previews=Q/'previews';previews.mkdir(exist_ok=True)
    with fitz.open(a.output)as final:
        for book in books:
            final[book+3].get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(previews/f'p{book:03d}.png')
    print('PATCHED',SHA(a.output),'books',books,flush=True)


if __name__=='__main__':
    main()
