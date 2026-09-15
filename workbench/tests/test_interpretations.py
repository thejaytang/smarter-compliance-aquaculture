"""Source-bound drafts, provider isolation, idempotence and annotation lifecycle."""
import json
import os
import threading
import time
import unittest
import uuid
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from local_workbench.sqlite_support import connect
from local_workbench.requirements import Requirements
from local_workbench.interpretations import Interpretations, annotations, KEYS, checking_logic
from local_workbench.ai_settings import AISettings

ACTOR='Weijie Tang'
TEXT='Everything installed as part of the anchoring line must be checked after a storm.'
class InterpretationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=TemporaryDirectory();self.root=Path(self.tmp.name)
  self.material=dict(id='a'*32,revision=1,source={'source_id':'fixture','content_hash':'v1'},blocks=[dict(id='b',type='text',text=TEXT,source_refs=[{'page':1}])])
  self.c=SimpleNamespace(db=lambda:connect(self.root/'test.sqlite'),lock=threading.RLock(),read_material=lambda a,i:deepcopy(self.material))
  self.c.app=SimpleNamespace(runtime=self.root,collaboration=self.c)
  self.r=Requirements(self.c);self.s=Interpretations(self.c);self.settings=AISettings(self.c.app)
  self.doc=self.r.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action='start',material_id=self.material['id'],material_revision=1,block_id='b'))['document'];self.uid=next(iter(self.doc['units']))
 def tearDown(self):self.tmp.cleanup()
 def step(self,action,**args):
  self.doc=self.r.apply(ACTOR,dict(request_id=str(uuid.uuid4()),action=action,session_id=self.doc['id'],expected_revision=self.doc['revision'],unit_id=self.uid,**args))['document']
 def fields(self):return {k:dict(value='',basis='unresolved',references=[],gaps=[]) for k in KEYS}
 def request(self,**kwargs):return dict(request_id=str(uuid.uuid4()),unit_id=self.uid,expected_revision=0,context_fingerprint=self.s.context(ACTOR,self.uid)['fingerprint'],fields=self.fields(),**kwargs)
 def test_save_replay_conflict_review_restore_actor(self):
  req=self.request();req['fields']['scope']=dict(value=TEXT[:48],basis='source',references=[{'id':'a'*32+':b','quote':TEXT[:48]}],gaps=[])
  a=self.s.save(ACTOR,req);self.assertEqual(a,self.s.save(ACTOR,req));self.assertEqual(self.s.read(ACTOR,self.uid)['revision'],1)
  self.assertEqual(self.s.save(ACTOR,self.request())['status'],'conflict')
  with self.assertRaises(ValueError):self.s.read('Ana Jokic',self.uid)
  with self.assertRaises(ValueError):self.s.save(ACTOR,dict(req,request_id=str(uuid.uuid4()),expected_revision=1,action='review'))
  restored=self.s.save(ACTOR,dict(req,request_id=str(uuid.uuid4()),expected_revision=1,action='restore',history_revision=1));self.assertEqual(restored['revision'],2)
  self.assertEqual(len(self.s.read(ACTOR,self.uid)['history']),2)
 def test_relational_trail_is_frozen_after_source_edits_and_retired_units(self):
  req=self.request();quote='after a storm'
  req['fields']['condition']=dict(value=quote,basis='source',references=[dict(id='a'*32+':b',quote=quote)],gaps=[])
  self.s.save(ACTOR,req);trail=self.s.trace(ACTOR,self.uid)
  ref=next(x for x in trail['fields'] if x['key']=='condition')['references'][0]
  self.assertEqual(trail['source']['source_id'],'fixture');self.assertEqual(ref['start'],TEXT.index(quote))
  self.assertEqual(trail['original_text'][ref['start']:ref['end']],quote)
  self.material['blocks'][0]['text']='Replacement source'
  self.assertEqual(self.s.trace(ACTOR,self.uid)['original_text'],TEXT)
  with self.c.db() as db:
   self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
   db.execute('DELETE FROM requirement_units WHERE id=?',(self.uid,))
  self.assertFalse(self.s.trace(ACTOR,self.uid)['unit_active'])
  with self.assertRaises(ValueError):self.s.trace('Ana Jokic',self.uid)
 def test_ambiguous_reference_positions_are_not_guessed(self):
  self.material['blocks'][0]['text']=TEXT+' '+TEXT
  ctx={'citations':[dict(id='citation',text='鱼🐟 check check')]}
  fields=self.fields();fields['scope']=dict(value='check',basis='source',references=[dict(id='citation',quote='check')],gaps=[])
  ref=self.s.validate_fields(fields,ctx)['scope']['references'][0];self.assertIsNone(ref['start'])
  fields['scope']['references'][0].update(start=9,end=14)
  self.assertEqual(self.s.validate_fields(fields,ctx)['scope']['references'][0]['start'],9)
  fields['scope']['references'][0]['start']=0
  with self.assertRaises(ValueError):self.s.validate_fields(fields,ctx)
 def test_query_design_preserved_through_save_restore_and_relational_join(self):
  from local_workbench.check_design import empty_design
  req=self.request();design=empty_design();design['groups']['scope']={'id':'group1','condition':'AND','rules':[{'id':'rule1','field':'components.kind','operator':'equal','type':'string','value':'anchor','interpretation_field':'scope'}]};req['check_design']=design
  self.s.save(ACTOR,req)
  self.assertEqual(self.s.read(ACTOR,self.uid)['querybuilder']['scope']['rules'][0],dict(field='components.kind',operator='equal',value='anchor'))
  trace=self.s.trace(ACTOR,self.uid);self.assertEqual(next(n for n in trace['rules'] if n['id']=='rule1')['field_key'],'scope')
  req.update(request_id=str(uuid.uuid4()),expected_revision=1,check_design=empty_design());self.s.save(ACTOR,req)
  req.update(request_id=str(uuid.uuid4()),expected_revision=2,action='restore',history_revision=1);self.s.save(ACTOR,req)
  self.assertEqual(self.s.read(ACTOR,self.uid)['check_design'],design)
 def test_legacy_lineage_uses_saved_step_and_marks_missing_citation_locations(self):
  req=self.request();self.s.save(ACTOR,req)
  with self.c.db() as db:
   db.execute('DELETE FROM interpretation_fields');db.execute('DELETE FROM interpretation_origins')
  self.s.read(ACTOR,self.uid);self.assertEqual(self.s.trace(ACTOR,self.uid)['quality'],'legacy-saved-step')
 def test_foreign_keys_reject_orphan_field(self):
  import sqlite3
  with self.assertRaises(sqlite3.IntegrityError):
   with self.c.db() as db:db.execute('INSERT INTO interpretation_fields VALUES(?,?,?,?,?,?)',(ACTOR,'missing',1,'scope','value','interpretation'))
 def test_invalid_citations_never_saved_and_logic_does_not_invent(self):
  req=self.request();req['fields']['verification'].update(value='Check within one day',basis='source',references=[{'id':'a'*32+':b','quote':'within one day'}])
  with self.assertRaises(ValueError):self.s.save(ACTOR,req)
  logic=checking_logic(self.fields());self.assertEqual(len(logic['gaps']),6);self.assertFalse(logic['executable']);self.assertNotIn('Satisfied',json.dumps(logic))
  self.assertNotIn('integrity',json.dumps(logic));self.assertEqual(self.s.read(ACTOR,self.uid)['revision'],0)
 def test_annotation_lifecycle_offsets_multiple_units_and_source_change(self):
  original=deepcopy(self.material);self.step('assign',field='Subject',start=0,end=48);self.step('done')
  spans=annotations(self.c,ACTOR,self.material['id'])['spans'];self.assertEqual(spans[0]['start'],0);self.assertEqual(spans[0]['end'],48)
  self.step('reopen');self.assertFalse(annotations(self.c,ACTOR,self.material['id'])['spans'])
  self.step('done');self.assertTrue(annotations(self.c,ACTOR,self.material['id'])['spans']);self.assertEqual(self.material,original)
  self.material['source']['content_hash']='changed';self.assertFalse(annotations(self.c,ACTOR,self.material['id'])['spans'])
  self.assertTrue(self.s.read(ACTOR,self.uid)['stale'])
 def test_saved_interpretation_stale_after_split_edit(self):
  self.s.save(ACTOR,self.request());self.step('assign',field='Subject',start=0,end=48)
  self.assertTrue(self.s.read(ACTOR,self.uid)['stale'])
 def test_one_setting_no_secret_echo_retain_clear_and_reject_credentials_url(self):
  data=dict(revision=0,enabled=True,endpoint='https://example.invalid/v1/chat/completions',model='chosen-model',api_key='private-test-key')
  saved=self.settings.save(ACTOR,data);self.assertTrue(saved['has_key']);self.assertNotIn('private-test-key',json.dumps(saved));self.assertNotIn('api_key',saved)
  self.settings.save(ACTOR,dict(data,revision=1,api_key=''));self.assertEqual(self.settings.config()['api_key'],'private-test-key')
  self.assertEqual(self.s.capability()['destination'],data['endpoint'])
  self.settings.save(ACTOR,dict(data,revision=2,api_key='',clear_key=True));self.assertFalse(self.settings.public()['has_key'])
  if os.name!='nt':self.assertEqual(os.stat(self.settings.path).st_mode&0o777,0o600)
  with self.assertRaises(ValueError):self.settings.save(ACTOR,dict(data,revision=3,endpoint='https://user:secret@example.invalid'))
  with self.assertRaises(ValueError):self.settings.save(ACTOR,data)
 def test_mock_generation_candidate_only_idempotent_and_complete_context(self):
  seen=[];response={'fields':self.fields()};response['fields']['condition']=dict(value='after a storm',basis='source',references=[{'id':'a'*32+':b','quote':'after a storm'}],gaps=[])
  class Mock(BaseHTTPRequestHandler):
   def do_POST(h):
    seen.append(json.loads(h.rfile.read(int(h.headers['Content-Length']))));raw=json.dumps({'choices':[{'message':{'content':json.dumps(response)}}]}).encode();h.send_response(200);h.end_headers();h.wfile.write(raw)
   def log_message(*args):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Mock);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   self.settings.save(ACTOR,dict(revision=0,enabled=True,endpoint=f'http://127.0.0.1:{server.server_port}/v1/chat/completions',model='mock'))
   req=self.request(confirm_context=True);req.pop('expected_revision');req.pop('fields')
   run=self.s.generate(ACTOR,req);self.assertEqual(self.s.generate(ACTOR,req)['id'],run['id'])
   deadline=time.time()+5
   while time.time()<deadline:
    result=self.s.run(ACTOR,run['id'])
    if result['status']!='running':break
    time.sleep(.02)
   self.assertEqual(result['status'],'ready',result);self.assertEqual(len(seen),1)
   self.assertEqual(json.loads(seen[0]['messages'][1]['content'])['materials'][0]['blocks'][0]['text'],TEXT)
   self.assertEqual(self.s.read(ACTOR,self.uid)['fields']['condition']['value'],'')
   self.assertEqual(result['suggestions']['condition']['value'],'after a storm')
  finally:server.shutdown();server.server_close();thread.join()

 def test_late_candidate_is_stale_and_timeout_keeps_formal_work(self):
  release=threading.Event();entered=threading.Event();response={'fields':self.fields()}
  class Delayed(BaseHTTPRequestHandler):
   def do_POST(h):
    h.rfile.read(int(h.headers['Content-Length']));entered.set();release.wait(3)
    try:
     raw=json.dumps({'choices':[{'message':{'content':json.dumps(response)}}]}).encode();h.send_response(200);h.end_headers();h.wfile.write(raw)
    except (BrokenPipeError,ConnectionResetError):pass
   def log_message(*args):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Delayed);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
  try:
   self.settings.save(ACTOR,dict(revision=0,enabled=True,endpoint=f'http://127.0.0.1:{server.server_port}/v1/chat/completions',model='mock'))
   self.s.save(ACTOR,self.request())
   req=self.request(confirm_context=True);req.pop('fields');run=self.s.generate(ACTOR,req);self.assertTrue(entered.wait(2))
   self.step('assign',field='Subject',start=0,end=48);release.set()
   deadline=time.time()+5
   while time.time()<deadline and self.s.run(ACTOR,run['id'])['status']=='running':time.sleep(.02)
   self.assertEqual(self.s.run(ACTOR,run['id'])['status'],'stale')
   self.assertEqual(self.s.read(ACTOR,self.uid)['revision'],1)
   release.clear();entered.clear();config=self.s.config;self.s.config=lambda:dict(config(),timeout=1)
   req=self.request(confirm_context=True);req.pop('fields');run=self.s.generate(ACTOR,req);self.assertTrue(entered.wait(2))
   deadline=time.time()+5
   while time.time()<deadline and self.s.run(ACTOR,run['id'])['status']=='running':time.sleep(.02)
   self.assertEqual(self.s.run(ACTOR,run['id'])['status'],'failed');self.assertEqual(self.s.read(ACTOR,self.uid)['revision'],1)
  finally:release.set();server.shutdown();server.server_close();worker.join()

 def test_context_limit_missing_confirmation_and_confidentiality_fail_before_network(self):
  self.settings.save(ACTOR,dict(revision=0,enabled=True,endpoint='https://example.invalid/v1/chat/completions',model='mock',max_bytes=1000))
  req=self.request(confirm_context=True);req.pop('fields')
  with self.assertRaisesRegex(ValueError,'exceeds'):self.s.generate(ACTOR,req)
  self.settings.save(ACTOR,dict(revision=1,enabled=True,endpoint='https://example.invalid/v1/chat/completions',model='mock'))
  with self.assertRaisesRegex(ValueError,'confirm'):self.s.generate(ACTOR,dict(req,confirm_context=False))
  self.material['confidential']=True;req['context_fingerprint']=self.s.context(ACTOR,self.uid)['fingerprint']
  with self.assertRaisesRegex(ValueError,'confidential'):self.s.generate(ACTOR,req)

 def test_review_saved_then_edit_clears_review(self):
  req=self.request()
  for k in KEYS:req['fields'][k].update(value='Manual interpretation needing no automatic inference',basis='interpretation')
  self.s.save(ACTOR,req)
  reviewed=self.s.save(ACTOR,dict(req,request_id=str(uuid.uuid4()),expected_revision=1,action='review'))
  self.assertEqual(reviewed['revision'],2);self.assertTrue(self.s.read(ACTOR,self.uid)['reviewed'])
  self.s.save(ACTOR,dict(req,request_id=str(uuid.uuid4()),expected_revision=2));self.assertFalse(self.s.read(ACTOR,self.uid)['reviewed'])

 def test_interrupted_run_is_readable_after_restart_without_overwriting_work(self):
  rid=str(uuid.uuid4())
  with self.c.db() as db:db.execute('INSERT INTO interpretation_runs VALUES(?,?,?)',(ACTOR,rid,json.dumps(dict(id=rid,unit_id=self.uid,status='running'))))
  self.assertEqual(self.s.read(ACTOR,self.uid)['runs'][0]['status'],'interrupted')
  self.assertEqual(self.s.read(ACTOR,self.uid)['revision'],0)
