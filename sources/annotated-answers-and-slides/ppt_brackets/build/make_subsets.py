from pathlib import Path
import json,zipfile,hashlib,re
from lxml import etree as E
R=Path(__file__).resolve().parents[1];rules=json.loads((R/'rules.json').read_text());reports=json.loads((R/'draft/qa_package.json').read_text());out=R/'subsets';out.mkdir(exist_ok=True)
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'};items=[]
for rec in reports:
 if not rec['changed_ui_slides']:continue
 v=rec['volume'];source=Path(rec['output']);selected={r['slide']:r['ui_slide'] for r in rules if r['volume']==v}
 with zipfile.ZipFile(source) as z:parts={n:z.read(n) for n in z.namelist()};infos=z.infolist()
 pres=E.fromstring(parts['ppt/presentation.xml']);rels=E.fromstring(parts['ppt/_rels/presentation.xml.rels']);rm={r.get('Id'):r.get('Target') for r in rels};lst=pres.find('p:sldIdLst',ns);mapping=[];keep_ids=[]
 for n in list(lst):
  rid=n.get('{'+ns['r']+'}id');part=int(re.search(r'slide(\d+)\.xml',rm[rid])[1])
  if part not in selected:lst.remove(n)
  else:keep_ids.append(rid);mapping.append({'subset_slide':len(mapping)+1,'actual_slide':selected[part],'part_number':part,'slide_xml_sha256':hashlib.sha256(parts[f'ppt/slides/slide{part}.xml']).hexdigest()})
 for rel in list(rels):
  if rel.get('Type','').endswith('/slide') and rel.get('Id') not in keep_ids:rels.remove(rel)
 for key,root in [('ppt/presentation.xml',pres),('ppt/_rels/presentation.xml.rels',rels)]:parts[key]=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
 app=E.fromstring(parts['docProps/app.xml']);node=app.find('{http://schemas.openxmlformats.org/officeDocument/2006/extended-properties}Slides')
 if node is not None:node.text=str(len(mapping))
 parts['docProps/app.xml']=E.tostring(app,xml_declaration=True,encoding='UTF-8',standalone=True)
 dest=out/f'volume{v:02d}_subset.pptx'
 with zipfile.ZipFile(dest,'w') as z:
  for info in infos:z.writestr(info,parts[info.filename])
 item={'volume':v,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'subset':str(dest),'subset_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'map':mapping,'selected_slide_xml_relationships_theme_master_media_preserved_exactly':True}
 items.append(item);(out/f'volume{v:02d}_map.json').write_text(json.dumps(item,ensure_ascii=False,indent=2)+'\n')
(out/'subset_maps.json').write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
print([(x['volume'],len(x['map'])) for x in items])
