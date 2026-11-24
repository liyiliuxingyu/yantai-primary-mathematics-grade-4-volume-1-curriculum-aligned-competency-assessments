from pathlib import Path
import json,re,ast
from fractions import Fraction
R=Path(__file__).resolve().parent;P=R/'project'
# Changes are confined to continuation rows in aligned answer formula blocks.
M={
'p003_s04':[(r'76\times(215-140)',r'76\times[215-140]')],
'p003_s05':[(r'(396\div11)\times58',r'[396\div11]\times58')],
'p003_s06':[(r'184\div(560\div70)',r'184\div[560\div70]')],
'p004_s02':[(r'9000-(30\times285+15\times15)',r'9000-[30\times285+15\times15]'),(r'9000-(8550+225)',r'9000-[8550+225]')],
'p007_s02':[(r'3744-38\times6',r'3744-[38\times6]')],
'p007_s03':[(r'25\times(672\div32)',r'25\times[672\div32]')],
'p007_s04':[(r'(275\div55)\times45',r'[275\div55]\times45')],
'p007_s05':[(r'73\times93-2876',r'[73\times93]-2876')],
'p007_s06':[(r'65\times(960\div12)',r'65\times[960\div12]')],
'p007_s07':[(r'336\div(252\div36)',r'336\div[252\div36]')],
'p008_s03':[(r'440\div(4\times5)',r'440\div[4\times5]'),(r'(440-440\div4\times3)\div5',r'[440-440\div4\times3]\div5'),(r'(440-110\times3)\div5',r'[440-110\times3]\div5'),(r'(440-330)\div5',r'[440-330]\div5')],
'p011_s06':[(r'1008\div(105\div5)',r'1008\div[105\div5]')],
'p015_s06':[(r'180\div(72\div4)',r'180\div[72\div4]')],
'p015_s07':[(r'34\times(160-45)',r'34\times[160-45]'),(r'34\times(160-60+15)',r'34\times[160-60+15]'),(r'34\times(100+15)',r'34\times[100+15]')],
'p015_s08':[(r'(288\div6)\times17',r'[288\div6]\times17')],
'p019_s12':[(r'80\times(200-131)',r'80\times[200-131]')],
'p042_s09':[(r'640\div(16\times5)',r'640\div[16\times5]')],
'p044_s02':[(r'5\times(24\div6)',r'5\times[24\div6]')],
'p044_s04':[(r'(275+500)\div25',r'[275+500]\div25')],
'p046_s09':[(r'45\times(240\div24)',r'45\times[240\div24]')]
}
fields=[];allkeys=[]
for n in range(1,61):
 f=P/f'questions/p{n:03d}.json';d=json.loads(f.read_text())
 for r in d['records']:
  allkeys.append(r['key']);fields.append((str(f.relative_to(P)),r['key'],'answer_latex',r.get('answer_latex','')))
for f in sorted((P/'detailed_layout').glob('notes_*.json')):
 for r in json.loads(f.read_text())['records']:
  if not 1<=int(r['key'][1:4])<=60:continue
  fields.append((str(f.relative_to(P)),r['key'],'latex',r.get('latex','')))
  for i,x in enumerate(r.get('local_replacements',[])):fields.append((str(f.relative_to(P)),r['key'],f'local_replacements[{i}].latex',x.get('latex','')))
patches=[];candidate_blocks=[];mathblocks=0;numeric=0

def value(expr):
 s=expr.replace(r'\times','*').replace(r'\div','/').replace('[','(').replace(']',')')
 def ev(n):
  if isinstance(n,ast.Constant):return Fraction(str(n.value))
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -ev(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=ev(n.left),ev(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  raise ValueError(ast.dump(n))
 return ev(ast.parse(s,mode='eval').body)
for filename,key,field,latex in fields:
 replacements=[]
 blocks=list(re.finditer(r'\\begin\{aligned\}(.*?)\\end\{aligned\}',latex,re.S));mathblocks+=len(blocks)
 for bi,b in enumerate(blocks):
  rows=b.group(1).split('\\\\')
  if '[' in b.group(1):candidate_blocks.append({'file':filename,'key':key,'field':field,'block_index_zero_based':bi,'rows':rows})
  for ri,row in enumerate(rows):
   if ri==0:continue # original formula is never changed
   for old,new in M.get(key,[]):
    if not row.endswith(old):continue
    prefix=row[:-len(old)]
    if re.fullmatch(r'[\s&={}]*',prefix) is None:continue
    oldrow=row;newrow=prefix+new
    assert value(old)==value(new),(key,old,new)
    numeric+=1
    replacements.append({'block_index_zero_based':bi,'row_index_zero_based':ri,'old':oldrow,'new':newrow,'old_expression':old,'new_expression':new,'reason':'原有外层中括号内仍有未完成运算，保留中括号至整组化为一个数；不改变原有运算与行数。'})
 if replacements:
  # Each exact row is uniquely identifiable in this formula field.
  for x in replacements:assert latex.count(x['old'])==1,(key,field,x['old'],latex.count(x['old']))
  patches.append({'file':filename,'key':key,'book_page':int(key[1:4]),'field':field,'replacements':replacements})
changed=set(x['key'] for x in patches)
out={
 'scope':'原书1—60页，所有当前questions answer_latex、detailed_layout notes latex及local_replacements latex，仅解答续行中外层中括号提前改小括号或去掉的情形。',
 'source_read_only':True,
 'question_records_reviewed':len(allkeys),
 'fields_reviewed':len(fields),
 'aligned_formula_blocks_reviewed':mathblocks,
 'math_square_bracket_aligned_blocks_reviewed':len(candidate_blocks),
 'changed_question_count':len(changed),
 'changed_keys':sorted(changed),
 'changed_field_count':len(patches),
 'replacement_row_count':sum(len(x['replacements']) for x in patches),
 'numeric_equivalence_checked_rows':numeric,
 'patches':patches,
 'candidate_formula_blocks':candidate_blocks,
 'no_change_examples':[
  {'key':'p023_s14','reason':'原式156÷[480÷(276−196)]，续行156÷[480÷80]已保留中括号，算成6后去掉正确。'},
  {'key':'p006_s05','reason':'B、D是题目给定选项及题意分析，非脱式续行；不得擅改题面选项160÷(900−520−360)。'},
  {'key':'p037_s08','reason':'TikZ的[scale]、[step]、[thick]、node[位置]是代码选项，不是数学中括号，不作修改。'},
  {'key':'p001_s04','reason':'答案只是按原分步结构合成综合算式，无续行中括号提前消失。'},
  {'key':'p045_s01','reason':'填空答案[200+(370−295)]÷5本身保留原分组，未给续行，不修改。'}
 ],
 'law_transformation_notes':[
  {'key':'p015_s07','reason':'减去一个差的性质改变中括号内部160−(60−15)为160−60+15，外层仍是34乘一个整体，故保留[160−60+15]与[100+15]；到乘法分配律展开为34×100+34×15时，该整体分组已被展开，不再强行保留[]。'},
  {'key':'p044_s04','reason':'[275+500]÷25依照和除以一个数的性质展开为275÷25+500÷25后，原整体分组已展开，不再强行保留[]。'}
 ],
 'unchanged_guarantees':['题干、原题第一行算式、题面中文提示均不修改。','所有建议只改变续行成对括号字符，不改数值、运算符、步骤数或方法。','每处新旧表达式已独立用Fraction精确计算确认数值相等。']
}
(R/'audit_1_60.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print({k:out[k] for k in ['question_records_reviewed','fields_reviewed','aligned_formula_blocks_reviewed','math_square_bracket_aligned_blocks_reviewed','changed_question_count','changed_field_count','replacement_row_count']})
print('keys',sorted(changed))
