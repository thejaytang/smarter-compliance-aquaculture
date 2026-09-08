"""Map literal source fields; never interpret audit answers as requirements."""
from collections import Counter,defaultdict
from hashlib import sha256
import re
from ...contracts.excel import ExcelDocument
from ...contracts.html import HtmlDocument
from ...contracts.source_records import (GLOBALGAP_HEADERS, MappedText, TextReference,
    SourceRecord, SourceRecords, ResidualReference)


def record_id(source_hash, anchor):
    return 'record:'+sha256((source_hash+'\0'+anchor).encode()).hexdigest()[:24]


def map_source_records(document, canonical_sha256, verification_sha256):
    if isinstance(document,ExcelDocument):
        profile,records,inventory,issues = _excel(document)
    elif isinstance(document,HtmlDocument) and document.profile=='lovdata':
        profile,records,inventory,issues = _lovdata(document)
    else:
        profile,records,issues='unsupported',[],['source_record_profile_not_supported']
        inventory=_html_inventory(document) if isinstance(document,HtmlDocument) else {}
    used={r.pointer for record in records for values in record.fields.values() for field in values for r in field.references}
    counts=Counter((r.fields['identifier'][0].text or '').strip() for r in records)
    for i,record in enumerate(records):
        identifier=(record.fields['identifier'][0].text or '').strip()
        if identifier and counts[identifier]>1:
            records[i]=record.model_copy(update={'issues':[*record.issues,'duplicate_source_identifier']})
    residual=[ResidualReference(reference=ref,reason=reason) for pointer,(ref,reason) in inventory.items() if pointer not in used]
    return SourceRecords(canonical_schema_version=document.schema_version,canonical_sha256=canonical_sha256,
        source_sha256=document.source.content_hash,source_verification_sha256=verification_sha256,profile=profile,
        status='not_supported' if profile=='unsupported' else 'review_required',records=records,residual=residual,
        issues=[*document.issues,*issues],source_reference_count=len(inventory),
        mapped_reference_count=len(used & set(inventory)))


def _field(text, refs):
    return MappedText(text=text,references=refs,status='missing' if text is None else 'present' if text.strip() else 'empty')


def _excel(document):
    inventory={};candidates=[]
    for si,sheet in enumerate(document.sheets):
        rows=defaultdict(dict)
        for ci,cell in enumerate(sheet.cells):
            column,row=re.fullmatch(r'([A-Z]+)([0-9]+)',cell.coordinate).groups()
            scalar='text' if cell.text is not None else 'value'
            value=getattr(cell,scalar)
            pointer=f'/sheets/{si}/cells/{ci}/{scalar}'
            ref=TextReference(pointer=pointer,locator=cell.locator)
            rows[int(row)][column]=(cell,ref,value)
            if cell.formula is not None:
                fp=f'/sheets/{si}/cells/{ci}/formula'
                inventory[fp]=(TextReference(pointer=fp,locator=cell.locator),'nonliteral_formula')
            elif value is not None and value.strip():inventory[pointer]=(ref,'outside_record_mapping')
        for row,cells in rows.items():
            headers={label:[col for col,(cell,_,value) in cells.items() if cell.formula is None and value==label] for label in GLOBALGAP_HEADERS}
            if all(len(cols)==1 for cols in headers.values()):candidates.append((si,sheet,rows,row,{k:v[0] for k,v in headers.items()}))
    if len(candidates)!=1:
        return 'unsupported',[],inventory,['globalgap_header_missing_or_ambiguous']
    si,sheet,rows,header,columns=candidates[0];records=[];issues=[]
    for row,cells in sorted(rows.items()):
        if row<=header:continue
        source=cells.get(columns['Principle'])
        if not source or source[0].formula is not None or not source[2] or not source[2].strip():continue
        identifier=source[2]
        # Template identity requires actual version/category cells, not a filename guess.
        version=cells.get(columns['Version']);category=cells.get(columns['Product Category'])
        if not version or version[0].formula is not None or version[2]!='IFA v6 Smart' or not category or category[0].formula is not None or category[2]!='AQ':
            issues.append('unmapped_template_row:'+sheet.part+'#'+str(row));continue
        fields={};record_issues=[]
        for label,key in GLOBALGAP_HEADERS.items():
            entry=cells.get(columns[label]);value=None;refs=[]
            if entry:
                cell,ref,value=entry
                if cell.formula is not None:
                    value=None;record_issues.append('nonliteral_field:'+key)
                elif value is not None:refs=[ref]
            fields[key]=[_field(value,refs)]
        for key in ('identifier','body','criteria','level'):
            if fields[key][0].status!='present':record_issues.append('missing_or_empty_field:'+key)
        if not re.fullmatch(r'AQ-Smart \d{2}(?:\.\d{2}){1,3}',identifier.strip()):record_issues.append('unrecognized_identifier_format')
        anchor=f'/sheets/{si}/rows/{row}'
        records.append(SourceRecord(id=record_id(document.source.content_hash,anchor),kind='standard_principle',
            source_anchor=anchor,locator=sheet.part+'#row='+str(row),fields=fields,issues=record_issues))
    if not records:issues.append('no_source_records')
    return 'globalgap_ifa_aq',records,inventory,issues


def _html_inventory(document):
    nodes={n.id:n for n in document.nodes};inventory={}
    for i,atom in enumerate(document.atoms):
        if not atom.text.strip():continue
        node=nodes[atom.node_id];control=False;clause=False
        while node:
            classes=node.attributes.get('class',[])
            if node.role in ('control','navigation') or 'share-paragraf' in classes:control=True
            if node.kind=='clause':clause=True
            node=nodes.get(node.parent_id)
        reason='source_control' if control else 'unmapped_record_content' if clause else 'outside_record_mapping'
        pointer=f'/atoms/{i}/text';inventory[pointer]=(TextReference(pointer=pointer,locator=nodes[atom.node_id].locator+f'::text({atom.text_index})'),reason)
    return inventory


def _lovdata(document):
    nodes={n.id:n for n in document.nodes};children=defaultdict(list);by_node=defaultdict(list)
    for node in document.nodes:children[node.parent_id].append(node)
    for i,atom in enumerate(document.atoms):by_node[atom.node_id].append((i,atom))
    def descendants(nid, stop_clauses=False):
        result={nid};stack=[nid]
        while stack:
            for child in children[stack.pop()]:
                if stop_clauses and child.kind=='clause':continue
                result.add(child.id);stack.append(child.id)
        return result
    def field(ids):
        entries=sorted((entry for nid in ids for entry in by_node[nid]),key=lambda v:v[0])
        refs=[TextReference(pointer=f'/atoms/{i}/text',locator=nodes[a.node_id].locator+f'::text({a.text_index})') for i,a in entries]
        return _field(''.join(a.text for _,a in entries),refs)
    inventory=_html_inventory(document);records=[]
    for clause in document.nodes:
        if clause.kind!='clause':continue
        owned=descendants(clause.id,True)
        parts=[n for n in document.nodes if n.id in owned]
        identifier=[n for n in parts if 'paragrafValue' in n.attributes.get('class',[])]
        title=[n for n in parts if 'paragrafTittel' in n.attributes.get('class',[])]
        fields={key:[] for key in ('identifier','title','body','notes','context')};issues=[]
        for key,found in [('identifier',identifier),('title',title)]:
            fields[key]=[field(descendants(n.id)) for n in found] or [_field(None,[])]
            if len(found)!=1:issues.append('missing_or_ambiguous_field:'+key)
        excluded=set()
        for n in parts:
            if (n.kind=='heading' or n.role in ('control','navigation') or 'share-paragraf' in n.attributes.get('class',[])):
                excluded.update(descendants(n.id))
        # Highest footnote roots avoid repeating nested td.fotnote content.
        note_roots=[n for n in parts if n.kind=='footnote' and not any(a.kind=='footnote' for a in _ancestors(n,nodes) if a.id in owned)]
        for n in note_roots:
            ids=descendants(n.id)&owned;fields['notes'].append(field(ids));excluded.update(ids)
        # Keep direct source blocks separate; table/list geometry remains in Canonical.
        for child in children[clause.id]:
            if child.kind=='clause':continue
            ids=descendants(child.id,True)&owned-excluded
            if ids:
                value=field(ids)
                if value.text and value.text.strip():fields['body'].append(value)
        for i,atom in by_node[clause.id]:
            if atom.text.strip():
                fields['body'].append(_field(atom.text,[TextReference(pointer=f'/atoms/{i}/text',locator=clause.locator+f'::text({atom.text_index})')]))
        fields['body'].sort(key=lambda f:int(f.references[0].pointer.split('/')[2]))
        for ancestor in reversed(list(_ancestors(clause,nodes))):
            if ancestor.kind=='section':
                for child in children[ancestor.id]:
                    if child.kind=='heading':fields['context'].append(field(descendants(child.id)))
        if not fields['body']:issues.append('missing_or_empty_field:body')
        if len(identifier)==1 and not (fields['identifier'][0].text or '').strip():issues.append('missing_or_empty_field:identifier')
        records.append(SourceRecord(id=record_id(document.source.content_hash,clause.id),kind='source_clause',source_anchor=clause.id,
            locator=clause.locator,fields=fields,issues=issues))
    return 'lovdata_clauses',records,inventory,[] if records else ['no_source_records']


def _ancestors(node,nodes):
    parent=nodes.get(node.parent_id)
    while parent:
        yield parent;parent=nodes.get(parent.parent_id)
