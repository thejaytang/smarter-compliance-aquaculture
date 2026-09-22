"""Read-only browser check of the real PE002 HTML and synthetic local links/lists.

Run with System2 Python and PYTHONPATH=workbench/backend/system2/src.
No business database, original write, remote asset or model access.
"""
import argparse
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile

from pdf_extraction.evidence.material_reader import read_html_original


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=62850)
    args = parser.parse_args()
    original = Path(__file__).resolve().parents[3] / 'workbench/resources/examples/example.html'
    fingerprint = sha256(original.read_bytes()).hexdigest()
    example = read_html_original(original, fingerprint)
    with tempfile.TemporaryDirectory(prefix='ui-r8-reader-') as temporary:
        folder = Path(temporary)
        synthetic = folder / 'synthetic-source.html'
        synthetic.write_text('''<!doctype html><html><head><meta charset="utf-8"></head><body>
<h1>Local references and numbering</h1>
<p id="reference"><a href="#note">Go to exact footnote</a></p>
<ol type="a" start="4" reversed><li>Fourth letter</li><li>Third letter</li><li value="1">Explicit first</li></ol>
<ol type="I" start="9"><li>Ninth Roman</li><li>Tenth Roman</li></ol>
<p id="duplicate">Duplicate target one</p><p id="duplicate">Duplicate target two</p>
<a href="#duplicate">Ambiguous reference</a><a href="#missing">Missing reference</a>
<a href="https://example.invalid/">External reference</a>
''' + ''.join(f'<p>Static source paragraph {i}.</p>' for i in range(1, 45)) + '''
<p id="note">Exact footnote at the end. <a href="#reference">Return to reference</a></p>
</body></html>''', encoding='utf-8')
        synthetic_hash = sha256(synthetic.read_bytes()).hexdigest()
        sample = read_html_original(synthetic, synthetic_hash)
        (folder / 'example.html').write_text(example['html'], encoding='utf-8')
        (folder / 'sample.html').write_text(sample['html'], encoding='utf-8')
        (folder / 'index.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8">
<title>R8 isolated original reader check</title>
<style>body{font:16px system-ui;margin:20px}main{display:flex;gap:24px;flex-wrap:wrap}iframe{width:400px;max-width:100%;height:680px}section{max-width:100%}</style>
<h1>Read-only original reader check</h1><p>No business writes or model connection.</p>
<main><section><h2>PE002 saved original</h2><iframe title="PE002 original" sandbox="" referrerpolicy="no-referrer" src="example.html"></iframe></section>
<section><h2>Synthetic local references</h2><iframe title="Synthetic references" sandbox="" referrerpolicy="no-referrer" src="sample.html"></iframe></section></main>
</html>''', encoding='utf-8')
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *values, **kwargs):
                super().__init__(*values, directory=temporary, **kwargs)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
        print(f'R8 reader fixture: http://127.0.0.1:{server.server_port}/', flush=True)
        print(f'PE002 original unchanged SHA256: {fingerprint}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            assert sha256(original.read_bytes()).hexdigest() == fingerprint
            assert sha256(synthetic.read_bytes()).hexdigest() == synthetic_hash


if __name__ == '__main__':
    main()
