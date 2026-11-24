"""Replace two explicitly guarded PDF-reference a:t values without re-exporting PPTX.

All non-target ZIP members, object IDs, and timing XML must remain byte-identical.
The input/output paths are explicit; this script never switches the release inventory.
"""
from pathlib import Path
import argparse,hashlib,json,re,zipfile
from xml.sax.saxutils import escape
from lxml import etree

HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
NS={'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'p':'http://schemas.openxmlformats.org/presentationml/2006/main'}

def timing(xml):
    match=re.search(rb'<p:timing(?:\s[^>]*)?>.*?</p:timing>',xml,re.S)
    return match.group(0) if match else b''

def shape_ids(xml):
    root=etree.fromstring(xml)
    return [dict(x.attrib) for x in root.findall('.//p:cNvPr',NS)]

def patch(source,dest,overrides,report_path):
    config=json.loads(overrides.read_text())
    before_bytes=source.read_bytes()
    assert sha(before_bytes)==config['expected_input_sha256'],'Unexpected source revision'
    assert source.resolve()!=dest.resolve(),'Use a separate immutable output directory'
    assert not dest.exists(),'Refuse to overwrite an existing immutable output'
    replacements={f'ppt/slides/slide{x["slide"]}.xml':x for x in config['replacements']}
    changes=[]
    dest.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(source) as before,zipfile.ZipFile(dest,'w') as after:
        after.comment=before.comment
        for item in before.infolist():
            data=before.read(item.filename)
            if item.filename in replacements:
                spec=replacements[item.filename]
                old=escape(spec['old']).encode('utf-8');new=escape(spec['new']).encode('utf-8')
                assert data.count(old)==1,(item.filename,'Exact target not unique')
                root=etree.fromstring(data)
                matches=[x for x in root.findall('.//a:t',NS) if x.text==spec['old']]
                assert len(matches)==1,(item.filename,'Target must be one complete editable a:t')
                changed=data.replace(old,new,1)
                assert timing(data)==timing(changed)
                assert shape_ids(data)==shape_ids(changed)
                changes.append({'slide':spec['slide'],'zip_part':item.filename,
                                'old':spec['old'],'new':spec['new'],
                                'before_sha256':sha(data),'after_sha256':sha(changed),
                                'timing_sha256':sha(timing(data)),
                                'shape_ids_unchanged':True,'timing_xml_byte_identical':True})
                data=changed
            after.writestr(item,data)
    with zipfile.ZipFile(source) as before,zipfile.ZipFile(dest) as after:
        assert after.testzip() is None
        assert before.namelist()==after.namelist()
        changed_parts=[n for n in before.namelist() if before.read(n)!=after.read(n)]
        assert sorted(changed_parts)==sorted(replacements)
        slide_parts=[n for n in before.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        assert len(slide_parts)==464
        assert all(timing(before.read(n))==timing(after.read(n)) for n in slide_parts)
        assert all(shape_ids(before.read(n))==shape_ids(after.read(n)) for n in slide_parts)
        report={'passed':True,'source':str(source.resolve()),'source_sha256':sha(before_bytes),
                'output':str(dest.resolve()),'output_sha256':sha(dest.read_bytes()),
                'slides':len(slide_parts),'changed_zip_parts':changed_parts,
                'all_other_zip_member_bytes_identical':True,
                'all_464_slide_shape_ids_and_timing_byte_identical':True,
                'replacements':changes,
                'scope':'直接替换两个完整a:t文本值；未重建幻灯片、未改变其余组件、页脚、ID、原生动画和形状顺序。播放行为未在PowerPoint测试。'}
    report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'passed':True,'output_sha256':report['output_sha256'],'changed_parts':changed_parts},ensure_ascii=False))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--overrides',type=Path,default=HERE/'pdf_pointer_overrides.json')
    p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    patch(a.source,a.output,a.overrides,a.report)
