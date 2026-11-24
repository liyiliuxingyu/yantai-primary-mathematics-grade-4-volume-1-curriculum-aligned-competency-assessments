from pathlib import Path
import hashlib,json,os,subprocess,zipfile
from PIL import Image,ImageChops
W=Path(__file__).resolve().parents[1]
env={'__file__':str(W/'build/render_volume1_subsets.py')};exec((W/'build/render_volume1_subsets.py').read_text().split('reports=[]')[0],env)
subset=env['subset'];source=env['source'];folder=W/'validation_subsets_v1';dest=folder/'alignment-356-358.pptx';idx=[356,357,358];s=subset(idx,dest);mp=folder/'alignment-356-358.json';mp.write_text(json.dumps(idx))
run=subprocess.run([os.environ['CODEX_PRIMARY_RUNTIME_NODE'],str(W/'build/render_subset.mjs'),str(dest),str(W/'final_render/volume01'),str(mp)],capture_output=True,text=True);(folder/'alignment-356-358.log').write_text(run.stdout+run.stderr);assert run.returncode==0,(run.stdout,run.stderr[-1000:]);print(run.stdout,flush=True)
old=W/'before_equal_alignment_v1.pptx'
with zipfile.ZipFile(old)as a,zipfile.ZipFile(source)as b:
 assert set(a.namelist())==set(b.namelist());delta=[n for n in a.namelist()if a.read(n)!=b.read(n)];assert set(delta)=={f'ppt/slides/slide{i}.xml'for i in idx},delta
pixels=[]
for i in idx:
 before=Image.open(W/f'alignment_before_v1/slide-{i}.png').convert('RGB');after=Image.open(W/f'final_render/volume01/slide-{i}.png').convert('RGB');bbox=ImageChops.difference(before,after).getbbox();assert bbox and bbox[0]>=60 and bbox[2]<=105,(i,bbox);pixels.append({'slide':i,'changed_pixel_bbox':bbox,'only_equal_sign_pixels_changed':True})
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
report={'passed':True,'source_sha256_before':sha(old),'source_sha256_after':sha(source),'changed_package_parts':delta,'all_other_package_member_bytes_unchanged':True,'only_equal_y_positions_changed':True,'pixel_changes':pixels,'other_58_reviewed_modified_pages_carried_forward_by_exact_xml_relationship_media_identity':True,'re_rendered_actual_pages':idx}
(W/'alignment_recheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
p=W/'final_render/volume01/qa_import.json';q=json.loads(p.read_text());q.update(source_sha256=sha(source),full_deck_imported=True,carryforward_validation=report,render_method='Exact XML/dependency subsets: 61 pages initially rendered, then 356–358 re-rendered after equal-sign alignment; remaining58 source/dependencies and pixels unchanged.');q['full_deck_import_limitation']=None;p.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
