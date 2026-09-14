"""Read-only checks of the original explicitly bound to a source record."""
from hashlib import sha256
from pathlib import Path

def original_ready(cfg,record,verify_hash=False):
 if record.get('download_status')!='SUCCESS' or record.get('snapshot_status')!='STORED':return False
 try:
  root=Path(cfg['source_root']).resolve();path=(root/str(record.get('folder_code') or '')/str(record.get('stored_filename') or '')).resolve()
  if not path.is_relative_to(root) or not path.is_file() or path.stat().st_size<=0:return False
  if verify_hash:
   hasher=sha256()
   with path.open('rb') as stream:
    for chunk in iter(lambda:stream.read(1024*1024),b''):hasher.update(chunk)
   return hasher.hexdigest()==record.get('content_hash')
  return True
 except (OSError,ValueError):return False
