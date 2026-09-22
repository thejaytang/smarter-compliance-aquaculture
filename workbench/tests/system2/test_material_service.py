from pathlib import Path
"""Isolated owning-store integration checks; no business originals or decisions."""
from hashlib import sha256
import base64
import sqlite3
from types import SimpleNamespace
import uuid

import pytest

from pdf_extraction.orchestration.material_service import MaterialService
from pdf_extraction.orchestration import material_parser


RAW = b'<html><body><h1>Fixture heading</h1><p>Original paragraph</p><table><tr><td>A</td><td>B</td></tr></table></body></html>'


def request(material=None, **extra):
    result = dict(request_id=str(uuid.uuid4()), actor='Isolated named reviewer')
    if material:
        result.update(material_id=material['id'], expected_revision=material['revision'])
    return dict(result, **extra)


def register(root, raw=RAW, generation=1):
    folder = root / 'registered'
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = f'TS001-{generation:03}'
    filename = snapshot + '_fixture.html'
    path = folder / filename
    path.write_bytes(raw)
    return dict(source_id='TS001', snapshot_id=snapshot, folder_code='registered', stored_filename=filename,
        content_hash=sha256(raw).hexdigest(), file_format='html', operator_selection_decision='INCLUDE',
        selection_status='INCLUDE', snapshot_status='STORED', source_status='CURRENT', download_status='SUCCESS',
        source_title='Isolated HTML material')


@pytest.fixture
def integration(tmp_path, monkeypatch):
    root = tmp_path / 'originals'
    row = register(root)
    handoff = SimpleNamespace(records=[row], registry_sha256='a'*64, source_root=root, assert_current=lambda: None)
    service = MaterialService(tmp_path / 'workflow', tmp_path / 'system1')
    monkeypatch.setattr(service, 'handoff', lambda: handoff)
    with service.store.connect() as db:
        db.execute('CREATE TABLE events(sequence INTEGER PRIMARY KEY, kind TEXT, data TEXT)')
        db.execute("INSERT INTO events VALUES(1,'historic','unaltered human decision')")
    return service, handoff


def test_open_read_save_confirm_are_not_parser_triggers(integration, monkeypatch):
    service, handoff = integration
    def forbidden(*args, **kwargs):
        pytest.fail('A display/save/confirmation implicitly invoked parsing')
    monkeypatch.setattr(material_parser, 'parse_material', forbidden)
    opened = service.open(request(source_id='TS001'))
    assert service.open(request(source_id='TS001'))['id'] == opened['id']
    assert len(service.store.list()) == 1
    assert service.read(opened['id'])['blocks'] == []
    assert 'Original paragraph' in service.reader(opened['id'])['html']
    block = dict(id='manual-1', type='text', text='Manually transcribed original', source_refs=[{'scope_id':'html:document'}])
    saved = service.mutate('save', request(opened, blocks=[block], association_reviewed=True))['material']
    confirmed = service.mutate('confirm', request(saved, explicit_confirmation=True, checked_scope=['html:document'],
        omissions_checked=True, dependencies_checked=True))['material']
    assert confirmed['content_status'] == 'content_review_complete'
    assert service.store.pending_candidates() == []
    assert service.tick()['status'] == 'idle'
    with service.store.connect() as db:
        assert [tuple(r) for r in db.execute('SELECT * FROM events')] == [(1,'historic','unaltered human decision')]


def test_source_replacement_keeps_pinned_original_and_human_history(integration):
    service, handoff = integration
    original = service.open(request(source_id='TS001'))
    pinned_before = service._path(original['source']).read_bytes()
    block = dict(id='manual-1',type='text',text='Preserved human correction',source_refs=[{'scope_id':'html:document'}])
    saved = service.mutate('save', request(original, blocks=[block]))['material']
    handoff.records = [register(handoff.source_root, b'<html><body>Changed upstream version</body></html>', 2)]
    new = service.open(request(source_id='TS001'))
    old = service.read(original['id'])
    assert old['source_stale'] and old['blocks'] == [block]
    assert new['id'] != old['id'] and new['blocks'] == []
    assert 'Original paragraph' in service.reader(old['id'])['html']
    assert 'Changed upstream' in service.reader(new['id'])['html']
    assert Path(service.original(old['id'])['path']).read_bytes() == pinned_before == RAW
    assert service.read(old['id'], revision=saved['revision'])['blocks'] == [block]


def test_explicit_extract_runs_real_html_parser_candidate_only_and_retries(integration, monkeypatch):
    service, _ = integration
    opened = service.open(request(source_id='TS001'))
    extract_request = request(opened)
    started = service.mutate('extract', extract_request)
    assert service.mutate('extract', extract_request) == started
    parsed = service.tick()
    assert parsed['candidate']['status'] == 'ready', parsed
    assert any(b['text'] == 'Original paragraph' for b in parsed['candidate']['blocks'])
    assert parsed['material']['blocks'] == []
    assert parsed['material']['confirmation'] is None
    assert service.tick()['status'] == 'idle'
    assert len(service.store.read(opened['id'])['candidates']) == 1
    assert parsed['candidate']['metadata']['canonical_artifacts']
    with service.store.connect() as db:
        assert db.execute('SELECT count(*) FROM events').fetchone()[0] == 1
    current = service.store.read(opened['id'])
    adopted = service.mutate('adopt', request(current, candidate_id=started['candidate']['id'], action='adopt', reviewed_against_source=True))['material']
    assert adopted['blocks'] and adopted['confirmation'] is None


def test_worker_failure_keeps_saved_draft_and_explicit_retry(integration, monkeypatch):
    service, _ = integration
    opened = service.open(request(source_id='TS001'))
    saved = service.mutate('save', request(opened, blocks=[dict(id='manual',type='text',text='Saved before failure',source_refs=[{'scope_id':'html:document'}])]))['material']
    service.mutate('extract', request(saved))
    real = material_parser.parse_material
    def failure(*args, **kwargs):
        raise ValueError('Isolated parser failure')
    monkeypatch.setattr(material_parser, 'parse_material', failure)
    result = service.tick()
    assert result['candidate']['status'] == 'failed'
    assert result['material']['blocks'] == saved['blocks']
    assert service.tick()['status'] == 'idle'
    monkeypatch.setattr(material_parser, 'parse_material', real)
    restarted = MaterialService(service.root, service.system1)
    monkeypatch.setattr(restarted, 'handoff', service.handoff)
    newer = restarted.mutate('extract', request(restarted.read(saved['id'])))
    assert newer['candidate']['id'] != result['candidate']['id']
    retried = restarted.tick()
    assert retried['candidate']['status'] == 'ready'
    assert len(retried['material']['candidates']) == 2
    assert retried['material']['blocks'] == saved['blocks']


def test_source_unavailability_preserves_save_but_blocks_confirmation(integration, monkeypatch):
    service, _ = integration
    material = service.open(request(source_id='TS001'))
    def unavailable():
        raise OSError('isolated System1 unavailable')
    monkeypatch.setattr(service, 'handoff', unavailable)
    read = service.read(material['id'])
    assert read['source_check_error']
    saved = service.mutate('save', request(material, blocks=[]))['material']
    with pytest.raises(OSError, match='System1 unavailable'):
        service.mutate('confirm', request(saved, explicit_confirmation=True, checked_scope=['html:document']))
    assert service.mutate('process', request(saved))['status'] == 'unavailable'
    assert service.store.read(material['id'])['revision'] == saved['revision']


def test_corrupt_pinned_original_blocks_reader_extract_and_confirmation(integration):
    service, _ = integration
    material = service.open(request(source_id='TS001'))
    service._path(material['source']).write_bytes(b'corrupted isolated pin')
    with pytest.raises(ValueError):
        service.reader(material['id'])
    with pytest.raises(ValueError, match='integrity'):
        service.mutate('extract', request(material))
    with pytest.raises(ValueError, match='integrity'):
        service.mutate('confirm', request(material, explicit_confirmation=True, checked_scope=['html:document']))


def test_store_open_receipt_retains_original_identity_after_upstream_change(integration):
    service, handoff = integration
    material = service.open(request(source_id='TS001'))
    command = request(source_id='TS001')
    initial = service.store.open(material['source'], material['title'], material['scope'], request=command)
    handoff.records = [register(handoff.source_root, b'<html><body>Next snapshot</body></html>', 2)]
    new = service.open(request(source_id='TS001'))
    replay = service.store.open_receipt(command)
    assert replay['id'] == initial['id'] != new['id']
    assert replay['source_stale']
    with pytest.raises(ValueError, match='reused'):
        service.store.open_receipt(dict(command, actor='Another reviewer'))


def test_source_open_issue_without_legacy_id_blocks_confirmation_only_for_its_source(integration):
    service,handoff=integration
    material=service.open(request(source_id='TS001'))
    saved=service.mutate('save',request(material,blocks=[]))['material']
    handoff.evidence={'source_open_issues':[{'source_id':'TS001','task_id':'native-report','reason':'Original appendix missing'}],
        'original_issues':[]}
    assert service.open(request(source_id='TS001'))['source_issues'][0]['task_id']=='native-report'
    assert service.listing()['materials'][0]['source_issues'][0]['task_id']=='native-report'
    saved=service.mutate('save',request(saved,blocks=[]))['material']
    assert saved['source_issues'][0]['task_id']=='native-report'
    command=request(saved,explicit_confirmation=True,checked_scope=['html:document'])
    with pytest.raises(ValueError,match='original document issue in System1'):
        service.mutate('confirm',command)
    assert service.store.read(saved['id'])['confirmation'] is None
    assert service.store.read(saved['id'])['revision']==saved['revision']
    handoff.evidence['source_open_issues'][0]['source_id']='TS002'
    confirmed=service.mutate('confirm',command)['material']
    assert confirmed['confirmation']['actor']=='Isolated named reviewer'
    assert confirmed['requirement_status']=='not_connected'


def test_explicit_legacy_service_import_preserves_effective_text_and_unresolved_issue(integration,monkeypatch):
    import json
    from pdf_extraction.domains.requirements import classification
    service,handoff=integration
    material=service.open(request(source_id='TS001'))
    legacy={'id':'legacy-document','source':material['source'],'revision':7,'units':[
        {'id':'legacy-paragraph','kind':'source_text','version':4,'dependencies':[],
         'original':{'fields':{'body':'Original paragraph'},'references':[{'locator':'/html/body/p[1]'}],'structure':[]},
         'edits':{'body':'Preserved named reviewer correction'},'content_human':True}],
        'history':[{'actor':'Prior reviewer','action':'correct'}],'issues':['Legacy missing figure requires review']}
    with service.store.connect() as db:
        db.execute('CREATE TABLE documents(id TEXT PRIMARY KEY,data TEXT)')
        db.execute('INSERT INTO documents VALUES(?,?)',(legacy['id'],json.dumps(legacy)))
    monkeypatch.setattr(classification,'propose',lambda *a,**k:pytest.fail('Import triggered classification'))
    monkeypatch.setattr(material_parser,'parse_material',lambda *a,**k:pytest.fail('Import triggered parser'))
    command=request(material)
    imported=service.mutate('import-legacy',command)
    assert service.mutate('import-legacy',command)==imported
    assert imported['material']['blocks']==[] and imported['material']['confirmation'] is None
    candidate_detail=service.store.candidate_detail(material['id'],imported['candidate']['id'])
    assert candidate_detail['blocks'][0]['text']=='Preserved named reviewer correction'
    assert candidate_detail['metadata']['legacy_provenance']['revision']==7
    assert candidate_detail['metadata']['imported_issues']
    adopted=service.mutate('adopt',request(imported['material'],candidate_id=imported['candidate']['id'],
        action='adopt',reviewed_against_source=True,association_reviewed=True))['material']
    assert adopted['blocks'][0]['text']=='Preserved named reviewer correction'
    assert adopted['confirmation'] is None and adopted['issues']
    with pytest.raises(ValueError,match='unresolved_content_issues'):
        service.mutate('confirm',request(adopted,explicit_confirmation=True,checked_scope=['html:document']))
    with service.store.connect() as db:
        assert json.loads(db.execute('SELECT data FROM documents').fetchone()[0])==legacy
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]==1


def test_source_timeout_preserves_partial_save_and_blocks_confirmation(integration,monkeypatch):
    import subprocess
    service,_=integration
    material=service.open(request(source_id='TS001'))
    def timed_out(): raise subprocess.TimeoutExpired('isolated authority read',60)
    monkeypatch.setattr(service,'handoff',timed_out)
    assert service.read(material['id'])['source_check_error']
    saved=service.mutate('save',request(material,blocks=[]))['material']
    assert saved['source_check_error']
    with pytest.raises(subprocess.TimeoutExpired):
        service.mutate('confirm',request(saved,explicit_confirmation=True,checked_scope=['html:document']))


def test_empty_parser_result_remains_repairable_without_claiming_complete(integration):
    service, handoff = integration
    handoff.records = [register(handoff.source_root, b'<html><body></body></html>', 2)]
    material = service.open(request(source_id='TS001'))
    service.mutate('extract', request(material))
    result = service.tick()
    candidate = result['candidate']
    assert candidate['status'] == 'partial' and not candidate['complete']
    assert candidate['metadata']['parser_status'] == 'empty'
    assert candidate['metadata']['processed_scope'] == ['html:document']
    assert candidate['metadata']['usable_scope'] == []
    assert candidate['metadata']['unprocessed_scope'] == []
    current = service.read(material['id'])
    summary = current['candidates'][0]['extraction']
    assert summary['parser_status'] == 'empty' and summary['usable_scope_count'] == 0
    assert summary['processed_scope_count'] == 1 and summary['unresolved_count'] == 1
    with pytest.raises(ValueError, match='partial_candidate'):
        service.mutate('adopt', request(current, candidate_id=candidate['id'], action='adopt', reviewed_against_source=True))
    repair = dict(id='manual', type='text', text='Isolated manual repair', source_refs=[{'scope_id':'html:document'}])
    saved = service.mutate('candidate-draft', request(current, candidate_id=candidate['id'], blocks=[repair], issues=[]))['material']
    assert saved['blocks'] == [repair] and saved['confirmation'] is None
    detail = service.store.candidate_detail(material['id'], candidate['id'])
    assert detail['metadata']['parser_status'] == 'empty' and detail['blocks'] == []
    assert detail['resolution']['reviewed_against_source'] is False


def test_partial_scope_evidence_survives_worker_restart_and_keeps_human_overlay(integration, monkeypatch):
    service, _ = integration
    material = service.open(request(source_id='TS001'))
    manual = dict(id='manual', type='text', text='Previously saved human work', source_refs=[{'scope_id':'html:document'}])
    saved = service.mutate('save', request(material, blocks=[manual]))['material']
    service.mutate('extract', request(saved))
    evidence = {'parser_version':'material-structural-parser/2', 'status':'partial', 'blocks':[manual],
        'covered_scope':['html:document'], 'processed_scope':['html:document'], 'usable_scope':['html:document'],
        'unprocessed_scope':[], 'unresolved':[{'scope_id':'html:document','code':'incomplete_layout','message':'Check omitted layout content'}], 'warnings':['Engineering partial result'], 'canonical_artifacts':[]}
    monkeypatch.setattr(material_parser, 'parse_material', lambda *args, **kwargs: evidence)
    result = service.tick()
    restarted = MaterialService(service.root, service.system1)
    monkeypatch.setattr(restarted, 'handoff', service.handoff)
    current = restarted.read(saved['id'])
    assert current['blocks'] == [manual] and current['confirmation'] is None
    assert current['candidates'][0]['extraction']['parser_status'] == 'partial'
    assert current['candidates'][0]['extraction']['unresolved_count'] == 1
    assert restarted.store.candidate_detail(saved['id'], result['candidate']['id'])['metadata']['unresolved'] == evidence['unresolved']


def test_caption_and_cell_edits_survive_actual_save_and_reopen(integration, monkeypatch, tmp_path):
    import json
    import subprocess
    service, handoff = integration
    opened = service.open(request(source_id='TS001'))
    original = service._path(opened['source'])
    raw_before = original.read_bytes()
    attachment = tmp_path / 'synthetic-attachment.png'
    attachment.write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jlp8AAAAASUVORK5CYII='))
    attachment_before = attachment.read_bytes()
    ref = {'scope_id':'html:document', 'anchor':'original-document'}
    blocks = [
        {'id':'image-r4','type':'image','text':'Original caption', 'source_refs':[ref],
         'image':{'attachment':attachment.name,'attribution':'Synthetic credited image','source_ref':ref}},
        {'id':'table-r4','type':'table','text':'Retained table caption','source_refs':[ref],
         'table':{'rows':[['Header',''],['Old cell','Unchanged']],
                  'merges':[{'row':0,'col':0,'rowspan':1,'colspan':2}], 'notes':['Retained table note']}}
    ]
    saved = service.mutate('save', request(opened, blocks=blocks))['material']
    root = Path(__file__).resolve().parents[3]
    script = '''import fs from 'node:fs';
import {blockMarkdown,updateMarkdownBlock,MarkdownNotebook} from './workbench/frontend/components/markdown-content.js';
const original=JSON.parse(fs.readFileSync(0,'utf8'));
const current=updateMarkdownBlock(original,'image-r4',blockMarkdown(original[0]).replace('Original caption','Corrected caption'));
const owner={draft:{blocks:current},collaboration:{readonly:false},changed(){}};
const notebook=new MarkdownNotebook(owner);
notebook.change('table-r4',blockMarkdown(current[1]).replace('Old cell','Corrected cell'));
process.stdout.write(JSON.stringify(owner.draft.blocks));'''
    edited = json.loads(subprocess.run(['node','--input-type=module','-e',script],input=json.dumps(blocks),
        text=True,capture_output=True,cwd=root,check=True).stdout)
    updated = service.mutate('save', request(saved, blocks=edited))['material']
    reopened = MaterialService(service.root, service.system1)
    monkeypatch.setattr(reopened, 'handoff', lambda: handoff)
    actual = reopened.read(updated['id'])
    assert actual['revision'] == saved['revision'] + 1
    assert actual['blocks'][0]['type'] == 'image'
    assert actual['blocks'][0]['text'] == 'Corrected caption'
    assert actual['blocks'][0]['image'] == blocks[0]['image']
    assert actual['blocks'][0]['source_refs'] == blocks[0]['source_refs']
    assert actual['blocks'][1]['table'] == dict(blocks[1]['table'], rows=[['Header',''],['Corrected cell','Unchanged']])
    assert actual['blocks'][1]['text'] == blocks[1]['text']
    assert actual['blocks'][1]['source_refs'] == blocks[1]['source_refs']
    assert original.read_bytes() == raw_before and attachment.read_bytes() == attachment_before
    assert actual.get('confirmation') is None
