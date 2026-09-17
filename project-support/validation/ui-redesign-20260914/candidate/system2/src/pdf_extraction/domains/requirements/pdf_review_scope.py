"""Evidence-bound PDF coverage scopes; no semantic ownership is inferred here."""
from copy import deepcopy
import re
from ...contracts.hashing import digest


def pages(unit):
    refs=unit.get('reviewed_references',unit.get('original',{}).get('references',[]))
    found={r['page_index'] for r in refs if isinstance(r.get('page_index'),int) and r['page_index']>=0}
    for ref in refs:
        match=re.fullmatch(r'PDF pages ([\d, ]+)',ref.get('locator',''))
        if match:found.update(int(x.strip())-1 for x in match[1].split(',') if x.strip() and int(x.strip())>0)
    return found


def fingerprints(unit):
    return {r['canonical_sha256'] for r in unit.get('original',{}).get('references',[]) if r.get('canonical_sha256')}


def localize(units, page_indices=()):
    """Retain every old record and finding; replace only inferred coverage edges.

    Old all-source local coverage without findings remains a final completeness
    check. It grants no acceptance to new page checks. Explicit human relation
    dependencies are retained even when their target happens to be coverage.
    """
    result=deepcopy(units)
    coverage=[u for u in result if u['kind']=='coverage']
    ids={u['id'] for u in coverage}
    members=[u for u in result if u['kind']!='coverage']
    page_refs={p:{} for p in page_indices if isinstance(p,int) and p>=0}
    for u in members:
        for r in u.get('reviewed_references',u['original'].get('references',[])):
            p=r.get('page_index')
            if isinstance(p,int) and p>=0:page_refs.setdefault(p,{})[digest(r)]=r
    page_checks={}
    for p,refs in sorted(page_refs.items()):
        cid='coverage:pdf-page:'+str(p)
        check=next((u for u in coverage if u['id']==cid),None)
        if check is None:
            check={'id':cid,'kind':'coverage','chapter':'PDF page '+str(p+1),
                'original':{'fields':{'title':'Completeness · PDF page '+str(p+1),
                  'body':'Compare the complete original page with all mapped content. Check omissions, duplicates and unresolved continuations.'},
                  'references':[{'page_index':p,'locator':'PDF page '+str(p+1)}], 'structure':[]},
                'blockers':[],'dependencies':[],'content_parts':[],'coverage_scope':'pdf_page',
                'scope_version':'pdf-pages/1','grouping_version':'source-position/1'}
            result.append(check)
        page_checks[p]=cid
    for u in members:
        up=pages(u); hashes=fingerprints(u)
        keep=[d for d in u.get('dependencies',[]) if d not in ids or d in u.get('relation_dependencies',[])]
        keep.extend(page_checks[p] for p in sorted(up) if p in page_checks)
        for cov in coverage:
            if cov.get('coverage_scope')=='pdf_page':continue
            # Former inferred local scopes contain no parser findings. Keep their
            # records for overall completion, without all-to-all dependencies.
            if cov['id'].startswith('coverage:local:') and not cov.get('blockers') and not cov.get('touched') and not cov.get('drafts'):continue
            cp=pages(cov); ch=fingerprints(cov)
            if (cp and (not up or bool(cp&up))) or (not cp and ch and (not hashes or bool(ch&hashes))) or (not cp and not ch):
                keep.append(cov['id'])
        u['dependencies']=list(dict.fromkeys(keep));u['scope_version']='pdf-pages/1'
    return result
