"""Real Requirement HTTP/owner service over synthetic material and temporary SQLite."""
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
from backend.system3.requirement_structure import walk
from local_workbench.server import Handler, ui_content_type

HERE=Path(__file__).parent
ROOT=HERE.parents[2]
UI=ROOT/'workbench/frontend'
ACTOR='Weijie Tang'
TEXT='🐟 The operator shall inspect shackle A, shackle B and shackle A after a storm. Animals, including origin and destination.'

class Fixture(Handler):
 def do_GET(self):
  if not self.valid_host():return self.send(403,{'error':'Local fixture only'})
  path=urlsplit(self.path).path
  if path in {'/api/requirements','/api/requirements/session','/api/requirements/search'}:return super().do_GET()
  if path=='/fixture-info':return self.send(200,self.server.info)
  if path=='/fixture-evidence':return self.send(200,{'source_unchanged':self.server.info['material']==self.server.original,'sessions':Requirements(self.app.collaboration).listing(ACTOR,self.server.original['id'])})
  if path in {'/','/fixture.js','/fixture.css'}:
   file=HERE/('fixture.html' if path=='/' else path[1:]);return self.send(200,file.read_bytes(),ui_content_type(file))
  if path.startswith('/workbench/frontend/'):
   file=(UI/path.removeprefix('/workbench/frontend/')).resolve()
   if file.is_relative_to(UI) and file.is_file():return self.send(200,file.read_bytes(),ui_content_type(file))
  return self.send(404,{'error':'No fixture route. No business API proxy.'})
 def do_POST(self):
  if self.path!='/api/requirements/step':return self.send(403,{'error':'Only isolated Requirement steps are enabled'})
  return super().do_POST()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
 with TemporaryDirectory(prefix='ui-r5-fixture-') as temp:
  folder=Path(temp);path=folder/'synthetic.sqlite'
  blocks=[dict(id='main',type='text',text=TEXT,source_refs=[{'scope_id':'fixture:main'}]),
   *[dict(id=f'link{i}',type='text',text='An otherwise identical synthetic Requirement with a deliberately long shared prefix before its distinguishing final original wording: '+end,source_refs=[{'scope_id':f'fixture:link{i}'}]) for i,end in enumerate(['first target <script>literal only</script>','second target chosen by the reviewer'],1)],
   *[dict(id=f'pending-{kind}',type='text',text='Inspect A and B after a storm.',source_refs=[{'scope_id':f'fixture:{kind}'}]) for kind in ['empty','quantity','relationship']],
   *[dict(id=f'extra-{i}',type='text',text=f'Synthetic additional source passage {i}.',source_refs=[{'scope_id':f'fixture:extra-{i}'}]) for i in range(1,101)]]
  material=dict(id='5'*32,revision=1,source={'source_id':'FX005','snapshot_id':'FX005-001','content_hash':'synthetic-r5'},blocks=blocks,collaboration={'view':'personal'})
  original=deepcopy(material)
  c=SimpleNamespace(db=lambda:connect(path),lock=RLock(),read_material=lambda actor,identity:deepcopy(material))
  c.app=SimpleNamespace(runtime=folder,collaboration=c)
  service=Requirements(c);sessions={};nodes={};doc=None;uid=None
  def start(block):
   nonlocal doc,uid
   doc=service.apply(ACTOR,dict(action='start',request_id=str(uuid.uuid4()),material_id=material['id'],material_revision=1,block_id=block))['document'];uid=next(iter(doc['units']));sessions[block]=doc['id'];return uid
  def tree():return doc['structure_views'][uid]
  def step(action,**body):
   nonlocal doc
   doc=service.apply(ACTOR,dict(action=action,request_id=str(uuid.uuid4()),session_id=doc['id'],expected_revision=doc['revision'],**body))['document'];return doc
  def edit(operation,node=None,**body):return step('structure',unit_id=uid,node_id=node or tree()['id'],operation=operation,**body)
  def mark(field,word,node=None,last=False):
   text=doc['text'];a=text.rindex(word) if last else text.index(word);edit('add',node,field=field,start=a,end=a+len(word))
  def all_quantities():
   for n,_ in list(walk(tree())):
    if n['kind']=='group' and n['children']:edit('quantity',n['id'],quantity=len(n['children']))
  start('main');mark('Subject','The operator');mark('Modal Verb','shall');mark('Main Verb','inspect')
  mark('Object','shackle A');mark('Object','shackle B');mark('Object','shackle A',last=True);mark('conditions','after a storm')
  all_quantities();a=TEXT.index('Animals');edit('add-group',start=a,end=len(TEXT));owner=[n for n,_ in walk(tree()) if n['kind']=='clause' and n['id']!=tree()['id']][-1]['id']
  mark('Subject','Animals',owner);mark('Object','origin',owner);mark('Object','destination',owner);a=TEXT.index('including');edit('relationship',owner,start=a,end=a+len('including'));all_quantities()
  nodes['main_unit']=uid;nodes['relationship']=owner;nodes['object']=[n['id'] for n,_ in walk(tree()) if n['kind']=='fragment' and n.get('text')=='shackle A'][-1]
  for block in ['link1','link2']:start(block);mark('Subject','synthetic Requirement');step('done',unit_id=uid);step('phase',phase='complete')
  for kind in ['empty','quantity','relationship']:
   start('pending-'+kind)
   if kind=='empty':edit('add-group',start=0,end=len(doc['text']))
   elif kind=='quantity':mark('Object','A');mark('Object','B')
   else:
    edit('add-group',start=0,end=len(doc['text']));owner=[n for n,_ in walk(tree()) if n['kind']=='clause' and n['id']!=tree()['id']][-1]['id'];mark('Object','A',owner);a=doc['text'].index('after');edit('relationship',owner,start=a,end=a+len('after'));all_quantities()
  server=ThreadingHTTPServer(('127.0.0.1',args.port),Fixture)
  server.app=SimpleNamespace(reviewer=False,csrf='r5-fixture',store=SimpleNamespace(session=lambda token:{'id':'fixture','name':ACTOR,'token':'fixture'}),collaboration=c)
  server.info={'material':material,'sessions':sessions,'nodes':nodes,'csrf':'r5-fixture'};server.original=original
  print(f'R5 isolated Requirements: http://127.0.0.1:{server.server_port}/',flush=True)
  try:server.serve_forever()
  except KeyboardInterrupt:pass
  finally:server.server_close()
if __name__=='__main__':main()
