from pathlib import Path
from fractions import Fraction
from decimal import Decimal, localcontext
import json,re,ast
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'ppt_builder/oral_calculations.json'


def num(v):
    if not isinstance(v,Fraction):v=Fraction(v)
    if v.denominator==1:return str(v.numerator)
    d=v.denominator
    for p in (2,5):
        while d%p==0:d//=p
    if d!=1:return r'\frac{'+str(v.numerator)+'}{'+str(v.denominator)+'}'
    with localcontext() as ctx:
        ctx.prec=40;s=format(Decimal(v.numerator)/Decimal(v.denominator),'f')
    return s.rstrip('0').rstrip('.') if '.' in s else s


def evaluate(tex):
    s=tex.strip().replace('−','-').replace('×','*').replace('÷','/')
    for a,b in [(r'\times','*'),(r'\div','/'),(r'\left',''),(r'\right',''),(r'\,',''),(r'\;','')]:s=s.replace(a,b)
    s=s.replace('[','(').replace(']',')').replace('{','(').replace('}',')')
    s=re.sub(r'\s+','',s)
    if re.search(r'[^0-9.+*/()\-]',s):raise ValueError('Unparsed expression '+tex)
    tree=ast.parse(s,mode='eval')
    def ev(n):
        if isinstance(n,ast.Expression):return ev(n.body)
        if isinstance(n,ast.Constant):return Fraction(ast.get_source_segment(s,n))
        if isinstance(n,ast.UnaryOp):return ev(n.operand)*(-1 if isinstance(n.op,ast.USub) else 1)
        if isinstance(n,ast.BinOp):
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            if isinstance(n.op,ast.Div):return a/b
        raise ValueError('Unsafe AST')
    return ev(tree)

class Node:
    def __init__(self,kind,value=None,left=None,right=None):self.kind=kind;self.value=value;self.left=left;self.right=right
    def clone(self):return Node(self.kind,self.value,self.left.clone() if self.left else None,self.right.clone() if self.right else None)

class Parser:
    def __init__(self,tex):
        s=tex.replace(r'\times','*').replace(r'\div','/').replace('×','*').replace('÷','/').replace('[','(').replace(']',')')
        self.t=re.findall(r'\d+(?:\.\d+)?|[()+*/-]',s);self.i=0
        if ''.join(self.t)!=re.sub(r'\s+','',s):raise ValueError('Token mismatch '+tex)
    def expression(self,prec=0):
        if self.i>=len(self.t):raise ValueError('missing operand')
        t=self.t[self.i];self.i+=1
        if t=='(':
            node=Node('group',left=self.expression())
            if self.t[self.i]!=')':raise ValueError('parenthesis')
            self.i+=1
        else:node=Node('number',Fraction(t))
        while self.i<len(self.t) and self.t[self.i]!=')':
            op=self.t[self.i];p=2 if op in '*/' else 1
            if p<=prec:break
            self.i+=1;node=Node(op,left=node,right=self.expression(p))
        return node
    def parse(self):
        n=self.expression()
        if self.i!=len(self.t):raise ValueError('leftover tokens')
        return n


def texnode(n):
    if n.kind=='number':return num(n.value)
    if n.kind=='group':return texnode(n.left) if n.left.kind=='number' else '('+texnode(n.left)+')'
    return texnode(n.left)+{'*':r'\times','/':r'\div','+':'+','-':'-'}[n.kind]+texnode(n.right)


def has_group(n):
    if n.kind=='group' and n.left.kind!='number':return True
    return bool(n.left and has_group(n.left)) or bool(n.right and has_group(n.right))


def strip_groups(n):
    if n.kind=='group' and n.left.kind=='number':return n.left
    if n.left:n.left=strip_groups(n.left)
    if n.right:n.right=strip_groups(n.right)
    return n


def has_ready(n,ops):
    if n.kind in ops and n.left.kind=='number' and n.right.kind=='number':return True
    return bool(n.left and has_ready(n.left,ops)) or bool(n.right and has_ready(n.right,ops))


def reduce_ordinary(n):
    n=strip_groups(n)
    if has_group(n):
        def groups(x):
            if x.kind=='group':x.left=reduce_ordinary(x.left);return strip_groups(x)
            if x.left:x.left=groups(x.left)
            if x.right:x.right=groups(x.right)
            return x
        return groups(n)
    ops='*/' if has_ready(n,'*/') else '+-'
    def walk(x):
        if x.kind in ops and x.left.kind=='number' and x.right.kind=='number':
            return Node('number',evaluate(texnode(x)))
        if x.left:x.left=walk(x.left)
        if x.right:x.right=walk(x.right)
        return x
    return strip_groups(walk(n))


def ordinary_steps(expr):
    n=Parser(expr).parse();steps=[expr]
    for _ in range(30):
        if n.kind=='number':break
        n=reduce_ordinary(n);t=texnode(n)
        if t!=steps[-1]:steps.append(t)
    if n.kind!='number':raise ValueError('cannot reduce '+expr)
    if steps[-1]!=num(evaluate(expr)):raise ValueError('final mismatch '+expr)
    return steps

# Purposeful mental-calculation structures, keeping elementary steps visible.
# Each row is independently checked by exact arithmetic below.
OVERRIDES={
 r'84\div4':([r'84\div4',r'(80+4)\div4',r'80\div4+4\div4','20+1','21'],'把84分成80和4，分别求商后相加。'),
 r'23\times3':([r'23\times3',r'20\times3+3\times3','60+9','69'],'23由2个十和3个一组成，两部分分别乘3，再相加。'),
 r'360\times4':([r'360\times4',r'36\times4\times10',r'144\times10','1440'],'先算36乘4，再把所得的144扩大10倍。'),
 r'163-45':(['163-45','163-40-5','123-5','118'],'把45分成40和5，先减40，再减5。'),
 r'103-74':(['103-74','103-70-4','33-4','29'],'把74分成70和4，依次减去。'),
 r'188+423':(['188+423','188+400+23','588+23','611'],'先加423中的400，再加23。'),
 r'50\times18':([r'50\times18',r'5\times18\times10',r'90\times10','900'],'先算5乘18，再乘10。'),
 r'67\times5':([r'67\times5',r'67\times10\div2',r'670\div2','335'],'乘5可以先乘10，再取所得数的一半。'),
 r'34\times5':([r'34\times5',r'30\times5+4\times5','150+20','170'],'把34分成30和4，两个乘法在同一步算完后相加。'),
 r'564+39':(['564+39','564+40-1','604-1','603'],'39比40少1，先加40，再减去多加的1。'),
 r'105\times21':([r'105\times21',r'105\times(20+1)',r'105\times20+105\times1','2100+105','2205'],'把21分成20和1，分别相乘后相加。'),
 r'703\div19':([r'703\div19',r'(570+133)\div19',r'570\div19+133\div19','30+7','37'],'19乘30得570，19乘7得133，合起来正好是703，所以商是30加7。'),
 r'24\times18':([r'24\times18',r'24\times(20-2)',r'24\times20-24\times2','480-48','432'],'把18看作20减2，运用乘法分配律，先多算2个24再减去。'),
 r'327+25':(['327+25','327+20+5','347+5','352'],'先加20，再加5。'),
 r'605-37':(['605-37','605-30-7','575-7','568'],'把37分成30和7，依次减去。'),
 r'5\times7\times4':([r'5\times7\times4',r'(5\times4)\times7',r'20\times7','140'],'运用乘法交换律和结合律，先让5与4凑成20。'),
 r'25\times6\times4':([r'25\times6\times4',r'(25\times4)\times6',r'100\times6','600'],'先让25与4凑成100，再乘6。'),
 r'123-97':(['123-97','123-100+3','23+3','26'],'97比100少3，先减100，再把多减的3加回来。'),
 r'6\times4\div4\times6':([r'6\times4\div4\times6',r'6\times6','36'],'先乘4再除以4，数值不变；剩下6乘6。'),
 r'136-45-55':(['136-45-55','136-(45+55)','136-100','36'],'两个减数45与55先凑成100，减法的性质使计算更简便。'),
 r'200\div25\div2':([r'200\div25\div2',r'200\div(25\times2)',r'200\div50','4'],'连续除以25和2，可以除以它们的积50。'),
 r'101\times12':([r'101\times12',r'(100+1)\times12',r'100\times12+1\times12','1200+12','1212'],'把101分成100和1，分别乘12，再相加。'),
 r'139+65-39':(['139+65-39','(139-39)+65','100+65','165'],'先用139减39凑成100，再加65。'),
 r'37\times99+37':([r'37\times99+37',r'37\times(99+1)',r'37\times100','3700'],'把后面的37看作37乘1，运用乘法分配律逆向提取37。'),
 r'25\times3\times4':([r'25\times3\times4',r'(25\times4)\times3',r'100\times3','300'],'先把25与4凑成100，再乘3。'),
 r'11\times20':([r'11\times20',r'11\times2\times10',r'22\times10','220'],'先算11乘2，再乘10。'),
 r'12\times9':([r'12\times9',r'12\times(10-1)',r'12\times10-12\times1','120-12','108'],'把9看作10减1，先算10个12，再减1个12。'),
 r'152\times4':([r'152\times4',r'150\times4+2\times4','600+8','608'],'把152分成150和2，分别乘4后相加。'),
 r'600\div25':([r'600\div25',r'(600\times4)\div(25\times4)',r'2400\div100','24'],'利用商不变的规律，被除数和除数同时乘4，除数凑成100。'),
 r'24\times5':([r'24\times5',r'24\times10\div2',r'240\div2','120'],'先乘10，再除以2，得到乘5的结果。'),
 r'1-0.36-0.64':(['1-0.36-0.64','1-(0.36+0.64)','1-1','0'],'两个减数0.36与0.64先凑成1。'),
 r'37\times2\times5':([r'37\times2\times5',r'37\times(2\times5)',r'37\times10','370'],'运用乘法结合律，先让2与5凑10。'),
 r'25\times101':([r'25\times101',r'25\times(100+1)',r'25\times100+25\times1','2500+25','2525'],'把101分成100和1，分别相乘后相加。'),
 r'278-32-18':(['278-32-18','278-(32+18)','278-50','228'],'两个减数32和18先凑成50。'),
 r'14\times60':([r'14\times60',r'14\times6\times10',r'84\times10','840'],'先算14乘6，再乘10。'),
 r'280\div5\div2':([r'280\div5\div2',r'280\div(5\times2)',r'280\div10','28'],'把两个除数5与2先相乘凑成10。'),
 r'35\times25\times4':([r'35\times25\times4',r'35\times(25\times4)',r'35\times100','3500'],'运用乘法结合律，先让25与4凑成100。'),
 r'2.4\times5':([r'2.4\times5',r'(24\times5)\div10',r'120\div10','12'],'2.4表示24个十分之一；5份共有24乘5，即120个十分之一，也就是12。'),
 r'1.25\times8':([r'1.25\times8',r'(125\times8)\div100',r'1000\div100','10'],'1.25表示125个百分之一；8份共有125乘8，即1000个百分之一，也就是10。这里只用整数乘法与小数点移动。'),
}


def strategy_and_steps(expr):
    if expr in OVERRIDES:return OVERRIDES[expr]
    steps=ordinary_steps(expr)
    n=Parser(expr).parse()
    # Read the actual operation tree before selecting a mental-calculation rule.
    # Parentheses take priority even when they contain multiplication/division.
    if has_group(n):
        return steps,'先算小括号内的运算，再算括号外的运算。'
    def operation_kinds(node):
        out={node.kind} if node.kind in ['+','-','*','/'] else set()
        if node.left:out.update(operation_kinds(node.left))
        if node.right:out.update(operation_kinds(node.right))
        return out
    ops=operation_kinds(n)
    if ops.intersection(['*','/']) and ops.intersection(['+','-']):
        return steps,'先算乘除，再算加减；同一步中独立的运算同时完成。'
    if n.kind in ['*','/'] and n.left.kind=='number' and n.right.kind=='number':
        a,b=n.left.value,n.right.value
        if n.kind=='*' and b in [10,100,1000]:
            p={10:1,100:2,1000:3}[b]
            if n.left.value.denominator==1 and '.' not in expr:
                return steps,f'整数乘{b}，在数的末尾添{p}个0。'
            return steps,f'乘{b}，小数点向右移动{p}位；位数不够时补0。'
        if n.kind=='/' and b in [10,100,1000]:
            p={10:1,100:2,1000:3}[b];return steps,f'除以{b}，小数点向左移动{p}位；位数不够时补0。'
        if n.kind=='*' and (a,b) in [(125,8),(4,25)]:return steps,'利用熟悉的凑整积直接口算。'
        if n.kind=='*' and (a,b)==(40,25):
            return [expr,r'4\times25\times10',r'100\times10','1000'],'先算4乘25得100，再乘10。'
        if n.kind=='/':return steps,f'用乘法想商：{num(b)}乘{steps[-1]}等于{num(a)}，因此商为{steps[-1]}。'
        return steps,'相同数位对应计算，利用已经熟悉的整数乘法口算。'
    if n.kind in ['+','-'] and n.left.kind=='number' and n.right.kind=='number':
        a,b=map(Decimal,[num(n.left.value),num(n.right.value)])
        p=max(-a.as_tuple().exponent,-b.as_tuple().exponent,0)
        if p:
            unit={1:'十分之一',2:'百分之一',3:'千分之一'}.get(p,f'小数点后第{p}位计数单位')
            ia,ib=int(a*10**p),int(b*10**p);ir=ia+ib if n.kind=='+' else ia-ib
            strategy=f'统一成{unit}来想：{ia}个{unit}'+('加' if n.kind=='+' else '减')+f'{ib}个{unit}，得{ir}个{unit}。'
            aa=format(a,f'.{p}f');bb=format(b,f'.{p}f')
            aligned=aa+n.kind+bb
            if aligned!=expr:steps=[expr,aligned,steps[-1]]
            return steps,strategy
        if n.kind=='+':return steps,'相同数位上的数相加；某位满十时向前一位进1。'
        return steps,'相同数位上的数相减；不够减时从前一位退1。'
    def power_of_ten_chain(node):
        if node.kind=='number':return True
        return (node.kind in ['*','/'] and node.right.kind=='number'
                and node.right.value in [10,100,1000]
                and power_of_ten_chain(node.left))
    if power_of_ten_chain(n):
        return steps,'按运算顺序依次移动小数点，前一步所得的数继续参与后一步计算。'
    return steps,'同级运算从左往右依次计算。'


def latex_for(sub):
    rows=['&'+sub['steps'][0]]
    for relation,step in zip(sub['relations'],sub['steps'][1:]):rows.append((r'\approx{}&' if relation=='≈' else '={}&')+step)
    heading=sub['display_label']
    return r'\textbf{'+heading+r'}\par '+sub['strategy']+r'\[\begin{aligned}'+r'\\'.join(rows)+r'\end{aligned}\]'


def extract(q):
    out=[]
    for block in re.findall(r'\\\((.*?)\\\)',q['question_latex'],re.S):
        for raw in re.split(r'\\(?:qquad|quad)\s*',block):
            raw=raw.strip()
            if not raw:continue
            approx=r'\approx' in raw
            expression=raw.split('=')[0].split(r'\approx')[0].strip().rstrip('\\').strip()
            if expression:out.append((expression,approx))
    return out


def main():
    records={};subcount=0;flagged=[]
    for f in sorted((ROOT/'questions').glob('p*.json')):
        for q in json.loads(f.read_text())['records']:
            if not any(t in q['question_latex'] for t in ['口算','直接写得数','直接写出得数','直接写出下面','直接写出']):continue
            expressions=extract(q)
            # An aggregated continuation keeps the original (5) through (8) numbering.
            start=1
            m=re.search(r'（(\d+)）',q['id'])
            if m:start=int(m[1])
            subs=[]
            for i,(expr,approx) in enumerate(expressions):
                exact=evaluate(expr);caution=None
                if approx:
                    if expr==r'49\times31':steps=[expr,r'50\times30','1500'];strategy='把49看作50、31看作30，先估成整十数再相乘。估算第一步用约等号，不能把1500当作精确积。'
                    elif expr==r'61\times95':steps=[expr,r'60\times100','6000'];strategy='把61看作60、95看作100，用接近的整十、整百数估算；估计值6000不是精确积。'
                    else:raise ValueError('Unplanned estimate '+expr)
                    relations=['≈','='];result=steps[-1]
                else:
                    steps,strategy=strategy_and_steps(expr);relations=['=']*(len(steps)-1);result=num(exact)
                if expr in [r'2.4\times5',r'1.25\times8']:
                    caution='原题含非10幂的小数乘法；本册未系统学习一般小数乘法。本解按计数单位转成整数乘法和除以10或100，不使用后续小数乘法竖式。'
                    flagged.append({'record_key':q['key'],'local_index':i+1,'expression':expr,'note':caution})
                for j,(rel,s) in enumerate(zip(relations,steps[1:]),1):
                    v=evaluate(s)
                    if rel=='=' and v!=evaluate(steps[j-1]):raise AssertionError((q['key'],expr,steps[j-1],s))
                if evaluate(steps[-1])!=exact and not approx:raise AssertionError('last result')
                label=f'（{start+i}）' if len(expressions)>1 else '口算思路'
                sub={'key':q['key']+f'_oral_{i+1:02}','local_index':i+1,'original_subquestion_number':start+i,'display_label':label,'expression_latex':expr,'is_estimate':approx,'exact_result':num(exact),'result':result,'steps':steps,'relations':relations,'strategy':strategy,'numeric_verified':True,'scope_note':caution}
                sub['answer_latex']=latex_for(sub);subs.append(sub)
            complete='\\par '.join(s['answer_latex'] for s in subs)
            records[q['key']]={'book_page':q['book_page'],'source_page':q['source_page'],'question_id':q['id'],'subquestions':subs,'replacement_answer_latex':complete,'original_answer_latex':q['answer_latex'],'replace_answer':True,'preserve_question':True,'aggregated':len(subs)>1}
            subcount+=len(subs)
    result={'schema_version':1,'records':records,'summary':{'records':len(records),'subquestions':subcount,'aggregated_records':sum(v['aggregated'] for v in records.values()),'aggregated_subquestions':sum(len(v['subquestions']) for v in records.values() if v['aggregated']),'estimate_subquestions':sum(s['is_estimate'] for v in records.values() for s in v['subquestions']),'scope_cautions':flagged},'scope':'All explicitly labelled oral/direct-answer calculations in the reviewed 108 pages. Statistical/average applications, column calculations, and designated written/simplified calculations are excluded. Exact rational validation covers every generated equality; approximation steps preserve ≈ and do not claim exact equality.'}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result['summary'],ensure_ascii=False))

if __name__=='__main__':main()
