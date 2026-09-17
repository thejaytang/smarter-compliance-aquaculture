"""Read-only relocation/link preservation checks, plus a temporary local code handoff."""
from pathlib import Path
from urllib.parse import unquote
import hashlib,json,os,re,subprocess,sys,tempfile,zipfile
R=Path(__file__).resolve().parents[2];E=Path(__file__).resolve().parent
m=json.loads((E/'consolidation-manifest.json').read_text());h=lambda b:hashlib.sha256(b).hexdigest()
edits={x['path']:x for x in m['edits']};moves={x['old']:x['new'] for x in m['moves']};reverse={b:a for a,b in moves.items()}
for item in m['moves']:
 p=R/item['new'];entry=edits.get(item['new']);prior=R/entry['backup'] if entry else p
 assert h(prior.read_bytes())==item['sha256'],item
 assert not (R/item['old']).exists(),item
for item in m['edits']:
 assert h((R/item['backup']).read_bytes())==item['before'],item
 assert h((R/item['path']).read_bytes())==item['after'],item
pattern=re.compile(r'!?\[[^\]\n]*\]\(([^\n]*?)\)')
def links(raw,parent):
 result=[]
 for ref in pattern.findall(raw):
  ref=ref.strip('<>')
  if re.match(r'^[a-zA-Z][\w+.-]*:',ref) or ref.startswith('#'):continue
  rel=unquote(ref.split('#')[0])
  result.append(Path(os.path.normpath(str(parent/rel))))
 return result
new_broken=[];existing_broken=[];count=0
for rel,entry in edits.items():
 p=R/rel
 if p.suffix!='.md':continue
 old=R/reverse.get(rel,rel)
 baseline=links((R/entry['backup']).read_text(),old.parent)
 old_missing=set()
 for target in baseline:
  try: key=str(target.relative_to(R))
  except ValueError:key=''
  transformed=R/moves.get(key,key) if key else target
  if key.startswith('docs/') and key not in moves:transformed=R/'project-support'/key[5:]
  if not transformed.exists():old_missing.add(str(transformed))
 for target in links(p.read_text(),p.parent):
  count+=1
  if not target.exists():
   result={'file':rel,'target':str(target)}
   (existing_broken if str(target) in old_missing else new_broken).append(result)
assert not new_broken,new_broken
assert not (R/'docs').exists()
assert [p.name for p in R.glob('Open*')]==['Open Workbench.command']
subprocess.run(['/bin/zsh','-n',str(R/'Open Workbench.command')],check=True)
result={'preserved_relocations':len(m['moves']),'preserved_edit_backups':len(m['edits']),'checked_markdown_links':count,'new_broken_links':new_broken,'preexisting_missing_links':existing_broken,'root_entries':sorted(p.name for p in R.iterdir()),'mac_launcher_syntax':'PASS','windows_execution':'PENDING_ACTUAL_WINDOWS'}
with tempfile.TemporaryDirectory(prefix='aquaculture-code-handoff-') as temp:
 dest=Path(temp)/'code.zip'
 command=[str(R/'workbench/.venv/bin/python'),str(R/'workbench/scripts/build_windows_reviewer_code.py'),'--destination',str(dest)]
 process=subprocess.run(command,check=True,capture_output=True,text=True)
 with zipfile.ZipFile(dest) as z:
  prefix='aquaculture-offline-reviewer/'
  for name in ['workbench/deployment/Open Workbench.cmd','workbench/deployment/Open Reviewer Workbench.cmd','project-support/design/offline-human-review.md','project-support/design/human-led-workbench-goal.md']:
   assert z.read(prefix+name)==(R/name).read_bytes(),name
  assert prefix+'Open Workbench.cmd' not in z.namelist()
  instructions=z.read(prefix+'START-HERE-WINDOWS.txt').decode()
  assert 'workbench\\deployment\\Open Reviewer Workbench.cmd' in instructions
  result['code_handoff']={'byte_readback':'PASS','file_count':len(z.namelist()),'temporary_bundle_removed_after_validation':True}
(E/'consolidation-checks.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
