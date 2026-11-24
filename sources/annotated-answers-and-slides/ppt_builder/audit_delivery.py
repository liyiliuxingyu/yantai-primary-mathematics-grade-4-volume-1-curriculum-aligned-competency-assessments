#!/usr/bin/env python3
"""Audit actual finalized packages against the 108-page reviewed source.

This is a package/content audit, never a slideshow playback claim.
"""
import argparse, csv, hashlib, json, re, zipfile
from collections import Counter
from pathlib import Path
from lxml import etree as E
from PIL import Image
import fitz

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006'}
sha=lambda b:hashlib.sha256(b).hexdigest()
canon=lambda x:sha(json.dumps(x,ensure_ascii=False,sort_keys=True).encode())
CORE_FIELDS=('id','kind','question_latex','answer_latex','options','tables','diagrams','animation','animations','requires_diagram','requires_animation')
core=lambda x:canon({k:x.get(k) for k in CORE_FIELDS})

def audit(version):
    issues=[]; volumes=[]; indexes=[]; diagrams=[]; seen=set(); table_total=0; oral_seen=set(); vertical_seen=set(); given_vertical=set();legacy_vertical_arrays=0; expected_slots=set(); actual_slots=set(); unresolved=[]; expected_table=set(); actual_table=set(); variants_seen=set();native_totals=Counter();registration_totals=Counter();record_clicks=Counter();actual_record_clicks=Counter();operations=[];teaching_moves=[];inline_marks=[]
    current={r['key']:r for p in sorted((WORK/'questions').glob('p[0-9][0-9][0-9].json')) for r in json.loads(p.read_text())['records']}
    freeze_path=WORK/'source_release_freeze.json';freeze=json.loads(freeze_path.read_text()) if freeze_path.exists() else {}
    freeze_mismatch=[]
    for relative,expected in freeze.get('source_files',{}).items():
        path=WORK/relative
        if not path.exists() or sha(path.read_bytes())!=expected:freeze_mismatch.append(relative)
    if not freeze:issues.append({'final_source_release_freeze_missing':True})
    if freeze_mismatch:issues.append({'final_source_release_freeze_mismatch':freeze_mismatch})
    oral=json.loads((HERE/'oral_calculations.json').read_text())['records']
    vertical=json.loads((HERE/'vertical_calculations.json').read_text())['records']
    for n in range(1,7):
        build=HERE/f'build{n:02d}_{version}'
        required=['progress.json','normalized.json','ready.json','manifest.json','manifest.index.json','package_report.json']
        missing=[x for x in required if not (build/x).exists()]
        if missing:issues.append({'volume':n,'missing':missing});continue
        status=json.loads((build/'progress.json').read_text());metadata=Path(status.get('metadata_dir',str(build)));data=json.loads((metadata/'normalized.json').read_text())
        manifest=json.loads((metadata/'manifest.json').read_text()); index=json.loads((metadata/'manifest.index.json').read_text())
        package=json.loads((metadata/'package_report.json').read_text())
        final=Path(status.get('final',str(build/'validated'/f'小学四上同步素养卷第{n}册讲解课件答案.pptx')))
        receipt=Path(status.get('receipt',str(build/'validation_receipt.json')))
        if not receipt.exists():receipt=HERE/'qa'/f'volume{n:02d}_{version}.validation.json'
        if status['stage']!='complete':issues.append({'volume':n,'stage':status['stage']})
        if not final.exists() or not receipt.exists():issues.append({'volume':n,'missing_final_or_receipt':True});continue
        rec=json.loads(receipt.read_text()); finalsha=sha(final.read_bytes())
        if rec.get('finalSha256')!=finalsha:issues.append({'volume':n,'receipt_hash_mismatch':True})
        if package['issues']:issues.append({'volume':n,'package_issues':package['issues']})
        rawkeys=set()
        for r in data['records']:
            k=r['key']; rawkeys.add(k)
            if k in seen:issues.append({'duplicate_record':k})
            seen.add(k)
            if r.get('teaching_order'):teaching_moves.append(k)
            record_slides=[s for s in manifest['slides'] if s['record_key']==k]
            record_clicks[k]+=sum(bool(c.get('effects')) for s in record_slides for c in s['clicks'])
            if k not in current or core(r['raw'])!=core(current[k]):issues.append({'stale_record':k})
            source_tables=r['raw'].get('tables',[])
            normalized_tables=[b for b in r['blocks'] if b['type']=='table' and b.get('source_table') is not None]
            table_total+=len(source_tables)
            if len(source_tables)!=len(normalized_tables):issues.append({'table_loss':k,'source':len(source_tables),'normalized':len(normalized_tables)})
            for a,b in zip(source_tables,normalized_tables):
                if a!=b['source_table']:issues.append({'table_fields_changed':k})
                if a.get('title') and not b.get('title_runs'):issues.append({'table_title_loss':k})
                if a.get('footer') and not b.get('footer_runs'):issues.append({'table_footer_loss':k})
            for entry in json.loads((HERE/'final_answers.json').read_text()).get('records',{}).get(k,{}).get('table_final_answers',[]):expected_table.add((k,entry['table_index'],entry['row_index'],entry['column_index']))
            for slot in r.get('answer_slots',[]):
                if slot.get('mapped') or slot.get('unresolved'):expected_slots.add((k,slot['slot_index']))
                if not slot.get('mapped') and not slot.get('skip'):unresolved.append({'record_key':k,**slot})
            for b in r['blocks']:
                if b.get('review_start') and b.get('review_label') not in ('原题回填','原表回填'):variants_seen.add((k,b.get('review_label')))
                if b['type']=='vertical':
                    vertical_seen.add((k,b['calculation'].get('id',canon(b['calculation']))))
                    if b['role']=='question':given_vertical.add((k,b['calculation'].get('id',canon(b['calculation']))))
                if k in vertical and vertical[k].get('replace_array') and b.get('from_math_array'):
                    legacy_vertical_arrays+=1;issues.append({'legacy_vertical_array_survived':k,'role':b['role']})
                if b.get('subquestion_key'):oral_seen.add(b['subquestion_key'])
                if b['type']=='diagram':
                    target=lambda name:str(name).removeprefix('alt:').startswith(b['key']+'_')
                    locations=[s['slide'] for s in manifest['slides'] if any(target(t) for t in [*[x['name'] for x in s.get('bindings',[])],*[e['target'] for c in s['clicks'] for e in c['effects']]])]
                    diagrams.append({'volume':n,'book_page':r['book_page'],'source_page':r['source_page'],'question_id':r['id'],'record_key':k,'diagram_name':b.get('name',b['key']),'block_key':b['key'],'role':b['role'],'slides':locations,'source_json':f"questions/p{r['book_page']:03d}.json",'tikz':b.get('tikz'),'glyph_image':b.get('glyph_image'),'asset_id':b.get('asset_id'),'native_animation_type':b.get('animation',{}).get('type')})
            native_blocks=[b for b in r['blocks'] if b.get('animation')]
            has_drawing_command=bool(re.search(r'画出|补画|画一|画图|作出|作高|画高|补全|画.*?的高|画.*?垂线|画.*?对称轴',r['raw'].get('question_latex','')))
            if r['raw'].get('kind')=='drawing' or native_blocks or has_drawing_command and r['raw'].get('diagrams'):
                native_scene_rows=[{**x,'slide':s['slide']} for s in record_slides for x in s.get('scene_registrations',[])]
                answer_figures=[{'diagram_name':d['diagram_name'],'slides':d['slides']} for d in diagrams if d['record_key']==k and d['role']=='answer' and not d['native_animation_type']]
                verification=r['raw'].get('verification',{})
                operations.append({'volume':n,'book_page':r['book_page'],'source_page':r['source_page'],'question_id':r['id'],'record_key':k,'kind':r['raw'].get('kind'),'native_scenes':native_scene_rows,'answer_diagram_click_reveals':answer_figures,'lecture_clicks':record_clicks[k],'verification_status':verification.get('status'),'conditional_notes':verification.get('uncertainties',[]),'verification_reason':verification.get('reason'),'conditional_explanation_latex':r['raw']['answer_latex'] if verification.get('status')!='verified' else None,'coverage':'native_process' if native_scene_rows else 'analysis_then_answer_diagram_reveal' if answer_figures else 'text_formula_steps','scope':'Answer-diagram reveal means a staged vector answer figure; it is not a claim of continuous native geometric motion.'})
        for name in ['vertical','oral']:
            expected=sha((HERE/f'{name}_calculations.json').read_bytes())
            if data.get(f'{name}_metadata_sha256')!=expected:issues.append({'volume':n,'stale_metadata':name})
        if data.get('math_display_sha256')!=sha((HERE/'math_display_overrides.json').read_bytes()):issues.append({'volume':n,'stale_metadata':'math_display'})
        applicable_rules=json.loads((HERE/'teaching_order.json').read_text())['records']
        if any(r.get('teaching_order')!=applicable_rules.get(r['key']) for r in data['records']):issues.append({'volume':n,'stale_metadata':'applicable_teaching_order_rules'})
        if {x['record_key'] for x in index}!=rawkeys:issues.append({'volume':n,'index_coverage_mismatch':True})
        for slide in manifest['slides']:
            for slot in slide.get('answer_slots',[]):actual_slots.add((slide['record_key'],slot['slot_index']))
            for cell in slide.get('table_answers',[]):actual_table.add((slide['record_key'],cell['table_index'],cell['row_index'],cell['column_index']))
            for scene in slide.get('scene_registrations',[]):registration_totals[scene['registration_method']]+=1
            for mark in slide.get('inline_final_marks',[]):
                inline_marks.append({'record_key':slide['record_key'],'slide':slide['slide'],**mark})
                if not slide['clicks'] or not any(e['target']==mark['target'] and e['type']=='appear' for e in slide['clicks'][-1]['effects']):issues.append({'inline_final_mark_is_not_last_click':mark['target']})
        answer_path=HERE/'final_answers.json'
        if answer_path.exists() and data.get('final_answers_sha256')!=sha(answer_path.read_bytes()):issues.append({'volume':n,'stale_metadata':'final_answers'})
        with zipfile.ZipFile(final) as z:
            if z.testzip():issues.append({'volume':n,'zip_crc':False})
            slide_files=sorted((p for p in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',p)),key=lambda p:int(re.search(r'(\d+)\.xml',p).group(1)))
            if len(slide_files)!=len(index):issues.append({'volume':n,'slide_count_mismatch':True})
            for i,p in enumerate(slide_files):
                root=E.fromstring(z.read(p)); info=index[i]
                logical=lambda node:not any(a.tag=='{'+NS['mc']+'}Fallback' for a in node.iterancestors())
                title=root.xpath('.//p:sp[p:nvSpPr/p:cNvPr[@name="title"]]',namespaces=NS)
                titletext=''.join(title[0].xpath('.//a:t/text()',namespaces=NS)) if len(title)==1 else ''
                if f"原书第{info['book_page']}页" not in titletext or info['question_id'] not in titletext:issues.append({'volume':n,'slide':i+1,'title_loss':titletext})
                ids=[x.get('id') for x in root.xpath('.//p:cNvPr',namespaces=NS) if logical(x)]
                targets=root.xpath('.//p:spTgt/@spid',namespaces=NS)
                native_totals['shape_ids']+=len(ids);native_totals['timing_targets']+=len(targets)
                native_totals['omml']+=sum(logical(x) for x in root.xpath('.//m:oMath',namespaces=NS))
                native_totals['clicks']+=len(root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=NS))
                for click in root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=NS):
                    effective=click.xpath('.//p:animMotion|.//p:animRot|.//p:animEffect|.//p:set[p:to/p:strVal[@val="visible"]]',namespaces=NS)
                    if effective:actual_record_clicks[info['record_key']]+=1
                native_totals['native_motion']+=len(root.xpath('.//p:animMotion',namespaces=NS));native_totals['native_rotation']+=len(root.xpath('.//p:animRot',namespaces=NS))
                if len(ids)!=len(set(ids)) or not set(targets).issubset(set(ids)):issues.append({'volume':n,'slide':i+1,'animation_target_invalid':True})
                if any(0xE000<=ord(c)<0xE400 for c in ''.join(root.itertext())):issues.append({'volume':n,'slide':i+1,'unresolved_marker':True})
                if any(not ''.join(x.itertext()).strip() for x in root.xpath('.//m:oMath',namespaces=NS)):issues.append({'volume':n,'slide':i+1,'empty_formula':True})
                if not (build/'previews'/f'slide_{i+1:04d}.png').exists():issues.append({'volume':n,'slide':i+1,'preview_missing':True})
                indexes.append({'volume':n,'filename':final.name,**info})
            # Critical original table facts must survive in editable text, not only images.
            alltext=''.join(''.join(E.fromstring(z.read(p)).xpath('.//a:t/text()|.//m:t/text()',namespaces=NS)) for p in slide_files)
            for k,word in [('p007_s08','230元'),('p022_s06','用时2小时'),('p048_s04','10月31日')]:
                if k in rawkeys and word not in alltext:issues.append({'volume':n,'missing_critical_table_condition':k,'text':word})
        static=Path(status.get('actual_static_dir',str(build/'actual_static_export')))
        actual=list(static.glob('slide-*.png'))
        provenance=static/'export_provenance.json'
        if not provenance.exists() or json.loads(provenance.read_text()).get('source_sha256')!=finalsha:issues.append({'volume':n,'static_export_source_hash_mismatch':True})
        if len(actual)!=len(index):issues.append({'volume':n,'actual_static_png_count':len(actual),'expected':len(index)})
        for i in range(1,len(index)+1):
            png=static/f'slide-{i:03d}.png'
            try:
                with Image.open(png) as im:
                    if im.size!=(1280,720):issues.append({'volume':n,'slide':i,'actual_png_size':im.size})
                    im.verify()
            except Exception as e:issues.append({'volume':n,'slide':i,'actual_png_invalid':str(e)})
        static_pdf=static/(final.stem+'.pdf')
        if not static_pdf.exists():issues.append({'volume':n,'actual_static_pdf_missing':True})
        else:
            with fitz.open(static_pdf) as pdf:
                if pdf.page_count!=len(index):issues.append({'volume':n,'actual_static_pdf_pages':pdf.page_count})
        volumes.append({'volume':n,'records':len(rawkeys),'slides':len(index),'formulas':sum(len(s['formulas']) for s in manifest['slides']),'clicks':sum(len(s['clicks']) for s in manifest['slides']),'sha256':finalsha,'final':str(final),'previews':str(build/'previews'),'receipt':str(receipt),'index_path':str((metadata/'manifest.index.json').resolve()),'actual_static_dir':str(static.resolve()),'export_provenance':str(provenance.resolve())})
    if seen!=set(current):issues.append({'record_coverage_missing':sorted(set(current)-seen),'unexpected':sorted(seen-set(current))})
    no_clicks=sorted(k for k in seen if actual_record_clicks[k]<1)
    if no_clicks:issues.append({'records_without_effective_click':no_clicks})
    if dict(record_clicks)!=dict(actual_record_clicks):issues.append({'actual_native_click_count_does_not_match_manifest_by_record':True})
    expected_oral={q['key'] for r in oral.values() for q in r['subquestions']}
    if expected_oral!=oral_seen:issues.append({'oral_coverage_missing':sorted(expected_oral-oral_seen),'unexpected':sorted(oral_seen-expected_oral)})
    expected_vertical={(k,c.get('id',canon(c))) for k,r in vertical.items() for c in r['calculations']}
    expected_given={(k,c.get('id',canon(c))) for k,r in vertical.items() for c in r['calculations'] if c['role']=='question'}
    if expected_vertical!=vertical_seen:issues.append({'native_vertical_coverage_missing':sorted(expected_vertical-vertical_seen),'unexpected':sorted(vertical_seen-expected_vertical)})
    if expected_given!=given_vertical:issues.append({'given_vertical_coverage_missing':sorted(expected_given-given_vertical)})
    if expected_slots!=actual_slots:issues.append({'answer_slot_missing':sorted(expected_slots-actual_slots),'unexpected':sorted(actual_slots-expected_slots)})
    if expected_table!=actual_table:issues.append({'table_cell_missing':sorted(expected_table-actual_table),'unexpected':sorted(actual_table-expected_table)})
    finals=json.loads((HERE/'final_answers.json').read_text())['records'];expected_variants={(k,v['label']) for k,r in finals.items() for v in r.get('variants',[])}
    if expected_variants!=variants_seen:issues.append({'variant_missing':sorted(expected_variants-variants_seen),'unexpected':sorted(variants_seen-expected_variants)})
    expected_moves=set(json.loads((HERE/'teaching_order.json').read_text())['records'])
    if set(teaching_moves)!=expected_moves:issues.append({'teaching_conclusion_move_missing':sorted(expected_moves-set(teaching_moves))})
    if [(m['record_key'],m['anchor_text'],m['mark']) for m in inline_marks]!=[('p066_s01','平移','√')]:issues.append({'implicit_word_mark_coverage':inline_marks})
    result={'table_final_cells':len(actual_table),'linked_variants':len(variants_seen),'slot_candidates':sum(len(r['final_answers']) for r in finals.values()),'mapped_answer_slots':len(actual_slots),'unresolved_slots':unresolved,'schema':'suyang-ppt-delivery-audit-v2','version':version,'source_release_freeze':{'path':str(freeze_path),'sha256':sha(freeze_path.read_bytes()) if freeze else None,'source_files_checked':len(freeze.get('source_files',{})),'mismatch':freeze_mismatch},'records':len(seen),'records_with_effective_click':sum(actual_record_clicks[k]>0 for k in seen),'records_without_effective_click':no_clicks,'record_clicks':dict(actual_record_clicks),'operation_record_coverage':{'records':len(operations),'classes':dict(Counter(x['coverage'] for x in operations)),'index':str(HERE/f'operation_animation_index_{version}.json')},'pages':len({i['book_page'] for i in indexes}),'tables':table_total,'oral_subquestions':len(oral_seen),'vertical_blocks':len(vertical_seen),'given_vertical_blocks':len(given_vertical),'legacy_vertical_array_blocks':legacy_vertical_arrays,'native_package_totals':dict(native_totals),'scene_registration_methods':dict(registration_totals),'slides':len(indexes),'volumes':volumes,'issues':issues,'passed':not issues,'scope':'Actual package/source coverage and all exported static preview presence; no PowerPoint/WPS playback test.'}
    result['leading_conclusions_after_reasoning']=len(teaching_moves);result['inline_final_marks']=inline_marks
    (HERE/f'delivery_audit_{version}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    (HERE/f'total_index_{version}.json').write_text(json.dumps(indexes,ensure_ascii=False,indent=2))
    (HERE/f'diagram_index_{version}.json').write_text(json.dumps(diagrams,ensure_ascii=False,indent=2))
    (HERE/f'operation_animation_index_{version}.json').write_text(json.dumps(operations,ensure_ascii=False,indent=2))
    if indexes:
        with (HERE/f'total_index_{version}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['volume','filename','slide','book_page','source_page','question_id','record_key','continuation','subquestions','final_answer_slots','table_final_answers','review_label','click_count','input_pdf_page']);writer.writeheader()
            for x in indexes:writer.writerow({**x,'subquestions':'；'.join(q['label'] for q in x['subquestions'])})
    print(json.dumps({k:v for k,v in result.items() if k!='volumes'},ensure_ascii=False,indent=2))
    return 0 if not issues else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='v6');a=p.parse_args();raise SystemExit(audit(a.version))
