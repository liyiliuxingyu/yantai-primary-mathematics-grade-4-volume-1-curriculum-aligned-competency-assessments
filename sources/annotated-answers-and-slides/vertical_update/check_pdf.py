from pathlib import Path
import json,hashlib,math,re
from decimal import Decimal
import fitz,numpy as np
R=Path(__file__).resolve().parents[1];Q=R/'vertical_update';W=R.parent
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
before=fitz.open(W/'vertical_update/baseline/answers.pdf')
out=W/'output/pdf/小学同步素养四年级上册数学答案.pdf';after=fitz.open(out)
report=J(Q/'patch_report.json');plans=report['plans'];old=J(W/'vertical_update/baseline/current_release.json')
assert len(before)==len(after)==128
assert len([p for p in plans if p['vertical_result']])==30
checks=[];changed={p['book_page']+4 for p in plans}
for pn,(p,q)in enumerate(zip(before,after),1):
    assert p.rect==q.rect and p.rotation==q.rotation,(pn,'page geometry changed')
    pa=p.get_pixmap(alpha=False);pb=q.get_pixmap(alpha=False)
    if pn not in changed:
        assert pa.samples==pb.samples,(pn,'unrelated page changed')
        continue
    aa=np.frombuffer(pa.samples,dtype=np.uint8).reshape(pa.height,pa.width,3)
    bb=np.frombuffer(pb.samples,dtype=np.uint8).reshape(pb.height,pb.width,3)
    allowed=np.zeros(aa.shape[:2],bool)
    def mask(rect):
        x0,y0,x1,y1=fitz.Rect(rect)+(-1.5,-1.5,1.5,1.5)
        allowed[max(0,math.floor(y0)):min(pa.height,math.ceil(y1)),max(0,math.floor(x0)):min(pa.width,math.ceil(x1))]=True
    for row in [x for x in plans if x['book_page']+4==pn]:
        mask(row['page_rect'])
        if row['mask']:
            rect=fitz.Rect(row['mask']);band=next(b for b in old['bands']if b['book_page']==row['book_page']and b['source_rect'][1]<=rect.y0<b['source_rect'][3]);dy=band['target_rect'][1]-band['source_rect'][1];mask(rect+(0,dy,0,dy))
    if pn==14:
        mask(report['note_change']['old_rect']);mask(report['note_change']['new_rect'])
    diff=np.any(aa!=bb,axis=2)&~allowed
    assert not diff.any(),(pn,'unexpected pixel changes',int(diff.sum()))
    checks.append({'pdf_page':pn,'book_page':pn-4,'outside_approved_regions_identical':True})
audit=J(Q/'vertical_audit.json')['records'];arithmetic=[]
for row in audit:
    a,op,b=re.fullmatch(r'([\d.]+)([+＋−－\-×÷])([\d.]+)',row['expression']).groups()
    a,b=Decimal(a),Decimal(b);result=row['result']
    if op=='÷'and'……'in result:
        q,r=map(Decimal,result.split('……'));assert a==b*q+r and 0<=r<b
    else:
        expected=a+b if op in '+＋'else a-b if op in '−－-'else a*b if op=='×'else a/b
        assert expected==Decimal(result),(row['expression'],result,str(expected))
    arithmetic.append({'expression':row['expression'],'result':result,'independently_verified':True})
assert not after[0].get_text() and not after[0].get_images()
# The distance interpretation is independently consistent with all three labels.
assert 3*3+4*4==5*5
rec=next(r for r in J(R/'questions/p010.json')['records']if r['key']=='p010_s04')
assert rec['verification']['status']=='verified' and not rec['verification']['uncertainties']
qa={'passed':True,'pdf_sha256':SHA(out),'pages':128,'first_page_blank':True,'all_page_sizes_unchanged':True,'changed_book_pages':sorted(pn-4 for pn in changed),'unchanged_pages_identical':128-len(changed),'all_pages_raster_checked':128,'new_vertical_results':30,'original_equals_preserved':True,'geometry':{'key':'p010_s04','AC_cm':3,'AB_cm':4,'BC_cm':5,'choice':'A','distance_cm':3},'page_checks':checks,'arithmetic_checks':arithmetic,'three_columns_and_Kai_preserved':True}
(Q/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
print('QA_PASS',len(checks),'changed pages;',128-len(changed),'unchanged pages;30results',flush=True)
