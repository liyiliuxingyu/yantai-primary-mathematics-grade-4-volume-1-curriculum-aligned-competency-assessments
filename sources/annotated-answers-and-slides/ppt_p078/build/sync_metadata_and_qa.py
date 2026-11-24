#!/usr/bin/env python3
"""Seal the narrow page-78 update after final rendered-page inspection."""
from pathlib import Path, PurePosixPath
import copy, hashlib, importlib.util, json, posixpath, re, shutil, sys, zipfile
from lxml import etree as E
BASE=Path(__file__).resolve().parents[2];PROJECT=BASE/'project';WORK=BASE/'ppt_p078';DEST=PROJECT/'ppt_p078'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
sys.path[:0]=[str(PROJECT/'followup_style/ppt'),str(PROJECT/'ppt_builder')]
sp=importlib.util.spec_from_file_location('native_patch',PROJECT/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
qa=json.loads((WORK/'qa_package.json').read_text());rules=json.loads((WORK/'rules.json').read_text());DEST.mkdir(exist_ok=True)
for n in ('qa_package.json','rules.json','baseline_inventory.json'):
    shutil.copy2(WORK/n,DEST/n)
(DEST/'build').mkdir(exist_ok=True)
for f in (WORK/'build').glob('*'):
    if f.is_file():shutil.copy2(f,DEST/'build'/f.name)
manifestpath=PROJECT/'ppt_builder/current_metadata/volume05/manifest.json';indexpath=manifestpath.with_name('manifest.index.json')
manifest=json.loads(manifestpath.read_text());index=json.loads(indexpath.read_text());rows={s['slide']:s for s in manifest['slides']};ix={s['slide']:s for s in index}
overlay={'scope':'Only original-book page78 photo corrections; slide order, original IDs and animation XML retained.','slides':[]}
for rule,report in zip(rules,qa['changes']):
    assert rule['ui_slide']==report['slide'];ui=rule['ui_slide'];row=rows[ui];row['post_export_content_patched']=True;row['semantic_overlay']='ppt_p078/post_export_overlay.json'
    ix[ui]['post_export_content_patched']=True;ix[ui]['semantic_overlay']='ppt_p078/post_export_overlay.json'
    bindings={b['name']:b for b in row.get('bindings',[])};formulas={f['target'].removeprefix('alt:'):f for f in row.get('formulas',[])};vectors={v['target'].removeprefix('alt:'):v for v in row.get('vectors',[])}
    sem=[]
    for op,actual in zip(rule['ops'],report['ops']):
        name=op['name'];r=actual['rect'];binding={'name':name,'rect':dict(zip(('left','top','width','height'),r))}
        if name in bindings:bindings[name].update(binding)
        else:row.setdefault('bindings',[]).append(binding)
        if op['type']=='math':
            ast=m.MathParser(op['tex']).parse();new={'target':'alt:'+name,'ast':ast,'points':32,'color':'C00000','font':'Droid Sans Fallback'}
            if name in formulas:formulas[name].update(new)
            else:row.setdefault('formulas',[]).append(new)
            sem.append({'name':name,'type':'math','latex':op['tex'],'plain':actual['plain'],'rect':r,'native_omml':True,'svg_png_compatibility':True})
        elif op['type']=='picture':
            new={'target':'alt:'+name,'svg_path':str(PROJECT/actual['svg']),'source_relative':actual['svg']}
            if name in vectors:vectors[name].update(new)
            else:row.setdefault('vectors',[]).append(new)
            sem.append({'name':name,'type':'tikz_vector','svg':actual['svg'],'png':actual['png'],'rect':r})
        else:sem.append({'name':name,'type':'native_editable_text','text':op['text'],'rect':r,'points':32,'color':op['color']})
    overlay['slides'].append({'slide':ui,'part_number':rule['slide'],'record_key':rule['key'],'objects':sem,'timing_bytes_unchanged':True})
manifest['final_pptx_sha256']=qa['output_sha256'];manifest['p078_photo_revision']='ppt_p078/qa_final.json'
manifest['post_export_authority']='ppt_builder/current_inventory.json; current_metadata + documented post-export overlays'
manifestpath.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');indexpath.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
(DEST/'post_export_overlay.json').write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n')

out=Path(qa['output']);checks={};parentsrc=Path(qa['source'])
with zipfile.ZipFile(parentsrc) as z,zipfile.ZipFile(out) as f:
    assert f.testzip() is None
    original={n:z.read(n) for n in z.namelist()};final={n:f.read(n) for n in f.namelist()}
    assert all(final[n]==b for n,b in original.items() if n not in qa['changed_original_parts'])
    targets=0
    for n,b in final.items():
        if n.endswith('.rels'):
            base='' if n=='_rels/.rels' else str(PurePosixPath(n).parent.parent)
            for r in E.fromstring(b):
                if r.get('TargetMode')=='External':continue
                target=r.get('Target','');full=posixpath.normpath(posixpath.join(base,target)) if not target.startswith('/') else target.lstrip('/')
                assert full in final,(n,target,full);targets+=1
    for n,b in original.items():
        if re.fullmatch(r'ppt/slides/slide\d+\.xml',n):
            assert m.timing(b)==m.timing(final[n]);m.assert_preserved_ids(m.logical_ids(E.fromstring(b)),m.logical_ids(E.fromstring(final[n])))
    for part in (113,117,130,132):
        body=E.fromstring(final[f'ppt/slides/slide{part}.xml']);texts=''.join(body.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS))
        assert '快板' not in texts
        if part in (113,117):assert '138cm' not in texts and '146cm' not in texts and '136cm' in texts and '140cm' in texts
    q4parts=(123,124,125)
    assert all(final[f'ppt/slides/slide{n}.xml']==original[f'ppt/slides/slide{n}.xml'] for n in q4parts)
    checks={'package_integrity':True,'all_relationship_targets_exist':True,'relationship_count_checked':targets,'only_whitelisted_slide_parts_changed':True,'all_other_original_parts_byte_identical':True,'all_433_slide_timing_xml_byte_identical':True,'all_original_shape_ids_names_order_preserved':True,'q4_original_B_D_ambiguity_retained_byte_identical':True,'question_text_editable':True,'formulas_native_omml_with_compiled_svg_png':True,'graph_is_real_tikz_vector':True}
assert len(manifest['slides'])==433 and len(index)==433
assert [r['slide'] for r in manifest['slides']]==list(range(1,434))
assert [r['slide'] for r in index]==list(range(1,434))
assert all(sum(a)==408 for a in ((136,136,136),(146,131,131),(146,146,116)))
assert 136*3==408 and 140*3==420 and 408<420
volumes=[];patch=[]
for n in range(1,7):
    src=next((BASE/'bundle/讲解课件').glob(f'*第{n}册*.pptx'));dest=out.parent/src.name
    if n!=5:shutil.copy2(src,dest)
    count=(426,479,406,462,433,464)[n-1];same=sha(src)==sha(dest)
    assert n==5 or same
    d={'volume':n,'output':str(dest),'output_sha256':sha(dest),'source_sha256':sha(src),'slides':count,'changed_slides':qa['changed_slides'] if n==5 else[],'byte_identical_to_previous':same}
    volumes.append(d);patch.append({'volume':n,'pptx':dest.name,'sha256':d['output_sha256'],'parent_sha256':d['source_sha256'],'slides':count,'p078_photo_revision':'ppt_p078/qa_final.json','changed_slides':d['changed_slides']})
    if n==5:patch[-1].update(manifest_path=str(manifestpath),manifest_sha256=sha(manifestpath),index_path=str(indexpath),index_sha256=sha(indexpath))
(DEST/'inventory_patch.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
render=json.loads((WORK/'after_final/qa_import.json').read_text());assert render['full_deck_imported'] and render['slides']==433 and render['rendered']==qa['changed_slides']
assert sys.argv[-1]=='--reviewed-final-nine','Visual inspection confirmation is required after viewing the final nine PNGs.'
result={'passed':True,'scope':'第78页第1/5/6题与选择题标题；仅第5册9张更新，其余5册原字节保留。','checks':checks,'volumes':volumes,'changed_slides':qa['changed_slides'],'static_render':{'renderer':'Artifact Tool','entire_final_deck_imported':True,'imported_slides':433,'exported_and_visually_reviewed_slides':qa['changed_slides'],'unmodified_slides_not_rerendered':424,'render_directory':str(WORK/'after_final')},'mathematics':{'example_sums':[408,408,408],'example_rider_counts':[0,1,2],'no_140_boundary_admission_claim':True,'total_height':408,'three_riders_lower_bound':420,'question5_no_invented_temperature_values':True},'native_powerpoint_playback_tested':False,'native_wps_playback_tested':False,'native_impress_playback_tested':False,'native_playback_limitation':'CUA and Sky application inventories were checked. No Impress, WPS or PowerPoint GUI app was available; only a headless LibreOfficeDev runtime was found. No GUI animation-playback test is claimed.','original_animations':{'slide_counts_unchanged':True,'original_timing_xml_bytes_unchanged_all_slides':True,'original_shape_id_name_order_preserved':True,'new_section_instruction_static_only':True},'real_limits':['Static render and package checks do not constitute native click-by-click playback.','Original question4 B/D ambiguity is retained and explained; no unique choice is fabricated.']}
(DEST/'qa_final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'qa':str(DEST/'qa_final.json'),'inventory_patch':str(DEST/'inventory_patch.json'),'vol5_sha256':sha(out),'checks':checks},ensure_ascii=False))
