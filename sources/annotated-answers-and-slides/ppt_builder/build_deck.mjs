import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {randomUUID} from 'node:crypto';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const W=1280,H=720,MARGIN=64,BOTTOM=650,BODY_PT=32,PX=BODY_PT*96/72;
const BLACK='#111111',RED='#C00000';
function args(){const out={};for(let i=2;i<process.argv.length;i+=2)out[process.argv[i].replace(/^--/,'')]=process.argv[i+1];return out;}
const FONT_ADVANCES=JSON.parse(await fs.readFile(path.join(HERE,'font_advances.json'),'utf8'));
function asianBoundary(a,b){return !!a&&!!b&&((/[^\x00-\x7F\s]/u.test(a)&&/[!-~]/.test(b))||(/[!-~]/.test(a)&&/[^\x00-\x7F\s]/u.test(b)));}
function textWidth(s){const chars=[...s];return chars.reduce((n,c,i)=>n+((c==='　'||c===' ')?PX:/\s/.test(c)?PX*.31:/[\x00-\x7F]/.test(c)?PX*(FONT_ADVANCES[c]??.6):PX)+(i&&asianBoundary(chars[i-1],c)?PX*.25:0),0);}
function astPlain(a){if(a.t==='text')return a.v;if(a.t==='seq')return a.items.map(astPlain).join('');if(a.t==='frac')return '('+astPlain(a.num)+')/('+astPlain(a.den)+')';if(a.t==='sup'||a.t==='sub')return astPlain(a.base)+astPlain(a.arg);if(a.t==='subsup')return astPlain(a.base)+astPlain(a.sub)+astPlain(a.sup);if(a.t==='rad')return '√'+astPlain(a.base);if(a.t==='bar')return astPlain(a.base);if(a.t==='matrix')return a.rows.map(r=>r.map(astPlain).join(',')).join(';');throw Error('Unknown AST '+a.t);}
function mathSize(b,assets){const a=assets?.[b.asset_id];return a?{width:a.width_px,height:a.height_px}:{width:Math.max(22,textWidth(b.plain??astPlain(b.ast))*.72),height:56};}
function slotSize(r,assets){
 const a=r.answer,answer=a.type==='math'?mathSize(a,assets):{width:textWidth(a.text),height:58};
 let old=0,p=r.placeholder;
 if(r.kind==='cell_composite'){const l=textWidth(r.known_prefix)+3,rr=textWidth(r.known_suffix)+3,w=Math.max(48,answer.width+16);return {width:l+w+rr,height:Math.max(62,answer.height+12),left:l,inner:w,answer};}
 if(r.kind==='parentheses'){const inner=p.slice(1,-1).replace(/\\qquad/g,'　　').replace(/\\quad/g,'　').replace(/\\[,; ]/g,' ');old=textWidth(inner);const l=textWidth(p[0])+3,rr=textWidth(p.at(-1))+3,w=Math.max(old,answer.width+12);return {width:l+w+rr,height:Math.max(62,answer.height+12),left:l,inner:w,answer};}
 if(p.startsWith('\\underline'))old=textWidth(p.replace(/\\underline\{|\}/g,'').replace(/\\qquad/g,'　　').replace(/\\quad/g,'　').replace(/\\[,; ]/g,' '));
 else if(r.kind==='underline')old=textWidth(p);
 const w=Math.max(r.kind==='underline'?old:48,answer.width+16),h=Math.max(62,answer.height+14);return {width:w,height:h,left:0,inner:w,answer};
}
function paragraphLines(b,assets,width){
 const atoms=[];const closing=/^[，。、；：！？）》」』】〕〉”’….,;:!?)]$/u,opening=/^[（《「『【〔〈“‘(]$/u;
 const flat=a=>a.kind==='group'?a.items.flatMap(flat):[a];
 for(const r of b.runs){
  if(r.type==='slot'){const size=slotSize(r,assets);atoms.push({kind:'slot',block:r,size,width:size.width,height:size.height,formula_group:r.formula_group});}
  else if(r.type==='math'){const size=mathSize(r,assets);atoms.push({kind:'math',block:r,width:size.width+3,height:size.height,formula_group:r.formula_group});}
  else {let previous='';for(const token of r.text.match(/[（(][ 　\t]*[）)]|_+|[A-Za-z0-9.,]+|[ \t]+|\n|[^\x00-\x7F]|./gu)??[]){
   const atom={kind:'text',text:token,width:textWidth(token)+(asianBoundary(previous,token[0])?PX*.25:0),height:58};previous=[...token].at(-1)??'';
   if(closing.test(token)&&atoms.length&&atoms.at(-1).kind!=='newline'){
    const previous=atoms.pop();const items=[...flat(previous),atom];atoms.push({kind:'group',items,width:items.reduce((n,x)=>n+x.width,0),height:Math.max(...items.map(x=>x.height)),formula_group:previous.formula_group});
   }else atoms.push(token==='\n'?{kind:'newline'}:atom);
  }}
 }
 const bundled=[];
 for(let i=0;i<atoms.length;i++){const a=atoms[i];if(a.formula_group){const items=[a];while(i+1<atoms.length&&atoms[i+1].formula_group===a.formula_group)items.push(atoms[++i]);const w=items.reduce((n,x)=>n+x.width,0);if(w<=width)bundled.push({kind:'group',items,width:w,height:Math.max(...items.map(x=>x.height))});else bundled.push(...items);}else bundled.push(a);}
 const grouped=[];
 for(let i=0;i<bundled.length;i++){
  let a=bundled[i];
  if(a.kind==='text'&&opening.test(a.text)&&i+1<bundled.length&&bundled[i+1].kind!=='newline'){
   const items=[a,...flat(bundled[++i])];a={kind:'group',items,width:items.reduce((n,x)=>n+x.width,0),height:Math.max(...items.map(x=>x.height))};
  }
  grouped.push(a);
 }
 const lines=[];let pieces=[],x=0,maxH=58;
 const flush=()=>{if(pieces.length){lines.push({type:'line',pieces,height:maxH+5,source:b});pieces=[];x=0;maxH=58;}};
 for(const atom of grouped){
  if(atom.kind==='newline'){flush();continue;}
  if(atom.width>width)throw Error('OVERSIZE_INLINE '+b.key+': '+atom.width);
  if(x+atom.width>width&&pieces.length)flush();
  for(const child of flat(atom)){
   if(child.kind==='text'){
    const prev=pieces.at(-1);if(prev?.type==='text'){prev.text+=child.text;prev.width+=child.width;}
    else pieces.push({type:'text',text:child.text,x,width:child.width,height:58});
   }else if(child.kind==='math')pieces.push({type:'math',block:child.block,x,width:child.width-3,height:child.height});
   else pieces.push({type:'slot',block:child.block,size:child.size,x,width:child.width,height:child.height});
   x+=child.width;maxH=Math.max(maxH,child.height+4);
  }
 }
 flush();return lines;
}
function unitsFor(b,assets,width){
 if(b.type==='paragraph')return paragraphLines(b,assets,width);
 if(b.type==='heading')return [{type:'heading',text:b.text,height:64,source:b}];
 if(b.type==='math'){
  const size=mathSize(b,assets);if(size.width>width-42)throw Error('OVERSIZE_MATH '+b.key+': '+size.width);
  return [{type:'equation',block:b,width:size.width,height:Math.max(62,size.height+8),source:b}];
 }
 if(b.type==='diagram'){
  const a=assets?.[b.asset_id];let natural=a?{width:a.width_px,height:a.height_px}:{width:600,height:320};
  if(['altitude','perpendicular','perpendicular_shortest_path'].includes(b.animation?.type)&&b.animation_bounds){const q=b.animation_bounds;natural={width:(q[2]-q[0])*100,height:(q[3]-q[1])*100};}
  const nativeConstruction=['altitude','perpendicular','perpendicular_shortest_path'].includes(b.animation?.type);
  const caption=b.caption&&(nativeConstruction||!b.tikz?.includes(b.caption))?paragraphLines({...b,runs:[{type:'text',text:b.caption}]},assets,width):[];
  const capHeight=caption.reduce((n,x)=>n+x.height+7,0);for(const u of caption)u.table_title=true;
  const scale=Math.min(width/natural.width,(480-capHeight)/natural.height);
  return [...caption,{type:'diagram',block:b,width:natural.width*scale,height:natural.height*scale+14,source:b}];
 }
 if(b.type==='table'){
  const rows=b.rows.length,cols=Math.max(...b.rows.map(x=>x.length));
  const vals=b.rows.map(r=>Array.from({length:cols},(_,c)=>(r[c]?.runs??[]).map(x=>x.text??x.plain??'').join('')));
  // Match installed CJK metrics and reserve the Asian/Latin spacing that actual
  // Office-compatible renderers add. Whole cell strings remain on one line.
  const widths=Array.from({length:cols},(_,c)=>Math.max(92,...vals.map(r=>textWidth(r[c]??'')+32),...b.rows.map(r=>r[c]?.final_slot?slotSize(r[c].final_slot,assets).width+24:0)));
  const repeatFirst=!!(b.source_table||b.review_table)&&cols>1;const groups=[];let group=repeatFirst?[0]:[],total=repeatFirst?widths[0]:0;
  for(let c=repeatFirst?1:0;c<cols;c++){
   if(widths[c]+(repeatFirst?widths[0]:0)>width)throw Error('OVERSIZE_TABLE_CELL '+b.key+': '+widths[c]);
   if(group.length&&(total+widths[c]>width)){groups.push(group);group=repeatFirst?[0]:[];total=repeatFirst?widths[0]:0;}
   group.push(c);total+=widths[c];
  }
  if(group.length)groups.push(group);
  const chunks=[],maxRows=(b.title_runs?.length||b.footer_runs?.length)?5:6;
  for(const [part,columns]of groups.entries())for(let start=0;start<rows;){
   const indices=[];if(start>0&&b.has_header)indices.push(0);
   const take=maxRows-indices.length;for(let j=start;j<Math.min(rows,start+take);j++)indices.push(j);
   const copy={...b,rows:indices.map(i=>columns.map(c=>b.rows[i][c]??{runs:[]}))};
   const titles=(b.title_runs?.length?b.title_runs:(groups.length>1?[[{type:'text',text:'表格'}]]:[]));
   for(const runs of titles){const label=groups.length>1?[...runs,{type:'text',text:`（第${part+1}部分）`}]:runs;const title={...b,type:'paragraph',runs:label};for(const u of paragraphLines(title,assets,width)){u.table_title=true;chunks.push(u);}}
   chunks.push({type:'table',block:copy,values:indices.map(i=>columns.map(c=>vals[i][c])),widths:columns.map(c=>widths[c]),height:indices.length*68+32,table_height:indices.length*68,source:b,source_row_indices:indices,source_column_indices:columns});start+=take;
  }
  for(const runs of b.footer_runs??[]){const footer={...b,type:'paragraph',runs};chunks.push(...paragraphLines(footer,assets,width));}
  return chunks;
 }
 if(b.type==='vertical'){
  const n=b.calculation.rows.length;
  if(n>10)throw Error('OVERSIZE_VERTICAL '+b.key+': '+n+' rows');
  const extra=(b.calculation.label?58:0)+((b.calculation.carry_marks?.length||b.calculation.borrow_steps?.length)?32:0);
  return [{type:'vertical',block:b,height:n*52+12+extra,source:b}];
 }
 throw Error('Unsupported block '+b.type);
}
export function planDeck(data,{strict=true}={}){
 const slides=[],issues=[];const assets=data.assets??{};
 if(strict&&data.error_count)throw Error('Normalization errors remain: '+data.error_count);
 for(const record of data.records){
  let slide=null;let number=0,largeGroup=null;const firstSlide=slides.length;
  const newSlide=()=>{number++;slide={record_key:record.key,book_page:record.book_page,source_page:record.source_page,question_id:record.id,continuation:number,title:`原书第${record.book_page}页　${record.id}`,units:[],y:120,subquestions:[]};slides.push(slide);};
  newSlide();
  for(let bi=0;bi<record.blocks.length;bi++){
   const block=record.blocks[bi];
   let units;
   try{units=unitsFor(block,assets,W-2*MARGIN-32);}catch(e){issues.push({key:record.key,block:block.key,severity:'error',code:String(e.message).split(' ')[0],detail:String(e.message)});continue;}
   if(record.key==='p066_s01'&&block.is_review)for(const unit of units)if(unit.type==='line'&&unit.pieces.some(p=>p.type==='text'&&p.text.includes('平移'))){unit.inline_checkmark=true;unit.height+=36;}
   const limit=block.is_review&&!block.review_table&&(record.answer_slots??[]).some(x=>x.unresolved)?BOTTOM-90:BOTTOM;
   let groupHeight=units.reduce((n,u)=>n+u.height+7,0);
   if((block.phase==='subquestion'||block.review_start)&&slide.units.length)newSlide();
   if(block.is_review){slide.is_review=true;slide.review_label=block.review_label??'原题回填';}
   if(block.option_index===0){
    for(let k=bi+1;k<record.blocks.length&&record.blocks[k].option_index!==undefined;k++)groupHeight+=unitsFor(record.blocks[k],assets,W-2*MARGIN-32).reduce((n,u)=>n+u.height+7,0);
   }else if(block.aligned_group&&record.blocks[bi-1]?.aligned_group!==block.aligned_group){
    let count=1;for(let k=bi+1;k<record.blocks.length&&record.blocks[k].aligned_group===block.aligned_group;k++){groupHeight+=unitsFor(record.blocks[k],assets,W-2*MARGIN-32).reduce((n,u)=>n+u.height+7,0);count++;}
    if(groupHeight>limit-120){const pages=Math.ceil(groupHeight/(limit-120));largeGroup={id:block.aligned_group,perPage:Math.ceil(count/pages),seen:0};if(slide.units.length)newSlide();}
   }
   if(largeGroup&&largeGroup.id===block.aligned_group&&largeGroup.seen>0&&largeGroup.seen%largeGroup.perPage===0&&slide.units.length)newSlide();
   if(groupHeight<=limit-120&&slide.y+groupHeight>limit&&slide.units.length)newSlide();
   for(let ui=0;ui<units.length;ui++){
    const unit=units[ui];
    if(unit.height>limit-120){issues.push({key:record.key,block:block.key,severity:'error',code:'OVERSIZE_BLOCK',detail:unit.type+' '+unit.height});continue;}
    // Keep a method heading with at least one subsequent calculation line.
    let reserve=unit.type==='heading'?100:0;
    if(unit.table_title){for(let uj=ui+1;uj<units.length;uj++){reserve+=units[uj].height+7;if(!units[uj].table_title)break;}}
    if(slide.y+unit.height+reserve>limit&&slide.units.length)newSlide();
    if(block.is_review){slide.is_review=true;slide.review_label=block.review_label??'原题回填';}
    if(block.is_review){for(const piece of unit.pieces??[]){if(piece.type==='slot'&&piece.block.unresolved&&piece.block.reveal){(slide.unknown_slots??=[]).push({index:piece.block.slot_index,label:piece.block.display_label??'待核'});}}}
    unit.y=slide.y;unit.role=block.role;unit.block_key=block.key;slide.units.push(unit);slide.y+=unit.height+7;
    if(block.subquestion_key&&!slide.subquestions.some(x=>x.key===block.subquestion_key))slide.subquestions.push({key:block.subquestion_key,label:block.subquestion_label});
   }
   if(largeGroup&&largeGroup.id===block.aligned_group)largeGroup.seen++;
  }
  for(const s of slides.slice(firstSlide)){if(s.is_review)s.title+='　'+(s.review_label??'原题回填');if(s.subquestions.length===1&&!String(s.question_id).includes(s.subquestions[0].label))s.title+=s.subquestions[0].label;}
 }
 return {width_px:W,height_px:H,body_points:BODY_PT,slides,issues,record_count:data.records.length,error_count:issues.length,estimated:!data.assets};
}

function shapeText(slide,name,text,rect,{color=BLACK,points=BODY_PT,bold=false,font='Droid Sans Fallback'}={}){
 const s=slide.shapes.add({geometry:'textbox',name,position:rect,fill:'none',line:{style:'solid',fill:'none',width:0}});
 s.text=text;s.text.style={fontSize:`${points}pt`,typeface:font,color,bold,wrap:'none',autoFit:'none',insets:0,verticalAlignment:'middle'};return s;
}
function line(slide,name,x1,y1,x2,y2,{color=RED,dashed=false,width=3}={}){
 const left=Math.min(x1,x2),top=Math.min(y1,y2),w=Math.max(.1,Math.abs(x2-x1)),h=Math.max(.1,Math.abs(y2-y1));
 const pts=[{moveTo:{x:x1-left,y:y1-top}},{lineTo:{x:x2-left,y:y2-top}}];
 return slide.shapes.add({geometry:'custom',name,position:{left,top,width:w,height:h},fill:'none',line:{style:dashed?'dashed':'solid',fill:color,width},customPaths:[{width:w,height:h,commands:pts}]});
}
function pathShape(slide,name,points,{color=RED,closed=true,pivot=null,fill='none',width=3}={}){
 let left=Math.min(...points.map(p=>p[0])),right=Math.max(...points.map(p=>p[0])),top=Math.min(...points.map(p=>p[1])),bottom=Math.max(...points.map(p=>p[1]));
 if(pivot){const rx=Math.max(...points.map(p=>Math.abs(p[0]-pivot[0])),.2),ry=Math.max(...points.map(p=>Math.abs(p[1]-pivot[1])),.2);left=pivot[0]-rx;right=pivot[0]+rx;top=pivot[1]-ry;bottom=pivot[1]+ry;}
 const w=Math.max(.2,right-left),h=Math.max(.2,bottom-top),commands=[{moveTo:{x:points[0][0]-left,y:points[0][1]-top}},...points.slice(1).map(p=>({lineTo:{x:p[0]-left,y:p[1]-top}})),...(closed?[{close:{}}]:[])];
 return slide.shapes.add({geometry:'custom',name,position:{left,top,width:w,height:h},fill,line:{style:'solid',fill:color,width},customPaths:[{width:w,height:h,commands}]});
}
function mapper(block,rect,asset){
 if(asset?.svg_affine){const a=asset.svg_affine,[vx,vy,vw,vh]=a.viewbox;return {map:p=>[rect.left+(a.sx*p[0]+a.ox-vx)/vw*rect.width,rect.top+(a.sy*p[1]+a.oy-vy)/vh*rect.height],sx:a.sx/vw*rect.width,sy:-a.sy/vh*rect.height};}
 const bounds=block.animation_bounds;if(!bounds)throw Error('ANIMATION_BOUNDS_REQUIRED '+block.key);
 const [x0,y0,x1,y1]=bounds;const border=asset?1.3333333*(rect.width/asset.width_px):0;
 const sx=(rect.width-2*border)/(x1-x0),sy=(rect.height-2*border)/(y1-y0);
 const map=p=>[rect.left+border+(p[0]-x0)*sx,rect.top+border+(y1-p[1])*sy];return {map,sx,sy};
}
function rotatePoints(points,center,angle,direction){const r=angle*(direction==='clockwise'?-1:1)*Math.PI/180;return points.map(p=>[center[0]+(p[0]-center[0])*Math.cos(r)-(p[1]-center[1])*Math.sin(r),center[1]+(p[0]-center[0])*Math.sin(r)+(p[1]-center[1])*Math.cos(r)]);}
function planConstructionBoard(F,A,B,P,u){
 const distance=Math.hypot(P[0]-F[0],P[1]-F[1]),long=distance+25,short=long/Math.sqrt(3),v=[(P[0]-F[0])/distance,(P[1]-F[1])/distance],body={left:64,right:1216,top:120,bottom:650};
 const rotate=(p,c,a)=>{const r=a*Math.PI/180,x=p[0]-c[0],y=p[1]-c[1];return[c[0]+x*Math.cos(r)-y*Math.sin(r),c[1]+x*Math.sin(r)+y*Math.cos(r)];};
 const bbox=points=>({x0:Math.min(...points.map(p=>p[0])),x1:Math.max(...points.map(p=>p[0])),y0:Math.min(...points.map(p=>p[1])),y1:Math.max(...points.map(p=>p[1]))});
 const outside=points=>points.reduce((n,p)=>n+Math.max(0,body.left-p[0],p[0]-body.right)+Math.max(0,body.top-p[1],p[1]-body.bottom),0);
 let best=null;
 for(const sign of [1,-1]){
  const pts=[F,[F[0]+sign*u[0]*short,F[1]+sign*u[1]*short],[F[0]+v[0]*long,F[1]+v[1]*long]],bb=bbox(pts),center=[(bb.x0+bb.x1)/2,(bb.y0+bb.y1)/2];
  const rotationSweep=[];for(let a=0;a<=20;a+=1)rotationSweep.push(...pts.map(p=>rotate(p,center,a)));const sweep=bbox(rotationSweep),w=sweep.x1-sweep.x0,h=sweep.y1-sweep.y0;
  const origins=[[body.right-w-10,(body.top+body.bottom-h)/2],[body.right-w-10,body.top+10],[body.left+10,(body.top+body.bottom-h)/2]];
  const length=Math.hypot(B[0]-A[0],B[1]-A[1]),ft=(F[0]-A[0])*u[0]+(F[1]-A[1])*u[1];
  for(const d of [60,-60,35,-35]){const pos=Math.max(0,Math.min(length,ft+d)),S=[A[0]+u[0]*pos,A[1]+u[1]*pos],move=[S[0]-F[0],S[1]-F[1]];if(Math.hypot(...move)<10)continue;
   for(const origin of origins){const offset=[origin[0]-sweep.x0,origin[1]-sweep.y0],all=[...pts,...pts.map(p=>[p[0]+move[0],p[1]+move[1]])];
    for(let t=0;t<=1.00001;t+=.05){for(const p of pts){const q=rotate(p,center,20*(1-t));all.push([q[0]+offset[0]*(1-t)+move[0]*t,q[1]+offset[1]*(1-t)+move[1]*t]);}}
    const score=outside(all);if(!best||score<best.score)best={score,points:pts.map(p=>[p[0]+offset[0],p[1]+offset[1]]),first:[move[0]-offset[0],move[1]-offset[1]],second:[-move[0],-move[1]],sweep_bbox:bbox(all),angle:20};
   }
  }
 }
 if(!best||best.score>.02)throw Error('BOARD_OUTSIDE_VIEW '+JSON.stringify(best));return best;
}
function addConstruction(slide,block,rect,sm,font,asset){
 const spec=block.animation;(sm.scene_registrations??=[]).push({block_key:block.key,type:spec.type,registration_method:'native_shared_transform',actual_background_anchor:true});const {map}=mapper(block,rect,asset);let base=spec.base??[[0,0],[6,0]];let vertex=spec.vertex??[3,0];
 if(typeof base[0]==='string')base=base.map(n=>spec.points[n]);if(typeof vertex==='string')vertex=spec.points[vertex];
 const a=base[0],b=base[1],dx=b[0]-a[0],dy=b[1]-a[1],d2=dx*dx+dy*dy;
 const t=((vertex[0]-a[0])*dx+(vertex[1]-a[1])*dy)/d2,projection=[a[0]+t*dx,a[1]+t*dy];let claimed=spec.foot;if(typeof claimed==='string')claimed=spec.points[claimed];if(claimed&&Math.hypot(claimed[0]-projection[0],claimed[1]-projection[1])>.01)throw Error('INCONSISTENT_FOOT '+block.key);const foot=projection;
 const offBase=Math.hypot(vertex[0]-foot[0],vertex[1]-foot[1])>1e-5;
 const endpoint=spec.endpoint??(spec.type==='perpendicular'?[foot[0]-dy/Math.sqrt(d2)*2,foot[1]+dx/Math.sqrt(d2)*2]:vertex);
 const A=map(a),B=map(b),F=map(foot),P=map(spec.type==='altitude'||offBase?vertex:endpoint);const u=[(B[0]-A[0])/Math.hypot(B[0]-A[0],B[1]-A[1]),(B[1]-A[1])/Math.hypot(B[0]-A[0],B[1]-A[1])];
 if(spec.grid?.dotted){const g=spec.grid;for(let x=g.x_min;x<=g.x_max+1e-8;x+=g.step??1)for(let y=g.y_min;y<=g.y_max+1e-8;y+=g.step??1){const p=map([x,y]);slide.shapes.add({geometry:'ellipse',name:block.key+'_dot'+x+'_'+y,position:{left:p[0]-1.5,top:p[1]-1.5,width:3,height:3},fill:BLACK,line:{style:'solid',fill:BLACK,width:.5}});}}
 else if(spec.grid){const g=spec.grid;for(let x=g.x_min;x<=g.x_max+1e-8;x+=g.step??1){const p=map([x,g.y_min]),q=map([x,g.y_max]);line(slide,block.key+'_gx'+x,p[0],p[1],q[0],q[1],{color:'#BBBBBB',width:.7});}for(let y=g.y_min;y<=g.y_max+1e-8;y+=g.step??1){const p=map([g.x_min,y]),q=map([g.x_max,y]);line(slide,block.key+'_gy'+y,p[0],p[1],q[0],q[1],{color:'#BBBBBB',width:.7});}}
 const answerObject=spec.object_role==='answer';
 if(spec.object_points){const pn=block.key+'_given_polygon';pathShape(slide,pn,spec.object_points.map(map),{color:answerObject?RED:BLACK,width:2});if(answerObject)sm.clicks.push({label:'先按条件画出图形',effects:[{type:'wipe',target:pn,direction:'right',duration_ms:900}]});}
 if(!asset){
  if(!answerObject)line(slide,block.key+'_given_line',A[0],A[1],B[0],B[1],{color:BLACK,width:2});
  const lname=spec.line_name??(spec.labels?.base==='l'?'l':'');if(lname)shapeText(slide,block.key+'_given_l',lname,{left:B[0]+8,top:B[1]-45,width:70,height:46},{color:BLACK,points:26,font});
  const vname=spec.point_name??spec.labels?.vertex??'';if(vname){const vp=map(vertex),labelRect={left:vp[0]+8,top:vp[1]+5,width:70,height:46};if(block.name==='p011_s09_animation_0'){labelRect.left-=56;labelRect.top-=20;}shapeText(slide,block.key+'_given_A',vname,labelRect,{color:BLACK,points:26,font});}
 }
 if(t<-.00001||t>1.00001){const ext=block.key+'_base_extension',near=t<0?A:B;line(slide,ext,near[0],near[1],F[0],F[1],{color:RED,dashed:true,width:2});sm.clicks.push({label:'延长底边',effects:[{type:'wipe',target:ext,direction:'right',duration_ms:500}]});}
 const board=block.key+'_board',boardPlan=planConstructionBoard(F,A,B,P,u);
 pathShape(slide,board,boardPlan.points,{color:'#555555',width:2});
 (sm.initial_rotations??=[]).push({target:board,degrees:boardPlan.angle});
 (sm.construction_bounds??=[]).push({block_key:block.key,board_bbox_all_stages:boardPlan.sweep_bbox,board_type:'30-60-90',long_leg_covers_line:true});
 sm.clicks.push({label:'①直角边与底或已知直线对齐',effects:[{type:'appear',target:board},{type:'rotation',target:board,degrees:-boardPlan.angle,duration_ms:700},{type:'motion',target:board,dx:boardPlan.first[0],dy:boardPlan.first[1],duration_ms:700}]});
 sm.clicks.push({label:'④平移三角板到指定位置',effects:[{type:'motion',target:board,dx:boardPlan.second[0],dy:boardPlan.second[1],duration_ms:900}]});
 const high=block.key+'_constructed_line';const start=spec.type==='altitude'||offBase?map(vertex):F;const end=spec.type==='altitude'||offBase?F:P;line(slide,high,start[0],start[1],end[0],end[1],{dashed:spec.type==='altitude',width:3});sm.clicks.push({label:'③沿另一直角边作线',effects:[{type:'wipe',target:high,direction:start[1]<end[1]?'down':'up',duration_ms:900}]});
 const v=[(P[0]-F[0])/Math.max(.1,Math.hypot(P[0]-F[0],P[1]-F[1])),(P[1]-F[1])/Math.max(.1,Math.hypot(P[0]-F[0],P[1]-F[1]))],z=13;
 const r1=block.key+'_right1',r2=block.key+'_right2';line(slide,r1,F[0]+u[0]*z,F[1]+u[1]*z,F[0]+u[0]*z+v[0]*z,F[1]+u[1]*z+v[1]*z,{width:2});line(slide,r2,F[0]+v[0]*z,F[1]+v[1]*z,F[0]+u[0]*z+v[0]*z,F[1]+u[1]*z+v[1]*z,{width:2});const effects=[{type:'appear',target:r1},{type:'appear',target:r2},{type:'hide',target:board}];
 if(spec.type==='altitude'){
  const hn=block.key+'_high_label',bn=block.key+'_base_label',ht=spec.labels?.altitude??'高',bt=spec.labels?.base??'底',hw=Math.max(80,textWidth(ht)*28/32+10),bw=Math.max(80,textWidth(bt)*28/32+10);
  const hd=Math.abs(u[0])*hw/2+Math.abs(u[1])*27.5+16,bd=Math.abs(v[0])*bw/2+Math.abs(v[1])*27.5+16;
  shapeText(slide,hn,ht,{left:(start[0]+end[0])/2+u[0]*hd-hw/2,top:(start[1]+end[1])/2+u[1]*hd-27,width:hw,height:55},{color:RED,points:28,font});
  shapeText(slide,bn,bt,{left:(A[0]+B[0])/2-v[0]*bd-bw/2,top:(A[1]+B[1])/2-v[1]*bd-27,width:bw,height:55},{color:RED,points:28,font});effects.push({type:'appear',target:hn},{type:'appear',target:bn});
  if(block.name==='p095_s04_animation_1'){const minX=Math.min(...spec.object_points.map(p=>map(p)[0]));(sm.geometry_adjustments??=[]).push({target:hn,rect:{left:minX-hw-16,top:(start[1]+end[1])/2-27,width:hw,height:55},reason:'高标签避开三角形上边'});}
 }
 if(spec.labels?.endpoint){const label=block.key+'_endpoint_label';shapeText(slide,label,spec.labels.endpoint,{left:P[0]+10,top:P[1]-30,width:100,height:55},{color:RED,points:26,font});effects.push({type:'appear',target:label});}
 if(spec.length_cm){const label=block.key+'_length_label';shapeText(slide,label,String(spec.length_cm)+'厘米',{left:(F[0]+P[0])/2+12,top:(F[1]+P[1])/2-30,width:220,height:55},{color:RED,points:26,font});effects.push({type:'appear',target:label});}
 if(spec.label){const label=block.key+'_route_label';shapeText(slide,label,spec.label,{left:(F[0]+P[0])/2+12,top:(F[1]+P[1])/2-30,width:300,height:55},{color:RED,points:26,font});effects.push({type:'appear',target:label});}
 sm.clicks.push({label:'②标直角与对应标注',effects});
}
function addTransformScene(slide,block,rect,sm,font,asset){
 if(!asset?.svg_affine)throw Error('MISSING_ACTUAL_BACKGROUND_REGISTRATION '+block.key);
 const spec=block.animation,{map,sx,sy}=mapper(block,rect,asset);
 (sm.scene_registrations??=[]).push({block_key:block.key,type:spec.type,registration_method:asset.svg_affine.method,actual_background_anchor:true,affine:asset.svg_affine,layout_placement:spec.placement??[0,0],background_shift:block.background_shift??[0,0]});
 if(spec.show_pivot_label){const p=map(spec.center),dot=block.key+'_pivot',label=block.key+'_pivot_label';slide.shapes.add({geometry:'ellipse',name:dot,position:{left:p[0]-4,top:p[1]-4,width:8,height:8},fill:RED,line:{style:'solid',fill:RED,width:1}});shapeText(slide,label,'旋转中心',{left:p[0]-160,top:p[1]+8,width:160,height:50},{color:RED,font,points:26});sm.clicks.push({label:'标出左下角的旋转中心',effects:[{type:'appear',target:dot},{type:'appear',target:label}]});}
 const defaultPaths=spec.object_paths??(spec.object_points?[spec.object_points]:[]);
 const basicPaths=[...defaultPaths,...(spec.additional_paths??[])];
 if(basicPaths.some(p=>!Array.isArray(p)))throw Error('ANIMATION_OBJECT_PATHS_REQUIRED '+block.key);
 const closed=spec.closed??((basicPaths[0]?.length??spec.objects?.[0]?.points?.length??0)>2),stroke=spec.stroke_width_pt?spec.stroke_width_pt*96/72:3;
 const shifted=(paths,origin)=>paths.map(path=>path.map(p=>[p[0]+origin[0],p[1]+origin[1]]));
 function draw(name,paths,pivot=null){
  const screen=paths.map(p=>p.map(map));const all=screen.flat();let left=Math.min(...all.map(p=>p[0])),right=Math.max(...all.map(p=>p[0])),top=Math.min(...all.map(p=>p[1])),bottom=Math.max(...all.map(p=>p[1]));
  const marker=spec.endpoint_markers;
  if(marker){
   const primary=screen[0],ends=marker==='arrow_both'?[[primary[0],primary[1]],[primary.at(-1),primary.at(-2)]]:[[primary.at(-1),primary.at(-2)]];
   for(const [tip,prev]of ends){const length=Math.hypot(tip[0]-prev[0],tip[1]-prev[1]);if(!length)continue;const ux=(tip[0]-prev[0])/length,uy=(tip[1]-prev[1])/length,L=11,z=5;screen.push([[tip[0]-ux*L-uy*z,tip[1]-uy*L+ux*z],tip,[tip[0]-ux*L+uy*z,tip[1]-uy*L-ux*z]]);}
  }
  const allScreen=screen.flat();left=Math.min(...allScreen.map(p=>p[0]));right=Math.max(...allScreen.map(p=>p[0]));top=Math.min(...allScreen.map(p=>p[1]));bottom=Math.max(...allScreen.map(p=>p[1]));
  if(pivot){const P=map(pivot),rx=Math.max(.2,...allScreen.map(p=>Math.abs(p[0]-P[0]))),ry=Math.max(.2,...allScreen.map(p=>Math.abs(p[1]-P[1])));left=P[0]-rx;right=P[0]+rx;top=P[1]-ry;bottom=P[1]+ry;}
  const w=Math.max(.2,right-left),h=Math.max(.2,bottom-top);
  const pathsConfig=screen.map((points,i)=>({width:w,height:h,commands:[{moveTo:{x:points[0][0]-left,y:points[0][1]-top}},...points.slice(1).map(p=>({lineTo:{x:p[0]-left,y:p[1]-top}})),...(i===0&&closed?[{close:{}}]:[])]}));
  slide.shapes.add({geometry:'custom',name,position:{left,top,width:w,height:h},fill:'none',line:{style:'solid',fill:RED,width:stroke},customPaths:pathsConfig});
 }
 function process(paths,steps,labelPrefix='',history=true,placement=spec.placement??[0,0]){
  let current=shifted(paths,placement),previous=null;
  for(let i=0;i<steps.length;i++){
   const step=steps[i],name=block.key+'_'+labelPrefix+'move'+i,rawCenter=step.center??spec.center??[0,0],center=[rawCenter[0]+placement[0],rawCenter[1]+placement[1]];
   draw(name,current,step.type==='rotation'?center:null);const effects=[{type:'appear',target:name}];if(previous&&!history)effects.push({type:'hide',target:previous});
   if(step.type==='rotation'){
    const angle=Number(step.angle??90);effects.push({type:'rotation',target:name,degrees:(step.direction==='clockwise'?1:-1)*angle,duration_ms:1000});current=current.map(p=>rotatePoints(p,center,angle,step.direction));
   }else if(step.type==='translation'){
    const dx=Number(step.dx??0),dy=Number(step.dy??0);effects.push({type:'motion',target:name,dx:dx*sx,dy:-dy*sy,duration_ms:1000});current=current.map(path=>path.map(p=>[p[0]+dx,p[1]+dy]));
   }else throw Error('UNSUPPORTED_TRANSFORM_STEP '+step.type);
   sm.clicks.push({label:labelPrefix+(step.type==='rotation'?'按指定中心、方向和角度旋转':'按指定方向和格数平移'),effects});previous=name;
  }
 }
 if(spec.type==='rotation')process(basicPaths,[spec]);
 else if(spec.type==='translation'){
  const steps=[];if(spec.dx)steps.push({type:'translation',dx:spec.dx,dy:0});if(spec.dy)steps.push({type:'translation',dx:0,dy:spec.dy});process(basicPaths,steps,'',false);
 }else if(spec.type==='sequence'||spec.type==='rotation_sequence')process(basicPaths,spec.steps.map(s=>({type:spec.type==='rotation_sequence'?'rotation':s.type,...s})),spec.type==='rotation_sequence'?'第':'',spec.type!=='rotation_sequence');
 else if(spec.type==='rotation_copies'){
  for(const angle of spec.angles){const cp=spec.copy_placements?.find(p=>Number(p.angle)===Number(angle));process(basicPaths,[{...spec,type:'rotation',angle}],String(angle)+'度_',true,cp?.origin??[0,0]);}
 }else if(spec.type==='parallel_objects'||spec.type==='sequence_objects'){
  const at=sm.clicks.length;
  for(const [i,obj]of spec.objects.entries())process([obj.points,...(obj.additional_paths??[])],[obj],'图形'+(i+1)+'_');
  if(spec.type==='parallel_objects'){const generated=sm.clicks.splice(at);sm.clicks.push({label:'各图形独立变换',effects:generated.flatMap(x=>x.effects)});}
  if(spec.symmetry_axis){const axis=spec.symmetry_axis,a=map(axis.p1),b=map(axis.p2),nm=block.key+'_axis';line(slide,nm,a[0],a[1],b[0],b[1],{dashed:true});sm.clicks.push({label:'补出对称轴',effects:[{type:'wipe',target:nm,direction:'down'}]});}
 }else if(spec.type==='symmetry'){
  const axis=spec.axis,a=axis.p1??axis[0],b=axis.p2??axis[1],dx=b[0]-a[0],dy=b[1]-a[1],d2=dx*dx+dy*dy;
  const mirror=p=>{const t=((p[0]-a[0])*dx+(p[1]-a[1])*dy)/d2;return [2*(a[0]+t*dx)-p[0],2*(a[1]+t*dy)-p[1]];};
  const aa=map(a),bb=map(b),nm=block.key+'_axis';
  // In these completion tasks the axis/AB is already given in the retained
  // question vector. Avoid superimposing another dash rhythm into a solid line.
  if(!asset){line(slide,nm,aa[0],aa[1],bb[0],bb[1],{dashed:true});sm.clicks.push({label:'确定对称轴',effects:[{type:'wipe',target:nm,direction:'down'}]});}
  const reflected=basicPaths.map(path=>path.map(mirror));const points=basicPaths[0];
  for(let i=0;i<points.length;i++){
   const p=map(points[i]),q=map(reflected[0][i]),dot=block.key+'_mirror_point'+i,guide=block.key+'_mirror_guide'+i;
   slide.shapes.add({geometry:'ellipse',name:dot,position:{left:p[0]-4,top:p[1]-4,width:8,height:8},fill:RED,line:{style:'solid',fill:RED,width:1}});line(slide,guide,p[0],p[1],q[0],q[1],{color:'#777777',dashed:true,width:1});sm.clicks.push({label:'逐点找对称点',effects:[{type:'appear',target:dot},{type:'motion',target:dot,dx:q[0]-p[0],dy:q[1]-p[1],duration_ms:800},{type:'appear',target:guide}]});
  }
  const result=block.key+'_mirror_result';draw(result,reflected);sm.clicks.push({label:'按原顺序连接对称点',effects:[{type:'wipe',target:result,direction:'right',duration_ms:900}]});
 }else throw Error('UNSUPPORTED_GEOMETRY_ANIMATION '+spec.type);
}
function addVertical(slide,block,unit,sm,font){
 const calc=block.calculation,rows=calc.rows,pitch=40,rowPitch=52;
 const minCol=Math.min(0,...rows.flatMap(r=>r.cells.map(c=>Number(c.column))));const baseX=MARGIN+(1-minCol)*pitch;
 const hasMarks=calc.carry_marks?.length||calc.borrow_steps?.length;let top=unit.y+(calc.label?58:0)+(hasMarks?32:0);
 const color=block.role==='question'?BLACK:RED;const rowTargets=[];const quotient=new Map();
 if(calc.label)shapeText(slide,block.key+'_vertical_label',calc.label.replace('（原题字形仍保留）',''),{left:MARGIN,top:unit.y,width:1120,height:52},{color,font});
 for(let ri=0;ri<rows.length;ri++){
  const row=rows[ri],targets=[];
  for(let ci=0;ci<row.cells.length;ci++){
   const cell=row.cells[ci];let offset=0;
   for(const char of [...String(cell.text)]){
    if(char===' '){offset++;continue;}
    const name=block.key+'_vr'+ri+'c'+ci+'s'+offset,x=baseX+(Number(cell.column)+offset)*pitch;
    shapeText(slide,name,char,{left:x,top:top+ri*rowPitch,width:pitch,height:47},{color,font});
    sm.formulas.push({target:name,ast:{t:'text',v:char},color:color.slice(1),points:BODY_PT,font});targets.push(name);
    if(row.kind==='quotient')quotient.set(Number(cell.column)+offset,name);offset++;
   }
  }
  if(row.rule_after){const rule=row.rule_after===true?{start_column:minCol,end_column:calc.column_count-1}:row.rule_after;const rn=block.key+'_rule'+ri;line(slide,rn,baseX+rule.start_column*pitch-4,top+(ri+1)*rowPitch-4,baseX+(rule.end_column+1)*pitch+4,top+(ri+1)*rowPitch-4,{color,width:2});targets.push(rn);}
  if(row.annotation){const an=block.key+'_annotation'+ri;shapeText(slide,an,row.annotation,{left:baseX+(calc.column_count+1)*pitch,top:top+ri*rowPitch,width:100,height:48},{color,font,points:BODY_PT});targets.push(an);}
  rowTargets.push(targets);
 }
 let bracketTargets=[];
 if(calc.division_bracket){
  const q=calc.division_bracket,x=baseX+q.left_column*pitch-17,y=top+q.top_row*rowPitch-5,h=(q.bottom_row-q.top_row)*rowPitch;
  const curve=block.key+'_division_curve';slide.shapes.add({geometry:'custom',name:curve,position:{left:x,top:y,width:20,height:h},fill:'none',line:{style:'solid',fill:color,width:2},customPaths:[{width:20,height:h,commands:[{moveTo:{x:0,y:0}},{quadBezTo:{x1:20,y1:h/2,x:0,y:h}}]}]});
  const bar=block.key+'_division_bar';line(slide,bar,x,y,baseX+(q.right_column+1)*pitch+4,y,{color,width:2});bracketTargets=[curve,bar];
 }
 if(calc.highlight){const h=calc.highlight;slide.shapes.add({geometry:'rect',name:block.key+'_highlight',position:{left:baseX+h.from_column*pitch-6,top:top+h.from_row*rowPitch-4,width:(h.to_column-h.from_column+1)*pitch+12,height:(h.to_row-h.from_row+1)*rowPitch+4},fill:'none',line:{style:'dashed',fill:color,width:2}});}
 if(block.role==='question')return;
 const reveal=(targets,label)=>{if(targets.length)sm.clicks.push({label,effects:targets.map(target=>({type:'appear',target}))});};
 if(calc.op==='÷'&&calc.division_bracket){
  const first=rows.findIndex(r=>r.kind==='dividend_divisor');reveal([...rowTargets[first],...bracketTargets],'竖式：被除数与除数');
  const shown=new Set();
  for(let ri=0;ri<rows.length;ri++){
   const row=rows[ri];if(ri===first||row.kind==='quotient')continue;const targets=[...rowTargets[ri]];
   if(row.kind==='trial_product'&&quotient.has(Number(row.quotient_column))){const q=quotient.get(Number(row.quotient_column));if(!shown.has(q)){targets.unshift(q);shown.add(q);}}
   reveal(targets,'竖式：'+row.kind);
  }
  reveal([...quotient.values()].filter(x=>!shown.has(x)),'竖式：补全商位');
 }else for(let ri=0;ri<rows.length;ri++){
  if(rows[ri].kind==='result'){
   const marks=[];
   for(const [i,c]of (calc.carry_marks??[]).entries()){const name=block.key+'_carry'+i;shapeText(slide,name,c.text,{left:baseX+Number(c.column)*pitch,top:top-30,width:pitch,height:28},{color,font,points:18});sm.formulas.push({target:name,ast:{t:'text',v:String(c.text)},color:color.slice(1),points:18,font});marks.push(name);}
   const previousBorrow=new Map();
   for(const [si,step]of (calc.borrow_steps??[]).entries()){
    const effects=[];for(const [i,c]of step.updates.entries()){const name=block.key+'_borrow'+si+'_'+i;shapeText(slide,name,String(c.new_value),{left:baseX+Number(c.column)*pitch,top:top-30,width:pitch,height:28},{color,font,points:18});sm.formulas.push({target:name,ast:{t:'text',v:String(c.new_value)},color:color.slice(1),points:18,font});const strike=name+'_strike';line(slide,strike,baseX+Number(c.column)*pitch+5,top+16,baseX+Number(c.column)*pitch+30,top+33,{color,width:1.5});if(previousBorrow.has(c.column))effects.push({type:'hide',target:previousBorrow.get(c.column)});effects.push({type:'appear',target:name},{type:'appear',target:strike});previousBorrow.set(c.column,name);}if(effects.length)sm.clicks.push({label:'退位标记',effects});
   }
   reveal(marks,'进位标记');
  }
  reveal([...rowTargets[ri],...(ri===0?bracketTargets:[])],'竖式：'+rows[ri].kind);
 }
}
export async function buildDeck(data,plan,{draft,manifestPath,font='Droid Sans Fallback',previews,previewEvery=0}={}){
 if(plan.error_count)throw Error('Layout preflight errors remain');
 const {Presentation,PresentationFile}=await import('@oai/artifact-tool');
 const presentation=Presentation.create({slideSize:{width:W,height:H}});
 const manifest={width_px:W,height_px:H,font,slides:[]};const index=[];const assets=data.assets??{},records=new Map(data.records.map(r=>[r.key,r]));
 if(!data.assets)throw Error('Compiled assets manifest required; no placeholder fallback');
 for(let si=0;si<plan.slides.length;si++){
  const ps=plan.slides[si],slide=presentation.slides.add();slide.background.fill='#FFFFFF';const sm={slide:si+1,record_key:ps.record_key,bindings:[],formulas:[],vectors:[],tables:[],clicks:[],answer_slots:[],table_answers:[]};manifest.slides.push(sm);
  const titleShape=shapeText(slide,'title',ps.title,{left:MARGIN,top:32,width:1152,height:64},{points:30,bold:true,font});
  const sourceShape=shapeText(slide,'source',`PDF原页序 ${ps.source_page}　${ps.continuation>1?'解析续页 '+ps.continuation:''}`,{left:MARGIN,top:674,width:1060,height:26},{points:14,color:'#555555',font});
  shapeText(slide,'slide_number',String(si+1),{left:1170,top:674,width:50,height:26},{points:14,color:'#555555',font});
  const clickByBlock=new Map();
  function register(target,unit){
   if(unit.role==='question')return;
   const key=unit.block_key;if(!clickByBlock.has(key)){const click={label:unit.source.phase??'讲解',effects:[]};clickByBlock.set(key,click);sm.clicks.push(click);}
   clickByBlock.get(key).effects.push({type:'appear',target});
  }
  async function addMath(b,name,x,y,width,height,unit){
   const a=assets[b.asset_id];if(!a?.svg_path)throw Error('MISSING_MATH_ASSET '+b.key);
   const svg=await fs.readFile(a.svg_path,'utf8');slide.images.add({svg,alt:name,position:{left:x,top:y,width,height},fit:'contain'});
   sm.bindings.push({name,rect:{left:x,top:y,width,height}});
   const target='alt:'+name;sm.formulas.push({target,ast:b.ast,color:unit.role==='question'?'000000':'C00000',points:BODY_PT,font});sm.vectors.push({target,svg_path:a.svg_path});register(target,unit);
  }
  async function drawSlot(r,nm,x,y,width,height,unit){
   const z=slotSize(r,assets),mid=y+height/2;
   if(r.kind==='cell_composite'){shapeText(slide,nm+'_prefix',r.known_prefix,{left:x,top:y,width:z.left,height},{color:BLACK,font});shapeText(slide,nm+'_suffix',r.known_suffix,{left:x+z.left+z.inner,top:y,width:width-z.left-z.inner,height},{color:BLACK,font});slide.shapes.add({geometry:'rect',name:nm+'_blank_frame',position:{left:x+z.left,top:mid-24,width:z.inner,height:48},fill:'none',line:{style:'solid',fill:BLACK,width:1.5}});}
   else if(r.kind==='parentheses'){shapeText(slide,nm+'_left',r.placeholder[0],{left:x,top:y,width:z.left,height},{color:BLACK,font});shapeText(slide,nm+'_right',r.placeholder.at(-1),{left:x+z.left+z.inner,top:y,width:width-z.left-z.inner,height},{color:BLACK,font});}
   else if(r.kind==='underline')line(slide,nm+'_blank_line',x,mid+22,x+width,mid+22,{color:BLACK,width:1.5});
   else if(r.kind==='circle'||r.kind==='square')slide.shapes.add({geometry:r.kind==='circle'?'ellipse':'rect',name:nm+'_blank_frame',position:{left:x,top:mid-24,width,height:48},fill:'none',line:{style:'solid',fill:BLACK,width:1.5}});
   if(r.reveal){const ax=x+z.left+(z.inner-z.answer.width)/2,ay=mid-z.answer.height/2,virtual={...unit,role:'answer',block_key:r.group_key??'final_slots',source:{phase:r.phase_label??'原题空位回填'}};
    if(r.answer.type==='math')await addMath(r.answer,nm+'_answer',ax,ay,z.answer.width,z.answer.height,virtual);
    else{shapeText(slide,nm+'_answer',r.answer.text,{left:ax,top:ay,width:z.answer.width+4,height:z.answer.height},{color:RED,font});register(nm+'_answer',virtual);}
    const detail={slot_index:r.slot_index,table_index:r.table_index,row_index:r.row_index,column_index:r.column_index,placeholder:r.placeholder,kind:r.kind,target:r.answer.type==='math'?'alt:'+nm+'_answer':nm+'_answer',answer:r.answer.latex??r.answer.text,full_answer:r.full_answer,unresolved:!!r.unresolved,note:r.note??'',variant:ps.review_label??'原题回填'};
    (r.is_table?sm.table_answers:sm.answer_slots).push(detail);
   }
  }
  let object=0;const finalWordChecks=[];
  for(const unit of ps.units){
   const color=unit.role==='question'?BLACK:RED;const name=unit.block_key+'_'+object++;
   if(unit.type==='line'){
    const groupSpacing=ps.record_key==='p094_s05'&&unit.role==='question'&&unit.pieces.some(p=>p.type==='text'&&p.text.includes('小丽组'));
    const six=groupSpacing?unit.pieces.find(p=>p.type==='math'&&astPlain(p.block.ast)==='6'):null,four=groupSpacing?unit.pieces.find(p=>p.type==='math'&&astPlain(p.block.ast)==='4'):null;
    if(groupSpacing&&(!six||!four))throw Error('GROUP_SIZE_INLINE_ANCHORS_CHANGED');
    let pi=0;for(const piece of unit.pieces){
     const extra=groupSpacing?(piece.x>=four.x?24:piece.x>=six.x?12:0):0;
     const nm=name+'_p'+pi++;const x=MARGIN+piece.x+extra,y=unit.inline_checkmark?unit.y:unit.y+(unit.height-piece.height)/2;
     if(groupSpacing&&x+piece.width+4>W-MARGIN)throw Error('TARGETED_INLINE_SPACING_OVERFLOW');
     if(piece.type==='text'){shapeText(slide,nm,piece.text,{left:x,top:y,width:piece.width+4,height:piece.height},{color,font,bold:!!unit.table_title});register(nm,unit);}
     else if(piece.type==='math')await addMath(piece.block,nm,x,y,piece.width,piece.height,unit);
     else if(piece.type==='slot')await drawSlot(piece.block,nm,x,y,piece.width,piece.height,unit);
     if(unit.inline_checkmark&&piece.type==='text'&&piece.text.includes('平移')){const at=piece.text.indexOf('平移'),tick=ps.record_key+'_translation_check',rect={left:x+textWidth(piece.text.slice(0,at))+textWidth('平移')/2-18,top:y+52,width:36,height:36};shapeText(slide,tick,'√',rect,{color:RED,font,points:24});finalWordChecks.push({label:'在平移下面画√',effects:[{type:'appear',target:tick}]});(sm.inline_final_marks??=[]).push({target:tick,anchor_text:'平移',mark:'√',rect});}
    }
   }else if(unit.type==='heading'){shapeText(slide,name,unit.text,{left:MARGIN,top:unit.y,width:1152,height:unit.height},{color,font,bold:true});register(name,unit);
   }else if(unit.type==='equation'){
    // The first digit is always at x=106. The equals sign hangs to its left.
    const b=unit.block;
    const operator=b.leading_operator??(b.leading_equals?'=':null);if(operator){const en=name+'_operator';shapeText(slide,en,operator,{left:64,top:unit.y+3,width:34,height:unit.height-8},{color,font});sm.formulas.push({target:en,ast:{t:'text',v:operator},color:color.replace('#',''),points:BODY_PT,font});register(en,unit);}
    const natural=mathSize(b,assets);await addMath(b,name,106,unit.y+(unit.height-natural.height)/2,natural.width,natural.height,unit);
   }else if(unit.type==='diagram'){
    const b=unit.block,a=assets[b.asset_id];
    const spec=b.animation??b.native?.animation;
    if(['altitude','perpendicular','perpendicular_shortest_path'].includes(spec?.type)){
     addConstruction(slide,b,{left:MARGIN,top:unit.y,width:unit.width,height:unit.height-14},sm,font,null);
    }else if(a?.svg_path){const svg=await fs.readFile(a.svg_path,'utf8');const rect={left:MARGIN,top:unit.y,width:unit.width,height:unit.height-14};slide.images.add({svg,alt:name,position:rect,fit:'contain'});sm.bindings.push({name,rect});sm.vectors.push({target:'alt:'+name,svg_path:a.svg_path});if(!spec)register('alt:'+name,unit);}
    else if(b.glyph_svg){const svg=await fs.readFile(b.glyph_svg,'utf8');const rect={left:MARGIN,top:unit.y,width:unit.width,height:unit.height-14};slide.images.add({svg,alt:name,position:rect,fit:'contain'});sm.bindings.push({name,rect});sm.vectors.push({target:'alt:'+name,svg_path:b.glyph_svg});register('alt:'+name,unit);}
    else if(b.glyph_image){const bytes=await fs.readFile(b.glyph_image);const alt=name+' 原字形保留裁片',rect={left:MARGIN,top:unit.y,width:unit.width,height:unit.height-14};slide.images.add({blob:bytes,contentType:'image/png',alt,position:rect,fit:'contain'});sm.bindings.push({name:alt,rect});register('alt:'+alt,unit);}
    else if(!b.native&&!spec)throw Error('MISSING_DIAGRAM_ASSET '+b.key);
    if(spec){
     const rect={left:MARGIN,top:unit.y,width:unit.width,height:unit.height-14};
     if(!['altitude','perpendicular','perpendicular_shortest_path'].includes(spec.type))addTransformScene(slide,b,rect,sm,font,a);
    }
   }else if(unit.type==='table'){
    const b=unit.block;const table=slide.tables.add({rows:unit.values.length,columns:unit.widths.length,left:MARGIN,top:unit.y,width:unit.widths.reduce((a,b)=>a+b,0),height:unit.table_height??unit.height-32,columnWidths:unit.widths,values:unit.values});
    table.borders.assign({style:'solid',fill:'#111111',width:1.5});table.styleOptions={headerRow:false,bandedRows:false};
    table.cells.block({row:0,column:0,rowCount:unit.values.length,columnCount:unit.widths.length}).assign({fill:'#FFFFFF',textStyle:{fontSize:PX,typeface:font,color},margins:{left:8,right:8,top:4,bottom:4}});
    sm.tables.push({name,rect:{left:MARGIN,top:unit.y,width:unit.widths.reduce((a,b)=>a+b,0),height:unit.table_height??unit.height-32},match_values:unit.values,cells:b.rows.map(row=>row.map(c=>c.runs)),points:BODY_PT,color:color.replace('#',''),font});register(name,unit);
    for(let ri=0;ri<b.rows.length;ri++){let xx=MARGIN;for(let ci=0;ci<unit.widths.length;ci++){const r=b.rows[ri][ci]?.final_slot;if(r){const z=slotSize(r,assets);await drawSlot(r,name+'_cell'+ri+'_'+ci,xx+(unit.widths[ci]-z.width)/2,unit.y+ri*68+(68-z.height)/2,z.width,z.height,unit);}xx+=unit.widths[ci];}}
   }else if(unit.type==='vertical'){
    addVertical(slide,unit.block,unit,sm,font);
   }
  }
  if(ps.unknown_slots?.length){const groups=new Map();for(const q of ps.unknown_slots){if(!groups.has(q.label))groups.set(q.label,[]);groups.get(q.label).push(q.index+1);}const label=[...groups].map(([l,ii])=>'第'+ii.join('、')+'空：'+l).join('；')+'，详见本题解析。';shapeText(slide,'unknown_notice',label,{left:MARGIN,top:585,width:1152,height:58},{color:RED,font});register('unknown_notice',{role:'answer',block_key:'final_slots',source:{phase:'原题空位回填'}});}
  titleShape.bringToFront();sourceShape.bringToFront();
  sm.clicks.push(...finalWordChecks);
  const teacherNote=records.get(ps.record_key)?.verification?.teacher_reference_note;
  const slotNotes=(records.get(ps.record_key)?.answer_slots??[]).filter(x=>!x.mapped&&!x.skip).map(x=>`原题空位${x.slot_index+1}保持空白：${x.note??x.answer?.note??'条件未能唯一确定，详见解析'}`);
  slide.speakerNotes.text=`原书第${ps.book_page}页，PDF原页序${ps.source_page}，题号${ps.question_id}，稳定标识${ps.record_key}。`+(teacherNote?'\n教学资料说明：'+(typeof teacherNote==='string'?teacherNote:JSON.stringify(teacherNote)):'' )+(slotNotes.length?'\n'+slotNotes.join('\n'):'');
  index.push({slide:si+1,book_page:ps.book_page,source_page:ps.source_page,question_id:ps.question_id,record_key:ps.record_key,continuation:ps.continuation,subquestions:ps.subquestions,final_answer_slots:sm.answer_slots,table_final_answers:sm.table_answers,review_label:ps.review_label,click_count:sm.clicks.length});
  if(previews&&(previewEvery===1||(previewEvery>1&&si%previewEvery===0))){await fs.mkdir(previews,{recursive:true});const png=await presentation.export({slide,format:'png',scale:1});await fs.writeFile(path.join(previews,`slide_${String(si+1).padStart(4,'0')}.png`),new Uint8Array(await png.arrayBuffer()));}
  if((si+1)%25===0)process.stdout.write(JSON.stringify({slides_built:si+1,total:plan.slides.length,rss_mb:Math.round(process.memoryUsage().rss/1048576)})+'\n');
 }
 await fs.mkdir(path.dirname(draft),{recursive:true});const stagedDraft=draft+'.'+randomUUID()+'.tmp.pptx';await (await PresentationFile.exportPptx(presentation)).save(stagedDraft);const stagedHandle=await fs.open(stagedDraft,'r');await stagedHandle.sync();await stagedHandle.close();await fs.rename(stagedDraft,draft);
 await fs.writeFile(manifestPath,JSON.stringify(manifest,null,2));await fs.writeFile(manifestPath.replace(/\.json$/,'.index.json'),JSON.stringify(index,null,2));
 return {slides:plan.slides.length,records:plan.record_count,draft,manifestPath};
}

async function main(){
 const a=args();if(!a.input)throw Error('--input required');const data=JSON.parse(await fs.readFile(a.input,'utf8'));
 const plan=planDeck(data,{strict:a.mode==='build'});
 const report={slides:plan.slides.length,records:plan.record_count,errors:plan.error_count,issues:plan.issues,estimated:plan.estimated,per_page:{}};
 for(const s of plan.slides)report.per_page[s.book_page]=(report.per_page[s.book_page]??0)+1;
 if(a.plan){await fs.mkdir(path.dirname(a.plan),{recursive:true});await fs.writeFile(a.plan,JSON.stringify(plan,null,2));}
 if(a.report){await fs.mkdir(path.dirname(a.report),{recursive:true});await fs.writeFile(a.report,JSON.stringify(report,null,2));}
 console.log(JSON.stringify({...report,issues:undefined,per_page:undefined}));
 if(a.mode==='build'){
  if(!a.draft||!a.manifest)throw Error('--draft and --manifest required');
  console.log(JSON.stringify(await buildDeck(data,plan,{draft:a.draft,manifestPath:a.manifest,font:a.font??'Droid Sans Fallback',previews:a.previews,previewEvery:Number(a['preview-every']??0)})));
 }
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(e=>{console.error(e.stack);process.exitCode=1;});
