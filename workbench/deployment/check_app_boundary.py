"""Reject active business data in the application Git index (not Git history)."""
from pathlib import PurePosixPath
import subprocess
import sys

EXACT={'system1/Code/config/config.json','system1/Code/config/schedule.json','system1/Requirement_Source_Registry.xlsx','system2/System2_Requirement_Register.xlsx','system2/System2_Requirement_Register 2.xlsx','system1/Others/Legacy_Requirement_Workbook.xlsx'}

def business_file(path):
    p=PurePosixPath(path)
    return (path in EXACT or 'runtime' in p.parts or path.startswith('reviewer-workspace/')
        or path.startswith('project-support/') and (path.endswith('.zip') or 'fixture' in p.parts or 'pytest-tmp' in p.parts)
        or path.startswith('system1/Data/') and path not in ('system1/Data/STORAGE.md','system1/Data/.gitkeep')
        or path.startswith(('system1/saved-records/','workbench/saved-packages/')) and (path.endswith('.zip') or path.endswith('.zip.sha256'))
        or p.name in ('ai-provider.json','model-provider.local.json') or p.name=='.env')

def main():
    paths=subprocess.check_output(['git','ls-files','-z']).decode('utf-8').split('\0')
    bad=[p for p in paths if p and business_file(p)]
    if bad:
        print('Application update contains local business data/settings:\n'+'\n'.join(bad));return 1
    print('Application/data boundary passed.');return 0

if __name__=='__main__':sys.exit(main())
