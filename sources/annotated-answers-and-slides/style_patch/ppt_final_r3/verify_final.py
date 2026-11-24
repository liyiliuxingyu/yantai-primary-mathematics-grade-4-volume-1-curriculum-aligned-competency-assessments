from pathlib import Path
import hashlib,json,re,zipfile
from lxml import etree as E
import fitz

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
NAME='小学四上同步素养卷第1册讲解课件答案.pptx'
SRC=ROOT/'deliverables/讲解课件'/NAME
DST=OUT/NAME
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','mc':'http://schemas.openxmlformats.org/markup-compatibility/2006'}
def sha(x):return hashlib.sha256(x).hexdigest()
def timing(x):
    m=re.search(rb'<p:timing>.*?</p:timing>',x,re.S)
    return m.group() if m else b''

with zipfile.ZipFile(SRC) as a,zipfile.ZipFile(DST) as b:
    an,bn=set(a.namelist()),set(b.namelist());assert an.issubset(bn)
    modified=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    expected={f'ppt/slides/slide{n}.xml' for n in [71,74,75,76]}|{f'ppt/slides/_rels/slide{n}.xml.rels' for n in [74,75,76]}
    assert set(modified)==expected,modified
    added=sorted(bn-an);assert len(added)==10 and all(n.startswith('ppt/media/p003_formula_') for n in added)
    assert all(timing(a.read(f'ppt/slides/slide{n}.xml'))==timing(b.read(f'ppt/slides/slide{n}.xml')) for n in range(1,427))
    details=[]
    for n in [71,74,75,76]:
        r=E.fromstring(b.read(f'ppt/slides/slide{n}.xml'))
        native=r.xpath('.//mc:Choice//m:oMath',namespaces=NS)
        fallback=r.xpath('.//mc:Fallback/p:pic',namespaces=NS)
        assert len(native)=={71:0,74:2,75:3,76:3}[n]
        assert len(native)==len(fallback)
        ids=[v.get('id') for v in r.xpath('.//p:cNvPr',namespaces=NS) if not v.xpath('ancestor::mc:Fallback',namespaces=NS)]
        assert len(ids)==len(set(ids))
        targets=r.xpath('.//p:spTgt/@spid',namespaces=NS);assert set(targets).issubset(set(ids))
        d={'slide':n,'native_omml_formula_count':len(native),'real_svg_png_fallback_count':len(fallback),'all_timing_targets_resolve':True}
        if n in (75,76):
            g=r.find('p:cSld/p:spTree/p:grpSp',NS);assert g.find('p:nvGrpSpPr/p:cNvPr',NS).get('id')=='4'
            texts=[''.join(s.xpath('.//a:t/text()',namespaces=NS)) for s in g.findall('p:sp',NS)]
            labels={'每班4千克','18个班','回收总量72千克','已处理32千克','剩余40千克','4批','平均每批10千克'}
            assert labels.issubset(set(texts));assert len(g.findall('p:cxnSp',NS))==6
            d.update({'outer_group_id':4,'all_seven_complete_node_labels_present':True,'native_connectors':6})
        details.append(d)
    r=E.fromstring(b.read('ppt/slides/slide71.xml'));text=''.join(r.xpath('.//a:t/text()',namespaces=NS));assert '两幅图分析方向不同，得到的综合算式相同。' in text and '4×18' not in text

pdf=OUT/'actual_static_export'/NAME.replace('.pptx','.pdf');doc=fitz.open(pdf);assert len(doc)==4
formulas=[]
for p in sorted((OUT/'formulas').glob('formula_*.tex')):
    log=p.with_suffix('.log').read_text();warnings=[s for s in log.splitlines() if any(x in s for x in ['Missing character:','Overfull','Underfull','LaTeX Warning:'])];assert not warnings
    formulas.append({'source':str(p),'source_sha256':sha(p.read_bytes()),'actual_xelatex_compiled':True,'warnings':warnings,'svg_sha256':sha(p.with_suffix('.svg').read_bytes()),'png_sha256':sha(p.with_suffix('.png').read_bytes())})
receipt=json.loads((OUT/'qa/finalizer_receipt.json').read_text())
assert receipt['finalSha256']==sha(DST.read_bytes())
result={'source':str(SRC),'source_sha256':sha(SRC.read_bytes()),'output':str(DST),'output_sha256':sha(DST.read_bytes()),'slide_count':426,'modified_original_zip_parts':modified,'added_media_parts':added,'other_original_zip_components_byte_identical':True,'all_422_other_slide_xml_byte_identical':True,'all_426_timing_xml_byte_identical':True,'affected_slide_checks':details,'native_omml_formula_total':8,'formula_fallback_compilation':formulas,'actual_libreoffice_static_export':{'pdf':str(pdf),'pdf_sha256':sha(pdf.read_bytes()),'exported_original_slide_numbers':[71,74,75,76],'page_count':4,'rendered_pngs':[str(OUT/'actual_static_export'/f'slide-{n:03d}.png') for n in [71,74,75,76]],'visual_review_pass':True,'notes':'Only the four changed pages were re-exported after the final formula revision. No additional whole-deck static comparison was needed because every other slide XML and all shared parts remain byte-identical.'},'skill_validation':{k:receipt[k] for k in ['packageIntegrity','presentationLayout','fontSelection','firstPartyImport']},'claim_boundary':'Native text, connectors, and OMML are verified structurally. Static output was viewed in LibreOffice-exported PDF/PNG. Microsoft PowerPoint slideshow playback was not performed.'}
(OUT/'qa_ppt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['skill_validation','formula_fallback_compilation']},ensure_ascii=False))
