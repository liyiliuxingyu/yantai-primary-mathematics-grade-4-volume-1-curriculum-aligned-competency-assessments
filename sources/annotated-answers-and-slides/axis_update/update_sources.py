from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent;P=R/'project';J=lambda p:json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
notes={
'p065_s05':'对称轴是直线。一般长方形有经过两组对边中点的2条对称轴；正方形再加上两条对角线所在的直线，共4条。等边三角形有分别经过顶点和对边中点的3条对称轴。',
'p070_s06':'对角线是线段，对称轴是直线，原句应判错。正确说法：正方形每条对角线所在的直线都是它的对称轴。',
'p070_s11':'“任意一条边上的高所在的直线”都要成为对称轴，说明三组对应边分别相等，因此是等边三角形。一般等腰三角形只有1条对称轴，不满足“任意一条边”的要求。',
'p085_s11':'对称轴是直线。正方形的4条对称轴是两条对角线所在的直线，以及两组对边中点连线所在的直线；等边三角形有3条，等腰梯形有经过两底中点的1条。'}
for L in'CD':
 f=P/f'detailed_layout/notes_{L}.json';d=J(f)
 for n in d['records']:
  if n['key']in notes:
   n['latex']=notes[n['key']];n['reason']+=' 本次严格区分线段与直线；对称轴表述补所在直线。'
   if n['key']=='p070_s06':
    assert not n.get('local_replacements')
    n['local_replacements']=[{'rect':[499.3,222.6,510.1,234.8],'latex':r'\(\times\)','font_size':10.5,'align':'center','valign':'center','clear_to_white':True,'kind':'judgment_correction','reason':'仅覆盖此题原红勾，不遮住两侧黑括号；对角线是线段，对称轴是直线，按原题严格判错。'}]
 save(f,d)
for pg in[65,70,85]:
 f=P/f'questions/p{pg:03}.json';d=J(f)
 for q in d['records']:
  if q['key']=='p070_s06':
   q['answer_latex']=r'\(\times\)。对角线是线段，对称轴是直线。正确说法：正方形每条对角线所在的直线都是它的对称轴。'
   q['verification']['reason']='严格区分对角线（线段）与对称轴（直线）；书后第九单元(B)二4原参考也是×。'
  elif q['key']=='p085_s11':
   q['answer_latex']=r'依次填\(4,3,1\)。正方形的4条对称轴是两条对角线所在的直线和两组对边中点连线所在的直线；等边三角形有3条；通常所说的等腰梯形有经过两底中点的1条。'
  elif q['key']=='p065_s05':
   q['answer_latex']='长方形有2条对称轴，都是经过一组对边中点的直线；有4条对称轴的常见四边形是正方形；三角形中有3条对称轴的是等边三角形。依次填2、正方、等边。'
  else:continue
  q['verification']['changes'].append('区分线段与直线，规范对称轴所在直线表述；p070_s06由√订正为×。'if q['key']=='p070_s06'else'规范对称轴的直线表述，条数不变。')
 save(f,d)
(R/'source_changes.json').write_text(json.dumps({'changed_note_keys':list(notes),'judgment_key':'p070_s06','strict_statement':'正方形每条对角线所在的直线都是它的对称轴。','judgment':'×','unchanged_symmetry_axis_counts':True},ensure_ascii=False,indent=2))
for name in['final_answers.json','final_answers_c.json']:
 f=P/'ppt_builder'/name;d=J(f);d['records']['p070_s06']['final_answers'][0]['answer_latex']=r'\times';save(f,d)
print('Four note texts and three question answers updated; one local mark added.')
