"""Check mapping inventory and source references; not a new independent source read."""
from collections import defaultdict,Counter
from hashlib import sha256
import re
from ..contracts.excel import ExcelDocument
from ..contracts.html import HtmlDocument
from ..contracts.source_records import GLOBALGAP_HEADERS


def verify_source_records(document, mapping, canonical_sha256, source_verification_sha256):
    errors=[]
    def check(ok,code):
        if not ok:errors.append(code)
    refs,inventory,expected,profile,extra = _expectations(document)
    groups = structures = None
    if mapping.schema_version == "source-records/2":
        from .source_content import extend_expectations
        profile,extra,groups,structures = extend_expectations(document, refs, inventory, expected, profile, extra)
    check(mapping.canonical_schema_version==document.schema_version,'canonical_schema_mismatch')
    check(mapping.canonical_sha256==canonical_sha256 and mapping.source_sha256==document.source.content_hash,'canonical_or_source_hash_mismatch')
    check(mapping.source_verification_sha256==source_verification_sha256,'verification_hash_mismatch')
    check(mapping.profile==profile and mapping.status==('not_supported' if profile=='unsupported' else 'review_required'),'mapping_profile_or_status_mismatch')
    check(mapping.issues==[*document.issues,*extra],'mapping_issue_inventory_mismatch')
    check([r.source_anchor for r in mapping.records]==list(expected),'record_inventory_or_order_mismatch')
    identifiers=Counter(''.join(refs[p][0] for p in e[2].get('identifier', [])).strip() for e in expected.values())
    used=set()
    for record in mapping.records:
        if record.source_anchor not in expected:continue
        kind,locator,fields,issues=expected[record.source_anchor]
        identity=''.join(refs[p][0] for p in fields.get('identifier', [])).strip()
        if identity and identifiers[identity]>1:issues=[*issues,'duplicate_source_identifier']
        check(record.id=='record:'+sha256((document.source.content_hash+'\0'+record.source_anchor).encode()).hexdigest()[:24],'unstable_record_id')
        check(record.kind==kind and record.locator==locator,'record_identity_mismatch')
        check(record.issues==issues,'record_issue_inventory_mismatch:'+record.id)
        check(set(record.fields)==set(fields),'field_inventory_mismatch:'+record.id)
        if structures is not None:
            check([r.model_dump() for r in record.structure] == structures.get(record.source_anchor, []), 'structure_reference_mismatch:'+record.id)
        for key,values in record.fields.items():
            if groups is not None and record.source_anchor in groups:
                check([[r.pointer for r in field.references] for field in values] == groups[record.source_anchor].get(key, []), 'field_group_mismatch:'+record.id+':'+key)
            actual=[r.pointer for field in values for r in field.references]
            check(actual==fields.get(key,[]),'field_scope_or_order_mismatch:'+record.id+':'+key)
            used.update(actual)
            for field in values:
                for r in field.references:check(r.pointer in refs and r.locator==refs[r.pointer][1],'field_provenance_mismatch')
                if field.references and all(r.pointer in refs for r in field.references):
                    expected_text=''.join(refs[r.pointer][0] for r in field.references)
                    check(field.text==expected_text,'field_text_mutation')
                else:check(field.text is None or field.text=='','unproven_field_text')
                check(field.status==('missing' if field.text is None else 'present' if field.text.strip() else 'empty'),'field_status_mismatch')
    expected_residual=[p for p in inventory if p not in used]
    check([r.reference.pointer for r in mapping.residual]==expected_residual,'residual_inventory_mismatch')
    for r in mapping.residual:
        ptr=r.reference.pointer
        check(ptr in refs and r.reference.locator==refs[ptr][1] and r.reason==inventory.get(ptr),'residual_provenance_mismatch')
    check(mapping.source_reference_count==len(inventory) and mapping.mapped_reference_count==len(used&set(inventory)),'coverage_count_mismatch')
    check(mapping.confidence is None and mapping.review_policy == 'review_required', 'mapping_review_policy_mismatch')
    for record in mapping.records:
        check(record.confidence is None and record.review_policy == 'review_required', 'record_review_policy_mismatch')
        for values in record.fields.values():
            for field in values:
                check(field.confidence is None and field.review_policy == 'review_required', 'field_review_policy_mismatch')
    return {'schema_version':'source-records-verification/1','status':'failed' if errors else 'passed',
        'meaning':'Canonical-to-record mapping and coverage only; source fidelity remains bound to the separate source verification.',
        'errors':list(dict.fromkeys(errors)), 'canonical_sha256':canonical_sha256,
        'record_count':len(mapping.records),'source_reference_count':len(inventory),
        'mapped_reference_count':len(used&set(inventory)),'residual_count':len(expected_residual)}


def _expectations(document):
    refs={};inventory={};expected={};profile='unsupported';extra=[]
    if isinstance(document,ExcelDocument):
        candidates=[]
        for si,sheet in enumerate(document.sheets):
            rows=defaultdict(dict)
            for ci,c in enumerate(sheet.cells):
                col=re.match('[A-Z]+',c.coordinate).group();row=int(c.coordinate[len(col):])
                attr='text' if c.text is not None else 'value';ptr=f'/sheets/{si}/cells/{ci}/{attr}'
                value=getattr(c,attr);refs[ptr]=(value,c.locator);rows[row][col]=(c,ptr,value)
                if c.formula is not None:
                    fp=f'/sheets/{si}/cells/{ci}/formula';refs[fp]=(c.formula,c.locator);inventory[fp]='nonliteral_formula'
                elif value is not None and value.strip():inventory[ptr]='outside_record_mapping'
            for row,entries in rows.items():
                found={label:[col for col,(c,_,value) in entries.items() if c.formula is None and value==label] for label in GLOBALGAP_HEADERS}
                if all(len(cols)==1 for cols in found.values()):candidates.append((si,sheet,rows,row,found))
        if len(candidates)!=1:extra=['globalgap_header_missing_or_ambiguous']
        else:
            profile='globalgap_ifa_aq';si,sheet,rows,header,found=candidates[0]
            for row,entries in sorted(rows.items()):
                if row<=header:continue
                identity=entries.get(found['Principle'][0])
                if not identity or identity[0].formula is not None or not (identity[2] or '').strip():continue
                version=entries.get(found['Version'][0]);category=entries.get(found['Product Category'][0])
                if not version or version[0].formula is not None or version[2]!='IFA v6 Smart' or not category or category[0].formula is not None or category[2]!='AQ':
                    extra.append('unmapped_template_row:'+sheet.part+'#'+str(row));continue
                fields={};issues=[]
                for label,key in GLOBALGAP_HEADERS.items():
                    cell=entries.get(found[label][0]);fields[key]=[cell[1]] if cell and cell[0].formula is None and cell[2] is not None else []
                    if cell and cell[0].formula is not None:issues.append('nonliteral_field:'+key)
                for key in ('identifier','body','criteria','level'):
                    if not fields[key] or not (refs[fields[key][0]][0] or '').strip():issues.append('missing_or_empty_field:'+key)
                if not re.fullmatch(r'AQ-Smart \d{2}(?:\.\d{2}){1,3}',identity[2].strip()):issues.append('unrecognized_identifier_format')
                expected[f'/sheets/{si}/rows/{row}']=('standard_principle',sheet.part+'#row='+str(row),fields,issues)
            if not expected:extra.append('no_source_records')
    elif isinstance(document,HtmlDocument):
        nodes={n.id:n for n in document.nodes};ancestry={}
        for n in document.nodes:
            chain=[n];parent=nodes.get(n.parent_id)
            while parent:
                chain.append(parent);parent=nodes.get(parent.parent_id)
            ancestry[n.id]=chain
        def classes(n):return n.attributes.get('class',[])
        def is_control(n):return n.role in ('control','navigation') or 'share-paragraf' in classes(n)
        atoms=defaultdict(list)
        for i,a in enumerate(document.atoms):
            ptr=f'/atoms/{i}/text';refs[ptr]=(a.text,nodes[a.node_id].locator+f'::text({a.text_index})');atoms[a.node_id].append(ptr)
            chain=ancestry[a.node_id]
            if a.text.strip():inventory[ptr]='source_control' if any(is_control(n) for n in chain) else 'unmapped_record_content' if any(n.kind=='clause' for n in chain) else 'outside_record_mapping'
        if document.profile=='lovdata':
            profile='lovdata_clauses'
            for clause in document.nodes:
                if clause.kind!='clause':continue
                owned=[n for n in document.nodes if next((a.id for a in ancestry[n.id] if a.kind=='clause'),None)==clause.id]
                owned_ids={n.id for n in owned};fields={k:[] for k in ('identifier','title','body','notes','context')};issues=[]
                for key,css in [('identifier','paragrafValue'),('title','paragrafTittel')]:
                    roots=[n for n in owned if css in classes(n)]
                    if len(roots)!=1:issues.append('missing_or_ambiguous_field:'+key)
                    for i,a in enumerate(document.atoms):
                        if any(n.id in {r.id for r in roots} for n in ancestry[a.node_id]):fields[key].append(f'/atoms/{i}/text')
                # Body and notes retain source text order; nested clauses are separate records.
                note_ids={n.id for n in owned if n.kind=='footnote'}
                body_groups=defaultdict(list)
                for i,a in enumerate(document.atoms):
                    if a.node_id not in owned_ids:continue
                    chain=ancestry[a.node_id];local=[n for n in chain if n.id in owned_ids];ptr=f'/atoms/{i}/text'
                    if any(n.id in note_ids for n in local):fields['notes'].append(ptr);continue
                    if any(n.kind=='heading' or is_control(n) for n in local):continue
                    if a.node_id==clause.id:
                        if a.text.strip():body_groups[ptr].append(ptr)
                    else:
                        root=next(n for n in chain if n.parent_id==clause.id)
                        body_groups[root.id].append(ptr)
                for group in body_groups.values():
                    if ''.join(refs[p][0] for p in group).strip():fields['body'].extend(group)
                fields['body'].sort(key=lambda ptr:int(ptr.split('/')[2]))
                for section in reversed(ancestry[clause.id][1:]):
                    if section.kind!='section':continue
                    for heading in document.nodes:
                        if heading.parent_id==section.id and heading.kind=='heading':
                            for i,a in enumerate(document.atoms):
                                if heading.id in {n.id for n in ancestry[a.node_id]}:fields['context'].append(f'/atoms/{i}/text')
                if not fields['body']:issues.append('missing_or_empty_field:body')
                if not any(x=='missing_or_ambiguous_field:identifier' for x in issues) and not ''.join(refs[p][0] for p in fields['identifier']).strip():issues.append('missing_or_empty_field:identifier')
                expected[clause.id]=('source_clause',clause.locator,fields,issues)
            if not expected:extra=['no_source_records']
        else:extra=['source_record_profile_not_supported']
    else:raise TypeError('unsupported_canonical')
    return refs,inventory,expected,profile,extra
