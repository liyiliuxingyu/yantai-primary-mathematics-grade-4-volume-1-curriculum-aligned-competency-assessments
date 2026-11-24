"""Independent exact arithmetic verification of the final average-answer patch."""
from pathlib import Path
from fractions import Fraction
import ast, json, re, hashlib
R=Path(__file__).resolve().parent
if (R/'project/questions').is_dir():
    P=R/'project';APPROVED=R/'approved_changes.json'
elif (R.parent/'questions').is_dir():
    P=R.parent;APPROVED=R/'change.json'
else:
    raise RuntimeError('Cannot locate current question source tree.')
def J(p):return json.loads(Path(p).read_text())
def remove_group_command(s,command):
    token='\\'+command
    while token in s:
        start=s.index(token);i=start+len(token)
        while i<len(s) and s[i].isspace():i+=1
        if i>=len(s) or s[i]!='{':break
        d=1;j=i+1
        while j<len(s) and d:
            if s[j]=='{':d+=1
            elif s[j]=='}':d-=1
            j+=1
        s=s[:start]+s[j:]
    return s

def norm(s):
    for c in ['text','textrm','mathrm','mbox']:
        s=remove_group_command(s,c)
    s=s.replace('\\left','').replace('\\right','')
    for c in ['bigl','bigr','Bigl','Bigr','big','Big','displaystyle','quad','qquad']:
        s=s.replace('\\'+c,'')
    s=s.replace('\\times','*').replace('\\div','/').replace('×','*').replace('÷','/')
    s=s.replace('−','-').replace('–','-').replace('＝','=')
    s=s.replace('\\,','').replace('\\;','').replace('\\!','').replace('~','')
    s=s.replace('\\(','').replace('\\)','').replace('\\[','').replace('\\]','')
    s=s.replace('&','').replace('{}','').replace('[','(').replace(']',')').replace('{','(').replace('}',')')
    return s.strip()

def value(s):
    s=norm(s)
    if not s or re.search(r'[^0-9+*/().\-\s]',s):raise ValueError(s)
    tree=ast.parse(s,mode='eval')
    def e(t):
        if isinstance(t,ast.Expression):return e(t.body)
        if isinstance(t,ast.Constant) and isinstance(t.value,(int,float)):return Fraction(str(t.value))
        if isinstance(t,ast.UnaryOp) and isinstance(t.op,(ast.UAdd,ast.USub)):
            return e(t.operand)*(1 if isinstance(t.op,ast.UAdd) else -1)
        if isinstance(t,ast.BinOp):
            a,b=e(t.left),e(t.right)
            if isinstance(t.op,ast.Add):return a+b
            if isinstance(t.op,ast.Sub):return a-b
            if isinstance(t.op,ast.Mult):return a*b
            if isinstance(t.op,ast.Div):return a/b
        raise ValueError(s)
    return e(tree)

def check_text(s,key,origin):
    checks=[];skips=[];fail=[]
    segments=re.findall(r'\\begin\{aligned\}(?:\[t\])?(.*?)\\end\{aligned\}',s,re.S)
    for seq,seg in enumerate(segments):
        rows=re.split(r'\\\\',seg);previous=None
        for ix,row in enumerate(rows):
            row=norm(row).strip()
            if not row:continue
            if row.startswith('='):
                expr=row.lstrip('=')
                try:v=value(expr)
                except Exception as ex:skips.append({'segment':seq,'row':ix,'expression':row,'reason':str(ex)});previous=None;continue
                if previous is not None:
                    proof={'key':key,'origin':origin,'segment':seq,'row':ix,'left':previous[0],'right':expr,'left_value':str(previous[1]),'right_value':str(v),'passed':previous[1]==v}
                    checks.append(proof)
                    if not proof['passed']:fail.append(proof)
                previous=(expr,v)
            else:
                parts=re.split(r'[，,;；]',row)
                if len(parts)>1:
                    previous=None
                    for part in parts:
                        if '=' not in part:continue
                        eq=part.split('=')
                        try:vs=[value(x) for x in eq]
                        except Exception:skips.append({'segment':seq,'row':ix,'expression':part});continue
                        for a,b,va,vb in zip(eq,eq[1:],vs,vs[1:]):
                            proof={'key':key,'origin':origin,'segment':seq,'row':ix,'left':a,'right':b,'left_value':str(va),'right_value':str(vb),'passed':va==vb};checks.append(proof)
                            if not proof['passed']:fail.append(proof)
                else:
                    if '=' in row:
                        eq=row.split('=')
                        try:vs=[value(x) for x in eq]
                        except Exception:skips.append({'segment':seq,'row':ix,'expression':row});previous=None;continue
                        for a,b,va,vb in zip(eq,eq[1:],vs,vs[1:]):
                            proof={'key':key,'origin':origin,'segment':seq,'row':ix,'left':a,'right':b,'left_value':str(va),'right_value':str(vb),'passed':va==vb};checks.append(proof)
                            if not proof['passed']:fail.append(proof)
                        previous=(eq[-1],vs[-1])
                    else:
                        try:previous=(row,value(row))
                        except Exception:skips.append({'segment':seq,'row':ix,'expression':row});previous=None
    # Standalone display or inline arithmetic equalities outside aligned blocks.
    standalone=re.findall(r'\\\((.*?)\\\)|\\\[(.*?)\\\]',s,re.S)
    for seq,pair in enumerate(standalone):
        raw=pair[0] or pair[1]
        if '\\begin{aligned}' in raw or '=' not in raw:continue
        expr=norm(raw)
        parts=expr.split('=')
        try:vs=[value(x) for x in parts]
        except Exception:skips.append({'standalone':seq,'expression':expr,'reason':'non-scalar expression; manual review'});continue
        for a,b,va,vb in zip(parts,parts[1:],vs,vs[1:]):
            proof={'key':key,'origin':origin,'standalone':seq,'left':a,'right':b,'left_value':str(va),'right_value':str(vb),'passed':va==vb};checks.append(proof)
            if not proof['passed']:fail.append(proof)
    return checks,skips,fail

def main():
    approved=J(APPROVED)
    changes=approved['changes'] if isinstance(approved,dict) else approved
    keys=[x if isinstance(x,str) else x['key'] for x in changes]
    records={r['key']:r for n in range(1,109) for r in J(P/f'questions/p{n:03}.json')['records']}
    notes={n['key']:n for l in 'ABCD' for n in J(P/f'detailed_layout/notes_{l}.json')['records']}
    checks=[];skips=[];failed=[]
    for key in keys:
        texts=[('answer',records[key]['answer_latex']),('note',notes[key]['latex'])]
        texts += [('local'+str(i+1),n['latex']) for i,n in enumerate(notes[key].get('local_replacements',[]))]
        for origin,s in texts:
            a,b,c=check_text(s,key,origin);checks.extend(a);skips.extend([{'key':key,'origin':origin,**v} for v in b]);failed.extend(c)
    out={'passed':not failed,'scope':'原书73—108页平均数题最终改动白名单的独立精确算术核验','changed_keys':keys,'exact_arithmetic':'fractions.Fraction over AST arithmetic; decimals parsed exactly','checked_equalities':len(checks),'failed_equalities':failed,'manual_review_required':skips,'checks':checks}
    (R/'qa_math_arithmetic.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='checks'},ensure_ascii=False,indent=2))
    assert not failed
if __name__=='__main__':main()
