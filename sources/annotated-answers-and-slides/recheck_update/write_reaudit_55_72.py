from pathlib import Path
import json,hashlib
P=Path('p74_review/project');R=Path('p74_review')
notes={}
for L in 'BCD':notes.update({r['key']:r for r in json.load(open(P/f'detailed_layout/notes_{L}.json'))['records']})
records={};coverage=[]
for n in range(55,73):
 d=json.load(open(P/f'questions/p{n:03}.json'));coverage.append({'book_page':n,'record_count':len(d['records']),'checked_keys':[r['key'] for r in d['records']]});records.update({r['key']:r for r in d['records']})
accepted=json.load(open(P/'simplify_update/accepted_changes.json'));oldset={x['key'] for x in accepted['changes']}
changes=[]
k='p056_s01';r=records[k];n=notes[k]
old=r'\[\begin{aligned}&3750\div5\div20\\={}&750\div(2\times10)\\={}&750\div2\div10\\={}&375\div10\\={}&37.5\text{（千克）}\end{aligned}\]'
new=r'\[\begin{aligned}&3750\div5\div20\\={}&3750\div(5\times20)\\={}&3750\div100\\={}&37.5\text{（千克）}\end{aligned}\]'
assert old in r['answer_latex'] and old in n['latex']
answer=r['answer_latex'].replace('方法二：先求每辆车运的质量，再除以每车20件。把除数20分解成2与10的积，再用“除以一个积，等于依次除以两个因数”的性质，最后按除以10时的小数点移动规律计算。','方法二：先分车再分件的数量分析仍然成立；计算时用连续除法的性质，把5与20先凑成100，直接除以100。').replace(old,new)
note=n['latex'].replace('方法二，分两次平均分：先求每辆车运多少千克，再除以每车20件。除以20可拆成先除以2、再除以10，最后用小数点移动计算：','方法二，仍按先分给5辆车、再按每车20件平均分来分析。计算时连续除以5和20，等于一次除以它们的积；5与20先凑成100，可直接用小数点移动规律计算：').replace(old,new)
changes.append({'key':k,'book_page':56,'id':r['id'],'why':'另法仍先求750再把20拆成2×10；改用连除性质，先将两个除数5与20凑100，少做两步且避免750÷20的临时分解。主法的总件数100与两种数量分析不变。','simple_latex':new,'new_answer_latex':answer,'new_note_latex':note,'original_answer_needs_replacement':False,'primary_method_already_simple':True,'only_existing_alternative_formula_changed':True,'quantity_methods_preserved':True,'result':'37.5千克；375000千克','exact_equivalence_checked':True,'grade_scope':'整数连除性质与除以100的小数点移动，不用一般小数除法。','recommendation':'adopt'})
k='p057_s03';r=records[k]
f=r'\[\begin{aligned}&36.8+5.9\\={}&36.8+6-0.1\\={}&42.8-0.1\\={}&42.7\end{aligned}\]'
changes.append({'key':k,'book_page':57,'id':r['id'],'why':'5.9接近整十计数单位6，先加6再减多加的0.1，可避免原式十分位进位；这是补偿凑整，不以42.7是否为整数作标准。','simple_latex':f,'new_answer_latex':'另一个加数不变，一个加数增加5.9，和也增加5.9。把5.9凑成6，多加的0.1再减回：'+f+'填42.7。','new_note_latex':'一个加数增加5.9，另一个不变，原和应增加一次5.9，不用分别求两个加数。把5.9凑成6，先加整数，再减去多加的0.1：'+f,'original_answer_needs_replacement':False,'result':'42.7','exact_equivalence_checked':True,'grade_scope':'小数加法与凑整补偿。','recommendation':'adopt'})
k='p058_s02';r=records[k]
f=r'\[\begin{aligned}&30-9.5\\={}&30-10+0.5\\={}&20+0.5\\={}&20.5\end{aligned}\]'
changes.append({'key':k,'book_page':58,'id':r['id'],'why':'减数9.5与10只差0.5，先减整十数再补回0.5，免去整数减小数的借位。','simple_latex':f,'new_answer_latex':'一个加数等于和减另一个加数。把9.5凑成10，多减的0.5再加回：'+f+'所以选C。','new_note_latex':'所求数与9.5相加组成30，应由和减去已知加数。把9.5凑成10，先减整数，再补回多减的0.5：'+f+r'填回检验：\(20.5+9.5=30\)，所以选C。','original_answer_needs_replacement':False,'result':'20.5；选C','exact_equivalence_checked':True,'grade_scope':'加减互逆与小数凑整补偿。','recommendation':'adopt'})
assert not ({x['key'] for x in changes}&oldset)
# Exact independent rational arithmetic.
from fractions import Fraction as F
assert F(3750)/5/20==F(3750)/(5*20)==F('37.5')
assert F('36.8')+F('5.9')==F('36.8')+6-F('.1')==F('42.7')
assert 30-F('9.5')==30-10+F('.5')==F('20.5')
report={'scope':'Read-only simplification recheck of current canonical questions, answers and in-question notes, original book pages55–72. No source/PDF was changed.','coverage':coverage,'record_count':len(records),'covered_pages':list(range(55,73)),'covered_keys':list(records),'changes':changes,'change_count':len(changes),'old_56_revision_keys_in_range':sorted(k for k in oldset if 55<=int(k[1:4])<=72),'unchanged_reason_samples':[{'keys':['p057_s13','p061_s06','p061_s07','p061_s08','p062_s05','p062_s08'],'reason':'旁注已使用凑整、同增同减或比较结构，判断题不必再把两边完整重算，避免重复列式。'},{'keys':['p059_s01','p059_s02','p059_s03','p059_s04','p063_s03','p063_s04','p063_s05'],'reason':'标能简便的各式已经实际用运算律/补偿或抵消，保留。'},{'keys':['p059_s05','p059_s07','p060_s03','p063_s06'],'reason':'已提供补偿凑整途径；不把同一数量关系的换写再增加为新解法。'},{'keys':['p060_s01','p060_s02','p061_s11','p064_s01','p064_s02','p064_s03','p064_s04'],'reason':'没有遗漏明显更省算的凑整结构，已有不同数量分析或相同数先合并的合理方法；不为了形式变化强行重排。'},{'book_pages':list(range(65,73)),'reason':'几何运动、轴对称内容为主，出现的格数、钟面角度及单位换算均是直接易算结构；本轮不改几何结论或图形。'}],'checks':{'all_records_and_current_notes_read':True,'all_candidate_intermediate_equalities_exactly_checked':True,'new_candidates_disjoint_from_prior56':True,'result_integer_not_a_simplification_criterion':True,'geometry_unchanged':True},'visual_scope':'本分审以当前题源和notes全文核读为主，没有宣称重新人工查看55–72全部PDF页；候选改的是旁注，原空/选项结果不变。'}
(R/'reaudit_55_72_sub.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(len(records),'records',len(changes),'new candidates')
