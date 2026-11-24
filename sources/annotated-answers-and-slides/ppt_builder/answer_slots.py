"""Stable question-source blank enumeration and editable slot conversion."""
import copy,json,re,hashlib
from pathlib import Path

SPACE=r'(?:[ \t\u3000]|\\(?:qquad|quad|,|;| ))*'
TOKEN=re.compile(r'\\underline\{'+SPACE+r'\}|（'+SPACE+r'）|(?<!\\)\('+SPACE+r'\)|_{2,}|\\(?:square|bigcirc)(?![A-Za-z])|[□○◯]')
BASE=0xE000

def enumerate_slots(question):
    result=[]
    for i,m in enumerate(TOKEN.finditer(question)):
        p=m.group();kind='parentheses' if p.startswith(('（','(')) else 'square' if p in ('□',r'\square') else 'circle' if p in ('○','◯',r'\bigcirc') else 'underline'
        result.append({'slot_index':i,'placeholder':p,'kind':kind,'span':[m.start(),m.end()]})
    return result

def mark_question(question,provided,key):
    slots=enumerate_slots(question);issues=[];answers={x['slot_index']:x for x in (provided or {}).get('final_answers',[])}
    for i in answers:
        if i>=len(slots):issues.append({'severity':'error','code':'ANSWER_SLOT_INDEX','detail':f'{key} slot {i} exceeds {len(slots)} source slots'})
    result=question
    for slot in reversed(slots):
        i=slot['slot_index'];answer=answers.get(i);slot['mapped']=False
        if answer and answer.get('note'):slot['note']=answer['note']
        if answer and answer.get('expected_placeholder') not in (None,slot['placeholder']):
            issues.append({'severity':'error','code':'ANSWER_SLOT_PLACEHOLDER','detail':f'{key} slot {i}: expected {answer.get("expected_placeholder")!r}, source {slot["placeholder"]!r}'});continue
        if answer and answer.get('skip'):
            slot.update(skip=True,note=answer.get('note',''));continue
        if not answer or (answer.get('answer_latex') is None and answer.get('answer_text') is None):
            issues.append({'severity':'warning','code':'ANSWER_SLOT_UNMAPPED','detail':f'{key} slot {i} {slot["placeholder"]}: '+(answer or {}).get('note','no verified answer mapping')})
            if answer:
                slot.update(answer=answer,unresolved=True,marker=chr(BASE+i));a,b=slot['span'];result=result[:a]+slot['marker']+result[b:]
            continue
        slot.update(answer=answer,mapped=True,marker=chr(BASE+i));a,b=slot['span'];result=result[:a]+slot['marker']+result[b:]
    return result,slots,issues

SYMBOL_TEX={'×':r'\times ','÷':r'\div ','≤':r'\leq ','≥':r'\geq ','≠':r'\ne ','≈':r'\approx ','⊥':r'\perp ','∥':r'\parallel ','□':r'\square ','○':r'\bigcirc ','△':r'\triangle ','∠':r'\angle ','′':r'\prime ','π':r'\pi ','…':r'\ldots ','°':r'{}^\circ '}
def ast_tex(a,degree_context=False):
    t=a['t']
    if t=='text':
        out=''
        for c in a['v']:
            if c in SYMBOL_TEX:out+=(r'\circ ' if c=='°' and degree_context else SYMBOL_TEX[c])
            elif '\u4e00'<=c<='\u9fff':out+=r'\text{'+c+'}'
            elif c==' ':out+=r'\, '
            elif c in '%#&$':out+='\\'+c
            else:out+=c
        return out
    if t=='seq':return ''.join(ast_tex(x,degree_context) for x in a['items'])
    if t=='frac':return r'\frac{'+ast_tex(a['num'])+'}{'+ast_tex(a['den'])+'}'
    if t in ('sup','sub'):return '{'+ast_tex(a['base'])+'}'+('^' if t=='sup' else '_')+'{'+ast_tex(a['arg'],True)+'}'
    if t=='subsup':return '{'+ast_tex(a['base'])+'}_{'+ast_tex(a['sub'])+'}^{'+ast_tex(a['sup'],True)+'}'
    if t=='rad':return r'\sqrt'+('['+ast_tex(a['degree'])+']' if a.get('degree') else '')+'{'+ast_tex(a['base'])+'}'
    if t=='bar':return r'\underline{'+ast_tex(a['base'])+'}'
    raise ValueError('Slot math AST not supported: '+t)

def transform_blocks(blocks,slots,math_factory):
    active={s['marker']:s for s in slots if s.get('mapped') or s.get('unresolved')};issues=[]
    def slot_run(slot):
        a=slot['answer'];answer=({'type':'text','text':'？'} if slot.get('unresolved') else math_factory(a['answer_latex'],'answer',True) if a.get('answer_latex') is not None else {'type':'text','text':a['answer_text']})
        return {'type':'slot','slot_index':slot['slot_index'],'kind':slot['kind'],'placeholder':slot['placeholder'],'answer':answer,'reveal':False,'unresolved':slot.get('unresolved',False),'note':slot.get('note',''),'display_label':a.get('display_label','待核')}
    def math_split(ast):
        if ast['t']=='seq':
            out=[]
            for x in ast['items']:out+=math_split(x)
            return out
        if ast['t']=='text':
            parts=re.split('(['+''.join(active)+'])',ast['v']) if active else [ast['v']]
            return [active[x] if x in active else {'t':'text','v':x} for x in parts if x]
        if ast['t'] in ('sup','sub') and any(c in json.dumps(ast['base'],ensure_ascii=False) for c in active) and not any(c in json.dumps(ast['arg'],ensure_ascii=False) for c in active):
            return math_split(ast['base'])+[{**ast,'base':{'t':'seq','items':[]}}]
        if any(c in json.dumps(ast,ensure_ascii=False) for c in active):raise ValueError('Nested fraction/exponent slot needs explicit source mapping')
        return [ast]
    def expand(run):
        if run['type']=='text':
            parts=re.split('(['+''.join(active)+'])',run['text']) if active else [run['text']]
            return [slot_run(active[x]) if x in active else {'type':'text','text':x} for x in parts if x]
        if run['type']=='math' and any(c in json.dumps(run['ast'],ensure_ascii=False) for c in active):
            out=[];pending=[]
            def flush():
                if pending:out.append(math_factory(ast_tex({'t':'seq','items':pending.copy()}),'question',True));pending.clear()
            for item in math_split(run['ast']):
                if 'slot_index' in item:flush();out.append(slot_run(item))
                else:pending.append(item)
            flush();group='slot_formula_'+hashlib.sha256(run.get('latex',json.dumps(run['ast'],ensure_ascii=False)).encode()).hexdigest()[:12]
            for x in out:x['formula_group']=group
            return out
        return [run]
    for b in blocks:
        if b['role']!='question':continue
        if b['type']=='paragraph':b['runs']=[x for r in b['runs'] for x in expand(r)]
        elif b['type']=='math' and any(c in json.dumps(b['ast'],ensure_ascii=False) for c in active):
            runs=expand(b);b.clear();b.update(type='paragraph',runs=runs,role='question',phase='question')
    return blocks,issues

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--questions',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    records={}
    for path in sorted(a.questions.glob('p[0-9][0-9][0-9].json')):
        for r in json.loads(path.read_text())['records']:
            slots=enumerate_slots(r['question_latex'])
            if slots:records[r['key']]={'id':r['id'],'question_latex':r['question_latex'],'final_answers':[{'slot_index':s['slot_index'],'kind':s['kind'],'expected_placeholder':s['placeholder'],'answer_latex':None,'context':r['question_latex'][max(0,s['span'][0]-35):s['span'][1]+35]} for s in slots]}
    a.out.write_text(json.dumps({'schema_version':1,'records':records},ensure_ascii=False,indent=2));print(len(records),sum(len(r['final_answers']) for r in records.values()))
