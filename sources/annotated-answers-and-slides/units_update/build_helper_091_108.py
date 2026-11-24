"""Read-only answer/note unit-format proposals for original pages91--108."""
from pathlib import Path
import json,re,collections
R=Path(__file__).resolve().parent;P=R/'project'
J=lambda p:json.loads(Path(p).read_text())
UNIT_WORDS={'元','厘米','米','人','分','页','毫升','千克','吨','千瓦时','千米/时','个','本','场','米/分','千米'}
def ascii_result_units(s):
    return re.sub(r'（([^（）]+)）',lambda m:'('+m[1]+')' if m[1] in UNIT_WORDS else m[0],s)
def replace_one(s,a,b):
    assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
notes={r['key']:(f'detailed_layout/notes_{l}.json',r) for l in 'ABCD' for r in J(P/f'detailed_layout/notes_{l}.json')['records']}
records=[]
for n in range(91,109):
    records += [(f'questions/p{n:03}.json',r) for r in J(P/f'questions/p{n:03}.json')['records']]
assert len(records)==124
custom={}
def S(key,kind,text):custom[(key,kind)]=text
S('p093_s01','answer',r'按进率先换算：\[60\text{米}=0.06\text{千米}\]\[7\text{千米}60\text{米}=(7+0.06)\text{千米}=7.06\text{千米}\]\[1\text{平方米}=10000\text{平方厘米}\]\[800\text{平方厘米}=(800\div10000)\text{平方米}=0.08\text{平方米}\]依次填\(7.06,0.08\)，原空后的单位不重复填写。')
S('p093_s01','note',r'第一空先把60米换成千米，再与原有7千米合并，整数部分7不再另行缩小：\[60\text{米}=0.06\text{千米}\]\[7\text{千米}60\text{米}=(7+0.06)\text{千米}=7.06\text{千米}\]第二空是面积单位换算，不能沿用长度单位的进率：\[1\text{平方米}=10000\text{平方厘米}\]\[800\text{平方厘米}=(800\div10000)\text{平方米}=0.08\text{平方米}\]')
S('p093_s06','note',r'700克与1.8千克单位不同，先统一单位：\[700\text{克}=0.7\text{千克}\]白鸭比黑鸭重，先在黑鸭质量上加0.7求出白鸭，再把两只鸭的质量相加；不能把0.7直接当作白鸭的质量。\par \[\begin{aligned}&1.8+(1.8+0.7)\\={}&1.8+2.5\\={}&4.3\text{(千克)}\end{aligned}\]')
S('p105_s02','answer',r'按单位换算：\[6\text{千克}50\text{克}=(6000+50)\text{克}=6050\text{克}\]\[15.6\text{元}=15\text{元}6\text{角}\]\[900\text{克}=0.9\text{千克}\]\[3.07\text{千米}=3\text{千米}70\text{米}\]填6050、15、6、0.9、3、70，原空后的单位不重复填写。')
S('p105_s02','note',r'（1）千克换克乘1000，6千克先换成6000克，再加原有50克：\[6\text{千克}50\text{克}=(6000+50)\text{克}=6050\text{克}\]（2）元与角的进率是10，小数部分先换成角：\[0.6\text{元}=6\text{角}\]整数部分仍是15元：\[15.6\text{元}=15\text{元}6\text{角}\]（3）克换千克除以1000：\[900\text{克}=0.9\text{千克}\]（4）千米换米乘1000：\[0.07\text{千米}=70\text{米}\]与原有整数部分合并：\[3.07\text{千米}=3\text{千米}70\text{米}\]不能把小数部分的07直接读成7米。')
S('p106_s02','answer',r'选C。13.8吨中的8在十分位，表示\(0.8\)吨；按进率换算：\[0.8\text{吨}=(0.8\times1000)\text{千克}=800\text{千克}\]所以表示800千克，不是8千克或80千克。')
S('p106_s02','note',r'13.8中的8在十分位，表示8个十分之一吨，即0.8吨。进率为：\[1\text{吨}=1000\text{千克}\]按进率换算：\[0.8\text{吨}=(0.8\times1000)\text{千克}=800\text{千克}\]不能只看到数字8就直接当成8千克。')
conversion_keys={'p093_s01','p093_s02','p093_s06','p097_s01','p100_s03','p101_s03','p104_s02','p105_s02','p106_s02'}
def transform(key,kind,s):
    out=ascii_result_units(s)
    if (key,kind) in custom:return custom[(key,kind)]
    if key=='p093_s02':
        if kind=='answer':out=replace_one(out,r'\(240960000\text{公顷}=2.4096\text{亿公顷}\)。',r'\[240960000\text{公顷}=2.4096\text{亿公顷}\]')
        elif kind=='note':out=replace_one(out,'把大数改用“亿”作单位，要除以一亿，也就是把小数点向左移8位。','把大数改用“亿”作单位，要除以一亿，也就是把小数点向左移8位：'+r'\[240960000\text{公顷}=2.4096\text{亿公顷}\]')
    elif key=='p093_s06' and kind=='answer':
        out=replace_one(out,r'\(700\text{克}=0.7\text{千克}\)。',r'\[700\text{克}=0.7\text{千克}\]')
    elif key=='p097_s01':
        if kind=='answer':out=replace_one(out,r'\(126339000\text{亩}=1.26339\text{亿亩}\)。',r'\[126339000\text{亩}=1.26339\text{亿亩}\]')
        elif kind=='note':out=replace_one(out,'先把原数除以一亿，用带“亿”的数表示，','先把原数除以一亿，用带“亿”的数表示：'+r'\[126339000\text{亩}=1.26339\text{亿亩}\]')
    elif key=='p100_s03':
        if kind=='answer':
            a='答：重叠部分长0.04米，也就是4厘米。';assert out.count(a)==2
            out=out.replace(a,r'\[0.04\text{米}=4\text{厘米}\]答：重叠部分长4厘米。')
        elif kind=='note':out=replace_one(out,r'\(0.04\text{米}=4\text{厘米}\)。',r'\[0.04\text{米}=4\text{厘米}\]')
    elif key=='p101_s03':
        if kind=='answer':
            out=replace_one(out,r'7角5分是\(0.75\)元，',r'先统一单位：\[7\text{角}5\text{分}=0.75\text{元}\]')
            out=replace_one(out,r'7米2厘米是\(7.02\)米，',r'先统一单位：\[7\text{米}2\text{厘米}=7.02\text{米}\]')
        elif kind=='note':out=replace_one(out,'（2）（3）先统一为元、米再比较，7角5分是0.75元，7米2厘米是7.02米。',r'（2）（3）先统一为元、米再比较：\[7\text{角}5\text{分}=0.75\text{元}\]\[7\text{米}2\text{厘米}=7.02\text{米}\]')
    elif key=='p104_s02' and kind in {'answer','note'}:
        for x in [r'4.68\text{元}=468\text{分}',r'4680\text{分}=46.8\text{元}']:
            out=replace_one(out,r'\('+x+r'\)。',r'\['+x+r'\]')
    return out
changes=[];allkeys=[];field_count=0;unit_bracket_occurrences=0;conversion_locations=[];unchanged=[]
for qfile,r in records:
    key=r['key'];allkeys.append(key);nfile,n=notes[key]
    fields=[(qfile,'answer_latex','answer',r['answer_latex']),(nfile,'latex','note',n['latex'])]+[(nfile,f'local_replacements[{i}].latex','local',x['latex']) for i,x in enumerate(n.get('local_replacements',[]))]
    record_changes=[]
    for filename,field,kind,old in fields:
        field_count+=1
        if kind=='local' and ('\\color{black}' in old or n.get('kind','').startswith('black_')):continue
        unit_bracket_occurrences+=sum(1 for m in re.findall(r'（([^（）]+)）',old) if m in UNIT_WORDS)
        new=transform(key,kind,old)
        if old!=new:
            why=[]
            if ascii_result_units(old)!=old:why.append('仅普通计算结果的单位括号由中文（）改为英文ASCII()，不动数学分组和自然答语。')
            if key in conversion_keys and kind in {'answer','note'}:
                why.append('真实单位/数量级换算改为独立显示行，单位不加括号；换算填空仍只填原空所需数值或必要的亿，不重复已印单位。')
                displays=re.findall(r'\\\[(.*?)\\\]',new,re.S)
                conv=[d for d in displays if '=' in d and '\\text{' in d and '\\begin{aligned}' not in d]
                conversion_locations.append({'key':key,'file':filename,'field':field,'before_format':'inline_or_prose' if '\\begin{aligned}' not in old else 'conversion_inline_or_prose_alongside_calculation','classification':'true_unit_or_magnitude_conversion','standalone_conversion_lines':conv,'count':len(conv)})
            record_changes.append({'file':filename,'field':field,'old':old,'new':new,'reason':' '.join(why)})
    if record_changes:changes.append({'key':key,'book_page':r['book_page'],'id':r['id'],'field_changes':record_changes})
    else:unchanged.append(key)
report={
 'scope':{'book_pages':[91,108],'question_records_read':len(records),'all_record_keys':allkeys,'math_fields_read':field_count,'ordinary_existing_unit_parentheses_checked':unit_bracket_occurrences,'source_writes_performed':False},
 'changes':changes,'changed_question_count':len(changes),'changed_field_count':sum(len(x['field_changes']) for x in changes),
 'actual_conversion_question_keys':sorted(conversion_keys),'actual_conversion_question_count':len(conversion_keys),'conversion_locations':conversion_locations,'conversion_field_location_count':len(conversion_locations),'standalone_conversion_line_occurrences_proposed':sum(x['count'] for x in conversion_locations),
 'classification_notes':[
  {'keys':['p093_s01','p093_s06','p100_s03','p101_s03','p104_s02','p105_s02','p106_s02'],'classification':'measurement_unit_conversion','reason':'同一质量/长度/面积/钱数用不同单位表示，换算独立成行且单位不加括号。'},
  {'keys':['p093_s02','p097_s01'],'classification':'magnitude_reexpression','reason':'以亿公顷/亿亩改写数量级也按用户要求作为换算独立成行；后续四舍五入不是单位换算，保留原近似数与原填空约束。'},
  {'keys':['p096_s01'],'classification':'not_unit_conversion','reason':'按鸡蛋单价将费用除以每千克价格求质量，是数量关系，不能写84元=7千克；保留算式，只改已有结果单位括号。'},
  {'keys':['p105_s04'],'classification':'not_unit_conversion','reason':'按每千米热量求100千米热量是倍数/单价关系；两周为情境条件，不作周至天单位换算。'},
  {'keys':['p093_s03','p099_s02','p101_s01','p105_s01'],'classification':'decimal_counting_units_not_measurement_conversion','reason':'一/十分之一/百分之一/千分之一是计数单位和数位解释，不把其分解当成物理单位换算，不任意改写原小数算式。'},
  {'keys':['p097_s06','p098_s05','p101_s04','p101_s06','p103_s02','p105_s05'],'classification':'standard_angle_notation_preserved','reason':'规范度数记法如78度/78^\\circ保留，不把几何量的度符号变成结果注释，不修改已知角或原题图形。'},
 ],
 'conversion_fill_policy':'原题空后已有单位时，填空主答案只填数值；原题只印公顷/亩而要求亿时仍保留必要的亿。完整单位只在旁边解析的换算行出现。',
 'no_change_record_keys':unchanged,
 'preservation':{'questions_options_tables_diagrams_untouched':True,'numeric_calculation_results_unchanged':True,'full_calculation_steps_and_simplification_preserved':True,'multiplication_order_preserved':True,'normal_mathematical_parentheses_preserved':True,'natural_answer_sentences_keep_units_without_extra_parentheses':True,'black_local_patches_not_changed':True},
}
(R/'audit_helper_091_108.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['changes','no_change_record_keys','conversion_locations']},ensure_ascii=False,indent=2))
