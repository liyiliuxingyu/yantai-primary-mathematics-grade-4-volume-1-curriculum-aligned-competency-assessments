"""Independently check the bracket-preservation patch; exact arithmetic, source scope and chain continuity."""
from pathlib import Path
from fractions import Fraction
import argparse, ast, difflib, hashlib, json, re, zipfile
HERE=Path(__file__).resolve().parent
if (HERE/'project/questions').is_dir():
    R=HERE;P=HERE/'project';Q=P/'bracket_update';APPROVED=HERE/'approved_changes.json'
elif (HERE.parent/'questions').is_dir():
    P=HERE.parent;Q=HERE;R=HERE;APPROVED=HERE/'change.json'
else:raise RuntimeError('Current question source tree cannot be located.')
def J(p):return json.loads(Path(p).read_text())
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def SHA(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def strip_commands(s):
    for cmd in ['text','textrm','mathrm','mbox']:
        token='\\'+cmd
        while token in s:
            a=s.index(token);i=a+len(token)
            while i<len(s) and s[i].isspace():i+=1
            if i>=len(s) or s[i]!='{':break
            d=1;j=i+1
            while j<len(s) and d:
                if s[j]=='{':d+=1
                if s[j]=='}':d-=1
                j+=1
            s=s[:a]+s[j:]
    for cmd in ['left','right','bigl','bigr','Bigl','Bigr','big','Big','displaystyle','quad','qquad']:
        s=s.replace('\\'+cmd,'')
    s=s.replace('\\times','*').replace('\\div','/').replace('×','*').replace('÷','/').replace('−','-')
    s=s.replace('\\,','').replace('\\;','').replace('\\!','').replace('~','')
    s=s.replace('\\(','').replace('\\)','').replace('\\[','').replace('\\]','')
    return s.replace('&','').replace('{}','').strip()
def expression(s):
    s=strip_commands(s).lstrip('=').strip();return s.replace('[','(').replace(']',')')
def val(s):
    s=expression(s)
    if not s or re.search(r'[^0-9+*/().\-\s]',s):raise ValueError(s)
    def e(n):
        if isinstance(n,ast.Expression):return e(n.body)
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):return Fraction(str(n.value))
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return e(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp):
            a,b=e(n.left),e(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
        raise ValueError(s)
    return e(ast.parse(s,mode='eval'))
def getter(record,path):
    out=record
    for attr,idx in re.findall(r'([A-Za-z_]+)(?:\[(\d+)\])?',path):
        out=out[attr]
        if idx:out=out[int(idx)]
    return out

def only_brackets(a,b):
    edits=[]
    for typ,aa,ab,ba,bb in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if typ=='equal':continue
        x,y=a[aa:ab],b[ba:bb]
        assert set(x+y)<=set('()[]'),(typ,x,y)
        edits.append({'old':x,'new':y,'old_offset':aa,'new_offset':ba})
    assert re.sub(r'[()\[\]]','',a)==re.sub(r'[()\[\]]','',b)
    assert a.count('\\\\')==b.count('\\\\')
    assert re.findall(r'\\[()\[\]]',a)==re.findall(r'\\[()\[\]]',b),'Math-mode delimiters must not change.'
    assert re.findall(r'\\text\{[^}]*\}',a)==re.findall(r'\\text\{[^}]*\}',b)
    assert re.findall(r'（[^）]*）',a)==re.findall(r'（[^）]*）',b)
    return edits

class Parser:
    def __init__(self,s):
        self.s=strip_commands(s).lstrip('=')
        if re.search(r'[^0-9.+*/()\[\]\-\s]',self.s):raise ValueError(self.s)
        self.t=re.findall(r'\d+(?:\.\d+)?|[+*/()\[\]-]',self.s);self.i=0
    def node(self):
        n=self.add()
        if self.i!=len(self.t):raise ValueError('trailing tokens')
        return n
    def add(self):
        n=self.mul()
        while self.i<len(self.t) and self.t[self.i] in ['+','-']:
            op=self.t[self.i];self.i+=1;n=('op',op,n,self.mul())
        return n
    def mul(self):
        n=self.atom()
        while self.i<len(self.t) and self.t[self.i] in ['*','/']:
            op=self.t[self.i];self.i+=1;n=('op',op,n,self.atom())
        return n
    def atom(self):
        t=self.t[self.i];self.i+=1
        if t in ['+','-']:return ('op',t,('num',Fraction(0)),self.atom())
        if t in ['(','[']:
            n=self.add();end=')' if t=='(' else ']'
            if self.t[self.i]!=end:raise ValueError('mismatched grouping')
            self.i+=1;return ('group',t,n)
        return ('num',Fraction(t))
def nv(n):
    if n[0]=='num':return n[1]
    if n[0]=='group':return nv(n[2])
    a,b=nv(n[2]),nv(n[3]);return {'+':lambda:a+b,'-':lambda:a-b,'*':lambda:a*b,'/':lambda:a/b}[n[1]]()
def ops(n):return n[0]=='op' or (n[0]=='group' and ops(n[2]))
def groups(n,path=()):
    out=[]
    if n[0]=='group':out.append((path,n[1],n[2]));out+=groups(n[2],path)
    if n[0]=='op':out+=groups(n[2],path+(n[1]+'L',))+groups(n[3],path+(n[1]+'R',))
    return out
def at_path(n,path):
    if not path:return n
    while n[0]=='group':n=n[2]
    if n[0]!='op' or path[0][0]!=n[1]:return None
    return at_path(n[2 if path[0][1]=='L' else 3],path[1:])

def source_fields(snapshot):
    for f,d in snapshot.items():
        for r in d['records']:
            fields=['answer_latex'] if f.startswith('questions/') else ['latex']+[f'local_replacements[{i}].latex' for i in range(len(r.get('local_replacements',[])))]
            for field in fields:
                if field.split('[')[0] not in r:continue
                yield f,r['key'],field,getter(r,field)

def scan_continuity(snapshot):
    flags=[];missing=[];chains=0;adjacent=0;square_rows=0;unparsed=[]
    for f,key,field,text in source_fields(snapshot):
        for bi,body in enumerate(re.findall(r'\\begin\{aligned\}(?:\[t\])?(.*?)\\end\{aligned\}',text,re.S)):
            rows=re.split(r'\\\\',body);prev=None;chains+=1
            for ri,row in enumerate(rows):
                clean=strip_commands(row).lstrip('=')
                if not clean:continue
                try:n=Parser(clean).node();v=nv(n)
                except Exception:
                    if '[' in clean:unparsed.append({'key':key,'field':field,'block':bi,'row':ri,'expression':clean})
                    prev=None;continue
                if any(t=='[' for p,t,n0 in groups(n)):square_rows+=1
                if prev:
                    adjacent+=1
                    a,pv,prow=prev
                    # A surviving corresponding group at the same operator path must keep [].
                    if pv==v:
                        for path,t,g in groups(a):
                            if t!='[':continue
                            target=at_path(n,path)
                            if target is not None and target[0]!='group' and ops(target) and nv(g)==nv(target):
                                missing.append({'file':f,'key':key,'field':field,'block':bi,'old_row':prow,'new_row':row,'path':path,'value':str(nv(g))})
                            for np,nt,ng in groups(n):
                                if np==path and nt=='(' and ops(ng) and nv(g)==nv(ng):
                                    flags.append({'file':f,'key':key,'field':field,'block':bi,'old_row':prow,'new_row':row,'path':path,'value':str(nv(g))})
                prev=(n,v,row)
    return {'aligned_formula_blocks_scanned':chains,'numeric_adjacent_row_pairs_checked':adjacent,'rows_with_square_grouping':square_rows,'remaining_square_to_round_continuity_flags':flags,'square_group_disappeared_but_corresponding_operation_remains':missing,'non_numeric_square_rows_for_manual_review':unparsed}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--baseline-source',type=Path);args=ap.parse_args()
    Q.mkdir(exist_ok=True)
    basepath=Q/'baseline_source_snapshot.json'
    zipfile_path=args.baseline_source or (R/'bundle/小学四上同步素养卷LaTeX与TikZ源码答案.zip')
    if zipfile_path.exists():
        with zipfile.ZipFile(zipfile_path) as z:
            names=sorted(n for n in z.namelist() if re.fullmatch(r'questions/p\d{3}\.json|detailed_layout/notes_[ABCD]\.json',n))
            baseline={n:json.loads(z.read(n)) for n in names}
        W(basepath,{'source_archive_sha256':SHA(zipfile_path),'files':baseline})
    else:baseline=J(basepath)['files']
    approved=J(APPROVED);changes=approved['changes'];keys=[c['key'] for c in changes]
    assert len(keys)==len(set(keys))==41
    current={n:J(P/n) for n in baseline}
    brecs={(n,r['key']):r for n,d in baseline.items() for r in d['records']}
    crecs={(n,r['key']):r for n,d in current.items() for r in d['records']}
    field_evidence=[];declared={};row_evidence=[];pairs=set();ppt_only_evidence=[]
    for c in changes:
        for f in c['field_changes']:
            item=(f['file'],c['key'],f['field']);assert item not in declared;declared[item]=f
            assert getter(brecs[(f['file'],c['key'])],f['field'])==f['old'],item
            assert getter(crecs[(f['file'],c['key'])],f['field'])==f['new'],item
            edits=only_brackets(f['old'],f['new']);assert edits
            field_evidence.append({'file':f['file'],'key':c['key'],'field':f['field'],'bracket_edits':edits,'row_count_unchanged':True,'units_unchanged':True})
        for row in c['row_replacements']:
            pair=(row['old'],row['new']);assert pair not in pairs; pairs.add(pair)
            edits=only_brackets(*pair);a,b=val(pair[0]),val(pair[1]);assert a==b,(c['key'],pair,a,b)
            row_evidence.append({'key':c['key'],'old':pair[0],'new':pair[1],'old_value':str(a),'new_value':str(b),'passed':True})
        for row in c.get('ppt_only_row_replacements',[]):
            pair=(row['old'],row['new']);assert pair not in pairs; pairs.add(pair)
            edits=only_brackets(*pair);a,b=val(pair[0]),val(pair[1]);assert a==b
            assert c['key'] in ['p091_s03','p104_s02']
            assert a=={'p091_s03':Fraction(98),'p104_s02':Fraction('46.8')}[c['key']]
            ppt_only_evidence.append({'key':c['key'],'old':pair[0],'new':pair[1],'old_value':str(a),'new_value':str(b),'bracket_edits':edits,'row_count_unchanged':True,'source_and_pdf_unchanged':True,'reason':row['reason'],'passed':True})
    assert len(field_evidence)==66 and len(row_evidence)==60
    assert len(ppt_only_evidence)==2 and len(pairs)==62
    assert {x['key'] for x in ppt_only_evidence}=={'p091_s03','p104_s02'}
    syncfile=Q/'new_local_patches.json'
    sync=J(syncfile) if syncfile.exists() else {'records':[]}
    assert len(sync['records'])==17
    sync_by_id={x['id']:x for x in sync['records']};assert len(sync_by_id)==17
    sync_evidence=[];seen_sync=[]
    def canon(s):return re.sub(r'\s+','',strip_commands(s).lstrip('='))
    question_changes=[];note_changes=[];qn=0;unit_snapshot=[]
    for name,d in baseline.items():
        other=current[name];assert {k:v for k,v in d.items() if k!='records'}=={k:v for k,v in other.items() if k!='records'}
        assert len(d['records'])==len(other['records'])
        for a,b in zip(d['records'],other['records']):
            assert a['key']==b['key'];key=a['key']
            if name.startswith('questions/'):
                qn+=1
                assert {k:v for k,v in a.items() if k not in ['answer_latex','verification']}=={k:v for k,v in b.items() if k not in ['answer_latex','verification']},key
                if a!=b:
                    question_changes.append(key);assert key in keys
                    av,bv=a.get('verification',{}),b.get('verification',{})
                    assert {k:v for k,v in av.items() if k!='changes'}=={k:v for k,v in bv.items() if k!='changes'}
                    assert bv.get('changes',[])[:len(av.get('changes',[]))]==av.get('changes',[])
                    assert len(bv.get('changes',[]))==len(av.get('changes',[]))+1
                    assert (name,key,'answer_latex') in declared
                else:assert key not in keys
            else:
                if a!=b:note_changes.append(key);assert key in keys
                # All note changes must be precisely declared bracket fields, or an explicitly labelled display-sync local patch added later.
                stripped_a=json.loads(json.dumps(a));stripped_b=json.loads(json.dumps(b))
                for (fn,kk,field),change in declared.items():
                    if fn!=name or kk!=key:continue
                    if field=='latex':stripped_a['latex']=stripped_b['latex']='__DECLARED__'
                    else:
                        ii=int(re.search(r'\[(\d+)\]',field)[1]);stripped_a['local_replacements'][ii]['latex']=stripped_b['local_replacements'][ii]['latex']='__DECLARED__'
                old_locals=a.get('local_replacements',[])
                new_locals=b.get('local_replacements',[])
                assert len(new_locals)>=len(old_locals)
                for ii,patch in enumerate(new_locals[len(old_locals):],start=len(old_locals)):
                    sid=f'{key}_local{ii+1}';assert sid in sync_by_id and key in keys
                    entry=sync_by_id[sid];seen_sync.append(sid)
                    assert entry['key']==key and patch['latex']==entry['latex']
                    assert patch['rect']==entry['mask_rect'] and patch['target_rect']==entry['container_rect']
                    assert patch['font_size']==entry['font_size'] and patch['baseline_anchor']==entry['baseline_anchor']
                    assert entry['old_row_count_preserved']==1
                    assert strip_commands(patch['latex']).startswith('='),'Do not duplicate the black original first expression.'
                    assert patch['latex'].count('\\\\')==0,'A display-sync patch must contain only its original single row.'
                    assert canon(patch['latex'])==canon(entry['new_expression'])
                    assert any(canon(entry['new_expression'])==canon(v['new']) for c in changes if c['key']==key for v in c['row_replacements'])
                    ov,nv0,lv=val(entry['old_visible_row']),val(entry['new_expression']),val(patch['latex'])
                    assert ov==nv0==lv
                    assert re.sub(r'[()\[\]]','',canon(entry['old_visible_row']))==re.sub(r'[()\[\]]','',canon(entry['new_expression']))
                    sync_evidence.append({'key':key,'id':sid,'old_visible_row':entry['old_visible_row'],'new_expression':entry['new_expression'],'old_value':str(ov),'new_value':str(nv0),'single_original_row_preserved':True,'matches_approved_answer_row':True})
                if 'local_replacements' in a:
                    stripped_b['local_replacements']=stripped_b.get('local_replacements',[])[:len(old_locals)]
                else:stripped_b.pop('local_replacements',None)
                assert stripped_a==stripped_b,('undeclared_note_change',key)
    assert qn==867 and set(question_changes)==set(keys)
    assert set(seen_sync)==set(sync_by_id)
    scan=scan_continuity(current)
    assert not scan['remaining_square_to_round_continuity_flags']
    assert not scan['square_group_disappeared_but_corresponding_operation_remains']
    assert not scan['non_numeric_square_rows_for_manual_review']
    report={
      'passed':True,'task':'Independent verification of current bracket-preservation edit only; not previous average-number QA.',
      'source_records_checked':qn,'approved_question_count':41,'changed_question_keys':keys,
      'changed_math_field_count':len(field_evidence),'deduplicated_changed_row_expressions':len(row_evidence),
      'source_deduplicated_changed_row_expressions':len(row_evidence),'ppt_only_variant_count':len(ppt_only_evidence),'ppt_total_deduplicated_row_expressions':len(pairs),'ppt_only_variant_evidence':ppt_only_evidence,
      'approved_changes_sha256':SHA(APPROVED),
      'field_edits_only_round_or_square_bracket_characters':True,'all_numbers_operators_words_units_and_row_counts_unchanged':True,
      'all_question_prompts_original_formulas_diagrams_tables_conditions_unchanged':True,
      'source_question_changes_exactly_whitelist':True,'note_changes_whitelist':sorted(set(note_changes)),
      'exact_arithmetic':'Fraction over independently parsed arithmetic; decimal literals exact.',
      'field_change_evidence':field_evidence,'row_equivalence_evidence':row_evidence,
      'additional_original_display_sync_single_row_patches':len(sync_evidence),'display_sync_evidence':sync_evidence,
      'continuity_scan':scan,
      'manual_law_exceptions':[
        {'key':'p015_s07','reason':'Once multiplication distributes the whole [100+15] into 34*100+34*15, the original grouped sum is expanded; retaining square brackets around a surviving sum is no longer applicable.'},
        {'key':'p044_s04','reason':'[275+500]/25 may become275/25+500/25 by division of a sum; that is a genuine law expansion, not early replacement of [] by ().'},
        {'key':'p091_s03','reason':'The independent note begins with100-(100*8-784)/8 and has no previous square bracket to carry; it is left as an independent original round grouping.'},
        {'key':'p101_s02','reason':'Only one combined formula is given, so no continuation row replaces the existing square grouping.'},
      ],
      'source_files_sha256':{n:SHA(P/n) for n in current},
      'baseline_snapshot_sha256':SHA(basepath),
      'pdf_layout_tested_in_this_report':False,'native_powerpoint_playback_tested':False,
    }
    W(Q/'qa_math_independent.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ['source_files_sha256','field_change_evidence','row_equivalence_evidence']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
