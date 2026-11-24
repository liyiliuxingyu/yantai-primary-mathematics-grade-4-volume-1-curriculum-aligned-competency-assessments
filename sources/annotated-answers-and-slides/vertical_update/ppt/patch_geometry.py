from pathlib import Path
import json,hashlib,zipfile,copy,re,shutil
from lxml import etree as E
import fitz
R=Path(__file__).resolve().parents[2];S=R/'source';W=R/'vertical_update/ppt';D=S/'vertical_update/ppt';A=D/'assets';A.mkdir(parents=True,exist_ok=True)
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
svg=(W/'p010_s04_g1_asset.svg').read_text().replace('width="114.75" height="113.82"','width="114.75pt" height="113.82pt"')
(A/'p010_s04_g1.svg').write_text(svg)
sv=fitz.open(stream=svg.encode(),filetype='svg');pv=fitz.open(stream=sv.convert_to_pdf(),filetype='pdf');pv[0].get_pixmap(matrix=fitz.Matrix(612/pv[0].rect.width,607/pv[0].rect.height),alpha=True).save(A/'p010_s04_g1.png')
# Names and timing links are stable; change the text in the named native shapes.
changes={220:{'p010_s04_b006_0_p8':'所作的垂线段。','p010_s04_b006_1_p0':'图中CA与AB互相垂直，垂足在A。','p010_s04_b006_2_p0':'所以，所求距离就是线段CA的长度。','p010_s04_b007_3_p0':'图中已知','p010_s04_b008_5_p0':'垂线段AC的长度是3厘米，不取斜线段BC的长度。','p010_s04_b008_6_p0':'选A。'},221:{'p010_s04_b009_0_p5_answer':'A','unknown_notice':'答案：A（3厘米）。'}}
with zipfile.ZipFile(W/'baseline.pptx')as z:
 data={n:z.read(n)for n in z.namelist()}
 before={sn:E.fromstring(data[f'ppt/slides/slide{sn}.xml'])for sn in [218,219,220,221]}
 for sn,old in before.items():
  root=copy.deepcopy(old)
  for sp in root.findall('.//p:sp',NS):
   nv=sp.find('p:nvSpPr/p:cNvPr',NS);name=nv.get('name');texts=sp.findall('.//a:t',NS)
   if name=='title':
    for t in texts:t.text=(t.text or '').replace('（读图条件）','')
   if name in changes.get(sn,{}):
    assert len(texts)==1,(sn,name,len(texts));texts[0].text=changes[sn][name]
  # Every cNvPr ID/name/order and animation timing tree must be unchanged.
  assert root.xpath('.//p:cNvPr/@id',namespaces=NS)==old.xpath('.//p:cNvPr/@id',namespaces=NS)
  assert root.xpath('.//p:cNvPr/@name',namespaces=NS)==old.xpath('.//p:cNvPr/@name',namespaces=NS)
  assert (E.tostring(root.find('p:timing',NS)) if root.find('p:timing',NS) is not None else None)==(E.tostring(old.find('p:timing',NS)) if old.find('p:timing',NS) is not None else None)
  data[f'ppt/slides/slide{sn}.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
 data['ppt/media/image765.svg']=svg.encode();data['ppt/media/image765.png']=(A/'p010_s04_g1.png').read_bytes()
 out=W/'小学四上同步素养卷第1册讲解课件答案.pptx'
 with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6)as q:
  for n,b in data.items():q.writestr(n,b)
 with zipfile.ZipFile(out)as q:assert q.testzip()is None
 # No unaffected slide XML or non-target media can differ.
 changed=[n for n in data if data[n]!=z.read(n)]
 assert set(changed)=={f'ppt/slides/slide{n}.xml'for n in[218,219,220,221]}|{'ppt/media/image765.svg','ppt/media/image765.png'}
 pp=E.fromstring(data['ppt/presentation.xml']);assert len(pp.findall('p:sldIdLst/p:sldId',NS))==426
 # Update active metadata; math ASTs and animation click targets stay the same.
 mp=S/'ppt_builder/current_metadata/volume01/manifest.json';ip=mp.with_name('manifest.index.json');man=json.load(open(mp));idx=json.load(open(ip))
 for row in man['slides']:
  if row.get('record_key')!='p010_s04':continue
  if row['slide']==219:
   for v in row['vectors']:
    if v['target']=='alt:p010_s04_b005_0':v.update(svg_path=str(A/'p010_s04_g1.svg'),source_relative='vertical_update/ppt/assets/p010_s04_g1.svg')
  if row['slide']==221:
   for a in row['answer_slots']:a.update(answer='A',unresolved=False,note='AC为3厘米，点C到直线AB的距离等于垂线段AC的长度，选A。')
  row['post_export_content_patched']=True;row['semantic_overlay']='vertical_update/ppt/geometry_patch.json'
 for row in idx:
  if row.get('record_key')!='p010_s04':continue
  row['question_id']='二、2'
  for a in row.get('final_answer_slots',[]):a.update(answer='A',unresolved=False,note='AC为3厘米，垂足在A，距离为3厘米，选A。')
 man['final_pptx_sha256']=sha(out);man['ac_length_revision']={'question':'p010_s04','AC_cm':3,'answer':'A','qa':'vertical_update/ppt/qa_geometry.json'}
 mp.write_text(json.dumps(man,ensure_ascii=False,indent=2)+'\n');ip.write_text(json.dumps(idx,ensure_ascii=False,indent=2)+'\n')
 for p in (S/'ppt_builder').glob('final_answers*.json'):
  d=json.load(open(p));records=d.get('records',{})
  if not isinstance(records,dict)or 'p010_s04'not in records:continue
  for a in records['p010_s04']['final_answers']:
   if a['slot_index']==0:
    a.update(answer_latex='A',unresolved=False,note='用户已核实AC=3厘米；垂线段AC的长度就是所求距离，选A。');a.pop('display_label',None)
  p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 merge=S/'ppt_builder/merge_final_answers.py';t=merge.read_text();t=t.replace("('p010_s04',0):'待核',",'');merge.write_text(t)
 for fn,field in [('diagram_index.json','diagrams'),('tikz_index.json','figures')]:
  p=S/fn;d=json.load(open(p))
  for x in d[field]:
   if x.get('diagram_name')=='p010_s04_g1':x.update(question_id='二、2',notes='上边AC按用户核实修正为3厘米；AB=4厘米、BC=5厘米。题图不增添原卷未画的直角符号。',source_tikz_sha256=sha(S/'tikz/p010_s04_g1.tikz.tex'))
  p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 p=S/'figures/p010_s04_g1.tex';p.write_text(p.read_text().replace('二、2（读图条件）','二、2'))
 receipt={'passed':True,'baseline_sha256':sha(W/'baseline.pptx'),'pptx_sha256':sha(out),'slides':426,'changed_slides':[218,219,220,221],'changed_zip_parts':changed,'all_unaffected_parts_identical':True,'shape_ids_names_and_order_unchanged':True,'animation_timing_xml_unchanged':True,'answer':'A','AC_cm':3,'AB_cm':4,'BC_cm':5,'native_playback_tested':False,'source_files':['tikz/p010_s04_g1.tikz.tex','figures/p010_s04_g1.tex','diagram_index.json','tikz_index.json','ppt_builder/current_metadata/volume01/manifest.json','ppt_builder/current_metadata/volume01/manifest.index.json','ppt_builder/final_answers.json','ppt_builder/final_answers_a.json','ppt_builder/merge_final_answers.py','vertical_update/ppt/assets/p010_s04_g1.svg','vertical_update/ppt/assets/p010_s04_g1.png']}
 (D/'geometry_patch.json').write_text(json.dumps({'question':'p010_s04','slide_text_replacements':changes,'replaced_media':['ppt/media/image765.svg','ppt/media/image765.png'],'preserve_timing':True},ensure_ascii=False,indent=2)+'\n');(D/'qa_geometry.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');shutil.copyfile(__file__,D/'patch_geometry.py');print(json.dumps(receipt,ensure_ascii=False))
