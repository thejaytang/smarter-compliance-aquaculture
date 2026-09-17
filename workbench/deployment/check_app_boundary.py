"""Check the current Git index, not old history; never delete local files."""
from pathlib import PurePosixPath
import argparse
import re
import unicodedata
import subprocess
import sys

ROOT_FILES={'.gitattributes','.gitignore','.python-version','README.md','USER_GUIDE.md','ENVIRONMENT.md','AGENTS.md','deployment.py','Open Workbench (Windows).cmd','Open Workbench (macOS).command'}
WORKBENCH_FILES={'workbench/pyproject.toml','workbench/workspace/README.txt','workbench/runtime/README.txt'}
PREFIXES=('workbench/frontend/','workbench/backend/application/','workbench/backend/shared/','workbench/backend/system3/',
 'workbench/backend/system1/src/','workbench/backend/system1/deployment/',
 'workbench/backend/system2/src/','workbench/backend/system2/config/','workbench/backend/system2/ui/',
 'workbench/contracts/','workbench/config/','workbench/deployment/')
INITIAL_DATA_FILES={'workbench/initial-data/'+name for name in ('README.md','manifest.json','workspace-20260917.zip','workspace-20260917.zip.sha256')}
COMPONENT_FILES={'workbench/backend/__init__.py','workbench/backend/system2/pyproject.toml','workbench/backend/system2/uv.lock','workbench/backend/system2/USER_GUIDE.md'}

def business_file(path):
    p=PurePosixPath(path)
    if p.name=='.DS_Store':return True
    if path in ROOT_FILES|WORKBENCH_FILES|COMPONENT_FILES|INITIAL_DATA_FILES:return False
    if not path.startswith(PREFIXES):return True
    if any(x in p.parts for x in ('.venv','node_modules','__pycache__','.cache','runtime','workspace','tests','project-support')):return True
    if p.name.startswith('.env') and p.name!='.env.example':return True
    if p.name in ('ai-provider.json','model-provider.local.json','machine-assessment-rules.local.json','scoring-rules.local.json'):return True
    return p.suffix.lower() in {'.sqlite','.sqlite3','.db','.zip','.xlsx','.key','.pem','.pyc','.log'}

def development_file(path):
    p=PurePosixPath(path)
    if path=='PROJECT_STATE.md':return True
    if not path.startswith(('project-support/','workbench/tests/','workbench/examples/','workbench/scripts/')):return False
    if any(x in p.parts for x in ('.git','.venv','node_modules','__pycache__','.cache','cache','runtime','tmp')):return False
    if p.name.startswith('.env') and p.name!='.env.example':return False
    if p.name in {'ai-provider.json','model-provider.local.json','server.json','service.lock','.DS_Store'}:return False
    return p.suffix.lower() not in {'.sqlite','.sqlite3','.db','.key','.pem','.pyc','.ses'} and not p.name.endswith(('-wal','-shm','-journal'))


def naming_issues(paths, *, style=True):
    issues=[];seen={}
    for path in paths:
        p=PurePosixPath(path)
        for component in p.parts:
            if (re.match(r'^(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\.|$)',component,re.I)
                or component.endswith((' ','.')) or re.search(r'[<>:"\\|?*\x00-\x1f]',component)):
                issues.append('Windows-incompatible name: '+path)
        for part in (p,*p.parents):
            spelling=str(part);key=unicodedata.normalize('NFC',spelling).casefold()
            if key in seen and seen[key]!=spelling:issues.append('Case/Unicode collision: '+spelling+' / '+seen[key])
            seen[key]=spelling
        if not style or '/vendor/' in path:continue
        if p.suffix=='.py' and not re.fullmatch(r'[a-z_][a-z0-9_]*',p.stem):
            issues.append('Python module must use snake_case: '+path)
        if any(any(c.isupper() for c in part) for part in p.parts[:-1]):
            issues.append('Product directories must use lowercase: '+path)
    return sorted(set(issues))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development',action='store_true',help='Allow Jay development documents and tests; retain credential/runtime exclusions.')
    development=parser.parse_args().development
    paths=subprocess.check_output(['git','ls-files','-z']).decode('utf-8').split('\0')
    paths=[p for p in paths if p]
    bad=[p for p in paths if business_file(p) and not (development and development_file(p))]
    if bad:
        print('Excluded local/development data remains in the product index:\n'+'\n'.join(bad));return 1
    issues=naming_issues(paths,style=False)+naming_issues([p for p in paths if not development_file(p)])
    if issues:
        print('\n'.join(issues));return 1
    print(('Development' if development else 'Product')+' index boundary and naming checks passed.');return 0

if __name__=='__main__':sys.exit(main())
