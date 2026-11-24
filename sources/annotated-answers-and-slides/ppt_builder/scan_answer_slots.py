"""Stable textual answer-slot scanner shared by extraction and slide authors.

These are candidates only. Symbolic variables and instructional examples must be
explicitly marked ignore by the reviewed metadata; never infer an answer here.
"""
import re,json
from pathlib import Path

SPACE=r'(?:[ \t\u3000~]|\\(?:quad|qquad|enspace|thinspace)\b|\\hspace\{[^}]*\})'
TOKEN=re.compile(
    r'（'+SPACE+r'*）|(?<!\\)\('+SPACE+r'*\)|'
    r'\\(?:bigcirc|square|Box)(?![A-Za-z])|[□○◯]|'
    r'(?<!\\)_{2,}|＿{2,}|\\underline\{'+SPACE+r'*\}'
)

def scan_slots(question_latex):
    out=[]
    for i,m in enumerate(TOKEN.finditer(question_latex)):
        token=m.group()
        kind='circle' if token in ['○','◯',r'\bigcirc'] else 'square' if token in ['□',r'\square',r'\Box'] else 'underline' if '_' in token or '＿' in token or token.startswith(r'\underline') else 'parentheses'
        out.append({'slot_index':i,'placeholder':token,'placeholder_kind':kind,'start':m.start(),'end':m.end(),'context':question_latex[max(0,m.start()-45):min(len(question_latex),m.end()+45)]})
    return out

if __name__=='__main__':
    root=Path(__file__).resolve().parent.parent
    records={}
    for f in sorted((root/'questions').glob('p[0-9][0-9][0-9].json')):
        for r in json.loads(f.read_text())['records']:
            slots=scan_slots(r.get('question_latex',''))
            if slots:records[r['key']]={'book_page':r['book_page'],'id':r['id'],'kind':r['kind'],'candidates':slots}
    p=root/'ppt_builder/answer_slot_candidates.json'
    p.write_text(json.dumps({'schema_version':1,'records':records},ensure_ascii=False,indent=2))
    print(json.dumps({'records':len(records),'candidate_slots':sum(len(r['candidates']) for r in records.values()),'path':str(p)}))
