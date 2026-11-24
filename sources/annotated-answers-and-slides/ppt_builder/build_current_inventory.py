#!/usr/bin/env python3
"""Publish only exact, immutable, finalized and statically exported revisions."""
import argparse,hashlib,json
from pathlib import Path

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--version',default='v8');ap.add_argument('--required-subdir',default='validated_final_all');ap.add_argument('--output',type=Path,default=HERE/'current_inventory.json');a=ap.parse_args()
    volumes=[]
    for n in range(1,7):
        build=HERE/f'build{n:02d}_{a.version}';status=json.loads((build/'progress.json').read_text())
        if status.get('stage')!='complete':raise ValueError(f'Volume {n} is not complete')
        final=Path(status['final']).resolve();metadata=Path(status['metadata_dir']).resolve();static=Path(status['actual_static_dir']).resolve();prov=Path(status['export_provenance']).resolve()
        if a.required_subdir and not final.parent.name.startswith(a.required_subdir):raise ValueError(f'Volume {n} has not reached the required immutable revision')
        digest=sha(final);receipt=json.loads(Path(status['receipt']).read_text());export=json.loads(prov.read_text());index=metadata/'manifest.index.json';manifest=metadata/'manifest.json'
        if digest!=receipt['finalSha256'] or digest!=export['source_sha256']:raise ValueError(f'Volume {n} final/receipt/export disagree')
        normalized=json.loads((metadata/'normalized.json').read_text())
        current_rules=json.loads((HERE/'teaching_order.json').read_text())['records']
        if any(r.get('teaching_order')!=current_rules.get(r['key']) for r in normalized['records']):raise ValueError(f'Volume {n} has stale applicable conclusion ordering')
        rows=json.loads(index.read_text());slides=json.loads(manifest.read_text())['slides'];decoded=static/'decoded_images_manifest.json'
        if len(rows)!=status['slides'] or len(slides)!=len(rows) or len(list(static.glob('slide-*.png')))!=len(rows):raise ValueError(f'Volume {n} slide coverage mismatch')
        seal=json.loads(decoded.read_text())
        if seal['source_sha256']!=digest or seal['pages_fully_decoded']!=len(rows):raise ValueError(f'Volume {n} decoded image seal mismatch')
        if any(sha(static/row['png'])!=row['sha256'] for row in seal['pngs']):raise ValueError(f'Volume {n} raster changed after its full decode seal')
        volumes.append({'volume':n,'current_pptx':str(final),'sha256':digest,'index_path':str(index),'index_sha256':sha(index),'manifest_path':str(manifest),'manifest_sha256':sha(manifest),'metadata_dir':str(metadata),'actual_static_dir':str(static),'export_provenance':str(prov),'export_provenance_sha256':sha(prov),'decoded_images_manifest':str(decoded),'decoded_images_manifest_sha256':sha(decoded),'slide_count':len(rows),'receipt_path':str(Path(status['receipt']).resolve())})
    freeze=HERE.parent/'source_release_freeze.json'
    result={'schema':'suyang-current-ppt-inventory-v1','version':a.version,'source_release_freeze':str(freeze.resolve()),'source_release_freeze_sha256':sha(freeze),'slide_count':sum(v['slide_count'] for v in volumes),'volumes':volumes,'scope':'Immutable finalized PPTX revisions and actual LibreOffice static export provenance. No PowerPoint slideshow playback claim.'}
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(str(a.output.resolve()))

if __name__=='__main__':main()
