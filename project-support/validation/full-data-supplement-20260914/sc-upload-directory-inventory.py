import pathlib,json,stat,zipfile,subprocess,hashlib,time
p=pathlib.Path('/tmp/sc-full-backup-20260914/04-directories-and-inventory.zip');rows=json.loads(pathlib.Path('/tmp/sc-full-inventory.json').read_text());dirs=[x for x in rows if stat.S_ISDIR(x['mode'])]
with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as z:
 for x in dirs:
  i=zipfile.ZipInfo(x['path'].rstrip('/')+'/');i.create_system=3;i.external_attr=(x['mode']<<16)|0x10;z.writestr(i,b'')
 z.write('/tmp/sc-full-inventory.json','BACKUP-MANIFESTS/full-source-inventory.json')
with zipfile.ZipFile(p) as z:assert z.testzip() is None
h=hashlib.sha256(p.read_bytes()).hexdigest()
for n in range(5):
 r=subprocess.run(['gh','release','upload','full-workspace-20260914',str(p),'--repo','thejaytang/smarter-compliance-aquaculture','--clobber'])
 if not r.returncode:break
 time.sleep(2**n)
r.check_returncode()
a=json.loads(subprocess.check_output(['gh','api','repos/thejaytang/smarter-compliance-aquaculture/releases/tags/full-workspace-20260914']))
a=next(x for x in a['assets'] if x['name']==p.name);assert a['digest']=='sha256:'+h and a['size']==p.stat().st_size
record={'name':p.name,'bytes':p.stat().st_size,'sha256':h,'directory_count':len(dirs),'remote_verified':True}
(p.parent/'DIRECTORY-INVENTORY-INDEX.json').write_text(json.dumps(record,indent=2))
subprocess.run(['gh','release','upload','full-workspace-20260914',str(p.parent/'DIRECTORY-INVENTORY-INDEX.json'),'--repo','thejaytang/smarter-compliance-aquaculture','--clobber'],check=True)
print(json.dumps(record))
