"""Actual Interpretation HTTP service, synthetic Materials, temporary SQLite only."""
import argparse
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import RLock
from types import SimpleNamespace
from urllib.parse import urlsplit
import uuid
from backend.shared.sqlite_support import connect
from backend.system3.requirements import Requirements
from backend.system3.interpretations import Interpretations, KEYS
from backend.system3.check_design import empty_design
from local_workbench.server import Handler, ui_content_type

HERE=Path(__file__).parent;ROOT=HERE.parents[2];UI=ROOT/'workbench/frontend';ACTOR='Weijie Tang'
TEXT='The facility shall inspect the anchoring line after a storm. Keep records of integrity.'

class Fixture(Handler):
 def do_GET(self):
  if not self.valid_host():return self.send(403,{'error':'Local fixture only'})
  path=urlsplit(self.path).path
  if path in {'/api/interpretations','/api/requirements/session','/api/requirements'}:return super().do_GET()
  if path=='/fixture-info':return self.send(200,self.server.info)
  if path=='/fixture-evidence':return self.send(200,{'source_unchanged':self.server.material==self.server.original,'saved':Interpretations(self.app.collaboration).read(ACTOR,self.server.info['units'][0])})
  if path in {'/','/fixture.js','/fixture.css'}:
   file=HERE/('fixture.html' if path=='/' else path[1:]);return self.send(200,file.read_bytes(),ui_content_type(file))
  if path.startswith('/workbench/frontend/'):
   file=(UI/path.removeprefix('/workbench/frontend/')).resolve()
   if file.is_relative_to(UI) and file.is_file():return self.send(200,file.read_bytes(),ui_content_type(file))
  return self.send(404,{'error':'No fixture route. No business proxy or provider.'})
 def do_POST(self):
  if self.path!='/api/interpretations/save':return self.send(403,{'error':'Only explicit isolated Interpretation save is enabled'})
  return super().do_POST()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
 with TemporaryDirectory(prefix='ui-r6-fixture-') as temp:
  folder=Path(temp);path=folder/'synthetic.sqlite';mid='6'*32
  material=dict(id=mid,title='Synthetic ABC source',revision=1,source={'source_id':'FX006','snapshot_id':'FX006-001','content_hash':'synthetic-r6'},blocks=[dict(id='main',type='text',text=TEXT,source_refs=[{'scope_id':'fixture:main'}]),dict(id='records',type='text',text='Keep records of integrity. Facility context.',source_refs=[{'scope_id':'fixture:records'}]),dict(id='other',type='text',text='Another facility requires a separate interpretation.',source_refs=[{'scope_id':'fixture:other'}])])
  c=SimpleNamespace(db=lambda:connect(path),lock=RLock(),read_material=lambda actor,identity:deepcopy(material));c.app=SimpleNamespace(runtime=folder,collaboration=c)
  requirements=Requirements(c);interpretations=Interpretations(c);sessions=[];units=[]
  for block in ['main','other']:
   doc=requirements.apply(ACTOR,dict(action='start',request_id=str(uuid.uuid4()),material_id=mid,material_revision=1,block_id=block))['document'];uid=next(iter(doc['units']));units.append(uid)
   doc=requirements.apply(ACTOR,dict(action='assign',request_id=str(uuid.uuid4()),session_id=doc['id'],expected_revision=doc['revision'],unit_id=uid,field='Subject',start=0,end=12))['document'];sessions.append(doc)
  uid=units[0];ctx=interpretations.context(ACTOR,uid)
  fields={key:dict(value='Synthetic human explanation for '+key,basis='interpretation',state='specified',absence_reason='',references=[],gaps=[]) for key in KEYS}
  fields['scope']['references']=[dict(id=mid+':records',quote='Keep records of integrity.')]
  fields['condition'].update(value='',state='not_stated',absence_reason='The reviewer has not identified a separate condition in this synthetic Set.')
  design=empty_design(2);design['concepts']=[dict(id='facility',label='Facility',kind='concept',status='confirmed',references=[dict(id=mid+':main',quote='The facility')]),dict(id='other-facility',label='Facility',kind='property',status='proposed',references=[]),dict(id='storm',label='Storm',kind='event',status='proposed',references=[dict(id=mid+':main',quote='after a storm')])]
  predicate=lambda identity,wording,concepts:dict(id=identity,expression=wording,interpretation_field='scope',concept_ids=concepts)
  design['groups']['scope']=dict(id='scope-root',condition='AND',rules=[predicate('same-label','Facility',['facility','other-facility']),dict(id='nested-or',condition='OR',**{'not':True},rules=[predicate('storm-rule','Facility after Storm',['facility','storm']),dict(id='range-rule',field='components.count',operator='between',type='integer',value=[1,2],interpretation_field='scope',concept_ids=['facility'])])])
  design['groups']['demand']=dict(id='demand-root',condition='AND',rules=[dict(id='demand-rule',expression='Facility integrity',interpretation_field='demand',concept_ids=['facility'])])
  interpretations.save(ACTOR,dict(action='save',request_id=str(uuid.uuid4()),unit_id=uid,expected_revision=0,context_fingerprint=ctx['fingerprint'],linked_material_ids=[],fields=fields,check_design=design,approve_cards={}))
  server=ThreadingHTTPServer(('127.0.0.1',args.port),Fixture);server.app=SimpleNamespace(reviewer=False,csrf='r6-fixture',store=SimpleNamespace(session=lambda token:{'id':'fixture','name':ACTOR,'token':'fixture'}),collaboration=c)
  server.info={'material':material,'units':units,'sessions':sessions,'csrf':'r6-fixture'};server.material=material;server.original=deepcopy(material)
  print(f'R6 isolated ABC: http://127.0.0.1:{server.server_port}/',flush=True)
  try:server.serve_forever()
  except KeyboardInterrupt:pass
  finally:server.server_close()
if __name__=='__main__':main()
