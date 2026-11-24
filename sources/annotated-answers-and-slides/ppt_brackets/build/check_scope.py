from pathlib import Path
import json,zipfile,sys,importlib.util,re
from lxml import etree as E
R=Path(__file__).resolve().parents[1];P=R.parent/'project';sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
spec=importlib.util.spec_from_file_location('m',P/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
reports=json.loads((R/'draft/qa_package.json').read_text());rules=json.loads((R/'rules.json').read_text());out=[]
for rec in reports:
 v=rec['volume'];selected=[r for r in rules if r['volume']==v];by={r['slide']:r for r in selected};targetchanges=0
 with zipfile.ZipFile(rec['source']) as z0,zipfile.ZipFile(rec['output']) as z1:
  old={n:z0.read(n) for n in z0.namelist()};new={n:z1.read(n) for n in z1.namelist()};allowed={f'ppt/slides/slide{r["slide"]}.xml' for r in selected}|{f'ppt/slides/_rels/slide{r["slide"]}.xml.rels' for r in selected}
  assert set(old)<=set(new)
  assert {n for n,b in old.items() if b!=new[n]}<=allowed
  for name,b in old.items():
   mt=re.fullmatch(r'ppt/slides/slide(\d+)\.xml',name)
   if not mt:continue
   a=E.fromstring(b);f=E.fromstring(new[name]);assert m.timing(b)==m.timing(new[name]);m.assert_preserved_ids(m.logical_ids(a),m.logical_ids(f))
   if int(mt[1]) in by:
    allowednames={o['name'] for o in by[int(mt[1])]['ops']}
    for nv in m.visible_nodes(a):
     name0=nv.get('name')
     if name0 in allowednames:
      sp0=m.find_shape(a,name0);sp1=m.find_shape(f,name0);op=next(x for x in by[int(mt[1])]['ops'] if x['name']==name0)
      s0=''.join(sp0.xpath('.//m:t/text()',namespaces=m.NS));s1=''.join(sp1.xpath('.//m:t/text()',namespaces=m.NS));assert s0==op['expected_old_plain'] and s1==op['expected_new_plain'];assert s0.translate(str.maketrans('','','()[]'))==s1.translate(str.maketrans('','','()[]'));assert m.get_rect(sp0)==m.get_rect(sp1);targetchanges+=1
     else:
      try:sp0=m.find_shape(a,name0);sp1=m.find_shape(f,name0)
      except (StopIteration,AssertionError):continue
      assert E.tostring(sp0)==E.tostring(sp1),(v,int(mt[1]),name0)
  out.append({'volume':v,'slides':rec['total_slides'],'changed_slide_count':len(selected),'changed_formula_count':targetchanges,'unchanged_copy':not selected,'timing_bytes_unchanged':True,'shape_ids_names_order_unchanged':True,'all_other_original_package_parts_byte_identical':True,'ordinary_text_unchanged':True,'all_target_rectangles_and_fonts_unchanged':True})
assert sum(x['changed_formula_count'] for x in out)==sum(len(r['ops']) for r in rules)
(R/'qa_scope.json').write_text(json.dumps({'passed':True,'volumes':out,'formula_rows':sum(len(r['ops']) for r in rules),'only_bracket_characters_changed':True},ensure_ascii=False,indent=2)+'\n')
print('Pure bracket scope passed;'+str(sum(len(r['ops']) for r in rules))+' formula rows.',flush=True)
