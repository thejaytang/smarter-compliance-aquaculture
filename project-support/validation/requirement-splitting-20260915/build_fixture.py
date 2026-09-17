import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/scripts'))
import material_fixture
material_fixture.TARGET=Path(__file__).resolve().parent/'fixture'
raw=b'<html><body><h1>Chapter 2</h1><p>The human shall remove the fish if the water is hot or the pump is off. Small fish are exempt when the water is cold.</p><h1>Chapter 3</h1><p>The human shall use a net.</p></body></html>'
material_fixture.build([('TS004','.html',raw,None,'ENGINEERING FIXTURE: Requirement splitting')])
