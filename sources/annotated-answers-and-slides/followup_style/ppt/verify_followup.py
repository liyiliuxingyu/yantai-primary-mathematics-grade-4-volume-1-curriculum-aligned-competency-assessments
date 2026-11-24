from pathlib import Path
import hashlib,json,re,zipfile
from lxml import etree as E
import fitz
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
NAME='小学四上同步素养卷第1册讲解课件答案.pptx'
SRC=ROOT/'deliverables/讲解课件'/NAME
DST=OUT/'r3'/NAME
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','mc':'http://schemas.openxmlformats.org/markup-compatibility/2006','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
def sha(x):return hashlib.sha256(x).hexdigest()
def timing(x):
 m=re.search(rb'<p:timing>.*?</p:timing>',x,re.S);return m.group() if m else b''
changed=[117,118,171,172]
details=[]
with zipfile.ZipFile(SRC) as a,zipfile.ZipFile(DST) as b:
 assert b.testzip() is None
 an,bn=set(a.namelist()),set(b.namelist());assert an.issubset(bn)
 modified=[n for n in a.namelist() if a.read(n)!=b.read(n)]
 expected={f'ppt/slides/slide{n}.xml' for n in changed}|{f'ppt/slides/_rels/slide{n}.xml.rels' for n in changed}
 assert set(modified)==expected,modified
 added=sorted(bn-an);assert len(added)==18 and all(n.startswith('ppt/media/followup_formula_') for n in added)
 assert all(timing(a.read(f'ppt/slides/slide{n}.xml'))==timing(b.read(f'ppt/slides/slide{n}.xml')) for n in range(1,427))
 for n in changed:
  r=E.fromstring(b.read(f'ppt/slides/slide{n}.xml'))
  native=r.xpath('.//mc:Choice//m:oMath',namespaces=NS);fallback=r.xpath('.//mc:Fallback/p:pic',namespaces=NS)
  assert len(native)=={117:2,118:3,171:1,172:3}[n] and len(fallback)==len(native)
  ids=[v.get('id') for v in r.xpath('.//p:cNvPr',namespaces=NS) if not v.xpath('ancestor::mc:Fallback',namespaces=NS)]
  assert len(ids)==len(set(ids));assert set(r.xpath('.//p:spTgt/@spid',namespaces=NS)).issubset(set(ids))
  d={'slide':n,'native_omml_formula_count':len(native),'actual_svg_png_fallback_count':len(fallback),'all_animation_targets_resolve':True}
  if n in (118,172):
   g=r.find('p:cSld/p:spTree/p:grpSp',NS);assert g.find('p:nvGrpSpPr/p:cNvPr',NS).get('id')=='4'
   nodes=[s for s in g.findall('p:sp',NS) if '_node_' in s.find('p:nvSpPr/p:cNvPr',NS).get('name')]
   assert len(nodes)==7 and len(g.findall('p:cxnSp',NS))==6
   labels=[''.join(s.xpath('.//a:t/text()',namespaces=NS)) for s in nodes]
   assert all(re.search(r'\d',s) for s in labels)
   if n==118:
    e=next(s for s in nodes if s.find('p:nvSpPr/p:cNvPr',NS).get('name')=='p005_s04_node_e')
    vals={run.find('a:t',NS).text:run.find('a:rPr/a:solidFill/a:srgbClr',NS).get('val') for run in e.findall('.//a:r',NS)}
    assert vals['3']=='000000' and vals['324']=='C00000'
   d.update({'outer_group_id':4,'native_quantity_node_count':7,'native_connector_count':6,'complete_labels':labels})
  details.append(d)
pdf=OUT/'r3/actual_static_export'/NAME.replace('.pptx','.pdf')
with fitz.open(pdf) as doc:
 assert len(doc)==4
 for j,n in enumerate(changed):doc[j].get_pixmap(matrix=fitz.Matrix(1.2,1.2)).save(pdf.parent/f'slide-{n:03d}.png')
formula_assets=[]
for p in sorted((OUT/'formulas').glob('formula_*.tex')):
 warnings=[s for s in p.with_suffix('.log').read_text().splitlines() if any(x in s for x in ['Missing character:','Overfull','Underfull','LaTeX Warning:'])]
 assert not warnings,warnings
 formula_assets.append({'source':str(p),'tex_sha256':sha(p.read_bytes()),'actual_xelatex_compile':True,'svg_sha256':sha(p.with_suffix('.svg').read_bytes()),'png_sha256':sha(p.with_suffix('.png').read_bytes()),'warnings':warnings})
receipt=json.loads((OUT/'qa/finalizer_receipt.json').read_text());assert receipt['finalSha256']==sha(DST.read_bytes())
result={'source':str(SRC),'source_sha256':sha(SRC.read_bytes()),'output':str(DST),'output_sha256':sha(DST.read_bytes()),'slide_count':426,'changed_slides':changed,'modified_original_parts':modified,'added_media_parts':added,'all_other_original_package_components_byte_identical':True,'all_422_other_slide_xml_byte_identical':True,'all_426_timing_xml_byte_identical':True,'affected_slides':details,'native_omml_formula_count':9,'formula_assets':formula_assets,'actual_static_export':{'software':'LibreOffice Impress headless','pdf':str(pdf),'pdf_sha256':sha(pdf.read_bytes()),'slide_numbers':changed,'rendered_pngs':[str(pdf.parent/f'slide-{n:03d}.png') for n in changed],'visual_review_pass':True},'artifact_tool_source_inspection':str(OUT/'source_inspection_summary.json'),'skill_validation':{k:receipt[k] for k in ['packageIntegrity','presentationLayout','fontSelection','firstPartyImport']},'claim_boundary':'The four affected slides were actually viewed in full-size LibreOffice PDF/PNG. Native editable objects and all original timing targets verified structurally. No Microsoft PowerPoint slideshow playback was performed.'}
(OUT/'qa_ppt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['output','output_sha256','slide_count','changed_slides','all_422_other_slide_xml_byte_identical','all_426_timing_xml_byte_identical','native_omml_formula_count']},ensure_ascii=False))
