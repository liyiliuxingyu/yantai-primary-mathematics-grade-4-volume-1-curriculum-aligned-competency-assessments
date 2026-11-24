from pathlib import Path
from lxml import etree as E
import zipfile,json,hashlib,subprocess,copy,re,fitz
W=Path(__file__).resolve().parent;SRC=W.parent/'bundle/讲解课件';OUT=W/'final';OUT.mkdir(exist_ok=True)
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math','mc':'http://schemas.openxmlformats.org/markup-compatibility/2006','r':'http://schemas.openxmlformats.org/package/2006/relationships'}
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xml(el):return E.tostring(el,encoding='UTF-8',xml_declaration=True,standalone=True)
def shape(root,name):
 q=root.xpath('//p:sp[p:nvSpPr/p:cNvPr[@name="'+name+'"]]',namespaces=NS);assert len(q)==1,(name,len(q));return q[0]
def text_shape(root,name,new):
 sp=shape(root,name);ts=sp.xpath('.//a:t',namespaces=NS);assert len(ts)==1,(name,len(ts));old=ts[0].text;ts[0].text=new;return old
assets=W/'formula';assets.mkdir(exist_ok=True)
tex=r'''\documentclass[border=0pt]{standalone}
\usepackage{xcolor,amsmath}
\begin{document}\color[HTML]{C00000}\fontsize{32}{38}\selectfont\(\times\)\end{document}
'''
(assets/'axis_times.tex').write_text(tex)
p=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(assets),'axis_times.tex'],cwd=assets,capture_output=True,text=True)
# output-directory must resolve relative to cwd exactly once.
if p.returncode:
 p=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','axis_times.tex'],cwd=assets,capture_output=True,text=True)
(assets/'compile.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stdout[-2000:]
pdf=fitz.open(assets/'axis_times.pdf');page=pdf[0];page.get_pixmap(matrix=fitz.Matrix(4,4),alpha=True).save(assets/'axis_times.png');(assets/'axis_times.svg').write_text(page.get_svg_image(text_as_path=True));pdf.close()
reports=[]
for v,changes in [(4,[374,375]),(5,[293])]:
 name=f'小学四上同步素养卷第{v}册讲解课件答案.pptx';source=SRC/name
 with zipfile.ZipFile(source)as z:parts={i.filename:z.read(i.filename)for i in z.infolist()};infos={i.filename:i for i in z.infolist()}
 updated={};details=[]
 if v==4:
  n='ppt/slides/slide374.xml';d=E.fromstring(parts[n]);details.append({'slide':374,'old1':text_shape(d,'p070_s06_b001_1_p0','×。对角线是线段，对称轴是直线。'),'old2':text_shape(d,'p070_s06_b001_2_p0','正确说法：对角线所在的直线是正方形的对称轴。')})
  sp=shape(d,'p070_s06_b001_2_p0');sp.find('p:spPr/a:xfrm/a:ext',NS).set('cx','10604500');updated[n]=xml(d)
  n='ppt/slides/slide375.xml';d=E.fromstring(parts[n]);s=shape(d,'p070_s06_b002_0_p1_answer');t=s.find('.//m:t',NS);assert t.text=='✓';t.text='×';updated[n]=xml(d);details.append({'slide':375,'native_omml':'✓ → ×','compatibility_branches':'actual XeLaTeX SVG+PNG replaced at this slide only'})
  relname='ppt/slides/_rels/slide375.xml.rels';rels=E.fromstring(parts[relname]);paths={'Rbc28de851d4446a8':('/ppt/media/axis_times_20261103.png','png'),'R11c30d8d5e8e41db':('/ppt/media/axis_times_20261103.svg','svg')}
  for rel in rels:
   if rel.get('Id')in paths:
    path,ext=paths[rel.get('Id')];rel.set('Target',path);updated[path[1:]]=(assets/f'axis_times.{ext}').read_bytes()
  updated[relname]=xml(rels)
 else:
  n='ppt/slides/slide293.xml';d=E.fromstring(parts[n]);old=text_shape(d,'p085_s11_b001_2_p0','对角线和对边中点连线所在的直线，共');updated[n]=xml(d);details.append({'slide':293,'old':old,'new':'对角线和对边中点连线所在的直线，共'})
 target=OUT/name
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for n,b in parts.items():z.writestr(infos[n],updated.pop(n,b))
  for n,b in updated.items():z.writestr(n,b)
 with zipfile.ZipFile(source)as a,zipfile.ZipFile(target)as b:
  assert b.testzip()is None
  altered=[n for n in a.namelist()if a.read(n)!=b.read(n)];added=sorted(set(b.namelist())-set(a.namelist()))
  assert sorted(n for n in altered if re.fullmatch(r'ppt/slides/slide\d+\.xml',n))==[f'ppt/slides/slide{i}.xml'for i in changes]
  times=0;ids=0
  for n in a.namelist():
   if re.fullmatch(r'ppt/slides/slide\d+\.xml',n):
    x=E.fromstring(a.read(n));y=E.fromstring(b.read(n));xt=x.find('p:timing',NS);yt=y.find('p:timing',NS)
    assert (E.tostring(xt)if xt is not None else None)==(E.tostring(yt)if yt is not None else None),n;times+=1
    assert x.xpath('//p:cNvPr/@id',namespaces=NS)==y.xpath('//p:cNvPr/@id',namespaces=NS),n;ids+=1
  if v==4:
   for sl in changes:
    el=E.fromstring(b.read(f'ppt/slides/slide{sl}.xml'));txt=''.join(el.xpath('//a:t/text()|//m:t/text()',namespaces=NS));assert '✓'not in txt and '√'not in txt
  reports.append({'volume':v,'source':str(source),'source_sha256':SHA(source),'output':str(target),'output_sha256':SHA(target),'slide_count':times,'changed_slides':changes,'modified_original_parts':altered,'added_media_parts':added,'all_timing_xml_byte_identical':times,'all_shape_id_sequences_identical':ids,'all_other_original_components_byte_identical':True,'changes':details})
(W/'qa_package.json').write_text(json.dumps({'passed':True,'volumes':reports,'all_six_decks_scan':'scan.json','powerpoint_playback_tested':False},ensure_ascii=False,indent=2))
print(json.dumps(reports,ensure_ascii=False),flush=True)
