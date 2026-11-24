#!/usr/bin/env python3
"""Normalize reviewed pNNN.json files. No artifact is authored by this command.

Unknown TeX and missing diagrams are reported rather than replaced with scans.
"""
from __future__ import annotations
import argparse, collections, copy, hashlib, json, math, re, time
from pathlib import Path
from answer_slots import mark_question,transform_blocks

SYMBOLS = {
    'times':'×','div':'÷','circ':'°','angle':'∠','square':'□','triangle':'△',
    'bigcirc':'○','perp':'⊥','parallel':'∥','approx':'≈','sim':'∼','le':'≤',
    'leq':'≤','ge':'≥','geq':'≥','ne':'≠','neq':'≠','to':'→','checkmark':'✓',
    'cdot':'·','ldots':'…','dots':'…','pi':'π','alpha':'α','beta':'β',
    'theta':'θ','pm':'±','infty':'∞','prime':'′','%':'%','{':'{','}':'}','_':'_',
    '&':'&','$':'$','#':'#',',':' ',';':' ',':':' ','!':'','quad':'  ',
    'qquad':'    ',' ':' ', 'left':'','right':'','big':'','Big':'',
    'bigl':'','bigr':'','biggl':'','biggr':'', 'displaystyle':'',
}
FORMAT_COMMANDS={'text','textrm','textnormal','textbf','mathrm','mathbf','mathsf','mathbin','mathrel','operatorname'}
MATH_COMMANDS=set(SYMBOLS)|FORMAT_COMMANDS|{'frac','dfrac','tfrac','sqrt','phantom','begin','end','hline','cline'}

class LatexError(ValueError): pass

def braced(s:str, pos:int):
    while pos<len(s) and s[pos].isspace(): pos+=1
    if pos>=len(s): raise LatexError('缺少参数')
    if s[pos]!='{': return s[pos],pos+1
    start=pos+1; depth=1;pos+=1
    while pos<len(s):
        if s[pos]=='\\': pos+=2;continue
        if s[pos]=='{':depth+=1
        elif s[pos]=='}':
            depth-=1
            if depth==0:return s[start:pos],pos+1
        pos+=1
    raise LatexError('花括号未闭合')

def split_top(s:str, delimiter:str):
    out=[];start=0;depth=0;i=0
    while i<len(s):
        if s.startswith(delimiter,i) and depth==0:
            out.append(s[start:i]);i+=len(delimiter);start=i;continue
        if s[i]=='\\':i+=2;continue
        if s[i]=='{':depth+=1
        elif s[i]=='}':depth-=1
        i+=1
    out.append(s[start:]);return out

class MathParser:
    def __init__(self,text):self.s=text;self.i=0
    def parse(self):
        out=[]
        while self.i<len(self.s):
            c=self.s[self.i]
            if c in ' \n\t':self.i+=1;continue
            if c=='}':raise LatexError('意外右花括号')
            if c in '^_':
                self.i+=1
                arg=self.argument()
                if not out:base={'t':'text','v':''}
                else:base=out.pop()
                kind='sup' if c=='^' else 'sub'
                if base.get('t') in ('sup','sub') and base['t']!=kind:
                    base={'t':'subsup','base':base['base'],base['t']:base['arg'],kind:arg}
                else:base={'t':kind,'base':base,'arg':arg}
                out.append(base);continue
            atom=self.atom()
            if atom is not None:
                if atom.get('t')=='text' and out and out[-1].get('t')=='text':out[-1]['v']+=atom['v']
                else:out.append(atom)
        return {'t':'seq','items':out}
    def argument(self):
        while self.i<len(self.s) and self.s[self.i].isspace():self.i+=1
        if self.i>=len(self.s):raise LatexError('缺少数学参数')
        if self.s[self.i]=='{':
            arg,self.i=braced(self.s,self.i);return MathParser(arg).parse()
        # An unbraced TeX parameter is one token, which may itself be a full
        # control sequence, e.g. 180^\circ. Never truncate it to a backslash.
        atom=self.atom()
        return {'t':'seq','items':[] if atom is None else [atom]}
    def atom(self):
        c=self.s[self.i]
        if c=='{':return self.argument()
        if c!='\\':self.i+=1;return {'t':'text','v':c}
        self.i+=1;m=re.match(r'[A-Za-z]+|.',self.s[self.i:])
        if not m:raise LatexError('末尾反斜线')
        name=m.group();self.i+=len(name)
        if name in SYMBOLS:return {'t':'text','v':SYMBOLS[name]}
        if name in FORMAT_COMMANDS:
            if not name.startswith('text') and name!='operatorname':return self.argument()
            arg,self.i=braced(self.s,self.i)
            if name.startswith('text') or name=='operatorname':return {'t':'text','v':plain_text(arg)}
        if name in ('frac','dfrac','tfrac'):return {'t':'frac','num':self.argument(),'den':self.argument()}
        if name=='underline':return {'t':'bar','base':self.argument(),'position':'bot'}
        if name=='sqrt':
            degree=None
            if self.i<len(self.s) and self.s[self.i]=='[':
                j=self.s.find(']',self.i);degree=MathParser(self.s[self.i+1:j]).parse();self.i=j+1
            return {'t':'rad','degree':degree,'base':self.argument()}
        if name=='phantom':return {'t':'text','v':' ' * max(1,len(ast_plain(self.argument())))}
        if name=='begin':
            env,self.i=braced(self.s,self.i)
            if env!='array':raise LatexError('不支持数学环境 '+env)
            cols,self.i=braced(self.s,self.i)
            end=self.s.find('\\end{array}',self.i)
            if end<0:raise LatexError('array 未闭合')
            body=self.s[self.i:end];self.i=end+len('\\end{array}')
            body=re.sub(r'\\(?:hline|cline\{[^}]*\})','',body)
            rows=[]
            for row in split_top(body,r'\\'):
                if row.strip():rows.append([MathParser(cell).parse() for cell in split_top(row,'&')])
            return {'t':'matrix','rows':rows,'columns':cols}
        raise LatexError('未支持公式命令 \\'+name)

def ast_plain(a):
    t=a['t']
    if t=='text':return a['v']
    if t=='seq':return ''.join(map(ast_plain,a['items']))
    if t=='frac':return '('+ast_plain(a['num'])+')/('+ast_plain(a['den'])+')'
    if t in ('sup','sub'):return ast_plain(a['base'])+('^' if t=='sup' else '_')+ast_plain(a['arg'])
    if t=='subsup':return ast_plain(a['base'])+'_'+ast_plain(a['sub'])+'^'+ast_plain(a['sup'])
    if t=='rad':return '√('+ast_plain(a['base'])+')'
    if t=='bar':return ast_plain(a['base'])
    if t=='matrix':return '；'.join('，'.join(map(ast_plain,r)) for r in a['rows'])
    raise LatexError('未知 AST '+t)

def plain_text(s):
    s=re.sub(r'\\par(?![A-Za-z])','\n',s.replace('~',' ')).replace('\\noindent','')
    for cmd in ('textbf','textrm','textnormal','text','emph'):
        while '\\'+cmd in s:
            m=re.search(r'\\'+cmd+r'\s*',s)
            if not m:break
            arg,j=braced(s,m.end());s=s[:m.start()]+arg+s[j:]
    for name,value in sorted(SYMBOLS.items(),key=lambda x:-len(x[0])):
        s=re.sub(r'\\'+re.escape(name)+(r'(?![A-Za-z])' if name.isalpha() else ''),lambda _:value,s)
    unknown=re.findall(r'\\[A-Za-z]+',s)
    if unknown:raise LatexError('未支持文本命令 '+','.join(sorted(set(unknown))))
    s=s.replace(r'\%','%').replace(r'\&','&').replace('{','').replace('}','')
    return s

_RESULT_UNIT = r'(?:平方千米|平方厘米|平方分米|平方毫米|平方米|立方厘米|立方分米|立方米|千瓦时|千米每时|千米|厘米|分米|毫米|千克|毫克|毫升|公顷|小时|分钟|摄氏度|大格|元|角|分|吨|克|米|升|时|秒|天|日|年|月|周|岁|人|名|辆|台|盒|本|个|朵|棵|只|枚|杯|瓶|艘|张|箱|块|筐|次|户|把|队|套|班|面|排|份|轮|组|节|件|袋|座|顶|度|根|层|页|道|盏|趟|支|桶|包|下|部|册|格|场|双)'
_RESULT_UNIT_PARENS=re.compile(r'（((?:万|亿)?'+_RESULT_UNIT+r'(?:[/／·]'+_RESULT_UNIT+r')?(?:[，,][^（）]*)?)）')

def normalize_answer_unit_parentheses(tex):
    """Only result-unit wrappers; numerical groups and question glyphs stay intact."""
    return _RESULT_UNIT_PARENS.sub(lambda m:'('+m[1]+')',tex)

def math_block(tex,role='answer',inline=False):
    if role!='question':tex=normalize_answer_unit_parentheses(tex)
    # Trimming an escaped TeX space would leave a dangling backslash.
    tex=tex.replace('\\ ',r'\quad ')
    leading_operator=None
    if not inline:
        if tex.lstrip().startswith('='):leading_operator='=';tex=tex.lstrip()[1:].lstrip()
        elif tex.lstrip().startswith(r'\approx'):leading_operator='≈';tex=tex.lstrip()[len(r'\approx'):].lstrip()
        elif tex.lstrip().startswith('≈'):leading_operator='≈';tex=tex.lstrip()[1:].lstrip()
    ast=MathParser(tex).parse()
    return {'type':'math','latex':tex.strip(),'ast':ast,'plain':ast_plain(ast),'role':role,'inline':inline,'leading_equals':leading_operator=='=','leading_operator':leading_operator}

def inline_runs(s,role):
    # A formatting wrapper may enclose inline math; remove its outer syntax
    # before splitting so a plain-text fragment never contains half a brace.
    for cmd in ('textbf','emph','textnormal'):
        while True:
            m=re.search(r'\\'+cmd+r'\s*',s)
            if not m:break
            arg,j=braced(s,m.end());s=s[:m.start()]+arg+s[j:]
    out=[];i=0;start=0
    while i<len(s):
        mark=None;close=None
        if s.startswith(r'\(',i):mark=r'\(';close=r'\)'
        elif s[i]=='$' and (i==0 or s[i-1]!='\\'):mark='$';close='$'
        if mark:
            if i>start:out.append({'type':'text','text':plain_text(s[start:i])})
            end=s.find(close,i+len(mark))
            if end<0:raise LatexError('行内公式未闭合')
            out.append(math_block(s[i+len(mark):end],role,True));i=end+len(close);start=i
        else:i+=1
    if start<len(s):out.append({'type':'text','text':plain_text(s[start:])})
    return [x for x in out if x.get('text','x')!='']

def convert_latex(s,role='answer'):
    """Return ordered semantic blocks, retaining exact math/TikZ source."""
    s=re.sub(r'\\begin\{minipage\}(?:\[[^]]*\])?\{[^}]*\}','',s)
    s=s.replace(r'\end{minipage}','').replace(r'\noindent','')
    s=re.sub(r'\\\((\\begin\{aligned\}.*?\\end\{aligned\})\\\)',lambda m:r'\['+m.group(1)+r'\]',s,flags=re.S)
    s=re.sub(r'\\\((\\begin\{array\}.*?\\end\{array\})\\\)',lambda m:r'\['+m.group(1)+r'\]',s,flags=re.S)
    out=[];i=0;start=0;phase='question' if role=='question' else 'analysis';method=None
    def emit_text(t):
        nonlocal phase,method
        for para in re.split(r'\\par(?![A-Za-z])\s*|\n\s*\n',t):
            if not para.strip():continue
            # Dedicated method headings are not conflated with another solution.
            pieces=re.split(r'(\\textbf\{(?:方法|另一方法)[^}]*\})',para)
            for piece in pieces:
                if not piece.strip():continue
                if re.fullmatch(r'\\textbf\{(?:方法|另一方法)[^}]*\}',piece):
                    label=plain_text(piece).strip();method=label;phase='method'
                    out.append({'type':'heading','text':label,'role':role,'phase':'method','method':method});phase='analysis'
                else:
                    runs=inline_runs(piece,role)
                    plain=''.join(x.get('text',x.get('plain','')) for x in runs).strip()
                    actual_phase='conclusion' if plain.startswith('答：') or plain.startswith('答:') else phase
                    pending=[]
                    def paragraph():
                        if pending:out.append({'type':'paragraph','runs':pending.copy(),'role':role,'phase':actual_phase,'method':method});pending.clear()
                    for run in runs:
                        oral_parts=[]
                        if run['type']=='math':
                            oral_parts=[x.strip() for x in split_top(run['latex'],r'\quad') if x.strip()]
                            if len(oral_parts)<2:oral_parts=[x.strip() for x in split_top(run['latex'],r'\qquad') if x.strip()]
                        if role=='question' and len(oral_parts)>=2 and all(x.rstrip().endswith('=') for x in oral_parts):
                            paragraph();group='given_'+hashlib.sha256(run['latex'].encode()).hexdigest()[:10]
                            for expr in oral_parts:
                                mb=math_block(expr,role);mb.update(phase='question',aligned_group=group);out.append(mb)
                        elif role=='question' and len(oral_parts)>=8 and all(re.fullmatch(r'\d+(?:\.\d+)?',x) for x in oral_parts):
                            paragraph()
                            # A long list of measured data is an editable numeric
                            # table; retain its order and split at eight entries.
                            cells=[{'runs':[math_block(x,role,True)]} for x in oral_parts]
                            out.append({'type':'table','rows':[cells[j:j+8] for j in range(0,len(cells),8)],'role':role,'phase':'question','has_header':False,'numeric_data_list':True})
                        elif run['type']=='math' and len(run.get('plain',''))>48 and len(split_top(run['latex'],'='))>=3 and not re.search(_RESULT_UNIT,run.get('plain','').split('=',1)[0]):
                            paragraph()
                            for ei,expr in enumerate(split_top(run['latex'],'=')):
                                mb=math_block(('=' if ei else '')+expr,role);mb.update(phase='question' if role=='question' else 'calculation',method=method,aligned_group='chain_'+hashlib.sha256(run['latex'].encode()).hexdigest()[:10]);out.append(mb)
                        else:pending.append(run)
                    paragraph()
    while i<len(s):
        if s.startswith(r'\begin{tikzpicture}',i):
            emit_text(s[start:i]);end=s.find(r'\end{tikzpicture}',i)
            if end<0:raise LatexError('TikZ 未闭合')
            end+=len(r'\end{tikzpicture}')
            out.append({'type':'diagram','tikz':s[i:end],'role':role,'phase':phase,'method':method})
            i=end;start=i;continue
        if s.startswith(r'\[',i):
            emit_text(s[start:i]);end=s.find(r'\]',i)
            if end<0:raise LatexError('显示公式未闭合')
            tex=s[i+2:end].strip()
            if tex.startswith(r'\begin{aligned}'):
                tex=tex[len(r'\begin{aligned}'):]
                if not tex.endswith(r'\end{aligned}'):raise LatexError('aligned 未闭合')
                tex=tex[:-len(r'\end{aligned}')]
                rows=[]
                for original in split_top(tex,r'\\'):
                    if not original.strip():continue
                    row=re.sub(r'^(?:\{\})?\s*&','',original.strip()).strip()
                    if r'\begin{array}' not in row:row=row.replace('&','')
                    rows.append(row)
            else:rows=[tex]
            group='eq_'+hashlib.sha256(tex.encode()).hexdigest()[:10]
            for row in rows:
                b=math_block(row,role);b.update(phase='calculation',method=method,aligned_group=group)
                if b['ast']['t']=='seq' and len(b['ast']['items'])==1 and b['ast']['items'][0]['t']=='matrix':
                    matrix=b['ast']['items'][0]
                    b={'type':'table','rows':[[{'runs':[{'type':'math','ast':cell,'plain':ast_plain(cell),'role':role,'inline':True}]} for cell in rr] for rr in matrix['rows']],'role':role,'phase':'calculation','method':method,'has_header':True,'from_math_array':True}
                out.append(b)
            i=end+2;start=i;continue
        i+=1
    emit_text(s[start:]);return out

def normalize_record(record,page,vertical=None,oral=None,final_answers=None,display_override=None,teaching_order=None):
    key=record.get('key') or f"p{page['book_page']:03d}_s{record.get('section_index',0)+1:02d}"
    problems=[];blocks=[]
    q=record.get('question_latex','').strip();a=record.get('answer_latex','').strip();original_a=a;answer_slots=[];conclusion_latex=None
    if display_override:
        if hashlib.sha256(a.encode()).hexdigest()!=display_override['source_answer_sha256']:problems.append({'severity':'error','code':'DISPLAY_OVERRIDE_SHA','detail':key})
        else:a=display_override['replacement_answer_latex']
    if teaching_order:
        if hashlib.sha256(original_a.encode()).hexdigest()!=teaching_order['source_answer_sha256'] or not a.startswith(teaching_order['prefix_latex']):problems.append({'severity':'error','code':'TEACHING_ORDER_SHA','detail':key})
        else:
            a=a[len(teaching_order['prefix_latex']):].lstrip();a=re.sub(r'^(?:\\par\s*)+','',a);conclusion_latex=teaching_order['conclusion_latex']
    if vertical and vertical.get('replace_array'):
        # Remove the legacy TeX verticals before any semantic blocks are made.
        # Decimal arrays have multiple columns, so column-count is not a filter.
        a=re.sub(r'\\begin\{array\}\{[^}]*\}.*?\\end\{array\}','',a,flags=re.S)
        a=re.sub(r'\\\[\s*(?:(?:\\quad|\\qquad)\s*)*\\\]','',a)
        a=re.sub(r'\\\(\s*(?:(?:\\quad|\\qquad)\s*)*\\\)','',a)
    if final_answers is not None:
        q,answer_slots,slot_issues=mark_question(q,final_answers,key);problems.extend(slot_issues)
    if not q:problems.append({'severity':'error','code':'MISSING_QUESTION','detail':'缺完整原题文字'})
    if not a and not conclusion_latex:problems.append({'severity':'error','code':'MISSING_ANSWER','detail':'缺完整解析'})
    for role,tex in [('question',q),('answer','' if oral and oral.get('replace_answer') else a)]:
        try:blocks.extend(convert_latex(tex,role))
        except LatexError as e:problems.append({'severity':'error','code':'LATEX_CONVERSION','role':role,'detail':str(e)})
    # Options are explicit editable paragraphs.
    qpos=next((i for i,b in enumerate(blocks) if b['role']=='answer'),len(blocks))
    for index,opt in reversed(list(enumerate(record.get('options',[])))):
        text=opt.get('latex',opt.get('text','')) if isinstance(opt,dict) else str(opt)
        try:blocks.insert(qpos,{'type':'paragraph','runs':inline_runs(text,'question'),'role':'question','phase':'question','option_index':index})
        except LatexError as e:problems.append({'severity':'error','code':'OPTION_CONVERSION','detail':str(e)})
    for diagram in record.get('diagrams',[]):
        role=diagram.get('role','question');tikz=diagram.get('tikz','').strip()
        if not tikz and not diagram.get('native') and not diagram.get('preserve_glyph'):
            problems.append({'severity':'error','code':'MISSING_DIAGRAM_SOURCE','detail':diagram.get('name','unnamed')});continue
        b={'type':'diagram',**diagram,'role':role,'phase':'question' if role=='question' else 'construction'}
        b.pop('animation',None);b.pop('animations',None)
        pos=next((i for i,x in enumerate(blocks) if x['role']=='answer'),len(blocks)) if role=='question' else len(blocks)
        blocks.insert(pos,b)
        quantity_pos=next((i for i,x in enumerate(blocks) if x['role']=='answer'),len(blocks))
        for gi,group in enumerate(diagram.get('quantity_groups',[])):
            factor=str(group['per_group']);groups=str(group['groups']);groups='('+groups+')' if '+' in groups else groups
            runs=[{'type':'text','text':group.get('figure','')+'：'+group.get('grouping','')+'。'} ,math_block(factor+r'\times'+groups,'answer',True)]
            blocks.insert(quantity_pos+gi,{'type':'paragraph','runs':runs,'role':'answer','phase':'analysis','quantity_group':True})
        if diagram.get('preserve_glyph') and not diagram.get('glyph_svg') and not diagram.get('glyph_image'):
            problems.append({'severity':'error','code':'MISSING_GLYPH_SOURCE','detail':'字形为条件：需原字形 glyph_svg 或 glyph_image 实际路径，不可替换字体'})
    for table_index,table in enumerate(record.get('tables',[])):
        values=table.get('values') or ([table['headers']]+table.get('rows',[]) if table.get('headers') else table.get('rows'))
        if not values or not isinstance(values,list):
            problems.append({'severity':'error','code':'MISSING_TABLE_VALUES','detail':'表格必须提供矩阵'});continue
        rows=[]
        try:
            for row in values:
                cells=[]
                for cell in row:
                    rr=inline_runs(str(cell),'question')
                    # Quantities and units are ordinary table text, not an
                    # equation container with application-specific inner padding.
                    simple=lambda a:a['t']=='text' or a['t']=='seq' and all(simple(x) for x in a['items'])
                    for j,run in enumerate(rr):
                        if run['type']=='math' and simple(run['ast']) and not re.search(r'[+×÷=<>≤≥≠]|(?<![A-Za-z])-[0-9]',run['plain']):rr[j]={'type':'text','text':run['plain']}
                    cells.append({'runs':rr})
                rows.append(cells)
        except LatexError as e:problems.append({'severity':'error','code':'TABLE_CONVERSION','detail':str(e)})
        role=table.get('role','question');titles=[]
        for field in ('title','caption'):
            text=table.get(field)
            if text and text not in titles:titles.append(text)
        footers=[]
        footer=table.get('footer')
        if footer:footers.extend(footer if isinstance(footer,list) else [footer])
        notes=table.get('notes',[]);notes=notes if isinstance(notes,list) else [notes]
        analysis_notes=[]
        if key=='p052_s02':analysis_notes=notes
        elif key=='p084_s03' and notes:footers.append('两项总价合计1014元。')
        else:footers.extend(notes)
        tb={'type':'table','rows':rows,'role':role,'phase':'question' if role=='question' else 'conclusion','raw_table_index':table_index,'caption':table.get('caption',''),'title_runs':[inline_runs(x,role) for x in titles],'footer_runs':[inline_runs(x,role) for x in footers],'has_header':bool(table.get('headers')),'source_table':table}
        pos=next((i for i,x in enumerate(blocks) if x['role']=='answer'),len(blocks)) if role=='question' else len(blocks);blocks.insert(pos,tb)
        for note in analysis_notes:blocks.insert(pos+1,{'type':'paragraph','runs':inline_runs(note,'answer'),'role':'answer','phase':'analysis','table_note':True})
    # Geometry agents provide record-level animation. Keep the original
    # question graphic, and add a construction scene after the first analysis.
    animation=record.get('animation')
    if not animation:
        candidates=list(record.get('animations',[]))
        for g in record.get('diagrams',[]):
            for spec in ([g['animation']] if g.get('animation') else [])+g.get('animations',[]):candidates.append({'diagram_name':g.get('name'),**spec})
        unique={json.dumps(spec,ensure_ascii=False,sort_keys=True):spec for spec in candidates};candidates=list(unique.values())
        if candidates:
            if len(candidates)>1 and all(s.get('type') in ('translation','rotation') for s in candidates) and len({s.get('diagram_name') for s in candidates})==1:
                animation={**candidates[0],'type':'sequence','steps':[{k:v for k,v in s.items() if k not in ('object_points','additional_paths','diagram_name')} for s in candidates]}
            else:animation={'type':'alternatives','alternatives':candidates}
    if not animation and key=='p010_s10':
        animation={'type':'perpendicular','line_name':'l','point_name':'A','schematic':True}
    if animation:
        question_diagram=next((b for b in blocks if b['type']=='diagram' and b['role']=='question'),None)
        alternatives=animation.get('alternatives') if animation.get('type')=='alternatives' else None
        scenes=[{**animation,**a,'alternatives':None,'placement':animation.get('alternative_placements',[[0,0]]*len(alternatives))[i]} for i,a in enumerate(alternatives)] if alternatives else [animation]
        position=next((i+1 for i,b in enumerate(blocks) if b['role']=='answer' and b['type']=='paragraph'),len(blocks))
        for ai,spec in enumerate(scenes):
            answer_objects={'p035_s04','p035_s05','p035_s06','p039_s01','p043_s02','p095_s04','p095_s05'}
            if key in answer_objects and spec.get('type')=='altitude':spec={**spec,'object_role':'answer'}
            associated=next((b for b in blocks if b['type']=='diagram' and b.get('name')==spec.get('diagram_name')),None)
            if key=='p095_s05':
                spec={**spec,'grid':{'x_min':0,'x_max':11,'y_min':0,'y_max':5,'step':1,'dotted':True}}
                if spec.get('type')=='rotation':spec['show_pivot_label']=True
            if associated and associated.get('role')=='answer' and spec.get('type') not in ('altitude','perpendicular','perpendicular_shortest_path'):
                associated=question_diagram
            base=copy.deepcopy(associated or question_diagram) if (associated or question_diagram) else {'type':'diagram'}
            if not spec.get('grid') and base.get('tikz'):
                gm=re.search(r'\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)\s*grid\s*\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)',base['tikz'])
                if gm:
                    x0,y0,x1,y1=map(float,gm.groups());spec={**spec,'grid':{'x_min':min(x0,x1),'x_max':max(x0,x1),'y_min':min(y0,y1),'y_max':max(y0,y1),'step':1}}
            bounds=animation_bounds(spec)
            if base.get('tikz') and not spec.get('grid') and spec.get('type') not in ('altitude','perpendicular','perpendicular_shortest_path'):
                coords=[(float(x),float(y)) for x,y in re.findall(r'\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)',base['tikz'])]
                if coords:
                    bb=[min(x for x,y in coords)-.6,min(y for x,y in coords)-.6,max(x for x,y in coords)+.6,max(y for x,y in coords)+.6]
                    bounds=[min(bounds[0],bb[0]),min(bounds[1],bb[1]),max(bounds[2],bb[2]),max(bounds[3],bb[3])] if bounds else bb
            base.update(role='answer',phase='construction',animation=spec,animation_bounds=bounds,name=key+f'_animation_{ai}')
            if key=='p071_s02' and spec.get('placement') not in (None,[0,0]):base['background_shift']=spec['placement']
            blocks.insert(position+ai,base)
    if vertical:
        if vertical.get('replace_array') and any(b['type']=='table' and b.get('from_math_array') and b['role']=='answer' for b in blocks):
            problems.append({'severity':'error','code':'LEGACY_VERTICAL_ARRAY_REMAINED','detail':key})
        if vertical.get('replace_question_diagrams'):
            replaced=set(vertical['replace_question_diagrams']);blocks=[b for b in blocks if not (b['type']=='diagram' and b.get('name') in replaced)]
        for calc in vertical.get('calculations',[]):
            role=calc.get('role','answer')
            vb={'type':'vertical','calculation':calc,'role':role,'phase':'calculation'}
            if role=='question':blocks.insert(next((i for i,b in enumerate(blocks) if b['role']=='answer'),len(blocks)),vb)
            else:blocks.append(vb)
    if oral and oral.get('replace_answer'):
        for item in oral['subquestions']:
            sq=item['key'];label=item['display_label']
            common={'subquestion_key':sq,'subquestion_label':label}
            blocks.append({'type':'heading','text':label,'role':'question','phase':'subquestion',**common})
            given=math_block(item['expression_latex'],'question');given.update(phase='question',**common);blocks.append(given)
            if item.get('strategy'):blocks.append({'type':'paragraph','runs':inline_runs(item['strategy'],'answer'),'role':'answer','phase':'analysis',**common})
            for index,step in enumerate(item['steps'][1:],1):
                relation=item['relations'][index-1];prefix=r'\approx ' if relation=='≈' else '='
                mb=math_block(prefix+step,'answer');mb.update(phase='calculation',aligned_group=sq,**common);blocks.append(mb)
            if item.get('scope_note'):blocks.append({'type':'paragraph','runs':inline_runs(item['scope_note'],'answer'),'role':'answer','phase':'analysis',**common})
    if conclusion_latex:
        conclusion=convert_latex(conclusion_latex,'answer')
        for b in conclusion:b.update(phase='conclusion',teaching_conclusion=True)
        blocks.extend(conclusion)
    if answer_slots:
        try:
            blocks,slot_issues=transform_blocks(blocks,answer_slots,math_block);problems.extend(slot_issues)
            if any(s.get('mapped') or s.get('unresolved') for s in answer_slots):
                for variant in ([{'label':'原题回填','final_answers':final_answers.get('final_answers',[])}]+final_answers.get('variants',[])):
                    variant_map={x['slot_index']:x for x in variant.get('final_answers',[])}
                    review=copy.deepcopy([b for b in blocks if b['role']=='question' and b['type'] in ('paragraph','math','heading') and not b.get('is_review')])
                    for i,b in enumerate(review):
                        b['is_review']=True;b['review_start']=i==0;b['review_label']=variant.get('label','原题回填')
                        for run in b.get('runs',[]):
                            if run['type']=='slot':
                                replacement=variant_map.get(run['slot_index'],{})
                                if replacement.get('answer_latex') is not None:run['answer']=math_block(replacement['answer_latex'],'answer',True);run['unresolved']=False
                                elif replacement.get('answer_text') is not None:run['answer']={'type':'text','text':replacement['answer_text']};run['unresolved']=False
                                run['reveal']=True
                    blocks.extend(review)
        except (ValueError,LatexError) as e:problems.append({'severity':'error','code':'ANSWER_SLOT_CONVERSION','detail':str(e)})
    if final_answers and final_answers.get('table_final_answers'):
        grouped=collections.defaultdict(list)
        for cell in final_answers['table_final_answers']:grouped[cell['table_index']].append(cell)
        for ti,entries in grouped.items():
            source_table=next((b for b in blocks if b['type']=='table' and b.get('raw_table_index')==ti and not b.get('is_review')),None)
            if source_table is None:problems.append({'severity':'error','code':'TABLE_ANSWER_INDEX','detail':str(ti)});continue
            filled=copy.deepcopy(source_table);filled.update(is_review=True,review_start=True,review_label='原表回填',review_table=True,role='question',phase='question')
            filled.pop('source_table',None)
            for entry in entries:
                ri=entry['row_index']+(1 if filled.get('has_header') else 0);ci=entry['column_index']
                try:cell=filled['rows'][ri][ci];original=record['tables'][ti]['rows'][entry['row_index']][ci]
                except (IndexError,KeyError):problems.append({'severity':'error','code':'TABLE_CELL_INDEX','detail':str(entry)});continue
                if str(original)!=str(entry.get('expected_original','')):problems.append({'severity':'error','code':'TABLE_CELL_ORIGINAL','detail':str(entry)});continue
                is_blank=not str(original).strip() or bool(re.fullmatch(r'[（(][ \t\u3000]*[）)]|_+',str(original)))
                if not is_blank and not entry.get('allow_nonblank_override'):problems.append({'severity':'error','code':'TABLE_CELL_NONBLANK','detail':str(entry)});continue
                unresolved=entry.get('answer_latex') is None and entry.get('answer_text') is None
                answer=({'type':'text','text':entry.get('display_label','待核')} if unresolved else math_block(entry['answer_latex'],'answer',True) if entry.get('answer_latex') is not None else {'type':'text','text':entry['answer_text']})
                kind='parentheses' if str(original).startswith(('（','(')) and is_blank else 'cell'
                composite=re.fullmatch(r'(.*?)\\square(.*?)',str(original))
                known_prefix=known_suffix=''
                if composite and entry.get('answer_latex') is not None:
                    known_prefix,known_suffix=composite.groups();full=entry['answer_latex']
                    if full.startswith(known_prefix) and full.endswith(known_suffix):
                        inside=full[len(known_prefix):len(full)-len(known_suffix) if known_suffix else None]
                        answer=math_block(inside,'answer',True);kind='cell_composite'
                    else:problems.append({'severity':'error','code':'TABLE_COMPOSITE_VALUE','detail':str(entry)})
                cell['runs']=[];cell['final_slot']={'type':'slot','kind':kind,'placeholder':str(original),'answer':answer,'reveal':True,'is_table':True,'table_index':ti,'row_index':entry['row_index'],'column_index':ci,'unresolved':unresolved,'note':entry.get('note',''),'group_key':f'{key}_table{ti}_row{entry["row_index"]}','phase_label':f'原表第{entry["row_index"]+1}行回填','known_prefix':known_prefix,'known_suffix':known_suffix,'full_answer':entry.get('answer_latex',entry.get('answer_text'))}
            blocks.append(filled)
    verification=record.get('verification',{})
    if verification.get('status')!='verified':problems.append({'severity':'warning','code':'NOT_VERIFIED','detail':verification.get('status','missing')})
    has_diagram=any(b['type']=='diagram' for b in blocks)
    if record.get('requires_diagram') and not has_diagram:problems.append({'severity':'error','code':'DIAGRAM_REQUIRED','detail':'原题要求图形，但无重绘图源'})
    inferred_animation=record.get('kind')=='drawing' and bool(re.search(r'作(?:出)?.{0,5}高|画.{0,8}(?:高|平移|旋转)|平移后|旋转后',q))
    if (record.get('requires_animation') or inferred_animation) and not any(b['type']=='diagram' and (b.get('animation') or b.get('native',{}).get('animation')) for b in blocks):
        problems.append({'severity':'error','code':'ANIMATION_REQUIRED','detail':'需提供几何动画参数，不能降级为静态图'})
    for i,b in enumerate(blocks):b['key']=key+f'_b{i:03d}'
    return {'key':key,'book_page':page['book_page'],'source_page':page['source_page'],'id':record.get('id',''),'kind':record.get('kind',''),'section_index':record.get('section_index',0),'verification':verification,'answer_slots':answer_slots,'teaching_order':teaching_order,'blocks':blocks,'problems':problems,'raw':record}

def animation_bounds(spec):
    grid=spec.get('grid')
    if grid:return [grid['x_min']-.7,grid['y_min']-.7,grid['x_max']+.7,grid['y_max']+.7]
    points=spec.get('object_points',[]) or [p for path in spec.get('object_paths',[]) for p in path]
    points=points+[p for path in spec.get('additional_paths',[]) for p in path]
    if spec.get('type') in ('parallel_objects','sequence_objects'):
        points=[p for obj in spec.get('objects',[]) for p in obj.get('points',[])]
    if not points and spec.get('type') in ('altitude','perpendicular','perpendicular_shortest_path'):
        points=[p for p in spec.get('base',[]) if isinstance(p,list)]
        points.extend([spec[k] for k in ('vertex','foot','endpoint') if isinstance(spec.get(k),list)])
        if not points:points=[[0,0],[6,0],[3,0],[3,2]]
    if not points:return None
    placement=spec.get('placement',[0,0]);current=[[p[0]+placement[0],p[1]+placement[1]] for p in points];allpts=copy.deepcopy(current)
    if spec.get('copy_placements'):
        allpts=[]
        for cp in spec['copy_placements']:
            origin=cp['origin'];current_cp=[[p[0]+origin[0],p[1]+origin[1]] for p in points];allpts.extend(current_cp)
            angle=math.radians(float(cp['angle'])*(-1 if spec.get('direction')=='clockwise' else 1));allpts.extend([[origin[0]+p[0]*math.cos(angle)-p[1]*math.sin(angle),origin[1]+p[0]*math.sin(angle)+p[1]*math.cos(angle)] for p in points])
    steps=spec.get('steps') if spec.get('type') in ('sequence','rotation_sequence') else [spec]
    if spec.get('type')=='rotation_sequence':steps=[{'type':'rotation',**step} for step in steps]
    if spec.get('type')=='rotation_copies':steps=[{'type':'rotation','center':spec.get('center',[0,0]),'angle':angle,'direction':spec.get('direction')} for angle in spec.get('angles',[])]
    if spec.get('type')=='symmetry':
        a=spec['axis']['p1'];b=spec['axis']['p2'];dx=b[0]-a[0];dy=b[1]-a[1];d2=dx*dx+dy*dy
        for p in current:
            t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d2;allpts.append([2*(a[0]+t*dx)-p[0],2*(a[1]+t*dy)-p[1]])
        allpts.extend([a,b])
    for step in steps:
        if step['type']=='translation':current=[[p[0]+step.get('dx',0),p[1]+step.get('dy',0)] for p in current]
        elif step['type']=='rotation':
            cc=step.get('center',spec.get('center',[0,0]));center=[cc[0]+placement[0],cc[1]+placement[1]];angle=float(step.get('angle',90))*(-1 if step.get('direction')=='clockwise' else 1)
            for k in range(1,9):
                r=math.radians(angle*k/8);allpts.extend([[center[0]+(p[0]-center[0])*math.cos(r)-(p[1]-center[1])*math.sin(r),center[1]+(p[0]-center[0])*math.sin(r)+(p[1]-center[1])*math.cos(r)] for p in current])
            r=math.radians(angle);current=[[center[0]+(p[0]-center[0])*math.cos(r)-(p[1]-center[1])*math.sin(r),center[1]+(p[0]-center[0])*math.sin(r)+(p[1]-center[1])*math.cos(r)] for p in current]
        allpts.extend(copy.deepcopy(current))
    xs=[p[0] for p in allpts];ys=[p[1] for p in allpts];pad=max(.6,.08*max(max(xs)-min(xs),max(ys)-min(ys)))
    if spec.get('type') in ('altitude','perpendicular','perpendicular_shortest_path'):pad=max(pad,.25*max(max(xs)-min(xs),max(ys)-min(ys)))
    return [min(xs)-pad,min(ys)-pad,max(xs)+pad,max(ys)+pad]

def convert_all(folder:Path,start:int,end:int,expected:dict|None=None,answers_path:Path|None=None):
    records=[];issues=[];missing=[]
    vertical_path=Path(__file__).parent/'vertical_calculations.json'
    vertical_bytes=vertical_path.read_bytes() if vertical_path.exists() else None
    vertical=json.loads(vertical_bytes).get('records',{}) if vertical_bytes else {}
    oral_path=Path(__file__).parent/'oral_calculations.json';oral_bytes=oral_path.read_bytes() if oral_path.exists() else None
    oral=json.loads(oral_bytes).get('records',{}) if oral_bytes else {}
    display_path=Path(__file__).parent/'math_display_overrides.json';display_bytes=display_path.read_bytes() if display_path.exists() else None;display=json.loads(display_bytes).get('records',{}) if display_bytes else {}
    teaching_path=Path(__file__).parent/'teaching_order.json';teaching_bytes=teaching_path.read_bytes() if teaching_path.exists() else None;teaching=json.loads(teaching_bytes).get('records',{}) if teaching_bytes else {}
    answers_path=answers_path or Path(__file__).parent/'final_answers.json';answers_bytes=answers_path.read_bytes() if answers_path.exists() else None
    answers=json.loads(answers_bytes).get('records',{}) if answers_bytes else None
    for n in range(start,end+1):
        f=folder/f'p{n:03d}.json'
        if not f.exists():missing.append(n);continue
        page=json.loads(f.read_text())
        if page.get('book_page')!=n:issues.append({'severity':'error','code':'PAGE_MISMATCH','book_page':n})
        for rec in page.get('records',[]):
            r=normalize_record(rec,page,vertical.get(rec.get('key')),oral.get(rec.get('key')),answers.get(rec.get('key'),{}) if answers is not None else None,display.get(rec.get('key')),teaching.get(rec.get('key')));records.append(r)
            issues.extend({'key':r['key'],**x} for x in r['problems'])
        if expected:
            actual={r['section_index'] for r in page.get('records',[])};wanted=set(range(expected.get(str(page['source_page']),0)))
            for ix in sorted(wanted-actual):issues.append({'severity':'error','code':'MISSING_SECTION','book_page':n,'section_index':ix})
    for n in missing:issues.append({'severity':'error','code':'MISSING_PAGE','book_page':n})
    keys=[r['key'] for r in records]
    for k,c in collections.Counter(keys).items():
        if c>1:issues.append({'severity':'error','code':'DUPLICATE_KEY','key':k,'count':c})
    counts=collections.Counter(b['type'] for r in records for b in r['blocks'])
    return {'schema_version':1,'range':[start,end],'records':records,'issues':issues,'counts':dict(counts),'error_count':sum(x['severity']=='error' for x in issues),'vertical_metadata_sha256':hashlib.sha256(vertical_bytes).hexdigest() if vertical_bytes else None,'oral_metadata_sha256':hashlib.sha256(oral_bytes).hexdigest() if oral_bytes else None,'final_answers_sha256':hashlib.sha256(answers_bytes).hexdigest() if answers_bytes else None,'math_display_sha256':hashlib.sha256(display_bytes).hexdigest() if display_bytes else None,'teaching_order_sha256':hashlib.sha256(teaching_bytes).hexdigest() if teaching_bytes else None}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--questions',type=Path,required=True);ap.add_argument('--start',type=int,default=1);ap.add_argument('--end',type=int,default=108);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expected',type=Path);ap.add_argument('--answers',type=Path)
    args=ap.parse_args();expected=json.loads(args.expected.read_text()) if args.expected else None
    if args.start==91:
        gate=Path(__file__).parent/'volume6_source_gate.flag'
        while gate.exists():time.sleep(2)
    data=convert_all(args.questions,args.start,args.end,expected,args.answers);args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(data,ensure_ascii=False,indent=2))
    print(json.dumps({'records':len(data['records']),'counts':data['counts'],'issues':len(data['issues']),'errors':data['error_count']},ensure_ascii=False));raise SystemExit(1 if data['error_count'] else 0)
if __name__=='__main__':main()
