export const paneNames=['original','content','requirements','interpretation'];
export const snapWidth=80;
export function resizePair(widths,left,right,delta){
 const next=[...widths],sum=widths[left]+widths[right],wanted=widths[left]+delta;
 if(wanted<=snapWidth)return {widths:next,collapse:left};
 if(sum-wanted<=snapWidth)return {widths:next,collapse:right};
 next[left]=wanted;next[right]=sum-wanted;
 return {widths:next,collapse:null};
}
