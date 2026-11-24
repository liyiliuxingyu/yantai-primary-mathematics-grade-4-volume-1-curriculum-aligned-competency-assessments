from pathlib import Path
import json,re,hashlib
R=Path(__file__).resolve().parent;P=R/'project'
J=lambda p:json.loads(p.read_text())
SHA=lambda s:hashlib.sha256(s.encode()).hexdigest()
fields=[];questions={};notes={}
for n in range(1,37):
 f=P/f'questions/p{n:03d}.json'
 for r in J(f)['records']:
  questions[r['key']]=r
  fields.append({'file':str(f.relative_to(P)),'key':r['key'],'field':'answer_latex','old':r.get('answer_latex','')})
for f in sorted((P/'detailed_layout').glob('notes_*.json')):
 for r in J(f)['records']:
  if not 1<=int(r['key'][1:4])<=36:continue
  notes[r['key']]=r
  fields.append({'file':str(f.relative_to(P)),'key':r['key'],'field':'latex','old':r.get('latex','')})
  for i,v in enumerate(r.get('local_replacements',[])):
   fields.append({'file':str(f.relative_to(P)),'key':r['key'],'field':f'local_replacements[{i}].latex','old':v.get('latex','')})
idx={(f['key'],f['field']):f for f in fields}
manual={};manual_spans={};conversions=[]
def eq(*rows):return r'\[\begin{aligned}&'+r'\\={}&'.join(rows)+r'\end{aligned}\]'
def replace(key,field,old,new,kind,reason):
 original=idx[(key,field)]['old'];current=manual.get((key,field),original)
 assert current.count(old)==1,(key,field,old,current.count(old))
 manual[(key,field)]=current.replace(old,new)
 manual_spans.setdefault((key,field),[]).append({'old':old,'new':new,'kind':kind,'reason':reason})
def register(key,kind,locations,reason):conversions.append({'key':key,'book_page':int(key[1:4]),'classification':kind,'locations':locations,'decision':'edit','reason':reason})
# Time representation, not elapsed-time arithmetic: keep original notation and move only the equivalence out of prose.
replace('p010_s02','answer_latex',r'\(21\)时就是晚上\(9\)时。',r'先换成钟面上的时刻：\[21\text{时}=\text{晚上}9\text{时}\]','clock_notation_conversion','21时与晚上9时是同一时刻，独立显示，不引入新的数值。')
replace('p010_s02','latex',r'先把二十四时计时法中的\(21\)时换成钟面上的晚上\(9\)时。',r'先换成钟面上的时刻：\[21\text{时}=\text{晚上}9\text{时}\]','clock_notation_conversion','时刻表示转换单独成行；不改角度计算、填空单位或原题。')
register('p010_s02','clock_notation_conversion',['answer_latex opening','notes_A latex opening'],'原有21时=晚上9时另行；这是计时法改写，单列记录，不能与时长单位混为一谈。')
# The road-width problem contains unit conversion embedded in the original numerical solution.
old=idx[('p016_s02','answer_latex')]['old']
new='先按“每秒\\(60\\)厘米、共\\(40\\)秒”求总长，再把厘米数换成米。\\[100\\text{厘米}=1\\text{米}\\]\\par\\noindent\\begin{minipage}{\\linewidth}\\textbf{方法一：先求厘米数，再换算}\\par '+eq('60\\times40','2400\\text{(厘米)}')+'\\[2400\\text{厘米}=(2400\\div100)\\text{米}=24\\text{米}\\]答：这条马路宽\\(24\\)米。\\end{minipage}\\par\\noindent\\begin{minipage}{\\linewidth}\\textbf{方法二：每十秒分为一段}\\par 先同时求每段的厘米数和段数：\\[60\\times10=600\\text{(厘米)},\\qquad40\\div10=4\\text{(段)}\\]\\[600\\text{厘米}=(600\\div100)\\text{米}=6\\text{米}\\]再用每段长度乘段数：'+eq('6\\times4','24\\text{(米)}')+'答：这条马路宽\\(24\\)米。\\end{minipage}\\par 每\\(10\\)秒走\\(6\\)米，\\(40\\)秒有这样的\\(4\\)段。\\par 用相同的速度单位检验，先把米换成厘米：\\[24\\text{米}=2400\\text{厘米}\\]'+eq('2400\\div40','60\\text{(厘米/秒)}')+'还原题目每秒\\(60\\)厘米的速度。'
manual[('p016_s02','answer_latex')]=new
manual_spans[('p016_s02','answer_latex')]=[{'old':old,'new':new,'kind':'conversion_calculation_separation','reason':'原主法60×40÷100与分组法、检验把数值计算和换算混为同一个脱式。分别保留厘米数计算、单列厘米=米换算行，再继续原计算；两项互相独立的600厘米和4段仍同时求出，不加新方法。'}]
old=idx[('p016_s02','latex')]['old']
new='沿最短路线走过的路程，正好等于马路的宽。原方法先求厘米总数，再单独换成米；换单位不能只改单位名称。另一种分组思路是把每\\(10\\)秒看成一段，先同时求每段的厘米数和段数：\\[60\\times10=600\\text{(厘米)},\\qquad40\\div10=4\\text{(段)}\\]\\[600\\text{厘米}=(600\\div100)\\text{米}=6\\text{米}\\]再用每段长度乘段数：'+eq('6\\times4','24\\text{(米)}')
manual[('p016_s02','latex')]=new
manual_spans[('p016_s02','latex')]=[{'old':old,'new':new,'kind':'conversion_calculation_separation','reason':'原题旁另法把厘米转米的÷100嵌在主脱式中。改为先同时求600厘米与4段，独立换600厘米=6米，再算6×4；原位主法由PDF编辑者同步拆出2400厘米=24米。'}]
register('p016_s02','physical_unit_conversion',[
 {'field':'answer_latex','location':'intro','equivalence':'100厘米=1米'},
 {'field':'answer_latex','location':'method1','equivalence':'2400厘米=(2400÷100)米=24米'},
 {'field':'answer_latex','location':'method2','equivalence':'600厘米=(600÷100)米=6米'},
 {'field':'answer_latex','location':'verification','equivalence':'24米=2400厘米'},
 {'field':'notes_A latex','location':'grouped method','equivalence':'600厘米=(600÷100)米=6米'}
],'实际长度单位换算；全部独立显示，换算行单位不套括号；数值计算结果仍用ASCII单位括号。')
# One kilometre to metres before speed/time division.
replace('p017_s06','answer_latex',r'先统一单位，\(1\)千米\(=1000\)米。',r'先统一长度单位：\[1\text{千米}=1000\text{米}\]','physical_unit_conversion','原行内千米=米改为独立数学行，后续1000÷100与填空数10保留。')
replace('p017_s06','latex',r'先把\(1\)千米换成\(1000\)米，才能与每分钟\(100\)米的速度使用同一种长度单位。',r'先统一长度单位：\[1\text{千米}=1000\text{米}\]这样才能与每分钟\(100\)米的速度使用同一种长度单位。','physical_unit_conversion','原口述单位换算改为独立数学行，原空只填10不重抄题目。')
register('p017_s06','physical_unit_conversion',['answer_latex opening','notes_A latex opening'],'1千米与1000米等值改写，必须先统一，换算行不加单位括号；实际求时长仍是计算，不剥掉结果单位括号。')
# Keep 半小时, avoid introducing decimals/fractions absent from this stage.
replace('p022_s02','answer_latex','半小时是30分钟，先求每分钟打字数，再乘30：',r'先统一时间单位：\[\text{半小时}=30\text{分钟}\]先求每分钟打字数，再乘30：','duration_unit_conversion','半小时转分钟独立行，保留原“半小时”，不新增0.5或1/2。')
replace('p022_s02','latex',r'先把半小时换成\(30\)分钟，使时间单位一致。',r'先统一时间单位：\[\text{半小时}=30\text{分钟}\]','duration_unit_conversion','换算单列，后续432÷6×30及时间倍数另法全部保留。')
register('p022_s02','duration_unit_conversion',['answer_latex','notes_A latex'],'半小时=30分钟独立行；不用新小数/分数表示。')
# Giraffe distance in kilometres before metres/min comparison.
replace('p022_s07','answer_latex',r'选\(A\)。统一为米/分：',r'选\(A\)。先把长颈鹿的路程换成米：\[3\text{千米}=3000\text{米}\]统一为米/分：','physical_unit_conversion','当前解答直接写3000÷3但缺少显式单位换算行；把已在题旁条件出现的3千米=3000米单列，不改数值或比较顺序。')
replace('p022_s07','latex',r'比较快慢应统一成相同的速度单位，题中多数已用“米/分”。长颈鹿的\(3\)千米先换成\(3000\)米，再除以\(3\)分钟；',r'比较快慢应统一成相同的速度单位，题中多数已用“米/分”。先换长颈鹿的路程：\[3\text{千米}=3000\text{米}\]再除以\(3\)分钟；','physical_unit_conversion','口述长度换算独立显示；不是把原已知表格数据改写，也不把所有动物的原单位重复抄一遍。')
register('p022_s07','physical_unit_conversion',['answer_latex before speed comparison','notes_A latex'],'长颈鹿的3千米先换3000米，才和其他米/分速度比较；换算行独立、单位不加括号。')
# Same time of day written in two clocks. Preserve existing hh:mm in the answer.
replace('p024_s01','answer_latex','下午1:00是13:00；',r'先把到达时刻改用二十四时计时法：\[\text{下午}1{:}00=13{:}00\]','clock_notation_conversion','仅将原时刻等值改写单列，不额外添12+1算式，不动后续13−9或分段验算。')
replace('p024_s01','latex',r'下午\(1\)时换成\(24\)时计时法是\(13\)时，',r'先把到达时刻改用二十四时计时法：\[\text{下午}1\text{时}=13\text{时}\]','clock_notation_conversion','原时刻改写单独成行；不同于换算小时和分钟，不添无必要公式。')
register('p024_s01','clock_notation_conversion',['answer_latex opening','notes_A latex opening'],'下午1时与13时改写单列，后续总用时四小时算法不变。')
# Exact whitelist from all parenthetical tokens encountered in these answer fields.
unit_tokens={'米/分','米','千克','件','元','袋','块','个','人','平方米','厘米/秒','元/千克','箱','元/盒','千米','分','千米/时','元/本','小时','秒','台','天','下','名','棵','页','本','厘米','元/条'}
patches=[];inventory=[];unit_counts={};unit_occurrences=0
for f in fields:
 key,path=f['key'],f['field'];old=f['old'];new=manual.get((key,path),old)
 unit_replacements=[]
 for token in sorted(unit_tokens):
  needle='（'+token+'）';count=old.count(needle)
  if count:
   unit_counts[token]=unit_counts.get(token,0)+count;unit_occurrences+=count
   unit_replacements.append({'old':needle,'new':'('+token+')','count':count,'kind':'calculation_result_unit_parenthesis_ascii','reason':'纯结果单位括号改用英文半角()，不是单位换算；普通中文备注、数学分组与原题括号不改。'})
  new=new.replace(needle,'('+token+')')
 # New units are already ASCII, and no target fullwidth unit may remain.
 assert not any('（'+t+'）'in new for t in unit_tokens)
 classification='conversion_or_clock_notation'if key in {c['key']for c in conversions}else('calculation_unit_parentheses_only'if unit_replacements else 'no_target_conversion_or_unit_parenthesis')
 inventory.append({'file':f['file'],'key':key,'field':path,'source_sha256':SHA(old),'classification':classification,'original_unit_parentheses':unit_replacements})
 if old!=new:
  patches.append({'file':f['file'],'key':key,'book_page':int(key[1:4]),'field':path,'old':old,'new':new,'old_sha256':SHA(old),'new_sha256':SHA(new),'conversion_replacements':manual_spans.get((key,path),[]),'unit_parenthesis_replacements':unit_replacements})
# Verify every non-unit Chinese parenthetical survives verbatim in each field.
nonunit_checks=0
for p in patches:
 for content in re.findall('（([^（）]+)）',p['old']):
  if content not in unit_tokens:
   assert p['new'].count('（'+content+'）')==p['old'].count('（'+content+'）'),(p['key'],content)
   nonunit_checks+=1
# Only proposal files are written. Canonical project is kept untouched.
review=[]
for key in questions:
 fs=[x for x in inventory if x['key']==key];unit=sum(len(x['original_unit_parentheses'])for x in fs)
 cs=[c for c in conversions if c['key']==key]
 review.append({'key':key,'fields_reviewed':[x['field']for x in fs],'conversion_classification':cs[0]['classification']if cs else 'none','requires_conversion_edit':bool(cs),'unit_format_fields':[x['field']for x in fs if x['original_unit_parentheses']],'unchanged_reason':None if cs or unit else '已检查全部解答/注释字段；没有实际单位换算或目标全角结果单位括号。'})
out={'scope':'原书1—36页当前327条题目解答与327条题旁注释及43个local答案字段；只审答案，不改原题/选项/已知表头/几何已知标签。','source_version_basis':'units_review/project，父agent从最新source16和full16恢复；无canonical编辑。','record_count':len(questions),'answer_fields_read':sum(x['field']=='answer_latex'for x in fields),'note_fields_read':sum(x['field']=='latex'for x in fields),'local_fields_read':sum(x['field'].startswith('local_replacements')for x in fields),'total_fields_read':len(fields),'conversions':conversions,'conversion_question_count':len(conversions),'physical_or_duration_conversion_question_count':sum(c['classification']!='clock_notation_conversion'for c in conversions),'clock_notation_question_count':sum(c['classification']=='clock_notation_conversion'for c in conversions),'patch_count_fields':len(patches),'patch_count_questions':len(set(x['key']for x in patches)),'original_fullwidth_unit_occurrences':unit_occurrences,'unit_occurrences_by_token':unit_counts,'ordinary_chinese_parenthetical_preservation_checks':nonunit_checks,'patches':patches,'field_inventory':inventory,'record_review':review,
 'checked_no_conversion_edit':[
  {'keys':['p004_s03','p004_s04'],'classification':'different_problem_count_unit','reason':'分别问袋数和块数是选择不同信息求不同量，不是把已求袋数按进率换成块数；不新增袋=块换算。结果单位括号仍按ASCII规范。'},
  {'keys':['p017_s05','p018_s06','p021_s04'],'classification':'unit_name_or_rate_notation','reason':'每小时千米数写成千米/时是同一速度单位的名称/读法，不是换到不同进率单位；不增添换算行。计算结果括号单独规范。'},
  {'keys':['p022_s06'],'classification':'elapsed_time_same_unit','reason':'12时43分到14时43分得2小时是同单位时刻求间隔，没有小时与分钟之间的换算，原解时间计算保留；速度结果单位括号改ASCII。'},
  {'keys':['p013_s06','p033_s07','p033_s08'],'classification':'known_same_length_unit','reason':'全为原图同一厘米单位；没有单位变换。原空已有单位时填数字，13页两空未预印单位时仍填5厘米，不重复整题。'},
  {'keys':['p035_s04','p035_s05','p035_s06'],'classification':'grid_interval_reading','reason':'按原图每格1厘米数格得到长度，属于给定比例的读图和作图，不是通常的米/厘米进率转换；不凭空添加格=厘米公式或新方法。'},
  {'keys':['p027_s09'],'classification':'numerical_rewrite_not_unit','reason':'把除数35化成70是商不变性质中的数值改写，没有单位，不受单位换算另行要求影响。'}],
 'omissions_justification':['1—36页未出现质量克/千克/吨互换、元角分换算、面积单位进率换算或万/亿单位改写的实际解答；含这些字样的同单位计算不误判为换算。','inline_layout slots_A/B仅是版面插入位置与题号索引，没有可编辑答案内容；原题空格及预印单位不改。','仅在精确白名单纯单位括号上改全角到ASCII；不处理（学完运算律后）、（乘法分配律）、（在下一页）等普通备注。','表格已知数据、题图已知标签不属于答案文字，本审不改；后续PDF应只替换红答案，避免误改黑题干的单位。'],
 'validation':{'source_untouched':True,'all_target_fullwidth_unit_parentheses_absent_in_proposals':True,'ordinary_chinese_parentheticals_preserved':True,'new_methods_added':False,'new_condition_numbers_added':False,'half_hour_not_rewritten_as_decimal_or_fraction':True,'numeric_conversion_checks':['100厘米=1米','2400厘米=24米','600厘米=6米','24米=2400厘米','1千米=1000米','半小时=30分钟','3千米=3000米','21时=晚上9时','下午1时=13时']}}
(R/'audit_001_036.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print({k:out[k]for k in ['record_count','total_fields_read','conversion_question_count','patch_count_fields','patch_count_questions','original_fullwidth_unit_occurrences']})
print('Conversion keys',[x['key']for x in conversions])
