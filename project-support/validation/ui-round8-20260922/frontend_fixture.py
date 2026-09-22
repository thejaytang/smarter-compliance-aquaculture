"""Read-only static fixture. Synthetic worksheet API lives entirely in page memory."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import mimetypes
HERE=Path(__file__).parent
ROOT=HERE.parents[2]
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  path=urlsplit(self.path).path
  if path in {'/','/frontend_fixture.js','/frontend_fixture.css'}:file=HERE/('frontend_fixture.html' if path=='/' else path[1:])
  elif path.startswith('/workbench/frontend/'):
   file=(ROOT/path[1:]).resolve()
   if not file.is_relative_to(ROOT/'workbench/frontend'):return self.send_error(403)
  else:return self.send_error(404)
  if not file.is_file():return self.send_error(404)
  data=file.read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript' if file.suffix in {'.js','.mjs'} else mimetypes.guess_type(str(file))[0] or 'application/octet-stream');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_POST(self):self.send_error(403,'Read-only fixture')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=62853);args=parser.parse_args();server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);print(f'R8 frontend reading: http://127.0.0.1:{server.server_port}/',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
