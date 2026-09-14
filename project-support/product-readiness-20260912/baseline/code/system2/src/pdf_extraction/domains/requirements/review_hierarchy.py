"""Project existing Canonical hierarchy without inferring missing section semantics."""
from copy import deepcopy
from ...contracts.hashing import digest


def project(units,canonicals):
    identities={}
    for u in units:
        if u['kind']=='coverage' or u.get('superseded_by'):continue
        for r in u['original'].get('references',[]):
            if r.get('block_id') and r.get('canonical_sha256') and not r.get('locator'):
                identities[(r['canonical_sha256'],r['block_id'])]=u['id']
    containers={}
    for fingerprint,doc in canonicals.items():
        for bid,b in doc.get('blocks',{}).items():
            if b['type'] in {'document','section'}:
                identities[(fingerprint,bid)]='container:'+digest([fingerprint,bid])[:24]
        for bid,b in doc.get('blocks',{}).items():
            if b['type'] in {'document','section'}:
                uid=identities[(fingerprint,bid)]
                containers[uid]={'id':uid,'type':b['type'],'parent_id':identities.get((fingerprint,b.get('parent_id'))),
                    'order_in_parent':b.get('order_in_parent'),'canonical_sha256':fingerprint,'block_id':bid,
                    'title':'PDF pages '+', '.join(str(p['page_index']+1) for p in doc.get('pages',[]))+' · parsed '+b['type'],
                    'origin':'canonical'}
    for index,u in enumerate(units):
        u.setdefault('source_order',index)
        if u['kind']=='coverage':continue
        refs=u['original'].get('references',[])
        keys={(r.get('canonical_sha256'),r.get('block_id')) for r in refs if r.get('block_id')}
        if len(keys)!=1:continue
        fingerprint,bid=next(iter(keys));b=canonicals.get(fingerprint,{}).get('blocks',{}).get(bid)
        if not b:continue
        is_row=any(r.get('locator') for r in refs) and b.get('table')
        u['source_hierarchy']={'type':'table_row' if is_row else b['type'],
            'parent_id':identities.get((fingerprint,bid if is_row else b.get('parent_id'))),
            'parent_block_id':bid if is_row else b.get('parent_id'),
            'heading_level':b.get('heading_level'),'list_level':b.get('list_level'),
            'order_in_parent':b.get('order_in_parent'),'canonical_sha256':fingerprint,'block_id':bid,
            'origin':'canonical'}
    return containers


def value(unit):
    return dict(unit.get('source_hierarchy',{}),**unit.get('hierarchy_edit',{}))


def label(unit):
    fields=dict(unit.get('original',{}).get('fields',{}),**unit.get('edits',{}))
    if value(unit).get('type')=='table':
        refs=unit.get('reviewed_references') or unit.get('original',{}).get('references',[])
        pages=sorted({r['page_index']+1 for r in refs if r.get('page_index') is not None})
        return 'Table'+(' · PDF pages '+', '.join(map(str,pages)) if pages else '')
    return (fields.get('identifier') or fields.get('title') or fields.get('body') or 'Untitled source content')[:180]


def ancestors(unit,units,containers=None):
    containers=containers or {};result=[];seen={unit['id']};pid=value(unit).get('parent_id')
    while pid:
        if pid in seen:raise ValueError('hierarchy_cycle')
        seen.add(pid)
        if pid in units:
            p=units[pid]
            result.append({'id':pid,'title':label(p),
                'type':value(p).get('type'),'version':p.get('version',1)})
            pid=value(p).get('parent_id')
        elif pid in containers:
            p=containers[pid];result.append(deepcopy(p));pid=p.get('parent_id')
        else:
            result.append({'id':pid,'unresolved':True});break
    return result
