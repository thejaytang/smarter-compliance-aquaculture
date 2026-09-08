from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from openpyxl import Workbook

from pdf_extraction.intake import system1
from pdf_extraction.intake.registry import IntakeError, build_manifest, read_registry
from tests.contracts.test_source_intake import source, row, store


def fixture(tmp_path, monkeypatch, effective='INCLUDE'):
    root=tmp_path/'system1'; config=root/'Code/config/config.json';config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'workbook':'../../registry.xlsx','source_root':'../../Data'}))
    registry=root/'registry.xlsx'; record=row(source());record['selection_status']='=IF(1=1,"INCLUDE","PENDING")'
    w=Workbook();s=w.active;s.title='Source Register';s.append(['Display']);s.append(list(record));s.append(list(record.values()));w.save(registry);w.close()
    store(root/'Data',source())
    reply={'ok':True,'data':{'revision':'b'*64,'sources':[dict(record,effective_selection=effective,source_revision='revision-1')]}}
    calls=[]
    def call(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(returncode=0,stdout=json.dumps(reply))
    monkeypatch.setattr(system1.subprocess,'run',call)
    return root,registry,reply,calls


def test_authority_supplies_selection_when_cache_is_empty_without_writes(tmp_path,monkeypatch):
    root,registry,_,calls=fixture(tmp_path,monkeypatch)
    before=registry.read_bytes()
    rows,digest=read_registry(registry)
    assert rows[0]['selection_status'] is None
    assert not build_manifest(rows,digest,root/'Data',{'PA001'})['items']
    handoff=system1.read_system1(root)
    manifest=build_manifest(handoff.records,handoff.registry_sha256,handoff.source_root,{'PA001'})
    assert len(manifest['items'])==1 and not manifest['rejected']
    assert registry.read_bytes()==before and handoff.registry_sha256==sha256(before).hexdigest()
    command,kwargs=calls[0]
    assert command==[str(root/'Code/.venv/bin/python'),'-m','system1.workbench_bridge']
    assert json.loads(kwargs['input'])=={'command':'read','config':str(root/'Code/config/config.json')}
    assert kwargs['env']['PYTHONPATH']==str(root/'Code/src')
    assert handoff.evidence['sources']['PA001']['source_revision']=='revision-1'


@pytest.mark.parametrize('effective',['PENDING','EXCLUDE'])
def test_human_include_does_not_override_system1_effective_selection(tmp_path,monkeypatch,effective):
    root,_,_,_=fixture(tmp_path,monkeypatch,effective)
    handoff=system1.read_system1(root)
    result=build_manifest(handoff.records,handoff.registry_sha256,handoff.source_root,{'PA001'})
    assert not result['items'] and result['rejected'][0]['fields']==['selection_status']


@pytest.mark.parametrize('mutation',['missing_selection','duplicate_source','missing_revision','wrong_identity','failure','invalid_json'])
def test_malformed_authority_receipt_is_rejected(tmp_path,monkeypatch,mutation):
    root,_,reply,_=fixture(tmp_path,monkeypatch)
    if mutation=='missing_selection':reply['data']['sources'][0].pop('effective_selection')
    elif mutation=='duplicate_source':reply['data']['sources']*=2
    elif mutation=='missing_revision':reply['data']['sources'][0].pop('source_revision')
    elif mutation=='wrong_identity':reply['data']['sources'][0]['source_id']='PA002'
    elif mutation=='failure':reply['ok']=False
    else:monkeypatch.setattr(system1.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='broken'))
    with pytest.raises(IntakeError,match='invalid_read_receipt'):system1.read_system1(root)


def test_changed_authority_is_not_published(tmp_path,monkeypatch):
    root,registry,reply,_=fixture(tmp_path,monkeypatch)
    def changed(*args,**kwargs):
        registry.write_bytes(b'external change')
        return SimpleNamespace(returncode=0,stdout=json.dumps(reply))
    monkeypatch.setattr(system1.subprocess,'run',changed)
    with pytest.raises(IntakeError,match='changed_during_handoff'):system1.read_system1(root)


def test_live_cli_binds_handoff_and_record_projection(tmp_path,monkeypatch):
    from pdf_extraction.orchestration.source_batch import main
    root,registry,_,_=fixture(tmp_path,monkeypatch)
    out=tmp_path/'result'
    monkeypatch.setattr('sys.argv',['source_batch','--system1',str(root),'--source-id','PA001','--output',str(out)])
    assert main()==0
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['selection_authority']['sha256']==sha256((out/'system1-handoff.json').read_bytes()).hexdigest()
    assert (out/'PA001-001/source-records.json').is_file()
    assert read_registry(registry)[0][0]['selection_status'] is None
