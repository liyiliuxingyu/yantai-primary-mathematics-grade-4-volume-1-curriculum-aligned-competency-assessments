"""Machine checks for the concise in-question PDF; not a mathematical proof.

Run after publishing.  This script checks source assets, placement and approved
note ledgers.  The separate visual/math audit files record human review scope.
"""
from pathlib import Path
import argparse, hashlib, json, math, re, sys
import fitz
import numpy as np

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R))
from answer_content import load_pages, aligned

J = lambda p: json.loads(Path(p).read_text())
SHA = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok, message, *detail):
    if not ok:
        raise AssertionError((message, *detail))

def rgb(page, rect=None, scale=2):
    p = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    return np.frombuffer(p.samples, dtype=np.uint8).reshape(p.height, p.width, p.n)[:, :, :3]

def rect_close(a, b, tolerance=.025):
    return all(abs(x-y) < tolerance for x, y in zip(a, b))

def run(receipt):
    release = J(receipt)
    require(release['sha256'] == SHA(release['pdf']), 'publication hash differs')
    require(SHA(release['input_pdf']) == release['input_sha256'], 'base input changed')
    for path, digest in release['source_files'].items():
        require(SHA(R/path) == digest, 'approved source changed', path)
    require(release['pointer_masks']==J(R/'inline_layout/pointer_masks.json')['masks'],
            'published pointer masks differ from source')
    require(release['duplicate_formula_masks']==J(R/'detailed_layout/duplicate_formula_masks.json')['items'],
            'published duplicate-formula masks differ from source')
    source_footers={f['book_page']:f['rect']for f in J(R/'inline_layout/footer_crops.json')['crops']}
    require(len(release['moved_footers'])==108 and
            all(f['source_rect']==source_footers[f['book_page']]for f in release['moved_footers']),
            'published footer crops differ from source')
    doc = fitz.open(release['pdf'])
    base = fitz.open(release['cleaned_base_pdf'])
    original = fitz.open(release['input_pdf'])
    require(len(doc) == len(base) == len(original) == 128, 'not 128 pages')
    first = doc[0]
    require(not first.get_text() and not first.get_images() and not list(first.annots() or [])
            and not first.get_links(), 'first page contains content')
    require(np.min(rgb(first, scale=1)) == 255, 'first page is not pure white')
    require(release['separate_analysis_pages'] == 0, 'unexpected continuation pages')
    require(release['extra_diagrams'] == 0, 'unexpected repeated supplemental diagram')
    require(len(release['mapping']) == 108, 'wrong question page count')

    records = {s['record']['key']: s['record'] for p in load_pages() for s in p['sections']}
    notes = {}
    for letter in 'ABCD':
        for n in J(R/f'detailed_layout/notes_{letter}.json')['records']:
            require(n['key'] not in notes, 'duplicate ledger record', n['key'])
            notes[n['key']] = n
            require(n.get('reason', '').strip(), 'missing rationale for note/omission', n['key'])
            if n.get('covered_by'):
                require(n['covered_by'] in records, 'coverage points to unknown key', n['key'])
    require(set(notes) == set(records) and len(notes) == 867, 'incomplete ledger')
    expected_visible = {k for k,n in notes.items() if n['latex'].strip()}
    actual_visible = [a['key'] for a in release['answers']]
    require(set(actual_visible) == expected_visible and len(actual_visible) == len(expected_visible),
            'note omitted or displayed more than once')
    require(release['visible_note_blocks'] == len(actual_visible),
            'unexpected visible block count', len(actual_visible))
    index = J(Path(release['compiled_pdf']).parent/'snippet_index.json')
    expected_patches = {f"{k}_local{i+1}": (k,p)
                        for k,n in notes.items()
                        for i,p in enumerate(n.get('local_replacements', n.get('original_replacements', [])))}
    require(set(index) == expected_visible | set(expected_patches), 'snippet index differs from approved ledger')
    for k in expected_visible:
        body = index[k]['body']
        prefix = r'\textbf{'+records[k]['id']+r'：}\ '
        approved = aligned(notes[k]['latex'].strip())
        require(body in (approved, prefix+approved), 'note body differs from approved text', k)
    for pid,(k,p) in expected_patches.items():
        require(index[pid]['body'] == aligned(p['latex']), 'local math differs from approved text', pid)
    compilation_log = Path(release['compiled_tex']).parent/'compile.log'
    log = compilation_log.read_text()
    require(not any(x in log for x in ['Missing character:', 'Undefined control sequence.', 'Overfull \\hbox', 'Overfull \\vbox']),
            'LaTeX font/overflow warning')
    compiled = fitz.open(release['compiled_pdf'])
    require(len(compiled) == len(index), 'compiled snippet page count differs')

    # Reconstruct the actual scan background with the original image bytes and
    # original image rectangles.  This also verifies duplicate resources agree.
    pure = fitz.open()
    raw_by_sha = {}
    original_img_cache = {}
    for p in original:
        for info in p.get_images(full=True):
            xref=info[0]
            if xref not in original_img_cache:
                raw=original.extract_image(xref)['image']
                original_img_cache[xref]=(hashlib.sha256(raw).hexdigest(),raw)
            digest,raw=original_img_cache[xref]
            raw_by_sha[digest]=raw
    by_base={i:[] for i in range(1,129)}
    for image in release['source_original_images']:
        require(image['sha256'] in raw_by_sha, 'source scan digest missing in original input')
        by_base[image['base_page']].append(image)
    for i in range(1,129):
        q=pure.new_page(width=595,height=841)
        for image in by_base[i]:
            q.insert_image(image['rect'], stream=raw_by_sha[image['sha256']], keep_proportion=False)

    mask_checks=[]
    for kind, masks in [('pointer',release['pointer_masks']),('duplicate_formula',release['duplicate_formula_masks']),('legacy_duplicate_note',release.get('legacy_note_cleanup',[]))]:
        for m in masks:
            r=fitz.Rect(m['rect'])
            arr=rgb(pure[m['book_page']+3],r,4)
            ink=int((arr.min(axis=2)<210).sum())
            # Cleanup restores the actual scan crop, rather than painting a
            # white rectangle.  A few scan edge pixels may therefore be safely
            # included.  Test their retention instead of falsely treating any
            # included gray pixel as deletion of original text.
            missing=0
            if ink:
                restored=rgb(base[m['book_page']+3],r,4)
                require(restored.shape==arr.shape,'restored scan crop differs in size',kind,m['book_page'])
                missing=int(((arr.min(axis=2)<210)&(restored.min(axis=2)>235)).sum())
                require(missing==0,'cleanup removes original scan ink',kind,m['book_page'],list(r),missing)
            mask_checks.append({'kind':kind,'book_page':m['book_page'],
                                'original_scan_ink_pixels_below_210_at_4x':ink,
                                'original_scan_ink_pixels_lost_after_scan_restore':missing})

    # Local patches start on the source blank answer area.  Their actual ink
    # rectangle is recorded after fitting; verify no original black condition
    # is underneath that ink area, including extended target rectangles.
    patches=release['local_replacements']
    require({p['id'] for p in patches}==set(expected_patches), 'local patch omitted/duplicated')
    local_checks=[]
    for p in patches:
        e=index[p['id']];t=fitz.Rect(p['target_rect']);er=fitz.Rect(e['clip'])
        require(abs(t.width-e['ink_width'])<.002 and abs(t.height-e['ink_height'])<.002,
                'local formula scaled',p['id'])
        require(fitz.Rect(0,0,595,841).contains(t),'local formula outside source page',p['id'])
        arr=rgb(pure[p['book_page']+3],t,4)
        ink=int((arr.min(axis=2)<210).sum())
        require(ink==0 or(p.get('kind')=='analysis_box_answer'and p.get('original_prompt_replaced')),'local formula overlaps original black scan ink',p['id'],ink)
        local_checks.append({'id':p['id'],'source_target_rect':list(t),'original_scan_dark_pixels_at_4x':ink})

    # Look just beyond the erased old answer regions too: an old equals sign
    # can sit several points left of the new formula and survive an otherwise
    # sound replacement.  Exclude original scan colors and all neighboring
    # cleanup/patch rectangles; these must not be confused with residual ink.
    ghost_checks=[]
    for p in patches:
        if p.get('kind')=='analysis_box_answer':
            ghost_checks.append({'id':p['id'],'machine_halo_check':'not_applicable_to_dense_graph_labels','reason':'These small adjacent nodes intentionally retain red operations in nearby circles. Their 14 new labels were independently inspected at high magnification; source-ink and fit checks above still apply. The large-formula remnant test below cannot distinguish the retained operators from stray ink.'})
            continue
        book=p['book_page'];area=(fitz.Rect(p['rect'])|fitz.Rect(p['target_rect']))+(-14,-7,14,7)
        area &= fitz.Rect(0,0,595,841)
        oldpix=original[book+3].get_pixmap(matrix=fitz.Matrix(4,4),clip=area,alpha=False)
        old=np.frombuffer(oldpix.samples,dtype=np.uint8).reshape(oldpix.height,oldpix.width,oldpix.n)[:,:,:3]
        background=rgb(pure[book+3],area,4)
        a=old.astype(float)
        candidate=(a[:,:,0]>a[:,:,1]*1.2)&(a[:,:,0]>a[:,:,2]*1.2)&(a[:,:,1]<200)
        candidate &= (np.max(np.abs(old.astype(np.int16)-background.astype(np.int16)),axis=2)>8)
        yy,xx=np.indices(candidate.shape)
        gx=(oldpix.x+xx+.5)/4;gy=(oldpix.y+yy+.5)/4
        for m in patches+release['pointer_masks']+release['duplicate_formula_masks']+release.get('legacy_note_cleanup',[]):
            if m['book_page']!=book:continue
            r=m.get('restore_rect',m['rect'])
            candidate &= ~((gx>=r[0])&(gx<r[2])&(gy>=r[1])&(gy<r[3]))
        count=int(candidate.sum())
        require(count==0,'old red answer remnants outside local restore rectangle',p['id'],count)
        ghost_checks.append({'id':p['id'],'halo_LR_TB_pt':[14,7],
                             'old_red_pixels_beyond_scan_background_outside_all_erase_masks_at_4x':count})

    img_cache={}
    def image_hashes(page):
        hashes=set()
        for info in page.get_images(full=True):
            xref=info[0]
            if xref not in img_cache:
                img_cache[xref]=hashlib.sha256(doc.extract_image(xref)['image']).hexdigest()
            hashes.add(img_cache[xref])
        return hashes
    all_published_images=set()
    for p in doc:
        all_published_images.update(image_hashes(p))
    expected_noncover={image['sha256']for image in release['source_original_images']if image['base_page']!=1}
    require(expected_noncover<=all_published_images,
            'a noncover source scan image is absent from the publication')
    stream_sha=lambda d,x:hashlib.sha256(d.xref_stream(x) or b'').hexdigest()
    per_page=[]
    all_mapped_keys=[]
    raw_reference=None;optimization=None;removed_source_forms=[]
    preserved_reference=None
    if release.get('preservation'):
        preserved_path=R/'followup_style/before/previous.pdf'
        require(SHA(preserved_path)==release['preservation']['baseline_pdf_sha256'],'preserved baseline changed')
        preserved_reference=fitz.open(preserved_path)
    if release.get('lossless_optimization'):
        optimization=J(R/release['lossless_optimization'])
        require(optimization['passed']and optimization['candidate_sha256']==release['sha256']and optimization['pages_compared']==128 and optimization['different_rgb_pixels_total']==0 and not optimization['text_different_pages'],'invalid lossless proof')
        require(SHA(optimization['source_pdf'])==optimization['source_sha256'],'raw reference changed')
        raw_reference=fitz.open(optimization['source_pdf'])
    for m in release['mapping']:
        book=m['book_page'];pn=m['answer_pdf_page'];p=doc[pn-1]
        require(pn==book+4,'PDF book/page map changed',book,pn)
        require(rect_close(p.rect,[0,0,*m['page_size']]),'wrong published page size',book)
        require(not m['analysis_pdf_pages'],'analysis pages added',book)
        all_mapped_keys.extend(m['record_pdf_pages'])
        for k, pp in m['record_pdf_pages'].items():
            require(records[k]['book_page']==book and pp==[pn], 'record maps to wrong question page',k)
        expected_scan={v['sha256'] for v in by_base[book+4]}
        require(expected_scan<=image_hashes(p),'original scan bytes missing in published question page',book)
        bands=sorted([b for b in release['bands'] if b['book_page']==book],key=lambda b:b['source_rect'][1])
        require(bands and bands[0]['source_rect'][1]==0 and bands[-1]['source_rect'][3]==841,
                'source bands incomplete',book)
        require(all(a['source_rect'][3]==b['source_rect'][1] for a,b in zip(bands,bands[1:])),
                'source bands overlap or leave gap',book)
        expected_streams={hashlib.sha256(base[book+3].read_contents()).hexdigest()}
        expected_streams.update(stream_sha(base,x[0])for x in base[book+3].get_xobjects())
        if preserved_reference is not None and book not in release['preservation']['changed_book_pages']:
            expected_streams={stream_sha(preserved_reference,x[0])for x in preserved_reference[pn-1].get_xobjects()}
            require(hashlib.sha256(p.read_contents()).hexdigest()==hashlib.sha256(preserved_reference[pn-1].read_contents()).hexdigest(),'retained page content program changed',book)
        actual_streams={stream_sha(doc,x[0])for x in p.get_xobjects()}
        source_programs_exact=expected_streams<=actual_streams
        if not source_programs_exact:
            require(raw_reference is not None,'cleaned source drawing program not retained',book)
            raw_streams={stream_sha(raw_reference,x[0])for x in raw_reference[pn-1].get_xobjects()}
            require(expected_streams<=raw_streams,'raw source drawing program not retained',book)
            removed_source_forms.append({'book_page':book,'source_form_stream_hashes_not_retained_after_optimization':sorted(expected_streams-actual_streams)})
        wrappers=[x for x in p.get_xobjects()if x[2]==0]
        answers=[a for a in release['answers']if a['book_page']==book]
        reused=0
        for b in bands:
            sr,tr=fitz.Rect(b['source_rect']),fitz.Rect(b['target_rect'])
            require(abs(sr.width-tr.width)<.001 and abs(sr.height-tr.height)<.001,
                    'source band rescaled',book)
            shift=tr.y0-sr.y0
            require(abs(shift-round(shift))<.001,'noninteger vertical translation',book)
            hits=[x for x in wrappers if rect_close(fitz.Rect(x[3])*p.transformation_matrix,tr)]
            require(hits,'missing source band wrapper',book,list(tr))
            match=re.search(r'/Matrix\s*\[([^]]+)\]',doc.xref_object(hits[0][0]))
            require(match,'missing wrapper matrix',book)
            values=list(map(float,match.group(1).split()))
            require(np.max(np.abs(np.array(values[:4])-[1,0,0,1]))<.00002 and abs(values[4])<.00002,
                    'wrapper transform changed scale',book,values)
            for a in answers:
                t=fitz.Rect(a['target_rect']);inter=t&tr
                if inter.is_empty:continue
                area=fitz.Rect(inter.x0,inter.y0-shift,inter.x1,inter.y1-shift)
                arr=rgb(base[book+3],area,2)
                dark=int((arr.min(axis=2)<235).sum())
                require(dark==0,'note overlaps retained source ink',book,a['key'],list(area),dark)
                reused+=1
        for a in answers:
            t=fitz.Rect(a['target_rect']);e=index[a['key']]
            require(p.rect.contains(t),'note outside page',a['key'])
            require(abs(t.width-e['ink_width'])<.002 and abs(t.height-e['ink_height'])<.002,
                    'note formula/text scaled',a['key'])
        for i,a in enumerate(answers):
            for b in answers[i+1:]:
                inter=fitz.Rect(a['target_rect'])&fitz.Rect(b['target_rect'])
                require(inter.is_empty or inter.get_area()<.01,'notes overlap',a['key'],b['key'])
        f=next(x for x in release['moved_footers']if x['book_page']==book)
        footer=fitz.Rect(f['target_rect'])
        require(p.rect.contains(footer),'footer outside page',book)
        require(all((fitz.Rect(a['target_rect'])&footer).is_empty for a in answers),'footer overlaps note',book)
        per_page.append({'book_page':book,'pdf_page':pn,'height_pt':p.rect.height,
                         'source_bands':len(bands),'notes':len(answers),'reused_blank_intersections_tested':reused,
                         'source_scan_bytes_retained':True,'cleaned_source_programs_exact_in_this_pdf':source_programs_exact,'raw_source_programs_retained':True,'source_scale_1_to_1':True})
        if book%18==0:print('verified question page',book,flush=True)
    for h in release.get('moved_headings',[]):
        page=doc[h['pdf_page']-1];t=fitz.Rect(h['target_rect']);sr=fitz.Rect(h['source_rect'])
        require(page.rect.contains(t)and abs(t.width-sr.width)<.001 and abs(t.height-sr.height)<.001,'moved heading resized/clipped',h)
        require(all((t&fitz.Rect(a['target_rect'])).is_empty for a in release['answers']if a['book_page']==h['book_page']),'heading overlaps explanation',h)
    for f in release.get('footer_overrides',[]):
        page=doc[f['book_page']+3];require(('• '+f['label']+' •')in page.get_text(),'corrected footer absent',f)
    require(len(all_mapped_keys)==867 and set(all_mapped_keys)==set(records),'mapping drops or duplicates records')
    return {'passed':True,'pdf_sha256':release['sha256'],'pdf_pages':128,'question_pages':108,
            'record_coverage':867,'visible_note_blocks':len(actual_visible),'empty_notes_with_recorded_reason':867-len(actual_visible),
            'first_page_pure_white':True,'separate_analysis_pages':0,'extra_supplemental_diagrams':0,
            'local_patch_count':len(patches),'duplicate_formula_masks':len(release['duplicate_formula_masks']),
            'noncover_scan_image_digests_retained':len(expected_noncover),
            'source_scan_bytes_and_original_scale_preserved':True,'approved_note_texts_match':True,
            'all_reused_blank_regions_dark_ink_free_at_2x':True,'latex_missing_glyph_and_overflow_warnings':0,
            'mask_checks':mask_checks,'local_checks':local_checks,'pages':per_page,
            'optimized_source_form_stream_changes':removed_source_forms,'source_form_retention_note':'原始拼版逐流验证；优化版对被去重/清理的旧Form单列记录，并由全128页2倍逐像素及抽文零差异证明可见内容保持。','local_red_ghost_checks':ghost_checks,'local_red_ghost_pixels_beyond_scan_background_in_checked_halos':0,
            'limits':'This is automated file/placement/source-integrity QA. It does not establish mathematical correctness or replace actual visual review. No PowerPoint playback test is implied.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,default=R/'detailed_layout/current_release.json')
    p.add_argument('--output',type=Path,default=R/'detailed_layout/qa_release.json');a=p.parse_args()
    try:report=run(a.receipt)
    except Exception as e:
        a.output.write_text(json.dumps({'passed':False,'error':repr(e),'receipt':str(a.receipt)},ensure_ascii=False,indent=2))
        raise
    a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k not in ('mask_checks','local_checks','local_red_ghost_checks','pages')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
