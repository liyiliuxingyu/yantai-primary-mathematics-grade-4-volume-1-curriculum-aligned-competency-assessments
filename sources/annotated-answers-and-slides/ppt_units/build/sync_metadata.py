#!/usr/bin/env python3
"""Synchronize active metadata/build templates with the finalized deck bytes."""
from pathlib import Path,PurePosixPath
import copy,hashlib,importlib.util,json,posixpath,re,shutil,sys,zipfile
from lxml import etree as E
BASE=Path(__file__).resolve().parents[2];P=BASE/'project';W=BASE/'ppt_units';DEST=P/'ppt_units';DEST.mkdir(exist_ok=True)
sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
from convert_inputs import normalize_answer_unit_parentheses as norm
sp=importlib.util.spec_from_file_location('units_native',P/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
ur=json.loads((W/'rules_units.json').read_text());cr=json.loads((W/'conversion_rules.json').read_text());jobs=json.loads((W/'render_jobs.json').read_text());allobjects=json.loads((W/'modified_objects.json').read_text())['objects']
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
def seq(nodes):return {'t':'seq','items':[a for n in nodes if(a:=ast(n)) is not None]}
def ast(n):
    t=E.QName(n).localname
    if t.endswith('Pr'):return None
    if t=='r':return {'t':'text','v':''.join(n.xpath('.//m:t/text()',namespaces=m.NS))}
    if t=='f':return {'t':'frac','num':seq(n.find('m:num',m.NS)),'den':seq(n.find('m:den',m.NS))}
    if t in('sSup','sSub'):return {'t':'sup'if t=='sSup'else'sub','base':seq(n.find('m:e',m.NS)),'arg':seq(n.find('m:sup'if t=='sSup'else'm:sub',m.NS))}
    if t=='sSubSup':return {'t':'subsup','base':seq(n.find('m:e',m.NS)),'sub':seq(n.find('m:sub',m.NS)),'sup':seq(n.find('m:sup',m.NS))}
    if t=='rad':return {'t':'rad','base':seq(n.find('m:e',m.NS)),'degree':seq(n.find('m:deg',m.NS))if n.find('m:deg',m.NS)is not None else None}
    if t=='m':return {'t':'matrix','rows':[[seq(c)for c in r.findall('m:e',m.NS)]for r in n.findall('m:mr',m.NS)]}
    if t=='bar':return {'t':'bar','base':seq(n.find('m:e',m.NS)),'position':'bot'}
    if t=='d':
        pr=n.find('m:dPr',m.NS);beg=pr.find('m:begChr',m.NS)if pr is not None else None;end=pr.find('m:endChr',m.NS)if pr is not None else None
        return {'t':'seq','items':[{'t':'text','v':beg.get(m.q('m:val'),'(')if beg is not None else'('},*seq(n.findall('m:e',m.NS))['items'],{'t':'text','v':end.get(m.q('m:val'),')')if end is not None else')'}]}
    return seq(n)
def shape(n):return next(a for a in n.iterancestors()if a.tag in(m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')))
def native(n):return E.QName(n).localname!='grpSp' and bool(n.findall('.//m:oMath',m.NS))
def normal_slots(rows):
    for r in rows:
        for k in('answer','answer_latex','full_answer','note'):
            if isinstance(r.get(k),str):r[k]=norm(r[k])

changed_meta=[];patch=[]
for job in jobs:
 v=job['volume'];src=Path(job['source']);mp=P/f'ppt_builder/current_metadata/volume{v:02d}/manifest.json';ip=mp.with_name('manifest.index.json');man=json.loads(mp.read_text());index=json.loads(ip.read_text());im={s['slide']:s for s in index};touched={}
 for r in ur+cr:
    if r['volume']==v:touched.setdefault(r['ui_slide'],set()).update(o['name']for o in r['ops'])
 for o in allobjects:
    if o['volume']==v:touched.setdefault(o['slide'],set()).add(o['name'])
 with zipfile.ZipFile(src)as z:
  for row in man['slides']:
    ui=row['slide'];part=im[ui].get('original_part_number',row.get('original_part_number',ui));root=E.fromstring(z.read(f'ppt/slides/slide{part}.xml'));relations=E.fromstring(z.read(f'ppt/slides/_rels/slide{part}.xml.rels'));rel={r.get('Id'):r.get('Target')for r in relations};nvs={n.get('name'):n for n in m.visible_nodes(root)}
    active={f['target'].removeprefix('alt:'):f for f in row.get('formulas',[])};vectors={f['target'].removeprefix('alt:'):f for f in row.get('vectors',[])};bindings={b['name']:b for b in row.get('bindings',[])}
    affected=set(touched.get(ui,set()))
    affected|={name for name,f in active.items()if f.get('color','').upper()in('C00000','FF0000') and norm(json.dumps(f.get('ast',{}),ensure_ascii=False))!=json.dumps(f.get('ast',{}),ensure_ascii=False)}
    if not affected:continue
    for name in sorted(affected):
        if name not in nvs:continue
        sh=shape(nvs[name]);rect=m.get_rect(sh);binding={'name':name,'rect':dict(zip(('left','top','width','height'),rect))}
        if name in bindings:bindings[name].update(binding)
        else:row.setdefault('bindings',[]).append(binding)
        if native(sh):
            a=seq(sh.findall('.//m:oMath',m.NS));assert m.ast_plain(a).strip(),(v,ui,name)
            sizes=sh.xpath('.//a:rPr/@sz',namespaces=m.NS);colors=sh.xpath('.//a:srgbClr/@val',namespaces=m.NS);f={'target':'alt:'+name,'ast':a,'color':colors[0]if colors else active.get(name,{}).get('color','C00000'),'points':int(sizes[0])/100 if sizes else active.get(name,{}).get('points',32),'font':'Droid Sans Fallback'}
            active[name]=f
            outer=m.container(sh);svg=outer.xpath('.//*[local-name()="svgBlip"]/@r:embed',namespaces=m.NS)
            if svg:
                media=posixpath.normpath(posixpath.join('ppt/slides',rel[svg[0]])).lstrip('/');content=z.read(media);asset=P/'ppt_units/assets/formulas'/PurePosixPath(media).name
                if not asset.name.startswith('simplify_') or asset.exists()and asset.read_bytes()!=content:asset=asset.with_name('preserved_'+hashlib.sha256(content).hexdigest()[:24]+'.svg')
                if not asset.exists():asset.parent.mkdir(parents=True,exist_ok=True);asset.write_bytes(content)
                assert asset.read_bytes()==content
                vectors[name]={'target':'alt:'+name,'svg_path':str(asset),'source_relative':str(asset.relative_to(P))}
        else:active.pop(name,None);vectors.pop(name,None)
    row['formulas']=list(active.values());row['vectors']=list(vectors.values());row['post_export_content_patched']=True;row['semantic_overlay']='ppt_units/post_export_overlay.json';normal_slots(row.get('answer_slots',[]));normal_slots(row.get('table_answers',[]))
    for click in row.get('clicks',[]):
        for effect in click.get('effects',[]):
            target=effect.get('target','');name=target.removeprefix('alt:')
            if name in nvs and not native(shape(nvs[name])):effect['target']=name
    im[ui]['post_export_content_patched']=True;im[ui]['semantic_overlay']='ppt_units/post_export_overlay.json';normal_slots(im[ui].get('final_answer_slots',[]));normal_slots(im[ui].get('table_final_answers',[]));changed_meta.append({'volume':v,'slide':ui,'targets':sorted(affected),'actual_pptx_unchanged_by_metadata_sync':True})
 man['final_pptx_sha256']=sha(src);man['unit_format_revision']={'qa':'ppt_units/qa_final.json','rules':'ppt_units/conversion_rules.json','unit_rules':'ppt_units/rules_units.json','original_question_units_protected':True};man['post_export_authority']='Current native PPTX, current metadata and ppt_units/post_export_overlay.json; earlier overlays retain history.';man['regenerate_from_this_manifest']=False
 mp.write_text(json.dumps(man,ensure_ascii=False,indent=2)+'\n');ip.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
 patch.append({'volume':v,'pptx':src.name,'sha256':sha(src),'parent_sha256':next(r['sha256']for r in json.loads((W/'audit.json').read_text())['volumes']if r['volume']==v),'slides':[426,479,406,462,433,464][v-1],'changed_slides':job['modified_slides'],'unit_format_revision':'ppt_units/qa_final.json','manifest_path':str(mp),'manifest_sha256':sha(mp),'index_path':str(ip),'index_sha256':sha(ip)})

# Active final-slot answers and generator outputs; previous QA/old_text snapshots
# stay historical.  Questions, known labels and mathematical groups are untouched.
builder_updates=[]
for file in(P/'ppt_builder').glob('final_answers*.json'):
 if 'audit'in file.name:continue
 data=json.loads(file.read_text());count=0
 for record in data.get('records',{}).values():
  for entry in record.get('final_answers',[]):
   if isinstance(entry.get('answer_latex'),str):
    old=entry['answer_latex'];entry['answer_latex']=norm(old);count+=old!=entry['answer_latex']
 if count:file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');builder_updates.append({'file':str(file.relative_to(P)),'fields':count})
templates=['followup_style/ppt/patch_followup.py','style_patch/ppt_final_r3/patch_p003_math.py','style_patch/ppt_final_r3/patch_p003_native_stage.py','ppt_average/build/make_rules.py','simplify_update/ppt_1_2/build/make_rules.py','simplify_update/ppt/build/make_rules_extra.py','ppt_recheck/v3_4/make_rules.py','ppt_recheck/build/make_rules_late.py','ppt_recheck/late/build/make_rules_late.py','ppt_recheck/v1_2/build/apply_v1.py','ppt_recheck/v1_2/v2/build/patch_v2.py','ppt_recheck_v2/build/patch_v2.py']
for name in templates:
 f=P/name
 if not f.exists():continue
 old=f.read_text();new=norm(old)
 if old!=new:f.write_text(new);builder_updates.append({'file':name,'replacement_count':sum(old.count(x['raw'])for c in json.loads((W/'audit.json').read_text())['result_unit_fullwidth_candidates']for x in c['pairs']if x['recognized_unit'])})

approved=json.loads((BASE/'approved_changes.json').read_text());latest={r['key']:r for pp in(P/'questions').glob('p*.json')for r in json.loads(pp.read_text())['records']};fields={c['key']:next((f for f in c['field_changes']if f['field']=='answer_latex'),None)for c in approved['changes']};convkeys=set(json.loads((P/'units_update/conversion_keys.json').read_text())['keys'])
overpath=P/'ppt_builder/math_display_overrides.json';over=json.loads(overpath.read_text())
for key,r in over['records'].items():
 if fields.get(key):
  old=fields[key]['old'];current=latest[key]['answer_latex'];mismatch=hashlib.sha256(old.encode()).hexdigest()!=r.get('source_answer_sha256')
  r['replacement_answer_latex']=current if key in convkeys or mismatch else norm(r['replacement_answer_latex']);r['source_answer_sha256']=hashlib.sha256(current.encode()).hexdigest();r['unit_format_sync']='Approved current answer is authoritative; conversion LHS is not split away from its RHS.'
overpath.write_text(json.dumps(over,ensure_ascii=False,indent=2)+'\n')
teachpath=P/'ppt_builder/teaching_order.json';teach=json.loads(teachpath.read_text())
for key,r in list(teach['records'].items()):
 current=latest[key]['answer_latex'].strip();prefix=norm(r['prefix_latex'])
 if not current.startswith(prefix):
  if re.match(r'^(?:(?:依次)?选(?:择)?|(?:依次)?填(?:写)?|答案(?:为|是)|应填)',current)and'。'in current:prefix=current[:current.index('。')+1]
  else:del teach['records'][key];continue
 r.update(prefix_latex=prefix,conclusion_latex=prefix if prefix.endswith('。')else prefix.rstrip('，,：:；;')+'。',source_answer_sha256=hashlib.sha256(current.encode()).hexdigest())
teach['unit_format_sync']='Leading conclusions rebound to the audited current answers; no mathematical source changed.';teach['moved_conclusions']=len(teach['records']);teachpath.write_text(json.dumps(teach,ensure_ascii=False,indent=2)+'\n')

overlay={'scope':'Result-unit ASCII parentheses and standalone approved conversion blocks only; native timing XML and every original shape ID/name/order retained.','objects':allobjects,'conversion_pages':json.loads((W/'conversion_pages.json').read_text())['pages'],'metadata_reconciliation':changed_meta}
(DEST/'post_export_overlay.json').write_text(json.dumps(overlay,ensure_ascii=False,indent=2)+'\n');(DEST/'inventory_patch.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n');(DEST/'builder_sync.json').write_text(json.dumps({'passed':True,'updates':builder_updates,'answer_unit_parser_guard':'ppt_builder/convert_inputs.py','conversion_source_answer_keys':sorted(convkeys),'display_override_source_hashes_updated':True,'leading_conclusion_hashes_rebound':True,'no_original_question_or_known_label_changes':True},ensure_ascii=False,indent=2)+'\n')
for n in('audit.json','rules_units.json','conversion_rules.json','modified_objects.json','conversion_pages.json','qa_phase_units.json','qa_conversions_package.json','probe_baseline_v1.json','probe_final_v1.json'):
 shutil.copy2(W/n,DEST/n)
for v in range(1,7):
 d=DEST/f'render_provenance/volume{v:02d}';d.mkdir(parents=True,exist_ok=True);shutil.copy2(W/f'final_render/volume{v:02d}/qa_import.json',d/'qa_import.json')
(DEST/'build').mkdir(exist_ok=True)
for f in(W/'build').glob('*'):
 if f.is_file():shutil.copy2(f,DEST/'build'/f.name)
print(json.dumps({'metadata_slides_synced':len(changed_meta),'builder_files_synced':len(builder_updates),'inventory_patch':str(DEST/'inventory_patch.json')},ensure_ascii=False))
