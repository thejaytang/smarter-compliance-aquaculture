from pathlib import Path
import csv,json,hashlib,base64,stat,os,time,datetime
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2';site=s/'.venv/lib/python3.12/site-packages';cache=s/'.cache/uv/archive-v0';out=root/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic/package-recovery-02';out.mkdir(exist_ok=False)
packages=[('numba','0.67.0'),('anyio','4.14.2'),('img2table','1.4.0')]
def meta(p):
 st=p.lstat();return {'path':str(p),'mode':stat.S_IMODE(st.st_mode),'size':st.st_size,'flags':st.st_flags,'inode':st.st_ino,'device':st.st_dev,'mtime_ns':st.st_mtime_ns}
def save(name,value): (out/name).write_text(json.dumps(value,indent=2)+'\n')
report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Only installed RECORD-listed dataless files of numba, anyio and img2table; exact-byte project-cache recovery, no install/network/version change','packages':[]};prepared=[];archives=list(cache.iterdir())
for pkg,ver in packages:
 record=site/f'{pkg}-{ver}.dist-info/RECORD';raw=record.read_bytes();rows=list(csv.reader(raw.decode().splitlines()));candidates=[a for a in archives if (a/pkg).is_dir() and (a/f'{pkg}-{ver}.dist-info').is_dir()]
 entry={'package':pkg,'version':ver,'installed_RECORD_sha256':hashlib.sha256(raw).hexdigest(),'cache_archives':[str(a) for a in candidates],'recorded_package_files':0,'ordinary_readable_metadata_files':0,'dataless_files':[],'missing_files':[],'unrecoverable':[],'recoverable':[],'source_read_errors':[]};report['packages'].append(entry)
 for rel,expected,size in rows:
  if not rel.startswith(pkg+'/'):continue
  entry['recorded_package_files']+=1;target=site/rel
  if not target.exists():entry['missing_files'].append(rel);continue
  info=meta(target)
  if not info['flags']&0x40000000:entry['ordinary_readable_metadata_files']+=1;continue
  entry['dataless_files'].append(rel)
  if not expected.startswith('sha256='):entry['unrecoverable'].append({'path':rel,'reason':'no installed RECORD sha256'});continue
  recovered=None
  for a in candidates:
   source=a/rel
   if not source.is_file() or source.is_symlink() or source.stat().st_flags&0x40000000:continue
   try:data=source.read_bytes()
   except OSError as e:entry['source_read_errors'].append({'path':str(source),'error':repr(e)});continue
   actual=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
   if expected!='sha256='+actual or (size and int(size)!=len(data)):continue
   staged=out/'verified-sources'/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(data)
   recovered={'relative_path':rel,'package':pkg,'version':ver,'source':str(source),'verified_source':str(staged),'target_before':info,'expected_RECORD':expected,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)};prepared.append(recovered);entry['recoverable'].append(rel);break
  if recovered is None:entry['unrecoverable'].append({'path':rel,'reason':'no readable exact-RECORD source in project cache'})
 save('audit.json',report)
print(json.dumps({'phase':'audit_complete','packages':[{'package':p['package'],'record_files':p['recorded_package_files'],'dataless':len(p['dataless_files']),'recoverable':len(p['recoverable']),'unrecoverable':len(p['unrecoverable'])} for p in report['packages']]}),flush=True)
save('prepared.json',prepared);journal=[]
for item in prepared:
 target=site/item['relative_path'];backup=out/'placeholders'/item['relative_path'];backup.parent.mkdir(parents=True,exist_ok=True)
 assert target.stat().st_dev==out.stat().st_dev
 assert meta(target)==item['target_before'],'target changed during preparation'
 staged=Path(item['verified_source']);data=staged.read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256']
 new=target.with_name(target.name+'.codex-recovery-02-new');assert not new.exists()
 with new.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.chmod(new,item['target_before']['mode']);assert hashlib.sha256(new.read_bytes()).hexdigest()==item['sha256']
 row={**item,'backup':str(backup),'state':'prepared'};journal.append(row);save('journal.json',journal)
 os.rename(target,backup);row['state']='placeholder_preserved';save('journal.json',journal)
 os.replace(new,target);assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256']
 row.update(state='restored_and_verified',target_after=meta(target),backup_after=meta(backup));save('journal.json',journal)
summary={'restored_count':len(journal),'packages':[],'scope':report['scope'],'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'whole_environment_health':'NOT_ESTABLISHED'}
for p in report['packages']:
 remaining=[rel for rel in p['dataless_files'] if (site/rel).stat().st_flags&0x40000000]
 summary['packages'].append({'package':p['package'],'version':p['version'],'recorded_package_files':p['recorded_package_files'],'dataless_before':len(p['dataless_files']),'restored_exact_RECORD_bytes':len(p['recoverable']),'dataless_remaining':len(remaining),'missing_files':p['missing_files'],'remaining_paths':remaining})
save('summary.json',summary);print(json.dumps({**summary,'packages':[{k:v for k,v in p.items() if k!='remaining_paths'} for p in summary['packages']]},indent=2),flush=True)
