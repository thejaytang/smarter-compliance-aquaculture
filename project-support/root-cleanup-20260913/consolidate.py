"""One-time guarded root consolidation. Retains prior bytes and records relocation."""
from pathlib import Path
import hashlib,json,os,re,shutil
from urllib.parse import unquote
R=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent
manifest_path=E/'consolidation-manifest.json'
if manifest_path.exists(): raise SystemExit('Already applied; inspect the existing manifest before any recovery.')
sha=lambda b:hashlib.sha256(b).hexdigest()
old_docs=R/'docs'
mapping={p:R/'project-support'/p.relative_to(old_docs) for p in old_docs.rglob('*') if p.is_file()}
for n in ('Open Workbench.cmd','Open Reviewer Workbench.cmd'):
 mapping[R/n]=R/'workbench/deployment'/n
for a,b in mapping.items():
 if b.exists():raise SystemExit(f'Target already exists: {b}')
 if a.is_symlink():raise SystemExit(f'Symlink requires inspection: {a}')
manifest={'scope':'Root auxiliary documentation and Windows launchers only; business data and component documentation stay owned by their components.','moves':[{'old':str(a.relative_to(R)),'new':str(b.relative_to(R)),'sha256':sha(a.read_bytes()),'bytes':a.stat().st_size} for a,b in mapping.items()],'edits':[]}
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
for a,b in mapping.items():b.parent.mkdir(parents=True,exist_ok=True);a.rename(b)
for d in sorted(old_docs.rglob('*'),key=lambda p:len(p.parts),reverse=True):
 if d.is_dir():d.rmdir()
old_docs.rmdir()
for item in manifest['moves']:
 assert sha((R/item['new']).read_bytes())==item['sha256'],item

def edit(p,text):
 raw=p.read_bytes()
 if raw==text.encode():return
 backup=E/'pre-change/consolidation'/p.relative_to(R)
 if backup.exists():raise ValueError('Refuse to overwrite prior bytes: '+str(backup))
 backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(raw)
 p.write_text(text)
 manifest['edits'].append({'path':str(p.relative_to(R)),'before':sha(raw),'after':sha(p.read_bytes()),'backup':str(backup.relative_to(R))})

# Rebase actual Markdown links by resolved ownership, without changing quoted historical paths.
active=[R/x for x in ['AGENTS.md','README.md','PROJECT_STATE.md','ENVIRONMENT.md']]
for component in ['workbench','system1','system2','system3']:
 base=R/component
 active.extend(base.glob('*.md'))
 active.extend((base/'docs').rglob('*.md'))
active.extend((R/'system1/Code').glob('*.md'))
active.extend(b for a,b in mapping.items() if b.suffix=='.md')
active.extend((R/'project-support/design').glob('*.md'))
active.append(R/'project-support/product-readiness-20260912/execution.md')
pattern=re.compile(r'(!?\[[^\]\n]*\]\()([^\n]*?)(\))')
for p in sorted(set(active)):
 if not p.is_file():continue
 old=next((a for a,b in mapping.items() if b==p),p)
 def link(m):
  raw=m[2];wrapped=raw.startswith('<') and raw.endswith('>');target=raw[1:-1] if wrapped else raw
  if re.match(r'^[a-zA-Z][\w+.-]*:',target) or target.startswith('#'):return m[0]
  path,sep,anchor=target.partition('#')
  resolved=Path(os.path.normpath(str(old.parent/unquote(path))))
  relocated=mapping.get(resolved)
  if relocated is None and (resolved==old_docs or old_docs in resolved.parents):
   relocated=R/'project-support'/resolved.relative_to(old_docs)
  if relocated is None:return m[0]
  new=os.path.relpath(relocated,p.parent)
  if '%20' in path:new=new.replace(' ','%20')
  if sep:new+='#'+anchor
  if wrapped:new='<'+new+'>'
  return m[1]+new+m[3]
 edit(p,pattern.sub(link,p.read_text()))

# These executable scripts belong to the live workbench; retained historical scripts are untouched.
for p in (R/'workbench/scripts').glob('*.py'):
 s=p.read_text()
 for c in ('design','plans','reports','visuals'):s=s.replace('docs/'+c+'/','project-support/'+c+'/')
 if p.name=='build_windows_reviewer_code.py':
  s=s.replace('Double-click Open Reviewer Workbench.cmd.','Double-click workbench\\\\deployment\\\\Open Reviewer Workbench.cmd.')
  s=s.replace('"Open Reviewer Workbench.cmd" --root','"workbench\\\\deployment\\\\Open Reviewer Workbench.cmd" --root')
 edit(p,s)
p=R/'workbench/src/local_workbench/recovery.py'
s=p.read_text().replace("'Open Workbench.cmd', 'Open Reviewer Workbench.cmd'","'workbench/deployment/Open Workbench.cmd', 'workbench/deployment/Open Reviewer Workbench.cmd'")
edit(p,s)
p=R/'workbench/deployment/Open Workbench.cmd'
edit(p,p.read_text().replace('set "PROJECT_DIR=%~dp0"','for %%I in ("%~dp0..\\..") do set "PROJECT_DIR=%%~fI\\"'))
p=R/'workbench/deployment/Open Reviewer Workbench.cmd'
edit(p,p.read_text().replace('call "%~dp0Open Workbench.cmd" --reviewer --root "%~dp0reviewer-workspace" %*','for %%I in ("%~dp0..\\..") do set "PROJECT_DIR=%%~fI"\ncall "%~dp0Open Workbench.cmd" --reviewer --root "%PROJECT_DIR%\\reviewer-workspace" %*'))
# Plain current instructions, not historical reports.
for p in [R/'ENVIRONMENT.md',R/'workbench/USER_GUIDE.md',R/'workbench/docs/windows-offline-review-checklist.md']:
 s=p.read_text()
 s=re.sub(r'(?<![/\\])`Open Reviewer Workbench.cmd`','`workbench/deployment/Open Reviewer Workbench.cmd`',s)
 s=re.sub(r'(?<![/\\])`Open Workbench.cmd`','`workbench/deployment/Open Workbench.cmd`',s)
 edit(p,s) if not any(e['path']==str(p.relative_to(R)) for e in manifest['edits']) else None
# Link changes already backed up; subsequent edits share that same original backup.
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'moved_files':len(mapping),'edited_files':len(manifest['edits']),'root':sorted(p.name for p in R.iterdir())}))
