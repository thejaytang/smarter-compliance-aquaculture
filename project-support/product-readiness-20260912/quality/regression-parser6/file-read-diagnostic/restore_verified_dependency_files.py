from pathlib import Path
import os,csv,json,hashlib,base64,stat,datetime
root=Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side');s=root/'system2';out=root/'project-support/product-readiness-20260912/quality/regression-parser6/file-read-diagnostic';point=out/'environment-recovery-01';point.mkdir(exist_ok=False)
audit=json.loads((out/'recovery-source-audit.json').read_text());journal=[]
def metadata(p):
 st=p.stat();return {'path':str(p),'mode':stat.S_IMODE(st.st_mode),'size':st.st_size,'flags':st.st_flags,'device':st.st_dev,'inode':st.st_ino,'mtime_ns':st.st_mtime_ns}
def save(): (point/'journal.json').write_text(json.dumps(journal,indent=2)+'\n')
for item in audit['dependency_candidates']:
 source=Path(item['source']);target=Path(item['target']);site=target.parents[len(Path(target.relative_to(s/'.venv/lib/python3.12/site-packages')).parts)-1]
 rel=target.relative_to(s/'.venv/lib/python3.12/site-packages')
 record=s/'.venv/lib/python3.12/site-packages'/f"{item['package']}-{item['version']}.dist-info/RECORD"
 expected={r[0]:r[1] for r in csv.reader(record.open())}[str(rel)];data=source.read_bytes();sha=hashlib.sha256(data).hexdigest();encoded=base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip('=')
 assert sha==item['sha256'] and expected=='sha256='+encoded
 backup=point/'placeholders'/rel;backup.parent.mkdir(parents=True,exist_ok=True);assert target.stat().st_dev==point.stat().st_dev
 before=metadata(target);entry={'package':item['package'],'version':item['version'],'source':str(source),'expected_installed_record':expected,'sha256':sha,'target_before':before,'backup':str(backup),'state':'prepared','at':datetime.datetime.now(datetime.timezone.utc).isoformat()};journal.append(entry);save()
 staged=target.with_name(target.name+'.codex-recovery-01-new');assert not staged.exists()
 with staged.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 os.chmod(staged,before['mode']);assert hashlib.sha256(staged.read_bytes()).hexdigest()==sha
 os.rename(target,backup);entry['state']='placeholder_preserved';save()
 os.replace(staged,target);assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
 entry.update(state='restored_and_verified',target_after=metadata(target),backup_after=metadata(backup));save()
print(json.dumps({'status':'RESTORED_EXACT_RECORD_BYTES','count':len(journal),'journal':str(point/'journal.json'),'version_change':False,'network_or_package_install':False},indent=2))
