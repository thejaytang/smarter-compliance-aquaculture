"""Compatibility shim: deployment.py owns environment creation."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from deployment import installation_commands as commands
if __name__=='__main__':
    from deployment import main
    sys.argv=[sys.argv[0],'rebuild',*sys.argv[1:]]
    main()
