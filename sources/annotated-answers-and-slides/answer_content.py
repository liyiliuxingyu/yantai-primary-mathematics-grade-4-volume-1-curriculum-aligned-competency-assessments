from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parent
OLD=ROOT/'recovered/source/new_work'

def load_pages():
    pages=[]
    oral_path=ROOT/'ppt_builder/oral_calculations.json'
    oral=json.loads(oral_path.read_text()).get('records',{}) if oral_path.exists() else {}
    for p in sorted(OLD.glob('side[1-6].json')):
        pages.extend(json.loads(p.read_text())['pages'])
    pages.sort(key=lambda p:p['source_page'])
    for page in pages:
        book=page['source_page']-4
        f=ROOT/'questions'/f'p{book:03}.json'
        if f.exists():
            records=json.loads(f.read_text())['records']
            for record in records:
                i=record['section_index']
                assert page['sections'][i]['id']==record['id'],(book,i,record['id'])
                if record.get('answer_latex'):
                    page['sections'][i]['latex']=record['answer_latex']
                if record.get('key') in oral and oral[record['key']].get('replace_answer'):
                    page['sections'][i]['latex']=oral[record['key']]['replacement_answer_latex']
                page['sections'][i]['record']=record
    assert [p['source_page'] for p in pages]==list(range(5,113))
    return pages

def aligned(content):
    def change(m):
        rows=m.group(2).split('\\\\')
        # A quantity equality is already a standalone conversion row. Keep its
        # left-hand quantity beside '=' instead of making a naked-number
        # calculation's separate opening row. Ordinary calculations below keep
        # the established left equals column and aligned first numbers.
        units=r'(?:平方厘米|平方分米|平方米|平方千米|厘米|毫米|分米|千米|千克|毫克|公顷|分钟|小时|吨|克|米|时|秒|分|元|角|万|亿)'
        for row in rows:
            if row.count('&')!=1:continue
            lhs,rhs=row.split('&',1)
            if not(lhs.strip()and re.match(r'^\s*=',rhs)):continue
            quantity_lhs=re.search(r'\\text\{[^}]*'+units+r'[^}]*\}',lhs)
            number_rewrite=re.fullmatch(r'\s*\d+(?:\.\d+)?\s*',lhs)and re.search(r'\\text\{[万亿]\}',rhs)
            if quantity_lhs or number_rewrite:return m.group(0)
        first=next((r for r in rows if r.strip()),'')
        if first.count('&')>1 and not first.lstrip().startswith('&'):return m.group(0)
        new=[]
        for row in rows:
            if row.count('&')==1:
                lhs,rhs=row.split('&',1)
                if lhs.strip() and re.match(r'^\s*=',rhs):
                    new.append('&'+lhs.strip())
                    row='={}&'+re.sub(r'^\s*=\s*','',rhs)
            # Canonical two-column display, idempotent for already-correct ={}& rows.
            row=re.sub(r'^\s*&?\s*=\s*(?:\{\})?\s*&\s*',r'={}&',row)
            if not re.match(r'^\s*=\{\}&',row):
                row=re.sub(r'^\s*&?\s*=\s*',r'={}&',row)
            if row.strip() and '&' not in row:row='&'+row
            new.append(row)
        rows=new
        return m.group(1)+'\\\\'.join(rows)+m.group(3)
    return re.sub(r'(\\begin\{aligned\}(?:\[t\])?)(.*?)(\\end\{aligned\})',change,content,flags=re.S)
