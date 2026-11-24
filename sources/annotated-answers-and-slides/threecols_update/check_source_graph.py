"""Prove original non-note Form graphs survive the three-column reflow.

Indirect-object numbers and compression are serialization details. Compare
decoded dictionaries/streams recursively, and check each outer Form's vertical
translation independently against the recorded added question gaps.
"""
from pathlib import Path
import argparse, hashlib, json, math, re
import fitz
from pypdf import PdfReader
from pypdf.generic import IndirectObject, DictionaryObject, ArrayObject, StreamObject

R=Path(__file__).resolve().parents[1]
Q=R/'threecols_update'
J=lambda p:json.loads(Path(p).read_text())
SHA=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def roots(doc,page):
    used=set(re.findall(rb'/([A-Za-z0-9_]+)\s+Do\b',page.read_contents()))
    return {name:(xref,list(fitz.Rect(box)*page.transformation_matrix))
            for xref,name,parent,box in page.get_xobjects()
            if not parent and name.encode() in used}


def near(a,b,tolerance=.004):
    return len(a)==len(b) and max(abs(x-y)for x,y in zip(a,b))<tolerance


def matrix(doc,xref):
    kind,value=doc.xref_get_key(xref,'Matrix')
    if kind=='null':return [1,0,0,1,0,0]
    assert kind=='array'
    values=[float(x)for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][-+]?\d+)?',value)]
    assert len(values)==6
    return values


class GraphComparator:
    def __init__(self,before,after):
        self.before=before;self.after=after
        self.seen=set();self.streams={};self.compared_nodes=0

    def object(self,reader,xref):
        return reader.get_object(IndirectObject(xref,0,reader))

    def stream_hash(self,obj,side):
        ref=getattr(obj,'indirect_reference',None)
        key=(side,ref.idnum if ref else id(obj))
        if key not in self.streams:
            self.streams[key]=hashlib.sha256(obj.get_data()).hexdigest()
        return self.streams[key]

    def compare(self,a,b,path='root',root=False):
        if isinstance(a,IndirectObject) or isinstance(b,IndirectObject):
            if not(isinstance(a,IndirectObject)and isinstance(b,IndirectObject)):
                return {'path':path,'reason':'indirection_kind_changed'}
            pair=(a.idnum,a.generation,b.idnum,b.generation,root)
            if pair in self.seen:return None
            self.seen.add(pair);self.compared_nodes+=1
            return self.compare(a.get_object(),b.get_object(),path,root)
        if isinstance(a,DictionaryObject) or isinstance(b,DictionaryObject):
            if not(isinstance(a,DictionaryObject)and isinstance(b,DictionaryObject)):
                return {'path':path,'reason':'dictionary_kind_changed'}
            ignored={'/Length','/Filter'}|({'/Matrix'}if root else set())
            ka=set(a)-ignored;kb=set(b)-ignored
            if ka!=kb:return {'path':path,'reason':'dictionary_keys_changed','old_only':sorted(ka-kb),'new_only':sorted(kb-ka)}
            if isinstance(a,StreamObject)!=isinstance(b,StreamObject):
                return {'path':path,'reason':'stream_kind_changed'}
            if isinstance(a,StreamObject):
                if self.stream_hash(a,'before')!=self.stream_hash(b,'after'):
                    return {'path':path,'reason':'decoded_stream_changed'}
            for key in sorted(ka):
                issue=self.compare(a.raw_get(key),b.raw_get(key),path+str(key))
                if issue:return issue
            return None
        if isinstance(a,ArrayObject) or isinstance(b,ArrayObject):
            if not(isinstance(a,ArrayObject)and isinstance(b,ArrayObject))or len(a)!=len(b):
                return {'path':path,'reason':'array_changed'}
            for i,(x,y)in enumerate(zip(a,b)):
                issue=self.compare(x,y,path+f'[{i}]')
                if issue:return issue
            return None
        if a!=b:return {'path':path,'reason':'scalar_changed','before':str(a),'after':str(b)}
        return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--before',type=Path,default=R.parent/'downloads/小学同步素养四年级上册数学答案.pdf')
    parser.add_argument('--after',type=Path,default=R.parent/'output/pdf/小学同步素养四年级上册数学答案.pdf')
    args=parser.parse_args()
    old=J(Q/'baseline_release.json');current=J(R/'detailed_layout/current_release.json')
    plans={x['book_page']:x for x in J(Q/'layout_plan.json')}
    assert SHA(args.before)==old['sha256'] and SHA(args.after)==current['sha256']
    bd,ad=fitz.open(args.before),fitz.open(args.after)
    br,ar=PdfReader(args.before),PdfReader(args.after)
    graph=GraphComparator(br,ar);checks=[];issues=[];nroots=0
    for book in range(1,109):
        pn=next(m['answer_pdf_page']for m in old['mapping']if m['book_page']==book)
        broots,aroots=roots(bd,bd[pn-1]),roots(ad,ad[pn-1])
        note_names=set()
        for note in [a for a in old['answers']if a['book_page']==book]:
            matches=[name for name,(_,rect)in broots.items()if near(rect,note['target_rect'])]
            assert len(matches)==1,(book,note['key'],matches)
            note_names.add(matches[0])
        pp=plans[book];extra=pp['new_height']-pp['old_height']
        pagecheck={'book_page':book,'pdf_page':pn,'non_note_roots':[]}
        for name,(bx,rect)in broots.items():
            if name in note_names:continue
            nroots+=1
            if name not in aroots:
                issues.append({'book_page':book,'root':name,'reason':'original_root_missing'});continue
            ax=aroots[name][0]
            bm,am=matrix(bd,bx),matrix(ad,ax)
            expected=list(bm)
            shift=sum(s['extra']for s in pp['seams']if s['old_y']<=rect[1]+.003)
            expected[5]+=extra-shift
            matrix_ok=near(expected,am,.00003)
            if not matrix_ok:issues.append({'book_page':book,'root':name,'reason':'unexpected_matrix_change','before':bm,'after':am,'expected':expected})
            problem=graph.compare(IndirectObject(bx,0,br),IndirectObject(ax,0,ar),root=True)
            if problem:issues.append({'book_page':book,'root':name,**problem})
            pagecheck['non_note_roots'].append({'name':name,'decoded_graph_identical':problem is None,'matrix_matches_recorded_vertical_translation':matrix_ok,'expected_shift':extra-shift})
        checks.append(pagecheck)
    report={'passed':not issues,'baseline_pdf_sha256':SHA(args.before),'pdf_sha256':SHA(args.after),'question_pages':108,'non_note_original_roots_checked':nroots,'recursive_indirect_nodes_checked':graph.compared_nodes,'decoded_streams_hashed':len(graph.streams),'ignored_serialization_keys':['/Length','/Filter'],'outer_matrix_checked_separately':True,'original_black_questions_diagrams_and_calculation_forms_unchanged':not issues,'permitted_original_prose_masks':len(J(Q/'original_prose.json')['records']),'prose_mask_scope':'Separate white page overlays only; original Form graphs are retained unchanged.','checks':checks,'issues':issues}
    (Q/'qa_source_graph.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['passed','question_pages','non_note_original_roots_checked','recursive_indirect_nodes_checked','decoded_streams_hashed']},ensure_ascii=False),flush=True)
    assert report['passed'],issues[:5]


if __name__=='__main__':main()
