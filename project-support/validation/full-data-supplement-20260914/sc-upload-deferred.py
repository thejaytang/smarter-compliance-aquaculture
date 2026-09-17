import pathlib,json,stat,zipfile,hashlib,subprocess,time,os,signal,tempfile,shutil
root=pathlib.Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');out=pathlib.Path('/tmp/sc-full-backup-20260914');repo='thejaytang/smarter-compliance-aquaculture';tag='full-workspace-20260914';ip=out/'DEFERRED-DATA-INDEX.json'
index=json.loads(ip.read_text()) if ip.exists() else {'status':'UPLOADING','parts':[],'uploaded_paths':[],'failed_reads':[]}
done=set(index['uploaded_paths'])
def read_json(p):
 for attempt in range(10):
  try:return json.loads(p.read_text())
  except json.JSONDecodeError:time.sleep(.2)
 raise RuntimeError('Checkpoint could not be read')
def upload(p):
 for attempt in range(5):
  try:subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True,timeout=180);return
  except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
   if attempt==4:raise
   time.sleep(2**attempt)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def timeout(signum,frame):raise TimeoutError('source read timeout')
signal.signal(signal.SIGALRM,timeout)
while True:
 parent=read_json(out/'full-progress-state.json');priority=read_json(out/'PRIORITY-DATA-INDEX.json');pending={x['path'] for x in parent['deferred']}|set(priority.get('pending_cloud_paths',[]));pending-=done
 ready=[];size=0
 for f in sorted(pending):
  p=root/f;s=p.lstat()
  if s.st_flags&0x40000000:continue
  if ready and (size+s.st_size>512*1024*1024 or len(ready)>=2500):break
  ready.append(f);size+=s.st_size
 if not ready:
  print('WAITING',len(pending),'parent',parent['status'],flush=True)
  if not pending and parent['status']!='UPLOADING':index['status']='COMPLETE';ip.write_text(json.dumps(index));upload(ip);break
  time.sleep(30);continue
 if shutil.disk_usage(out).free<3*1024**3:raise RuntimeError('Disk space guard: below 3 GiB')
 number=len(index['parts'])+1;p=out/f'03-cloud-recovered-part{number:03d}.zip';manifest=[]
 print('BUILD',number,'files',len(ready),'bytes',size,flush=True)
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  for f in ready:
   src=root/f;s=src.stat();h=hashlib.sha256()
   try:
    with tempfile.SpooledTemporaryFile(max_size=8*1024*1024) as spool:
     signal.alarm(30)
     try:
      with src.open('rb') as stream:
       left=s.st_size
       while left:
        b=stream.read(min(left,4*1024*1024))
        if not b:raise OSError('short read')
        spool.write(b);h.update(b);left-=len(b)
     finally:signal.alarm(0)
     spool.seek(0);info=zipfile.ZipInfo.from_file(src,arcname=f);info.compress_type=zipfile.ZIP_DEFLATED;info._compresslevel=1
     with z.open(info,'w',force_zip64=True) as target:shutil.copyfileobj(spool,target,4*1024*1024)
    manifest.append({'path':f,'bytes':s.st_size,'sha256':h.hexdigest()})
   except (OSError,TimeoutError) as e:index['failed_reads'].append({'path':f,'error':type(e).__name__});print('READ_DEFERRED',f,flush=True)
  z.writestr('BACKUP-MANIFESTS/'+p.name+'.json',json.dumps(manifest))
 if not manifest:p.unlink();time.sleep(30);continue
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
 digest=sha(p);upload(p);remote=json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/releases/tags/'+tag]));a=next(x for x in remote['assets'] if x['name']==p.name);assert a.get('digest')=='sha256:'+digest and a['size']==p.stat().st_size
 done.update(x['path'] for x in manifest);index['parts'].append({'name':p.name,'bytes':p.stat().st_size,'sha256':digest,'file_count':len(manifest),'remote_verified':True});index['uploaded_paths']=sorted(done);ip.write_text(json.dumps(index,indent=2));upload(ip)
 with (out/'deferred-uploaded-file-manifest.jsonl').open('a') as log:
  for row in manifest:log.write(json.dumps(row)+'\n')
 print('UPLOADED VERIFIED',p.name,'files',len(manifest),'recovered total',len(done),flush=True);p.unlink()
