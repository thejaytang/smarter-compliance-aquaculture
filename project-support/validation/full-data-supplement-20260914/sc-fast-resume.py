import pathlib,json,zipfile,hashlib,subprocess,time
root=pathlib.Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');out=pathlib.Path('/tmp/sc-full-backup-20260914');tag='full-workspace-20260914';repo='thejaytang/smarter-compliance-aquaculture'
rows=json.loads(pathlib.Path('/tmp/sc-fast-delta-files.json').read_text());index=json.loads((out/'PRIORITY-DATA-INDEX.json').read_text());done=set();parts={p['name'] for p in index['parts']}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def upload(p):
 for attempt in range(5):
  try:
   subprocess.run(['gh','release','upload',tag,str(p),'--repo',repo,'--clobber'],check=True,timeout=120);return
  except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
   if attempt==4:raise
   time.sleep(2**attempt)
def record(p,n):
 index['parts'].append({'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p),'file_count':n,'status':'UPLOADED'});index['status']='PRIORITY_DATA_PARTIAL';index['priority_uploaded_files']=len(done);index['priority_remaining_files']=len(rows)-len(done);(out/'PRIORITY-DATA-INDEX.json').write_text(json.dumps(index,indent=2));upload(out/'PRIORITY-DATA-INDEX.json')
for p in sorted(out.glob('01-current-data-part*.zip')):
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  names={i.filename for i in z.infolist() if not i.filename.startswith('BACKUP-MANIFESTS/')};done.update(names)
 if p.name not in parts:upload(p);record(p,len(names));print('SALVAGED UPLOADED',p.name,len(names),flush=True)
available=[];pending=[]
for x in rows:
 if x['path'] in done:continue
 if (root/x['path']).stat().st_flags&0x40000000:pending.append(x['path'])
 else:available.append(x)
print('READY',len(available),'CLOUD_PENDING',len(pending),flush=True)
groups=[];g=[];size=0
for x in available:
 if g and (size+x['size']>512*1024*1024 or len(g)>=3000):groups.append(g);g=[];size=0
 g.append(x);size+=x['size']
if g:groups.append(g)
start_number=max([int(p.stem[-3:]) for p in out.glob('01-current-data-part*.zip')],default=0)+1
for number,g in enumerate(groups,start_number):
 p=out/f'01-current-data-part{number:03d}.zip';manifest=[]
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
  for x in g:
   f=root/x['path'];s=f.stat()
   if s.st_flags&0x40000000:pending.append(x['path']);continue
   info=zipfile.ZipInfo.from_file(f,arcname=x['path']);info.compress_type=zipfile.ZIP_DEFLATED;info._compresslevel=1;h=hashlib.sha256();left=s.st_size
   with f.open('rb') as src,z.open(info,'w',force_zip64=True) as dst:
    while left:
     b=src.read(min(left,4*1024*1024))
     if not b:raise RuntimeError('SHORT_READ '+x['path'])
     dst.write(b);h.update(b);left-=len(b)
   manifest.append({'path':x['path'],'bytes':s.st_size,'sha256':h.hexdigest()});done.add(x['path'])
  z.writestr('BACKUP-MANIFESTS/'+p.name+'.json',json.dumps(manifest))
 with zipfile.ZipFile(p) as z:assert z.testzip() is None
 upload(p);record(p,len(manifest));print('UPLOADED',p.name,len(manifest),flush=True)
index['priority_uploaded_files']=len(done);index['priority_remaining_files']=len(rows)-len(done);index['pending_cloud_paths']=pending;index['status']='PRIORITY_DATA_COMPLETE' if len(done)==len(rows) else 'PRIORITY_DATA_PARTIAL';(out/'PRIORITY-DATA-INDEX.json').write_text(json.dumps(index,indent=2));upload(out/'PRIORITY-DATA-INDEX.json');(out/'priority-uploaded-paths.json').write_text(json.dumps(sorted(done)));print('DONE',len(done),'REMAIN',len(rows)-len(done),flush=True)
