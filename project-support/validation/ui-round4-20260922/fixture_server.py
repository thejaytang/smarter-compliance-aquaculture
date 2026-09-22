"""R4 editor fixture with an isolated owning MaterialStore and real save/read HTTP.
Run in the declared System2 environment. No workers, business originals or proxy.
"""
import argparse
import base64
from hashlib import sha256
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
from types import SimpleNamespace
from urllib.parse import urlsplit
import uuid

from local_workbench.server import Handler, ui_content_type
from pdf_extraction.orchestration.material_service import MaterialService

HERE = Path(__file__).parent
ROOT = HERE.parents[2]
UI = ROOT/'workbench/frontend'
RAW = b'<html><body><h1>Synthetic editor fixture</h1><p>These source bytes must stay unchanged.</p></body></html>'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jlp8AAAAASUVORK5CYII=')
ACTOR = 'Weijie Tang'

class Fixture(Handler):
    def do_GET(self):
        if not self.valid_host():
            return self.send(403, {'error':'Local fixture only'})
        parsed = urlsplit(self.path)
        if parsed.path in {'/api/material','/api/material/history'}:
            return super().do_GET()
        if parsed.path == '/fixture-info':
            return self.send(200, {'id':self.server.identity,'csrf':'r4-fixture','source_hash':sha256(RAW).hexdigest()})
        if parsed.path == '/fixture-evidence':
            material=self.server.owner.read(self.server.identity)
            return self.send(200, {'material':material,'original_unchanged':self.server.original.read_bytes()==RAW,
                'attachment_unchanged':self.server.attachment.read_bytes()==PNG})
        if parsed.path in {'/','/fixture.js','/fixture.css'}:
            target=HERE/('fixture.html' if parsed.path=='/' else parsed.path[1:])
            return self.send(200,target.read_bytes(),ui_content_type(target))
        if parsed.path.startswith('/workbench/frontend/'):
            target=(UI/parsed.path.removeprefix('/workbench/frontend/')).resolve()
            if target.is_relative_to(UI) and target.is_file():
                return self.send(200,target.read_bytes(),ui_content_type(target))
        return self.send(404, {'error':'No fixture route. Business APIs are unavailable.'})
    def do_POST(self):
        if self.path!='/api/material/save':
            return self.send(403, {'error':'Only explicit isolated draft save is available'})
        return super().do_POST()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=0);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='ui-r4-fixture-') as folder:
        root=Path(folder);originals=root/'originals';registered=originals/'registered';registered.mkdir(parents=True)
        (registered/'FX004-001_synthetic.html').write_bytes(RAW)
        row=dict(source_id='FX004',snapshot_id='FX004-001',folder_code='registered',stored_filename='FX004-001_synthetic.html',
            content_hash=sha256(RAW).hexdigest(),file_format='html',operator_selection_decision='INCLUDE',selection_status='INCLUDE',snapshot_status='STORED',source_status='CURRENT',download_status='SUCCESS',source_title='Synthetic editing fixture')
        handoff=SimpleNamespace(records=[row],registry_sha256='a'*64,source_root=originals,assert_current=lambda:None)
        service=MaterialService(root/'workflow',root/'unused-system1');service.handoff=lambda:handoff
        opened=service.open({'request_id':str(uuid.uuid4()),'actor':ACTOR,'source_id':'FX004'})
        ref={'scope_id':'html:document','anchor':'original-document'}
        blocks=[dict(id='intro',type='text',text='Edit this opening paragraph. Keep its original source identity.',source_refs=[ref]),
            dict(id='list',type='text',text='5. First item\n6. Second item\n7. Third item',source_refs=[ref]),
            dict(id='nested',type='text',text='- Parent item\n  - Nested first\n  - Nested second\n- Final parent',source_refs=[ref]),
            dict(id='image',type='image',text='Original image caption',source_refs=[ref],image={'attachment':'synthetic.png','source_ref':ref,'attribution':'Synthetic credited image'}),
            dict(id='table',type='table',text='Retained table caption',source_refs=[ref],table={'rows':[['A','B','C','D'],*[[f'row {r} col {c}' for c in range(1,5)] for r in range(2,17)]],'merges':[{'row':0,'col':0,'rowspan':1,'colspan':2}],'notes':['Retain this first note.','Retain this second note.']}),
            dict(id='ending',type='text',text='Final paragraph after the table.',source_refs=[ref])]
        service.mutate('save', {'request_id':str(uuid.uuid4()),'actor':ACTOR,'material_id':opened['id'],'expected_revision':opened['revision'],'blocks':blocks})
        attachment=root/'synthetic.png';attachment.write_bytes(PNG)
        def fresh():
            reader=MaterialService(service.root,service.system1);reader.handoff=lambda:handoff;return reader
        def read(actor,identity,revision=None,view='personal'):
            if identity!=opened['id'] or view!='personal':raise ValueError('Only the synthetic personal material exists')
            return fresh().read(identity,revision)
        def action(actor,kind,request):
            if kind!='save' or request['material_id']!=opened['id']:raise ValueError('Only synthetic draft save is available')
            return service.mutate(kind,dict(request,actor=actor))
        server=ThreadingHTTPServer(('127.0.0.1',args.port),Fixture)
        server.app=SimpleNamespace(reviewer=False,csrf='r4-fixture',store=SimpleNamespace(session=lambda token:{'id':'fixture','name':ACTOR,'token':'fixture'}),
            collaboration=SimpleNamespace(mode='coordinator',read_material=read,material_action=action))
        server.identity=opened['id'];server.owner=service;server.original=service._path(opened['source']);server.attachment=attachment
        print(f'R4 isolated editor: http://127.0.0.1:{server.server_port}/',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.server_close()

if __name__=='__main__':main()
