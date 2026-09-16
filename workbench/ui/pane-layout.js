export const paneNames=['original','content','requirements','interpretation'];
export const paneMinimums=[260,340,320,320];
export const collapsedPaneWidth=44;
export const paneSeparatorWidth=7;
export function minimumWorkspaceWidth(collapsed=[]){
 const visible=paneNames.filter(name=>!collapsed.includes(name)).length;
 return paneNames.reduce((sum,name,i)=>sum+(collapsed.includes(name)?collapsedPaneWidth:paneMinimums[i]),0)+Math.max(0,visible-1)*paneSeparatorWidth;
}
export const snapWidth=80;
export function resizePair(widths,left,right,delta){
 const next=[...widths],sum=widths[left]+widths[right],wanted=widths[left]+delta;
 if(wanted<=snapWidth)return {widths:next,collapse:left};
 if(sum-wanted<=snapWidth)return {widths:next,collapse:right};
 next[left]=wanted;next[right]=sum-wanted;
 return {widths:next,collapse:null};
}
