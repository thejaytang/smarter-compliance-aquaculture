import pathlib,json,stat,zipfile,hashlib,subprocess,time,os,shutil,datetime
root=pathlib.Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');out=pathlib.Path('/tmp/sc-full-backup-20260914');repo='thejaytang/smarter-compliance-aquaculture';tag='full-workspace-20260914'
rows=json.loads(pathlib.Path('/tmp/sc-remaining-delta-files.json').read_text());groups=[];g=[];size=0
for x in rows:
 if g and (size+x['size']>512*1024*1024 or len(g)>=2500):groups.append(g);g=[];size=0
 g.append(x);size+=x['size']
if g:groups.append(g)
ip=out/'full-progress-state.json'
index=json.loads(ip.read_text()) if ip.exists() else {'status':'UPLOADING','source_inventory_files':260410,'source_inventory_symlinks':349,'source_inventory_bytes':59160003237,'supplement_entries':len(rows),'planned_parts':len(groups),'parts':[],'deferred':[],'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def upload(p):
 for attempt in range(5):
  try:subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True,timeout=180);return
  except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
   if attempt==4:raise
   time.sleep(2**attempt)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def checkpoint():
 ip.write_text(json.dumps(index,indent=2)+'\n')
 public={k:v for k,v in index.items() if k!='deferred'};public['deferred_file_count']=len(index['deferred']);public['deferred_manifest']='DEFERRED-FILES.json'
 pub=out/'FULL-DATA-INDEX.json';pub.write_text(json.dumps(public,indent=2)+'\n');upload(pub)
 if len(index['parts'])%20==0 or index['status']!='UPLOADING':
  pending=out/'DEFERRED-FILES.json';pending.write_text(json.dumps(index['deferred']));upload(pending)
done={x['number'] for x in index['parts']};checkpoint()
for number,g in enumerate(groups,1):
 if number in done:continue
 if shutil.disk_usage(out).free<3*1024**3:raise RuntimeError('Disk space guard: less than 3 GiB free; existing source is preserved.')
 cloud=[str(root/x['path']) for x in g if stat.S_ISREG(x['mode']) and (root/x['path']).stat().st_flags&0x40000000]
 if cloud:
  cp=out/'cloud-request-batch.json';cp.write_text(json.dumps(cloud))
  # A separate persistent download process owns all cloud requests; avoid duplicate per-part calls.
  pass
 print('BUILD',number,'of',len(groups),'entries',len(g),'cloud',len(cloud),flush=True)
 p=out/f'02-remaining-data-part{number:03d}.zip';manifest=[]
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  for x in g:
   f=root/x['path'];s=f.lstat()
   if stat.S_ISLNK(s.st_mode):
    b=os.readlink(f).encode();info=zipfile.ZipInfo(x['path']);info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(info,b);manifest.append({'path':x['path'],'kind':'symlink','target':b.decode(),'sha256':hashlib.sha256(b).hexdigest()});continue
   deadline=time.monotonic()
   while f.stat().st_flags&0x40000000 and time.monotonic()<deadline:time.sleep(.25)
   if f.stat().st_flags&0x40000000:index['deferred'].append({'path':x['path'],'reason':'cloud_pending'});continue
   s=f.stat();info=zipfile.ZipInfo.from_file(f,arcname=x['path']);info.compress_type=zipfile.ZIP_DEFLATED;info._compresslevel=1;h=hashlib.sha256();left=s.st_size
   with f.open('rb') as src,z.open(info,'w',force_zip64=True) as dst:
    while left:
     b=src.read(min(left,4*1024*1024))
     if not b:raise RuntimeError('Short read: '+x['path'])
     dst.write(b);h.update(b);left-=len(b)
   after=f.stat();manifest.append({'path':x['path'],'kind':'file','bytes':s.st_size,'sha256':h.hexdigest(),'mtime_ns':s.st_mtime_ns,'changed_during_capture':(s.st_size,s.st_mtime_ns)!=(after.st_size,after.st_mtime_ns)})
  z.writestr('BACKUP-MANIFESTS/'+p.name+'.json',json.dumps(manifest))
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
 sha=digest(p);upload(p)
 remote=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/tags/'+tag]));asset=next(a for a in remote['assets'] if a['name']==p.name)
 if asset.get('digest')!='sha256:'+sha or asset['size']!=p.stat().st_size:raise RuntimeError('Remote digest mismatch: '+p.name)
 index['parts'].append({'number':number,'name':p.name,'bytes':p.stat().st_size,'sha256':sha,'entries':len(manifest),'remote_verified':True});checkpoint()
 with (out/'full-uploaded-file-manifest.jsonl').open('a') as log:
  for item in manifest:log.write(json.dumps(item)+'\n')
 print('UPLOADED VERIFIED',p.name,p.stat().st_size,'deferred',len(index['deferred']),flush=True);p.unlink()
index['status']='PARTS_COMPLETE_WITH_DEFERRED_FILES' if index['deferred'] else 'REMAINING_SUPPLEMENT_COMPLETE';checkpoint();upload(out/'full-uploaded-file-manifest.jsonl');print('FINISHED',index['status'],flush=True)
