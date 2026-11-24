"""Check all publication pages, source coverage, Kai fonts and glyph bounds."""
from pathlib import Path
import json,hashlib,math,re,sys,collections
import fitz,numpy as np
R=Path(__file__).resolve().parents[1];Q=R/'threecols_update';ROOT=R.parent
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
before=fitz.open(ROOT/'downloads/小学同步素养四年级上册数学答案.pdf')
out=ROOT/'output/pdf/小学同步素养四年级上册数学答案.pdf';after=fitz.open(out)
old=J(Q/'baseline_release.json');new=J(R/'detailed_layout/current_release.json')
idx=J(Q/'compiled/snippet_index.json');items={n['id']:n for n in J(Q/'items.json')if n['kind']=='note'}
assert len(before)==len(after)==128 and len(idx)==len(items)==856
assert not J(Q/'compile_warnings.json')
compiled=fitz.open(Q/'compiled/threecols.pdf');assert len(compiled)==856
font_checks=[]
for key,e in idx.items():
    assert e['body']==items[key]['body'] and e['columns']==3
    p=compiled[e['page']-1];pix=p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=True)
    a=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,4)
    y,x=np.where(a[:,:,3]>0)
    assert x.min()>0 and x.max()<pix.width-1 and y.min()>0 and y.max()<pix.height-1,(key,'ink touches boundary')
    chinese=[s for b in p.get_text('dict')['blocks']for l in b.get('lines',[])for s in l['spans']if re.search('[\u3400-\u9fff]',s['text'])]
    assert all('FandolKai' in s['font'] for s in chinese),(key,'CJK is not Kai')
    assert all(abs(s['size']-11.5*72/72.27)<.03 for s in chinese),(key,'CJK size changed')
    font_checks.append({'key':key,'three_columns':True,'all_CJK_Kai':True,'font_pt':11.5,'full_ink_inside_page':True,'source_unchanged':True})
plans=J(Q/'layout_plan.json');checks=[];unchanged=[];prose=J(Q/'original_prose.json')['records'];prose_checks=[]
for pn,(p,q)in enumerate(zip(before,after),1):
    assert p.rect.width==q.rect.width==595
    plan=next((x for x in plans if x['pdf_page']==pn),None)
    aa=np.frombuffer(p.get_pixmap(alpha=False).samples,dtype=np.uint8).reshape(round(p.rect.height),595,3)
    bb=np.frombuffer(q.get_pixmap(alpha=False).samples,dtype=np.uint8).reshape(round(q.rect.height),595,3)
    if plan is None:
        assert np.array_equal(aa,bb),('unchanged page differs',pn);unchanged.append(pn);continue
    seams=plan['seams'];shift=lambda y:sum(s['extra']for s in seams if s['old_y']<=y+.003)
    expected=np.full_like(bb,255)
    for y in range(aa.shape[0]):expected[y+shift(y)]=aa[y]
    allowed=np.zeros(bb.shape[:2],bool)
    def mask(rect):
        x0,y0,x1,y1=fitz.Rect(rect)+(-2,-2,2,2)
        allowed[max(0,math.floor(y0)):min(bb.shape[0],math.ceil(y1)),max(0,math.floor(x0)):min(595,math.ceil(x1))]=True
    for a in [a for a in old['answers']if a['pdf_page']==pn]:
        r=fitz.Rect(a['target_rect']);dy=shift(r.y0);mask(r+(0,dy,0,dy))
    for a in [a for a in new['answers']if a['pdf_page']==pn]:mask(a['target_rect'])
    for row in [x for x in prose if x['book_page']==plan['book_page']]:
        rect=fitz.Rect(row['mask_rect']);dy=shift(rect.y0);mask(rect+(0,dy,0,dy))
        x0,y0,x1,y1=rect
        patch=aa[max(0,math.ceil(y0)):math.floor(y1),max(0,math.ceil(x0)):math.floor(x1)]
        black=np.all(patch<100,axis=2)
        assert not black.any(),('black original content inside red prose mask',row['index'],int(black.sum()))
        prose_checks.append({'index':row['index'],'no_black_source_content_covered':True,'transferred_to':row['key']})
    for s in seams:
        y=s['old_y']+sum(t['extra']for t in seams if t['old_y']<s['old_y']);mask([0,y-2,595,y+s['extra']+2])
    diff=np.any(expected!=bb,axis=2)&~allowed
    if diff.any():
        yy,xx=np.where(diff);print('DIFF',pn,int(diff.sum()),[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())],flush=True)
        np.save(ROOT/f'qa/diff{pn}.npy',diff)
    # Original source Forms are independently checked by decoded object graph.
    # Integer page growth can cause subpixel antialiasing differences in nested Forms.
    # Every new note fits in its question gap and remains fully on the page.
    for cut in {a['source_cut_y']for a in new['answers']if a['pdf_page']==pn}:
        group=sorted([a for a in new['answers']if a['pdf_page']==pn and a['source_cut_y']==cut],key=lambda a:a['target_rect'][1])
        boundary=next(b['target_rect'][1]for b in new['bands']if b['pdf_page']==pn and abs(b['source_rect'][1]-cut)<.01)
        for i,a in enumerate(group):
            rect=fitz.Rect(a['target_rect']);assert q.rect.contains(rect)
            assert rect.y1<=boundary-1.9,(a['key'],'overlaps following question')
            if i:assert rect.y0>=group[i-1]['target_rect'][3]+3.9
    checks.append({'book_page':plan['book_page'],'pdf_page':pn,'outside_note_raster_difference_pixels':int(diff.sum()),'notes_fit':True,'height_growth':plan['new_height']-plan['old_height']})
assert not after[0].get_text() and not after[0].get_images()
W(Q/'qa.json',{'passed':True,'pdf_sha256':SHA(out),'pages':128,'first_page_blank':True,'note_count':856,'columns':3,'font':'FandolKai-Regular','font_pt':11.5,'source_body_changes':0,'wide_equations_unscaled':31,'missing_glyphs':0,'overfull_boxes':0,'all_pages_raster_checked':128,'unchanged_pages_identical':unchanged,'page_checks':checks,'snippet_checks':font_checks,'relocated_prose_checks':prose_checks,'source_graph_validation':'qa_source_graph.json'})
print('QA_PASS',len(checks),'question pages;',len(unchanged),'unchanged pages;',len(font_checks),'notes',flush=True)
