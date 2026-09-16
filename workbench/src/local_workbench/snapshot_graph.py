"""Content-addressed full snapshots. No filesystem/business writes in merge logic.

Ancestry, not timestamps, decides whether a received record can replace a local
record. Missing records never mean deletion. Concurrent structures remain explicit.
"""
from copy import deepcopy
from collections import deque
from .collaboration import fingerprint
from .collaboration_merge import merge_documents


def node(key, value, parents=(), actor='Baseline', at=None):
    result = {'key': key, 'value': deepcopy(value), 'parents': sorted(set(parents)), 'actor': actor, 'at': at}
    result['id'] = fingerprint(result)
    return result


def validate_graph(nodes, heads):
    if not isinstance(nodes, dict) or not isinstance(heads, dict) or len(nodes) > 100000:
        raise ValueError('Invalid snapshot version inventory.')
    for identity, item in nodes.items():
        if not isinstance(item, dict) or set(item) != {'id','key','value','parents','actor','at'}:
            raise ValueError('Invalid snapshot version record.')
        if identity != item['id'] or fingerprint({k:v for k,v in item.items() if k != 'id'}) != identity:
            raise ValueError('Snapshot version fingerprint differs.')
        if (not isinstance(item['key'],str) or len(item['key']) > 300 or not isinstance(item['value'],dict)
                or not isinstance(item['parents'],list) or len(item['parents']) > 100
                or len(set(item['parents'])) != len(item['parents']) or not isinstance(item['actor'],str)):
            raise ValueError('Invalid snapshot version fields.')
        if any(p not in nodes or nodes[p]['key'] != item['key'] for p in item['parents']):
            raise ValueError('Snapshot ancestry is missing or belongs to another record.')
    # Kahn traversal rejects cycles without recursion or an unbounded ancestor walk.
    degrees = {i:len(n['parents']) for i,n in nodes.items()}; children = {i:[] for i in nodes}
    for i,n in nodes.items():
        for p in n['parents']: children[p].append(i)
    pending = deque(i for i,v in degrees.items() if not v); seen = 0
    while pending:
        i = pending.popleft(); seen += 1
        for child in children[i]:
            degrees[child] -= 1
            if degrees[child] == 0: pending.append(child)
    if seen != len(nodes): raise ValueError('Snapshot version ancestry contains a cycle.')
    for key, values in heads.items():
        if not isinstance(values,list) or not values or len(values)>100 or len(set(values))!=len(values):
            raise ValueError('Invalid current snapshot versions.')
        if any(i not in nodes or nodes[i]['key']!=key for i in values):
            raise ValueError('Snapshot head belongs to another record.')
    return nodes


def ancestors(nodes, identity):
    distances={identity:0}; pending=deque([identity])
    while pending:
        i=pending.popleft()
        for p in nodes[i]['parents']:
            if p not in distances: distances[p]=distances[i]+1;pending.append(p)
    return distances


def tips(nodes, identities):
    identities=list(dict.fromkeys(identities)); remove=set()
    for identity in identities:remove.update(set(ancestors(nodes,identity))-{identity})
    return [i for i in identities if i not in remove]


def compare(nodes, left, right, decisions=None):
    """A deterministic merge result, with saved decisions bound to both heads."""
    ours,theirs=nodes[left],nodes[right]
    if ours['key']!=theirs['key']:raise ValueError('Cannot synchronize different records.')
    a,b=ancestors(nodes,left),ancestors(nodes,right)
    if right in a:return {'head':left,'status':'kept_local','differences':[],'unresolved':[]}
    if left in b:return {'head':right,'status':'updated','differences':[],'unresolved':[]}
    common=set(a)&set(b)
    bases=tips(nodes,sorted(common)) if common else []
    pair=fingerprint([left,right]); chosen=(decisions or {}).get(pair,{})
    if ours['value']==theirs['value']:
        result={'merged':ours['value'],'differences':[],'unresolved':[]}
    elif len(bases)==1 and not ours['key'].startswith('requirements:'):
        result=merge_documents(nodes[bases[0]]['value'],ours['value'],theirs['value'],chosen,version=2)
    else:
        # Unrelated or ambiguous merge bases: never invent a baseline.
        identity='whole-record';choice=chosen.get(identity,{}).get('action')
        if choice not in (None,'current','incoming'):raise ValueError('Choose one complete record version.')
        result={'merged':theirs['value'] if choice=='incoming' else ours['value'],
            'differences':[{'id':identity,'path':'','label':'Complete saved record','kind':'record',
                'current':ours['value'],'incoming':theirs['value'],'base':None,'conflict':True,'resolution':choice}],
            'unresolved':[] if choice else [identity]}
    differences=[dict(d,pair=pair,reviewer=theirs['actor']) for d in result['differences']]
    if result['unresolved']:
        return {'head':left,'status':'conflict','differences':differences,'unresolved':result['unresolved'],'pair':pair}
    merged=node(ours['key'],result['merged'],[left,right],actor='Synchronization',at=None)
    nodes[merged['id']]=merged
    return {'head':merged['id'],'status':'merged','differences':differences,'unresolved':[],'pair':pair}


def preview(local_nodes, local_heads, incoming_nodes, incoming_heads, decisions=None):
    nodes=deepcopy(local_nodes)
    for identity,item in incoming_nodes.items():
        if identity in nodes and nodes[identity]!=item:raise ValueError('Conflicting version identity.')
        nodes[identity]=deepcopy(item)
    validate_graph(nodes,{**local_heads,**incoming_heads})
    results=[];heads=deepcopy(local_heads)
    for key in sorted(incoming_heads):
        local=local_heads.get(key,[]); candidates=tips(nodes,[*local,*incoming_heads[key]])
        if not candidates:continue
        current=next((i for i in local if i in candidates),candidates[0]); conflicts=[];diffs=[]
        status='new' if not local else 'unchanged' if candidates==local else 'updated'
        for other in candidates:
            if other==current:continue
            result=compare(nodes,current,other,decisions)
            diffs.extend(result['differences'])
            if result['unresolved']:
                conflicts.extend(dict(d,key=key) for d in result['differences'] if d['id'] in result['unresolved'])
            else:current=result['head'];status=result['status']
        heads[key]=[current] if not conflicts else candidates
        results.append({'key':key,'status':'conflict' if conflicts else status,'head':current,
            'contributors':sorted({nodes[a]['actor'] for i in candidates for a in ancestors(nodes,i) if nodes[a]['actor'] not in ('Baseline','Synchronization')}),
            'conflicts':conflicts,'differences':diffs})
    return {'nodes':nodes,'heads':heads,'items':results,'conflicts':[d for r in results for d in r['conflicts']]}
