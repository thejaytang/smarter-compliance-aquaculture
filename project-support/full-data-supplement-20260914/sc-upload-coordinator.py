import pathlib,json,stat,subprocess,os,time,datetime,shutil,sys
ROOT=pathlib.Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');OUT=pathlib.Path('/tmp/sc-full-backup-20260914');SAVE=ROOT/'project-support/full-data-supplement-20260914/live-checkpoint';SAVE.mkdir(exist_ok=True)
REPO='thejaytang/smarter-compliance-aquaculture';TAG='full-workspace-20260914'
def read(p):
 for _ in range(20):
  try:return json.loads(pathlib.Path(p).read_text())
  except json.JSONDecodeError:time.sleep(.1)
 raise RuntimeError('Concurrent checkpoint could not be read')
inv=read('/tmp/sc-full-inventory.json');original={r['path'] for r in inv if stat.S_ISREG(r['mode']) or stat.S_ISLNK(r['mode'])};priority={r['path'] for r in read('/tmp/sc-fast-delta-files.json')};source={r['path'] for r in read('/tmp/sc-final-remote-tree.json')['tree'] if r['type']=='blob'}
def snapshot():
 s=read(OUT/'full-progress-state.json');p=read(OUT/'PRIORITY-DATA-INDEX.json');d=read(OUT/'DEFERRED-DATA-INDEX.json')
 uploaded=source|(priority-set(p.get('pending_cloud_paths',[])))|set(d['uploaded_paths'])
 with (OUT/'full-uploaded-file-manifest.jsonl').open() as stream:
  for line in stream:
   try:uploaded.add(json.loads(line)['path'])
   except json.JSONDecodeError:pass
 return s,p,d,original-uploaded
s,p,d,missing=snapshot()
if '--check' in sys.argv:
 print(json.dumps({'original':len(original),'uploaded_unique':len(original)-len(missing),'missing':len(missing),'remaining_parts':len(s['parts'])}));sys.exit()
(OUT/'coordinator.pid').write_text(str(os.getpid()))
processes={'main':{'pid':3902,'needle':'/tmp/sc-upload-remaining.py'},'recovery':{'pid':9589,'needle':'/tmp/sc-upload-deferred.py'},'cloud':{'pid':2303,'needle':'/tmp/sc-download-cloud-bulk'},'priority_cloud':{'pid':1250,'needle':'/tmp/sc-download-cloud-keepalive'}};children={};restarts={'main':0,'recovery':0,'cloud':0};start=time.monotonic();last_publish=0;low_since=None

def alive(key):
 if key in children:return children[key].poll() is None
 r=subprocess.run(['ps','-p',str(processes[key]['pid']),'-o','command='],capture_output=True,text=True)
 return r.returncode==0 and processes[key]['needle'] in r.stdout

def launch(key,cmd,log):
 f=open(log,'a');child=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT);f.close();children[key]=child;processes[key]['pid']=child.pid;restarts[key]+=1;print('RESTART',key,child.pid,flush=True)

def stop(key):
 if alive(key):os.kill(processes[key]['pid'],15)

def publish(path):
 for n in range(4):
  try:subprocess.run(['gh','release','upload',TAG,str(path),'--repo',REPO,'--clobber'],check=True,timeout=180);return
  except (subprocess.CalledProcessError,subprocess.TimeoutExpired):
   if n==3:raise
   time.sleep(2**n)

def checkpoint(status,s,p,d,missing,force=False):
 global last_publish
 now=datetime.datetime.now(datetime.timezone.utc).isoformat();data={'status':status,'updated_utc':now,'original_files_and_symlinks':len(original),'uploaded_unique_original_paths':len(original)-len(missing),'missing_original_paths':len(missing),'first_pass_parts':len(s['parts']),'first_pass_planned_parts':s['planned_parts'],'cloud_recovery_parts':len(d['parts']),'cloud_recovery_uploaded_paths':len(d['uploaded_paths']),'processes':processes,'restarts':restarts,'free_bytes':shutil.disk_usage(OUT).free,'full_completion_requires_zero_missing_paths':True}
 tmp=OUT/'UPLOAD-STATUS.json.tmp';tmp.write_text(json.dumps(data,indent=2));tmp.replace(OUT/'UPLOAD-STATUS.json')
 for name in ['UPLOAD-STATUS.json','full-progress-state.json','PRIORITY-DATA-INDEX.json','FULL-DATA-INDEX.json','DEFERRED-DATA-INDEX.json','DIRECTORY-INVENTORY-INDEX.json','full-uploaded-file-manifest.jsonl','deferred-uploaded-file-manifest.jsonl']:
  path=OUT/name
  if path.exists():shutil.copy2(path,SAVE/name)
 if force or time.monotonic()-last_publish>120:
  try:publish(OUT/'UPLOAD-STATUS.json');last_publish=time.monotonic()
  except Exception as error:print('STATUS_UPLOAD_RETRY_LATER',type(error).__name__,flush=True)
 print('CHECKPOINT',status,'uploaded',len(original)-len(missing),'missing',len(missing),'first_pass',len(s['parts']),flush=True)

final_status=None
while time.monotonic()-start<4*60*60:
 s,p,d,missing=snapshot();free=shutil.disk_usage(OUT).free
 if not missing and len(s['parts'])==s['planned_parts'] and s['status']!='UPLOADING':
  remote=read_remote=json.loads(subprocess.check_output(['gh','api','repos/'+REPO+'/releases/tags/'+TAG]));assets={a['name']:a for a in remote['assets']};expected=p['parts']+s['parts']+d['parts']+[read(OUT/'DIRECTORY-INVENTORY-INDEX.json'),{'name':'00-current-review-databases.zip','bytes':24550336,'sha256':'2ff117bd47de3384ba3eff26c1950fd9e1ca95d0bed2635ae268d68b4fcf9a79'}]
  for item in expected:
   a=assets[item['name']];assert a['size']==item['bytes'] and a['digest']=='sha256:'+item['sha256'],item['name']
  final_status='COMPLETE';break
 if free<3*1024**3:
  stop('cloud');stop('priority_cloud');low_since=low_since or time.monotonic();checkpoint('WAITING_FOR_DISK_SPACE',s,p,d,missing)
  if time.monotonic()-low_since>600:final_status='INCOMPLETE_DISK_SPACE';break
  time.sleep(60);continue
 low_since=None
 if s['status']=='UPLOADING' and not alive('main'):
  if restarts['main']>=3:final_status='INCOMPLETE_UPLOAD_ERROR';break
  launch('main',[sys.executable,'-u','/tmp/sc-upload-remaining.py'],'/tmp/sc-remaining-upload-progress.txt')
 if d.get('status')!='COMPLETE' and not alive('recovery'):
  if restarts['recovery']>=3:final_status='INCOMPLETE_RECOVERY_ERROR';break
  launch('recovery',[sys.executable,'-u','/tmp/sc-upload-deferred.py'],'/tmp/sc-deferred-upload-progress.txt')
 if not alive('cloud') and missing:
  paths=[]
  for rel in sorted(missing):
   path=ROOT/rel
   if path.lstat().st_flags&0x40000000:paths.append(str(path))
  if paths:
   cp=OUT/'coordinator-cloud-pending.json';cp.write_text(json.dumps(paths));launch('cloud',['/tmp/sc-download-cloud-bulk','download-and-wait',str(cp),str(OUT/'coordinator-cloud-results.json')],'/tmp/sc-all-cloud-keepalive-progress.txt')
 checkpoint('UPLOADING',s,p,d,missing);time.sleep(60)
if final_status is None:final_status='INCOMPLETE_CLOUD_TIME_LIMIT'
s,p,d,missing=snapshot();(OUT/'FINAL-MISSING-PATHS.json').write_text(json.dumps(sorted(missing),indent=2));publish(OUT/'FINAL-MISSING-PATHS.json');checkpoint(final_status,s,p,d,missing,True)
if final_status=='COMPLETE':
 full=read(OUT/'FULL-DATA-INDEX.json');full['final_completion_status']='COMPLETE';full['remaining_missing_paths']=0;full['completion_status_asset']='UPLOAD-STATUS.json';(OUT/'FULL-DATA-INDEX.json').write_text(json.dumps(full,indent=2));publish(OUT/'FULL-DATA-INDEX.json')
 for name in ['full-uploaded-file-manifest.jsonl','deferred-uploaded-file-manifest.jsonl']:publish(OUT/name)
subprocess.run(['gh','release','edit',TAG,'--repo',REPO,'--title','Full workspace data supplement ('+('complete' if final_status=='COMPLETE' else 'incomplete; see UPLOAD-STATUS.json')+')'],check=True)
for key in processes:stop(key)
print('FINISHED',final_status,'missing',len(missing),flush=True)
