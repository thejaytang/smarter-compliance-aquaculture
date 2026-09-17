"""Reversible source-position grouping, never semantic obligation splitting."""
from copy import deepcopy
import re
from ...contracts.hashing import digest


def unique(values):
    return list({digest(v):v for v in values}.values())


def group_units(units):
    """Only combine untouched fragments with explicit section/table position evidence.

    Records with decisions/drafts retain their exact identity. Mapping each grouped
    field back to its member records is persisted alongside the original references.
    """
    result=[]; groups={}; chapter='Original order'; chapter_id=None; previous_key=None; run=0
    pdf=any(r.get('page_index') is not None for u in units for r in u.get('original',{}).get('references',[]))
    coverage=[u for u in units if u['kind']=='coverage']
    contextual={u['id'] for u in units if u['kind'] in {'source_heading','source_note','source_definition','source_definition_term','source_caption'}}
    for original in units:
        u=deepcopy(original)
        if u['kind']=='coverage': continue
        fields=u['original'].get('fields',{})
        locators=[r.get('locator','').split('::')[0] for r in u['original'].get('references',[])]
        heading=u['kind']=='source_heading'
        if heading:
            chapter=' '.join((fields.get('title') or fields.get('body') or chapter).split())[:180]
            chapter_id=u['id']
        if fields.get('context'): chapter=fields['context'].split('\n')[0][:180]
        u['chapter']=chapter
        # Remove the old all-to-all context graph; existing explicit table dependencies survive.
        u['dependencies']=[d for d in u.get('dependencies',[]) if not (contextual and contextual-{u['id']} <= set(u.get('dependencies',[])) and d in contextual) and d not in {c['id'] for c in coverage}]
        if chapter_id and chapter_id!=u['id']: u['dependencies'].append(chapter_id)
        protected=bool(u.get('touched') or u.get('content_human') or u.get('requirement_human') or u.get('drafts') or u.get('edits') or u.get('superseded_by'))
        table=None
        for loc in locators:
            m=re.match(r'^(.*? > table:nth-of-type\(\d+\))',loc)
            if m: table=m[1];break
        for loc in locators:
            match=re.match(r'^(xl/worksheets/[^#]+)#',loc)
            if match:table=match[1];chapter=match[1].rsplit('/',1)[-1].replace('.xml','');u['chapter']=chapter;break
        # Clause records already contain the complete authoritative boundaries.
        key=None
        if not pdf and not protected and u['kind'] not in {'source_clause','standard_indicator','standard_principle'}:
            if table:key='table:'+table
            elif not heading and chapter_id and u['kind'] not in {'source_note','source_image','source_link'}:
                key='section:'+chapter_id
        if key != previous_key: run+=1
        previous_key=key
        if key: key=key+':run:'+str(run)
        if key and key in groups:
            parent=groups[key]
            parent.setdefault('members',[]).append({'id':u['id'],'kind':u['kind'],'fields':fields,'references':u['original']['references']})
            for field,text in fields.items():
                if text: parent['original']['fields'][field]='\n'.join(filter(None,[parent['original']['fields'].get(field,''),text]))
            parent['original']['references']=unique(parent['original']['references']+u['original']['references'])
            parent['original']['structure']=unique(parent['original'].get('structure',[])+u['original'].get('structure',[]))
            parent['blockers']=list(dict.fromkeys(parent.get('blockers',[])+u.get('blockers',[])))
            parent['dependencies']=list(dict.fromkeys(parent['dependencies']+u['dependencies']))
            parent['content_parts']=[]  # A new composite has no validated confidence.
        else:
            if key:
                u['members']=[{'id':u['id'],'kind':u['kind'],'fields':deepcopy(fields),'references':deepcopy(u['original']['references'])}]
                u['id']='group:'+digest(key)[:24]
                u['kind']='source_table' if table else 'source_section'
                u['original']['fields'].setdefault('title','Table in '+chapter if table else chapter)
                u['content_parts']=[]
                groups[key]=u
            result.append(u)
    # Each complete unit gets a bounded coverage task. Source-level findings remain
    # explicit and block only when unresolved global fidelity really is unknown.
    mapping={m['id']:u['id'] for u in result for m in u.get('members',[])}
    for u in result:
        u['dependencies']=list(dict.fromkeys(mapping.get(d,d) for d in u['dependencies'] if mapping.get(d,d)!=u['id']))
    ranges={}
    for u in list(result):
        scope=u['chapter']
        ranges.setdefault(scope,[]).append(u)
    for scope,members in ([] if pdf else ranges.items()):
        refs=unique([r for u in members for r in u['original']['references']])
        cid='coverage:local:'+digest([scope,[u['id'] for u in members]])[:24]
        result.append({'id':cid,'kind':'coverage','chapter':scope,'original':{'fields':{'title':'Completeness · '+scope,'body':'Compare this bounded range with its original. Check omitted text, tables, images, reading order and footnotes.'},'references':refs,'structure':[]},'blockers':[],'dependencies':[],'content_parts':[]})
        for u in members:u['dependencies'].append(cid)
    for cov in coverage:
        cov=deepcopy(cov);cov['chapter']='Source completeness'; result.append(cov)
        if cov.get('blockers'):
            for u in result:
                if u['id']!=cov['id'] and u['kind']!='coverage':u['dependencies'].append(cov['id'])
    for u in result:
        if u['kind']=='source_table':
            rows={};matched=0
            for member in u.get('members',[]):
                locator=next((r.get('locator','') for r in member['references'] if r.get('locator')),'')
                html_row=re.search(r'^(.*?tr:nth-of-type\(\d+\)).*?> (?:td|th):nth-of-type\((\d+)\)',locator)
                excel_row=re.match(r'^(xl/worksheets/[^#]+)#([A-Z]+)([0-9]+)',locator)
                if html_row:row,col=html_row[1],int(html_row[2])
                elif excel_row:
                    row=excel_row[1]+'#row='+excel_row[3];col=0
                    for char in excel_row[2]:col=col*26+ord(char)-64
                else:continue
                matched+=1
                text='\n'.join(str(v) for k,v in member['fields'].items() if v and k!='context')
                cells=rows.setdefault(row,{})
                cells.setdefault(col,[]).append(text)
            u['table_rows']=[{'row':i+1,'locator':r,'text':' | '.join('\n'.join(cols.get(c,[])) for c in range(1,max(cols)+1))} for i,(r,cols) in enumerate(rows.items())]
            # Only replace the flat display when every member is represented, once.
            if matched!=len(u.get('members',[])):u['table_rows']=[]
            if u['table_rows']:u['original']['fields']['body']='\n'.join(r['text'] for r in u['table_rows'])
        u['grouping_version']='source-position/1'
        u['original']['references']=unique(u['original'].get('references',[]))
    if pdf:
        from .pdf_review_scope import localize
        result=localize(result)
    return result


def order_units(units, canonicals):
    """Original order from Canonical positions, not the order of mapper categories."""
    indexes={}
    for sequence,(fingerprint,doc) in enumerate(canonicals.items()):
        nodes={n['id']:i for i,n in enumerate(doc.get('nodes',[]))}
        indexes[fingerprint]=(sequence,doc,nodes)
    def position(unit):
        found=[]
        for ref in unit.get('original',{}).get('references',[]):
            index=indexes.get(ref.get('canonical_sha256'))
            if not index:continue
            seq,doc,nodes=index;ptr=ref.get('pointer','').split('/')
            try:
                if len(ptr)>2 and ptr[1]=='atoms':
                    atom=doc['atoms'][int(ptr[2])];found.append((seq,nodes[atom['node_id']],int(ptr[2])))
                elif len(ptr)>2 and ptr[1]=='nodes':found.append((seq,int(ptr[2]),0))
                elif len(ptr)>4 and ptr[1]=='sheets':
                    cell=doc['sheets'][int(ptr[2])]['cells'][int(ptr[4])]
                    from openpyxl.utils.cell import coordinate_to_tuple
                    row,col=coordinate_to_tuple(cell['coordinate']);found.append((seq,int(ptr[2])*10000000+row,col))
            except (KeyError,IndexError,ValueError):pass
            if ref.get('page_index') is not None:
                box=ref.get('bbox') or [0,0,0,0];y=box.get('y0',0) if isinstance(box,dict) else box[1]
                found.append((seq,ref['page_index']*100000+y,0))
        return min(found) if found else (len(indexes),100000000,0)
    return sorted(units,key=position)
