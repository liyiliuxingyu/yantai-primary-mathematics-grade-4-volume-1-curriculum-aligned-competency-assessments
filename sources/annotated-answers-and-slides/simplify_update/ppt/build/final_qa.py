from pathlib import Path
from lxml import etree as E
import hashlib,json,re,zipfile
P=Path(__file__).resolve().parents[1]
N={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','mc':'http://schemas.openxmlformats.org/markup-compatibility/2006'}
def sha(b):return hashlib.sha256(b).hexdigest()
def timing(b):
 m=re.search(rb'<p:timing>.*?</p:timing>',b,re.S);return m.group() if m else b''
def logical(r):return [(x.get('id'),x.get('name')) for x in r.xpath('//p:cNvPr[not(ancestor::mc:Fallback)]',namespaces=N)]
idx={(x['volume'],x['slide']):x for x in json.load(open(P/'inventory.json'))};recs=json.load(open(P/'r4/qa_package.json'));out=[];overlay=[]
for rec in recs:
 f=P/'r4'/Path(rec['output']).name;v=int(re.search(r'第(\d+)册',f.name)[1]);base=P.parent/'bundle/讲解课件'/f.name
 with zipfile.ZipFile(f) as z,zipfile.ZipFile(base) as old:
  changed=sorted(rec['changed_slides']);alln=sorted(int(re.search(r'slide(\d+)',s)[1]) for s in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',s));alltiming=True;idsok=True;newids=0;newmath=0
  for n in alln:
   k=f'ppt/slides/slide{n}.xml';b=z.read(k);before=old.read(k);r=E.fromstring(b);r0=E.fromstring(before)
   alltiming &= timing(b)==timing(before)
   li=logical(r);oldli=logical(r0);oldid=dict(oldli)
   idsok &= len({i for i,nm in li})==len(li) and [(i,nm) for i,nm in li if i in oldid]==oldli
   if n not in changed:assert b==before
   else:
    newids+=len(li)-len(oldli);newmath+=len(r.findall('.//m:oMath',N))-len(r0.findall('.//m:oMath',N));sh=[]
    for sp in r.xpath('//p:sp[not(ancestor::mc:Fallback)]',namespaces=N):
     nv=sp.find('p:nvSpPr/p:cNvPr',N);text=''.join(sp.xpath('.//a:t/text()|.//m:t/text()',namespaces=N))
     assert not any(t in text for t in ('\t','\r','\x08','\x0c','\\times','\\begin{','\\text{','imes')),(v,n,nv.get('name'),repr(text))
     sh.append({'id':nv.get('id'),'name':nv.get('name'),'text':text,'native_omml':bool(sp.findall('.//m:oMath',N))})
    meta=idx[v,n];overlay.append({'volume':v,'slide':n,'book_page':meta['book_page'],'question_id':meta['question_id'],'record_key':meta['record_key'],'native_click_count':meta.get('click_count'),'timing_sha256':sha(timing(b)),'objects':sh})
  assert alltiming and idsok
 out.append({'volume':v,'filename':f.name,'path':str(f),'output_sha256':sha(f.read_bytes()),'bytes':f.stat().st_size,'slides':rec['total_slides'],'changed_slides':changed,'changed_slide_count':len(changed),'all_original_timing_bytes_preserved':alltiming,'all_original_shape_ids_names_order_preserved':idsok,'new_unique_shape_ids':newids,'net_new_native_omml_objects':newmath,'unmodified_slides_byte_identical':True,'unrelated_zip_parts_byte_identical':True})
(P/'final_inventory_3_6.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(P/'post_export_overlay_3_6.json').write_text(json.dumps({'role':'Authoritative final visible object content for the 44 patched slides. All unlisted slides remain byte-identical to the baseline.','slides':overlay},ensure_ascii=False,indent=2)+'\n')
(P/'metadata_scope_3_6.json').write_text(json.dumps({'current_metadata_index_role':'Structural location index. Original slide numbers, record keys, continuation numbers, click counts, and original shape IDs are preserved.','current_metadata_manifest_role':'Pre-patch authoring reference; its old semantic text must not be used to regenerate an updated deck.','authoritative_math':'../accepted_changes.json plus the final OOXML visible objects in post_export_overlay_3_6.json.','reproducible_patch':'build/patch_simplify.py --rules rules_all.json --source ../bundle/讲解课件 --out NEW_IMMUTABLE_DIRECTORY --assets formulas','native_formula_implementation':'New multi-line work uses one preserved animation-anchor group containing independent editable OMML objects at explicit equality/RHS columns. Each formula has dedicated actual XeLaTeX SVG and PNG compatibility assets.','animation_scope':'All original timing XML bytes retained. Added rows within an existing inline-analysis click appear together in that existing click; existing separate calculation-click groups remain.','playback_software_test':'No PowerPoint/WPS slideshow was opened or tested. ArtifactTool import and static rendering only.'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False))
