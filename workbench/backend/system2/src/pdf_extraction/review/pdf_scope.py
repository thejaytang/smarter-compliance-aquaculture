"""Apply changed page scopes to the current projection while preserving object identity."""
from ..domains.requirements.pdf_review_scope import localize
from .repairs import invalidate


def refresh(doc):
    current={u['id']:u for u in doc['units']};changed=[]
    for value in localize(doc['units'],doc.get('processed_pages',[])):
        uid=value['id']
        if uid not in current:
            value.update(version=1,edits={},touched=False,content_human=False,requirement_human=False,
                classification='undetermined',content_status='pending',requirement_status='blocked')
            doc['units'].append(value);current[uid]=value
        else:
            u=current[uid]
            if u.get('dependencies',[])!=value.get('dependencies',[]):changed.append(uid)
            u['dependencies']=value.get('dependencies',[])
            if value.get('scope_version'):u['scope_version']=value['scope_version']
    return invalidate(current,changed)
