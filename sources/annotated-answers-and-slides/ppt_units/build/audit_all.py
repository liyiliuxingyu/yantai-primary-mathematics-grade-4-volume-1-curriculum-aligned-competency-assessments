#!/usr/bin/env python3
"""Read all six current teaching decks; do not alter presentation content."""
from pathlib import Path
import hashlib, importlib.util, json, re, sys, zipfile
from lxml import etree as E
BASE=Path(__file__).resolve().parents[2];PROJECT=BASE/'project';OUT=BASE/'ppt_units'
sys.path[:0]=[str(PROJECT/'followup_style/ppt'),str(PROJECT/'ppt_builder')]
spec=importlib.util.spec_from_file_location('native_units',PROJECT/'ppt_average/build/native_patch.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
units=['平方千米','平方厘米','平方分米','平方毫米','平方米','立方厘米','立方分米','立方米','千米','厘米','分米','毫米','千克','毫克','公里','公顷','毫升','小时','分钟','秒钟','摄氏度','分钟','元','角','分','吨','克','米','升','时','秒','天','日','年','月','周','岁','人','名','辆','台','盒','本','个','朵','棵','只','枚','杯','瓶','艘','张','箱','块','筐','次','户','把','队','套','班','面','排','份','轮','组','节','件','袋','座','顶','千瓦时','度','根','层','页','道','盏','趟','支','桶','包','米²','cm²','m²','km','cm','mm','kg','g','m','h','s','℃','°C']
units+=['下','部','册','格','大格','场','双']
u='(?:'+'|'.join(map(re.escape,sorted(set(units),key=len,reverse=True)))+')'
unit_full=re.compile('^(?:万|亿)?'+u+'(?:[/／·]'+u+')?$')
pairs=re.compile(r'（([^（）]{1,20})）')
conversion=re.compile(r'(?<![\d.])\d+(?:\.\d+)?\s*'+u+r'(?:²|³)?\s*(?:=|＝|≈)\s*\d+(?:\.\d+)?\s*'+u+r'(?:²|³)?')
def isred(color):return color.upper() in ('C00000','FF0000','CC0000','E00000','D00000')
def objectnode(n):
    return next((a for a in n.iterancestors() if a.tag in (m.q('p:sp'),m.q('p:pic'),m.q('p:grpSp'))),None)
invent=[];candidates=[];convs=[];protected=[];other=[];meta=[];vols=[];table_candidates=[];table_count=0;black_solutions=[]
for v in range(1,7):
    source=next((BASE/'bundle/讲解课件').glob(f'*第{v}册*.pptx'))
    manifest=json.loads((PROJECT/f'ppt_builder/current_metadata/volume{v:02d}/manifest.json').read_text());idx=json.loads((PROJECT/f'ppt_builder/current_metadata/volume{v:02d}/manifest.index.json').read_text())
    ms={s['slide']:s for s in manifest['slides']};irs={s['slide']:s for s in idx}
    count=0
    with zipfile.ZipFile(source) as z:
        assert z.testzip() is None
        for ui in range(1,len(idx)+1):
            ir=irs[ui];row=ms[ui];part=ir.get('original_part_number',row.get('original_part_number',ui));root=E.fromstring(z.read(f'ppt/slides/slide{part}.xml'))
            fm={f['target'].removeprefix('alt:'):f for f in row.get('formulas',[])};objects=[]
            for frame in root.findall('.//p:graphicFrame',m.NS):
                tbl=frame.find('.//a:tbl',m.NS)
                if tbl is None:continue
                table_count+=1;name=frame.find('p:nvGraphicFramePr/p:cNvPr',m.NS).get('name')
                for rr,tr in enumerate(tbl.findall('a:tr',m.NS)):
                    for cc,tc in enumerate(tr.findall('a:tc',m.NS)):
                        txt=''.join(tc.xpath('.//a:t/text()|.//m:t/text()',namespaces=m.NS));ps=[p.group() for p in pairs.finditer(txt) if unit_full.fullmatch(p.group(1))]
                        cols=tc.xpath('.//a:srgbClr/@val',namespaces=m.NS)
                        if ps and any(isred(c) for c in cols):table_candidates.append({'volume':v,'slide':ui,'part_number':part,'record_key':ir['record_key'],'table_name':name,'row':rr,'column':cc,'text':txt,'unit_pairs':ps,'decision':'preserve_known_unit_header' if rr==0 and any(w in txt for w in ('刻度','边长','单位')) else 'review'})
            for n in m.visible_nodes(root):
                sp=objectnode(n)
                if sp is None:continue
                kind=E.QName(sp).localname;math=bool(sp.findall('.//m:t',m.NS));text=''.join(sp.xpath('.//m:t/text()',namespaces=m.NS)) if math else ''.join(sp.xpath('.//a:t/text()',namespaces=m.NS))
                if kind=='grpSp':text=''
                name=n.get('name');f=fm.get(name);colors=sp.xpath('.//a:srgbClr/@val',namespaces=m.NS);color=(f or {}).get('color') or (colors[0] if colors else '')
                red=isred(color)
                try:rect=m.get_rect(sp)
                except Exception:rect=None
                ob={'id':n.get('id'),'name':name,'kind':kind,'text':text,'native_math':math,'rect':rect,'color':color,'answer_or_analysis':red}
                objects.append(ob)
                context={'volume':v,'slide':ui,'part_number':part,'record_key':ir['record_key'],'book_page':ir['book_page'],'question_id':ir['question_id'],**ob}
                ps=[{'raw':p.group(),'unit':p.group(1),'start':p.start(),'end':p.end(),'recognized_unit':bool(unit_full.fullmatch(p.group(1)))} for p in pairs.finditer(text)]
                if ps:
                    if not red:
                        protected.append({**context,'pairs':ps,'reason':'question/known-label colors; protected unless explicitly identified below as black solution'})
                        if ir['record_key'] in ('p003_s07','p005_s04','p007_s08') and '_equation_' in name:
                            pts=sp.xpath('.//a:rPr/@sz',namespaces=m.NS)
                            black_solutions.append({**context,'pairs':ps,'answer_or_analysis':True,'classification':'black_solution_equation_in_answer_analysis_tree','points':int(pts[0])/100 if pts else 23,'color':'000000'})
                    elif any(p['recognized_unit'] for p in ps):candidates.append({**context,'pairs':ps})
                    else:other.append({**context,'pairs':ps,'reason':'fullwidth parentheses not recognized as a result unit'})
                cv=[{'raw':p.group(),'start':p.start(),'end':p.end()} for p in conversion.finditer(text)]
                if cv:
                    result={**context,'conversions':cv,'protected_question':not red,'object_is_only_conversion':bool(len(cv)==1 and text.strip(' 。；;，,\n')==cv[0]['raw'].strip())}
                    convs.append(result)
            for c in convs:
                if c['volume']!=v or c['slide']!=ui:continue
                r=c['rect'];siblings=[]
                if r:
                    for o in objects:
                        s=o['rect']
                        if o['name']==c['name'] or not o['text'] or s is None:continue
                        if abs((r[1]+r[3]/2)-(s[1]+s[3]/2))<max(15,min(r[3],s[3])*.5):siblings.append({'name':o['name'],'text':o['text'],'rect':s,'answer_or_analysis':o['answer_or_analysis']})
                c['same_line_siblings']=siblings;c['possibly_embedded']=not c['object_is_only_conversion'] or bool(siblings)
            invent.append({'volume':v,'slide':ui,'part_number':part,'record_key':ir['record_key'],'objects':objects});count+=1
            for f in row.get('formulas',[]):
                payload=json.dumps(f.get('ast',{}),ensure_ascii=False)
                pp=[p.group() for p in pairs.finditer(payload) if unit_full.fullmatch(p.group(1))]
                if pp:meta.append({'volume':v,'slide':ui,'part_number':part,'record_key':ir['record_key'],'target':f['target'],'color':f.get('color'),'result_unit_fullwidth_pairs':pp})
    assert count==len(idx)==len(manifest['slides'])
    vols.append({'volume':v,'file':str(source),'sha256':sha(source),'slides':count})
OUT.mkdir(exist_ok=True)
(OUT/'logical_inventory.json').write_text(json.dumps({'volumes':vols,'slides':invent},ensure_ascii=False,indent=2)+'\n')
result={'read_only':True,'volumes':vols,'total_slides':sum(v['slides'] for v in vols),'result_unit_fullwidth_candidates':candidates,'additional_black_solution_candidates':black_solutions,'conversion_candidates':convs,'protected_question_or_known_label_pairs':protected,'unrecognized_answer_parentheses':other,'active_metadata_unit_fullwidth_candidates':meta,'table_cell_candidates':table_candidates,'counts':{'unit_candidate_objects':len(candidates),'unit_candidate_slides':len({(c['volume'],c['slide']) for c in candidates}),'black_solution_unit_objects':len(black_solutions),'all_solution_unit_objects':len(candidates)+len(black_solutions),'all_solution_unit_slides':len({(c['volume'],c['slide']) for c in candidates+black_solutions}),'conversion_objects':len(convs),'answer_conversion_objects':sum(not c['protected_question'] for c in convs),'possibly_embedded_answer_conversions':sum(not c['protected_question'] and c['possibly_embedded'] for c in convs),'protected_pair_objects':len(protected),'unrecognized_answer_pair_objects':len(other),'metadata_formula_candidates':len(meta),'native_tables_scanned':table_count,'table_cell_candidates':len(table_candidates)}}
(OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total_slides':result['total_slides'],'counts':result['counts'],'unit_pages':sorted({c['book_page'] for c in candidates}),'conversion_records':sorted({c['record_key'] for c in convs if not c['protected_question']})},ensure_ascii=False))
