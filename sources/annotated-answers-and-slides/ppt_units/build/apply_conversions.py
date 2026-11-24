#!/usr/bin/env python3
"""Narrow conversion-layout changes using the original animation anchors."""
from pathlib import Path
import copy,importlib.util,json,re,sys,zipfile
from lxml import etree as E
BASE=Path(__file__).resolve().parents[2];P=BASE/'project';W=BASE/'ppt_units'
spec=importlib.util.spec_from_file_location('unit_phase',W/'build/patch_unit_parens.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
m=g.m;NS=m.NS;q=m.q
inv=json.loads((W/'logical_inventory.json').read_text());slides={(s['volume'],s['slide']):s for s in inv['slides']}

def find(root,name):
    nodes=[n for n in m.visible_nodes(root)if n.get('name')==name];assert len(nodes)==1,(name,len(nodes))
    return next(a for a in nodes[0].iterancestors()if a.tag in(q('p:sp'),q('p:pic'),q('p:grpSp')))
def nv_shape(root,name):return next(n for n in m.visible_nodes(root)if n.get('name')==name)
def placeholder(root,name,ident,rect):
    tree=root.find('p:cSld/p:spTree',NS);sp=m.el('p:sp');nv=m.sub(sp,'p:nvSpPr');m.sub(nv,'p:cNvPr',id=ident,name=name);m.sub(nv,'p:cNvSpPr',txBox='1');m.sub(nv,'p:nvPr');pr=m.sub(sp,'p:spPr');xf=m.sub(pr,'a:xfrm');m.sub(xf,'a:off',x=round(rect[0]*9525),y=round(rect[1]*9525));m.sub(xf,'a:ext',cx=round(rect[2]*9525),cy=round(rect[3]*9525));m.sub(m.sub(pr,'a:prstGeom',prst='rect'),'a:avLst');m.sub(pr,'a:noFill');tree.append(sp);return sp
def move(root,op):
    matches=root.xpath('.//p:cNvPr[@name=$name]',name=op['name'],namespaces=NS);assert matches
    for n in matches:
        sh=next(a for a in n.iterancestors()if a.tag in(q('p:sp'),q('p:pic'),q('p:grpSp')))
        xf=sh.find('p:spPr/a:xfrm',NS)
        if xf is None:xf=sh.find('p:grpSpPr/a:xfrm',NS)
        assert xf is not None,op
        off=xf.find('a:off',NS);off.set('x',str(int(off.get('x'))+round(op.get('dx',0)*9525)));off.set('y',str(int(off.get('y'))+round(op.get('dy',0)*9525)))
    return {'name':op['name'],'dx':op.get('dx',0),'dy':op.get('dy',0),'rect':m.get_rect(find(root,op['name'])),'native_and_fallback_translated':True}
def rich(root,rels,op,assets,extra):
    old=find(root,op['name']);nv=copy.deepcopy(nv_shape(root,op['name']));outer=m.container(old)
    grp=m.el('p:grpSp');ng=m.sub(grp,'p:nvGrpSpPr');ng.append(nv);m.sub(ng,'p:cNvGrpSpPr');m.sub(ng,'p:nvPr')
    xf=m.sub(m.sub(grp,'p:grpSpPr'),'a:xfrm');m.sub(xf,'a:off',x=0,y=0);m.sub(xf,'a:ext',cx=12192000,cy=6858000);m.sub(xf,'a:chOff',x=0,y=0);m.sub(xf,'a:chExt',cx=12192000,cy=6858000)
    ident=max(int(n.get('id'))for n in m.visible_nodes(root))+1;outer.getparent().replace(outer,grp);reports=[]
    for i,row in enumerate(op['rows']):
        x,y,w,h=row['rect'];name=op['name']+'_units_row_'+str(i);pts=row.get('points',op.get('points',32));color=row.get('color','C00000')
        children=[(name,row,[x,y,w,h])]
        if row['type']=='math' and row['tex'].lstrip().startswith('=') and len(row['tex'].strip())>1:
            children=[(name+'_equals',row['_equals'],[max(0,x-42),y,34,h]),(name,row['_rhs'],[x,y,w,h])]
        for child,content,rect in children:
            sp=placeholder(root,child,ident,rect);ident+=1;sp.getparent().remove(sp);grp.append(sp)
            if content['type']=='math':result=m.patch_math(root,rels,{'name':child,'rect':rect,'points':pts,'color':color,'min_scale':.55},assets[id(content)],extra)
            else:result=m.patch_text(root,{'name':child,'rect':rect,'text':content['text'],'points':pts,'color':color})
            reports.append({'type':content['type'],**result})
    return {'name':op['name'],'original_anchor_id':nv.get('id'),'native_group_anchor':True,'rows':reports}

def main():
    rules=[]
    for filename in ('conversion_ops_v1_2.json','conversion_ops_v3_4.json','conversion_ops_v5_6.json'):
        rules+=json.loads((W/filename).read_text())
    rules.sort(key=lambda r:(r['volume'],r['ui_slide']));mathops=[]
    for r in rules:
        s=slides[r['volume'],r['ui_slide']];r['slide']=s['part_number'];assert s['record_key']==r['key']
        seen=set()
        for op in r['ops']:
            if 'type' not in op:op['type']=op.pop('op')
            assert op['name'] not in seen,(r['key'],r['ui_slide'],op['name']);seen.add(op['name'])
            assert any(o['name']==op['name']for o in s['objects']),(r['key'],op)
            if op['type']=='math':mathops.append(op)
            if op['type']=='rich':
                for row in op['rows']:
                    x,y,w,h=row['rect'];assert 0<=x and x+w<=1280 and 100<=y and y+h<=669,(r['key'],row)
                    row.setdefault('points',op.get('points',32));row.setdefault('color','C00000')
                    if row['type']=='math':
                        if row['tex'].lstrip().startswith('=') and len(row['tex'].strip())>1:
                            row['_equals']={'type':'math','tex':'=','points':row['points'],'color':row['color']}
                            row['_rhs']={'type':'math','tex':row['tex'].lstrip()[1:].lstrip(),'points':row['points'],'color':row['color']};mathops.extend([row['_equals'],row['_rhs']])
                        else:mathops.append(row)
    for op in mathops:
        op.setdefault('points',32);op.setdefault('color','C00000');op['ast']=m.MathParser(op['tex']).parse();op['min_scale']=.55
        assert m.ast_plain(op['ast']).strip(),('empty_math',op)
    g.uniq={g.key_for(op):op for op in mathops};g.compile_batches()
    assets={id(op):m.compile_asset(op,g.ASSETS,P/'fonts/DroidSansFallback.ttf')for op in mathops}
    final=W/'final';final.mkdir(exist_ok=True);reports=[];only={int(x)for x in sys.argv[1:]}
    prior=json.loads((W/'qa_conversions_package.json').read_text())if only and(W/'qa_conversions_package.json').exists()else[]
    for v in range(1,7):
        if only and v not in only:reports.append(next(r for r in prior if r['volume']==v));continue
        source=next((W/'phase_units').glob(f'*第{v}册*.pptx'));dest=final/source.name;vr=[r for r in rules if r['volume']==v]
        if not vr:dest.write_bytes(source.read_bytes());reports.append({'volume':v,'output':str(dest),'output_sha256':m.sha(dest.read_bytes()),'changed_slides':[]});continue
        with zipfile.ZipFile(source)as z:
            original={n:z.read(n)for n in z.namelist()};parts=dict(original);extra={};changed=[];proof=[]
            for r in vr:
                name=f'ppt/slides/slide{r["slide"]}.xml';rn=f'ppt/slides/_rels/slide{r["slide"]}.xml.rels';b=parts[name];root=E.fromstring(b);rels=E.fromstring(parts[rn]);before=m.logical_ids(root);ops=[]
                for op in r['ops']:
                    if op['type']=='math':result=m.patch_math(root,rels,op,assets[id(op)],extra)
                    elif op['type']=='text':result=m.patch_text(root,{**op,'color':op.get('color','C00000')})
                    elif op['type']=='blank':result=m.patch_text(root,{'name':op['name'],'text':'','rect':m.get_rect(find(root,op['name'])),'points':32,'color':'C00000'})
                    elif op['type']=='move':result=move(root,op)
                    elif op['type']=='rich':result=rich(root,rels,op,assets,extra)
                    else:raise ValueError(op['type'])
                    ops.append({'operation':op['type'],**result})
                m.assert_preserved_ids(before,m.logical_ids(root));nb=m.xml(root);t=m.timing(b)
                if t:nb=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:t,nb,flags=re.S)
                assert m.timing(nb)==t
                # Every original click still reveals visible content. Rich groups
                # inherit the same old ID; emptied redundant runs remain valid IDs.
                empty=[]
                for effect in root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=NS):
                    ids=effect.xpath('.//p:spTgt/@spid',namespaces=NS);texts=[]
                    for ident in ids:
                        n=next((n for n in m.visible_nodes(root)if n.get('id')==ident),None)
                        if n is None:continue
                        sh=next(a for a in n.iterancestors()if a.tag in(q('p:sp'),q('p:pic'),q('p:grpSp')))
                        texts+=sh.xpath('.//a:t/text()|.//m:t/text()',namespaces=NS)
                    if ids and not ''.join(texts).strip():empty.append(ids)
                assert not empty,('empty_click',v,r['ui_slide'],r['key'],empty)
                parts[name]=nb;rr=m.xml(rels)
                if rr!=parts[rn]:parts[rn]=rr
                changed.append(r['slide']);proof.append({'volume':v,'slide':r['ui_slide'],'part_number':r['slide'],'key':r['key'],'ops':ops,'all_original_clicks_have_content':True})
            for n,b in extra.items():parts[n]=b
            allowed={f'ppt/slides/slide{s}.xml'for s in changed}|{f'ppt/slides/_rels/slide{s}.xml.rels'for s in changed};delta=[n for n in original if original[n]!=parts[n]];assert set(delta)<=allowed
            for n,b in original.items():
                if re.fullmatch(r'ppt/slides/slide\d+\.xml',n):
                    assert m.timing(b)==m.timing(parts[n]);m.assert_preserved_ids(m.logical_ids(E.fromstring(b)),m.logical_ids(E.fromstring(parts[n])))
            with zipfile.ZipFile(dest,'w')as f:
                for info in z.infolist():f.writestr(copy.copy(info),parts.pop(info.filename))
                for n,b in parts.items():f.writestr(n,b,compress_type=zipfile.ZIP_DEFLATED)
        reports.append({'volume':v,'source':str(source),'source_sha256':m.sha(source.read_bytes()),'output':str(dest),'output_sha256':m.sha(dest.read_bytes()),'changed_slides':[r['ui_slide']for r in vr],'changed_original_parts':delta,'new_parts':sorted(extra),'timing_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'changes':proof})
        print(json.dumps({'volume':v,'changed_conversion_slides':reports[-1]['changed_slides']},ensure_ascii=False),flush=True)
    (W/'conversion_rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n');(W/'qa_conversions_package.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'conversion_keys':len({r['key']for r in rules}),'conversion_slides':len(rules),'objects':sum(len(r['ops'])for r in rules)},ensure_ascii=False))
if __name__=='__main__':main()
