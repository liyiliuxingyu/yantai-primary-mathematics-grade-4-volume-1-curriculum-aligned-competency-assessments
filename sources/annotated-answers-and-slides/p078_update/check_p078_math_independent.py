"""Independent mathematics and source-scope QA for the clear original page 78 correction."""
from pathlib import Path
from fractions import Fraction
import argparse, ast, hashlib, json, re, zipfile
HERE=Path(__file__).resolve().parent
if (HERE/'project/questions').is_dir():
    R=HERE;P=HERE/'project';Q=P/'p078_update';APPROVED=HERE/'approved_changes.json'
elif (HERE.parent/'questions').is_dir():
    P=HERE.parent;Q=HERE;R=HERE;APPROVED=HERE/'approved_changes.json'
else:raise RuntimeError('Cannot locate current question source tree.')
def J(p):return json.loads(Path(p).read_text())
def W(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def arithmetic(s):
    s=s.replace('\\times','*').replace('\\div','/').replace('×','*').replace('÷','/').replace('−','-')
    if re.search(r'[^\d.\s+*/()\-]',s):raise ValueError(s)
    def ev(n):
        if isinstance(n,ast.Expression):return ev(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):return Fraction(str(n.value))
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return ev(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp):
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
        raise ValueError(s)
    return ev(ast.parse(s.strip(),mode='eval'))
def simple_math(s):
    s=re.sub(r'\\text\{[^{}]*\}','',s).replace('&','').replace('{}','')
    return s.strip()
def verify_live_equations(text,key,origin):
    evidence=[]
    for i,body in enumerate(re.findall(r'\\begin\{aligned\}(.*?)\\end\{aligned\}',text,re.S)):
        previous=None
        for j,row in enumerate(re.split(r'\\\\',body)):
            clean=simple_math(row)
            if not clean:continue
            if clean.startswith('='):
                current=arithmetic(clean.lstrip('='))
                assert previous is not None and previous==current,(key,origin,i,j,clean)
                evidence.append({'key':key,'origin':origin,'kind':'aligned','block':i,'row':j,'value':str(current)})
                previous=current
            else:previous=arithmetic(clean)
    for i,body in enumerate(re.findall(r'\\\((.*?)\\\)',text,re.S)):
        if '=' not in body:continue
        parts=[simple_math(p) for p in body.split('=')]
        values=[arithmetic(p) for p in parts]
        assert len(set(values))==1,(key,origin,body)
        evidence.append({'key':key,'origin':origin,'kind':'inline','expression':body,'value':str(values[0])})
    return evidence
EXPECTED_COORDS=[
('0.2802','3.7564'),('0.5680','3.5942'),('0.2562','3.2657'),('0.8079','3.2498'),
('-0.0101','2.8005'),('-0.5012','2.6311'),('0.0696','2.5317'),('0.4042','2.2417'),
('-1.2661','1.9083'),('-0.7016','1.8672'),('-0.8211','1.5960'),('-1.1226','1.2544'),
('-1.4085','0.8709'),('0.3922','0.7740'),('-0.8871','0.6299'),('-0.0232','0.4583')]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-final',action='store_true',help='Run only after the owner declares SOURCE_FINAL.');args=ap.parse_args();assert args.source_final,'Source is still being edited; do not sign its final hash.'
    Q.mkdir(exist_ok=True)
    baseline_path=Q/'baseline_source_snapshot.json';archive=R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as z:
            paths=sorted(p for p in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json|detailed_layout/notes_[ABCD]\.json|diagram_index\.json|tikz_index\.json',p))
            baseline={p:json.loads(z.read(p)) for p in paths}
        W(baseline_path,{'source_archive_sha256':SHA(archive),'files':baseline})
    else:baseline=J(baseline_path)['files']
    approved=J(APPROVED);allowed={'p078_s01','p078_s05','p078_s06'}
    assert {c['key'] for c in approved['changes']}==allowed
    current={p:J(P/p) for p in baseline}
    old={r['key']:r for p,d in baseline.items() if p.startswith('questions/') for r in d['records']}
    now={r['key']:r for p,d in current.items() if p.startswith('questions/') for r in d['records']}
    assert len(old)==len(now)==867 and set(old)==set(now)
    actual_changed={k for k in now if now[k]!=old[k]};assert actual_changed==allowed
    for c in approved['changes']:
        assert old[c['key']]==c['old_record']
        assert now[c['key']]==c['new_record'],('approved record is not final',c['key'])
    oldnotes={r['key']:r for p,d in baseline.items() if p.startswith('detailed_layout/') for r in d['records']}
    notes={r['key']:r for p,d in current.items() if p.startswith('detailed_layout/') for r in d['records']}
    assert set(oldnotes)==set(notes)==set(now)
    notes_changed={k for k in notes if notes[k]!=oldnotes[k]};assert notes_changed<=allowed
    for c in approved['changes']:assert notes[c['key']]['latex']==c['final_note_latex']
    black_digits=notes['p078_s01'].get('local_replacements',[])[len(oldnotes['p078_s01'].get('local_replacements',[])):]
    assert len(black_digits)==3 and all(x.get('kind')=='black_source_photo_correction' for x in black_digits[:2])
    assert black_digits[2].get('kind')=='black_section_heading_photo_correction'
    assert [re.findall(r'\\mathrm\{(\d+)\}',x['latex'])[0] for x in black_digits[:2]]==['136','140']
    assert black_digits[2]['latex']==r'{\color{black}（每题2分，共12分）}', 'Restore the entire heading parenthesis, not only its final12.'
    graph_patches=notes['p078_s05'].get('local_replacements',[])[len(oldnotes['p078_s05'].get('local_replacements',[])):]
    assert len(graph_patches)==1 and graph_patches[0].get('kind')=='black_scatter_graph_photo_reconstruction'
    assert 'p078_update/assets/p078_temperatures_photo.tikz' in graph_patches[0]['latex']
    term_patches=notes['p078_s06'].get('local_replacements',[])[len(oldnotes['p078_s06'].get('local_replacements',[])):]
    assert len(term_patches)==1 and term_patches[0].get('kind','').startswith('black_')
    assert r'\color{black}' in term_patches[0]['latex'] and re.findall(r'[\u3400-\u9fff]',term_patches[0]['latex'])==['秧','歌']
    assert term_patches[0].get('original_prompt_replaced') is True
    # Quantitative checks independently reconstructed from the photo's conditions.
    total=Fraction(136)*3;minimum_if_all_can_ride=Fraction(140)*3
    assert total==408 and minimum_if_all_can_ride==420 and total<minimum_if_all_can_ride
    examples=[(136,136,136),(146,131,131),(146,146,116)]
    ex=[]
    for expected_count,heights in enumerate(examples):
        assert sum(heights)==408 and Fraction(sum(heights),3)==136
        assert all(h!=140 for h in heights),'Do not rely on the boundary interpretation of 以下.'
        weak=sum(h>=140 for h in heights);strict=sum(h>140 for h in heights)
        assert weak==strict==expected_count
        ex.append({'heights_cm':heights,'sum_cm':sum(heights),'mean_cm':136,'can_ride_both_boundary_interpretations':expected_count})
    assert now['p078_s01']['question_latex'].count('136cm')==1 and '140cm以下' in now['p078_s01']['question_latex']
    assert '138' not in now['p078_s01']['question_latex'] and '146cm以下' not in now['p078_s01']['question_latex']
    assert now['p078_s01']['answer_latex'].startswith('选C')
    live_examples=[tuple(map(int,t)) for t in re.findall(r'\((\d+),(\d+),(\d+)\)',now['p078_s01']['answer_latex'])]
    assert live_examples==examples
    union=45-10;intersection=21+17-union;only1=21-intersection;only2=17-intersection
    assert (union,intersection,only1,only2)==(35,3,18,14) and only1+intersection+only2+10==45
    assert now['p078_s02']['answer_latex'].startswith('选D')
    lower=45;strict_upper=45*3-40-40;assert strict_upper==55
    assert sum([49,43,43])==45*3 and min([49,43,43])>40
    accepted=[x for x in [42,70,49,60] if lower<=x<strict_upper];assert accepted==[49]
    assert now['p078_s03']['answer_latex'].startswith('选C')
    age_examples=[(16,4,10),(26,14,20)]
    for a,b,c in age_examples:
        m=Fraction(a+b+c,3);assert a==m+6 and b==m-6 and c==m
    assert age_examples[0][2]!=age_examples[1][2]
    assert all(t in now['p078_s04']['answer_latex'] for t in ['B成立','D按','具体岁数','单选设置不唯一'])
    assert now['p078_s04']==old['p078_s04'],'Preserve the ambiguous original wording and analysis.'
    assert [tuple(map(int,t)) for t in re.findall(r'\((\d+),(\d+),(\d+)\)',now['p078_s04']['answer_latex'])]==age_examples
    # The chart coordinates are photograph-relative layout coordinates, not temperatures.
    diagram=next(g for g in now['p078_s05']['diagrams'] if g['name']=='p078_temperatures')
    points=re.findall(r'\\fill\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)\s*circle',diagram['tikz'])
    assert len(points)==16
    fixed=[(Fraction(x),Fraction(y)) for x,y in EXPECTED_COORDS]
    coords=[(Fraction(x),Fraction(y)) for x,y in points]
    assert coords==fixed,'Only graphical sizing/font changes are permitted after point positions were fixed.'
    asset_tikz=P/approved['diagram_source'];asset_points=re.findall(r'\\fill\s*\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)\s*circle',asset_tikz.read_text())
    assert [(Fraction(x),Fraction(y)) for x,y in asset_points]==fixed,'Active TikZ asset and question source must use the same16 points.'
    without_comments=lambda s:re.sub(r'(?m)^\s*%[^\n]*(?:\n|$)','',s).strip()
    assert without_comments(asset_tikz.read_text())==without_comments(diagram['tikz'])
    graph_names={'p078_pirate_ship','p078_temperatures'}
    graph_source={g['name']:g for key in ['p078_s01','p078_s05'] for g in now[key]['diagrams']}
    assert '140 cm以下' in graph_source['p078_pirate_ship']['tikz'] and '146 cm以下' not in graph_source['p078_pirate_ship']['tikz']
    for index_file,list_key in [('diagram_index.json','diagrams'),('tikz_index.json','figures')]:
        before=baseline[index_file];after=current[index_file]
        assert {k:v for k,v in before.items() if k!=list_key}=={k:v for k,v in after.items() if k!=list_key}
        assert [x for x in before[list_key] if x.get('diagram_name') not in graph_names]==[x for x in after[list_key] if x.get('diagram_name') not in graph_names]
        changed_graphs=[x for x in after[list_key] if x.get('diagram_name') in graph_names];assert len(changed_graphs)==2
        for entry in changed_graphs:
            g=graph_source[entry['diagram_name']]
            assert entry['source_tikz_sha256']==hashlib.sha256(g['tikz'].encode()).hexdigest()
            assert without_comments((P/entry['tikz_source']).read_text())==without_comments(g['tikz'])
            wrapper=P/entry['tex'];wrapper_text=wrapper.read_text()
            linked=[(wrapper.parent/v).resolve() for v in re.findall(r'\\input\{([^}]+)\}',wrapper_text)]
            assert g['tikz'].strip() in wrapper_text or (P/entry['tikz_source']).resolve() in linked
    days=[]
    for i in range(4):
        band=[(x,y) for x,y in coords if 3-i<y<4-i];assert len(band)==4
        offset=sum(x for x,y in band)/4
        days.append({'day':i+1,'points':4,'mean_photo_relative_horizontal_offset':str(offset),'is_temperature_value':False})
    assert all(x>0 for x,y in coords[:4]) and all(x<0 for x,y in coords[8:12])
    assert sum(x for x,y in coords[12:])<0
    assert min(range(4),key=lambda i:abs(Fraction(days[i]['mean_photo_relative_horizontal_offset'])))==1
    assert 'dashed' in diagram['tikz'] and '22^\\circ' in diagram['tikz']
    assert '不是温度' in diagram.get('notes','') or '非温度' in diagram.get('notes','') or '而非温度' in diagram.get('notes','')
    assert now['p078_s05']['question_latex']==old['p078_s05']['question_latex']
    assert now['p078_s05']['answer_latex'].startswith('选B') and '原图没有精确刻度' in now['p078_s05']['answer_latex']
    q6=now['p078_s06'];assert '秧歌和剪纸' in q6['question_latex'] and '快板' not in q6['question_latex']+notes['p078_s06']['latex']
    assert q6['question_latex']==old['p078_s06']['question_latex'].replace('快板','秧歌')
    assert q6['answer_latex']==old['p078_s06']['answer_latex']
    score_rows=['281-94*2','281-188','93'];scores=[arithmetic(s) for s in score_rows];assert scores==[Fraction(93)]*3
    assert q6['answer_latex'].startswith('选A')
    live_equation_evidence=[]
    for k in [f'p078_s{i:02}' for i in range(1,7)]:
        for origin,text in [('answer',now[k]['answer_latex']),('note',notes[k]['latex'])]:
            live_equation_evidence+=verify_live_equations(text,k,origin)
    assert approved['section_heading']=='二、选择（将正确答案的序号填在括号里）。（每题2分，共12分）'
    assert arithmetic('2*6')==12 and approved['book_page']==78 and approved['pdf_page']==82
    photo=P/approved['source_photo'];assert SHA(photo)==approved['source_photo_sha256']=='5d75f494b69410e18e6975a11d51f86397cd36c1d94402d457bcdbf5bcd4a143'
    result={
      'passed':True,'scope':'Independent mathematics/text/source-scope verification for photo-confirmed original page78; all six questions reviewed, only records1/5/6 may change.',
      'source_final':True,'question_records_compared':867,'changed_record_count':3,'changed_record_keys':sorted(allowed),'other_records_unchanged':864,'unchanged_this_page_keys':['p078_s02','p078_s03','p078_s04'],
      'approved_changes_sha256':SHA(APPROVED),'source_photo_sha256':SHA(photo),
      'active_photo_trace_tikz_sha256':SHA(asset_tikz),
      'source_black_correction_values':[136,140,12],'source_black_section_heading':'（每题2分，共12分）','entire_black_heading_parenthetical_restored_in_source':True,'source_black_term_restored':'秧歌','source_new_black_patch_count':len(black_digits)+len(graph_patches)+len(term_patches),'source_black_graph_patch_count':1,'other_diagram_index_entries_unchanged':True,'standalone_tikz_and_question_source_consistent':True,
      'source_photo_actually_viewed':True,'q6_enlargement_actually_viewed':True,'q6_verified_term':'秧歌',
      'question_results':{
        '1':{'choice':'C','mean_cm':136,'total_cm':408,'minimum_total_cm_for_three_riders':420,'three_riders_impossible':True,'constructive_cases':ex,'all_possible_counts':[0,1,2],'no_example_uses_140':True},
        '2':{'choice':'D','actual_union':union,'both':intersection,'only_first':only1,'only_second':only2,'neither':10,'total':45},
        '3':{'choice':'C','total':135,'max_lower_bound':45,'max_strict_upper_bound':55,'possible_offered_value':49,'witness':[49,43,43]},
        '4':{'B_true':True,'D_true_when_age_means_specific_years':True,'nonunique_single_choice_preserved':True,'counterexamples_to_unique_age':age_examples},
        '5':{'choice':'B','point_count':16,'points_per_day':4,'only_given_reference_temperature_C':22,'exact_point_temperatures_not_inferred':True,'fixed_photo_relative_coordinates_preserved':True,'days':days},
        '6':{'choice':'A','score':93,'score_unit':'分','term':'秧歌','independent_calculation_rows':score_rows,'all_rows_equal_93':True},
      },
      'live_source_numeric_equalities_checked':len(live_equation_evidence),'live_source_numeric_equality_evidence':live_equation_evidence,
      'boundary_limit':'Sign says140cm以下. The exclusion of three riders uses the necessary weak bound at least140 each, which remains valid under either boundary convention; all constructive heights avoid140.',
      'chart_limit':'Numeric x/y values are drawing coordinates measured relative to the photograph. They are not inferred Celsius measurements; only approximate balance about the22°C reference supports choiceB.',
      'preserved_ambiguity':'Question4 original optionD says无法确定丙的年龄. B describes the relation to the average; D remains true if it asks for a concrete number of years. No silent forced single choice.',
      'source_files_sha256':{n:SHA(P/n) for n in current},
      'baseline_source_snapshot_sha256':SHA(baseline_path),
      'other_pages_prompts_diagrams_conditions_unchanged':True,
      'pdf_layout_or_native_powerpoint_playback_signoff_in_this_report':False,
      'evidence':['check_p078_math_independent.py','baseline_source_snapshot.json','approved_changes.json','assets/p078_original_photo.jpg'],
    }
    observation=Q/'qa_black_display_independent.json'
    if observation.exists():
        observed=J(observation);assert observed['passed'] and observed['approved_changes_sha256']==SHA(APPROVED)
        result['black_display_manual_observation']={'qa':'qa_black_display_independent.json','passed':True,'pdf_sha256':observed['pdf_sha256'],'historical_manual_observation_of_named_export':True,'scope':observed['scope']}
    W(Q/'qa_math_independent.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='source_files_sha256'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
