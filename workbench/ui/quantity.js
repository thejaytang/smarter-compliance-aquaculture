export function quantityLabel(q) { return Array.isArray(q) ? `${q[0]} to ${q[1]}` : `Exactly ${q}`; }
export function quantityPreset(preset,count) {
  if(!Number.isInteger(count)||count<0)throw Error('Invalid item count.');
  if(preset==='all')return count;
  if(preset==='any'&&count>=1)return [1,count];
  if(preset==='one'&&count>=1)return 1;
  if(preset==='not-all'&&count>=2)return [1,count-1];
  throw Error('This shortcut needs more items in the group.');
}
export function quantityMode(quantity,count) {
  if(!Array.isArray(quantity))return quantity===count?'all':quantity===1?'one':'custom';
  return quantity[0]===1&&quantity[1]===count?'any':quantity[0]===1&&quantity[1]===count-1?'not-all':'custom';
}
export const quantityPreview=q=>Array.isArray(q)?`[${q[0]}, ${q[1]}]`:String(q);
export function quantityRange(low,high,count){
  if(!/^\d+$/.test(String(low))||!/^\d+$/.test(String(high)))throw Error('Enter whole numbers in both fields.');
  const min=Number(low),max=Number(high);
  if(!Number.isSafeInteger(min)||!Number.isSafeInteger(max)||min<0||max>count||min>max)throw Error(`Use 0–${count}, with MIN ≤ MAX.`);
  return [min,max];
}
