export const workspaceModules = Object.freeze({
  sources: [['addSources','Add sources'],['system1','Source review'],['sourceRecords','Source register'],['history','Review history']],
  materials: [['system2','Material review'],['system2History','Archive']],
});
const defaults = {sources:'system1',materials:'system2'};
const storageKey = 'workbench-navigation-v2';
export function workspaceFor(view) {
  return Object.keys(workspaceModules).find(key=>workspaceModules[key].some(([id])=>id===view)) || null;
}
export function createNavigation(storage) {
  let saved;
  try { saved=JSON.parse(storage?.getItem(storageKey)||'null'); } catch {}
  const last={...defaults};
  for(const key of Object.keys(last))if(workspaceFor(saved?.last?.[key])===key)last[key]=saved.last[key];
  let workspace=Object.hasOwn(defaults,saved?.workspace)?saved.workspace:'sources';
  let view=last[workspace];
  return {
    get view(){return view;}, get workspace(){return workspace;},
    forWorkspace(key){return last[key]||defaults.sources;},
    commit(next){
      const group=workspaceFor(next);
      if(!group)return false;
      workspace=group;view=next;last[group]=next;
      try { storage?.setItem(storageKey,JSON.stringify({workspace,last})); } catch {}
      return true;
    },
  };
}

// A blocked or failed transition preserves the active module and return location.
export async function guardedNavigation({canLeave,prepare,commit}) {
  if(!canLeave())return false;
  await prepare();
  await commit();
  return true;
}
