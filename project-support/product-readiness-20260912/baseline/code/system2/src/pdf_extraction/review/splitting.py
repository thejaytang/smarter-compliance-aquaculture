"""Exact text partitioning with explicit field and relationship disposition."""
from copy import deepcopy
from fractions import Fraction
import json
from .effective import resolve,table_owner
from .hierarchy import TYPES,ensure_order,ordered,validate,affected_scopes
from ..domains.requirements.review_hierarchy import value,label
from ..contracts.hashing import digest


def source_fields(unit):
    return dict(unit['original'].get('fields',{}),**unit.get('edits',{}))


def context(db,did,unit):
    incoming=[]
    for row in db.execute('SELECT u.data FROM review_units u JOIN review_dependencies d ON u.document_id=d.document_id AND u.id=d.unit_id WHERE d.document_id=? AND d.dependency_id=?',(did,unit['id'])):
        u=json.loads(row[0])
        if u.get('superseded_by'):continue
        links=[{'index':i,'role':l['role']} for i,l in enumerate(u.get('content_relations',[])) if l['target_unit_id']==unit['id']]
        parent=value(u).get('parent_id')==unit['id']
        if links or parent:incoming.append({'id':u['id'],'title':label(u),'fingerprint':digest(u),'parent':parent,'links':links})
    return {'fields':{k:v for k,v in source_fields(unit).items() if k!='body' and v},'outgoing':unit.get('content_relations',[]),'incoming':incoming}


def destinations(mapping,key,count,single=False):
    if not isinstance(mapping,dict):raise ValueError('invalid_split_assignment_map')
    v=mapping.get(str(key))
    if not isinstance(v,list) or not v or any(type(i)!=int or not 0<=i<count for i in v) or len(set(v))!=len(v) or (single and len(v)!=1):
        raise ValueError('explicit_split_assignment_required:'+str(key))
    return v


def split(doc,unit,request):
    units={u['id']:u for u in doc['units']}
    if unit['kind']=='coverage' or unit.get('superseded_by') or unit.get('evidence_only'):raise ValueError('split_requires_current_source_text')
    if table_owner(unit,units):raise ValueError('table_boundaries_require_table_geometry_repair')
    if set(unit.get('drafts',{}))-{request['actor']}:raise ValueError('split_target_has_unsubmitted_draft')
    spec=request.get('split_spec',{})
    if not isinstance(spec,dict):raise ValueError('invalid_split_specification')
    parts=spec.get('parts',[])
    view=resolve(unit,units);body=view['fields'].get('body','');refs=view.get('references',[])
    if not isinstance(parts,list) or len(parts)<2 or any(not isinstance(p,dict) or not isinstance(p.get('text'),str) or not p['text'].strip() for p in parts) or ''.join(p['text'] for p in parts)!=body:
        raise ValueError('split_must_preserve_every_source_character_in_order')
    n=len(parts);ids=['split:'+digest([request['request_id'],i])[:24] for i in range(n)]
    if any(uid in units for uid in ids):raise ValueError('split_identity_already_exists')
    for p in parts:
        if p.get('type') not in TYPES-{'table','table_row'}:raise ValueError('split_content_type_required')
        level=p.get('heading_level')
        if level is not None and (type(level)!=int or not 1<=level<=6 or p['type']!='heading'):raise ValueError('invalid_split_heading_level')
        destinations({'refs':p.get('reference_indices')},'refs',len(refs))
    fields=source_fields(unit);field_map={k:destinations(spec.get('fields',{}),k,n,single=k=='identifier') for k,v in fields.items() if k!='body' and v}
    links=unit.get('content_relations',[])
    outgoing={i:destinations(spec.get('outgoing',{}),i,n) for i in range(len(links))}
    incoming={};incoming_spec=spec.get('incoming',{})
    if not isinstance(incoming_spec,dict):raise ValueError('invalid_split_assignment_map')
    for other in doc['units']:
        if other.get('superseded_by') or other['id']==unit['id']:continue
        parent=value(other).get('parent_id')==unit['id']
        indexes=[i for i,l in enumerate(other.get('content_relations',[])) if l['target_unit_id']==unit['id']]
        if not parent and not indexes:continue
        row=incoming_spec.get(other['id'],{})
        if not isinstance(row,dict):raise ValueError('invalid_split_relationship_assignment')
        if row.get('fingerprint')!=digest(other):raise ValueError('stale_or_missing_split_relationship')
        if other.get('drafts'):raise ValueError('split_related_content_has_unsubmitted_draft')
        incoming[other['id']]={'parent':destinations(row,'parent',n,True)[0] if parent else None,
            'links':{i:destinations(row.get('links',{}),i,n) for i in indexes}}
    ensure_order(doc);current=ordered(doc['units']);index=next(i for i,u in enumerate(current) if u['id']==unit['id'])
    left=Fraction(str(unit.get('reading_order_key',unit['source_order'])))
    right=next((Fraction(str(u.get('reading_order_key',u['source_order']))) for u in current[index+1:] if Fraction(str(u.get('reading_order_key',u['source_order'])))>left),left+1)
    new=[];offset=0
    for i,p in enumerate(parts):
        part_fields={'body':p['text']}
        for k,targets in field_map.items():
            if i in targets:part_fields[k]=deepcopy(fields[k])
        part_refs=[deepcopy(refs[j]) for j in p['reference_indices']]
        span={'source_unit_id':unit['id'],'source_unit_version':unit['version'],'body_sha256':digest(body),'start':offset,'end':offset+len(p['text']),'offset_unit':'unicode_codepoint'}
        for ref in part_refs:ref['split_text_range']=span
        relations=[deepcopy(link) for j,link in enumerate(links) if i in outgoing[j]]
        # Dependencies without typed meaning retain the complete original evidence scope.
        dependencies=set(unit.get('dependencies',[]))-set(unit.get('relation_dependencies',[]))
        dependencies.update(l['target_unit_id'] for l in relations)
        child={'id':ids[i],'kind':'source_text','version':1,'original':{'fields':part_fields,'references':part_refs,'structure':[]},
            'source_order':str(left+(right-left)*Fraction(i+1,n+1)),'dependencies':sorted(dependencies),
            'content_relations':relations,'relation_dependencies':sorted({l['target_unit_id'] for l in relations}),
            'hierarchy_dependencies':[value(unit)['parent_id']] if value(unit).get('parent_id') in dependencies else [],
            'hierarchy_edit':{'type':p['type'],'heading_level':p.get('heading_level'),'parent_id':value(unit).get('parent_id'),'origin':'human'},
            'boundary_created_from':span,'boundary_sources':unit.get('boundary_sources',[unit['id']]),'boundary_request_id':request['request_id'],
            'edits':{},'drafts':{},'content_human':False,'requirement_human':False,'touched':True,'classification':'undetermined',
            'blockers':deepcopy(unit.get('blockers',[])),'content_parts':[],'requirement_parts':[],'chapter':unit.get('chapter','Original order')}
        new.append(child);offset+=len(p['text'])
    changed={unit['id']}
    for other in doc['units']:
        if other['id']==unit['id'] or other.get('superseded_by'):continue
        if unit['id'] not in other.get('dependencies',[]):continue
        changed.add(other['id']);assignment=incoming.get(other['id'],{})
        old_links=other.get('content_relations',[]);new_links=[]
        for i,l in enumerate(old_links):
            if l['target_unit_id']==unit['id']:
                new_links.extend(dict(l,target_unit_id=ids[j]) for j in assignment['links'][i])
            else:new_links.append(l)
        if 'parent' in assignment and assignment['parent'] is not None:
            other.setdefault('hierarchy_edit',{}).update(parent_id=ids[assignment['parent']],origin='human')
        typed=(unit['id'] in other.get('relation_dependencies',[]) or unit['id'] in other.get('hierarchy_dependencies',[]) or bool(assignment))
        replacement={l['target_unit_id'] for l in new_links if l['target_unit_id'] in ids}
        if assignment.get('parent') is not None:replacement.add(ids[assignment['parent']])
        if not typed:replacement.update(ids)
        other['dependencies']=sorted(set(other['dependencies'])-{unit['id']}|replacement)
        other['content_relations']=new_links
        for key in ('relation_dependencies','hierarchy_dependencies'):
            other[key]=[d for d in other.get(key,[]) if d!=unit['id']]
        other['relation_dependencies']=list(dict.fromkeys(other['relation_dependencies']+[l['target_unit_id'] for l in new_links]))
        if assignment.get('parent') is not None:other['hierarchy_dependencies'].append(ids[assignment['parent']])
    unit['superseded_by']=ids;doc['units'].extend(new);units.update({u['id']:u for u in new});changed.update(ids)
    doc['units']=ordered(doc['units']);validate(doc)
    return affected_scopes(units,changed),ids
