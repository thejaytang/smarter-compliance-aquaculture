"""Restore the dated full development seed in a new, isolated local workspace."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
from local_workbench.workspace_integrity import inspect
from local_workbench.workspace_package import validate

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'workbench/deployment'))
from restore_initial_data import restore


def verify(destination):
    seed=ROOT/'workbench/initial-data/workspace-20260922.zip'
    digest='cd5d033e4cfa10ae91838589b773720d9388918122cb43058d1fa61f9bb05bc0'
    raw=seed.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==digest
    _,manifest=validate(raw)
    destination.mkdir()
    for name in ('config','schedule'):
        target=destination/'workbench/config/system1'/(name+'.example.json')
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'workbench/config/system1'/target.name,target)
    restored=restore(destination,seed,digest)
    stores=destination/'workbench/workspace/databases'
    report=inspect(stores,destination/'workbench/workspace/sources')
    assert len(report['originals'])==len(manifest['originals'])==76
    assert len(report['bindings'])==len(manifest['bindings'])==157
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stores.glob('*.sqlite')}
    assert set(before)=={'system1.sqlite','system2.sqlite','system3_requirements.sqlite','system3_scd.sqlite'}
    try:
        restore(destination,seed,digest)
    except ValueError as error:
        assert 'already has work' in str(error)
    else:
        raise AssertionError('Existing workspace was overwritten.')
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in stores.glob('*.sqlite')}
    result={'status':'passed','restoration':restored,'verified_originals':76,
            'verified_bindings':157,'stores':sorted(before),'existing_work_rejected_unchanged':True,
            'platform':sys.platform,'native_windows':sys.platform=='win32'}
    (ROOT/'project-support/validation/branch-split-20260922/full-seed-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    verify(Path(sys.argv[1]))
