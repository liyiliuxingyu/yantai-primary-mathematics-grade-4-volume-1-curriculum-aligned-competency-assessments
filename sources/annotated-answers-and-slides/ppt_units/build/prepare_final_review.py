#!/usr/bin/env python3
"""Index final visible objects and schedule actual changed-slide rendering."""
from pathlib import Path,PurePosixPath
import hashlib,importlib.util,json,posixpath,shutil,sys,zipfile
from lxml import etree as E
BASE=Path(__file__).resolve().parents[2];P=BASE/'project';W=BASE/'ppt_units'
sys.path[:0]=[str(P/'followup_style/ppt'),str(P/'ppt_builder')]
sp=importlib.util.spec_from_file_location('unit_native',P/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
ur=json.loads((W/'rules_units.json').read_text());cr=json.loads((W/'conversion_rules.json').read_text());cq=json.loads((W/'qa_conversions_package.json').read_text());inv=json.loads((W/'logical_inventory.json').read_text())
base_slides={(s['volume'],s['slide']):s for s in inv['slides']};sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
def lookup(root,name):
    ns=[n for n in m.visible_nodes(root)if n.get('name')==name]
    if not ns:return None
    n=ns[0];sh=next(a for a in n.iterancestors()if a.tag in(m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp')))
    kind=E.QName(sh).localname
    if kind=='grpSp':text=''
    elif sh.findall('.//m:t',m.NS):text=''.join(sh.xpath('.//m:t/text()',namespaces=m.NS))
    else:text=''.join(sh.xpath('.//a:t/text()',namespaces=m.NS))
    return {'id':n.get('id'),'name':name,'rect':m.get_rect(sh),'kind':kind,'text':text,'native_math':kind!='grpSp' and bool(sh.findall('.//m:t',m.NS))}

allobj=[];conversion_pages=[];jobs=[];actual_sha=[]
for v in range(1,7):
    f=next((W/'final').glob(f'*第{v}册*.pptx'));um=[r for r in ur if r['volume']==v];cm=[r for r in cr if r['volume']==v];changed=sorted({r['ui_slide']for r in um+cm});extra={183,184} if v==5 else{352} if v==6 else set();rendered=sorted(set(changed)|extra)
    cmap={r['ui_slide']:r for r in cm};objmap={}
    with zipfile.ZipFile(f)as z:
        for ui in rendered:
            s=base_slides[v,ui];part=s['part_number'];root=E.fromstring(z.read(f'ppt/slides/slide{part}.xml'))
            if ui in cmap or ui in extra:conversion_pages.append({'volume':v,'slide':ui,'part_number':part,'record_key':s['record_key'],'actual_conversion_layout_changed':ui in cmap})
            for r in um:
                if r['ui_slide']!=ui:continue
                for op in r['ops']:
                    actual=lookup(root,op['name'])
                    if actual and actual['text']:objmap[ui,op['name']]={'volume':v,'slide':ui,'part_number':part,'record_key':s['record_key'],'change_type':'unit_parentheses','old_text':op['old_text'],'expected_new_text':op['new_text'],'points':op['points'],'color':op['color'],**actual}
            if ui in cmap:
                report=next(r for vr in cq if vr['volume']==v for r in vr.get('changes',[])if r['slide']==ui)
                for op,proof in zip(cmap[ui]['ops'],report['ops']):
                    name=op['name'];objmap.pop((ui,name),None)
                    if op['type']=='blank':continue
                    if op['type']=='rich':
                        for child in proof['rows']:
                            actual=lookup(root,child['name']);assert actual
                            objmap[ui,child['name']]={'volume':v,'slide':ui,'part_number':part,'record_key':s['record_key'],'change_type':'conversion_'+child['type'],'points':child['points'],'source_anchor':name,'latex':next((r['tex'] for r in op['rows']if r['type']=='math'and child['name'].startswith(name+'_units_row_'+str(op['rows'].index(r)))),'')if child['type']=='math'else None,**actual}
                    else:
                        actual=lookup(root,name)
                        if actual and actual['text']:objmap[ui,name]={'volume':v,'slide':ui,'part_number':part,'record_key':s['record_key'],'change_type':'conversion_'+op['type'],'points':op.get('points',32),'latex':op.get('tex'),**actual}
        for entry in objmap.values():
            r=entry['rect'];assert r[0]>=-1 and r[1]>=99 and r[0]+r[2]<=1281 and r[1]+r[3]<=670,(entry['volume'],entry['slide'],entry['name'],r)
    allobj+=list(objmap.values());jobs.append({'volume':v,'source':str(f),'source_sha256':sha(f),'slides':rendered,'modified_slides':changed,'output_directory':str(W/f'final_render/volume{v:02d}')});actual_sha.append({'volume':v,'sha256':sha(f)})
(W/'modified_objects.json').write_text(json.dumps({'objects':sorted(allobj,key=lambda o:(o['volume'],o['slide'],o['rect'][1],o['rect'][0])),'slide_count':sum(len(j['modified_slides'])for j in jobs),'final_pptx_sha256':actual_sha},ensure_ascii=False,indent=2)+'\n')
(W/'conversion_pages.json').write_text(json.dumps({'pages':conversion_pages,'source_conversion_keys':json.loads((P/'units_update/conversion_keys.json').read_text()),'notes':'Already-proper p081_s04 and p104_s02 final conversion are included as actual whole-slide checks.'},ensure_ascii=False,indent=2)+'\n')
(W/'render_jobs.json').write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n')
build=W/'build';shutil.copy2(BASE.parent/'p78_review/ppt_p078/build/render_inspect.mjs',build/'render_inspect.mjs')
import os
if not(build/'node_modules').exists():(build/'node_modules').symlink_to(os.environ['CODEX_PRIMARY_RUNTIME_NODE_MODULES'],target_is_directory=True)
print(json.dumps({'modified_slides':{j['volume']:len(j['modified_slides'])for j in jobs},'rendered_pages':{j['volume']:len(j['slides'])for j in jobs},'modified_visible_objects':len(allobj),'conversion_pages':len(conversion_pages)},ensure_ascii=False))
