"""Bounded recovery of unreadable historical rendering artifacts, never stores or originals."""
from pathlib import Path
import hashlib,json
area=Path(__file__).resolve().parent;root=area.parents[1]
packages=[root/'workbench/runtime'/name for name in ('round2-final-recovery','workflow-correction-final-backup','archive-focus-pre-load-backup','workflow-correction-pre-load-backup-verified','workflow-correction-pre-load-backup','offline-collaboration-pre-migration-backup')]
packages=[p for p in packages if (p/'manifest.json').is_file()]
manifests=[json.loads((p/'manifest.json').read_text()) for p in packages]
def content(path):
 with path.open('rb') as stream:return stream.read(path.stat().st_size)
def sha(data):return hashlib.sha256(data).hexdigest()
def restore(path):
 path=path.resolve();rel=path.relative_to(root);key=rel.as_posix()
 if not key.startswith('system2/runtime/workflow/artifacts/') or {'crops':'.png','overlays':'.png','pages':'.png','raw':'.json'}.get(path.parent.name)!=path.suffix:raise ValueError('Not an eligible historical crop.')
 old=content(path)
 if len(old)==path.stat().st_size:raise ValueError('Current resource is readable; no restoration justified.')
 canonical=path.parent.parent/'canonical.json';ck=canonical.relative_to(root).as_posix();current=content(canonical)
 valid=[]
 for package,manifest in zip(packages,manifests):
  entry=manifest['files'].get(key)
  if manifest.get('status')!='complete' or not entry or entry['bytes']!=path.stat().st_size:continue
  if manifest['files'].get(ck,{}).get('sha256')!=sha(current):continue
  saved=content(package/'files'/rel)
  if len(saved)!=entry['bytes'] or sha(saved)!=entry['sha256']:continue
  if sha(content(package/'files'/ck))!=sha(current):continue
  valid.append((package,entry,saved))
 hashes={entry['sha256'] for _,entry,_ in valid}
 if len(valid)<2 or len(hashes)!=1:raise ValueError('No two readable historical copies agree with recorded identity and current Canonical.')
 chosen,entry,saved=valid[0]
 preserved=area/'unreadable-retained'/rel
 if preserved.exists():raise ValueError('Prior unreadable resource already retained; inspect manually.')
 preserved.parent.mkdir(parents=True,exist_ok=True);path.rename(preserved);path.write_bytes(saved)
 if sha(content(path))!=entry['sha256']:raise ValueError('Restored bytes failed validation.')
 journal=area/'restored-historical-crops.json';records=json.loads(journal.read_text()) if journal.exists() else []
 records.append({'path':key,'bytes':entry['bytes'],'sha256':entry['sha256'],'canonical_sha256':sha(current),'preserved':str(preserved.relative_to(root)),'verified_packages':[str(p.relative_to(root)) for p,_,_ in valid]})
 journal.write_text(json.dumps(records,indent=2));return key
if __name__=='__main__':
 import sys
 print(restore(root/sys.argv[1]))
