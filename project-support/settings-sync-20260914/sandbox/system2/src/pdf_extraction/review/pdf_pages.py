"""Read-only original-page discovery, independent of the pending-task queue."""
import json


def read(db,document_id,page_index=None,offset=0):
    row=db.execute('SELECT data FROM documents WHERE id=?',(document_id,)).fetchone()
    if not row:raise ValueError('document_not_found')
    doc=json.loads(row[0])
    if doc['source'].get('file_format')!='pdf':raise ValueError('pdf_source_required')
    total=doc.get('total_pages',0);processed=set(doc.get('processed_pages',[]));offset=max(0,int(offset))
    if page_index is not None and not 0<=int(page_index)<total:raise ValueError('original_page_out_of_range')
    # Only this source's references are inspected; full text/structure never leaves
    # the list endpoint. This also includes corrected and human-inserted positions.
    sql="""SELECT DISTINCT u.id,u.ordinal,u.title,u.kind,u.fingerprint,u.content_ok,u.requirement_ok,u.pending,u.waiting,
        json_extract(r.value,'$.page_index') AS page_index
        FROM review_units u, json_each(COALESCE(json_extract(u.data,'$.reviewed_references'),json_extract(u.data,'$.original.references'))) r
        WHERE u.document_id=? AND json_extract(r.value,'$.page_index') IS NOT NULL
        AND COALESCE(json_extract(u.data,'$.superseded_by'),'') IN ('','[]')"""
    rows=db.execute(sql,(document_id,)).fetchall()
    if page_index is None:
        counts={}
        for r in rows:
            if r['kind']=='coverage':continue
            v=counts.setdefault(r['page_index'],{'mapped_units':0,'accepted_content':0})
            v['mapped_units']+=1;v['accepted_content']+=int(r['content_ok'])
        return {'schema_version':'system2-pages/1','total':total,'offset':offset,'limit':50,
          'items':[dict(page_index=p,processed=p in processed,**counts.get(p,{'mapped_units':0,'accepted_content':0})) for p in range(offset,min(total,offset+50))]}
    p=int(page_index);matching=sorted((dict(r) for r in rows if r['page_index']==p and r['kind']!='coverage'),key=lambda r:r['ordinal'])
    selected=matching[offset:offset+50]
    for item in selected:
        data=json.loads(db.execute('SELECT data FROM review_units WHERE document_id=? AND id=?',(document_id,item['id'])).fetchone()[0])
        item['regions']=[{'bbox':r.get('bbox'),'coord_origin':r.get('coord_origin','top_left')}
            for r in data.get('reviewed_references',data['original']['references']) if r.get('page_index')==p and r.get('bbox')]
    coverage=next((dict(r) for r in rows if r['page_index']==p and r['id']=='coverage:pdf-page:'+str(p)),None)
    report=None
    if coverage:
        value=json.loads(db.execute('SELECT data FROM review_units WHERE document_id=? AND id=?',(document_id,coverage['id'])).fetchone()[0])
        report=value.get('source_verification')
    return {'schema_version':'system2-page/1','page_index':p,'revision':doc['revision'],'source_verification':report,'total_pages':total,'processed':p in processed,
       'items':selected,'total':len(matching),'offset':offset,'limit':50,'coverage':coverage,
       'warning':'Mapped regions are extraction evidence, not proof of complete page coverage. Inspect the original for unmapped content and duplicate regions.'}
