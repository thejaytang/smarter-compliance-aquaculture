"""Local automation preferences. Saving a schedule never dispatches a check."""
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from local_workbench.collaboration import named, fingerprint, now

class AutomationSettings:
 def __init__(self,app):self.app=app;self.c=app.collaboration;self.path=(app.layout.runtime/'settings' if getattr(app,'layout',None) else app.runtime)/'material-inspection-settings.json'
 def read(self):
  settings=json.loads(self.path.read_text()) if self.path.exists() else {}
  settings={'enabled':False,'timezone':'Europe/Oslo','sample_size':5,'assignee':'Weijie Tang','interval_days':7,**settings}
  batches=self.c.all('material_inspection_batch')
  last=max((b.get('completed_at') or b.get('at','') for b in batches),default=None)
  return {'settings':settings,'revision':fingerprint(settings),'last_run':last,
   'next_run':settings.get('next_run_at') if settings['enabled'] else None,
   'can_schedule':not self.app.reviewer,'can_edit_confidence':not self.app.reviewer,
   'status':getattr(self.app,'material_inspection_status',{'status':'disabled'})}
 def save(self,actor,request):
  actor=named(actor)
  if self.app.reviewer:raise ValueError('This offline installation does not run shared business schedules.')
  values=request.get('settings',{})
  if set(values)!={'enabled','timezone','sample_size','assignee','interval_days'}:raise ValueError('Choose the displayed automation settings only.')
  if type(values['enabled']) is not bool:raise ValueError('Explicitly choose whether this schedule is enabled.')
  for key,maximum in [('sample_size',100),('interval_days',365)]:
   if type(values[key]) is not int or not 1<=values[key]<=maximum:raise ValueError('Invalid sample size or inspection interval.')
  ZoneInfo(values['timezone']);named(values['assignee'])
  with self.c.lock:
   current=self.read()
   if request.get('revision')!=current['revision']:raise ValueError('Automation settings changed. Reload before saving.')
   previous=current['settings'];result=dict(values)
   same_cadence=all(previous.get(k)==values[k] for k in ('enabled','interval_days','timezone'))
   if values['enabled']:
    result['anchor_at']=previous.get('anchor_at') if same_cadence else now()
    result['anchor_at']=result['anchor_at'] or now()
    result['next_run_at']=previous.get('next_run_at') if same_cadence else None
    result['next_run_at']=result['next_run_at'] or (datetime.now(timezone.utc)+timedelta(days=values['interval_days'])).isoformat()
   temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2),encoding='utf-8');temporary.replace(self.path)
   self.c.put('automation_history',now(),{'actor':actor,'at':now(),'before':previous,'after':result})
   return self.read()
