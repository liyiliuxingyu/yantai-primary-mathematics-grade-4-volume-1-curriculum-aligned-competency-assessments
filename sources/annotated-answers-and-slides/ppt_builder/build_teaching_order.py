#!/usr/bin/env python3
"""Freeze presentation-only leading conclusion moves, preserving source math."""
import hashlib,json,re
from pathlib import Path
B=Path(__file__).resolve().parent
exceptions=json.loads((B/'qa/leading_conclusion_exceptions.json').read_text())
records={}
for page in sorted((B.parent/'questions').glob('p[0-9][0-9][0-9].json')):
    for r in json.loads(page.read_text())['records']:
        key=r['key'];answer=r['answer_latex'].strip()
        if key in exceptions['excluded_nonconclusions']:continue
        if not re.match(r'^(?:(?:依次)?选(?:择)?|(?:依次)?填(?:写)?|答案(?:为|是)|应填)',answer):continue
        if key in exceptions['records']:
            entry=exceptions['records'][key];prefix=entry['prefix_latex'];note=entry['reason']
        else:
            if '。' not in answer:raise ValueError('Unreviewed conclusion delimiter '+key)
            prefix=answer[:answer.index('。')+1];note='仅把已核首句结论移到解析、计算及图示之后。'
        if not answer.startswith(prefix):raise ValueError('Conclusion prefix no longer matches '+key)
        conclusion=prefix if prefix.endswith('。') else prefix.rstrip('，,：:；;')+'。'
        records[key]={'source_answer_sha256':hashlib.sha256(answer.encode()).hexdigest(),'prefix_latex':prefix,'conclusion_latex':conclusion,'reason':note}
out={'schema_version':1,'records':records,'scope':'Presentation-only order: read → analysis/calculation/diagram → conclusion → original-slot review. Original question and answer mathematical source are unchanged.','reviewed_candidates':252,'moved_conclusions':len(records),'excluded_nonconclusions':exceptions['excluded_nonconclusions'],'additional_exact_review':'p054_s04 依次选B,A首句由原尺寸最终QA及主程核准；其他依次选/应选/可选/正确答案/填入等前缀已全库扫查无额外匹配。'}
(B/'teaching_order.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(len(records))
