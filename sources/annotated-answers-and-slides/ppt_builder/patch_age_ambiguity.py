#!/usr/bin/env python3
"""Apply question-4 classroom answer B, preserving native IDs and timing.

The legacy filename is retained for existing build commands. Current rules
replace its former B,D patch; original option D stays in the question.
"""
from pathlib import Path
import argparse, copy, importlib.util, json, re, sys, zipfile
from lxml import etree as E
PROJECT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(PROJECT/'followup_style/ppt'),str(PROJECT/'ppt_builder')]
spec=importlib.util.spec_from_file_location('native_patch_q4',PROJECT/'ppt_average/build/native_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def apply(source,output,rules,manifest):
    output=Path(output);source=Path(source);proof=[];changes={}
    rows={s['slide']:s for s in manifest['slides']}
    with zipfile.ZipFile(source) as z:
        for op in rules['edits']:
            ui=op['slide'];row=rows[ui]
            assert row['record_key']=='p078_s04'
            partnum=row.get('original_part_number',op['part_number'])
            assert partnum==op['part_number']
            name=f'ppt/slides/slide{partnum}.xml';b=z.read(name);root=E.fromstring(b)
            ids=m.logical_ids(root);old=m.find_shape(root,op['name'])
            assert m.c_nv(old).get('id')==str(op['shape_id'])
            result=m.patch_text(root,{'name':op['name'],'text':'\n'.join(op['lines']),'points':32,'color':'C00000','rect':op['rect_px']})
            current=m.find_shape(root,op['name'])
            if op.get('center'):
                current.find('p:txBody/a:bodyPr',m.NS).set('anchor','ctr')
                for p in current.findall('p:txBody/a:p/a:pPr',m.NS):p.set('algn','ctr')
            m.assert_preserved_ids(ids,m.logical_ids(root));nb=m.xml(root);t=m.timing(b)
            if t:nb=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:t,nb,flags=re.S)
            assert m.timing(nb)==t;changes[name]=nb
            proof.append({'slide':ui,'part_number':partnum,'record_key':'p078_s04','shape_id':op['shape_id'],**result,'native_timing_unchanged':True})
            row.pop('age_ambiguity_patch',None)
            row['q4_teaching_answer_patch']={'answer':'B','reason':rules['mathematical_reason'],'name':op['name'],'lines':op['lines'],'rect_px':op['rect_px'],'points':32}
            bind=next((b for b in row['bindings'] if b['name']==op['name']),None)
            br={'name':op['name'],'rect':dict(zip(('left','top','width','height'),op['rect_px']))}
            if bind:bind.update(br)
            else:row['bindings'].append(br)
            if op['kind']=='answer_letters':
                for slot in row['answer_slots']:
                    if slot['target'].removeprefix('alt:')==op['name']:slot.update(target=op['name'],answer='B',note=rules['mathematical_reason'])
        output.parent.mkdir(parents=True,exist_ok=True)
        assert not output.exists(),output
        with zipfile.ZipFile(output,'w') as f:
            for info in z.infolist():f.writestr(copy.copy(info),changes.get(info.filename,z.read(info.filename)))
        with zipfile.ZipFile(output) as f:
            assert f.testzip() is None
            delta=[n for n in z.namelist() if z.read(n)!=f.read(n)]
            assert sorted(delta)==sorted(changes)
            count=0
            for n in z.namelist():
                if re.fullmatch(r'ppt/slides/slide\d+\.xml',n):
                    before=z.read(n);after=f.read(n);count+=1
                    assert m.timing(before)==m.timing(after)
                    m.assert_preserved_ids(m.logical_ids(E.fromstring(before)),m.logical_ids(E.fromstring(after)))
            assert count==433
    manifest['final_pptx_sha256']=m.sha(output.read_bytes());manifest['q4_teaching_answer_revision']='ppt_q4/qa_final.json'
    return {'passed':True,'source':str(source),'source_sha256':m.sha(source.read_bytes()),'output':str(output),'output_sha256':m.sha(output.read_bytes()),'total_slides':433,'changed_parts':delta,'changed_slides':[126,127],'unchanged_slide_count':431,'all_other_package_parts_byte_identical':True,'all_slide_timing_xml_byte_identical':True,'all_original_shape_ids_names_order_preserved':True,'changes':proof},manifest

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--rules',type=Path,default=Path(__file__).with_name('age_ambiguity_rules.json'));ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output-manifest',type=Path,required=True);ap.add_argument('--report',type=Path,required=True)
    args=ap.parse_args();rules=json.loads(args.rules.read_text());manifest=json.loads(args.manifest.read_text())
    result,manifest=apply(args.input,args.output,rules,manifest)
    args.output_manifest.parent.mkdir(parents=True,exist_ok=True);args.output_manifest.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
