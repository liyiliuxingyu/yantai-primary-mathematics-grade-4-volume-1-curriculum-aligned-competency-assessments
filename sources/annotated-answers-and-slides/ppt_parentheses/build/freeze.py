from pathlib import Path
import sys,json,re,shutil,hashlib,zipfile
from fractions import Fraction
from lxml import etree as E
R=Path(__file__).resolve().parents[2];P=R/'project';W=R/'ppt_parentheses';D=P/'ppt_parentheses'
sys.path.insert(0,str(P/'ppt_simplify/build'))
import patch_simplify as m
sha=lambda b:hashlib.sha256(b).hexdigest()
J=lambda p:json.loads(p.read_text())
def WJ(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
source=R/'bundle/讲解课件/小学四上同步素养卷第5册讲解课件答案.pptx'
final=W/'validated_r4'/source.name;draft=W/'draft'/source.name
receipt=J(W/'qa_r4/finalizer_v5.json');assert receipt['finalSha256']==sha(final.read_bytes())==sha(draft.read_bytes())
assert receipt['packageIntegrity']['status']=='pass' and receipt['firstPartyImport']['passed']
assert not receipt['presentationLayout']['findings'] and not receipt['presentationLayout']['warnings']
imp=J(W/'after/qa_import.json');assert imp['import_succeeded'] and imp['rendered']==[52,53]
assert J(W/'qa_portable.json')['passed']
def content(n):return bool(''.join(n.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)).strip() or n.xpath('.//a:blip',namespaces=m.NS))
def empty_clicks(root):
 nodes={n.get('id'):n for n in m.visible_nodes(root)};out=[]
 for click in root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=m.NS):
  bits=[]
  for target in click.xpath('.//p:spTgt/@spid',namespaces=m.NS):
   node=nodes[target];shape=next(a for a in node.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')]);bits.append(content(shape))
  if bits and not any(bits):out.append(click.get('id'))
 return out
with zipfile.ZipFile(source) as z:before={n:z.read(n) for n in z.namelist()}
with zipfile.ZipFile(final) as z:after={n:z.read(n) for n in z.namelist()}
assert set(before)<=set(after)
changed=[n for n,b in before.items() if after[n]!=b]
assert sorted(changed)==sorted(['ppt/slides/slide53.xml','ppt/slides/_rels/slide53.xml.rels'])
slide_names=[n for n in before if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)];assert len(slide_names)==430
new_empty=[];native_before=native_after=0
for name in slide_names:
 a=E.fromstring(before[name]);f=E.fromstring(after[name])
 assert m.timing(before[name])==m.timing(after[name]),name
 m.assert_preserved_ids(m.logical_ids(a),m.logical_ids(f))
 native_before+=len(a.findall('.//m:oMath',m.NS));native_after+=len(f.findall('.//m:oMath',m.NS))
 if before[name]!=after[name]:new_empty+=list(set(empty_clicks(f))-set(empty_clicks(a)))
assert not new_empty
root=E.fromstring(after['ppt/slides/slide53.xml']);objects=[]
for node in m.visible_nodes(root):
 shape=next((a for a in node.iterancestors() if a.tag in [m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')]),None)
 if shape is None:continue
 try:rect=m.get_rect(shape)
 except (AttributeError,ValueError):rect=None
 objects.append({'id':node.get('id'),'name':node.get('name'),'rect':rect,'text':''.join(shape.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS)),'native_math':bool(shape.findall('.//m:oMath',m.NS))})
byname={n['name']:n for n in objects}
expected={
 'p075_s03_b003_0':'(720×2)÷(12+8)',
 'p075_s03_b004_1_simplify_rhs0':'(720×2)÷20',
 'p075_s03_b004_1_simplify_rhs1':'720×(2÷2)÷10',
 'p075_s03_b004_1_simplify_rhs2':'720÷10',
 'p075_s03_b005_2':'72（米/分）'}
for name,text in expected.items():assert byname[name]['text']==text and byname[name]['native_math'],(name,byname[name])
values=[Fraction(720*2,12+8),Fraction(720*2,20),720*Fraction(2,2)/10,Fraction(720,10),Fraction(72)]
assert set(values)=={Fraction(72)}
assert len(root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=m.NS))==4
overlay={'volume':5,'slide':53,'key':'p075_s03','book_page':75,'source_page':79,'input_pdf_page':100,'question_id':'三、2','xml_sha256':sha(after['ppt/slides/slide53.xml']),'actual_objects':objects,'rules':J(W/'rules.json'),'calculation_rows':list(expected.values()),'answer':'来回平均每分钟走72米。','original_click_count':4,'click_order_unchanged':True}
WJ(D/'post_export_overlay.json',[overlay]);WJ(D/'rules.json',J(W/'rules.json'))
used=J(W/'used_formula_assets.json');mapped=[]
for x in used:
 entry={k:v for k,v in x.items() if k not in ['source','pdf','png','svg']}
 for ext,k in [('.tex','source'),('.pdf','pdf'),('.svg','svg'),('.png','png')]:entry[k]='ppt_parentheses/formulas/'+x['stem']+ext
 mapped.append(entry)
WJ(D/'used_formula_assets.json',mapped)
build=D/'build';build.mkdir(exist_ok=True)
for name in ['patch_parentheses.py','render_inspect.mjs','finalize.mjs','portable_sources.py','freeze.py']:shutil.copy2(W/'build'/name,build/name)
# The published rebuild entry point takes an explicit source-package path.
script=build/'patch_parentheses.py';t=script.read_text();t=t.replace("R=Path(__file__).resolve().parents[2];P=R/'project';W=R/'ppt_parentheses'", "P=Path(__file__).resolve().parents[2];R=P.parent;W=Path(sys.argv[2]).resolve()\nW.mkdir(parents=True,exist_ok=True)")
t=t.replace("source=R/'bundle/讲解课件/小学四上同步素养卷第5册讲解课件答案.pptx'", "source=Path(sys.argv[1]).resolve()\nassert SHA(source)=='4aad33ca4bcceb8c1c0ffbdc6ba5c49f435ed75a555f7593a45cf119b84feaed','Requires exact preceding version; do not run twice on a patched deck'")
script.write_text(t)
# Refresh the sole changed active slide record; untouched entries remain exact.
folder=P/'ppt_builder/current_metadata/volume05';mf=folder/'manifest.json';manifest=J(mf)
slide=next(s for s in manifest['slides'] if s['slide']==53)
slide['bindings']=[{'name':o['name'],'rect':dict(zip(['left','top','width','height'],o['rect']))} for o in objects if o['rect'] is not None]
slide['formulas']=[{'target':o['name'],'ast':{'t':'seq','items':[{'t':'text','v':o['text']}]},'color':'C00000','points':32,'font':'Droid Sans Fallback','implementation':'native OMML in delivered PPTX'} for o in objects if o['native_math'] and o['name']!='p075_s03_b004_1']
slide['vectors']=[{'target':r['ops'][i]['name'],'svg_path':a['svg']} for r in J(W/'rules.json') for i,a in enumerate(mapped)]
slide['post_export_semantic_overlay']='ppt_parentheses/post_export_overlay.json'
slide['ordinary_text_additions']=[J(W/'draft/qa_package.json')[0]['native_caption']]
manifest['final_pptx_sha256']=sha(final.read_bytes())
manifest['post_export_authority']='ppt_parentheses/post_export_overlay.json for slide53; retain existing ppt_recheck and ppt_simplify overlays for all untouched slides'
manifest['parentheses_revision']={'changed_slides':[53],'qa':'ppt_parentheses/qa_final.json','rules':'ppt_parentheses/rules.json','native_powerpoint_playback_tested':False}
WJ(mf,manifest)
idx=folder/'manifest.index.json';index=J(idx)
for x in index:
 if x['slide']==53:x['metadata_role']='structural_location_index';x['post_export_content_patched']=True;x['semantic_overlay']='ppt_parentheses/post_export_overlay.json'
WJ(idx,index)
deliver=R/'deliverables/讲解课件'/final.name;deliver.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(final,deliver)
entry={'volume':5,'filename':final.name,'output':str(deliver),'parent_sha256':sha(source.read_bytes()),'output_sha256':sha(final.read_bytes()),'slides':430,'changed_slides':[53],'static_rendered':[52,53],'individually_visually_inspected':[52,53],'timing_xml_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'unrelated_original_package_parts_byte_identical':True,'new_empty_click_targets':[],'native_math_count_before':native_before,'native_math_count_after':native_after,'native_math_changes':3,'added_caption_in_original_animation_group':True,'finalizer_passed':True,'artifacttool_import_passed':True}
qa={'passed':True,'scope':'Only 原书75页三、2; slide53 changed. Slides51,52,54 and all other original package parts remain byte-identical except slide53 relationship part.','volumes':[entry],'math':{'calculation_rows':list(expected.values()),'all_five_rows_equal':72,'unit':'米/分','total_distance_grouped_in_initial_two_rows':True,'simplification':'20=2×10, use multiplication/division properties to calculate 2÷2 first'},'formulas':'Native editable OMML plus independently XeLaTeX-compiled SVG/PNG compatibility branches','ordinary_caption_editable':True,'native_powerpoint_playback_tested':False,'native_wps_playback_tested':False,'static_visual_scope':'Actual ArtifactTool renders of slides52 and53 individually inspected; no fresh human review claimed for other slides.','source_sets_portably_compiled':3,'slide53_xml_sha256':overlay['xml_sha256'],'receipts':['finalizer_v5.json','qa_portable.json']}
WJ(W/'qa_final.json',qa);WJ(D/'qa_final.json',qa)
delta=[{'volume':5,'pptx':final.name,'sha256':sha(final.read_bytes()),'parent_sha256':sha(source.read_bytes()),'parentheses_revision':'ppt_parentheses/qa_final.json'}]
WJ(W/'inventory_patch.json',delta);WJ(D/'inventory_patch.json',delta)
shutil.copy2(W/'qa_r4/finalizer_v5.json',D/'finalizer_v5.json')
shutil.copy2(W/'after/qa_import.json',D/'qa_import.json')
(D/'README.txt').write_text('本次仅更正原书75页三、2（输入PDF第100页；第5册52—53张）的总路程括号，PPT只改第53张。\n五行脱式及原答语均保留，采用乘除性质简算。原430张动画timing字节及旧对象ID、名称、顺序均未改变；两行解释放在既有计算点击组内，无新增点击。\n普通文字是可编辑原生文字；公式是原生OMML，并带实际XeLaTeX编译SVG/PNG兼容分支。本目录3套公式的相对字体路径均已从工程根目录实际编译通过。\npost_export_overlay.json及当前交付PPT为本题权威内容。历史QA及未改页面的既有覆盖文件均保留为历史记录。\n重建命令：python ppt_parentheses/build/patch_parentheses.py 前版第5册.pptx 新工作目录；要求前版SHA与inventory_patch.json的parent_sha256精确一致。\n实际渲染审看52、53张；未在PowerPoint/WPS内实际放映，原动画结构保持不等于播放测试通过。\n')
print(json.dumps({'passed':True,'volumes':delta,'deliverable':str(deliver),'source':str(D)},ensure_ascii=False,indent=2))
