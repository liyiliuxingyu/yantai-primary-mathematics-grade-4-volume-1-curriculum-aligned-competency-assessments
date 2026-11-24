#!/usr/bin/env python3
"""Correct source-base versus actual input PDF page labels without reauthoring."""
import argparse,json,zipfile,os,uuid,copy
from pathlib import Path
from lxml import etree as E
HERE=Path(__file__).resolve().parent
NS={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def correct(source,out,store_package=False):
    index_path=source.parent/'manifest.index.json';manifest_path=source.parent/'manifest.json'
    index=json.loads(index_path.read_text());manifest=json.loads(manifest_path.read_text());mapping=json.loads((HERE.parent/'recovered/source/source_page_map.json').read_text())
    byslide={}
    for item in index:
        item['input_pdf_page']=mapping[str(item['source_page'])]+1;byslide[item['slide']]=item
    for s in manifest['slides']:
        x=byslide[s['slide']];s.update(book_page=x['book_page'],source_page=x['source_page'],input_pdf_page=x['input_pdf_page'],continuation=x['continuation'])
    index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2));manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    # Never expose a .pptx path while its central directory is still unwritten.
    temporary=out.with_name(out.name+'.'+uuid.uuid4().hex+'.zip.tmp')
    with zipfile.ZipFile(source) as zin,zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as zout:
        for part in zin.infolist():
            data=zin.read(part.filename)
            if part.filename.startswith('ppt/slides/slide') and part.filename.endswith('.xml'):
                number=int(part.filename.rsplit('slide',1)[1][:-4]);x=byslide[number];root=E.fromstring(data)
                foot=root.xpath('.//p:sp[p:nvSpPr/p:cNvPr[@name="source"]]//a:t',namespaces=NS)
                if not foot:raise RuntimeError('Source footer missing on slide '+str(number))
                foot[0].text=f"原题底本第{x['source_page']}页　输入PDF第{x['input_pdf_page']}页"+(f"　解析续页{x['continuation']}" if x['continuation']>1 else '')
                for t in foot[1:]:t.text=''
                data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            elif part.filename.startswith('ppt/notesSlides/notesSlide') and part.filename.endswith('.xml'):
                root=E.fromstring(data)
                for t in root.xpath('.//a:t',namespaces=NS):
                    if t.text:
                        import re
                        t.text=re.sub(r'PDF原页序(\d+)',lambda m:f"原题底本第{m[1]}页，输入PDF第{mapping[m[1]]+1}页",t.text).replace('保持空白：','未填定值（放映显示条件提示）：')
                data=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
            entry=copy.copy(part)
            if store_package:entry.compress_type=zipfile.ZIP_STORED
            zout.writestr(entry,data)
    with temporary.open('rb') as stream:os.fsync(stream.fileno())
    with zipfile.ZipFile(temporary) as check:
        if check.testzip():raise RuntimeError('Corrected temporary package failed CRC')
    os.replace(temporary,out)
    directory_fd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory_fd)
    finally:os.close(directory_fd)
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--store-package',action='store_true');a=p.parse_args();correct(a.input,a.output,a.store_package)
