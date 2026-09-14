from pathlib import Path
import tomllib,json,email,urllib.request,urllib.parse,hashlib,csv,base64,zipfile,os,stat,platform,datetime
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2';site=s/'.venv/lib/python3.12/site-packages';base=root/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic';out=base/'locked-wheel-recovery-03';out.mkdir(exist_ok=False)
lock_bytes=(s/'uv.lock').read_bytes();lock=tomllib.loads(lock_bytes.decode());previous=json.loads((base/'package-recovery-02/summary.json').read_text());report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'uv_lock_sha256':hashlib.sha256(lock_bytes).hexdigest(),'machine':platform.machine(),'packages':[]};prepared=[]
def save(name,v):(out/name).write_text(json.dumps(v,indent=2)+'\n')
def meta(p):
 st=p.lstat();return {'path':str(p),'mode':stat.S_IMODE(st.st_mode),'size':st.st_size,'flags':st.st_flags,'inode':st.st_ino,'device':st.st_dev,'mtime_ns':st.st_mtime_ns}
for old in previous['packages']:
 name=old['package'];p=next(x for x in lock['package'] if x['name']==name);info=email.message_from_string((site/f"{name}-{p['version']}.dist-info/METADATA").read_text());assert info['Version']==old['version']==p['version'];assert p['source']['registry']=='https://pypi.org/simple'
 wheels=[w for w in p['wheels'] if ('cp312-cp312-macosx_12_0_arm64' in w['url'] if name=='numba' else 'py3-none-any.whl' in w['url'])];assert len(wheels)==1
 wheel=wheels[0];url=urllib.parse.urlsplit(wheel['url']);assert url.scheme=='https' and url.hostname=='files.pythonhosted.org'
 item={'name':name,'version':p['version'],'wheel':wheel,'status':'prepared','remaining_input_count':len(old['remaining_paths'])};report['packages'].append(item);save('downloads.json',report)
 try:
  request=urllib.request.Request(wheel['url'],headers={'User-Agent':'SmarterCompliance-LockedDependencyRecovery/1'})
  with urllib.request.urlopen(request,timeout=45) as response:
   final=urllib.parse.urlsplit(response.url);assert final.scheme=='https' and final.hostname=='files.pythonhosted.org';data=response.read(wheel['size']+1);item['http_status']=response.status
 except Exception as e:item.update(status='download_failed',error=repr(e));save('downloads.json',report);print(name,repr(e),flush=True);continue
 actual=hashlib.sha256(data).hexdigest();item['download_sha256']=actual;item['download_size']=len(data)
 if wheel['hash']!='sha256:'+actual or len(data)!=wheel['size']:item['status']='lock_hash_or_size_mismatch';save('downloads.json',report);continue
 archive=out/Path(url.path).name;archive.write_bytes(data);item.update(status='download_verified',archive=str(archive));save('downloads.json',report)
 rows={r[0]:r[1:] for r in csv.reader((site/f"{name}-{p['version']}.dist-info/RECORD").open())};item['files']=[]
 with zipfile.ZipFile(archive) as z:
  wheel_record={r[0]:r[1:] for r in csv.reader(z.read(f"{name}-{p['version']}.dist-info/RECORD").decode().splitlines())}
  for rel in old['remaining_paths']:
   target=site/rel
   if not target.stat().st_flags&0x40000000:item['files'].append({'path':rel,'status':'no_longer_dataless_no_change'});continue
   b=z.read(rel);actual=hashlib.sha256(b).hexdigest();record='sha256='+base64.urlsafe_b64encode(hashlib.sha256(b).digest()).decode().rstrip('=')
   if rows[rel][0]!=record or wheel_record[rel][0]!=record or str(len(b))!=rows[rel][1]:item['files'].append({'path':rel,'status':'individual_RECORD_mismatch'});continue
   staged=out/'verified-sources'/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(b)
   prepared.append({'relative_path':rel,'package':name,'version':p['version'],'wheel':str(archive),'verified_source':str(staged),'sha256':actual,'expected_RECORD':record,'target_before':meta(target)});item['files'].append({'path':rel,'status':'prepared_exact_RECORD'})
 save('downloads.json',report)
save('prepared.json',prepared);journal=[]
for item in prepared:
 target=site/item['relative_path'];backup=out/'placeholders'/item['relative_path'];backup.parent.mkdir(parents=True,exist_ok=True);assert target.stat().st_dev==out.stat().st_dev;assert meta(target)==item['target_before']
 data=Path(item['verified_source']).read_bytes();assert hashlib.sha256(data).hexdigest()==item['sha256'];new=target.with_name(target.name+'.codex-recovery-03-new');assert not new.exists()
 with new.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.chmod(new,item['target_before']['mode']);assert hashlib.sha256(new.read_bytes()).hexdigest()==item['sha256'];entry={**item,'backup':str(backup),'state':'prepared'};journal.append(entry);save('journal.json',journal)
 os.rename(target,backup);entry['state']='placeholder_preserved';save('journal.json',journal);os.replace(new,target);assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256'];entry.update(state='restored_and_verified',target_after=meta(target),backup_after=meta(backup));save('journal.json',journal)
summary={'restored_count':len(journal),'packages':[],'version_change':False,'installation':False,'uploaded_documents':False,'whole_environment_health':'NOT_ESTABLISHED'}
for old in previous['packages']:
 remaining=[p for p in old['remaining_paths'] if (site/p).stat().st_flags&0x40000000];summary['packages'].append({'name':old['package'],'version':old['version'],'restored':sum(x['package']==old['package'] for x in journal),'remaining_paths':remaining})
save('summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
