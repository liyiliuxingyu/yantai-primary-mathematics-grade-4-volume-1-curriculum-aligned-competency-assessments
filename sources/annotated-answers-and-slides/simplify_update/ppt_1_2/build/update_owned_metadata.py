from pathlib import Path
import json,zipfile,re,hashlib
from lxml import etree as E
import common_patch as C
B=Path(__file__).resolve().parents[1];R=B.parent;P=R/'project/ppt_builder';rules=json.loads((B/'rules.json').read_text());report=[]
for v in (1,2):
 fn=P/f'current_metadata/volume{v:02d}/manifest.json';d=json.loads(fn.read_text());changed={s['slide'] for s in rules if s['volume']==v};ppt=B/'final'/f'小学四上同步素养卷第{v}册讲解课件答案.pptx'
 assert ppt.exists();assetfolder=fn.parent/'simplify_assets';assetfolder.mkdir(exist_ok=True)
 with zipfile.ZipFile(ppt) as z:
  for s in d['slides']:
   if s['slide'] not in changed:continue
   r=E.fromstring(z.read(f'ppt/slides/slide{s["slide"]}.xml'));rel=E.fromstring(z.read(f'ppt/slides/_rels/slide{s["slide"]}.xml.rels'));relmap={a.get('Id'):a.get('Target') for a in rel};formulas=[];bindings=[];vectors=[]
   for shape in r.findall('.//p:sp',C.NS):
    if any(a.tag==C.q('mc:Fallback') for a in shape.iterancestors()):continue
    ms=shape.findall('.//a14:m',C.NS)
    if not ms:continue
    assert len(ms)==1
    m=ms[0];assert not m.findall('.//m:f',C.NS) and not m.findall('.//m:m',C.NS),'structured formula needs AST preservation'
    nv=C.c_nv(shape);name=nv.get('name');text=''.join(m.findall('.//m:t',C.NS)[i].text or '' for i in range(len(m.findall('.//m:t',C.NS))))
    rp=m.find('.//a:rPr',C.NS);points=float(rp.get('sz','3200'))/100;color=rp.find('a:solidFill/a:srgbClr',C.NS).get('val')
    formulas.append({'target':name,'ast':{'t':'text','v':text},'color':color,'points':points,'font':'Droid Sans Fallback'})
    rect=C.get_rect(shape);bindings.append({'name':name,'rect':dict(zip(('left','top','width','height'),rect))})
    outer=C.container(shape);fallback=outer.find('mc:Fallback',C.NS)
    if fallback is not None:
     svg=fallback.find('.//{http://schemas.microsoft.com/office/drawing/2016/SVG/main}svgBlip')
     if svg is not None:
      rid=svg.get(C.q('r:embed'));target=relmap[rid];path=target.lstrip('/') if target.startswith('/') else 'ppt/'+target.replace('../','');content=z.read(path);stem=hashlib.sha256(content).hexdigest()[:24]+'.svg';(assetfolder/stem).write_bytes(content)
      vectors.append({'target':name,'svg_path':f'ppt_builder/current_metadata/volume{v:02d}/simplify_assets/{stem}'})
   s['formulas']=formulas;s['bindings']=bindings;s['vectors']=vectors
   s['simplification_revision']={'changed_native_objects':'See simplify_review/ppt_1_2/rules.json and build/patch_owned.py','original_clicks_and_timing_retained':True,'source_pptx_sha256':hashlib.sha256(ppt.read_bytes()).hexdigest()}
 d['simplification_revision']={'scope':'Simplify suitable arithmetic; early units retain main methods and gain side notes.','changed_slides':sorted(changed),'source_pptx_sha256':hashlib.sha256(ppt.read_bytes()).hexdigest(),'metadata_formulas_extracted_from_actual_native_omml':True}
 fn.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 report.append({'volume':v,'manifest':str(fn),'changed_slides':sorted(changed),'index_changed':False,'index_reason':'Structural mapping and final numeric answers unchanged.','output_sha256':hashlib.sha256(ppt.read_bytes()).hexdigest(),'parent_sha256':hashlib.sha256((R/'bundle/讲解课件'/ppt.name).read_bytes()).hexdigest(),'simplify_revision':'simplify_review/ppt_1_2/qa_final.json'})
(B/'metadata_updates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
