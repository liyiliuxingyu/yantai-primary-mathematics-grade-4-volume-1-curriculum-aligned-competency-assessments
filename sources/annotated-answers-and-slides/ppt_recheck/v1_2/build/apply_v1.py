from pathlib import Path
import json,sys,re,argparse
HERE=Path(__file__).resolve().parent
PROJECT=next(q for p in HERE.parents for q in (p,p/'project') if (q/'ppt_builder').is_dir())
ROOT=next(p for p in HERE.parents if (p/'bundle/讲解课件').is_dir())
WORK=HERE.parent
sys.path.insert(0,str(PROJECT/'simplify_update/ppt_1_2/build'))
import patch_owned as O
C=O.C
old_patch_math=C.patch_math
def patch_math_upright(root,rels,op,asset,extra):
 report=old_patch_math(root,rels,op,asset,extra)
 native=C.find_shape(root,op['name'])
 for run in native.findall('.//m:r',C.NS):
  if re.search(r'[\u3400-\u9fff]',''.join(run.xpath('./m:t/text()',namespaces=C.NS))):
   pr=run.find('m:rPr',C.NS)
   if pr is None:pr=C.el('m:rPr');run.insert(0,pr)
   sty=pr.find('m:sty',C.NS)
   if sty is None:sty=C.sub(pr,'m:sty')
   sty.set(C.q('m:val'),'p')
 return report
C.patch_math=patch_math_upright
def note(name,rows,why,y=206,title='简便提示（学完运算律后）',h=410):
 return {'type':'note','name':name,'title':title,'text':why,'rect':[650,y,560,h],'title_points':22,'note_points':18,'points':32,'rows':rows}
def math(name,tex,rect=None):
 r={'type':'math','name':name,'tex':tex,'points':32}
 if rect:r['rect']=rect
 return r
def text(name,value,rect,points=32):return {'type':'text','name':name,'text':value,'rect':rect,'points':points}
rules=[
 {'volume':1,'slide':28,'key':'p002_s01','ops':[note('p002_s01_b006_3',[
  r'130+130\div2\times32',r'130+130\times(32\div2)',r'130+130\times16',r'130+2080',r'2210\text{(米)}'],'32先除以2，避免先求65。',124,h=430)]},
 {'volume':1,'slide':29,'key':'p002_s01','ops':[note('p002_s01_b010_2',[
  r'130\div2\times(2+32)',r'130\div2\times34',r'130\times(34\div2)',r'130\times17',r'2210\text{(米)}'],'先合并时间，再将34除以2。',124,h=430)]},
 {'volume':1,'slide':66,'key':'p003_s05','ops':[note('p003_s05_b004_4',[
  r'36\times58',r'36\times(60-2)',r'36\times60-36\times2',r'2160-72',r'2088'],'58看成60少2，再减回多算部分。')]},
 {'volume':1,'slide':73,'key':'p003_s07','ops':[
  text('p003_s07_b012_0','总量与已处理量分别平均分（学完运算律后简算）',[64,120,1152,64]),
  math('p003_s07_b014_2',r'(4\div4)\times18-32\div4',[106,268.4533,1100,45.0933]),
  math('p003_s07_b015_3',r'1\times18-8',[106,343.2,1100,45.0933]),
  {'type':'math','name':'p003_s07_b016_4','rows':[r'18-8',r'10\text{(千克)}'],'rect':[64,401,1152,112],'points':32},
  {'type':'move','name':'p003_s07_b017_5_p0','rect':[64,545.5,302.6666666666667,58]},
  {'type':'move','name':'p003_s07_b017_5_p1','rect':[362.6666666666667,559.4733858267717,41.64,30.053333333333335]},
  {'type':'move','name':'p003_s07_b017_5_p2','rect':[407.3066666666667,545.5,132,58]}]},
 {'volume':1,'slide':120,'key':'p005_s05','ops':[
  text('p005_s05_b006_6_p0','简便提示',[650,270,560,36],22),
  {'type':'math','name':'p005_s05_b006_6_p1','rows':[r'(630-78)\times14\div7',r'(630-78)\times(14\div7)',r'552\times2',r'1104'],'rect':[650,346,560,288],'points':32},
  text('p005_s05_b006_6_p2','（学完运算律后）',[650,308,560,32],18),
  text('p005_s05_b006_6_p3','括号减法与除法可同时算。',[650,641,560,28],18),
  text('p005_s05_b006_6_p4','',[64,124,1,1],1),
  text('p005_s05_b006_6_p5','',[64,124,1,1],1),
  text('p005_s05_b006_6_p6','',[64,124,1,1],1)]},
 {'volume':1,'slide':162,'key':'p007_s05','ops':[note('p007_s05_b004_4',[
  r'73\times93',r'73\times(100-7)',r'73\times100-73\times7',r'7300-511',r'6789'],'93看成100少7，再减回多算部分。')]},
 {'volume':1,'slide':256,'key':'p011_s08','ops':[note('p011_s08_b003_3',[
  r'63\times25',r'(60+3)\times25',r'60\times25+3\times25',r'1500+75',r'1575'],'把63按位展开；再与前面所得7相加。',200,title='运算律口算提示（学完运算律后）')]},
 {'volume':1,'slide':339,'key':'p015_s08','ops':[note('p015_s08_b004_4',[
  r'48\times17',r'(50-2)\times17',r'50\times17-2\times17',r'850-34',r'816'],'48看成50少2，两个乘法同时算。',200)]}
]
(WORK/'rules_v1.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2)+'\n')
folder=WORK/'formulas';folder.mkdir(exist_ok=True);font=PROJECT/'fonts/DroidSansFallback.ttf';assets={}
for s in rules:
 for op in s['ops']:
  if op['type'] not in ('note','math'):continue
  if op.get('rows'):
   a={'row_assets':[C.compile_asset({**op,'rows':None,'tex':row},folder,font) for row in op['rows']], 'equals_asset':C.compile_asset({**op,'rows':None,'tex':'='},folder,font)}
  else:a=C.compile_asset(op,folder,font)
  assets[id(op)]=a
args=argparse.ArgumentParser();args.add_argument('--out',type=Path,default=WORK/'draft2');parsed=args.parse_args()
source=next((ROOT/'bundle/讲解课件').glob('*第1册*.pptx'));out=parsed.out;out.mkdir(exist_ok=True)
report=O.patch_volume(source,out/source.name,rules,assets)
(out/'qa_package.json').write_text(json.dumps([report],ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['output','output_sha256','changed_slides','total_slides']},ensure_ascii=False),flush=True)
