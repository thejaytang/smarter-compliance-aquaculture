"""A failed source needs follow-up even when no extraction unit exists.

This is a projection of the owning job state, never a fabricated Canonical atom.
"""
from ..contracts.hashing import digest

UNIT_ID = 'processing-failure'


def describe(doc):
    if (doc.get('state') not in {'failed', 'conversion_required'} and not doc.get('error')
            and not any(c.startswith('HtmlProfileError:') for c in doc.get('issues',[]))):
        return None
    codes = list(doc.get('issues', []))
    if doc.get('error'):
        codes.append(doc['error'])
    missing_body = any('html_empty_body' in code for code in codes)
    return {
        'id': UNIT_ID, 'document_id': doc['id'],
        'source_sha256': doc['source']['content_hash'],
        'title': 'The saved original has no document body' if missing_body else 'Source processing needs follow-up',
        'reason': ('The registered HTML content region is empty. Its title, metadata or contents list cannot replace the missing document body.'
                   if missing_body else 'Processing stopped before a usable result was available. Compare the saved original and the recorded problem before retrying.'),
        'codes': codes, 'missing_body': missing_body, 'state': doc['state'],
        'fingerprint': digest([doc['id'], doc.get('generation', 0), doc.get('attempt', 0), codes]),
        'references': [{'locator': 'html:nth-of-type(1) > body:nth-of-type(1)'}]
            if doc['source'].get('file_format') in {'html','htm'} else [],
    }


def html_observations(raw):
    """Report literal local observations. Never follow links or execute scripts."""
    from lxml import html
    from ..contracts.html import HTML_PROFILES
    tree = html.document_fromstring(raw)
    profiles = [name for name, spec in HTML_PROFILES.items() if tree.xpath(spec['identity_xpath'])]
    result = {'profile': profiles[0] if len(profiles) == 1 else None, 'content_regions': [], 'full_document_links': [], 'references': []}
    if len(profiles) != 1:
        return result
    def locator(node):
        parts=[]
        for n in reversed([node,*node.iterancestors()]):
            index=1+sum(s.tag==n.tag for s in n.itersiblings(preceding=True))
            parts.append(str(n.tag)+':nth-of-type('+str(index)+')')
        return ' > '.join(parts)
    # Metadata and body together provide a compact original view, retaining the
    # literal body boundary even when it is empty. The complete file remains available.
    for expr in HTML_PROFILES[profiles[0]]['roots_xpath'][1:]:
        result['references'].extend({'locator':locator(n)} for n in tree.xpath(expr))
    for node in tree.xpath(HTML_PROFILES[profiles[0]]['roots_xpath'][-1]):
        text = ' '.join(node.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
        result['content_regions'].append({'xpath': tree.getroottree().getpath(node),
            'id': node.get('id'), 'text_characters': len(text), 'empty': not bool(text)})
    if profiles[0] == 'lovdata':
        for link in tree.xpath('//ul[contains(concat(" ",normalize-space(@class)," ")," pager ")]/li[contains(concat(" ",normalize-space(@class)," ")," complete ")]/a[@href]'):
            href = link.get('href')
            # Preserve only this profile's literal local document target, as text.
            if href.startswith('/dokument/') and href.endswith('/*'):
                result['full_document_links'].append({'label': link.text_content().strip(), 'href': href})
    return result


def retain(store, db, doc):
    """Retain the stopped attempt before retry or reprocessing changes its state."""
    failure = describe(doc)
    if failure and doc.get('retained_failure') != failure['fingerprint']:
        store._event(db, doc['id'], 'processing_failure', {k:v for k,v in failure.items() if k!='document_id'})
        doc['retained_failure'] = failure['fingerprint']
        if 'processing_failure_codes' not in doc:
            doc['processing_failure_codes']=[c for c in doc.get('issues',[]) if c.startswith('HtmlProfileError:')]


def recovered(store, db, doc):
    """A usable parser result retires only its earlier processing failure codes.

Content acceptance, upstream problems and Canonical integrity keep their gates.
"""
    codes=doc.pop('processing_failure_codes',[])
    doc['issues']=[c for c in doc['issues'] if c not in codes or c.startswith(('upstream_','canonical_'))]
    failure=doc.get('retained_failure')
    if failure and doc.get('recovered_failure')!=failure:
        store._event(db,doc['id'],'processing_recovered',{'failure_fingerprint':failure,
            'note':'Parsing produced a usable result; source fidelity and Requirement acceptance still require their own checks.'})
        doc['recovered_failure']=failure
