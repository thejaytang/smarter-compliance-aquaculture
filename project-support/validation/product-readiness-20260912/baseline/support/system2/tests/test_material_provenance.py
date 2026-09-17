from copy import deepcopy
import json
import uuid

from pdf_extraction.review.materials import MaterialStore
from pdf_extraction.review.material_provenance import record_changes
from .test_materials import source, scope, text, req


def test_old_adoption_provenance_survives_projection_reconstruction_without_history_rewrite(tmp_path):
    store = MaterialStore(tmp_path)
    material = store.open(source(), 'Old immutable history fixture', scope())
    base = {k: v for k, v in material.items() if k not in
            ('candidates', 'conflicts', 'related_versions', 'provenance_version', 'collaboration_provenance')}
    first = deepcopy(base)
    first.update(revision=1, content_revision=1, blocks=[text('Ana text')],
                 last_action={'kind':'saved','actor':'Ana Jokic','at':'2026-09-12T00:00:00+00:00'})
    second = deepcopy(first)
    second.update(revision=2, content_revision=2, blocks=[text('Daniel correction')],
        last_action={'kind':'collaboration_adopted','actor':'Weijie Tang','at':'2026-09-12T00:01:00+00:00'},
        collaboration_provenance=[{'path':'/blocks/b1/text','actor':'Daniel Restad','origin':'human',
            'adopter':'Weijie Tang','adopted_revision':2,'status':'human_unreviewed'}])
    # Construct a pre-projection fixture, not a mutation of real historical data.
    with store.transaction() as db:
        db.execute('DELETE FROM material_revisions');db.execute('DELETE FROM material_revision_index')
        db.execute('UPDATE material_documents SET data=? WHERE id=?', (json.dumps(second), material['id']))
        for version in [base, first, second]:
            db.execute('INSERT INTO material_revisions VALUES(?,?,?)',
                       (material['id'], version['revision'], json.dumps(version)))
    original_history = store.history(material['id'])
    current = store.save(req(second))['material']
    assert current['collaboration_provenance'][0]['actor'] == 'Daniel Restad'
    assert current['collaboration_provenance'][0]['adopted_revision'] == 2
    assert current['provenance_version'] == 1
    assert store.history(material['id'])[1:] == original_history


def table_material():
    return {'id':'fixture','revision':4,'content_revision':2,'source':{'content_hash':'h'},
        'blocks':[{'id':'table/one','type':'table','text':'Shared table','source_refs':[{'scope_id':'page:1'}],
                   'table':{'rows':[['Ana unchanged','Old Daniel']], 'merges':[], 'notes':[]}}],
        'collaboration_provenance':[
            {'path':'/blocks/table~1one','origin':'human','actor':'Weijie Tang','adopter':'Weijie Tang','adopted_revision':1},
            {'path':'/blocks/table~1one/table/rows/0/0','origin':'human','actor':'Ana Jokic','adopter':'Weijie Tang','adopted_revision':2},
            {'path':'/blocks/table~1one/table/rows/0/1','origin':'human','actor':'Daniel Restad','adopter':'Weijie Tang','adopted_revision':3}]}


def test_cell_save_preserves_other_author_and_old_adoption_in_same_table():
    before = table_material();after = deepcopy(before)
    after['blocks'][0]['table']['rows'][0][1] = 'New Daniel'
    after['content_revision'] += 1;after['revision'] += 1
    record_changes(before, after, 'saved', 'Daniel Restad', '2026-09-12T00:00:00+00:00')
    records = {r['path']:r for r in after['collaboration_provenance']}
    assert records['/blocks/table~1one/table/rows/0/0'] == before['collaboration_provenance'][1]
    assert records['/blocks/table~1one'] == before['collaboration_provenance'][0]
    assert records['/blocks/table~1one/table/rows/0/1']['actor'] == 'Daniel Restad'
    assert records['/blocks/table~1one/table/rows/0/1']['content_revision'] == 3


def test_structural_table_change_marks_whole_block_without_claiming_cell_correspondence():
    before = table_material();after = deepcopy(before)
    after['blocks'][0]['table']['rows'].append(['New row','Another cell'])
    record_changes(before, after, 'saved', 'Daniel Restad', '2026-09-12T00:00:00+00:00')
    assert len(after['collaboration_provenance']) == 1
    record = after['collaboration_provenance'][0]
    assert record['path'] == '/blocks/table~1one' and record['actor'] == 'Daniel Restad'
    assert record['scope_review_required'] is True and record['attribution_scope'] == 'whole_block'


def test_new_adoption_stamps_only_pending_choice_not_unmodified_contributors():
    before = table_material();after = deepcopy(before)
    after['blocks'][0]['table']['rows'][0][1] = 'Coordinator choice'
    after['revision'] = 5
    after['collaboration_provenance'].append({'path':'/blocks/table~1one/table/rows/0/1',
        'actor':'Daniel Restad','origin':'human','status':'pending_adoption'})
    record_changes(before, after, 'collaboration_adopted', 'Weijie Tang', '2026-09-12T00:00:00+00:00')
    assert after['collaboration_provenance'][:-1] == before['collaboration_provenance']
    assert after['collaboration_provenance'][-1]['adopted_revision'] == 5
    assert after['collaboration_provenance'][-1]['adopter'] == 'Weijie Tang'


def test_direct_manual_merge_attributes_each_changed_block_and_preserves_other_fields():
    before = table_material()
    before['blocks'].extend([text('first','b1'), text('second','b2')])
    after = deepcopy(before);after['blocks'][1]['text']='new first';after['blocks'][2]['text']='new second'
    record_changes(before, after, 'candidate_merge', 'Ana Jokic', '2026-09-12T00:00:00+00:00')
    records = {r['path']:r for r in after['collaboration_provenance']}
    assert records['/blocks/b1/text']['actor'] == records['/blocks/b2/text']['actor'] == 'Ana Jokic'
    assert records['/blocks/table~1one/table/rows/0/0'] == before['collaboration_provenance'][1]
