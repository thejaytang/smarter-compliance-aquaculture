"""Isolated R3 browser fixture. No application startup, workers, stores or API proxy.
Run with System2's declared Python; the coordinator owns starting/stopping this server.
"""
import argparse
import io
import json
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
from types import SimpleNamespace
from urllib.parse import urlsplit, parse_qs

from local_workbench.server import Handler, ui_content_type
from pdf_extraction.evidence.material_reader import read_html_original
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
UI = ROOT / 'workbench/frontend'
ID = 'a' * 32
RAW = b'''<!doctype html><html><head><meta charset="utf-8"><title>Synthetic regulation</title>
<script>parent.FIXTURE_SCRIPT_RAN=true</script><style>body{display:none}</style>
<link href="https://external.invalid/style"><base href="https://external.invalid/"></head><body>
<h1>Synthetic regulation: monitoring at facilities</h1><h2>1. Scope</h2>
<p>This fixture applies to aquaculture facilities. It is synthetic, not law.</p><ul><li>Facility A</li><li>Facility B</li></ul>
<h2>2. Measurements</h2><table><tr><th>Measurement</th><th>Depth</th><th>Frequency</th></tr>
<tr><td>Seawater temperature</td><td>3 metres</td><td>Weekly</td></tr></table>
<form action="https://external.invalid/submit"><p>Readable form text remains.</p><input name="unsafe"><button>Unsafe submit</button></form>
<img src="https://external.invalid/pixel" onerror="parent.FIXTURE_SCRIPT_RAN=true" alt="External source image">
<iframe src="https://external.invalid/frame"></iframe><svg onload="parent.FIXTURE_SCRIPT_RAN=true"></svg></body></html>'''
PDF = io.BytesIO()
pdf = canvas.Canvas(PDF)
for page in range(1, 5):
    pdf.setFont('Helvetica', 18)
    pdf.drawString(45, 780, f'Synthetic original - page {page}')
    pdf.setFont('Helvetica', 14)
    for line in range(8):
        pdf.drawString(45, 730-line*50, f'Facility monitoring, sample {page}.{line+1}.')
    pdf.showPage()
pdf.save()

class Fixture(Handler):
    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {'error': 'Local fixture Host required'})
        parsed = urlsplit(self.path)
        self.server.events.append(self.path)
        if parsed.path.startswith('/api/preview/'):
            return super().do_GET()  # Real registered-source HTTP boundary.
        if parsed.path.startswith('/vendor/pdfjs/') or parsed.path in {'/pdf-reader.html','/pdf-reader.js','/pdf-reader.css'}:
            return super().do_GET()  # Exact shipped PDF resources and production CSP.
        if parsed.path == '/fixture-info':
            return self.send(200, {'hash': self.server.fingerprint, 'id': ID})
        if parsed.path == '/fixture-events':
            return self.send(200, self.server.events)
        if parsed.path == '/api/material/original' and parse_qs(parsed.query) == {'id':[ID], 'view':['personal']}:
            return self.send(200, PDF.getvalue(), 'application/pdf')
        if parsed.path in {'/', '/fixture.js', '/fixture.css'}:
            target = HERE / ('fixture.html' if parsed.path == '/' else parsed.path[1:])
            return self.send(200, target.read_bytes(), ui_content_type(target))
        if parsed.path.startswith('/workbench/frontend/'):
            target = (UI / parsed.path.removeprefix('/workbench/frontend/')).resolve()
            if target.is_relative_to(UI) and target.is_file():
                return self.send(200, target.read_bytes(), ui_content_type(target))
        return self.send(404, {'error': 'No fixture route; business API is unavailable'})

    def do_POST(self):
        if not self.valid_host() or self.headers.get('Origin') != f'http://127.0.0.1:{self.server.server_port}':
            return self.send(403, {'error': 'Local fixture Origin required'})
        data = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        self.server.events.append({'write':self.path, 'body':data.decode(errors='replace')})
        if self.path == '/fixture-hash':
            changed = json.loads(data).get('changed') is True
            self.server.original.write_bytes(b'<h1>Changed synthetic source</h1>' if changed else RAW)
            return self.send(200, {'changed':changed})
        return self.send(400, {'error':'Fixture write recorded only; no business action exists'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ui-r3-fixture-') as temporary:
        original = Path(temporary)/'synthetic.htm'
        original.write_bytes(RAW)
        fingerprint = sha256(RAW).hexdigest()
        def artifact(command, **options):
            if command != 'artifact' or options != {'source_id':'FXHTML'}:
                raise ValueError('Only the synthetic registered HTML exists')
            return {'path':str(original), 'hash':fingerprint}
        def reader(command, **options):
            if command != 'material_source-html' or options['path'] != str(original):
                raise ValueError('Only the pure synthetic HTML reader exists')
            return read_html_original(**options)
        paths = {'pdf-reader.html': UI/'pages/pdf-reader.html', 'pdf-reader.js': UI/'components/pdf-reader.js', 'pdf-reader.css': UI/'assets/pdf-reader.css'}
        server = ThreadingHTTPServer(('127.0.0.1',args.port), Fixture)
        server.app = SimpleNamespace(reviewer=False, adapter=SimpleNamespace(call=artifact), system2=SimpleNamespace(call=reader), ui_root=UI, static_path=paths.__getitem__)
        server.events=[]
        server.original=original
        server.fingerprint=fingerprint
        print(f'R3 fixture only: http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()

if __name__ == '__main__':
    main()
