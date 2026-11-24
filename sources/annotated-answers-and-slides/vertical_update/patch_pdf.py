"""Correct AC's source label and append results to all vertical exercises."""
from pathlib import Path
import json,hashlib,sys,copy,math
import fitz,numpy as np
R=Path(__file__).resolve().parents[1];Q=R/'vertical_update';W=R.parent
J=lambda p:json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path.insert(0,str(R))
from bracket_update.patch_pdf import match_root,remove_page_draw,source_for_book,clip_source,graft

def main():
    baseline=W/'vertical_update/baseline/answers.pdf';old=J(W/'vertical_update/baseline/current_release.json')
    assert SHA(baseline)==old['sha256']
    local=J(Q/'local_additions.json')['records'];idx=J(Q/'compiled/snippet_index.json')
    notes_idx=J(R/'threecols_update/compiled/snippet_index.json')
    doc=fitz.open(baseline);compiled=fitz.open(Q/'compiled/详细题内答案.pdf')
    notes_pdf=fitz.open(R/'threecols_update/compiled/threecols.pdf');rel=copy.deepcopy(old)
    plans=[];masks=[]
    for book in sorted({p['book_page']for p in local}):
        page=doc[book+3];source=source_for_book(doc,page,old,book)
        rows=[x for x in local if x['book_page']==book]
        mm=[{'key':x['key'],'book_page':book,'rect':x['rect']}for x in rows if x.get('clear_to_white')]
        if mm:clip_source(doc,source,mm);masks.extend(mm)
        for p in rows:
            e=idx[p['id']];clip=e['clip'];origin=e['first_text_origin'];anchor=p['text_baseline_anchor']
            x=anchor[0]-(origin[0]-clip[0]);y=anchor[1]-(origin[1]-clip[1])
            target=fitz.Rect(x,y,x+e['ink_width'],y+e['ink_height'])
            assert (fitz.Rect(p['container_rect'])+(-.4,-.4,.4,.4)).contains(target),(p['id'],list(target),p['container_rect'])
            graft(doc,source,compiled,e,target,'Vertical_'+p['id'])
            meta=copy.deepcopy(p);meta.update({'target_rect':list(target),'restore_rect':p['rect']})
            rel['local_replacements'].append(meta)
            band=next(b for b in rel['bands']if b['book_page']==book and b['source_rect'][1]<=target.y0<b['source_rect'][3])
            dy=band['target_rect'][1]-band['source_rect'][1]
            plans.append({'id':p['id'],'key':p['key'],'book_page':book,'source_rect':list(target),'page_rect':list(target+(0,dy,0,dy)),'mask':p['rect']if p.get('clear_to_white')else None,'vertical_result':bool(p.get('vertical_result')),'result':p.get('result')})
    # The corrected interpretation stays in its existing three-column gap.
    answer=next(a for a in rel['answers']if a['key']=='p010_s04');page=doc[13]
    original=list(answer['target_rect']);root=match_root(doc,page,original);remove_page_draw(doc,page,root[1])
    e=notes_idx['p010_s04'];target=fitz.Rect(original[0],original[1],original[0]+e['ink_width'],original[1]+e['ink_height'])
    assert target.y1<=original[3]+.01
    page.show_pdf_page(target,notes_pdf,e['page']-1,clip=fitz.Rect(e['clip']),keep_proportion=False)
    answer['target_rect']=list(target)
    out=W/'output/pdf/小学同步素养四年级上册数学答案.pdf';doc.save(out,garbage=3,deflate=True);doc.close()
    rel.update({'run_name':'vertical_results_and_AC3','pdf':str(out),'sha256':SHA(out),'previous_pdf_sha256':SHA(baseline),'vertical_update':{'vertical_expressions':30,'vertical_question_pages':[11,15,58,63,90,94,103,107],'geometry_key':'p010_s04','AC_cm':3,'choice':'A','unchanged_page_sizes':True,'qa':'vertical_update/qa.json'}})
    rel['source_region_replacements']=rel.get('source_region_replacements',[])+masks
    write(R/'detailed_layout/current_release.json',rel);write(R/'answer_page_map.json',rel['mapping'])
    base_targets=J(R/'detailed_layout/base_local_targets.json')
    for p in rel['local_replacements']:
        if not any(x['id']==p['id']for x in base_targets['patches']):base_targets['patches'].append(p)
    write(R/'detailed_layout/base_local_targets.json',base_targets)
    write(Q/'source_masks.json',{'masks':masks})
    write(Q/'patch_report.json',{'pdf_sha256':SHA(out),'baseline_pdf_sha256':SHA(baseline),'plans':plans,'note_change':{'key':'p010_s04','old_rect':original,'new_rect':list(target)}})
    print('PDF_READY',SHA(out),len(plans),'new source annotations',flush=True)

if __name__=='__main__':main()
