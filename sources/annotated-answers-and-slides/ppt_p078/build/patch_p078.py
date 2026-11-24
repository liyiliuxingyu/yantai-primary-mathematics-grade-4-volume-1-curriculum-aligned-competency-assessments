#!/usr/bin/env python3
"""Page-78 photo corrections, preserving all original slide IDs and timings."""
from pathlib import Path
import copy, hashlib, importlib.util, json, os, re, shutil, subprocess, sys, zipfile
from lxml import etree as E
import fitz

BASE=Path(__file__).resolve().parents[2]
if (BASE/'diagram_source/xelatex.fmt').exists():
    os.environ['TEXFORMATS']=str(BASE/'diagram_source')+':'+os.environ.get('TEXFORMATS','')
if not subprocess.run(['kpsewhich','standalone.cls'],capture_output=True).stdout.strip():
    os.environ['TEXMF']='{/usr/share/texlive/texmf-dist,/usr/share/texmf}'
PROJECT=BASE/'project'; WORK=BASE/'ppt_p078'; OUT=BASE/'deliverables/讲解课件'
ASSETS=PROJECT/'ppt_p078/assets'; ASSETS.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(PROJECT/'followup_style/ppt'),str(PROJECT/'ppt_builder')]
spec=importlib.util.spec_from_file_location('native_patch',PROJECT/'ppt_average/build/native_patch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
q=m.q; NS=m.NS
approved=json.loads((BASE/'approved_changes.json').read_text())
inventory=json.loads((WORK/'baseline_inventory.json').read_text())
slides={s['slide']:s for s in inventory['slides']}
objects={o['name']:o for s in inventory['slides'] for o in s['objects']}
rules={}
def add(ui,op):
    rules.setdefault(ui,{'volume':5,'ui_slide':ui,'slide':slides[ui]['part_number'],'key':next(o['name'].split('_b')[0] for o in slides[ui]['objects'] if o['name'].startswith('p078_')),'ops':[]})['ops'].append(op)
def text(ui,name,value,rect=None,color='C00000'):
    add(ui,{'type':'text','name':name,'text':value,'rect':rect or objects[name]['rect'],'points':32,'color':color})
def math(ui,name,tex,rect=None):
    add(ui,{'type':'math','name':name,'tex':tex,'rect':rect or objects[name]['rect'],'points':32,'color':'C00000','min_scale':.68})

# Ordinary editable question text.  Only the first reading page gains the
# previously omitted section instruction; the original body anchors move down.
for ui,prefix in [(115,'p078_s01_b000'),(119,'p078_s01_b008')]:
    for o in slides[ui]['objects']:
        if not o['name'].startswith(prefix):continue
        if o['native_math']:continue
        value=o['text'].replace('138cm','136cm').replace('146cm','140cm').replace('高是136cm，他们可能有','高是136cm。他们可能有')
        rect=list(o['rect'])
        if ui==115:rect[1]+=136
        if value!=o['text'] or ui==115:text(ui,o['name'],value,rect,'000000')
add(115,{'type':'new_text','name':'p078_section_choice_instruction','text':'二、选择（将正确答案的序号填在括号里）。\n（每题2分，共12分）','rect':[64,108,1152,116],'points':32,'color':'000000'})

# The first click retains the same ten original shape IDs.  A non-strict
# lower bound at 140 avoids deciding whether the boundary itself is admitted.
text(117,'p078_s01_b002_0_p0','三人总身高')
math(117,'p078_s01_b002_0_p1',r'136\times3=408')
text(117,'p078_s01_b002_0_p2','厘米。能坐者身高至少',[525.613333,124.500052,426.666667,58])
math(117,'p078_s01_b002_0_p3','140',[955.28,138.473385,61.146667,30.053333])
text(117,'p078_s01_b002_0_p4','厘米；',[1019.426667,124.500052,174.666667,58])
text(117,'p078_s01_b002_1_p0','3人全能坐，至少需',[64,198.500052,384,58])
math(117,'p078_s01_b002_1_p1',r'140\times3=420',[448,210.700052,245.28,33.6])
text(117,'p078_s01_b002_1_p2','厘米。',[696.28,198.500052,174.666667,58])
math(117,'p078_s01_b002_2_p0','408<420',[64,282.340052,201,38.32])
text(117,'p078_s01_b002_2_p1','，所以不可能3人全能坐。',[268,272.500052,800,58])
for name,tex in [('p078_s01_b003_3_p1',r'(136,136,136)'),('p078_s01_b004_4_p1',r'(146,131,131)'),('p078_s01_b005_5_p1',r'(146,146,116)')]:math(117,name,tex)
math(118,'p078_s01_b006_0_p1','136')

for ui,name in [(132,'p078_s06_b000_0_p0'),(134,'p078_s06_b003_0_p0')]:
    text(ui,name,objects[name]['text'].replace('快板','秧歌'),color='000000')

# Graph explanation has the approved comparative statement, without invented
# point temperatures; keep its original two native 22 formula anchors.
text(130,'p078_s05_b002_0_p0','观察第二天四个气温点相对')
text(130,'p078_s05_b002_0_p2','摄氏度虚线，高出与低下的')
text(130,'p078_s05_b002_1_p0','部分大致相抵，移多补少后平均约为')
text(130,'p078_s05_b002_1_p2','摄氏度。')
text(130,'p078_s05_b002_2_p0','第一天偏高，第三天与第四天整体偏低。',[64,272.500052,1152,58])

def compile_diagram(name,tikz):
    folder=ASSETS/name;folder.mkdir(exist_ok=True)
    (folder/(name+'.tikz.tex')).write_text(tikz+'\n')
    font=PROJECT/'fonts/DroidSansFallback.ttf'
    source=folder/(name+'.tex')
    source.write_text('\\documentclass[tikz,border=1pt]{standalone}\n\\usepackage{fontspec}\n\\setmainfont{'+font.name+'}[Path={'+str(font.parent)+'/}]\n\\begin{document}\n\\input{'+name+'.tikz.tex}\n\\end{document}\n')
    run=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape',source.name],cwd=folder,capture_output=True,text=True)
    (folder/'compile.stdout.txt').write_text(run.stdout+run.stderr)
    assert run.returncode==0 and 'Missing character' not in run.stdout,(source,run.stdout[-1000:])
    pdf=source.with_suffix('.pdf');svg=source.with_suffix('.svg');png=source.with_suffix('.png')
    subprocess.run(['pdftocairo','-svg',str(pdf),str(svg)],check=True)
    subprocess.run(['pdftoppm','-singlefile','-r','192','-png',str(pdf),str(png.with_suffix(''))],check=True,stdout=subprocess.DEVNULL)
    with fitz.open(pdf) as doc:w,h=doc[0].rect.width*4/3,doc[0].rect.height*4/3
    return {'svg':svg,'png':png,'width':w,'height':h,'stem':'p078_'+name+'_'+hashlib.sha256(svg.read_bytes()).hexdigest()[:12]}

ship=next(c for c in approved['changes'] if c['key']=='p078_s01')['new_record']['diagrams'][0]
shipasset=compile_diagram('pirate_ship_140',ship['tikz'])
add(116,{'type':'picture','name':'p078_s01_b001_0','asset':shipasset})

def picture(root,rels,op,extra):
    old=m.find_shape(root,op['name']);nv=copy.deepcopy(m.c_nv(old));rect=op.get('rect',m.get_rect(old));a=op['asset']
    x,y,w,h=rect;scale=min(w/a['width'],h/a['height']);w=a['width']*scale;h=a['height']*scale
    ids={}
    for ext in ('png','svg'):
        rid='rIdP078'+a['stem']+ext;ids[ext]=rid
        assert not any(r.get('Id')==rid for r in rels)
        E.SubElement(rels,'{'+m.PR+'}Relationship',Id=rid,Type=NS['r']+'/image',Target='../media/'+a['stem']+'.'+ext)
        extra['ppt/media/'+a['stem']+'.'+ext]=a[ext].read_bytes()
    pic=m.el('p:pic');n=m.sub(pic,'p:nvPicPr');n.append(nv);m.sub(n,'p:cNvPicPr');m.sub(n,'p:nvPr')
    bf=m.sub(pic,'p:blipFill');bl=m.sub(bf,'a:blip');bl.set(q('r:embed'),ids['png']);exl=m.sub(bl,'a:extLst');ex=m.sub(exl,'a:ext',uri='{96DAC541-7B7A-43D3-8B79-37D633B846F1}');sv=E.SubElement(ex,'{'+m.SVG+'}svgBlip',nsmap={'asvg':m.SVG});sv.set(q('r:embed'),ids['svg']);m.sub(m.sub(bf,'a:stretch'),'a:fillRect')
    pr=m.sub(pic,'p:spPr');xf=m.sub(pr,'a:xfrm');m.sub(xf,'a:off',x=round(x*9525),y=round(y*9525));m.sub(xf,'a:ext',cx=round(w*9525),cy=round(h*9525));m.sub(m.sub(pr,'a:prstGeom',prst='rect'),'a:avLst')
    outer=m.container(old);outer.getparent().replace(outer,pic)
    return {'name':op['name'],'rect':[x,y,w,h],'svg':str(a['svg'].relative_to(PROJECT)),'png':str(a['png'].relative_to(PROJECT)),'dedicated_media':a['stem']}

def new_text(root,op):
    tree=root.find('p:cSld/p:spTree',NS);newid=max(int(x.get('id')) for x in m.visible_nodes(root))+1
    sp=m.el('p:sp');nv=m.sub(sp,'p:nvSpPr');m.sub(nv,'p:cNvPr',id=newid,name=op['name']);m.sub(nv,'p:cNvSpPr',txBox='1');m.sub(nv,'p:nvPr');pr=m.sub(sp,'p:spPr');xf=m.sub(pr,'a:xfrm');m.sub(xf,'a:off',x='0',y='0');m.sub(xf,'a:ext',cx='0',cy='0');tree.append(sp)
    return m.patch_text(root,op)

def serializable(obj):
    if isinstance(obj,Path):return str(obj)
    raise TypeError(type(obj).__name__)

def run(graphsvg=None,graphpng=None):
    if graphsvg:
        svg=Path(graphsvg);png=Path(graphpng)
        dest=ASSETS/'temperatures_photo';dest.mkdir(exist_ok=True)
        for f in svg.parent.glob('p078_temperatures_photo.*'):
            if f.suffix in ('.tikz','.tex','.svg','.png','.pdf'):shutil.copy2(f,dest/f.name)
        with fitz.open(svg.with_suffix('.pdf')) as doc:w,h=doc[0].rect.width*4/3,doc[0].rect.height*4/3
        asset={'svg':dest/svg.name,'png':dest/png.name,'width':w,'height':h,'stem':'p078_temperatures_'+hashlib.sha256(svg.read_bytes()).hexdigest()[:12]}
        add(129,{'type':'picture','name':'p078_s05_b001_0','asset':asset})
    source=Path(inventory['source']);dest=OUT/source.name;OUT.mkdir(parents=True,exist_ok=True)
    assets={}
    for r in rules.values():
        for op in r['ops']:
            if op['type']=='math':assets[id(op)]=m.compile_asset(op,ASSETS,PROJECT/'fonts/DroidSansFallback.ttf')
    (WORK/'rules.json').write_text(json.dumps(sorted(rules.values(),key=lambda x:x['ui_slide']),ensure_ascii=False,indent=2,default=serializable)+'\n')
    with zipfile.ZipFile(source) as z:
        original={i.filename:z.read(i.filename) for i in z.infolist()};parts=dict(original);extra={};reports=[]
        for ui,r in sorted(rules.items()):
            part=f'ppt/slides/slide{r["slide"]}.xml';rp=f'ppt/slides/_rels/slide{r["slide"]}.xml.rels';b=parts[part];root=E.fromstring(b);rels=E.fromstring(parts[rp]);ids=m.logical_ids(root);ops=[]
            for op in r['ops']:
                if op['type']=='math':result=m.patch_math(root,rels,op,assets[id(op)],extra)
                elif op['type']=='text':result=m.patch_text(root,op)
                elif op['type']=='new_text':result=new_text(root,op)
                elif op['type']=='picture':result=picture(root,rels,op,extra)
                else:raise ValueError(op['type'])
                ops.append(result)
            m.assert_preserved_ids(ids,m.logical_ids(root));nb=m.xml(root);t=m.timing(b)
            if t:nb=re.sub(rb'<p:timing>.*?</p:timing>',lambda _:t,nb,flags=re.S)
            assert m.timing(nb)==t;parts[part]=nb
            rb=m.xml(rels)
            if rb!=parts[rp]:parts[rp]=rb
            reports.append({'slide':ui,'part_number':r['slide'],'key':r['key'],'ops':ops})
        for k,b in extra.items():parts[k]=b
        allowed={f'ppt/slides/slide{r["slide"]}.xml' for r in rules.values()}|{f'ppt/slides/_rels/slide{r["slide"]}.xml.rels' for r in rules.values()}
        changed=[k for k in original if original[k]!=parts[k]];assert set(changed)<=allowed
        for k,b in original.items():
            if re.fullmatch(r'ppt/slides/slide\d+\.xml',k):
                assert m.timing(parts[k])==m.timing(b),k
                m.assert_preserved_ids(m.logical_ids(E.fromstring(b)),m.logical_ids(E.fromstring(parts[k])))
        with zipfile.ZipFile(dest.with_suffix('.tmp'),'w') as out:
            for info in z.infolist():out.writestr(info,parts.pop(info.filename))
            for k,b in parts.items():out.writestr(k,b,compress_type=zipfile.ZIP_DEFLATED)
        dest.with_suffix('.tmp').replace(dest)
    qa={'volume':5,'source':str(source),'source_sha256':m.sha(source.read_bytes()),'output':str(dest),'output_sha256':m.sha(dest.read_bytes()),'total_slides':433,'changed_slides':sorted(rules),'changed_original_parts':changed,'new_parts':sorted(extra),'timing_bytes_all_unchanged':True,'all_original_shape_ids_names_order_preserved':True,'new_static_instruction_shape':True,'changes':reports}
    (WORK/'qa_package.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:qa[k] for k in ('output','output_sha256','changed_slides')},ensure_ascii=False))

if __name__=='__main__':run(*sys.argv[1:])
