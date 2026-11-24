#!/usr/bin/env python3
"""Inspect native text bounds in every real LibreOffice PDF page.

Outlined mathematics/TikZ still need geometric package checks and visual review.
"""
import argparse,json
from pathlib import Path
import fitz
HERE=Path(__file__).resolve().parent

def main(version):
    issues=[];pages=0;spans=0
    for n in range(1,7):
        b=HERE/f'build{n:02d}_{version}';status=json.loads((b/'progress.json').read_text());static=Path(status.get('actual_static_dir',str(b/'actual_static_export')));metadata=Path(status.get('metadata_dir',str(b)));pdf=static/(Path(status['final']).stem+'.pdf');index=json.loads((metadata/'manifest.index.json').read_text())
        if not pdf.exists():issues.append({'volume':n,'missing_pdf':True});continue
        with fitz.open(pdf) as doc:
            for i,page in enumerate(doc):
                pages+=1
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines',[]):
                        for s in line['spans']:
                            spans+=1;x0,y0,x1,y1=s['bbox']
                            # Footer and deliberately small carry labels are not
                            # body paragraphs. Bounds are PDF points (3/4 px).
                            if s['size']<20:continue
                            if x0<0 or x1>938 or y0<0 or y1>501.8:
                                issues.append({'volume':n,'slide':i+1,'record_key':index[i]['record_key'],'text':s['text'],'font_points':s['size'],'bbox':s['bbox']})
    report={'version':version,'pages_inspected':pages,'native_text_spans_inspected':spans,'findings':issues,'scope':'Native PDF text bounds only. Outlined equations and TikZ are outside text extraction; this is not a mathematical correctness or animation playback test.'}
    (HERE/f'actual_geometry_audit_{version}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'pages':pages,'spans':spans,'findings':len(issues)},ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--version',default='v7');a=p.parse_args();main(a.version)
