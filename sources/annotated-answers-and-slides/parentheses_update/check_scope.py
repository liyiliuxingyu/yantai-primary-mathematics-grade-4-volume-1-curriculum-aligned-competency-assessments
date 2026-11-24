from pathlib import Path
import json,hashlib,zipfile,math
from fractions import Fraction
import fitz,numpy as np
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'parentheses_update';J=lambda p:json.loads(p.read_text());SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def W(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
zip_path=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip';changed_questions=[];changed_notes=[]
with zipfile.ZipFile(zip_path) as z:
 for f in sorted((P/'questions').glob('p[0-9][0-9][0-9].json')):
  old=json.loads(z.read('questions/'+f.name));new=J(f);assert len(old['records'])==len(new['records'])
  for a,b in zip(old['records'],new['records']):
   if a==b:continue
   assert a['key']==b['key']=='p075_s03';changed_questions.append(a['key'])
   assert {k:v for k,v in a.items() if k not in ['answer_latex','verification']}=={k:v for k,v in b.items() if k not in ['answer_latex','verification']}
   assert b['verification']['changes'][:len(a['verification']['changes'])]==a['verification']['changes']
 for L in 'ABCD':
  old=json.loads(z.read(f'detailed_layout/notes_{L}.json'));new=J(P/f'detailed_layout/notes_{L}.json')
  for a,b in zip(old['records'],new['records']):
   if a==b:continue
   assert a['key']==b['key']=='p075_s03';changed_notes.append(a['key'])
   assert {k:v for k,v in a.items() if k not in ['latex','reason','local_replacements']}=={k:v for k,v in b.items() if k not in ['latex','reason','local_replacements']}
 assert changed_questions==changed_notes==['p075_s03']
 oldindex=json.loads(z.read('detailed_layout/snippet_index.json'));newindex=J(Q/'compiled/snippet_index.json')
 assert len(oldindex)==len(newindex)==929
 assert {k for k in oldindex if oldindex[k]['body']!=newindex[k]['body']}=={'p075_s03','p075_s03_local1'}
old=fitz.open(R/'bundle/小学同步素养四年级上册数学答案.pdf');newpath=R/'deliverables/小学同步素养四年级上册数学答案.pdf';new=fitz.open(newpath);assert len(old)==len(new)==128
patch=J(Q/'patch_report.json');rel=J(P/'detailed_layout/current_release.json')
sr=fitz.Rect(patch['new_formula_rect']);band=next(b for b in rel['bands'] if b['book_page']==75 and sr in fitz.Rect(b['source_rect']));dy=band['target_rect'][1]-band['source_rect'][1]
allow=[fitz.Rect(patch['old_formula_rect'])+(0,dy,0,dy),sr+(0,dy,0,dy),fitz.Rect(patch['old_note_rect']),fitz.Rect(patch['new_note_rect'])];different=[]
for i in range(128):
 assert old[i].rect==new[i].rect
 a=old[i].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False);b=new[i].get_pixmap(matrix=fitz.Matrix(1,1),alpha=False)
 if a.samples!=b.samples:
  assert i==78,('another page changed',i+1)
  aa=np.frombuffer(a.samples,np.uint8).reshape(a.height,a.width,3);bb=np.frombuffer(b.samples,np.uint8).reshape(b.height,b.width,3);dif=(aa!=bb).any(2);mask=np.zeros((a.height,a.width),bool)
  for r in allow:
   r=r+(-2,-2,2,2);mask[max(0,math.floor(r.y0)):math.ceil(r.y1),max(0,math.floor(r.x0)):math.ceil(r.x1)]=True
  assert not (dif & ~mask).any(),'Changed pixels outside this question'
  different.append({'pdf_page':i+1,'changed_pixels':int(dif.sum()),'pixels_changed_outside_formula_and_note':0})
 if (i+1)%32==0:print('Checked PDF pages',i+1,flush=True)
assert len(different)==1 and not new[0].get_images() and not new[0].get_text() and not new[0].get_drawings()
values=[Fraction(720*2,12+8),Fraction(720*2,20),Fraction(720)*Fraction(2,2)/10,Fraction(720,10),Fraction(72)]
assert all(v==72 for v in values)
W(Q/'qa_scope.json',{'passed':True,'pdf_sha256':SHA(newpath),'pages':128,'changed_book_pages':[75],'changed_question_keys':['p075_s03'],'unchanged_pdf_pages':127,'other_questions_on_changed_page_pixels_identical':True,'changed_rectangles':[list(r) for r in allow],'comparison':different,'render_scale':1,'page_dimensions_unchanged':True,'first_page_blank':True,'separate_analysis_pages':0,'source_changed_question_keys':changed_questions,'source_changed_note_keys':changed_notes,'changed_compiled_bodies':['p075_s03','p075_s03_local1'],'compiled_snippets':929,'local_patches':73,'arithmetic_rows_exact':list(map(str,values)),'visual_review':'Actual view_image of p075_after.png confirms parentheses, equals alignment, clear spacing and intact neighboring questions. This does not claim a new full mathematics audit.'})
print('Only p075_s03 formula and note changed; all5 values72.',flush=True)
