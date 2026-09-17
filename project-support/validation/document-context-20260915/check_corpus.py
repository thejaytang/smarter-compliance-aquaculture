"""Read all current System1 HTML/PDF originals using isolated reader caches."""
from pathlib import Path
from hashlib import sha256
from tempfile import TemporaryDirectory
import json
from bs4 import BeautifulSoup
from pdf_extraction.evidence.material_reader import read_material
ROOT=Path(__file__).resolve().parents[2]
rows=[]
for source in sorted((ROOT/'system1/Data').rglob('*')):
    if source.suffix.lower() not in {'.html','.pdf'}: continue
    raw=source.read_bytes(); digest=sha256(raw).hexdigest()
    row={'path':str(source.relative_to(ROOT)), 'sha256':digest, 'bytes':len(raw)}
    try:
        with TemporaryDirectory(prefix='document-context-') as folder:
            copy=Path(folder)/('source'+source.suffix);copy.write_bytes(raw)
            result=read_material(copy,digest)
            assert result['source_sha256']==digest
            row['kind']=result['kind']
            if result['kind']=='html':
                info=result['document_information'];soup=BeautifulSoup(raw,'lxml')
                explicit=soup.select_one('#documentMeta')
                title=explicit.find('h1') if explicit else soup.select_one('main h1, article h1')
                headings=[el for el in soup.find_all('h1') if not el.find_parent(['nav','aside','footer'])]
                if title is None and len(headings)==1: title=headings[0]
                expected_title=title.get_text(' ',strip=True) if title else '\n'.join(el.get_text(' ',strip=True) for el in soup.select('p.oj-doc-ti')) or (soup.title.get_text(' ',strip=True) if soup.title else None)
                assert (info['title']['value'] if info['title'] else None)==expected_title
                expected=[]
                if explicit:
                    for tr in explicit.select('tr'):
                        label,value=tr.find('th'),tr.find('td')
                        if label and value and value.get_text(strip=True): expected.append((label.get_text(' ',strip=True),value.get_text(' ',strip=True)))
                assert [(f['label'],f['value']) for f in info['fields']]==expected
                rendered=BeautifulSoup(result['html'],'lxml')
                for field in [part for field in ([info['title']] if info['title'] else [])+info['fields'] for part in field.get('parts',[field])]:
                    if not field.get('anchor'): continue
                    target=rendered.find(id=field['anchor']);assert target is not None
                    assert ' '.join(target.get_text(' ',strip=True).split())==' '.join(field['value'].split())
                row.update(title=info['title']['value'] if info['title'] else None,fields=len(info['fields']),explicit_metadata=explicit is not None)
            else:
                row['pages']=result['pages'];assert result['image'].startswith('data:image/png;base64,')
                last=read_material(copy,digest,page=result['pages'])
                assert last['page']==result['pages'] and last['image'].startswith('data:image/png;base64,')
                assert 'document_information' not in result
            assert copy.read_bytes()==raw
        assert sha256(source.read_bytes()).hexdigest()==digest
        row['status']='PASS'
    except Exception as exc:row.update(status='FAIL',error=repr(exc))
    rows.append(row)
    print(source.name.split('_')[0],row['status'],row.get('error',''),flush=True)
out=Path(__file__).with_name('corpus-results.json');out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total':len(rows),'passed':sum(r['status']=='PASS' for r in rows),'failures':[r for r in rows if r['status']=='FAIL'],'missing_html_title':[r['path'] for r in rows if r.get('kind')=='html' and not r.get('title')]}),flush=True)
