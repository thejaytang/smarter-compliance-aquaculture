"""Source-backed containers and effective human parentage, browsable without issue filters."""
import json


def read(db,did,parent_id=None,offset=0):
    row=db.execute('SELECT data FROM documents WHERE id=?',(did,)).fetchone()
    if not row:raise ValueError('document_not_found')
    doc=json.loads(row[0])
    if not doc.get('hierarchy_version'):raise ValueError('source_hierarchy_projection_required')
    nodes={k:dict(v,container=True) for k,v in doc.get('hierarchy_containers',{}).items()}
    for r in db.execute("SELECT id,title,fingerprint,ordinal,content_ok,requirement_ok,json_extract(data,'$.source_hierarchy') AS source,json_extract(data,'$.hierarchy_edit') AS edit FROM review_units WHERE document_id=? AND kind!='coverage' AND COALESCE(json_extract(data,'$.superseded_by'),'') IN ('','[]')",(did,)):
        hierarchy=dict(json.loads(r['source'] or '{}'),**json.loads(r['edit'] or '{}'))
        nodes[r['id']]={'id':r['id'],'title':r['title'],'fingerprint':r['fingerprint'],'ordinal':r['ordinal'],
            'parent_id':hierarchy.get('parent_id'),'type':hierarchy.get('type','unknown'),
            'heading_level':hierarchy.get('heading_level'),'origin':hierarchy.get('origin','unmapped'),
            'content_ok':r['content_ok'],'requirement_ok':r['requirement_ok'],'container':False}
    if parent_id and parent_id not in nodes:raise ValueError('outline_parent_not_found')
    child_counts={}
    for n in nodes.values():child_counts[n.get('parent_id')]=child_counts.get(n.get('parent_id'),0)+1
    children=[dict(n,children=child_counts.get(n['id'],0)) for n in nodes.values() if n.get('parent_id')==parent_id]
    children.sort(key=lambda n:(n.get('ordinal',n.get('order_in_parent',0) or 0),n['id']))
    # Containers retain their Canonical insertion order across parsed windows.
    if parent_id is None:
        insertion_order={uid:i for i,uid in enumerate(nodes)}
        children.sort(key=lambda n:insertion_order[n['id']] if n['container'] else len(nodes)+n['ordinal'])
    trail=[];seen=set();p=parent_id
    while p:
        if p in seen:raise ValueError('hierarchy_cycle')
        seen.add(p);n=nodes.get(p)
        if not n:break
        trail.append({'id':p,'title':n['title']});p=n.get('parent_id')
    offset=max(0,int(offset))
    return {'schema_version':'system2-outline/1','parent_id':parent_id,'parent':nodes.get(parent_id),
        'trail':list(reversed(trail)),'items':children[offset:offset+50],'offset':offset,'limit':50,'total':len(children),
        'warning':'Parsed containers reflect the saved machine structure. They are not verified chapter assignments; compare headings and parentage with the original.'}
