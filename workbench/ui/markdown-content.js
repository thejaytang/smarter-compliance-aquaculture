import {numberedText} from './collaboration.js';
import {MarkdownIt,diffWordsWithSpace} from './vendor/markdown/tools.mjs';

const esc = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => structuredClone(value);
const md = new MarkdownIt({html:false,linkify:false,typographer:false,breaks:true});
// Source text never supplies executable HTML or remote images to the editor.
md.renderer.rules.image=(tokens,i)=>`<span class="md-image-label">[Image: ${esc(tokens[i].content||'original image')}]</span>`;
md.renderer.rules.link_open=(tokens,i,options,env,self)=>{tokens[i].attrSet('rel','noreferrer noopener');tokens[i].attrSet('target','_blank');return self.renderToken(tokens,i,options);};
const literal = s => String(s??'').replace(/([\\`*_[\]<>])/g,'\\$1');
const numbered = b => numberedText(b.text,b.numbering);
const cellText = s => literal(s).replace(/\|/g,'\\|').replace(/\r?\n/g,' ');

export function blockMarkdown(b){
  if(b.markdown?.version===1)return b.markdown.source;
  if(typeof b.markdown_source==='string')return b.markdown_source;
  if(b.type==='table'){
    const rows=b.table?.rows||[];
    if(!rows.length)return '';
    return (b.text?literal(b.text)+'\n\n':'')+rows.map((row,i)=>'| '+row.map(cellText).join(' | ')+' |'+(i===0?'\n| '+row.map(()=>'---').join(' | ')+' |':'')).join('\n')+(b.table?.notes?.length?'\n\n'+b.table.notes.map(literal).join('\n\n'):'');
  }
  if(b.type==='image')return `> Image${b.text?': '+literal(b.text):''}${b.image?.attribution?'\n> '+literal(b.image.attribution):''}`;
  if(b.type==='heading')return '#'.repeat(b.level||1)+' '+literal(numbered(b));
  // Keep extracted list markers, numbering, and hard line breaks in their order.
  return literal(numbered(b));
}
export function renderMarkdown(source){return md.render(String(source??''));}
const inlineText = tokens => (tokens||[]).map(t=>t.type==='softbreak'||t.type==='hardbreak'?'\n':t.children?inlineText(t.children):['text','code_inline','image'].includes(t.type)?t.content:'').join('');
export function markdownText(source){
  const tokens=md.parse(source,{}),out=[];let list=[];
  for(const t of tokens){
    if(t.type==='ordered_list_open')list.push({n:Number(t.attrGet('start')||1)});
    if(t.type==='bullet_list_open')list.push({bullet:true});
    if(t.type==='inline')out.push(inlineText(t.children));
    if(t.type==='fence'||t.type==='code_block')out.push(t.content.replace(/\n$/,''));
    if(t.type==='list_item_open')out.push('  '.repeat(Math.max(0,list.length-1))+(list.at(-1)?.bullet?'- ':`${list.length?list[list.length-1].n++:1}. `));
    if(t.type==='paragraph_close'||t.type==='heading_close'||t.type==='list_item_close'||t.type==='tr_close')out.push('\n');
    if(t.type==='td_close'||t.type==='th_close')out.push('\t');
    if(t.type==='ordered_list_close'||t.type==='bullet_list_close')list.pop();
  }
  return out.join('').replace(/\t\n/g,'\n').replace(/\n{3,}/g,'\n\n').trim();
}
function markdownTable(source){
  const tokens=md.parse(source,{}),rows=[];let row=null,inTable=false;
  for(const t of tokens){if(t.type==='table_open'){if(inTable||rows.length)return null;inTable=true;}if(t.type==='tr_open'&&inTable)row=[];if(t.type==='inline'&&row)row.push(inlineText(t.children));if(t.type==='tr_close'&&row){rows.push(row);row=null;}if(t.type==='table_close')inTable=false;}
  return rows.length&&rows.every(r=>r.length===rows[0].length)?rows:null;
}
export function updateMarkdownBlock(blocks,id,source){
  return updateMarkdownBlocks(blocks,new Map([[id,source]]));
}
export function updateMarkdownBlocks(blocks,changes){
  const next=clone(blocks);
  const ids=new Set(next.map(b=>b.id));
  if([...changes.keys()].some(id=>!ids.has(id)))throw Error('A selected passage no longer exists.');
  for(const b of next){
  if(!changes.has(b.id))continue;const source=changes.get(b.id);
  if(typeof source!=='string')throw Error('Markdown content must be text.');
  const before=blockMarkdown(b);if(source===before)continue;
  const base=b.markdown?.baseline??before;
  if(!b.markdown)b.markdown={version:1,source:before,baseline:base,original:clone(b)};
  b.markdown.source=source;b.text=markdownText(source);b.numbering='';
  const tokens=md.parse(source,{}),singleHeading=tokens.length===3&&tokens[0].type==='heading_open';
  const rows=markdownTable(source);
  if(singleHeading){b.type='heading';b.level=Number(tokens[0].tag.slice(1));}
  else if(rows){b.type='table';b.table={rows,merges:[],notes:[]};}
  else {b.type='text';delete b.level;}
  if(b.type!=='table')delete b.table;if(b.type!=='image')delete b.image;
  if(b.role==='document_information'){b.type='text';b.parent_id=null;b.dependencies=[];delete b.level;delete b.table;}
  }
  // Rebuild only invalid parent links; original associations remain in history.
  const preceding=[];
  for(const x of next){
    const parent=preceding.find(p=>p.id===x.parent_id);
    if(x.parent_id&&(!parent||(x.type==='heading'&&parent.level>=x.level)))x.parent_id=[...preceding].reverse().find(p=>x.type!=='heading'||p.level<x.level)?.id||null;
    if(x.type==='heading')preceding.push(x);
  }
  return next;
}
const mark = (text,kind) => `<${kind==='removed'?'del':'ins'} class="md-${kind}" aria-label="${kind==='removed'?'Deleted':'Added'}: ${esc(text)}">${esc(text)}</${kind==='removed'?'del':'ins'}>`;
function textDiff(oldText,newText){
  if(oldText===newText)return esc(newText);
  // Word context keeps prose readable; character refinement handles a short edit.
  const chunks=diffWordsWithSpace(oldText,newText,{timeout:60});
  if(!chunks)return mark(oldText,'removed')+mark(newText,'added');
  return chunks.map(c=>c.added?mark(c.value,'added'):c.removed?mark(c.value,'removed'):esc(c.value)).join('');
}
const shape = ts => JSON.stringify(ts.map(t=>[t.type,t.tag,t.nesting,t.attrs,t.markup,t.children?shape(t.children):null]));
export function renderChanges(before,after){
  if(before===after)return renderMarkdown(after);
  if(!after)return `<div class="md-removed md-whole" aria-label="Deleted cell">${renderMarkdown(before)}</div>`;
  if(!before)return `<div class="md-added md-whole" aria-label="Added cell">${renderMarkdown(after)}</div>`;
  const old=md.parse(before,{}),current=md.parse(after,{});
  if(shape(old)!==shape(current))return `<div class="md-removed md-whole" aria-label="Previous formatting or deleted content">${renderMarkdown(before)}</div><div class="md-added md-whole" aria-label="New formatting or added content">${renderMarkdown(after)}</div>`;
  function compare(a,b){for(let i=0;i<b.length;i++){if(b[i].children)compare(a[i].children,b[i].children);else if(['text','code_inline','code_block','fence'].includes(b[i].type)&&a[i].content!==b[i].content){const html=textDiff(a[i].content,b[i].content);b[i].type='html_inline';b[i].content=html;}}}
  compare(old,current);return md.renderer.render(current,md.options,{});
}
// Keep offsets in Unicode code points, identical to saved requirement spans.
export const semanticFields=['Subject','Modal Verb','Main Verb','Object','conditions','exceptions','subrequirement'];
export const semanticClass=f=>f==='relationship'?'semantic-7':'semantic-'+semanticFields.indexOf(f);
export function annotationLegend(){return `<details class="annotation-legend"><summary>Field colours · incomplete text may remain unmarked</summary>${semanticFields.map(f=>`<span class="semantic ${semanticClass(f)}">${f}</span>`).join('')}</details>`;}
export function renderAnnotations(source,expected,spans){
  if(!spans.length)return renderMarkdown(source);
  const tokens=md.parse(source,{}),chars=[],mapped=new Map(),list=[];
  const push=(text,token=null)=>{const entry=[];for(const c of Array.from(text)){const v={c,token,pos:null};chars.push(v);entry.push(v);}if(token)mapped.set(token,entry);};
  const inline=ts=>{for(const t of ts||[]){if(t.type==='softbreak'||t.type==='hardbreak')push('\n',t);else if(t.children)inline(t.children);else if(['text','code_inline','image'].includes(t.type))push(t.content,t);}};
  for(const t of tokens){
    if(t.type==='ordered_list_open')list.push({n:Number(t.attrGet('start')||1)});
    if(t.type==='bullet_list_open')list.push({bullet:true});
    if(t.type==='inline')inline(t.children);
    if(t.type==='fence'||t.type==='code_block')push(t.content.replace(/\n$/,''),t);
    if(t.type==='list_item_open')push('  '.repeat(Math.max(0,list.length-1))+(list.at(-1)?.bullet?'- ':`${list.length?list.at(-1).n++:1}. `));
    if(['paragraph_close','heading_close','list_item_close','tr_close'].includes(t.type))push('\n');
    if(['td_close','th_close'].includes(t.type))push('\t');
    if(['ordered_list_close','bullet_list_close'].includes(t.type))list.pop();
  }
  // Normalize the projection with the exact canonical text rules; never search for a phrase.
  let normalized=chars.filter((c,i)=>!(c.c==='\t'&&chars[i+1]?.c==='\n'));
  normalized=normalized.filter((c,i,a)=>!(c.c==='\n'&&a[i-1]?.c==='\n'&&a[i-2]?.c==='\n'));
  while(normalized.length&&/\s/u.test(normalized[0].c))normalized.shift();
  while(normalized.length&&/\s/u.test(normalized.at(-1).c))normalized.pop();
  const plain=normalized.map(v=>v.c).join('');
  if(plain!==expected||spans.some(s=>s.source_text!==expected||!Number.isInteger(s.start)||!Number.isInteger(s.end)||s.start<0||s.end>normalized.length||s.start>=s.end))return `<p class="annotation-warning">These saved ranges cannot be mapped reliably to this text. Check the source and splitting version.</p>${renderMarkdown(source)}`;
  normalized.forEach((v,i)=>v.pos=i);
  const markup=(text,active)=>{
    if(!active.length)return esc(text);
    active=[...active].sort((a,b)=>(b.end-b.start)-(a.end-a.start));
    const nested=active.every((s,i)=>!i||(s.start>=active[i-1].start&&s.end<=active[i-1].end&&(s.start>active[i-1].start||s.end<active[i-1].end)));
    const label=active.map(s=>`${s.field} · ${s.label||s.unit_id} · ${s.unit_id}`).join('; ');
    const deepest=active.at(-1),cls=nested?semanticClass(deepest.field):'semantic-overlap';
    let html=`<span class="annotation-mark semantic ${cls}" role="button" tabindex="0" data-annotations="${esc(JSON.stringify(active))}" title="${esc(label)}" aria-label="${esc((nested?'':'Overlapping references: ')+label)}">${esc(text)}</span>`;
    if(nested)for(const s of active.slice(0,-1).reverse())html=`<span class="annotation-outer ${semanticClass(s.field)}" title="${esc(s.field)}">${html}</span>`;
    return html;
  };
  let unsupported=false;
  for(const [t,cs] of mapped){
    let html='',last='',chunk='';const flush=()=>{if(chunk)html+=markup(chunk,JSON.parse(last||'[]'));chunk='';};
    for(const v of cs){const active=v.pos==null?[]:spans.filter(s=>s.start<=v.pos&&v.pos<s.end);const key=JSON.stringify(active);if(key!==last){flush();last=key;}chunk+=v.c;}flush();
    if(!cs.some(v=>v.pos!=null&&spans.some(s=>s.start<=v.pos&&v.pos<s.end)))continue;
    if(t.type==='image'){unsupported=true;continue;}
    if(t.type==='code_inline')html='<code>'+html+'</code>';
    if(t.type==='fence'||t.type==='code_block')html='<pre><code>'+html+'</code></pre>';
    t.type='html_inline';t.content=html;
  }
  if(normalized.some(v=>!v.token&&spans.some(s=>s.start<=v.pos&&v.pos<s.end)&&v.c.trim()))unsupported=true;
  const labels=[...new Map(spans.filter(s=>['conditions','exceptions','subrequirement'].includes(s.field)).map(s=>[s.field+s.unit_id,s])).values()];
  return (unsupported?'<p class="annotation-warning">Some selected characters are Markdown markers or image labels and cannot be coloured. Their saved ranges remain unchanged.</p>':'')+labels.map(s=>`<span class="annotation-relation semantic ${semanticClass(s.field)}">${esc(s.field)} · ${esc(s.label)}</span>`).join('')+md.renderer.render(tokens,md.options,{});
}
export function formatSelection(source,start,end,kind){
  const selected=source.slice(start,end),pairs={bold:['**','**'],italic:['*','*'],code:['`','`'],link:['[','](https://)']};
  let replacement,offset=0;
  if(pairs[kind]){const [l,r]=pairs[kind];replacement=l+(selected||'text')+r;offset=l.length;}
  else if(kind==='table')replacement='\n\n| Column 1 | Column 2 |\n| --- | --- |\n|  |  |\n';
  else {const a=source.lastIndexOf('\n',start-1)+1,tail=source.indexOf('\n',end),z=tail<0?source.length:tail;start=a;end=z;const prefix={heading:'## ',bullet:'- ',numbered:'1. ',quote:'> '}[kind];if(!prefix)throw Error('Unknown Markdown tool');replacement=source.slice(start,end).split('\n').map((line,i)=>(kind==='numbered'?`${i+1}. `:prefix)+line.replace(/^(?:#{1,6}\s|[-*+]\s|\d+\.\s|>\s)/,'')).join('\n');}
  return {source:source.slice(0,start)+replacement+source.slice(end),start:start+offset,end:start+replacement.length-(pairs[kind]?.[1].length||0)};
}
const btn=(action,label,extra='')=>`<button type="button" data-md-action="${action}" ${extra}>${label}</button>`;

// The editable document is a projection of source-bound blocks. Removed passages
// remain empty tombstones so saved Requirement/source links never get reassigned.
export function reconcileDocument(blocks,entries){
  const ids=new Set(blocks.map(b=>b.id)),seen=new Set(),changes=new Map();
  for(const entry of entries){
    if(!ids.has(entry.id)||seen.has(entry.id))throw Error('The document structure changed unexpectedly. Undo and retry.');
    seen.add(entry.id);changes.set(entry.id,entry.source);
  }
  for(const b of blocks)if(b.role!=='document_information'&&!seen.has(b.id))changes.set(b.id,'');
  return updateMarkdownBlocks(blocks,changes);
}
export function insertedDocumentBlock(near,kind,id=crypto.randomUUID()){
  const source=kind==='table'?'| Column 1 | Column 2 |\n| --- | --- |\n|  |  |':kind==='h1'?'# Heading':kind==='h2'?'## Heading':'';
  const b={id,type:'text',text:'',numbering:'',parent_id:near?.type==='heading'?near.id:near?.parent_id||null,source_refs:clone(near?.source_refs||[]),dependencies:[],markdown:{version:1,source:'',baseline:'',added:true}};
  return {...updateMarkdownBlock([b],id,source)[0],parent_id:b.parent_id};
}
// Serialize only the editor's supported markup. Paste never imports HTML, styles,
// event attributes, remote images or URLs into the DOM.
export function editableMarkdown(node){
  if(node.nodeType===3)return literal(node.nodeValue.replace(/\u00a0/g,' '));
  if(node.nodeType!==1&&node.nodeType!==11)return '';
  const tag=node.nodeName?.toLowerCase(),children=()=>Array.from(node.childNodes||[],editableMarkdown).join('');
  if(['script','style','iframe','img','button'].includes(tag))return '';
  if(tag==='br')return '\n';
  if(tag==='strong'||tag==='b')return '**'+children()+'**';
  if(tag==='em'||tag==='i')return '*'+children()+'*';
  if(tag==='s'||tag==='del')return '~~'+children()+'~~';
  if(tag==='code')return '`'+node.textContent.replace(/`/g,'\\`')+'`';
  if(tag==='pre')return '\n\n````\n'+node.textContent.replace(/\n$/,'')+'\n````\n\n';
  if(tag==='a'){
    const url=node.getAttribute('href')||'';
    return /^(https?:|mailto:|#)/i.test(url)?'['+children()+']('+url.replace(/\)/g,'%29')+')':children();
  }
  if(/^h[1-6]$/.test(tag))return '#'.repeat(Number(tag[1]))+' '+children().trim()+'\n\n';
  if(tag==='p'||tag==='div')return children()+'\n\n';
  if(tag==='blockquote')return children().trim().split('\n').map(s=>'> '+s).join('\n')+'\n\n';
  if(tag==='ul'||tag==='ol')return Array.from(node.children).map((li,i)=>{
    const prefix=tag==='ul'?'- ':`${Number(node.getAttribute('start')||1)+i}. `;
    return prefix+editableMarkdown(li).trim().replace(/\n/g,'\n  ');
  }).join('\n')+'\n\n';
  if(tag==='table'){
    const rows=Array.from(node.rows,row=>Array.from(row.cells,cell=>editableMarkdown(cell).trim().replace(/\n/g,' ').replace(/\|/g,'\\|')));
    if(!rows.length)return '';
    const width=Math.max(...rows.map(r=>r.length));
    return rows.map((r,i)=>'| '+Array.from({length:width},(_,c)=>r[c]||'').join(' | ')+' |'+(i===0?'\n| '+Array(width).fill('---').join(' | ')+' |':'')).join('\n')+'\n\n';
  }
  return children();
}

function textEdge(container,last=false){
  let node=container,child=last?node.lastElementChild:node.firstElementChild;
  while(child){
    node=child;
    if(!['DIV','UL','OL','LI','BLOCKQUOTE'].includes(node.tagName))break;
    child=last?node.lastElementChild:node.firstElementChild;
  }
  return node;
}
function appendRemainder(destination,fragment){
  const first=textEdge(fragment),target=textEdge(destination,true);
  if(first===fragment){target.append(...Array.from(fragment.childNodes));return;}
  // Keep remaining list items/paragraphs structurally intact after joining the
  // two edge text runs. Never append a text node directly under UL/OL.
  target.append(...Array.from(first.childNodes));let parent=first.parentNode;first.remove();
  while(parent!==fragment&&!parent.textContent.trim()){const next=parent.parentNode;parent.remove();parent=next;}
  destination.append(...Array.from(fragment.childNodes));
}

export class ContinuousDocument {
  constructor(notebook){this.n=notebook;this.m=notebook.m;this.undo=[];this.redo=[];this.rendered=new Map();}
  reset(){this.layoutObserver?.disconnect();this.undo=[];this.redo=[];this.active=null;this.insertAt=null;this.rendered.clear();}
  get locked(){return this.m.busy||this.m.opening||this.m.collaboration.readonly;}
  markup(){
    const body=this.m.draft.blocks.filter(b=>b.role!=='document_information');
    const visible=body.filter(b=>blockMarkdown(b).trim()||!b.markdown?.baseline);
    this.emptyBlock=null;
    if(!visible.length){
      if(body.length)visible.push(body[0]);
      else{this.emptyBlock=insertedDocumentBlock(this.m.draft.blocks.at(-1),'text');visible.push(this.emptyBlock);}
    }
    return `<div class="md-writing-surface"><div class="md-document md-writing-document md-cell-preview" data-writing-document contenteditable="${!this.locked}" role="textbox" aria-multiline="true" aria-label="Editable extracted content" spellcheck="true">${visible.map(b=>`<div data-writing-block="${esc(b.id)}" data-block="${esc(b.id)}" class="md-writing-block ${b.id===this.m.highlightBlock?'mw-linked-block':''}">${renderMarkdown(blockMarkdown(b))||'<p><br></p>'}</div>`).join('')}</div><div class="md-writing-controls" data-writing-controls hidden></div></div>`;
  }
  block(node){return (node?.nodeType===1?node:node?.parentElement)?.closest('[data-writing-block]');}
  range(){const s=globalThis.getSelection();return s?.rangeCount&&this.root.contains(s.anchorNode)&&this.root.contains(s.focusNode)?s.getRangeAt(0):null;}
  bookmark(){
    const range=this.range();if(!range)return null;
    const point=(node,offset)=>{const b=this.block(node);if(!b)return null;const r=document.createRange();r.selectNodeContents(b);r.setEnd(node,offset);return {id:b.dataset.writingBlock,offset:r.toString().length};};
    return {start:point(range.startContainer,range.startOffset),end:point(range.endContainer,range.endOffset)};
  }
  restore(mark){
    if(!mark?.start)return;
    const locate=p=>{const b=Array.from(this.root.children).find(n=>n.dataset.writingBlock===p?.id);if(!b)return null;const walker=document.createTreeWalker(b,4);let left=p.offset,node;while((node=walker.nextNode())){if(left<=node.length)return [node,left];left-=node.length;}return [b,b.childNodes.length];};
    const a=locate(mark.start),z=locate(mark.end)||a;if(!a)return;
    const range=document.createRange();range.setStart(...a);range.setEnd(...z);this.root.focus({preventScroll:true});const s=globalThis.getSelection();s.removeAllRanges();s.addRange(range);
  }
  remember(group=false){
    const now=Date.now(),mark=this.bookmark();
    if(!group||now-(this.lastEdit||0)>650||this.lastBlock!==mark?.start?.id){
      this.undo.push({blocks:clone(this.m.draft.blocks),mark});
      // Bounded, page-memory-only undo; never a database or browser-storage write.
      if(this.undo.length>40)this.undo.shift();
    }
    this.lastEdit=group?now:0;this.lastBlock=mark?.start?.id;this.redo=[];
  }
  travel(forward){
    if(this.locked)return;const from=forward?this.redo:this.undo,to=forward?this.undo:this.redo,item=from.pop();if(!item)return;
    to.push({blocks:clone(this.m.draft.blocks),mark:this.bookmark()});this.m.draft.blocks=item.blocks;this.lastEdit=0;this.m.changed(true);this.m.renderContent();this.restore(item.mark);
  }
  bind(){
    this.layoutObserver?.disconnect();
    this.root=this.m.q('[data-writing-document]');if(!this.root)return;
    this.host=this.root.parentElement;this.controls=this.host.querySelector('[data-writing-controls]');
    if(globalThis.ResizeObserver){this.layoutObserver=new ResizeObserver(()=>this.positionTools());this.layoutObserver.observe(this.root);}
    this.rendered=new Map(Array.from(this.root.children,b=>[b.dataset.writingBlock,b.innerHTML]));
    this.root.onpointermove=e=>{if(!this.insertAt)this.showTools(this.block(e.target),e.target.closest('td,th'));};
    this.root.onfocusin=e=>this.showTools(this.block(e.target)||this.block(globalThis.getSelection()?.anchorNode));
    this.root.onkeyup=()=>{if(!this.insertAt)this.showTools(this.block(globalThis.getSelection()?.anchorNode),(globalThis.getSelection()?.anchorNode?.parentElement)?.closest('td,th'));};
    this.host.onpointerleave=()=>{if(!this.insertAt&&!this.host.contains(document.activeElement))this.controls.hidden=true;};
    this.root.onclick=e=>{if(e.target.closest('a'))e.preventDefault();};
    this.root.onbeforeinput=e=>this.beforeInput(e);
    this.root.oninput=e=>{e.stopPropagation();if(!this.composing)this.sync();};
    this.root.oncompositionstart=()=>{this.remember();this.composing=true;};
    this.root.oncompositionend=()=>{this.composing=false;this.sync();};
    this.root.onpaste=e=>{e.preventDefault();if(!this.locked){this.remember();this.replaceText(e.clipboardData.getData('text/plain'));}};
    this.root.ondrop=e=>{e.preventDefault();this.m.message('Paste text into the document to keep its source links.','warning');};
    this.root.onkeydown=e=>{
      if(e.isComposing)return;
      if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='z'){e.preventDefault();this.travel(e.shiftKey);}
      else if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='y'){e.preventDefault();this.travel(true);}
      else if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='a'){e.preventDefault();const r=document.createRange();r.selectNodeContents(this.root);const s=globalThis.getSelection();s.removeAllRanges();s.addRange(r);}
      else if(e.key==='Escape'){this.insertAt=null;this.controls.hidden=true;}
      else if(e.key==='Tab'&&!e.shiftKey&&this.active){e.preventDefault();this.showTools(this.active,this.tableCell);this.controls.querySelector('button:not(:disabled):not(.md-to-requirement),.md-to-requirement:not(:disabled)')?.focus();}
    };
    this.controls.onmousedown=e=>{if(e.target.closest('button'))e.preventDefault();};
    this.controls.onclick=e=>{const button=e.target.closest('[data-write-action]');if(!button)return;e.preventDefault();e.stopPropagation();void this.action(button.dataset.writeAction).catch(error=>this.m.message(error.message,'error'));};
  }
  sync(){
    if(this.locked)return;
    try{
      // Structural edits are handled below. Never guess identities after an
      // unsupported browser mutation or assign text to a different source block.
      let blocks=this.m.draft.blocks;
      if(this.emptyBlock){
        const element=Array.from(this.root.children).find(b=>b.dataset.writingBlock===this.emptyBlock.id);
        if(element&&this.rendered.get(this.emptyBlock.id)!==element.innerHTML)blocks=[...blocks,this.emptyBlock];
        else return;
      }
      const byId=new Map(blocks.map(b=>[b.id,b]));
      const entries=Array.from(this.root.children,b=>{
        const old=byId.get(b.dataset.writingBlock);
        return {id:b.dataset.writingBlock,source:old&&this.rendered.get(old.id)===b.innerHTML?blockMarkdown(old):editableMarkdown(b).trim()};
      });
      const next=reconcileDocument(blocks,entries);
      if(JSON.stringify(next)!==JSON.stringify(this.m.draft.blocks)){
        this.m.draft.blocks=next;this.m.changed(true);
        this.emptyBlock=null;
        this.rendered=new Map(Array.from(this.root.children,b=>[b.dataset.writingBlock,b.innerHTML]));
      }
      if(this.active?.isConnected)this.showTools(this.active,this.tableCell);
    }catch(error){this.m.message(error.message,'error');this.m.renderContent();}
  }
  beforeInput(e){
    if(this.locked){e.preventDefault();return;}
    if(this.composing||e.isComposing)return;
    if(e.inputType==='historyUndo'||e.inputType==='historyRedo'){e.preventDefault();this.travel(e.inputType==='historyRedo');return;}
    const r=this.range();if(!r)return;
    if(e.inputType==='insertParagraph'){
      e.preventDefault();this.remember();this.split();return;
    }
    if(e.inputType==='insertLineBreak'){e.preventDefault();this.remember();this.replaceText('\n');return;}
    if(!r.collapsed&&(e.inputType.startsWith('delete')||e.inputType==='insertText')){
      e.preventDefault();this.lastEdit=0;this.remember(e.inputType==='insertText');this.replaceText(e.inputType==='insertText'?e.data||'':'');return;
    }
    if(r.collapsed&&['deleteContentBackward','deleteContentForward'].includes(e.inputType)){
      const b=this.block(r.startContainer),prefix=r.cloneRange();if(b){prefix.selectNodeContents(b);e.inputType==='deleteContentBackward'?prefix.setEnd(r.startContainer,r.startOffset):prefix.setStart(r.startContainer,r.startOffset);
        if(!prefix.toString()&&!b.querySelector('table')){
          const other=e.inputType==='deleteContentBackward'?b.previousElementSibling:b.nextElementSibling;
          e.preventDefault();if(other&&!other.querySelector('table')){this.remember();this.join(e.inputType==='deleteContentBackward'?other:b,e.inputType==='deleteContentBackward'?b:other);}return;
        }
      }
    }
    this.remember(e.inputType==='insertText'||e.inputType==='deleteContentBackward');
  }
  caret(node,offset){const r=document.createRange();r.setStart(node,offset);r.collapse(true);const s=globalThis.getSelection();s.removeAllRanges();s.addRange(r);this.root.focus({preventScroll:true});}
  replaceText(text){
    const r=this.range();if(!r)return;
    const first=this.block(r.startContainer),last=this.block(r.endContainer);
    if(first&&last&&first!==last&&!first.querySelector('table')&&!last.querySelector('table')){
      const tail=r.cloneRange();tail.selectNodeContents(last);tail.setStart(r.endContainer,r.endOffset);const suffix=tail.cloneContents();
      const head=r.cloneRange();head.selectNodeContents(first);head.setEnd(r.startContainer,r.startOffset);const prefix=head.cloneContents();
      const touched=[];let next=first.nextElementSibling;while(next){const following=next.nextElementSibling;touched.push(next.dataset.writingBlock);next.remove();if(next===last)break;next=following;}
      first.replaceChildren(prefix);const target=textEdge(first,true),insert=document.createTextNode(text);target.append(insert);
      appendRemainder(first,suffix);this.caret(insert,insert.length);
      this.mergeRefs(first.dataset.writingBlock,touched);
    }else{
      r.deleteContents();const insert=document.createTextNode(text);r.insertNode(insert);this.caret(insert,insert.length);
      // Select all may remove the block containers as well as their contents.
      if(!this.block(insert)){
        const id=first?.dataset.writingBlock||this.m.draft.blocks.find(b=>b.role!=='document_information')?.id;
        const b=document.createElement('div');b.dataset.writingBlock=id;b.dataset.block=id;b.className='md-writing-block';insert.replaceWith(b);b.append(insert);this.caret(insert,insert.length);
      }
    }
    this.sync();
  }
  mergeRefs(id,others){
    const b=this.m.draft.blocks.find(b=>b.id===id),all=this.m.draft.blocks.filter(b=>b.id===id||others.includes(b.id));
    if(!b)return;
    if(!b.markdown)b.markdown={version:1,source:blockMarkdown(b),baseline:blockMarkdown(b),original:clone(b)};
    b.source_refs=[...new Map(all.flatMap(b=>b.source_refs||[]).map(r=>[JSON.stringify(r),clone(r)])).values()];
  }
  join(first,last){
    const offset=first.textContent.length;this.mergeRefs(first.dataset.writingBlock,[last.dataset.writingBlock]);
    appendRemainder(first,last);last.remove();this.sync();
    this.restore({start:{id:first.dataset.writingBlock,offset},end:{id:first.dataset.writingBlock,offset}});
  }
  split(){
    if(this.emptyBlock){this.m.draft.blocks.push(this.emptyBlock);this.emptyBlock=null;}
    if(!this.range()?.collapsed)this.replaceText('');
    const r=this.range(),b=r&&this.block(r.startContainer);if(!b)return;
    if((r.startContainer.nodeType===1?r.startContainer:r.startContainer.parentElement).closest('td,th')){this.replaceText('\n');return;}
    const tail=r.cloneRange();tail.selectNodeContents(b);tail.setStart(r.startContainer,r.startOffset);const fragment=tail.extractContents();
    this.sync();const index=this.m.draft.blocks.findIndex(x=>x.id===b.dataset.writingBlock),near=this.m.draft.blocks[index],added=insertedDocumentBlock(near,'text');
    const wrapper=document.createElement('div');wrapper.append(fragment);
    // Enter after a heading starts ordinary body text.
    for(const h of wrapper.querySelectorAll('h1,h2,h3,h4,h5,h6')){const p=document.createElement('p');p.append(...h.childNodes);h.replaceWith(p);}
    const next={...updateMarkdownBlock([added],added.id,editableMarkdown(wrapper).trim())[0],parent_id:added.parent_id};this.m.draft.blocks.splice(index+1,0,next);
    this.m.changed(true);this.m.renderContent();this.restore({start:{id:next.id,offset:0}});
  }
  showTools(block,cell=null){
    if(!block||!this.root.contains(block)||this.locked)return;
    this.active=block;this.tableCell=cell;
    const b=this.m.draft.blocks.find(b=>b.id===block.dataset.writingBlock);
    const control=(action,label,attrs='')=>`<button type="button" data-write-action="${action}" ${attrs}>${label}</button>`;
    this.controls.hidden=false;
    const allowed=['text','heading'].includes(b?.type)&&b.text?.trim();
    this.controls.innerHTML=`${control('requirement','To requirement',`class="md-to-requirement" ${!allowed?'disabled':''} title="${this.m.dirty?'Save content before adding this passage to Requirements':allowed?'Add this passage in source order':'Choose a nonempty text passage'}"`)}${control('above','+', 'class="md-insert-edge md-insert-above" aria-label="Insert above passage"')}${control('below','+', 'class="md-insert-edge md-insert-below" aria-label="Insert below passage"')}`;
    if(cell&&block.contains(cell)){
      const row=cell.parentElement.rowIndex,col=cell.cellIndex,table=cell.closest('table');this.cellPosition={row,col};
      this.controls.innerHTML+=`<div class="md-table-edge md-table-row" role="group" aria-label="Row ${row+1}">${control('row-before','+','aria-label="Insert row above"')}${control('row-delete','−',`aria-label="Delete row ${row+1}" ${table.rows.length<=1?'disabled':''}`)}${control('row-after','+','aria-label="Insert row below"')}</div><div class="md-table-edge md-table-column" role="group" aria-label="Column ${col+1}">${control('col-before','+','aria-label="Insert column before"')}${control('col-delete','−',`aria-label="Delete column ${col+1}" ${cell.parentElement.cells.length<=1?'disabled':''}`)}${control('col-after','+','aria-label="Insert column after"')}</div>`;
    }
    this.positionTools();
  }
  positionTools(){
    const block=this.active,cell=this.tableCell;
    if(!block?.isConnected||!this.root?.contains(block)||!this.controls||this.controls.hidden)return;
    const box=block.getBoundingClientRect(),host=this.host.getBoundingClientRect();
    this.controls.style.top=(box.top-host.top)+'px';this.controls.style.height=box.height+'px';
    // Resize only repositions existing controls; it must preserve focus and open menus.
    if(cell&&block.contains(cell)){
      const cellBox=cell.getBoundingClientRect(),tableBox=cell.closest('table').getBoundingClientRect();
      const rowEdge=this.controls.querySelector('.md-table-row'),colEdge=this.controls.querySelector('.md-table-column');
      if(rowEdge){rowEdge.style.top=(cellBox.top-box.top+cellBox.height/2)+'px';rowEdge.style.right='0';}
      if(colEdge){colEdge.style.top=(tableBox.top-box.top-28)+'px';colEdge.style.left=Math.min(Math.max(0,cellBox.left-host.left),Math.max(0,host.width-80))+'px';}
    }
  }
  async action(action){
    if(this.locked||!this.active)return;
    const id=this.active.dataset.writingBlock,index=this.m.draft.blocks.findIndex(b=>b.id===id);
    if(action==='requirement'){
      if(this.m.dirty){this.m.message('Save content first, then choose To requirement. Your edits are still in this page.','warning');return;}
      return this.m.requirements.start(id);
    }
    if(action==='above'||action==='below'){
      this.insertAt={id,after:action==='below'};
      this.controls.innerHTML+=`<div class="md-insert-menu ${action==='above'?'md-menu-above':'md-menu-below'}" role="toolbar" aria-label="Insert ${action}">${[['text','Context'],['h1','H1'],['h2','H2'],['table','Table']].map(([v,label])=>`<button type="button" data-write-action="insert-${v}">${label}</button>`).join('')}<button type="button" data-write-action="cancel">Cancel</button></div>`;
      this.controls.querySelector('.md-insert-menu button')?.focus();return;
    }
    if(action==='cancel'){this.insertAt=null;this.showTools(this.active);return;}
    if(action.startsWith('insert-')){
      if(!this.insertAt)return;this.remember();const near=this.m.draft.blocks[index]||this.emptyBlock,b=insertedDocumentBlock(near,action.slice(7));
      if(!this.insertAt.after&&b.parent_id===near.id)b.parent_id=near.parent_id||null;
      this.m.draft.blocks.splice(index<0?this.m.draft.blocks.length:index+(this.insertAt.after?1:0),0,b);this.m.draft.blocks=updateMarkdownBlocks(this.m.draft.blocks,new Map());this.insertAt=null;this.m.changed(true);this.m.renderContent();this.restore({start:{id:b.id,offset:0}});return;
    }
    if(/^(row|col)-/.test(action)&&this.tableCell?.isConnected){
      this.remember();const table=this.tableCell.closest('table'),{row,col}=this.cellPosition;
      if(action.startsWith('row-')){
        if(action==='row-delete'){if(table.rows.length<=1)return;table.deleteRow(row);}
        else{const added=table.insertRow(row+(action==='row-after'?1:0));for(let i=0;i<this.tableCell.parentElement.cells.length;i++)added.insertCell().append(document.createElement('br'));}
      }else for(const tr of table.rows){
        if(action==='col-delete'){if(tr.cells.length<=1)return;tr.deleteCell(col);}
        else tr.insertCell(col+(action==='col-after'?1:0)).append(document.createElement('br'));
      }
      this.sync();this.m.renderContent();this.restore({start:{id,offset:0}});
    }
  }
}
export class MarkdownNotebook{
  constructor(owner){this.m=owner;this.editing=null;this.active=null;this.showChanges=false;this.mode="current";this.annotationData=null;this.annotationAutoShown=false;this.histories=new Map();this.selectedBlocks=new Set();this.writer=new ContinuousDocument(this);}
  reset(){this.editing=null;this.active=null;this.histories.clear();this.selectedBlocks.clear();this.selecting=false;this.lastPicked=null;this.bulkUndo=null;this.writer.reset();}
  async refreshAnnotations(completed=false){
    const key=`${this.m.state?.actor?.id}:${this.m.id}:${this.m.material?.revision}`,id=this.m.id;
    if(this.m.collaboration.readonly){this.annotationData=null;return;}
    try{const data=await this.m.api('/api/requirement-annotations?'+new URLSearchParams({material_id:id}));
      if(key!==`${this.m.state?.actor?.id}:${this.m.id}:${this.m.material?.revision}`)return;
      this.annotationData=data;
      // Source colours belong to the Requirement entry, including while collapsed.
      if(this.mode!=='current')this.m.renderContent();
    }catch(e){this.m.message('Annotations could not be loaded. '+e.message,'warning');}
  }
  annotated(b,source){
    if(this.m.collaboration.readonly||this.m.dirty||this.annotationData?.material_id!==this.m.id||this.annotationData?.material_revision!==this.m.material?.revision)return renderMarkdown(source);
    const spans=(this.annotationData?.spans||[]).filter(s=>s.block_id===b.id);
    return renderAnnotations(source,b.text,spans);
  }
  documentMarkup(){
    if(this.mode==='current'&&!this.m.collaboration.readonly&&!this.selecting)return this.writer.markup();
    const blocks=this.m.draft.blocks,levels=[];let html=(this.mode==='annotations'?annotationLegend()+(this.annotationData?.stale_sessions?.length?'<p class="annotation-warning">Some source passages changed. Review their saved splitting before restoring annotations.</p>':''):'')+'<div class="md-document" role="document" aria-label="Complete extracted Markdown">';
    for(let i=0;i<blocks.length;i++){
      const b=blocks[i];if(b.role==='document_information')continue;
      if(!this.showChanges&&!this.selecting&&!blockMarkdown(b).trim()&&b.markdown?.baseline)continue;
      if(b.type==='heading'){
        const level=b.level||1;
        while(levels.length&&levels.at(-1)>=level){html+='</section>';levels.pop();}
        html+=`<section class="md-section" data-section="${esc(b.id)}" aria-label="${esc(numbered(b))}">`;levels.push(level);
      }
      html+=this.markup(b,i)+(this.m.collaboration.merge?this.m.collaboration.blockMarkup(b):'');
    }
    return `<div class="md-bulk-tools" data-md-bulk>${this.bulkMarkup()}</div>`+html+'</section>'.repeat(levels.length)+'</div>';
  }
  markup(b,i){
    const source=blockMarkdown(b),editing=this.editing===b.id&&!this.m.collaboration.readonly,active=this.active===b.id||editing;
    const baseline=b.markdown?.baseline??source,changed=baseline!==source,deleted=!source.trim()&&!!baseline;
    const tools=active?`<div class="md-cell-tools"><span>${b.type==='heading'?'Heading':'Content'}</span>${!this.m.collaboration.readonly?btn(editing?'render':'edit',editing?'Render':'Edit'):''}${btn('original','Original')}${b.role!=='document_information'&&!deleted&&['text','heading'].includes(b.type)?btn('requirement','To requirements',this.m.dirty?'disabled title="Save content first"':''):''}${!this.m.collaboration.readonly?`<details><summary>More</summary><div>${b.role==='document_information'?'':btn('insert-before','Insert above')+btn('insert-after','Insert below')}${b.role!=='document_information'&&['text','heading'].includes(b.type)?btn('requirement-combine','Combine passages into one Requirement',this.m.dirty?'disabled':''):''}${b.type==='heading'?btn('select-before','Select all content before this section'):''}${btn('select-range','Select passages')}${btn('delete','Delete content')}${changed?btn('restore','Restore original'):''}${btn('source','Source details')}</div></details>`:''}</div>`:'';
    const formatting=editing?`<div class="md-format-tools" role="toolbar" aria-label="Markdown formatting">${[['heading','Heading'],['bold','Bold'],['italic','Italic'],['bullet','List'],['numbered','1. List'],['quote','Quote'],['table','Table'],['link','Link']].map(([k,n])=>btn('format',n,`data-md-format="${k}"`)).join('')}${btn('undo','Undo')}${btn('redo','Redo')}</div>`:'';
    const body=editing?`${formatting}<textarea class="md-cell-editor" data-md-source aria-label="Markdown block ${i+1}" spellcheck="false" rows="${Math.max(3,Math.min(18,source.split('\n').length+1))}">${esc(source)}</textarea><p class="md-edit-hint">Shift+Enter to render · changes stay in your draft</p>${b.markdown?.original?.table?.merges?.length||(!b.markdown&&b.table?.merges?.length)?'<p class="md-edit-hint">Markdown uses simple rows and columns. The original merged layout remains in cell history and the source.</p>':''}`:`<div class="md-cell-preview">${this.mode==='annotations'?this.annotated(b,source):this.showChanges?renderChanges(baseline,source):renderMarkdown(source)}${!source&&!baseline?'<p class="md-empty">Empty paragraph</p>':''}${deleted&&!this.showChanges?'<p class="md-empty">Deleted paragraph</p>':''}</div>`;
    return `<article class="md-cell ${active?'md-active':''} ${b.type==='heading'?'md-heading-block':''} ${b.id===this.m.highlightBlock?'mw-linked-block':''}" data-block="${esc(b.id)}" data-md-cell="${esc(b.id)}" style="--md-indent:${Math.min(4,Math.max(0,b.list_depth||0))}" tabindex="0" aria-label="Markdown block ${i+1}${changed?' with changes':''}">${this.selecting?`<label class="md-block-select"><input type="checkbox" data-md-select="${esc(b.id)}" ${this.selectedBlocks.has(b.id)?'checked':''}>Select passage ${i+1}</label>`:''}${tools}${body}</article>`;
  }
  bulkMarkup(){
    if(this.m.collaboration.readonly)return '';
    const tools=this.selectedBlocks.size?`<strong>${this.selectedBlocks.size} whole passages selected</strong> ${btn('bulk-edit','Edit selected')} ${btn('bulk-delete','Delete selected')} ${btn('clear-selection','Clear selection')}`:btn('select-range',this.selecting?'Stop selecting':'Select passages');
    return tools+(this.bulkUndo?btn('undo-bulk','Undo last bulk change'):'')+(this.selecting?'<small>Shift-click to select a range.</small>':'');
  }
  pick(id,checked,extend=false){
    const blocks=this.m.draft.blocks,a=blocks.findIndex(b=>b.id===this.lastPicked),b=blocks.findIndex(b=>b.id===id);
    if(b<0)return;
    const range=extend&&a>=0?blocks.slice(Math.min(a,b),Math.max(a,b)+1):[blocks[b]];
    for(const item of range)if(item.role!=='document_information')checked?this.selectedBlocks.add(item.id):this.selectedBlocks.delete(item.id);
    this.lastPicked=id;
  }
  bind(){
    this.writer.bind();
    const content=this.m.q('#mw-content');
    if(content)content.onmouseup=()=>{if(this.m.q('[data-writing-document]'))return;const selection=globalThis.getSelection?.();if(!selection||selection.isCollapsed)return;const cell=n=>(n?.nodeType===1?n:n?.parentElement)?.closest('[data-md-cell]');const a=cell(selection.anchorNode),b=cell(selection.focusNode);if(!a||!b||a===b||!content.contains(a)||!content.contains(b))return;const blocks=this.m.draft.blocks,i=blocks.findIndex(x=>x.id===a.dataset.mdCell),j=blocks.findIndex(x=>x.id===b.dataset.mdCell);this.selectedBlocks=new Set(blocks.slice(Math.min(i,j),Math.max(i,j)+1).filter(x=>x.role!=='document_information').map(x=>x.id));const bar=this.m.q('[data-md-bulk]');if(bar){bar.innerHTML=this.bulkMarkup();bar.querySelectorAll('[data-md-action]').forEach(button=>button.onclick=e=>{e.preventDefault();this.action(button.dataset.mdAction,button).catch(error=>this.m.message(error.message,'error'));});}};
    for(const checkbox of this.m.root.querySelectorAll('[data-md-select]'))checkbox.onclick=e=>{e.stopPropagation();this.pick(checkbox.dataset.mdSelect,checkbox.checked,e.shiftKey);this.m.renderContent();this.m.q(`[data-md-select="${checkbox.dataset.mdSelect}"]`)?.focus({preventScroll:true});};

    for(const mark of this.m.root.querySelectorAll('[data-annotations]')){
      const activate=e=>{e.preventDefault();e.stopPropagation();const refs=JSON.parse(mark.dataset.annotations);void this.m.requirements.navigateAnnotation(refs);};
      mark.onclick=activate;mark.onkeydown=e=>{if(e.key==='Enter'||e.key===' ')activate(e);};
    }

    for(const cell of this.m.root.querySelectorAll('[data-md-cell]')){
      cell.onclick=e=>{if(e.target.closest('button,summary,details,textarea,a,input,[data-annotations]'))return;if(!globalThis.getSelection?.()?.isCollapsed)return;if(this.active!==cell.dataset.mdCell){this.active=cell.dataset.mdCell;this.m.renderContent();}};
      cell.ondblclick=e=>{if(e.target.closest('button,summary,details,textarea,a,input,[data-annotations]'))return;this.edit(cell.dataset.mdCell);};
      cell.onkeydown=e=>{if(e.target.matches('textarea'))return;if(e.key==='Enter'&&e.target===cell){e.preventDefault();this.edit(cell.dataset.mdCell);}};
    }
    const area=this.m.q('[data-md-source]');
    if(area){
      area.oninput=()=>this.change(this.editing,area.value);area.onchange=()=>this.change(this.editing,area.value);
      area.onkeydown=e=>{if(e.isComposing)return;if((e.key==='Enter'&&e.shiftKey)||e.key==='Escape'){e.preventDefault();this.renderCell();}else if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='z'){e.preventDefault();this.travel(e.shiftKey?1:-1);}else if((e.metaKey||e.ctrlKey)&&['b','i'].includes(e.key.toLowerCase())){e.preventDefault();this.format(e.key.toLowerCase()==='b'?'bold':'italic');}};
      area.style.height='auto';area.style.height=Math.min(520,Math.max(100,area.scrollHeight+4))+'px';
    }
    for(const button of this.m.root.querySelectorAll('[data-md-action]'))button.onclick=e=>{e.preventDefault();e.stopPropagation();this.action(button.dataset.mdAction,button).catch(error=>this.m.message(error.message,'error'));};
  }
  edit(id){if(this.m.collaboration.readonly||this.m.busy||this.m.opening)return;this.editing=id;this.active=id;this.m.renderContent();const area=this.m.q('[data-md-source]');area?.focus();}
  renderCell(){const area=this.m.q('[data-md-source]');if(this.editing&&area)this.change(this.editing,area.value);this.editing=null;this.m.renderContent();this.m.q(`[data-md-cell="${this.active}"]`)?.focus();}
  change(id,value,record=true){
    if(this.m.busy||this.m.opening||this.m.collaboration.readonly)return;
    const b=this.m.draft.blocks.find(b=>b.id===id),before=blockMarkdown(b);if(before===value)return;
    if(record){let h=this.histories.get(id);if(!h||h.values[h.index]!==before)h={values:[before],index:0};h.values=h.values.slice(0,h.index+1);h.values.push(value);if(h.values.length>100)h.values.shift();h.index=h.values.length-1;this.histories.set(id,h);}
    this.bulkUndo=null;this.m.draft.blocks=updateMarkdownBlock(this.m.draft.blocks,id,value);this.m.changed(true);for(const button of this.m.root?.querySelectorAll('[data-md-action="requirement"]')||[])button.disabled=true;
  }
  travel(direction){const h=this.histories.get(this.editing);if(!h)return;const index=h.index+direction;if(index<0||index>=h.values.length)return;h.index=index;this.change(this.editing,h.values[index],false);const area=this.m.q('[data-md-source]');area.value=h.values[index];area.focus();}
  format(kind){const area=this.m.q('[data-md-source]');if(!area)return;const x=formatSelection(area.value,area.selectionStart,area.selectionEnd,kind);this.change(this.editing,x.source);area.value=x.source;area.focus();area.setSelectionRange(x.start,x.end);}
  async action(action,node){
    if(['select-range','clear-selection','select-before','bulk-edit','bulk-delete','undo-bulk'].includes(action)){
      if(this.m.collaboration.readonly||this.m.busy||this.m.opening)return;
      if(action==='undo-bulk'){if(!this.bulkUndo)return;if(this.bulkUndo.after!==JSON.stringify(this.m.draft.blocks)){this.bulkUndo=null;this.m.renderContent();return this.m.message('Content changed after that bulk edit. Restore individual passages from Changes instead.','warning');}this.m.draft.blocks=this.bulkUndo.before;this.bulkUndo=null;this.histories.clear();this.m.changed(true);this.m.renderContent();return;}
      if(action==='select-range'){this.selecting=!this.selecting;if(!this.selecting)this.selectedBlocks.clear();this.lastPicked=null;this.m.renderContent();return;}
      if(action==='clear-selection'){this.selectedBlocks.clear();this.selecting=false;this.lastPicked=null;this.m.renderContent();return;}
      if(action==='select-before'){const id=node.closest('[data-md-cell]').dataset.mdCell,index=this.m.draft.blocks.findIndex(b=>b.id===id);this.selectedBlocks=new Set(this.m.draft.blocks.slice(0,index).filter(b=>b.role!=='document_information').map(b=>b.id));this.selecting=true;this.m.renderContent();return;}
      const selected=this.m.draft.blocks.filter(b=>this.selectedBlocks.has(b.id));if(!selected.length)return;
      const bound=this.m.id,before=JSON.stringify(this.m.draft.blocks),isDelete=action==='bulk-delete';
      this.m.dialog(`<h2>${isDelete?'Delete':'Edit'} ${selected.length} selected passages</h2><p>${isDelete?'The selected contents will be cleared in this unsaved draft.':'Edit the selected passages together below. Each keeps its own source links and identity.'} Save material to commit; leaving without saving discards this change.</p><details><summary>Selected range</summary>${selected.map(b=>`<p>${esc(b.text)}</p>`).join('')}</details>${isDelete?'':`<div class="md-bulk-editors">${selected.map((b,i)=>`<label>Passage ${i+1}<textarea data-bulk-text="${esc(b.id)}" aria-label="Edit selected passage ${i+1}" rows="${Math.min(10,Math.max(3,blockMarkdown(b).split('\n').length))}">${esc(blockMarkdown(b))}</textarea></label>`).join('')}</div>`}<p data-bulk-status role="status"></p><button data-bulk-apply>${isDelete?'Delete selected contents':'Apply to draft'}</button>`,d=>{
        d.querySelector('[data-bulk-apply]').onclick=()=>{if(bound!==this.m.id||before!==JSON.stringify(this.m.draft.blocks)){d.querySelector('[data-bulk-status]').textContent='The draft changed. Close and select the passages again.';return;}
          if(this.m.busy||this.m.opening||this.m.collaboration.readonly){d.querySelector('[data-bulk-status]').textContent='Editing is unavailable while another operation is in progress.';return;}
          const changes=new Map(isDelete?selected.map(b=>[b.id,'']):Array.from(d.querySelectorAll('[data-bulk-text]'),area=>[area.dataset.bulkText,area.value]));
          const original=clone(this.m.draft.blocks),next=updateMarkdownBlocks(original,changes);
          if(JSON.stringify(next)!==before){this.m.draft.blocks=next;this.bulkUndo={before:original,after:JSON.stringify(next)};this.histories.clear();this.m.changed(true);}
          this.selecting=false;
          this.selectedBlocks.clear();this.editing=null;this.m.renderContent();d.close();
        };
      });return;
    }

    const id=node.closest('[data-md-cell]')?.dataset.mdCell||this.active,index=this.m.draft.blocks.findIndex(b=>b.id===id),b=this.m.draft.blocks[index];
    if(action==='original')return this.m.locateBlock(b);
    if(action==='requirement'&&b?.role==='document_information')return;
    if(action==='requirement')return this.m.requirements.start(id);
    if(action==='requirement-combine')return this.m.requirements.start(id,true);
    if(action==='source'){this.m.dialog(`<h2>Cell source</h2>${this.m.collaboration.blockMarkup?.(b)||''}<p>Source links and original cell contents are preserved with this material.</p><pre>${esc(JSON.stringify({source_refs:b.source_refs,original:b.markdown?.original||b},null,2))}</pre>`);return;}
    if(this.m.collaboration.readonly||this.m.busy||this.m.opening)return;
    if(action==='edit')return this.edit(id);
    if(action==='render')return this.renderCell();
    if(action==='format')return this.format(node.dataset.mdFormat);
    if(action==='undo'||action==='redo')return this.travel(action==='undo'?-1:1);
    if(action==='restore'&&b.markdown?.original){this.m.draft.blocks[index]=clone(b.markdown.original);this.histories.delete(id);this.editing=null;this.m.changed(true);this.m.renderContent();return;}
    if(action==='delete'||action==='restore'){this.change(id,action==='delete'?'':b.markdown?.baseline??blockMarkdown(b));this.editing=null;this.m.renderContent();return;}
    if(action==='insert-before'||action==='insert-after'||action==='add'){
      const at=action==='add'?this.m.draft.blocks.length:index+(action==='insert-after'?1:0),near=b||this.m.draft.blocks.at(-1),scope=this.m.material.scope?.[0];
      const refs=near?.source_refs|| (scope?[{scope_id:scope.id,...clone(scope.location||{})}]:[]);
      const cell={id:crypto.randomUUID(),type:'text',text:'',numbering:'',parent_id:near?.type==='heading'?near.id:near?.parent_id||null,source_refs:clone(refs),dependencies:[],markdown:{version:1,source:'',baseline:'',added:true}};
      if(action==='insert-before'&&cell.parent_id===near?.id)cell.parent_id=near.parent_id||null;
      this.m.draft.blocks.splice(at,0,cell);this.m.contentQuery='';this.m.blockPage=Math.floor(at/40);this.m.changed(true);this.edit(cell.id);
    }
  }
}
