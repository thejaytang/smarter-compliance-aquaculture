"""Create a local allowlisted code handoff. Never include runtime or environments."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import mmap
from pathlib import Path
import stat
import sys
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'workbench/src'))
from local_workbench.recovery import source_inventory

START_HERE='''Windows offline reviewer code handoff

This ZIP contains code and public setup/configuration templates only. It contains
no business database, original material, saved review, credentials or environment.
The coordinator supplies a separate work package for review. No package is sent
by these tools.

1. Extract this ZIP into a local folder. Keep live SQLite workspaces off shared
   network/synchronization folders. Recreate environments, never copy macOS .venv.
2. Read ENVIRONMENT.md, then run workbench\\deployment\\setup_windows.cmd.
   Prerequisites: Python 3.12 with the Windows py launcher, and uv. Setup may
   download declared Python dependencies; it does not download model weights,
   start a service, create normal source decisions or schedule jobs.
3. Run workbench\\.venv\\Scripts\\python.exe workbench\\scripts\\check_platform.py.
4. Double-click workbench\\deployment\\Open Reviewer Workbench.cmd. It creates a separate
   reviewer-workspace data folder beside the code. To choose another local folder:
   "workbench\\deployment\\Open Reviewer Workbench.cmd" --root "C:\\review-data\\reviewer-workbench"
   Select the named reviewer and import the coordinator's work ZIP using the UI.
   Reviewer mode does not need the coordinator's System1 database or config.json.
5. Follow workbench\\docs\\windows-offline-review-checklist.md. Windows/Office
   acceptance is PENDING_ACTUAL_WINDOWS until those actual checks are recorded.
   Saving a personal draft is distinct from adopting or confirming a main version.
6. For this round's synthetic acceptance, import windows-workflow-fixtures.zip
   supplied beside the code ZIP, and choose Ana Jokic. It contains engineering-only
   HTML, Excel and PDF originals plus a bound material spot-check. No business
   decision is requested. Source reviews open in the independent source workspace;
   Pending materials opens the three-pane reader/editor.
7. Save partial source, material and check results, select several under My
   submissions, and download one returned ZIP. The coordinator imports and compares
   it on macOS, adopts selected results and exports receipts. Keep remaining issues
   pending. Record the actual Windows version, browser, file reading, correction,
   save/restart/recovery and export results in the checklist.

The SHA-256 inventory is code-inventory.json. Its companion outside this ZIP also
records the ZIP hash. No automatic update, upload or transmission is enabled.
'''


def source_bytes(path):
    with path.open('rb') as stream:
        if not path.stat().st_size:return b''
        with mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as view:return bytes(view)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args(); destination=args.destination.resolve()
    inventory_path=destination.with_suffix('.inventory.json')
    if destination.exists() or inventory_path.exists():raise ValueError('Choose a new handoff destination; earlier packages are retained.')
    selected=set(source_inventory(ROOT))
    for folder, suffixes in [('workbench/scripts',{'.py'}),('workbench/deployment',{'.cmd','.command'}),('workbench/docs',{'.md'})]:
        selected.update(p for p in (ROOT/folder).glob('*') if p.is_file() and p.suffix in suffixes)
    for relative in ('system3/DESIGN.md','system3/docs/design-basis.md', 'project-support/design/offline-human-review.md', 'project-support/design/human-led-workbench-goal.md', 'system2/docs/contracts/human-material-workbench.md'):
        if (ROOT/relative).is_file():selected.add(ROOT/relative)
    files={}
    for path in sorted(selected):
        relative=path.relative_to(ROOT)
        if any(part in {'.venv','.cache','runtime','node_modules','__pycache__','.git','.env'} for part in relative.parts):
            raise ValueError('A generated or private directory entered the allowlist.')
        if path.is_symlink():raise ValueError('Code handoff refuses source aliases.')
        raw=source_bytes(path)
        if len(raw)!=path.stat().st_size:raise ValueError('Incomplete source read; no handoff was created: '+str(relative))
        files[relative.as_posix()]=raw
    files['START-HERE-WINDOWS.txt']=START_HERE.encode('utf-8')
    inventory={'format':'aquaculture-reviewer-code/1','scope':'explicitly allowlisted code, UI, public configuration templates, dependency declarations and setup/check instructions',
        'windows_acceptance':'PENDING_ACTUAL_WINDOWS','business_data_included':False,'environments_included':False,
        'files':{name:{'sha256':sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in sorted(files.items())}}
    files['code-inventory.json']=json.dumps(inventory,indent=2).encode('utf-8')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.zip.partial')
    if temporary.exists():raise ValueError('Previous incomplete code package is retained; choose a new destination.')
    with ZipFile(temporary,'w',compression=ZIP_DEFLATED,compresslevel=6) as archive:
        for name,raw in sorted(files.items()):
            entry=ZipInfo('aquaculture-offline-reviewer/'+name,date_time=(1980,1,1,0,0,0))
            entry.compress_type=ZIP_DEFLATED;entry.create_system=3
            entry.external_attr=(stat.S_IFREG| (0o755 if name.endswith('.command') else 0o644))<<16
            archive.writestr(entry,raw)
    for path in selected:
        if source_bytes(path)!=files[path.relative_to(ROOT).as_posix()]:
            raise ValueError('Source changed during packaging; incomplete ZIP retained, retry a new destination.')
    with ZipFile(temporary) as archive:
        if archive.testzip() is not None:raise ValueError('Code ZIP checksum verification failed.')
        for name,raw in files.items():
            if archive.read('aquaculture-offline-reviewer/'+name)!=raw:raise ValueError('Code ZIP byte verification failed.')
    temporary.rename(destination)
    inventory.update(zip_file=destination.name,zip_sha256=sha256(destination.read_bytes()).hexdigest(),zip_bytes=destination.stat().st_size,
        inventory_entry='aquaculture-offline-reviewer/code-inventory.json',file_count=len(files),verification='Every ZIP member independently read back and matched exact source bytes.')
    inventory_path.write_text(json.dumps(inventory,indent=2),encoding='utf-8')
    print(json.dumps({key:inventory[key] for key in ('zip_file','zip_sha256','zip_bytes','file_count','windows_acceptance')}))


if __name__=='__main__':main()
