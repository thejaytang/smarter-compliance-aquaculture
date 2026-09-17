"""Local synthetic Chat Completions fixture, never a production provider."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
class Mock(BaseHTTPRequestHandler):
 def do_POST(self):
  request=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  context=json.loads(request['messages'][1]['content'])
  fields={k:dict(value='',basis='unresolved',references=[],gaps=['Needs human interpretation; not defined by this source.']) for k in ('scope','scope_information','condition','condition_information','demand','verification')}
  text=context['requirement']['text'];storm='after a storm' in text
  quotes={'scope':'Everything installed as part of the anchoring line','condition':'after a storm','demand':'must be checked'} if storm else {'scope':'Farm staff and managers','condition':'','demand':'shall have suitable competence'}
  for k,q in quotes.items():
   if not q:continue
   citation=next(c for c in context['citations'] if q in c['text'])
   fields[k]=dict(value=q,basis='source',references=[dict(id=citation['id'],quote=q)],gaps=[])
  raw=json.dumps({'choices':[{'message':{'content':json.dumps({'fields':fields})}}]}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(raw)
 def log_message(*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Mock)
print(json.dumps({'endpoint':f'http://127.0.0.1:{server.server_port}/v1/chat/completions'}),flush=True)
try:server.serve_forever()
finally:server.server_close()
