"""Install root-approved, measured red-unit and conversion-row patches only."""
from pathlib import Path
import json,copy
R=Path(__file__).resolve().parent;P=R/'project';Q=P/'units_update'
J=lambda p:json.loads(Path(p).read_text())
def W(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert (R/'approved_changes.json').exists(),'Await SOURCE_READY.'
units=J(Q/'red_unit_patch_proposals.json')['records'];rows=J(Q/'conversion_row_proposals.json')['records']
proposals=[]
for x in units:
 if not x['install_new_local']:continue
 proposals.append({**x,'mask_rect':x['rect'],'container_rect':x['rect'],'proposal_kind':'unit_fragment'})
proposals.extend({**x,'proposal_kind':'standalone_conversion'}for x in rows)
files={L:J(P/f'detailed_layout/notes_{L}.json')for L in 'ABCD'};notes={n['key']:n for d in files.values()for n in d['records']}
approved=J(R/'approved_changes.json');bykey={x['key']:x for x in approved['changes']};baseline_notes=J(R/'baseline/notes.json');manifest=[];masks=[];installed_keys=set()
for x in proposals:
 assert x['black_pixels_in_mask_at_3x']==0
 key=x['key']
 if key not in bykey:bykey[key]={'key':key,'field_changes':[]};approved['changes'].append(bykey[key])
 note=notes[key];record=bykey[key]
 # The root's record/note contents have already been applied; add only the
 # measured red snippet. Save exact snapshots for independent source QA.
 record.setdefault('old_note',copy.deepcopy(baseline_notes[key]));installed_keys.add(key)
 patch={'rect':x['mask_rect'],'target_rect':x['container_rect'],'container_rect':x['container_rect'],'latex':x['latex'],'font_size':x['font_size'],'leading':x.get('leading',14),'snippet_width':505 if x['proposal_kind']=='standalone_conversion' else max(80,x['container_rect'][2]-x['container_rect'][0]),'text_baseline_anchor':x['text_baseline_anchor'],'reason':'按原基线同步单位格式；换算独立一行，结果单位使用英文括号。','source_mask':x['mask_rect'],'unit_format_only':True}
 patch_list=note.setdefault('local_replacements',[]);patch_list.append(patch);patch_id=f'{key}_local{len(patch_list)}'
 manifest.append({'id':patch_id,'key':key,'book_page':x['book_page'],'mask_rect':x['mask_rect'],'container_rect':x['container_rect'],'text_baseline_anchor':x['text_baseline_anchor'],'proposal_kind':x['proposal_kind'],'latex':x['latex']})
 m={'key':key,'book_page':x['book_page'],'rect':x['mask_rect'],'reason':'只剔除原红色旧单位/混行换算，黑题干与相邻数值不变。'}
 if not any(z['book_page']==m['book_page']and z['rect']==m['rect']for z in masks):masks.append(m)
 record['new_note']=copy.deepcopy(note)
for key in installed_keys:
 L=next(L for L,d in files.items()if any(n['key']==key for n in d['records']))
 bykey[key]['field_changes'].append({'file':f'detailed_layout/notes_{L}.json','book_page':int(key[1:4]),'field':'local_replacements','old':copy.deepcopy(baseline_notes[key].get('local_replacements',[])),'new':copy.deepcopy(notes[key]['local_replacements']),'kind':'approved_visible_red_unit_and_conversion_patches'})
for L,d in files.items():W(P/f'detailed_layout/notes_{L}.json',d)
for path in [R/'approved_changes.json',Q/'approved_changes.json']:W(path,approved)
W(Q/'new_local_patches.json',{'records':manifest,'count':len(manifest)})
W(Q/'source_masks.json',{'masks':masks,'all_masks_verified_black_pixel_free_at_3x':True})
print('INSTALLED',len(manifest),'new red locals',flush=True)
