"""Unified local setup, environment checks, explicit migration and launch."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).absolute().parent
BACKEND=ROOT/'workbench/backend'

def interpreter(component,windows=None):
    windows=os.name=='nt' if windows is None else windows
    return component/'.venv'/('Scripts/python.exe' if windows else 'bin/python')

def required_python():return (ROOT/'.python-version').read_text().strip()

def environment():
    env=dict(os.environ,PYTHONUTF8='1',PYTHONPATH=os.pathsep.join(map(str,[BACKEND/'application',ROOT/'workbench'])),
             PYTHONPYCACHEPREFIX=os.environ.get('PYTHONPYCACHEPREFIX',str(ROOT/'workbench/runtime/cache/python')),
             NUMBA_CACHE_DIR=str(ROOT/'workbench/runtime/cache/numba'))
    if os.name=='nt':
        paths=[]
        for base in (ROOT/'workbench/runtime/cache/tools',ROOT/'workbench/.cache/tools',ROOT.parent/'.tools'):
            paths.extend([base/'bin',base/'python/Scripts',*base.glob('node-*-win-x64'),*base.glob('native/poppler-*/Library/bin')])
        for key,suffix in [('LOCALAPPDATA','Programs/Tesseract-OCR'),('ProgramFiles','Tesseract-OCR')]:
            if env.get(key):paths.append(Path(env[key])/suffix)
        env['PATH']=os.pathsep.join([*[str(p) for p in paths if p.is_dir()],env.get('PATH','')])
    return env

def run(command,cwd=ROOT):
    return subprocess.run(list(map(str,command)),cwd=cwd,env={**environment(),'UV_CACHE_DIR':str(ROOT/'workbench/runtime/cache/uv')},check=True)

def installation_commands(root,python,windows=False,reviewer=False):
    root=Path(root);backend=root/'workbench/backend';commands=[]
    for c in (([backend/'system1'] if not reviewer else [])+[root/'workbench']):
        commands.append((root,[python,'-m','venv',str(c/'.venv'),'--without-pip']))
        declaration=c/('deployment/requirements.lock' if c.name=='system1' else 'pyproject.toml')
        args=['uv','pip','install','--python',str(interpreter(c,windows)),'-r',str(declaration)]
        if c.name=='system1':args.append('--require-hashes')
        if c.name=="system1" or windows:commands.append((root,args))
    commands.append((backend/'system2',['uv','sync','--locked','--python',python,'--no-editable','--inexact']))
    return commands

def rebuild(dry_run=False):
    if not shutil.which('uv',path=environment().get('PATH')):raise ValueError('Install uv, then run deployment.py install again. See ENVIRONMENT.md.')
    if '.'.join(map(str,sys.version_info[:2]))!=required_python():raise ValueError('Rebuild requires Python '+required_python()+'.')
    for cwd,command in installation_commands(ROOT,sys.executable,os.name=='nt'):
        print(subprocess.list2cmdline(command),flush=True)
        if not dry_run:run(command,cwd)

def check():
    report={'python_target':required_python(),'platform':sys.platform,'environments':{},'workspace_migrated':(ROOT/'workbench/runtime/state/layout.json').is_file()}
    for label,path in [('application',ROOT/'workbench'),('system1',BACKEND/'system1'),('system2',BACKEND/'system2')]:
        p=interpreter(path);report['environments'][label]={'available':p.is_file(),'path':str(p)}
        if p.is_file():report['environments'][label]['version']=subprocess.check_output([str(p),'--version'],text=True).strip()
    print(json.dumps(report,indent=2));return report

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',nargs='?',default='start',choices=['start','install','rebuild','check','migrate','restore-initial','verify','backup','restore'])
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--root',type=Path,default=ROOT/'workbench')
    parser.add_argument('--no-browser',action='store_true');parser.add_argument('--reviewer',action='store_true')
    parser.add_argument('--archive',type=Path);parser.add_argument('--sha256')
    parser.add_argument('--destination',type=Path)
    parser.add_argument('--legacy-system1',type=Path);parser.add_argument('--legacy-system2',type=Path)
    args=parser.parse_args()
    for path in (BACKEND/'application',ROOT/'workbench',ROOT/'workbench/deployment'):sys.path.insert(0,str(path))
    if args.action in ('install','rebuild'):rebuild(args.dry_run);return
    if args.action=='check':check();return
    if args.action in ('backup','restore'):
        if not args.destination:parser.error('Provide a new --destination directory.')
        from local_workbench.recovery import backup,restore
        if args.action=='backup':result=backup(ROOT,args.destination)
        else:
            if not args.archive:parser.error('Provide the recovery directory with --archive.')
            result=restore(args.archive,args.destination)
        print(json.dumps(result,indent=2));return
    if args.action=='restore-initial':
        if not args.archive or not args.sha256:parser.error('Provide --archive and --sha256 from the initial delivery.')
        from restore_initial_data import restore
        print(json.dumps(restore(ROOT,args.archive,args.sha256)));return
    if args.action=='migrate':
        from local_workbench.workspace_migration import migrate
        legacy=args.legacy_system1 or ROOT/'system1'
        config=legacy/'Code/config/config.json'
        print(json.dumps(migrate(ROOT,args.root,legacy,config,args.legacy_system2),indent=2));return
    if args.action=='verify':
        from local_workbench.workspace_integrity import inspect
        report=inspect(args.root/'workspace/databases',args.root/'workspace/sources')
        print(json.dumps({k:v for k,v in report.items() if k!='history'},indent=2));return
    if not (args.root/'runtime/state/layout.json').exists():raise ValueError('Workspace setup is required. Restore initial data once, or run the explicit migration. Ordinary startup never resets or imports data.')
    python=interpreter(ROOT/'workbench')
    if not python.exists():raise ValueError('Run deployment.py install before starting Workbench.')
    command=[python,'-m','local_workbench','--root',args.root]
    if args.no_browser:command.append('--no-browser')
    if args.reviewer:command.append('--reviewer')
    run(command)

if __name__=='__main__':
    target=required_python()
    if '.'.join(map(str,sys.version_info[:2]))!=target:
        command=['py','-'+target] if os.name=='nt' else [shutil.which('python'+target) or 'python'+target]
        try:sys.exit(subprocess.call(command+[str(Path(__file__).resolve()),*sys.argv[1:]]))
        except FileNotFoundError:sys.exit('Install Python '+target+' first. See ENVIRONMENT.md.')
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as exc:sys.exit(str(exc))
