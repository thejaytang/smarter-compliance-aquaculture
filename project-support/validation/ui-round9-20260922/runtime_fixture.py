"""Disposable runtime-status browser check. API calls are read-only synthetic data."""
import argparse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=62852)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[3] / 'workbench/frontend/components/runtime-status.js'
    with tempfile.TemporaryDirectory(prefix='ui-r9-runtime-') as temporary:
        folder = Path(temporary)
        (folder / 'runtime-status.js').write_bytes(source.read_bytes())
        (folder / 'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Isolated runtime status check</title><style>body,dialog{font:16px system-ui}dialog{max-height:75vh;width:600px;max-width:85vw;overflow:auto}small{display:block}section{padding:10px;border-bottom:1px solid #ddd}[aria-disabled=true]{opacity:.6}button{margin:8px}summary{cursor:pointer}</style>
<h1>Read-only runtime status fixture</h1><label><input id="fail" type="checkbox">Fail status reads</label>
<label><input id="delay" type="checkbox">Delay reads for three seconds</label>
<button id="background">Background refresh in five seconds</button><button id="open">Runtime status</button>
<p id="requests" role="status">0 read requests</p><dialog id="runtime" aria-label="Runtime status"></dialog>
<script type="module" src="fixture.js"></script></html>''', encoding='utf-8')
        (folder / 'fixture.js').write_text('''import {installRuntimeStatus} from './runtime-status.js';
let reads=0;const q=s=>document.querySelector(s);
const runtime=installRuntimeStatus({button:q('#open'),dialog:q('#runtime'),api:async path=>{
 if(path!=='/api/runtime-status')throw Error('Only synthetic status reads are available');
 const count=++reads,fail=q('#fail').checked,delay=q('#delay').checked;q('#requests').textContent=count+' read requests';
 if(delay)await new Promise(resolve=>setTimeout(resolve,3000));if(fail)throw Error('Synthetic status read failed');
 return {checked_at:'synthetic read '+count,status:'healthy',components:['source','material','requirements'].map(id=>({id,name:id,state:'idle',last_success:'fixture checkpoint',last_error:{at:'earlier',message:'Retained '+id+' failure',event_id:'fixture-'+id}}))};
}});q('#background').onclick=()=>{q('#requests').textContent='Background read scheduled';setTimeout(()=>runtime.refresh(true),5000);};
''', encoding='utf-8')
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *values, **kwargs):
                super().__init__(*values, directory=temporary, **kwargs)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
        print(f'R9 runtime fixture: http://127.0.0.1:{server.server_port}/', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == '__main__':
    main()
