from pathlib import Path
import json
from decimal import Decimal as D
root=Path('/workspace/scratch/1facfb035d44/simplify_review')
project=root/'project'
records=[]
coverage=[]
for b in range(45,65):
    rr=json.loads((project/f'questions/p{b:03}.json').read_text())['records']
    records.extend(rr)
    coverage.append({'book_page':b,'pdf_page':b+4,'record_count':len(rr),'record_keys':[x['key'] for x in rr],'question_answer_notes_read':True})
notes={n['key']:n for letter in 'ABCD' for n in json.loads((project/f'detailed_layout/notes_{letter}.json').read_text())['records']}
bykey={r['key']:r for r in records}
changes=[]
def add(key,why,simple,note,answer,result,**extra):
    r=bykey[key]
    changes.append({'key':key,'book_page':r['book_page'],'id':r['id'],'why':why,'simple_latex':simple,'note_latex':note,'answer_latex':answer,'result':result,'original_answer_needs_replacement':False,'local_replacements':[],**extra})
add('p045_s07',
    '现notes主式先算300×8再乘5，未利用8和5凑40。按乘法结合律先算总工作40小时，使后一步成为乘整十数；原填空12000正确。',
    r'\[\begin{aligned}&300\times8\times5\\={}&300\times(8\times5)\\={}&300\times40\\={}&12000\text{（份）}\end{aligned}\]',
    r'每小时印300份，一天工作8小时，一周只算5个工作日。先按“每小时份数\(\times\)每天小时数\(\times\)工作天数”列式，再用乘法结合律，先把8与5相乘凑成整十数40，求出一周总工作时间：\[\begin{aligned}&300\times8\times5\\={}&300\times(8\times5)\\={}&300\times40\\={}&12000\text{（份）}\end{aligned}\]原空格后已有“份”，只填12000。',
    r'填\(12000\)。每小时300份，按“每份数\(\times\)份数”列式，用乘法结合律先求总工作时间：\[\begin{aligned}&300\times8\times5\\={}&300\times(8\times5)\\={}&300\times40\\={}&12000\text{（份）}\end{aligned}\]一周只算5个工作日。',
    '12000份',main_note_calculation_replaced=True,visual_evidence='page_045.png：906–996pt范围的notes中原来是300×8×5→2400×5→12000；没有额外A4红计算需掩盖。')
add('p046_s03',
    '原旁注只解释三个因数的数量含义，没有展示4×25凑100的适合简算。选择答案B保持不变，先按每窗4块的数量关系列式，再依法交换结合。',
    r'\[\begin{aligned}&4\times18\times25\\={}&(4\times25)\times18\\={}&100\times18\\={}&1800\text{（块）}\end{aligned}\]',
    r'每扇窗4块玻璃，每层18扇，共25层，按“每份数\(\times\)份数”先列\(4\times18\times25\)。选项B的\(25\times18\times4\)只是交换因数位置，积不变，所以选B。计算时用乘法交换律和结合律，把4与25凑成100：\[\begin{aligned}&4\times18\times25\\={}&(4\times25)\times18\\={}&100\times18\\={}&1800\text{（块）}\end{aligned}\]',
    r'选B。每扇4块，先求18扇一层的玻璃数，再求25层：\[\begin{aligned}&4\times18\times25\\={}&(4\times25)\times18\\={}&100\times18\\={}&1800\text{（块）}\end{aligned}\]选项\(25\times18\times4\)与此式由乘法交换律相等。',
    'B；1800块',main_note_calculation_replaced=False,visual_evidence='page_046.png：原位只有选择B，459–484pt旁注只有文字；补充这一个简算式，不改选项黑色原式。')
add('p048_s02',
    'PDF原位已是128+275+172=(128+172)+275=300+275=575，不应重复再加红式。仅canonical答案还把依次相加标为方法一，故同步为当前已有凑整主解，并把旁注措辞统一成优先简算。',
    r'\[\begin{aligned}&128+275+172\\={}&(128+172)+275\\={}&300+275\\={}&575\text{（人）}\end{aligned}\]',
    r'三个社团的报名人数全部相加。用加法交换律和结合律，先把128与172凑成300，再加275。交换、结合加数都不改变总人数。',
    r'把航模、编程、书法三个社团人数相加，用加法交换律和结合律先凑300：\[\begin{aligned}&128+275+172\\={}&(128+172)+275\\={}&300+275\\={}&575\text{（人）}\end{aligned}\]答：三个社团一共有575人报名。',
    '575人',main_note_calculation_replaced=False,base_formula_already_simple=True,do_not_add_simple_latex_again_to_pdf=True,visual_evidence='page_048.png：约350–409pt的原位红主解已经凑300；438–463pt旁注仅需措辞同步。')
add('p058_s07',
    '小雨用时17.8−0.9可把0.9凑1后补偿0.1。原选B正确，原旁注尚未写出这条简算；只在题旁补一组脱式，不另重复答案。',
    r'\[\begin{aligned}&17.8-0.9\\={}&17.8-1+0.1\\={}&16.8+0.1\\={}&16.9\text{（秒）}\end{aligned}\]',
    r'路程相同，“小明比小雨慢0.9秒”表示小明多用0.9秒，小雨应用17.8秒减0.9秒。把0.9凑成1，多减的0.1再加回：\[\begin{aligned}&17.8-0.9\\={}&17.8-1+0.1\\={}&16.8+0.1\\={}&16.9\text{（秒）}\end{aligned}\]因此选B。',
    r'选B。小明较慢，用时多0.9秒，小雨用时为：\[\begin{aligned}&17.8-0.9\\={}&17.8-1+0.1\\={}&16.8+0.1\\={}&16.9\text{（秒）}\end{aligned}\]',
    'B；16.9秒',main_note_calculation_replaced=False,visual_evidence='page_058.png：596–621pt原旁注只有数量关系，原位选择B；没有需要擦掉的旧红算式。')
add('p061_s03',
    '第一空7.8−2.81可拆2.81为2.8与0.01，先减2.8正好得5，再减0.01。原答案4.99及3.76均正确；第二空正常加法无特别易算结构，保持正常计算。',
    r'\[\begin{aligned}&7.8-2.81\\={}&7.8-2.8-0.01\\={}&5-0.01\\={}&4.99\end{aligned}\]',
    r'第一空以7.8为基准，“少2.81”用减法。把2.81拆成2.8与0.01，先减2.8可以凑成整数5：\[\begin{aligned}&7.8-2.81\\={}&7.8-2.8-0.01\\={}&5-0.01\\={}&4.99\end{aligned}\]第二空以2.36为基准，“多1.4”用加法，\(2.36+1.4=3.76\)。两空的基准不同，不能共用一个原数。',
    r'两空依次填\(4.99\)、\(3.76\)。第一空简算：\[\begin{aligned}&7.8-2.81\\={}&7.8-2.8-0.01\\={}&5-0.01\\={}&4.99\end{aligned}\]第二空\(2.36+1.4=3.76\)。',
    '4.99；3.76',main_note_calculation_replaced=False,visual_evidence='page_061.png：477–502pt原旁注只有数位对齐说明，原空格4.99、3.76保留。')
add('p063_s07',
    '米制主解原按2−0.16−0.54顺次退位；可利用连减性质先把0.16和0.54凑0.7，再由2一次减去。厘米制原有200−(16+54)=130已经简便，保留作统一单位的另一写法，不重复增加算法。',
    r'\[\begin{aligned}&2-0.16-0.54\\={}&2-(0.16+0.54)\\={}&2-0.7\\={}&1.3\text{（米）}\end{aligned}\]',
    r'竹竿总长由入泥、水中、露出三段组成，水深只对应水中的一段。先统一单位：\(16\text{厘米}=0.16\text{米}\)，\(54\text{厘米}=0.54\text{米}\)。用米计算时，按连减性质先合并水深以外两段，0.16与0.54正好凑成0.7：\[\begin{aligned}&2-0.16-0.54\\={}&2-(0.16+0.54)\\={}&2-0.7\\={}&1.3\text{（米）}\end{aligned}\]也可统一成厘米，\(2\text{米}=200\text{厘米}\)，同样先合并两段：\[\begin{aligned}&200-(16+54)\\={}&200-70\\={}&130\text{（厘米）}\end{aligned}\]\(130\text{厘米}=1.3\text{米}\)。两种单位写法的数量关系相同。答：水池的水深是1.3米。',
    r'竹竿总长减入泥和露出两段，才是水深。统一成米，利用连减性质先凑0.7：\[\begin{aligned}&2-0.16-0.54\\={}&2-(0.16+0.54)\\={}&2-0.7\\={}&1.3\text{（米）}\end{aligned}\]也可统一成厘米：\[\begin{aligned}&200-(16+54)\\={}&200-70\\={}&130\text{（厘米）}\end{aligned}\]\(130\text{厘米}=1.3\text{米}\)。答：水池的水深是1.3米。',
    '1.3米',main_note_calculation_replaced=True,visual_evidence='page_063.png：872–1078pt整块notes含全部旧米制及厘米制计算，直接换notes即可；题干后没有独立A4原位红主解。')
# Independent numeric checks of every changed numeric result.
assert 300*8*5==300*(8*5)==12000
assert 4*18*25==(4*25)*18==1800
assert 128+275+172==(128+172)+275==575
assert D('17.8')-D('.9')==D('17.8')-1+D('.1')==D('16.9')
assert D('7.8')-D('2.81')==D('7.8')-D('2.8')-D('.01')==D('4.99')
assert D('2.36')+D('1.4')==D('3.76')
assert 2-D('.16')-D('.54')==2-(D('.16')+D('.54'))==D('1.3')
assert 200-(16+54)==130
assert sum(c['record_count'] for c in coverage)==158
out={
 'scope':{'first_book_page':45,'last_book_page':64,'page_count':20,'record_count':158,'all_records_questions_answers_notes_read':True,'pdf_source':'bundle/小学同步素养四年级上册数学答案.pdf','pdf_page_rule':'印刷书页+4；例如书45页=PDF第49页','independent_result_recheck':'6项所涉数值使用整数或Decimal独立验算通过','visual_check_scope':{'rendered_and_opened_book_pages':[45,46,48,58,61,63],'actual_all_20_pages_visual_review':False},'original_answer_needs_replacement_definition':'仅指需在原A4题面/原位红式区域清除替换；当前6项均无需此局部操作。notes内主计算被改的项单独以main_note_calculation_replaced记录。'},
 'coverage':coverage,
 'changes':changes,
 'change_count':len(changes),
 'already_adequate_examples':[
  {'key':'p045_s02','reason':'48×96=48×(100−4)已用分配律。'},
  {'key':'p046_s10','reason':'136×101−136=136×(101−1)已提取共同因数。'},
  {'key':'p046_s11','reason':'125×48已有8×6凑1000和50−2分配两条适合简算。'},
  {'key':'p048_s02','reason':'PDF原位已先128+172凑300，本次仅canonical和旁注措辞同步。'},
  {'key':'p052_s03','reason':'40×30及18×5先得到1200和90，后续1200×90易算；改配40×5并无明确额外收益，不为凑数改动。'},
  {'key':'p056_s01','reason':'3750÷(20×5)已先凑除数100；另一数量顺序不重复新列同一律。'},
  {'key':'p057_s13','reason':'1.08+5.99的比较已用接近6作补偿/估界。'},
  {'key':'p058_s06','reason':'76.54+9.99的选项与注解已明确+10−0.01。'},
  {'key':'p059_s01','reason':'52.46−(8.3+12.46)已先减12.46凑40。'},
  {'key':'p059_s02','reason':'86.72−10.1已用−10−0.1。'},
  {'key':'p059_s03','reason':'250−25.62−74.38已把两减数凑100。'},
  {'key':'p059_s04','reason':'6.9+1.3−6.9+1.3已先抵消同一加减项。'},
  {'key':'p059_s05','reason':'现有另算596.5−426+0.2已经给出补偿，不能重复再增加同式。'},
  {'key':'p059_s07','reason':'现有186.5−100+7.2已经是减92.8的补偿写法。'},
  {'key':'p060_s03','reason':'49.8+26.35已有先50+26.35再减0.2。'},
  {'key':'p060_s04','reason':'26.35+13.65已先凑40；两种数量思路均完整。'},
  {'key':'p063_s02','reason':'35−3.7+6.3现按保留符号先求6.3−3.7，未错误凑为3.7+6.3；这里没有应硬称凑整的两数。'},
  {'key':'p063_s03','reason':'27−9.98已减10再加0.02。'},
  {'key':'p063_s04','reason':'45.35−(7.2+5.35)已先减5.35凑40。'},
  {'key':'p063_s05','reason':'23.8与36.2凑60，3.9与5.1凑9，两组独立计算同一步完成。'},
  {'key':'p063_s06','reason':'已有9+20−0.5补偿计算，不重复再添加；直接加法与补偿只是同一数量关系的不同算法，不能据此声称两种独立解题思路。'}
 ],
 'not_forced':[
  '明确要求竖式计算的p058_s09、p063_s01保留竖式，不能以简算法代替指定任务。',
  '填空、比较、数位/单位判断不为展示运算律硬凑长公式。',
  '一般小数乘除尚未学，不引入；乘除10、100、1000按小数点移动处理。',
  '普通两数加减无明显凑整收益时保留直接算法，不把答案为整数当作简便判据。',
  '图形/海拔资料现有争议不在本次数学简算校改范围，未擅改题意；开放规则未把一例称为穷尽。'
 ]
}
(root/'audit_45_64.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(root/'audit_45_64.json');print('pages',len(coverage),'records',sum(c['record_count'] for c in coverage),'changes',len(changes))
