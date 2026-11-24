#!/usr/bin/env python3
"""Batch-compile mathematical/TikZ assets after the parent author marker.

All failed or missing assets are fatal and recorded. No scanned-page fallback.
"""
from __future__ import annotations
import argparse,hashlib,json,re,subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

def asset_id(kind,tex,color,points,preamble=''):
    return hashlib.sha256(json.dumps(['asset-v4-nowrap',kind,tex,color,points,preamble],ensure_ascii=False).encode()).hexdigest()[:24]

def collect_assets(data,points=32):
    assets={}
    def register(b):
        if b['type']=='math':
            color='000000' if b.get('role')=='question' else 'C00000'
            tex=b['latex'];key=asset_id('math',tex,color,points)
            assets.setdefault(key,{'id':key,'kind':'math','tex':tex,'color':color,'points':points});b['asset_id']=key
        elif b['type']=='slot':
            if b.get('answer'):register(b['answer'])
        elif b['type']=='paragraph':
            for r in b['runs']:register(r)
        elif b['type']=='table':
            # Tables are native editable objects. Their math runs are inserted
            # as OMML in cells; a vector image is not needed for each cell.
            for row in b['rows']:
                for cell in row:
                    if cell.get('final_slot'):register(cell['final_slot'])
            for runs in (b.get('title_runs',[])+b.get('footer_runs',[])):
                for r in runs:register(r)
            return
        elif b['type']=='diagram' and b.get('tikz'):
            diagram_points=float(b.get('source_font_points',12))
            source=b['tikz']
            if b.get('name','').startswith('p071_s02_animation_'):source=source.replace('node[below]{O}','node[below right]{O}')
            if b.get('background_shift'):
                dx,dy=b['background_shift'];scope=r'\begin{scope}[shift={('+str(dx)+','+str(dy)+')}]'
                source=re.sub(r'\\begin\{tikzpicture\}(?:\[[^\]]*\])?',lambda m:m.group()+scope,source,count=1).replace(r'\end{tikzpicture}',r'\end{scope}\end{tikzpicture}')
            if b.get('animation_bounds'):
                x0,y0,x1,y1=b['animation_bounds']
                # Expand the original picture to contain the whole motion,
                # without discarding the real TikZ extent.  In particular,
                # foreach/scoped glyph layouts cannot be inferred reliably by
                # searching only literal numeric coordinates in their source.
                bbox=r'\path[use as bounding box] ('+str(x0)+','+str(y0)+') rectangle ('+str(x1)+','+str(y1)+');'
                source=source.replace(r'\end{tikzpicture}',bbox+r'\end{tikzpicture}')
            pure_answers={'p031_s15_g1','p047_s04_a1','p083_s04_g1','p100_s04_g1'}
            diagram_color='C00000' if b.get('name') in pure_answers else '000000'
            key=asset_id('tikz',source,diagram_color,diagram_points,b.get('preamble',''))
            assets.setdefault(key,{'id':key,'kind':'tikz','tex':source,'color':diagram_color,'points':diagram_points,'preamble':b.get('preamble','')});b['asset_id']=key
            if b.get('animation',{}).get('grid') and not b['animation']['grid'].get('dotted') and b['animation'].get('type') not in ('altitude','perpendicular','perpendicular_shortest_path'):
                spec=b['animation'];assets[key]['svg_grid']=spec['grid'];initial=(spec.get('object_paths') or ([spec['object_points']] if spec.get('object_points') else []))+spec.get('additional_paths',[])
                for obj in spec.get('objects',[]):initial.extend([obj['points']]+obj.get('additional_paths',[]))
                for path in initial:
                    if path not in assets[key].setdefault('known_initial_paths',[]):assets[key]['known_initial_paths'].append(path)
            name=b.get('name','')
            if name in ('p066_s04_animation_0','p066_s05_animation_0'):
                assets[key]['svg_grid_instance']=1
            if name in ('p066_s02_animation_0','p066_s03_animation_0'):assets[key]['known_rect']=[[0,0],[8,1.8]]
            elif name=='p070_s02_animation_0':assets[key]['known_rect']=[[-.45,0],[0,4.5]]
            elif name in ('p072_s01_animation_0','p072_s02_animation_0'):
                assets[key]['known_rect']=[[0,0],[2,2]];assets[key]['known_rect_instance']=0;assets[key]['known_rect_reference']='图①完整2×2框；其他复制位置使用原图全局坐标'
                origin=[3.5,1.5] if name=='p072_s01_animation_0' else [6.5,1.5]
                assets[key]['known_initial_paths']=[[[p[0]+origin[0],p[1]+origin[1]] for p in path] for path in b['animation']['object_paths']]
                assets[key]['initial_path_relation']='黑色已知模板核对；红色副本在待填格内出现后按指定角度旋转'
            elif name=='p069_s04_animation_0':assets[key]['known_circle']={'center':[0,-.55],'radius':.6}
            elif name=='p070_s07_animation_0':
                axis=b['animation']['axis'];assets[key]['known_line']=[axis.get('p1'),axis.get('p2')] if isinstance(axis,dict) else axis;assets[key]['known_line_style']='dashed'
            elif name=='p095_s05_animation_1':assets[key]['known_dot_grid']={'x_min':0,'x_max':11,'y_min':0,'y_max':5,'count':72}
            if b.get('name','').startswith('p071_s02_animation_'):
                shift=b.get('animation',{}).get('placement') or [0,0];assets[key]['known_line']=[[p[0]+shift[0],p[1]+shift[1]] for p in b['animation']['object_points']]
        elif b['type']=='diagram' and b.get('glyph_image'):
            from PIL import Image
            p=Path(b['glyph_image']);digest=hashlib.sha256(p.read_bytes()).hexdigest();key=asset_id('glyph_image',digest,'000000',points)
            with Image.open(p) as im:w,h=im.size
            assets.setdefault(key,{'id':key,'kind':'glyph_image','image_path':str(p),'width_px':w,'height_px':h});b['asset_id']=key
        elif b['type']=='diagram' and b.get('glyph_svg'):
            p=Path(b['glyph_svg']);w,h=svg_size(p);key=asset_id('glyph_svg',hashlib.sha256(p.read_bytes()).hexdigest(),'000000',points)
            assets.setdefault(key,{'id':key,'kind':'glyph_svg','svg_path':str(p),'width_px':w,'height_px':h});b['asset_id']=key
    for r in data['records']:
        for b in r['blocks']:register(b)
    return assets

def svg_size(path):
    svg=ET.parse(path).getroot();vb=[float(x) for x in svg.get('viewBox','').split()]
    def px(value,fallback):
        if not value:return fallback
        m=re.fullmatch(r'([0-9.eE+-]+)(pt|px|mm|cm|in)?',value)
        if not m:raise ValueError('未知 SVG 尺寸 '+value)
        return float(m[1])*{'pt':96/72,'px':1,'mm':96/25.4,'cm':96/2.54,'in':96,None:1}[m[2]]
    return px(svg.get('width'),vb[2] if vb else 0),px(svg.get('height'),vb[3] if vb else 0)

def compile_batch(batch,folder,font_path):
    tex_path=folder/'batch.tex'
    # The supplied source font avoids depending on a missing ctex installation.
    fontdir=font_path.parent.as_posix()+'/'
    preamble=r'''\documentclass{article}
\usepackage{fix-cm,fontspec,amsmath,amssymb,xcolor,tikz}
\DeclareMathSizes{32}{32}{24}{18}
\usetikzlibrary{calc,arrows.meta,angles,quotes,positioning,patterns,decorations.pathreplacing,matrix,fit}
\usepackage[active,tightpage]{preview}
\setlength\PreviewBorder{1pt}
\pagestyle{empty}
'''+ '\\setmainfont{'+font_path.name+'}[Path={'+fontdir+'}]\n'
    preamble+='\n'.join(sorted({a.get('preamble','') for a in batch if a.get('preamble')}))+'\n\\begin{document}\n'
    pages=[]
    for a in batch:
        content=(r'\hbox{$\displaystyle '+a['tex']+r'$}') if a['kind']=='math' else a['tex']
        pages.append(r'\begin{preview}{\fontsize{'+str(a['points'])+'pt}{'+str(a['points']*1.25)+r'pt}\selectfont\color[HTML]{'+a['color']+'}'+content+r'}\end{preview}')
    tex_path.write_text(preamble+'\n'.join(pages)+'\n\\end{document}\n')
    run=subprocess.run(['xelatex','-interaction=nonstopmode','-halt-on-error','-no-shell-escape','-output-directory',str(folder),str(tex_path)],capture_output=True,text=True,timeout=180)
    (folder/'compile.stdout.txt').write_text(run.stdout+run.stderr)
    if run.returncode or 'Missing character' in run.stdout:raise RuntimeError('资产批量编译失败或缺字，见 '+str(folder/'compile.stdout.txt'))
    for n,a in enumerate(batch,1):
        dest=folder.parent/(a['id']+'.svg')
        result=subprocess.run(['pdftocairo','-svg','-f',str(n),'-l',str(n),str(folder/'batch.pdf'),str(dest)],capture_output=True,text=True,timeout=30)
        if result.returncode or not dest.exists():raise RuntimeError('SVG 导出失败 '+a['id']+': '+result.stderr)
        # Cairo writes point coordinates without unit suffixes. Preserve the
        # PDF physical size explicitly rather than interpreting points as px.
        svg=dest.read_text()
        svg=re.sub(r'(<svg\b[^>]*?\bwidth=")([0-9.]+)(")',r'\g<1>\2pt\3',svg,count=1)
        svg=re.sub(r'(<svg\b[^>]*?\bheight=")([0-9.]+)(")',r'\g<1>\2pt\3',svg,count=1)
        dest.write_text(svg)
        width,height=svg_size(dest)
        if width<=0 or height<=0:raise ValueError('空白尺寸资产 '+a['id'])
        a.update(svg_path=str(dest),width_px=width,height_px=height)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--normalized',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--font',type=Path,required=True);ap.add_argument('--batch-size',type=int,default=200);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();d=json.loads(args.normalized.read_text())
    if d.get('error_count'):raise SystemExit('预检错误尚未解决，拒绝编译')
    if not args.font.is_file():raise SystemExit('指定字体文件不存在')
    args.directory.mkdir(parents=True,exist_ok=True);assets=collect_assets(d)
    pending=[]
    for a in assets.values():
        if a['kind'] in ('glyph_image','glyph_svg'):continue
        p=args.directory/(a['id']+'.svg')
        if p.exists():
            try:w,h=svg_size(p);a.update(svg_path=str(p),width_px=w,height_px=h)
            except (ET.ParseError,ValueError):p.unlink();pending.append(a)
        else:pending.append(a)
    for i in range(0,len(pending),args.batch_size):
        batch=pending[i:i+args.batch_size];digest=hashlib.sha256(''.join(a['id'] for a in batch).encode()).hexdigest()[:10]
        folder=args.directory/f'batch_{i//args.batch_size:03d}_{digest}';folder.mkdir(exist_ok=True)
        compile_batch(batch,folder,args.font)
    for a in assets.values():
        if a.get('svg_grid'):
            root=ET.parse(a['svg_path']).getroot();g=a['svg_grid'];candidates=[]
            for path in root.iter('{http://www.w3.org/2000/svg}path'):
                color=path.get('stroke','');channels=re.findall(r'([0-9.]+)%',color)
                if len(channels)!=3 or len(set(channels))!=1:continue
                segments=re.findall(r'M\s*([-0-9.eE]+)\s+([-0-9.eE]+)\s+L\s*([-0-9.eE]+)\s+([-0-9.eE]+)',path.get('d',''))
                if len(segments)<4:continue
                t=re.fullmatch(r'matrix\(([^)]+)\)',path.get('transform',''));matrix=list(map(float,re.split(r'[, ]+',t[1].strip()))) if t else [1,0,0,1,0,0]
                aa,bb,cc,dd,ee,ff=matrix;groups={}
                for seg in segments:
                    x,y,z,w=map(float,seg);u=[aa*x+cc*y+ee,bb*x+dd*y+ff];v=[aa*z+cc*w+ee,bb*z+dd*w+ff]
                    if abs(u[1]-v[1])>.003 or abs(u[0]-v[0])<.1:continue
                    x0,x1=sorted([u[0],v[0]]);key=(round(x0,2),round(x1,2));groups.setdefault(key,[]).append((x0,x1,(u[1]+v[1])/2))
                for group in groups.values():
                    ys=sorted({round(p[2],3) for p in group});required=round((g['y_max']-g['y_min'])/g.get('step',1))+1
                    if len(ys)<required:continue
                    x0=sum(p[0] for p in group)/len(group);x1=sum(p[1] for p in group)/len(group);y0,y1=ys[0],ys[-1]
                    sx=(x1-x0)/(g['x_max']-g['x_min']);sy=-(y1-y0)/(g['y_max']-g['y_min'])
                    if sx<=0 or abs(sx/(-sy)-1)>.005:continue
                    candidates.append((sx,sy,x0-sx*g['x_min'],y1-sy*g['y_min'],[x0,y0,x1,y1],len(ys)))
            if not candidates:raise ValueError('Missing actual SVG grid calibration: '+a['id'])
            unique=[]
            for candidate in sorted(candidates,key=lambda c:(c[4][0],c[4][1])):
                if not any(max(abs(x-y) for x,y in zip(candidate[4],q[4]))<.02 for q in unique):unique.append(candidate)
            index=a.get('svg_grid_instance',0)
            if index>=len(unique):raise ValueError('Requested SVG grid instance not found '+a['id'])
            if len(unique)>1 and 'svg_grid_instance' not in a:raise ValueError('Ambiguous multiple SVG grids require explicit instance '+a['id'])
            sx,sy,ox,oy,bbox,linecount=unique[index];a['svg_affine']={'method':'actual_svg_grid_lines','sx':sx,'sy':sy,'ox':ox,'oy':oy,'viewbox':list(map(float,root.get('viewBox').split())),'grid_svg_bbox':bbox,'grid_math':g,'horizontal_line_count':linecount,'matching_grid_instances':len(unique),'selected_grid_instance':index,'grid_instance_selection':'explicit_right_diagram' if index==1 else 'unique_matching_grid','candidate_grid_svg_bboxes':[q[4] for q in unique]}
        elif a.get('known_rect') or a.get('known_circle') or a.get('known_dot_grid'):
            root=ET.parse(a['svg_path']).getroot();candidates=[]
            for path in root.iter('{http://www.w3.org/2000/svg}path'):
                dpath=path.get('d','');is_circle='C' in dpath and 'Z' in dpath
                if a.get('known_dot_grid'):
                    if not is_circle or path.get('fill')!='rgb(0%, 0%, 0%)':continue
                elif not path.get('stroke'):continue
                if a.get('known_circle') and not is_circle:continue
                if a.get('known_rect') and (is_circle or 'Z' not in dpath):continue
                nums=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',dpath)));pts=list(map(list,zip(nums[::2],nums[1::2])))
                t=re.fullmatch(r'matrix\(([^)]+)\)',path.get('transform',''))
                if t:
                    aa,bb,cc,dd,ee,ff=map(float,re.split(r'[, ]+',t[1].strip()));pts=[[aa*x+cc*y+ee,bb*x+dd*y+ff] for x,y in pts]
                if not pts:continue
                x0=min(p[0] for p in pts);x1=max(p[0] for p in pts);y0=min(p[1] for p in pts);y1=max(p[1] for p in pts)
                if min(x1-x0,y1-y0)<=0:continue
                if a.get('known_rect'):
                    lo,hi=a['known_rect'];ratio=abs((hi[0]-lo[0])/(hi[1]-lo[1]))
                    if abs((x1-x0)/(y1-y0)/ratio-1)>.01:continue
                elif abs((x1-x0)/(y1-y0)-1)>.01:continue
                candidates.append([x0,y0,x1,y1])
            if not candidates:raise ValueError('Missing actual SVG frame/circle/dots: '+a['id'])
            if a.get('known_dot_grid'):
                from collections import Counter
                radii=Counter(round((x1-x0+y1-y0)/2/.05)*.05 for x0,y0,x1,y1 in candidates);radius,count=radii.most_common(1)[0]
                dots=[[(x0+x1)/2,(y0+y1)/2] for x0,y0,x1,y1 in candidates if abs((x1-x0+y1-y0)/2-radius)<.026];g=a['known_dot_grid']
                if len(dots)!=g['count']:raise ValueError('Dot grid count mismatch '+a['id']+' '+str(len(dots)))
                x0=min(p[0] for p in dots);x1=max(p[0] for p in dots);y0=min(p[1] for p in dots);y1=max(p[1] for p in dots);sx=(x1-x0)/(g['x_max']-g['x_min']);sy=-(y1-y0)/(g['y_max']-g['y_min']);ox=x0-sx*g['x_min'];oy=y1-sy*g['y_min'];method='actual_svg_dot_lattice'
            elif a.get('known_rect'):
                candidates=sorted(candidates,key=lambda c:(c[0],c[1]));index=a.get('known_rect_instance',0)
                if len(candidates)>1 and 'known_rect_instance' not in a:raise ValueError('Ambiguous SVG reference frames require explicit instance '+a['id'])
                x0,y0,x1,y1=candidates[index];lo,hi=a['known_rect'];sx=(x1-x0)/(hi[0]-lo[0]);sy=-(y1-y0)/(hi[1]-lo[1]);ox=x0-sx*lo[0];oy=y1-sy*lo[1];method='actual_svg_known_frame'
            else:
                if len(candidates)!=1:raise ValueError('Ambiguous SVG dial circles require explicit reference '+a['id'])
                x0,y0,x1,y1=candidates[0];c=a['known_circle'];sx=(x1-x0+y1-y0)/(4*c['radius']);sy=-sx;ox=(x0+x1)/2-sx*c['center'][0];oy=(y0+y1)/2-sy*c['center'][1];method='actual_svg_known_dial_circle'
            a['svg_affine']={'method':method,'sx':sx,'sy':sy,'ox':ox,'oy':oy,'viewbox':list(map(float,root.get('viewBox').split())),'actual_svg_bbox':[x0,y0,x1,y1],'matching_anchor_instances':1 if a.get('known_dot_grid') else len(candidates),'selected_anchor_instance':a.get('known_rect_instance',0),'anchor_selection_basis':'72个已知点整体点阵' if a.get('known_dot_grid') else a.get('known_rect_reference','唯一匹配的已知框/钟面圆'),'candidate_anchor_svg_bboxes':candidates if not a.get('known_dot_grid') else [[x0,y0,x1,y1]]}
        elif a.get('known_line'):
            root=ET.parse(a['svg_path']).getroot();matches=[]
            for path in root.iter('{http://www.w3.org/2000/svg}path'):
                if not path.get('stroke') or (a.get('known_line_style')=='dashed' and not path.get('stroke-dasharray')):continue
                nums=re.fullmatch(r'M\s*([-0-9.eE]+)\s+([-0-9.eE]+)\s+L\s*([-0-9.eE]+)\s+([-0-9.eE]+)\s*',path.get('d',''))
                if not nums:continue
                pts=[list(map(float,nums.groups()[:2])),list(map(float,nums.groups()[2:]))];t=re.fullmatch(r'matrix\(([^)]+)\)',path.get('transform',''))
                if t:
                    aa,bb,cc,dd,ee,ff=map(float,re.split(r'[, ]+',t[1].strip()));pts=[[aa*x+cc*y+ee,bb*x+dd*y+ff] for x,y in pts]
                matches.append(pts)
            if len(matches)!=1:raise ValueError('背景已知AB线校准不唯一')
            p,q=a['known_line'];u,v=matches[0];scale=(v[0]-u[0])/(q[0]-p[0]) if q[0]!=p[0] else -(v[1]-u[1])/(q[1]-p[1]);view=list(map(float,root.get('viewBox').split()))
            a['svg_affine']={'method':'actual_svg_known_line','sx':scale,'sy':-scale,'ox':u[0]-scale*p[0],'oy':u[1]+scale*p[1],'viewbox':view,'known_line_svg':matches[0],'known_line_math':a['known_line'],'matching_anchor_instances':len(matches),'selected_anchor_instance':0,'anchor_selection_basis':'唯一给定的AB或指定对称轴端点'}
    d['assets']=assets;args.out.write_text(json.dumps(d,ensure_ascii=False,indent=2))
    print(json.dumps({'assets':len(assets),'newly_compiled':len(pending),'records':len(d['records'])}))
if __name__=='__main__':main()
