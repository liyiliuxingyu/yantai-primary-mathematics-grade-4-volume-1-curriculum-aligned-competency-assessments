from pathlib import Path
import sys,json,shutil,copy,argparse

W=Path(__file__).resolve().parents[1]
P=next((p/'project' if (p/'project/ppt_builder').is_dir() else p) for p in [W,*W.parents] if (p/'project/ppt_builder').is_dir() or (p/'ppt_builder').is_dir())
TASK=P.parent
sys.path.insert(0,str(P/'ppt_simplify/build'))
import patch_simplify as C
sys.path.insert(0,str(P/'simplify_update/ppt_1_2/build'))
import patch_owned as O
O.C=C

def math(name,tex=None,rect=None,rows=None):
 d={'type':'math','name':name,'points':32}
 if tex is not None:d['tex']=tex
 if rect is not None:d['rect']=rect
 if rows is not None:d['rows']=rows
 return d
def text(name,value,rect=None):
 d={'type':'text','name':name,'text':value,'points':32}
 if rect is not None:d['rect']=rect
 return d
def note(name,rect,title,explain,rows):
 return {'type':'note','name':name,'rect':rect,'title':title,'text':explain,
         'title_points':26,'note_points':24,'points':32,'rows':rows}

rules=[
 {'volume':2,'key':'p024_s03','slide':149,'ops':[
  note('p024_s03_b013_3',[650,120,560,360],'简便提示（学完运算律后）','两个30天先凑60，再加31天。',
       [r'30+31+30',r'(30+30)+31',r'60+31',r'91\text{(天)}']),
  text('p024_s03_b014_4_p0','答：2026年第2季度能卖728台空调。',[64,548,1152,64])]},
 {'volume':2,'key':'p025_s17','slide':192,'ops':[
  math('p025_s17_b003_4',r'6\times(8-1)',[106,418,1100,54]),
  math('p025_s17_b004_5',rows=[r'6\times7',r'42'],rect=[64,487,1152,116])]},
 {'volume':2,'key':'p030_s10','slide':310,'ops':[
  note('p030_s10_b005_0',[790,120,420,480],'面积简算','把39看成40少1。',
       [r'(15+24)\times32',r'39\times32',r'(40-1)\times32',r'40\times32-1\times32',r'1280-32',r'1248\text{(平方米)}'])]},
 {'volume':2,'key':'p031_s08','slide':333,'ops':[
  text('p031_s08_b003_2_p0','乘8再除8还原，两个5仍相乘。',[64,264.5,1152,58]),
  math('p031_s08_b004_3',r'(8\div8)\times(5\times5)',[106,337,1100,54]),
  math('p031_s08_b005_4',r'1\times25',[106,406,1100,54])]},
 {'volume':2,'key':'p032_s02','slide':352,'ops':[
  math('p032_s02_b008_3',r'(4\times25)\times12',[106,340,1100,54]),
  math('p032_s02_b009_4',rows=[r'100\times12',r'1200\text{(本)}'],rect=[64,409,1152,116]),
  text('p032_s02_b010_5_p0','答：一共采购了1200本图书。',[64,548,1152,64])]},
]
(W/'rules.json').write_text(json.dumps(rules,ensure_ascii=False,indent=2))
folder=W/'formulas';folder.mkdir(exist_ok=True)
font=P/'fonts/DroidSansFallback.ttf';assets={}
def compile_unique(op):
 a=C.compile_asset(op,folder,font)
 old=a['stem'];new='recheck20261105_'+old
 for key,ext in [('source','.tex'),('pdf','.pdf'),('svg','.svg'),('png','.png')]:
  target=folder/(new+ext);shutil.copy2(a[key],target);a[key]=target
 a['key']='recheck20261105_'+a['key'];a['stem']=new
 return a
for s in rules:
 for op in s['ops']:
  if op['type'] not in ('note','math'):continue
  if op.get('rows'):
   a={'row_assets':[compile_unique({**op,'rows':None,'tex':row}) for row in op['rows']],
      'equals_asset':compile_unique({**op,'rows':None,'tex':'='})}
  else:a=compile_unique(op)
  assets[id(op)]=a
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
out=args.out.resolve();out.mkdir(exist_ok=True)
source=args.source.resolve()
result=O.patch_volume(source,out/source.name,rules,assets)
(out/'qa_package.json').write_text(json.dumps([result],ensure_ascii=False,indent=2))
print(json.dumps({k:result[k] for k in ['output','output_sha256','total_slides','changed_slides']},ensure_ascii=False),flush=True)
