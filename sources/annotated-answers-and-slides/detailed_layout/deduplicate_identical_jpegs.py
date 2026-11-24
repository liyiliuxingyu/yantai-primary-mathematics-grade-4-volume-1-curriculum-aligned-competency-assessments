#!/usr/bin/env python3
"""Conservatively deduplicate identical embedded JPEGs, then compare every page.

Never edits the input. A candidate is retained only when every rendered RGB pixel
at the requested scale and every extracted text string is unchanged. The common
case is the same original JPEG stored once as DeviceRGB and once as ICCBased.
"""
import argparse, collections, hashlib, json, os, time
from pathlib import Path
import fitz
import numpy as np

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def image_groups(doc):
    groups=collections.defaultdict(list);images=0
    for xref in range(1,doc.xref_length()):
        if doc.xref_get_key(xref,'Subtype')!=('name','/Image'):continue
        images+=1
        img=doc.extract_image(xref)
        if not img or img['ext']!='jpeg':continue
        # Extra mask/decode guards keep transparency and decode semantics intact.
        guards=tuple((name,doc.xref_get_key(xref,name))for name in
                     ['Filter','SMask','Mask','Decode','DecodeParms','ImageMask','Interpolate'])
        key=(hashlib.sha256(img['image']).hexdigest(),img['width'],img['height'],img['bpc'],guards)
        groups[key].append({'xref':xref,'color_space':doc.xref_get_key(xref,'ColorSpace'),
                            'jpeg_bytes':len(img['image'])})
    return groups,images

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--qa',type=Path,required=True)
    p.add_argument('--scale',type=float,default=2);a=p.parse_args()
    if a.input.resolve()==a.output.resolve():raise ValueError('Never overwrite the input')
    if a.output.exists():raise ValueError('Candidate exists; choose a new output revision')
    started=time.time();source_sha=digest(a.input);doc=fitz.open(a.input)
    groups,before_images=image_groups(doc);replacements=[]
    for key,entries in groups.items():
        if len(entries)<2:continue
        entries.sort(key=lambda row:(row['color_space']!=('name','/DeviceRGB'),row['xref']))
        keep=entries[0]
        for duplicate in entries[1:]:
            doc.xref_copy(keep['xref'],duplicate['xref'])
            replacements.append({'keep':keep,'replace':duplicate,'jpeg_sha256':key[0],
                                 'width':key[1],'height':key[2],'bpc':key[3]})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    doc.save(a.output,garbage=4,deflate=True);doc.close()
    with a.output.open('rb')as f:os.fsync(f.fileno())
    candidate_sha=digest(a.output);candidate_bytes=a.output.stat().st_size
    old=fitz.open(a.input);new=fitz.open(a.output);assert len(old)==len(new)
    _,after_images=image_groups(new);pages=[];total_different=0;text_different=[]
    for i in range(len(old)):
        assert old[i].rect==new[i].rect,(i+1,'page dimensions')
        x=old[i].get_pixmap(matrix=fitz.Matrix(a.scale,a.scale),colorspace=fitz.csRGB,alpha=False)
        y=new[i].get_pixmap(matrix=fitz.Matrix(a.scale,a.scale),colorspace=fitz.csRGB,alpha=False)
        assert (x.width,x.height,x.n)==(y.width,y.height,y.n)
        delta=0;maximum=0
        if x.samples!=y.samples:
            aa=np.frombuffer(x.samples,dtype=np.uint8).reshape(x.height,x.width,x.n)
            bb=np.frombuffer(y.samples,dtype=np.uint8).reshape(y.height,y.width,y.n)
            delta=int(np.any(aa!=bb,axis=2).sum())
            maximum=int(np.max(np.abs(aa.astype(np.int16)-bb.astype(np.int16))))
        same_text=old[i].get_text()==new[i].get_text()
        if not same_text:text_different.append(i+1)
        total_different+=delta
        pages.append({'pdf_page':i+1,'width_px':x.width,'height_px':x.height,
                      'different_rgb_pixels':delta,'max_channel_difference':maximum,
                      'extracted_text_identical':same_text})
        if (i+1)%16==0:print('Compared',i+1,'pages; changed RGB pixels',total_different,flush=True)
    assert digest(a.input)==source_sha,'Input changed during comparison'
    accepted=total_different==0 and not text_different and not new.is_repaired
    old.close();new.close()
    report={'accepted':accepted,'passed':accepted,'source_pdf':str(a.input.resolve()),
            'source_sha256':source_sha,'source_bytes':a.input.stat().st_size,
            'candidate_pdf':str(a.output.resolve()),'candidate_sha256':candidate_sha,
            'candidate_bytes':candidate_bytes,'bytes_saved':a.input.stat().st_size-candidate_bytes,
            'source_image_xrefs':before_images,'candidate_image_xrefs':after_images,
            'identical_jpeg_replacements':len(replacements),'replacements':replacements,
            'pages_compared':len(pages),'render_scale':a.scale,'different_rgb_pixels_total':total_different,
            'text_different_pages':text_different,'pages':pages,'elapsed_seconds':time.time()-started,
            'scope':'Only original-JPEG byte hashes with matching dimensions, bpc, filters and mask/decode guards were merged. DeviceRGB preferred. All pages independently rendered at the recorded scale and compared pixel by pixel.',
            'pipeline_changed':False,'candidate_retained':accepted,
            'reuse_limit':'This proves only the exact source SHA above. A later full2 file needs its own independent candidate and all-page comparison.'}
    if not accepted:a.output.unlink()
    a.qa.parent.mkdir(parents=True,exist_ok=True);a.qa.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k not in['pages','replacements']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
