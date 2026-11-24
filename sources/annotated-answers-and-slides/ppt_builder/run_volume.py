#!/usr/bin/env python3
"""Reproducible sequential per-volume author pipeline. Parent marker only."""
import argparse,hashlib,json,os,subprocess,time,shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
WORK=HERE.parent
NODE=os.environ['CODEX_PRIMARY_RUNTIME_NODE']
PYTHON=os.environ['CODEX_PRIMARY_RUNTIME_PYTHON']
FONT=WORK/'recovered/source/new_work/DroidSansFallback.ttf'

def run(cmd,log,timeout=600):
    with log.open('w') as out:
        p=subprocess.run([str(x) for x in cmd],stdout=out,stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode:raise RuntimeError(str(log)+' failed with '+str(p.returncode))

def build_volume(number,version='v4',finalize_only=False,final_subdir='validated'):
    start=(number-1)*18+1;end=number*18
    build=HERE/f'build{number:02d}_{version}';build.mkdir(exist_ok=True)
    if number==3:(build/'store_package.flag').write_text('Standard ZIP_STORED packaging; exact parts retained, full finalizer/import still required.\n')
    final=build/final_subdir/f'小学四上同步素养卷第{number}册讲解课件答案.pptx'
    if final.exists():raise RuntimeError('Immutable final revision already exists; choose a new --final-subdir: '+str(final))
    status={'volume':number,'version':version,'range':[start,end],'stage':'normalizing'}
    def save(stage):
        status['stage']=stage;(build/'progress.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
        print(json.dumps({k:v for k,v in status.items() if k not in ('source_record_sha256',)},ensure_ascii=False),flush=True)
    normalized=build/'normalized.json';ready=build/'ready.json'
    if not finalize_only:
        save('normalizing')
        run([PYTHON,HERE/'convert_inputs.py','--questions',WORK/'questions','--start',start,'--end',end,'--out',normalized],build/'normalize.log')
        save('compiling_assets')
        run([PYTHON,HERE/'compile_assets.py','--normalized',normalized,'--directory',HERE/'assets','--font',FONT,'--out',ready],build/'assets.log')
        save('building_and_rendering_all_slides')
        run([NODE,'--max-old-space-size=6144',HERE/'build_deck.mjs','--input',ready,'--mode','build','--draft',build/'base.pptx','--manifest',build/'manifest.json','--previews',build/'previews','--preview-every',1,'--report',build/'layout.json'],build/'build.log',timeout=900)
        save('adding_native_math_and_animation')
        run([PYTHON,HERE/'patch_ooxml.py','--input',build/'base.pptx','--output',build/'candidate.pptx','--manifest',build/'manifest.json','--report',build/'package_report.json'],build/'patch.log')
    final.parent.mkdir(exist_ok=True)
    if final.exists():
        raise RuntimeError('Immutable final revision already exists; choose a new --final-subdir: '+str(final))
    save('finalizing')
    receipt=build/('validation_receipt.json' if final_subdir=='validated' else f'validation_receipt_{final_subdir}.json')
    if receipt.exists():
        receipt.rename(receipt.with_name('validation_receipt_'+str(time.time_ns())+'.superseded.json'))
    run([NODE,'--max-old-space-size=6144',HERE/'finalize_deck.mjs','--candidate',build/'candidate.pptx','--final',final,'--receipt',receipt],build/'finalize.log')
    data=json.loads(normalized.read_text());manifest=json.loads((build/'manifest.json').read_text());layout=json.loads((build/'layout.json').read_text())
    metadata=final.parent/'metadata';metadata.mkdir(exist_ok=True)
    for name in ['normalized.json','ready.json','manifest.json','manifest.index.json','package_report.json','layout.json']:
        shutil.copyfile(build/name,metadata/name)
    shutil.copyfile(receipt,metadata/'validation_receipt.json')
    if (WORK/'source_release_freeze.json').exists():shutil.copyfile(WORK/'source_release_freeze.json',metadata/'source_release_freeze.json')
    status.update(records=len(data['records']),slides=len(manifest['slides']),formulas=sum(len(s.get('formulas',[])) for s in manifest['slides']),clicks=sum(len(s.get('clicks',[])) for s in manifest['slides']),final=str(final.resolve()),receipt=str((metadata/'validation_receipt.json').resolve()),metadata_dir=str(metadata.resolve()),bytes=final.stat().st_size,previews=str(build/'previews'),source_record_sha256={r['key']:hashlib.sha256(json.dumps(r['raw'],ensure_ascii=False,sort_keys=True).encode()).hexdigest() for r in data['records']},vertical_metadata_sha256=data.get('vertical_metadata_sha256'),oral_metadata_sha256=data.get('oral_metadata_sha256'),final_answers_sha256=data.get('final_answers_sha256'),math_display_sha256=data.get('math_display_sha256'),answer_slots=sum(len(s.get('answer_slots',[])) for s in manifest['slides']))
    save('complete')
    (metadata/'progress.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
    return status

def main():
    p=argparse.ArgumentParser();p.add_argument('--start-volume',type=int,default=1);p.add_argument('--end-volume',type=int,default=6);p.add_argument('--version',default='v4');p.add_argument('--finalize-only',action='store_true');p.add_argument('--final-subdir',default='validated');a=p.parse_args()
    results=[]
    for n in range(a.start_volume,a.end_volume+1):results.append(build_volume(n,a.version,a.finalize_only,a.final_subdir))
    (HERE/f'run_{a.version}_summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
