import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/scripts'))
import material_fixture
material_fixture.TARGET=Path(__file__).resolve().parent/'fixture'
raw=b'<html><body><h1>Anchoring checks</h1><p>Everything installed as part of the anchoring line must be checked after a storm.</p><p>Farm staff and managers shall have suitable competence.</p></body></html>'
material_fixture.build([('TS007','.html',raw,None,'ENGINEERING FIXTURE: Four-pane checks')])
