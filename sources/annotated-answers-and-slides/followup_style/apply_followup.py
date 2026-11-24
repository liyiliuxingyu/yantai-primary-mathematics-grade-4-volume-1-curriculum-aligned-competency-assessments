from pathlib import Path
import json,hashlib,shutil

R=Path(__file__).resolve().parents[1]; W=R/'followup_style'
J=lambda p:json.loads(p.read_text())
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
backup=W/'before';backup.mkdir(exist_ok=True)
for f in ['questions/p005.json','questions/p007.json','detailed_layout/notes_A.json','detailed_layout/current_release.json','tikz_index.json','diagram_index.json','detailed_layout/source_freeze.json','ppt_builder/current_inventory.json']:
 p=R/f;q=backup/f;q.parent.mkdir(parents=True,exist_ok=True)
 assert not q.exists(),f
 shutil.copy2(p,q)
shutil.copy2(R/'deliverables/小学同步素养四年级上册数学答案.pdf',backup/'previous.pdf')

labels={
5:[r'扇贝单价\(12\)元',r'梭子蟹单价\(96\)元',r'两种单价和\(108\)元',r'\(3\)倍',r'单价和的\(3\)倍\(324\)元',r'多\(10\)元',r'礼盒单价\(334\)元'],
7:[r'椅子单价\(14\)元',r'椅子总价\(70\)元',r'椅子数量\(5\)把',r'总金额\(230\)元',r'桌子总价\(160\)元',r'桌子单价\(80\)元',r'桌子数量\(2\)张']}
coords={5:[(0,0),(4.3,0),(0,-1),(4.3,-1),(0,-2),(4.3,-2),(0,-3)],7:[(2.15,0),(0,-1),(4.3,-1),(0,-2),(4.3,-2),(0,-3),(4.3,-3)]}
edges={5:[(0,2),(1,2),(2,4),(3,4),(4,6),(5,6)],7:[(0,1),(0,2),(1,3),(1,4),(4,5),(4,6)]}
ops={5:['+',r'\times','+'],7:[r'\div','-',r'\times']}
keys={5:'p005_s04',7:'p007_s08'}
names={}
for pg in [5,7]:
 p=R/f'questions/p{pg:03}.json';d=J(p);q=next(q for q in d['records']if q['key']==keys[pg]);a=next(x for x in q['diagrams']if x['role']=='answer')
 tex=r'\begin{tikzpicture}[x=1cm,y=1cm,every node/.style={font=\small},b/.style={draw,minimum width=3.7cm,minimum height=.6cm,align=center}]'
 for i,((x,y),s) in enumerate(zip(coords[pg],labels[pg])):
  if pg==5 and i in(0,1):s=s.replace('元','元/千克')
  tex+=r'\node[b](n'+str(i)+')at('+str(x)+','+str(y)+r'){{\color{red}'+s+'}};'
 for u,v in edges[pg]:tex+=r'\draw(n'+str(u)+'.'+('south' if pg==7 else 'south')+')--(n'+str(v)+'.north);'
 for j,op in enumerate(ops[pg]):tex+=r'\node[red]at(2.15,'+str(-j if pg==5 else -j-1)+r'){$'+op+'$};'
 tex+=r'\end{tikzpicture}'
 a['tikz']=tex;a['notes']='按第一单元信息窗三的数量关系分析形式补齐数量名称、数据和单位；保留原分析方向与每份数×份数。'
 (R/f'tikz/{a["name"]}.tikz.tex').write_text(tex+'\n');names[a['name']]=a
 if pg==5:
  q['answer_latex']=r'从条件开始分析：先求两种单价之和，再求这个和的3倍，最后加多出的10元。'+r'\par 方法一：\[\begin{aligned}&(12+96)\times3+10\\={}&108\times3+10\\={}&324+10\\={}&334\text{（元）}\end{aligned}\]答：每盒即食海鲜礼盒334元。'+r'\par 方法二（乘法分配律）：\[\begin{aligned}&12\times3+96\times3+10\\={}&36+288+10\\={}&324+10\\={}&334\text{（元）}\end{aligned}\]答：每盒即食海鲜礼盒334元。'+r'\par 检验：\[\begin{aligned}&(334-10)\div3\\={}&324\div3\\={}&108\end{aligned}\]与两种单价之和\(12+96=108\)一致。'
 else:
  q['answer_latex']=r'从问题开始分析：椅子单价需要椅子总价和椅子数量；椅子总价需要总金额和桌子总价；桌子总价需要桌子单价和桌子数量。'+r'\par 方法一：\[\begin{aligned}&(230-80\times2)\div5\\={}&(230-160)\div5\\={}&70\div5\\={}&14\text{（元）}\end{aligned}\]答：每把椅子的单价是14元。'+r'\par 方法二：将总金额与桌款分别平均分成5份，再求每份的差。\[\begin{aligned}&230\div5-80\times2\div5\\={}&46-160\div5\\={}&46-32\\={}&14\text{（元）}\end{aligned}\]答：每把椅子的单价是14元。'+r'\par 检验：\[\begin{aligned}&80\times2+14\times5\\={}&160+70\\={}&230\text{（元）}\end{aligned}\]与小票总金额一致。'
 q['verification']['changes'].append('按第一单元信息窗三补齐原数量关系分析树的名称、数据、单位和回顾检验。')
 save(p,d)

npath=R/'detailed_layout/notes_A.json';nd=J(npath);boxes=J(W/'detected_boxes.json')
for pg in[5,7]:
 n=next(n for n in nd['records']if n['key']==keys[pg]);assert not n.get('local_replacements')
 n['local_replacements']=[]
 for i,(b,s) in enumerate(zip(boxes[str(pg)],labels[pg])):
  rect=[b[0]+.35,b[1]+.35,b[2]-.35,b[3]-.35]
  n['local_replacements'].append({'rect':rect,'latex':s,'font_size':(7.5 if i<2 else 8.5) if pg==5 else 8.5,'align':'center','valign':'center','clear_to_white':True,'kind':'analysis_box_answer','original_prompt_replaced':pg==7 and i==0,'reason':'原分析框内补齐数量名称、数据及单位；框线、连接线及算符圈不变。'+('单价的每千克含义保留在原题干。' if pg==5 else '')})
 if pg==5:
  n['latex']=r'从条件开始分析：先把两种单价相加，再求这个和的3倍，最后加多出的10元。\par 方法一：\[\begin{aligned}&(12+96)\times3+10\\={}&108\times3+10\\={}&324+10\\={}&334\text{（元）}\end{aligned}\]答：每盒即食海鲜礼盒334元。\par 方法二：用乘法分配律，先分别求两种单价的3倍，再合并并加多出的部分：\[\begin{aligned}&12\times3+96\times3+10\\={}&36+288+10\\={}&324+10\\={}&334\text{（元）}\end{aligned}\]两种方法结果相同。\par 检验：\[\begin{aligned}&(334-10)\div3\\={}&324\div3\\={}&108\end{aligned}\]与\(12+96=108\)一致。多出的10元不参加3倍计算。'
 else:
  n['latex']+=r'\par 检验：\[\begin{aligned}&80\times2+14\times5\\={}&160+70\\={}&230\text{（元）}\end{aligned}\]与小票总金额一致。'
 n['reason']+=' 本次按信息窗三补齐原分析树，并用还原条件的方法检验；已有原位计算保留。'
save(npath,nd)
for fn,field in [('tikz_index.json','figures'),('diagram_index.json','diagrams')]:
 p=R/fn;d=J(p)
 for x in d[field]:
  if x['diagram_name']in names:
   a=names[x['diagram_name']];x['notes']=a['notes'];x['source_tikz_sha256']=hashlib.sha256(a['tikz'].encode()).hexdigest();x['tikz_file_sha256']=SHA(R/f'tikz/{a["name"]}.tikz.tex')
 save(p,d)
save(W/'style_spec.json',{'changed_keys':list(keys.values()),'box_labels':labels,'boxes':boxes,'reference':'第一单元信息窗三','preserved_prior_change':'p003_s07','baseline_pdf_sha256':SHA(backup/'previous.pdf'),'new_box_labels':14,'coverage_pages':list(range(4,109))})
print('Updated two question records, two TikZ answers, fourteen original analysis boxes and detailed notes.')
