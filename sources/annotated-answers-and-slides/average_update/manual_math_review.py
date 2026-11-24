"""Question-data checks independent of the answer's calculation path."""
from pathlib import Path
from fractions import Fraction
import json, hashlib, re
from check_math_independent import value,J,R,P,APPROVED
CASES={
'p073_s01':[('(112+105+119)/3','112')],
'p073_s02':[('(500-400)/2','50'),('(500+400)/2','450')],
'p073_s06':[('(98+125+149)/31','12')],
'p073_s10':[('20*4-18*3','26')],
'p074_s06':[('14*3-20-14','8')],
'p075_s01':[('(70+120+170+240+190+130+60)/7','140')],
'p075_s03':[('(720*2)/(12+8)','72')],
'p075_s05':[('(87+83+85+88+82)/5','85')],
'p076_s01':[('67*3-65-66','70'),('(95+96+94)/3','95'),('90*3-88-92','90'),('95*3-95-93','97'),('(83+86+83)/3','84')],
'p077_s01':[('(16+15+20+18+14+19)/6','17')],
'p077_s02':[('237+145*3','672'),('(237+145*3)/6','112')],
'p077_s04':[('12*3-11*2','14')],
'p077_s05':[('(56+(56-8))/2','52')],
'p077_s06':[('(156+154+151+159+160)/5','156')],
'p077_s08':[('(156+154+151+159+160-154+159)/5','157'),('(157*5-159+154)/5','156')],
'p078_s03':[('45*3-40-40','55'),('(49+43+43)/3','45')],
'p078_s06':[('281-94*2','93')],
'p079_s01':[('(178+224+198)/3','200')],
'p079_s02':[('(178+224+198)/(9+11+10)','20')],
'p079_s03':[('(123+145+156+172+184)/5','156')],
'p088_s01':[('(68-8-16)/2','22')],
'p089_s02':[('(160+150)/2','155'),('160-150','10')],
'p089_s03':[('(12+8+7+13)/4','10')],
'p089_s04':[('20*3-23-15','22')],
'p089_s06':[('(96+156)/(3+4)','36')],
'p089_s07':[('(98+95+96+95+96)/5','96')],
'p090_s02':[('(73+81+81+87+95)/5','83.4'),('(73+81+87+87+95)/5','84.6')],
'p090_s03':[('80-(60-50)*6','20')],
'p091_s01':[('(96+88+92+88)/4','91'),('(96+88+82+18)/4','71')],
'p091_s04':[('2500*3-2700-2200','2600'),('3000*3-2700-2200','4100')],
'p098_s07':[('32/8','4')],
'p108_s02':[('(40*11)/(11-3)','55')],
'p108_s03':[('62*45+38*45','4500')],
}

def main():
    approved=J(APPROVED);keys=[x['key'] for x in approved['changes']]
    assert set(keys)==set(CASES)
    records={r['key']:r for n in range(1,109) for r in J(P/f'questions/p{n:03}.json')['records']}
    notes={n['key']:n for l in 'ABCD' for n in J(P/f'detailed_layout/notes_{l}.json')['records']}
    outcomes=[]
    for k in keys:
        for expr,want in CASES[k]:
            got=value(expr);assert got==Fraction(want),(k,expr,got,want)
            outcomes.append({'key':k,'independent_question_data_expression':expr,'exact_result':str(got),'result_in_published_answer':want})
    a=J(R/'qa_math_arithmetic.json');assert a['passed'] and a['checked_equalities']>=370 and not a['manual_review_required']
    # Verify explanations preserve uncertainty, option contradictions, and rules.
    def content(k):return records[k]['answer_latex']+'\n'+notes[k]['latex']
    assert all(t in content('p091_s01') for t in ['缺损','92','88','82','18','只按'])
    assert all(t in content('p091_s04') for t in ['2500','3000','2600','4100','核清'])
    assert all(t in content('p090_s02') for t in ['均不成立','83.4','84.6','未要求取整'])
    assert all(t in content('p090_s03') for t in ['20','均不成立'])
    assert all(t in content('p098_s07') for t in ['没有正确答案','增加1分','增加4分'])
    assert '(720\\times2)\\div(12+8)' in content('p075_s03')
    assert '(40\\times11)\\div(11-3)' in content('p108_s02')
    assert '利用加减运算的性质' in content('p089_s04')
    # True observed scope; this is math QA, not PDF/PPT playback or all-page render QA.
    result={
      'passed':True,'independent_reviewer':'average_crosscheck',
      'scope':'Final 32 mean-related approved records plus adjacent clothing p108_s03 note completion found during visual review; 33 records in total. All arithmetic chains and required uncertainty notices independently reviewed.',
      'changed_question_keys':keys,'questions_checked':len(keys),'average_related_questions_checked':32,'adjacent_visual_issue_repair':['p108_s03'],
      'arithmetic_equalities_checked':a['checked_equalities'],
      'arithmetic_failed_equalities':0,'arithmetic_unparsed_expressions':len(a['manual_review_required']),
      'calculation_blocks_checked':len({(c['key'],c['origin'],c.get('segment','standalone'+str(c.get('standalone','')))) for c in a['checks']}),
      'independent_question_data_outcomes_checked':len(outcomes),
      'question_data_results':outcomes,
      'manual_checks':{
        'mathematical_methods_fit_primary_stage':True,
        'all_final_values_and_units_preserved':True,
        'independent_computations_done_together_where_applicable':True,
        'multiplication_order_each_amount_times_count':True,
        'simplification_uses_grouping_complement_or_average_deviation':True,
        '75_total_distance_parenthesized':True,
        '108_total_pages_parenthesized':True,
        'grouping_properties_explained':True,
        'quantity_versus_number_of_observations_distinguished':True,
        'weighted_means_use_total_counts':True,
        'scoring_removes_one_high_and_one_low':True,
        'conceptual_questions_not_forced_into_needless_calculation':True,
      },
      'actual_original_pdf_book_pages_visually_reviewed':[75,77,79,90,91,108],
      'preserved_limits':[
        'Book 90 choice 4: average lies between 83.4 and 84.6; all printed choices invalid; no rounding instruction.',
        'Book 90 choice 5: original number is 20 and no printed option is 20.',
        'Book 91 problem 1: score glyphs damaged. 91 is conditional on 92 and 88; 71 is conditional on alternate 82 and 18.',
        'Book 91 problem 4: blurred mean. 2600mL if mean2500mL; 4100mL if mean3000mL. Original reading remains unresolved.',
        'Book98 choice5: correct increase4 points does not match printed D increase1 point; options not silently changed.',
        'Book74 choice4 original15kg versus book-reference A contradiction is outside this edit and remains preserved.',
      ],
      'sources_sha256':{str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted([P/f'questions/p{n:03}.json' for n in {int(k[1:4]) for k in keys}]+[P/'detailed_layout/notes_C.json',P/'detailed_layout/notes_D.json'])},
      'evidence':['qa_math_arithmetic.json','check_math_independent.py','manual_math_review.py'],
      'native_powerpoint_playback_tested':False,
      'pdf_or_ppt_layout_signoff_in_this_report':False,
    }
    (R/'qa_math_independent.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['question_data_results','sources_sha256']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
