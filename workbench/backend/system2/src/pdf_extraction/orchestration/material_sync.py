"""Peer synchronization creates an additive revision; no extraction or governance."""
from copy import deepcopy
from ..review.materials import validate_blocks, now
from .material_collaboration import validate_package, normalized, retained_checks


def validate_value(value):
 if not isinstance(value,dict) or set(value)!={'binding','blocks','issues','review'}:raise ValueError('Invalid material snapshot fields.')
 b=value['binding']
 if not isinstance(b,dict) or set(b)!={'id','source','scope','title'}:raise ValueError('Invalid material binding.')
 if not isinstance(b['scope'],list) or not b['scope']:raise ValueError('A material needs its complete original scope.')
 validate_blocks(value['blocks'],b['scope'])
 issues=value['issues']
 if (not isinstance(issues,list) or any(not isinstance(i,dict) or not isinstance(i.get('id'),str) or not i['id'] or not isinstance(i.get('message'),str) or type(i.get('resolved',False)) is not bool for i in issues) or len({i['id'] for i in issues})!=len(issues) or not isinstance(value['review'],dict)):
  raise ValueError('Invalid material review information.')
 return value


def command(service,action,request):
 value=validate_value(request['value'])
 if action=='sync-validate':return {'status':'valid'}
 origin,_=validate_package(request['origin']);store=service.store
 observed=service.read(request['material_id'])
 with store.transaction() as db:
  req,m,replay=store._begin(db,request,'peer_sync')
  if replay is not None:return replay
  b=value['binding']
  if any(m[k]!=b[k] for k in ('id','source','scope')):raise ValueError('Snapshot is bound to another original version.')
  if origin['source']!=m['source'] or origin['scope']!=m['scope']:raise ValueError('Snapshot evidence belongs to another original.')
  # Even a safe field merge can invalidate a reviewed page or relationship.
  checks=retained_checks([m,origin],value['blocks'],value['issues'],m)
  previous_status=m['content_status'];previous_confirmation=deepcopy(m.get('confirmation'));previous_association=m['association_review_required']
  changed=store._edit(m,dict(req,blocks=value['blocks'],issues=value['issues'],checked_scope=[],association_reviewed=False))
  m['checked_scope']=sorted(checks);m['review_checks']=checks
  exact=(origin['blocks']==value['blocks'] and origin['issues']==value['issues'] and value['review'].get('confirmation')==origin.get('confirmation'))
  can_confirm=not (m.get('source_stale') or observed.get('source_check_error') or observed.get('source_issues') or any(c['status'] in ('running','ready','partial') for c in store._view(db,m)['candidates']))
  if exact and origin.get('confirmation') and not origin.get('source_stale') and can_confirm:
   # Preserve a received exact-content declaration as its original person's
   # evidence. Do not invent a new confirmation by the importing reviewer.
   m['confirmation']=deepcopy(origin['confirmation']);m['confirmation']['content_revision']=m['content_revision']
   m['checked_scope']=deepcopy(origin['checked_scope']);m['review_checks']=retained_checks([origin],value['blocks'],value['issues'],m)
   m['association_review_required']=origin.get('association_review_required',False)
   if 'association_review' in origin:m['association_review']=deepcopy(origin['association_review'])
   if 'review_declarations' in origin:m['review_declarations']=deepcopy(origin['review_declarations'])
   m['content_status']='content_review_complete'
  elif changed:
   m['confirmation']=None;m['content_status']='review_in_progress' if checks else 'draft'
  else:
   m['confirmation']=previous_confirmation if can_confirm else None;m['content_status']=previous_status if can_confirm else 'review_in_progress'
   m['association_review_required']=previous_association
  confirmed=exact and can_confirm and bool(m.get('confirmation'))
  m.setdefault('synchronizations',[]).append({'request_id':req['request_id'],'actor':req['actor'],'at':now(),
   'head':req['sync_head'],'contributors':req.get('contributors'),'original_confirmation':deepcopy(origin.get('confirmation'))})
  m['revision']+=1;store._write(db,m,'content_confirmed' if confirmed else 'synchronized',origin['confirmation']['actor'] if confirmed else req['actor'])
  return store._receipt(db,req,{'status':'applied','material':store._view(db,m)})
