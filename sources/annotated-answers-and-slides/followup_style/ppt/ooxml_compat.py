#!/usr/bin/env python3
"""Add native PowerPoint timing/OMML to an Artifact Tool-authored package.

Targets use exported shape names or exact alt: descriptions, never array indices.
"""
from __future__ import annotations
import argparse, copy, hashlib, json, math, re, zipfile, os, uuid
from pathlib import Path
from lxml import etree as ET

NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'm':'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'a14':'http://schemas.microsoft.com/office/drawing/2010/main',
    'mc':'http://schemas.openxmlformats.org/markup-compatibility/2006'}
def tag(q):p,n=q.split(':');return '{'+NS[p]+'}'+n
def el(q,**attrs):return ET.Element(tag(q),{str(k):str(v) for k,v in attrs.items()})
def sub(parent,q,**attrs):c=el(q,**attrs);parent.append(c);return c

def visible_nodes(root):
    """Conditional fallback branch is one logical shape, not a duplicate."""
    for node in root.xpath('.//p:cNvPr',namespaces=NS):
        if any(a.tag==tag('mc:Fallback') for a in node.iterancestors()):continue
        yield node

def target_map(root):
    out={};ids=[]
    for nv in visible_nodes(root):
        spid=nv.get('id');ids.append(spid)
        for key in [nv.get('name'),('alt:'+nv.get('descr')) if nv.get('descr') else None]:
            if key:
                if key in out and out[key]!=spid:raise ValueError('目标名称不唯一 '+key)
                out[key]=spid
    if len(ids)!=len(set(ids)):raise ValueError('同页 shape ID 重复')
    return out,set(ids)

def bind_images(root,bindings):
    """Artifact Tool export omits image alt/name, so bind by exact authored EMU
    geometry, then assign a stable name. Ambiguous matches fail closed."""
    pictures=root.xpath('.//p:pic',namespaces=NS);used=set()
    for binding in bindings:
        rect=binding['rect'];expected=[round(rect[k]*9525) for k in ('left','top','width','height')];matches=[]
        for picture in pictures:
            if id(picture) in used:continue
            xf=picture.find('p:spPr/a:xfrm',NS)
            if xf is None:continue
            off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
            actual=[int(off.get('x')),int(off.get('y')),int(ext.get('cx')),int(ext.get('cy'))]
            if all(abs(a-b)<=20 for a,b in zip(actual,expected)):matches.append(picture)
        if len(matches)!=1:raise ValueError('图片几何匹配非唯一 '+binding['name']+' '+str(len(matches)))
        pic=matches[0];used.add(id(pic));nv=pic.find('p:nvPicPr/p:cNvPr',NS);nv.set('name',binding['name']);nv.set('descr',binding['name'])

def omml_run(text,color,points,font):
    r=el('m:r');rp=sub(r,'a:rPr',sz=round(points*100),lang='zh-CN')
    fill=sub(rp,'a:solidFill');sub(fill,'a:srgbClr',val=color.lstrip('#'))
    sub(rp,'a:latin',typeface='Cambria Math');sub(rp,'a:ea',typeface=font)
    t=sub(r,'m:t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=text
    return r

def ast_to_omml(ast,color='C00000',points=32,font='Droid Sans Fallback'):
    def render(a):
        t=a['t']
        if t=='seq':return [n for child in a['items'] for n in render(child)]
        if t=='text':return [omml_run(a['v'],color,points,font)]
        if t=='frac':
            n=el('m:f');fp=sub(n,'m:fPr');tp=sub(fp,'m:type');tp.set(tag('m:val'),'bar')
            for key in ('num','den'):
                c=sub(n,'m:'+key);c.extend(render(a[key]))
            return [n]
        if t in ('sup','sub','subsup'):
            n=el('m:'+{'sup':'sSup','sub':'sSub','subsup':'sSubSup'}[t]);e=sub(n,'m:e');e.extend(render(a['base']))
            keys=['sub','sup'] if t=='subsup' else ['sup' if t=='sup' else 'sub']
            for key in keys:
                c=sub(n,'m:'+key);c.extend(render(a[key] if t=='subsup' else a['arg']))
            return [n]
        if t=='rad':
            n=el('m:rad');pr=sub(n,'m:radPr');dh=sub(pr,'m:degHide');dh.set(tag('m:val'),'1' if a.get('degree') is None else '0')
            degree=sub(n,'m:deg')
            if a.get('degree'):degree.extend(render(a['degree']))
            e=sub(n,'m:e');e.extend(render(a['base']));return [n]
        if t=='bar':
            n=el('m:bar');pr=sub(n,'m:barPr');pos=sub(pr,'m:pos');pos.set(tag('m:val'),a.get('position','bot'))
            e=sub(n,'m:e');e.extend(render(a['base']));return [n]
        if t=='matrix':
            n=el('m:m')
            for row in a['rows']:
                mr=sub(n,'m:mr')
                for cell in row:e=sub(mr,'m:e');e.extend(render(cell))
            return [n]
        raise ValueError('不支持 OMML AST '+str(t))
    m=el('m:oMath');m.extend(render(ast));return m

def inject_formula(root,spec):
    targets,ids=target_map(root);key=spec['target']
    if key not in targets:raise ValueError('公式目标未找到 '+key)
    wanted=targets[key]
    nv=next(n for n in visible_nodes(root) if n.get('id')==wanted)
    shape=next((a for a in nv.iterancestors() if a.tag in (tag('p:sp'),tag('p:pic'))),None)
    if shape is None:raise ValueError('公式目标不是形状/图片 '+key)
    parent=shape.getparent();index=parent.index(shape)
    old_xfrm=shape.find('.//a:xfrm',NS)
    if old_xfrm is None:raise ValueError('公式目标缺 xfrm '+key)
    alternate=ET.Element(tag('mc:AlternateContent'),nsmap={'mc':NS['mc'],'a14':NS['a14'],'m':NS['m']})
    choice=sub(alternate,'mc:Choice',Requires='a14')
    native=sub(choice,'p:sp');nvsp=sub(native,'p:nvSpPr')
    nvnew=copy.deepcopy(nv);nvsp.append(nvnew);sub(nvsp,'p:cNvSpPr',txBox='1');sub(nvsp,'p:nvPr')
    props=sub(native,'p:spPr');props.append(copy.deepcopy(old_xfrm));geom=sub(props,'a:prstGeom',prst='rect');sub(geom,'a:avLst');sub(props,'a:noFill')
    tx=sub(native,'p:txBody');body=sub(tx,'a:bodyPr',wrap='none',lIns='0',tIns='0',rIns='0',bIns='0',anchor='ctr');sub(body,'a:noAutofit');sub(tx,'a:lstStyle')
    para=sub(tx,'a:p');sub(para,'a:pPr',algn='l');a14=sub(para,'a14:m');mp=sub(a14,'m:oMathPara')
    pr=sub(mp,'m:oMathParaPr');jc=sub(pr,'m:jc');jc.set(tag('m:val'),'left')
    mp.append(ast_to_omml(spec['ast'],spec.get('color','C00000'),spec.get('points',32),spec.get('font','Droid Sans Fallback')))
    sub(para,'a:endParaRPr',lang='zh-CN',sz=round(spec.get('points',32)*100))
    fallback=sub(alternate,'mc:Fallback');fallback.append(copy.deepcopy(shape))
    parent.remove(shape);parent.insert(index,alternate)

def inject_table(root,spec):
    matches=[]
    for table in root.xpath('.//a:tbl',namespaces=NS):
        if any(a.tag==tag('mc:Fallback') for a in table.iterancestors()):continue
        vals=[[''.join(tc.xpath('.//a:t/text()',namespaces=NS)) for tc in tr.findall('a:tc',NS)] for tr in table.findall('a:tr',NS)]
        column_count=max((len(row) for row in vals),default=0)
        expected_values=[row+['']*(column_count-len(row)) for row in spec['match_values']]
        if vals==expected_values:
            if spec.get('rect'):
                frame=next(a for a in table.iterancestors() if a.tag==tag('p:graphicFrame'));xf=frame.find('p:xfrm',NS)
                off=xf.find('a:off',NS);ext=xf.find('a:ext',NS)
                actual=[int(off.get('x')),int(off.get('y')),int(ext.get('cx')),int(ext.get('cy'))]
                expected=[round(spec['rect'][k]*9525) for k in ('left','top','width','height')]
                if not all(abs(a-b)<=20 for a,b in zip(actual,expected)):continue
            matches.append(table)
    if len(matches)!=1:raise ValueError('表格内容匹配非唯一 '+spec['name']+' '+str(len(matches)))
    table=matches[0];frame=next(a for a in table.iterancestors() if a.tag==tag('p:graphicFrame'))
    nv=frame.find('.//p:cNvPr',NS);nv.set('name',spec['name'])
    original=copy.deepcopy(frame);has_math=False
    for ri,tr in enumerate(table.findall('a:tr',NS)):
        for ci,tc in enumerate(tr.findall('a:tc',NS)):
            runs=spec['cells'][ri][ci] if ci<len(spec['cells'][ri]) else [];body=tc.find('a:txBody',NS)
            if body is None:raise ValueError('表格单元格缺 txBody')
            for p in list(body.findall('a:p',NS)):body.remove(p)
            p=sub(body,'a:p');sub(p,'a:pPr',algn='l')
            for run in runs:
                if run['type']=='math':
                    math_node=ast_to_omml(run['ast'],spec.get('color','000000'),spec.get('points',32),spec.get('font','Droid Sans Fallback'))
                    # An empty TeX array cell is an intentional blank, not a
                    # zero-content math object (which Office importers reject).
                    if not ''.join(math_node.itertext()).strip():continue
                    has_math=True;mathzone=sub(p,'a14:m');mathzone.append(math_node)
                else:
                    r=sub(p,'a:r');rp=sub(r,'a:rPr',lang='zh-CN',sz=round(spec.get('points',32)*100));fill=sub(rp,'a:solidFill');sub(fill,'a:srgbClr',val=spec.get('color','000000'));sub(rp,'a:latin',typeface=spec.get('font','Droid Sans Fallback'));sub(rp,'a:ea',typeface=spec.get('font','Droid Sans Fallback'));t=sub(r,'a:t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=run['text']
    if has_math:
        parent=frame.getparent();idx=parent.index(frame);parent.remove(frame)
        alt=ET.Element(tag('mc:AlternateContent'),nsmap={'mc':NS['mc'],'a14':NS['a14'],'m':NS['m']});choice=sub(alt,'mc:Choice',Requires='a14');choice.append(frame);fallback=sub(alt,'mc:Fallback');fallback.append(original);parent.insert(idx,alt)

def inject_svg(root,spec,relationships,extra_parts):
    targets,_=target_map(root);target=spec['target']
    if target not in targets:raise ValueError('SVG 目标缺失 '+target)
    nv=next(n for n in visible_nodes(root) if n.get('id')==targets[target]);picture=next((a for a in nv.iterancestors() if a.tag==tag('p:pic')),None)
    if picture is None:raise ValueError('SVG 目标不是图片 '+target)
    blip=picture.find('p:blipFill/a:blip',NS)
    if blip is None:raise ValueError('SVG 图片缺 blip '+target)
    asvg='http://schemas.microsoft.com/office/drawing/2016/SVG/main'
    if blip.find('.//{'+asvg+'}svgBlip') is not None:return
    data=Path(spec['svg_path']).read_bytes();digest=hashlib.sha256(data).hexdigest()[:24];media='ppt/media/vector_'+digest+'.svg';extra_parts[media]=data
    rns='http://schemas.openxmlformats.org/package/2006/relationships';used={r.get('Id') for r in relationships};rid='rIdSvg'+digest
    if rid not in used:ET.SubElement(relationships,'{'+rns+'}Relationship',Id=rid,Type=NS['r']+'/image',Target='../media/vector_'+digest+'.svg')
    extlst=blip.find('a:extLst',NS)
    if extlst is None:extlst=sub(blip,'a:extLst')
    ext=sub(extlst,'a:ext',uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}')
    sv=ET.SubElement(ext,'{'+asvg+'}svgBlip',nsmap={'asvg':asvg});sv.set(tag('r:embed'),rid)

class TimingBuilder:
    def __init__(self,root,manifest):
        self.root=root;self.manifest=manifest;self.targets,_=target_map(root);self.uid=0
    def ident(self):self.uid+=1;return str(self.uid)
    def behavior(self,node,target,duration=1,attrs=(),**kw):
        b=sub(node,'p:cBhvr',**kw);sub(b,'p:cTn',id=self.ident(),dur=str(duration),fill='hold')
        te=sub(b,'p:tgtEl');sub(te,'p:spTgt',spid=self.targets[target])
        if attrs:
            names=sub(b,'p:attrNameLst')
            for text in attrs:sub(names,'p:attrName').text=text
        return b
    def effect(self,parent,effect):
        target=effect['target']
        if target not in self.targets:raise ValueError('动画目标不存在 '+target)
        typ=effect['type'];dur=int(effect.get('duration_ms',600))
        if typ in ('appear','hide'):
            s=sub(parent,'p:set');self.behavior(s,target,1,('style.visibility',))
            to=sub(s,'p:to');sub(to,'p:strVal',val='visible' if typ=='appear' else 'hidden')
        elif typ=='motion':
            dx=float(effect.get('dx',0));dy=float(effect.get('dy',0))
            if not math.isfinite(dx+dy):raise ValueError('非法运动坐标')
            w=self.manifest.get('width_px',1280);h=self.manifest.get('height_px',720)
            s=sub(parent,'p:animMotion',origin='layout',pathEditMode='relative',path=f'M 0 0 L {dx/w:.10g} {dy/h:.10g} E')
            self.behavior(s,target,dur,('ppt_x','ppt_y'),additive='base')
        elif typ=='rotation':
            s=sub(parent,'p:animRot',by=str(round(float(effect['degrees'])*60000)))
            self.behavior(s,target,dur,('r',),additive='base')
        elif typ=='wipe':
            # A genuine entry animation, with separate visibility setup.
            self.effect(parent,{'type':'appear','target':target})
            s=sub(parent,'p:animEffect',transition='in',filter='wipe('+effect.get('direction','down')+')')
            self.behavior(s,target,dur)
        else:raise ValueError('不支持动画 '+typ)
    def add(self):
        old=self.root.find('p:timing',NS)
        if old is not None:
            if not self.manifest.get('replace_existing_timing'):raise ValueError('已有动画，拒绝无意覆盖')
            self.root.remove(old)
        if not self.manifest.get('clicks'):return
        timing=el('p:timing');tnl=sub(timing,'p:tnLst');par=sub(tnl,'p:par');ct=sub(par,'p:cTn',id=self.ident(),dur='indefinite',restart='never',nodeType='tmRoot')
        child=sub(ct,'p:childTnLst');seq=sub(child,'p:seq',concurrent='1',nextAc='seek');main=sub(seq,'p:cTn',id=self.ident(),dur='indefinite',nodeType='mainSeq');lst=sub(main,'p:childTnLst')
        for click in self.manifest['clicks']:
            outer=sub(lst,'p:par');outer_ct=sub(outer,'p:cTn',id=self.ident(),fill='hold')
            st=sub(outer_ct,'p:stCondLst');sub(st,'p:cond',delay='indefinite')
            children=sub(outer_ct,'p:childTnLst');inner=sub(children,'p:par')
            effects=click['effects'];entry=any(e['type'] in ('appear','wipe') for e in effects)
            args={'id':self.ident(),'fill':'hold','nodeType':'clickEffect'}
            if entry:args.update(presetID='1',presetClass='entr',presetSubtype='0')
            else:args.update(presetID='8',presetClass='emph',presetSubtype='0')
            ict=sub(inner,'p:cTn',**args);cond=sub(ict,'p:stCondLst');sub(cond,'p:cond',delay='0');ecs=sub(ict,'p:childTnLst')
            for effect in effects:self.effect(ecs,effect)
        for q,event in [('p:prevCondLst','onPrev'),('p:nextCondLst','onNext')]:
            c=sub(seq,q);cond=sub(c,'p:cond',evt=event,delay='0');t=sub(cond,'p:tgtEl');sub(t,'p:sldTgt')
        # Timing belongs after clrMapOvr/transition and before extLst.
        ext=self.root.find('p:extLst',NS)
        if ext is None:self.root.append(timing)
        else:self.root.insert(self.root.index(ext),timing)

def validate_slide(root,manifest=None):
    targets,ids=target_map(root);issues=[]
    tids=[n.get('id') for n in root.xpath('.//p:cTn',namespaces=NS)]
    if len(tids)!=len(set(tids)):issues.append('时间节点 ID 重复')
    for target in root.xpath('.//p:spTgt',namespaces=NS):
        if target.get('spid') not in ids:issues.append('动画引用不存在 shape '+str(target.get('spid')))
    count=len(root.xpath('.//p:cTn[@nodeType="clickEffect"]',namespaces=NS))
    if manifest and count!=len(manifest.get('clicks',[])):issues.append('点击数量不符')
    return {'shape_count':len(ids),'timing_node_count':len(tids),'click_count':count,'omml_count':len(root.xpath('.//mc:Choice//m:oMath',namespaces=NS)),'issues':issues}

def patch_package(source:Path,dest:Path,manifest:dict):
    reports=[];by_slide={str(s['slide']):s for s in manifest['slides']}
    with zipfile.ZipFile(source) as zin:
        bad=zin.testzip()
        if bad:raise ValueError('源 ZIP 损坏 '+bad)
        changed={};extra_parts={}
        for number,spec in by_slide.items():
            name=f'ppt/slides/slide{number}.xml';root=ET.fromstring(zin.read(name));relname=f'ppt/slides/_rels/slide{number}.xml.rels'
            rns='http://schemas.openxmlformats.org/package/2006/relationships'
            rels=ET.fromstring(zin.read(relname)) if relname in zin.namelist() else ET.Element('{'+rns+'}Relationships',nsmap={None:rns})
            bind_images(root,spec.get('bindings',[]))
            for vector in spec.get('vectors',[]):inject_svg(root,vector,rels,extra_parts)
            for table in spec.get('tables',[]):inject_table(root,table)
            for formula in spec.get('formulas',[]):inject_formula(root,formula)
            for initial in spec.get('initial_rotations',[]):
                targets,_=target_map(root);wanted=targets[initial['target']]
                nv=next(n for n in visible_nodes(root) if n.get('id')==wanted)
                shape=next(a for a in nv.iterancestors() if a.tag==tag('p:sp'))
                shape.find('p:spPr/a:xfrm',NS).set('rot',str(round(initial['degrees']*60000)))
            for adjustment in spec.get('geometry_adjustments',[]):
                targets,_=target_map(root);wanted=targets[adjustment['target']]
                nv=next(n for n in visible_nodes(root) if n.get('id')==wanted)
                shape=next(a for a in nv.iterancestors() if a.tag==tag('p:sp'))
                xf=shape.find('p:spPr/a:xfrm',NS);off=xf.find('a:off',NS);ext=xf.find('a:ext',NS);r=adjustment['rect']
                if not all(math.isfinite(r[k]) for k in ('left','top','width','height')):raise ValueError('几何标注位置非法')
                off.set('x',str(round(r['left']*9525)));off.set('y',str(round(r['top']*9525)));ext.set('cx',str(round(r['width']*9525)));ext.set('cy',str(round(r['height']*9525)))
            TimingBuilder(root,{**manifest,**spec}).add()
            report=validate_slide(root,spec);report['slide']=int(number);reports.append(report)
            if report['issues']:raise ValueError(json.dumps(report,ensure_ascii=False))
            changed[name]=ET.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            changed[relname]=ET.tostring(rels,xml_declaration=True,encoding='UTF-8',standalone=True)
        types=ET.fromstring(zin.read('[Content_Types].xml'));ctns='http://schemas.openxmlformats.org/package/2006/content-types'
        if extra_parts and not any(x.get('Extension')=='svg' for x in types):ET.SubElement(types,'{'+ctns+'}Default',Extension='svg',ContentType='image/svg+xml')
        changed['[Content_Types].xml']=ET.tostring(types,xml_declaration=True,encoding='UTF-8',standalone=True)
        temporary=dest.with_name(dest.name+'.'+uuid.uuid4().hex+'.zip.tmp')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item,changed.pop(item.filename,zin.read(item.filename)))
            for name,data in {**changed,**extra_parts}.items():
                if name not in zin.namelist():zout.writestr(name,data)
    with temporary.open('rb') as stream:os.fsync(stream.fileno())
    with zipfile.ZipFile(temporary) as check:
        if check.testzip():raise ValueError('Native package temporary CRC failure')
    os.replace(temporary,dest)
    return {'input':str(source),'output':str(dest),'slides':sorted(reports,key=lambda x:x['slide']),'issues':[]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--report',type=Path,required=True)
    a=ap.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    r=patch_package(a.input,a.output,json.loads(a.manifest.read_text()));a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({'slides':len(r['slides']),'omml':sum(x['omml_count'] for x in r['slides']),'clicks':sum(x['click_count'] for x in r['slides'])}))
if __name__=='__main__':main()
