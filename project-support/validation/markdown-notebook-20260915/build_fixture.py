import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/scripts'))
import material_fixture
material_fixture.TARGET=Path(__file__).resolve().parent/'fixture'
raw=b'<html><body><h1>Chapter 2</h1><p>The human shall remove the fish if the water is hot or the pump is off. Small fish are exempt when the water is cold.</p><ul><li>Inspect the net.</li><li>Record the result.</li></ul><table><tr><th>Check</th><th>Limit</th></tr><tr><td>Temperature</td><td>20</td></tr></table><h1>Chapter 3</h1><p>The human shall use a net.</p></body></html>'
material_fixture.build([('TS005','.html',raw,None,'ENGINEERING FIXTURE: Markdown notebook')])
