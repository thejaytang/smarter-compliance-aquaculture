"""Restore the checksummed one-time source seed into a fresh installation only."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile
import zipfile
from initialize_local import initialize

ROOT=Path(__file__).resolve().parents[2]

def restore(root, archive, expected_sha256):
    root=Path(root).resolve();archive=Path(archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=expected_sha256.strip().lower():raise ValueError('Initial data checksum differs.')
    if (root/'system1/Code/runtime/governance.sqlite').exists() or (root/'workbench/runtime/workbench.sqlite').exists():
        raise ValueError('This installation already has work. Initial data cannot overwrite an existing workspace; use Collaboration.')
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate archive entries.')
        manifest=json.loads(z.read('manifest.json'))
        if manifest.get('schema')!='source-initial-data/1' or set(z.namelist())!={'manifest.json',*manifest['files']}:raise ValueError('Invalid initial data manifest.')
        with tempfile.TemporaryDirectory(prefix='initial-data-',dir=root) as tmp:
            prepared=[]
            for rel,entry in manifest['files'].items():
                path=PurePosixPath(rel)
                allowed=rel.startswith('system1/Data/') or rel in ('system1/Code/runtime/governance.sqlite','system1/Code/runtime/governance-migration-input.xlsx','system1/Code/runtime/logs/source-assessments.sqlite','system1/Requirement_Source_Registry.xlsx','workbench/runtime/workbench.sqlite')
                if not allowed or path.is_absolute() or '..' in path.parts or '\\' in rel:raise ValueError('Unexpected initial data path.')
                target=(root/rel).resolve()
                if not target.is_relative_to(root):raise ValueError('Initial data leaves the repository.')
                if target.exists():raise ValueError('Initial data would overwrite '+rel)
                info=z.getinfo(rel)
                if info.file_size!=entry['bytes'] or info.file_size>128*1024*1024:raise ValueError('Initial data size differs.')
                raw=z.read(rel)
                if hashlib.sha256(raw).hexdigest()!=entry['sha256']:raise ValueError('Initial data content differs: '+rel)
                staged=Path(tmp)/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(raw);prepared.append((staged,target))
            written=[]
            try:
                for staged,target in prepared:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as out:
                        written.append(target)
                        out.write(staged.read_bytes())
                initialize(root)
            except Exception:
                for target in reversed(written):target.unlink(missing_ok=True)
                raise
    return dict(status='restored',files=len(prepared),source_revision=manifest.get('source_revision'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('archive',type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();print(json.dumps(restore(ROOT,args.archive,args.sha256)))
