from pathlib import Path
import json,hashlib,subprocess,os,shutil
R=Path(__file__).resolve().parent.parent;O=R/'diagram_source';O.mkdir(exist_ok=True)
points=[[(813.889,1112.333),(819.5,1116.5),(813,1124),(824,1125)],[(807.3,1134.7),(797.36,1138.09),(808.67,1141.11),(815.11,1148.33)],[(781.5,1154.14),(792.73,1155.82),(790.12,1162.12),(783.82,1169.82)],[(777.8,1178.5),(813.64,1183.45),(788,1185),(805.09,1190.36)]]
lines=[(.0474000264,1067.93884),(.0594914898,1081.97508),(.0612558034,1104.09213),(.073328135,1118.38667),(.07471954,1141.14903)]
coordinates=[];days=[]
for i,ps in enumerate(points):
 p=[]
 for x,y in ps:
  xr=808.5-.035*(y-1106.19066);dx=x-xr
  a,b=lines[i];c,d=lines[i+1];top=a*x+b;bot=c*x+d;v=4-i-(y-top)/(bot-top)
  coordinates.append((dx/20,v));p.append({'source_pixel_center':[x,y],'local_reference_x_pixel':xr,'horizontal_offset_pixel':dx,'tikz_position':[round(dx/20,4),round(v,4)]})
 days.append({'day':i+1,'point_count':4,'points':p,'mean_horizontal_offset_pixel':sum(t['horizontal_offset_pixel']for t in p)/4,'interpretation':['四点均在虚线右侧，平均气温高于22℃。','一左、一点在虚线附近、两右；右侧多出的距离合起来约等于左侧不足的距离，平均约22℃。','四点均在虚线左侧，平均气温低于22℃。','两点明显在左，一点在虚线附近，一点在右；左侧不足的距离明显更多，平均低于22℃。'][i]})
header='% 由原书第78页清晰照片重绘；TikZ坐标只是排版坐标，不是新增温度值。\n% 五条横边界分成四个日带；每带四点。仅22摄氏度为已知标记。\n'
tikz=header+r'''\begin{tikzpicture}[x=.495cm,y=.60cm,font=\fontsize{10.5}{12.5}\selectfont,line width=.45pt]
  \foreach \y in {0,1,2,3,4}{\draw (-5,\y)--(2,\y);}
  \draw (-5,-.12)--(-5,4.16);
  \foreach \y/\lab in {3.5/第一天,2.5/第二天,1.5/第三天,.5/第四天}{
    \node[anchor=east,inner sep=3pt] at (-5,\y) {\lab};
  }
  \draw[dashed,dash pattern=on 2.4pt off 2.4pt] (0,-.18)--(0,4.28);
  \node[above,inner sep=2pt,font=\fontsize{9.5}{11.5}\selectfont] at (0,4.28) {$22^\circ\mathrm{C}$};
'''
for i in range(4):
 tikz+='  % 第'+str(i+1)+'天：四个点\n'
 for x,y in coordinates[i*4:(i+1)*4]:tikz+=f'  \\fill ({x:.4f},{y:.4f}) circle[radius=1.5pt];\n'
tikz+='\\end{tikzpicture}\n'
(O/'p078_temperatures_photo.tikz').write_text(tikz)
fonts=O/'fonts';fonts.mkdir(exist_ok=True)
shutil.copy2(R/'project/fonts/DroidSansFallback.ttf',fonts/'DroidSansFallback.ttf')
tex=r'''\documentclass[tikz,border=3pt]{standalone}
\usepackage{fontspec}
\setmainfont{DroidSansFallback.ttf}[Path=fonts/]
\begin{document}
\input{p078_temperatures_photo.tikz}
\end{document}
'''
(O/'p078_temperatures_photo.tex').write_text(tex)
env=os.environ.copy();env['TEXMF']='{/usr/share/texlive/texmf-dist,/usr/share/texmf}'
process=subprocess.run(['xelatex','-fmt=./xelatex.fmt','-interaction=nonstopmode','-halt-on-error','p078_temperatures_photo.tex'],cwd=O,capture_output=True,text=True,env=env)
(O/'compile_stdout.txt').write_text(process.stdout+'\n'+process.stderr)
assert process.returncode==0,process.stdout[-3000:]
import fitz
pdf=O/'p078_temperatures_photo.pdf'
with fitz.open(pdf)as doc:
 assert len(doc)==1 and not doc[0].get_images()
 doc[0].get_pixmap(matrix=fitz.Matrix(3,3)).save(O/'p078_temperatures_photo.png')
 (O/'p078_temperatures_photo.svg').write_text(doc[0].get_svg_image(text_as_path=True))
 shape_count=len(doc[0].get_drawings());box=list(doc[0].rect)
review={'question_key':'p078_s05','book_page':78,'question_id':'二、5','source_photo':'upload/01-image-1793934362476.jpg','source_photo_sha256':hashlib.sha256((R.parent/'upload/01-image-1793934362476.jpg').read_bytes()).hexdigest(),'answer':'B','answer_text':'第二天','reason':'原图确为五条水平边界线围出四个日带，每天四个散点。22℃竖虚线作为基准，比较四点在其左右的距离；第二天左右偏差总量约相抵，平均约22℃。','primary_explanation':'以22℃为基准，把高于22℃的部分移给低于22℃的部分。第二天两个右侧点多出的部分，约能补足左侧那个点不足的部分；另一个点已在22℃附近，所以移多补少后四次气温都大约是22℃。因此选B。','horizontal_boundaries':5,'day_bands':4,'point_count':16,'vertical_reference':'22℃，竖虚线','days':days,'methodology':{'pixel_centers':'从原照片的暗点连通区域读取近似中心；源像素坐标只用于复原左右相对距离，不等同于温度刻度。','horizontal_correction':'按竖虚线随透视的轻微倾斜校正，每点减去同高的虚线横坐标，再按同一比例排版。','vertical_correction':'以各点所在日带的上下两条印刷边界线作局部校正，保持点在日带中的相对高度。','source_line_fits_xy':lines,'reference_fit_x_from_y':'x_ref=808.5−0.035×(y−1106.19066)，单位为原照片像素，仅复原参考线，不是温度换算。','tikz_units':'横坐标每单位对应20个校正后的照片像素；不解释为摄氏度。','near_axis_points':'第二天首点及第四天末点在虚线附近，扫描误差不足半个像素，不据此编造精确读数。'},'uncertainties':['原图没有横轴温度数值刻度，不能为16个点附会具体温度。','题目问大约22℃；照片点位左右距离仅用于判断偏差约抵消，不证明精确等于22℃。'],'difference_from_existing_diagram':['原源码只有4条水平线，清晰原图是5条水平边界分成4个日带，重绘恢复第5条边界。','原图为圆点，原源码使用小方块，改为16个实心圆点。','原源码第二天画成两左两右，清晰照片是一左、一点在轴附近、两右；恢复各点左右分布。','原源码第四天画成三左一右；照片为两左、一点在轴附近、一右，恢复相对分布。','竖参考线在原图宽度约七成处，重绘保留该位置，未强行放在水平线正中。'],'outputs':{'tikz':'diagram_source/p078_temperatures_photo.tikz','standalone_tex':'diagram_source/p078_temperatures_photo.tex','compiled_pdf':'diagram_source/p078_temperatures_photo.pdf','svg':'diagram_source/p078_temperatures_photo.svg'},'compile_verification':{'engine':'XeLaTeX','exit_code':process.returncode,'pages':1,'embedded_bitmap_images':0,'vector_drawings':shape_count,'pdf_page_rect_pt':box,'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'missing_characters':'Missing character:' in process.stdout}}
(R/'diagram_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'answer':'B','points':len(coordinates),'boundaries':5,'pdf':str(pdf),'drawings':shape_count,'compiled':True},ensure_ascii=False))
