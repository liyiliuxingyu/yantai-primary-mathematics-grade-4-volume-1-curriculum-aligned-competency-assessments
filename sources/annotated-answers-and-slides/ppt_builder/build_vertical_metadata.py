from pathlib import Path
from decimal import Decimal, localcontext
import json,re
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'ppt_builder/vertical_calculations.json'


def digits_cells(text, start=0):
    return [{'text':c,'column':start+i} for i,c in enumerate(str(text))]


def place_columns(int_digits, decimals):
    out=[]
    for i in range(int_digits):out.append({'column':i,'power10':int_digits-i-1,'kind':'digit'})
    if decimals:
        out.append({'column':int_digits,'kind':'decimal_point'})
        for i in range(decimals):out.append({'column':int_digits+1+i,'power10':-i-1,'kind':'digit'})
    return out


def addsub(a,b,op,role='answer',label=None,show_result=True):
    da,db=Decimal(a),Decimal(b)
    assert op in ['+','-']
    precision=max(max(0,-da.as_tuple().exponent),max(0,-db.as_tuple().exponent))
    res=da+db if op=='+' else da-db
    assert res>=0
    fmt=lambda v:format(v,f'.{precision}f')
    sa,sb,sr=fmt(da),fmt(db),fmt(res)
    ints=max(len(s.split('.')[0]) for s in [sa,sb,sr])
    count=ints+(precision+1 if precision else 0)
    def row(s,kind):
        pad=ints-len(s.split('.')[0]);return {'kind':kind,'value':s,'cells':digits_cells(s,pad)}
    rows=[row(sa,'operand'),row(sb,'operand')]
    rows[1]['cells'].insert(0,{'text':op,'column':-1})
    rows[1]['rule_after']={'start_column':-1,'end_column':count-1}
    if show_result:rows.append(row(sr,'result'))
    steps=[];carries=[];borrows=[]
    ia=list(map(int,sa.replace('.','').rjust(ints+precision,'0')))
    ib=list(map(int,sb.replace('.','').rjust(ints+precision,'0')))
    logical_to_column=[i if i<ints else i+1 for i in range(ints+precision)] if precision else list(range(ints))
    if op=='+':
        carry=0
        for i in reversed(range(len(ia))):
            total=ia[i]+ib[i]+carry;digit=total%10;newcarry=total//10
            steps.append({'column':logical_to_column[i],'digits':[ia[i],ib[i]],'carry_in':carry,'sum':total,'digit':digit,'carry_out':newcarry})
            if newcarry and i>0:carries.append({'column':logical_to_column[i-1],'text':str(newcarry)})
            carry=newcarry
    else:
        live=ia[:]
        for i in reversed(range(len(live))):
            before=live[i]
            if live[i]<ib[i]:
                j=i-1
                while j>=0 and live[j]==0:j-=1
                assert j>=0
                live[j]-=1
                mutations=[{'column':logical_to_column[j],'new_value':live[j]}]
                for k in range(j+1,i):live[k]=9;mutations.append({'column':logical_to_column[k],'new_value':9})
                live[i]+=10;mutations.append({'column':logical_to_column[i],'new_value':live[i]})
                borrows.append({'from_column':logical_to_column[j],'to_column':logical_to_column[i],'updates':mutations})
            steps.append({'column':logical_to_column[i],'minuend_digit_after_borrow':live[i],'subtrahend_digit':ib[i],'digit':live[i]-ib[i]})
    result={'op':op,'role':role,'operands':[a,b],'aligned_operands':[sa,sb],'result':sr,'column_count':count,'columns':place_columns(ints,precision),'rows':rows,'verification_steps':steps,'carry_marks':carries,'borrow_steps':borrows,'numeric_verified':True,'show_result':show_result}
    if precision:result['decimal_column']=ints
    if label:result['label']=label
    return result


def multiply(a,b,role='answer',label=None,show_result=True):
    assert str(a).isdigit() and str(b).isdigit()
    a,b=str(a),str(b);ai,bi=int(a),int(b);res=ai*bi
    n=max(len(a),len(b),len(str(res)))
    rows=[{'kind':'operand','value':a,'cells':digits_cells(a,n-len(a))},
          {'kind':'operand','value':b,'cells':[{'text':'×','column':-1}]+digits_cells(b,n-len(b)),'rule_after':{'start_column':-1,'end_column':n-1}}]
    partials=[]
    if len(b)>1:
        for power,ch in enumerate(reversed(b)):
            p=ai*int(ch);text=str(p);numeric=p*10**power
            row={'kind':'partial_product','value':text,'place_shift':power,'numeric_value':str(numeric),'multiplier_digit':ch,'cells':digits_cells(text,n-len(text)-power),'explanation':f'{a}×{ch}×10^{power}={numeric}'}
            rows.append(row);partials.append(numeric)
        rows[-1]['rule_after']={'start_column':-1,'end_column':n-1}
        assert sum(partials)==res
    if show_result:rows.append({'kind':'result','value':str(res),'cells':digits_cells(str(res),n-len(str(res)))})
    out={'op':'×','role':role,'operands':[a,b],'result':str(res),'column_count':n,'columns':place_columns(n,0),'rows':rows,'numeric_verified':True,'show_result':show_result,'partial_products':[str(v) for v in partials]}
    if label:out['label']=label
    return out


def divide(a,b,role='answer',label=None):
    assert str(a).isdigit() and str(b).isdigit()
    sa,sb=str(a),str(b);a,b=int(a),int(b);assert b>0
    q,r=divmod(a,b);n=len(sa);sq=str(q)
    qcells=digits_cells(sq,n-len(sq))
    rows=[{'kind':'quotient','value':sq,'cells':qcells},
          {'kind':'dividend_divisor','value':sa,'cells':digits_cells(sb,-len(sb)-1)+digits_cells(sa,0)}]
    work=0;started=False;steps=[]
    for i,ch in enumerate(sa):
        work=work*10+int(ch)
        if not started and work<b and i<n-1:continue
        started=True
        digit=work//b;product=digit*b;rem=work-product
        if len(rows)>2:
            display=str(work)
            rows.append({'kind':'partial_dividend','value':display,'brought_down_digit':ch,'cells':digits_cells(display,i-len(display)+1)})
        ps=str(product);start=i-len(str(work))+1
        rows.append({'kind':'trial_product','value':ps,'quotient_digit':str(digit),'quotient_column':i,'cells':digits_cells(ps,i-len(ps)+1),'rule_after':{'start_column':start,'end_column':i}})
        steps.append({'input_partial_dividend':work,'end_column':i,'quotient_digit':digit,'trial_product':product,'remainder':rem,'brought_down_digit':ch,'equation':f'{work}-{product}={rem}'})
        work=rem
    assert work==r
    rows.append({'kind':'remainder','value':str(r),'cells':digits_cells(str(r),n-len(str(r)))})
    assert b*q+r==a and 0<=r<b
    out={'op':'÷','role':role,'operands':[str(a),str(b)],'result':sq if not r else f'{q}…{r}','quotient':sq,'remainder':str(r),'column_count':n,'columns':place_columns(n,0),'rows':rows,'division_bracket':{'top_row':1,'left_column':0,'right_column':n-1,'bottom_row':2},'division_steps':steps,'numeric_verified':True,'check_equation':f'{b}×{q}+{r}={a}'}
    if label:out['label']=label
    return out


def main():
    records={}
    def add(key,calcs,**extra):
        records[key]={'calculations':calcs,'replace_array':True,**extra}
    for key,op,a,b in [
        ('p011_s02','×','114','23'),('p011_s03','÷','448','48'),('p011_s04','÷','372','62'),('p011_s05','÷','598','18'),
        ('p015_s01','×','258','13'),('p015_s02','÷','754','26'),('p015_s03','×','308','25'),('p015_s04','÷','552','69'),
        ('p090_s06','+','15.05','2.63'),('p090_s07','-','9.06','2.5'),('p090_s08','+','5.7','12.34'),
        ('p103_s04','+','9.27','15.9'),('p103_s05','+','25.7','16.4'),('p103_s06','-','10','4.03'),
        ('p107_s02','+','16.8','2.27'),('p107_s04','-','10.02','1.9')]:
        cal=multiply(a,b) if op=='×' else divide(a,b) if op=='÷' else addsub(a,b,op)
        add(key,[cal])
    add('p058_s09',[addsub('3.58','2.67','+',label='（1）'),addsub('4.6','12.95','+',label='（2）'),addsub('20.05','7.89','-',label='（3）'),addsub('50','16.34','-',label='（4）★'),addsub('33.66','16.34','+',label='（4）验算')])
    add('p063_s01',[addsub('8.7','12.36','+',label='（1）★'),addsub('21.06','12.36','-',label='（1）验算'),addsub('5.1','3.59','-',label='（2）'),addsub('12','2.25','-',label='（3）★'),addsub('9.75','2.25','+',label='（3）验算')])
    add('p090_s09',[addsub('12.8','1.24','-'),addsub('11.56','1.24','+',label='验算')])
    add('p094_s09',[addsub('12.4','2.76','+',label='（1）'),addsub('8.05','4.357','-',label='（2）'),multiply('28','304',label='（3）'),divide('6270','30',label='（4）')])
    add('p103_s07',[addsub('18.2','6.78','-'),addsub('11.42','6.78','+',label='验算')])
    add('p107_s03',[addsub('12','4.5','-'),addsub('7.5','4.5','+',label='验算')])
    add('p018_s03',[multiply('106','22',role='question')],replace_question_diagrams=['p018_s03_g1'],source_given_rows=True)
    records['p018_s03']['calculations'][0]['rows'][2]['annotation']='①'
    records['p018_s03']['calculations'][0]['rows'][3]['annotation']='②'
    add('p025_s02',[multiply('45','42',role='question')],replace_question_diagrams=['p025_s02_g1'],source_given_rows=True)
    c=addsub('34.95','2.5','+',role='question',show_result=False)
    # Keep the source's second addend as 2.5, not add a printed hundredth-place zero.
    c['rows'][1]['cells']=[x for x in c['rows'][1]['cells'] if x['column']!=c['column_count']-1]
    c['rows'][1]['value']='2.5';c['highlight']={'kind':'dashed_rectangle','from_column':c['decimal_column']+1,'to_column':c['decimal_column']+1,'from_row':0,'to_row':1}
    add('p062_s04',[c],replace_question_diagrams=['p062_vertical'],source_given_rows=True)
    # This question's printed partial products contain damaged glyphs. Preserve that
    # supplied original crop rather than silently replacing it with computed digits.
    add('p102_s02',[multiply('48','37',role='illustration',label='分配律竖式示意（原题字形仍保留）')],replace_array=False,retain_original_glyph=True,native_rebuild_of_original_allowed=False)
    all_records={q['key']:q for p in sorted((ROOT/'questions').glob('p*.json')) for q in json.loads(p.read_text())['records']}
    for key,item in records.items():
        q=all_records[key]
        item.update(book_page=q['book_page'],source_page=q['source_page'],question_id=q['id'])
        for i,calc in enumerate(item['calculations']):calc['id']=key+f'_vertical_{i+1:02}'
    included=set(records)
    excluded=[]
    for key,q in all_records.items():
        if '\\begin{array}' in q['answer_latex'] and key not in included:
            excluded.append({'key':key,'reason':'统计/枚举/口算结果矩阵，不是竖式，不应使用竖式专用布局'})
    result={'schema_version':1,'records':records,'summary':{'record_count':len(records),'calculation_count':sum(len(v['calculations']) for v in records.values()),'answer_calculation_count':sum(c['role']=='answer' for v in records.values() for c in v['calculations']),'numeric_verified_count':sum(c['numeric_verified'] for v in records.values() for c in v['calculations']),'excluded_non_vertical_arrays':excluded},'rendering_contract':{'column_unit':'same fixed horizontal pitch for every number digit; 0-based left-to-right; negative columns are legal for operation sign/divisor','row_unit':'one fixed row pitch, independent reveal by complete row','decimal_point':'is its own explicit cell, kept in decimal_column in every row','rules':'rule_after spans the stated columns; not emulated with underscore text','division_bracket':'top_row identifies dividend row; horizontal bar immediately above that row, rounded left cap between top_row and bottom_row; quotient is row 0, divisor uses negative columns','role':'question rows are visible with statement; answer rows reveal after analysis; illustration does not replace damaged source glyphs','source':'Question strings and original diagrams were inspected through reviewed structured records; ambiguous printed p102 glyphs remain original cropped image.'}}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result['summary'],ensure_ascii=False))

if __name__=='__main__':main()
