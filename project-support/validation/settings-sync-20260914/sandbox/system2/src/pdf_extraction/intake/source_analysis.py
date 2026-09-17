"""Transparent baseline source suggestions; never a legal or human decision."""
import re
from urllib.parse import urlsplit

SCORE_FIELDS=('authority_quality','scope_relevance','version_currency','traceability','access_permission')
EXTRA_FIELDS=('jurisdiction','document_type','source_family','requirement_role','authoritative_language','effective_date','inclusion_rationale','automation_readiness','acquisition_channel','provenance_status','update_model','applicability_reference','primary_source_id','source_notes')


def analyze(fields, text, meta, coverage, *, official_url='', retrieved=False):
    fields=dict(fields);body=re.sub(r'\s+',' ',text).strip();sample=body[:250000];lower=sample.lower()
    title=fields['source_title'];publisher=fields['issuer'];identity=(title+' '+publisher).lower()
    legal=re.search(r'\b(regulation|forskrift|lov om|act relating|directive|forordning)\b',identity)
    standard=re.search(r'\b(standard|iso|iec|globalg\.a\.p)\b',identity)
    kind='Regulation' if legal else 'Standard' if standard else 'Guidance' if re.search(r'\b(guidance|guideline|veileder|guidelines)\b',identity) else 'Other'
    language=str(meta.get('language') or meta.get('dc.language') or '').lower()
    if language.startswith(('no','nb','nn')):language='Norwegian'
    elif language.startswith('en'):language='English'
    elif len(re.findall(r'\b(og|skal|forskrift|virksomheten|til|eller)\b',lower))>=3:language='Norwegian'
    elif len(re.findall(r'\b(the|shall|must|and|with|requirements)\b',lower))>=3:language='English'
    else:language='Other'
    jurisdiction='Norway' if re.search(r'\b(norway|norge|norsk|norwegian|norske)\b',identity+' '+lower[:12000]) else 'European Union' if re.search(r'\b(european parliament|european union)\b',identity+' '+lower[:12000]) else 'Other'
    topics=sorted(set(re.findall(r'\b(aquaculture|fish|fisheries|salmon|water|welfare|environmental|akvakultur|fisk|fiskevelferd|laks|oppdrett|utslipp)\b',lower)))
    reference=re.search(r'\b(?:FOR|LOV)-\d{4}-\d{2}-\d{2}-\d+|\b(?:ISO|IEC)\s+\d+(?::\d{4})?',sample,re.I)
    effective=re.search(r'(?:Effective date|Entry into force|Ikrafttredelse|Ikraftsetting)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{2}[./-]\d{2}[./-]\d{4})',sample,re.I)
    summary=meta.get('description') or meta.get('og:description') or meta.get('dc.description')
    if not summary:
        sentences=re.split(r'(?<=[.!?])\s+|\n+',text)
        relevant=[re.sub(r'\s+',' ',line).strip() for line in sentences if 50<len(line)<1400 and re.search(r'\b(shall|must|applies|purpose|scope|skal|formål|virkeområde|aquaculture|akvakultur)\b',line,re.I)]
        summary=' '.join(relevant[:2]) or body[:700]
    summary=re.sub(r'\s+',' ',str(summary or '')).strip()[:1200]
    fields.update(jurisdiction=jurisdiction,document_type=kind,source_family={'A_Public_Authority':'Public authority','B_Standards_Body':'Standards body','C_Certification_Scheme':'Certification scheme'}.get(fields['folder_code'],'Pending classification'),requirement_role='Potential normative source' if legal or standard else 'Supporting reference',authoritative_language=language,effective_date=effective.group(1) if effective else '',inclusion_rationale=('Potential relevance: '+', '.join(topics)+'. Confirm applicability to the operation.' if topics else 'No configured aquaculture topic matched. Review applicability manually.'),automation_readiness='MEDIUM' if body else 'LOW',acquisition_channel='OFFICIAL_WEBSITE' if retrieved else 'MANUAL_COPY',provenance_status='UNVERIFIED',update_model='ROLLING' if official_url else 'MANUAL',applicability_reference=reference.group(0) if reference else '',primary_source_id='',source_notes=('Original excerpt: '+summary if summary else 'No readable original text. OCR or a readable original is required.'))
    dimensions={}
    def rate(key,rating,reason,evidence=''):
        dimensions[key]={'rating':rating,'reason':reason,'evidence':evidence[:500],'confidence':None,'requires_review':True}
        fields[key]='' if rating=='UNKNOWN' else rating
    rate('authority_quality','MEDIUM' if publisher else 'UNKNOWN','Publisher found in the original; authority has not been independently verified.' if publisher else 'No publisher identified in readable content.',publisher)
    rate('scope_relevance','HIGH' if any(t in topics for t in ('aquaculture','akvakultur','oppdrett')) else 'MEDIUM' if topics else 'UNKNOWN','Topic matches are suggestions, not an applicability decision.' if topics else 'No configured topic matched; applicability is unknown.',', '.join(topics))
    rate('version_currency','MEDIUM' if fields['version'] else 'UNKNOWN','A version/date is present; the latest version has not been independently checked.' if fields['version'] else 'No explicit version/date found.',fields['version'])
    rate('traceability','HIGH' if retrieved else 'MEDIUM','Original bytes were retrieved from the recorded URL and bound to a content hash.' if retrieved else 'Uploaded original is hash-bound. Its publication origin needs verification.',official_url or 'User-uploaded original')
    rate('access_permission','UNKNOWN','Readable or publicly reachable content does not establish reuse permission. Verify the applicable terms.')
    missing=[k for k in ('issuer','version','effective_date','applicability_reference') if not fields[k]]
    flags=[v['reason'] for v in dimensions.values() if v['rating']=='UNKNOWN']
    if coverage.get('unreadable_units'):flags.append('Some original pages have no readable text. No OCR was run.')
    if coverage.get('truncated'):flags.append('The basic parsing limit was reached; inspect the remaining original content.')
    return fields,{'schema':'source-basic-inspection/1','status':'partial' if flags or missing else 'complete','summary':summary,'summary_method':'Original metadata or selected original excerpt','coverage':coverage,'dimensions':dimensions,'missing_fields':missing,'flags':flags,'requires_review':True,'method':'Local native-text and explicit content rules; no external model'}
