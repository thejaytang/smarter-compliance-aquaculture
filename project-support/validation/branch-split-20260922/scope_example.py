"""Derive the authorized PE002-only logical package from a frozen full export."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import uuid
import zipfile
from backend.shared.collaboration_exchange import unpack, pack
from local_workbench.snapshot_graph import node, validate_graph

SOURCE = 'PE002'
MATERIAL = 'c3fd36db7f5b246d56f3c1bbd3f21ca5'


def build(archive, destination):
    with zipfile.ZipFile(archive) as z:
        full = unpack(z.read('logical-workspace.zip'))
    old = full['metadata']
    keys = {'source:' + SOURCE, 'review:' + SOURCE, 'material:' + MATERIAL, 'requirements:shared'}
    nodes, remap, evidence = {}, {}, {}

    def retain(identity):
        if identity in remap:
            return remap[identity]
        prior = old['nodes'][identity]
        parents = [retain(p) for p in prior['parents']]
        value = deepcopy(prior['value'])
        if prior['key'] == 'requirements:shared':
            value['sessions'] = [s for s in value['sessions'] if s['document']['material_id'] == MATERIAL]
            sessions = {s['document']['id'] for s in value['sessions']}
            units = {uid for s in value['sessions'] for step in s['steps'] for uid in step['document']['units']}
            value['interpretations'] = [i for i in value['interpretations'] if i['unit_id'] in units]
            value['candidates'] = [c for c in value['candidates'] if c.get('unit_id') in units]
            value['owners'] = {sid:owner for sid,owner in value['owners'].items() if sid in sessions}
            assert all(s['document']['source']['source_id'] == SOURCE for s in value['sessions'])
        current = node(prior['key'], value, parents, prior['actor'], prior['at'])
        remap[identity] = current['id']
        nodes[current['id']] = current
        if identity in old['evidence']:
            evidence[current['id']] = deepcopy(old['evidence'][identity])
        return current['id']

    heads = {key:[retain(h) for h in old['heads'][key]] for key in sorted(keys)}
    validate_graph(nodes, heads)
    digests = set()
    for n in nodes.values():
        if n['key'].startswith('source:'):
            digests.add(n['value']['content_hash'])
        elif n['key'].startswith('material:'):
            digests.add(n['value']['binding']['source']['content_hash'])
    files = {'originals/' + h:full['files']['originals/' + h] for h in digests}
    assert len(files) == 1
    assert all(hashlib.sha256(raw).hexdigest() == key.removeprefix('originals/') for key,raw in files.items())
    metadata = {**old, 'id':str(uuid.uuid4()), 'nodes':nodes, 'heads':heads, 'evidence':evidence, 'history':[]}
    raw = pack('collection', metadata, files)
    destination.write_bytes(raw)
    value = nodes[heads['requirements:shared'][0]]['value']
    summary = {'source_id':SOURCE, 'material_id':MATERIAL, 'source_export_id':old['id'], 'package_id':metadata['id'],
               'keys':sorted(keys), 'originals':len(files), 'sessions_including_history':len(value['sessions']),
               'active_requirements':sum(not s['document'].get('deleted') for s in value['sessions']),
               'interpretations_including_history':len(value['interpretations']), 'bytes':len(raw),
               'sha256':hashlib.sha256(raw).hexdigest()}
    assert summary['active_requirements'] == 21
    destination.with_suffix('.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    build(Path(sys.argv[1]), Path(sys.argv[2]))
