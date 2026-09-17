"""Temporary read-only fault proxy over the owned 60905 engineering fixture."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from urllib.parse import urlsplit
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  path=urlsplit(self.path).path
  if path=='/api/material/original' and (HERE/'fail-original').exists():
   payload=b'{"error":"engineering_original_temporarily_unavailable"}'
   self.send_response(503);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload);return
  if path not in ['/pdf-reader.html','/pdf-reader.js','/pdf-reader.css','/api/material/original'] and not path.startswith('/vendor/pdfjs/'):
   self.send_error(404);return
  try: response=urlopen(Request('http://127.0.0.1:60905'+self.path,headers={'Cookie':self.headers.get('Cookie','')}),timeout=10)
  except HTTPError as error:response=error
  with response:
   payload=response.read();self.send_response(response.status)
   for k,v in response.headers.items():
    if k.lower() not in ('server','date','connection','transfer-encoding','content-length'):self.send_header(k,v)
   self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',58451),Handler)
(HERE/'proxy.json').write_text(json.dumps({'port':server.server_port,'upstream':'http://127.0.0.1:60905','mode':'GET-only engineering fault proxy'}))
print(server.server_port,flush=True);server.serve_forever()
