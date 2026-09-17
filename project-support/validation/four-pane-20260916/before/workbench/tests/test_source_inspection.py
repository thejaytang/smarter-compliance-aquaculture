from hashlib import sha256
from pathlib import Path
import json
import socket
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
from local_workbench.source_intake import public_address, inspect_source
from local_workbench.source_checks import check_one

class SourceInspectionTests(unittest.TestCase):
 def test_public_only(self):
  for url in ('file:///tmp/a','https://user:secret@example.org/a','http://localhost:8080/a'):
   with self.assertRaises(ValueError):public_address(url)
  with patch('socket.getaddrinfo',return_value=[(0,0,0,'',('127.0.0.1',80))]):
   with self.assertRaises(ValueError):public_address('http://example.org')
 def test_url_inspection_stages_original_but_does_not_register(self):
  with tempfile.TemporaryDirectory() as tmp:
   calls=[];app=SimpleNamespace(runtime=Path(tmp),collaboration=SimpleNamespace(coordinator=lambda a:None,put=lambda *a:None),system2=SimpleNamespace(call=lambda *a,**k:calls.append((a,k)) or {'fields':{'source_title':'A law'},'warnings':[]}))
   raw=b'<h1>A law</h1>'
   with patch('local_workbench.source_intake.fetch_public',return_value=(raw,'text/html','https://example.org/law')):
    result=inspect_source(app,'A',{'official_url':'https://example.org/law'})
   self.assertEqual(result['fields']['official_url'],'https://example.org/law');self.assertEqual(len(calls),1)
   self.assertEqual(Path(calls[0][1]['path']).read_bytes(),raw)
   with self.assertRaises(ValueError):inspect_source(app,'B',{'upload_id':result['upload_id']})
   Path(calls[0][1]['path']).write_bytes(b'changed')
   with self.assertRaises(ValueError):inspect_source(app,'A',{'upload_id':result['upload_id']})
 def test_update_comparison_never_equates_failure_with_unchanged(self):
  source={'source_id':'A','retrieval_url':'https://example.org/law','content_hash':sha256(b'old').hexdigest()}
  with patch('local_workbench.source_checks.fetch_public',return_value=(b'old','text/html',source['retrieval_url'])):self.assertEqual(check_one(source)['status'],'unchanged')
  with patch('local_workbench.source_checks.fetch_public',return_value=(b'new','text/html',source['retrieval_url'])):self.assertEqual(check_one(source)['status'],'changed')
  with patch('local_workbench.source_checks.fetch_public',side_effect=OSError('Unavailable')):self.assertEqual(check_one(source)['status'],'failed')
  self.assertEqual(check_one({})['status'],'skipped')

 def test_native_open_accepts_registered_identity_only(self):
  from local_workbench.source_workflow import SourceWorkflow
  c=SimpleNamespace(source_original=lambda actor,sid:{'path':'/tmp/classified/original.pdf'})
  with patch('sys.platform','darwin'), patch('subprocess.run') as launch:
   result=SourceWorkflow(c).open_original('Weijie Tang',{'source_id':'PA001'})
   self.assertEqual(result['status'],'open_requested');self.assertEqual(launch.call_args.args[0][-1],str(__import__('pathlib').Path('/tmp/classified/original.pdf')))
   with self.assertRaises(ValueError):SourceWorkflow(c).open_original('Weijie Tang',{'source_id':'PA001','path':'/tmp/other.pdf'})

 def test_native_open_failure_is_actionable_without_a_false_receipt_error(self):
  from local_workbench.source_workflow import SourceWorkflow
  import subprocess
  c=SimpleNamespace(source_original=lambda actor,sid:{'path':'/tmp/classified/original.pdf'})
  for error in (OSError('missing app'),subprocess.TimeoutExpired('open',15),subprocess.CalledProcessError(1,'open')):
   with patch('sys.platform','darwin'), patch('subprocess.run',side_effect=error):
    with self.assertRaisesRegex(ValueError,'default application'):SourceWorkflow(c).open_original('Weijie Tang',{'source_id':'PA001'})

 def test_windows_native_open_uses_registered_path(self):
  from local_workbench.source_workflow import SourceWorkflow
  from pathlib import Path
  c=SimpleNamespace(source_original=lambda actor,sid:{'path':'C:/test data/original.pdf'})
  with patch('sys.platform','win32'), patch('os.startfile',create=True) as launch:
   self.assertEqual(SourceWorkflow(c).open_original('Weijie Tang',{'source_id':'PA001'})['status'],'open_requested')
   launch.assert_called_once_with(str(Path('C:/test data/original.pdf')))
   launch.side_effect=OSError('missing association')
   with self.assertRaisesRegex(ValueError,'default application'):
    SourceWorkflow(c).open_original('Weijie Tang',{'source_id':'PA001'})
