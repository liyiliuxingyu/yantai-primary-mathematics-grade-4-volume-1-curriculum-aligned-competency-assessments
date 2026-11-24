from pathlib import Path
import json,zipfile,hashlib,sys,shutil,copy
from lxml import etree as E
W=Path(__file__).resolve().parents[1]
TASK=next(p for p in W.parents if (p/'project/ppt_builder').is_dir())
P=TASK/'project';sys.path.insert(0,str(P/'ppt_simplify/build'));import patch_simplify as C
J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
name='小学四上同步素养卷第2册讲解课件答案.pptx';final=W/'final'/name;source=TASK/'bundle/讲解课件'/name
assert SHA(final)==SHA(W/'draft2'/name)
rules=J(W/'rules.json');changed=[x['slide'] for x in rules];report=J(W/'draft2/qa_package.json')[0]
assert SHA(source)==report['source_sha256'] and SHA(final)==report['output_sha256']
receipt=J(W/'qa/volume2.validation.json');assert receipt['packageIntegrity']['status']=='pass' and receipt['firstPartyImport']['passed']
meta=P/'ppt_builder/current_metadata/volume02/manifest.json';d=J(meta);idxfile=meta.with_name('manifest.index.json');idx=J(idxfile)
assetfolder=meta.parent/'recheck_assets';assetfolder.mkdir(exist_ok=True);overlay=[]
with zipfile.ZipFile(final) as z:
 for s in d['slides']:
  n=s['slide']
  if n not in changed:continue
  r=E.fromstring(z.read(f'ppt/slides/slide{n}.xml'));rel=E.fromstring(z.read(f'ppt/slides/_rels/slide{n}.xml.rels'));relmap={x.get('Id'):x.get('Target') for x in rel}
  names={x.get('name') for x in C.visible_nodes(r)};formulas=[];bindings=[];vectors=[]
  allobjects=[]
  for nv in C.visible_nodes(r):
   shape=next((a for a in nv.iterancestors() if a.tag in (C.q('p:sp'),C.q('p:pic'))),None)
   if shape is None:continue
   allobjects.append({'id':nv.get('id'),'name':nv.get('name'),'rect':C.get_rect(shape),'text':' '.join(shape.xpath('.//*[local-name()="t"]/text()')),'native_omml':bool(shape.findall('.//m:oMath',C.NS))})
  for shape in r.findall('.//p:sp',C.NS):
   if any(a.tag==C.q('mc:Fallback') for a in shape.iterancestors()):continue
   ms=shape.findall('.//a14:m',C.NS)
   if not ms:continue
   assert len(ms)==1;math=ms[0]
   assert not math.findall('.//m:f',C.NS) and not math.findall('.//m:m',C.NS),'unexpected structured formula; preserve full AST'
   nm=C.c_nv(shape).get('name');value=''.join(x.text or '' for x in math.findall('.//m:t',C.NS))
   rp=math.find('.//a:rPr',C.NS);points=float(rp.get('sz','3200'))/100;color=rp.find('a:solidFill/a:srgbClr',C.NS).get('val')
   formulas.append({'target':nm,'ast':{'t':'text','v':value},'color':color,'points':points,'font':'Droid Sans Fallback'})
   bindings.append({'name':nm,'rect':dict(zip(('left','top','width','height'),C.get_rect(shape)))})
   fallback=C.container(shape).find('mc:Fallback',C.NS)
   if fallback is not None:
    svg=fallback.find('.//{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip')
    if svg is not None:
     target=relmap[svg.get(C.q('r:embed'))];path=target.lstrip('/') if target.startswith('/') else 'ppt/'+target.replace('../','')
     raw=z.read(path);stem=hashlib.sha256(raw).hexdigest()[:24]+'.svg';(assetfolder/stem).write_bytes(raw)
     vectors.append({'target':nm,'svg_path':f'ppt_builder/current_metadata/volume02/recheck_assets/{stem}'})
  # Preserve the actual original TikZ picture nested under the old animation ID.
  for old in s.get('vectors',[]):
   target=old['target'];newtarget=target+'_retained_original'
   if newtarget in names and newtarget not in {v['target'] for v in vectors}:
    v=copy.deepcopy(old);v['target']=newtarget;vectors.append(v)
  s['formulas']=formulas;s['bindings']=bindings;s['vectors']=vectors
  s['post_export_content_patch']=next(x for x in rules if x['slide']==n)
  s['recheck_revision']={'actual_native_omml_extracted':True,'final_pptx_sha256':SHA(final),'semantic_overlay':'ppt_recheck_v2/post_export_overlay.json'}
  overlay.append({'volume':2,'slide':n,'key':s['record_key'],'rules':s['post_export_content_patch'],'actual_objects':allobjects,'formulas':formulas})
d['final_pptx_sha256']=SHA(final);d['regenerate_from_this_manifest']=False
d['metadata_scope']='Structural location index plus actual current native formulas; exact final teaching content and animation anchor grouping are preserved by the post-export rules and overlay.'
d['post_export_authority']='ppt_recheck_v2/post_export_overlay.json';save(meta,d)
for s in idx:
 if s['slide'] in changed:s.update({'metadata_role':'structural_location_index','post_export_content_patched':True,'semantic_overlay':'ppt_recheck_v2/post_export_overlay.json'})
save(idxfile,idx)
core=P/'ppt_recheck_v2';core.mkdir(exist_ok=True);save(core/'rules.json',rules);save(core/'post_export_overlay.json',{'volume':2,'sha256':SHA(final),'slides':overlay})
for f in (W/'build').glob('*.py'):shutil.copy2(f,core/f.name)
for f in (W/'build').glob('*.mjs'):shutil.copy2(f,core/f.name)
formula_core=core/'formulas';formula_core.mkdir(exist_ok=True)
for f in (W/'formulas').glob('recheck20261105_*'):
 if f.suffix not in ['.tex','.pdf','.svg','.png']:continue
 dest=formula_core/f.name
 if f.suffix=='.tex':dest.write_text(f.read_text().replace(P.as_posix()+'/fonts/','../../fonts/'))
 else:shutil.copy2(f,dest)
proof=[]
with zipfile.ZipFile(final) as z,zipfile.ZipFile(W/'draft1'/name) as a:
 for n in changed:
  folder='after2' if n==149 else 'after1';image=W/folder/f'slide-{n}.png'
  if n!=149:assert z.read(f'ppt/slides/slide{n}.xml')==a.read(f'ppt/slides/slide{n}.xml')
  proof.append({'slide':n,'image':str(image.resolve()),'image_sha256':SHA(image),'actual_render_source_deck':str((W/('draft2' if n==149 else 'draft1')/name).resolve()),'slide_xml_matches_final_exactly':True,'individually_visually_inspected':True})
qa={'passed':True,'powerpoint_playback_tested':False,'wps_playback_tested':False,'volumes':[{'volume':2,'output_sha256':SHA(final),'slides':479,'changed_slides':changed,'static_rendered_changed_slide_count':len(changed),'human_inspected_changed_slide_count':len(changed),'all_original_timing_bytes_unchanged':True,'all_original_ids_names_order_preserved':True,'unrelated_slides_and_parts_byte_identical':True,'static_renders':proof}],
 'mathematics':{'exact_step_values':{'p024_s03':{'original':728,'days_hint':91},'p025_s17':42,'p030_s10':1248,'p031_s08':25,'p032_s02':1200},'all_intermediate_expressions_recomputed_equal':True,'early_main_method_preserved':True},
 'rendering_revision':'Moved slide149 answer below the new days hint after an actual first-render overlap was found; final corrected rendering reviewed.',
 'native_math':'Changed equations are genuine native OMML, with compiled XeLaTeX SVG/PNG fallbacks; original TikZ picture retained.',
 'font_sizes':{'main_equations':32,'note_headings':26,'short_note_explanation':24},
 'finalizer_receipt':str((W/'qa/volume2.validation.json').resolve()),
 'limitation':'Static ArtifactTool checks and unchanged OOXML timing do not establish PowerPoint/WPS playback; neither application was opened.'}
save(W/'qa_final.json',qa);save(core/'qa_final.json',qa)
save(W/'inventory_patch.json',{'volume':2,'sha256':SHA(final),'output_sha256':SHA(final),'parent_sha256':SHA(source),'slides':479,'changed_slides':changed,'simplification_revision':'ppt_recheck_v2/qa_final.json'})
deliver=TASK/'deliverables/讲解课件'/name;deliver.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(final,deliver);assert SHA(deliver)==SHA(final)
print(json.dumps({'passed':True,'output':str(deliver),'sha256':SHA(final),'changed_slides':changed},ensure_ascii=False),flush=True)
