"""Fresh restoration, exact saved-content readback and overwrite protection."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
from local_workbench.server import Application
from backend.system3.requirements import Requirements
from backend.system3.interpretations import Interpretations
from local_workbench.workspace_integrity import inspect
from build_example_seed import ROOT, MID

sys.path.insert(0, str(ROOT/'workbench/deployment'))
from restore_initial_data import restore


def saved(root):
    app = Application(root/'workbench', code_root=ROOT, start_workers=False)
    try:
        c = app.collaboration
        assert [s['source_id'] for s in c.source_records()] == ['PE002']
        actor = 'Weijie Tang'
        m = c.read_material(actor, MID)
        r = Requirements(c)
        sessions = [r.read(actor, s['id']) for s in r.listing(actor, MID)['sessions']]
        assert len(sessions) == 21
        scd = Interpretations(c)
        interpretations = {uid:scd.read(actor, uid) for s in sessions for uid in s['units']}
        return {'blocks':m['blocks'], 'sessions':sessions, 'interpretations':interpretations}
    finally:
        app.close()


def verify(seed, destination):
    destination.mkdir()
    for name in ('config', 'schedule'):
        target = destination/'workbench/config/system1'/(name+'.example.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT/'workbench/config/system1'/target.name, target)
    digest = hashlib.sha256(seed.read_bytes()).hexdigest()
    result = restore(destination, seed, digest)
    original = saved(seed.parent/'producer')
    restored = saved(destination)
    assert restored['blocks'] == original['blocks']
    for first, second in zip(original['sessions'], restored['sessions'], strict=True):
        for key in ('id','units','roots','structures','source_segments','source','text'):
            assert first.get(key) == second.get(key), key
    assert set(restored['interpretations']) == set(original['interpretations'])
    for uid, first in original['interpretations'].items():
        second = restored['interpretations'][uid]
        for key in ('fields','check_design','card_reviews','review_status','context_snapshot','session_id','session_revision'):
            assert first.get(key) == second.get(key), (uid,key)
    assert saved(destination) == restored, 'Restart changed saved state.'
    dbs = destination/'workbench/workspace/databases'
    before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dbs.glob('*.sqlite')}
    try:
        restore(destination, seed, digest)
    except ValueError as error:
        assert 'already has work' in str(error)
    else:
        raise AssertionError('Existing work was overwritten.')
    assert before == {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in dbs.glob('*.sqlite')}
    integrity = inspect(dbs, destination/'workbench/workspace/sources')
    assert {x['source_id'] for x in integrity['originals']} == {'PE002'}
    report = {'status':'passed', 'sha256':digest, 'restoration':result, 'exact_blocks':85,
              'exact_active_requirements':21, 'exact_active_interpretations':21,
              'restart_readback':'passed', 'existing_work_rejected_unchanged':'passed',
              'source_ids':['PE002'], 'platform':sys.platform, 'native_windows':sys.platform=='win32'}
    (ROOT/'project-support/validation/branch-split-20260922/example-seed-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
