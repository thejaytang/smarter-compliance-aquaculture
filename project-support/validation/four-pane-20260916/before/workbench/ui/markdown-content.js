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
  const next=clone(blocks),b=next.find(x=>x.id===id);if(!b)throw Error('Markdown cell no longer exists.');
  const before=blockMarkdown(b);if(source===before)return next;
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
export function formatSelection(source,start,end,kind){
  const selected=source.slice(start,end),pairs={bold:['**','**'],italic:['*','*'],code:['`','`'],link:['[','](https://)']};
  let replacement,offset=0;
  if(pairs[kind]){const [l,r]=pairs[kind];replacement=l+(selected||'text')+r;offset=l.length;}
  else if(kind==='table')replacement='\n\n| Column 1 | Column 2 |\n| --- | --- |\n|  |  |\n';
  else {const a=source.lastIndexOf('\n',start-1)+1,tail=source.indexOf('\n',end),z=tail<0?source.length:tail;start=a;end=z;const prefix={heading:'## ',bullet:'- ',numbered:'1. ',quote:'> '}[kind];if(!prefix)throw Error('Unknown Markdown tool');replacement=source.slice(start,end).split('\n').map((line,i)=>(kind==='numbered'?`${i+1}. `:prefix)+line.replace(/^(?:#{1,6}\s|[-*+]\s|\d+\.\s|>\s)/,'')).join('\n');}
  return {source:source.slice(0,start)+replacement+source.slice(end),start:start+offset,end:start+replacement.length-(pairs[kind]?.[1].length||0)};
}
const btn=(action,label,extra='')=>`<button type="button" data-md-action="${action}" ${extra}>${label}</button>`;
export class MarkdownNotebook{
  constructor(owner){this.m=owner;this.editing=null;this.active=null;this.showChanges=true;this.histories=new Map();}
  reset(){this.editing=null;this.active=null;this.histories.clear();}
  documentMarkup(){
    const blocks=this.m.draft.blocks,levels=[];let html='<div class="md-document" role="document" aria-label="Complete extracted Markdown">';
    for(let i=0;i<blocks.length;i++){
      const b=blocks[i];if(b.role==='document_information')continue;
      if(b.type==='heading'){
        const level=b.level||1;
        while(levels.length&&levels.at(-1)>=level){html+='</section>';levels.pop();}
        html+=`<section class="md-section" data-section="${esc(b.id)}" aria-label="${esc(numbered(b))}">`;levels.push(level);
      }
      html+=this.markup(b,i)+(this.m.collaboration.merge?this.m.collaboration.blockMarkup(b):'');
    }
    return html+'</section>'.repeat(levels.length)+'</div>';
  }
  markup(b,i){
    const source=blockMarkdown(b),editing=this.editing===b.id&&!this.m.collaboration.readonly,active=this.active===b.id||editing;
    const baseline=b.markdown?.baseline??source,changed=baseline!==source,deleted=!source.trim()&&!!baseline;
    const tools=active?`<div class="md-cell-tools"><span>${b.type==='heading'?'Heading':'Content'}</span>${!this.m.collaboration.readonly?btn(editing?'render':'edit',editing?'Render':'Edit'):''}${btn('original','Original')}${b.role!=='document_information'&&!deleted&&['text','heading'].includes(b.type)?btn('requirement','To requirements',this.m.dirty?'disabled title="Save content first"':''):''}${!this.m.collaboration.readonly?`<details><summary>More</summary><div>${b.role==='document_information'?'':btn('insert-before','Insert above')+btn('insert-after','Insert below')}${btn('delete','Delete content')}${changed?btn('restore','Restore original'):''}${btn('source','Source details')}</div></details>`:''}</div>`:'';
    const formatting=editing?`<div class="md-format-tools" role="toolbar" aria-label="Markdown formatting">${[['heading','Heading'],['bold','Bold'],['italic','Italic'],['bullet','List'],['numbered','1. List'],['quote','Quote'],['table','Table'],['link','Link']].map(([k,n])=>btn('format',n,`data-md-format="${k}"`)).join('')}${btn('undo','Undo')}${btn('redo','Redo')}</div>`:'';
    const body=editing?`${formatting}<textarea class="md-cell-editor" data-md-source aria-label="Markdown block ${i+1}" spellcheck="false" rows="${Math.max(3,Math.min(18,source.split('\n').length+1))}">${esc(source)}</textarea><p class="md-edit-hint">Shift+Enter to render · changes stay in your draft</p>${b.markdown?.original?.table?.merges?.length||(!b.markdown&&b.table?.merges?.length)?'<p class="md-edit-hint">Markdown uses simple rows and columns. The original merged layout remains in cell history and the source.</p>':''}`:`<div class="md-cell-preview">${this.showChanges?renderChanges(baseline,source):renderMarkdown(source)}${!source&&!baseline?'<p class="md-empty">Empty paragraph</p>':''}${deleted&&!this.showChanges?'<p class="md-empty">Deleted paragraph</p>':''}</div>`;
    return `<article class="md-cell ${active?'md-active':''} ${b.type==='heading'?'md-heading-block':''} ${b.id===this.m.highlightBlock?'mw-linked-block':''}" data-block="${esc(b.id)}" data-md-cell="${esc(b.id)}" style="--md-indent:${Math.min(4,Math.max(0,b.list_depth||0))}" tabindex="0" aria-label="Markdown block ${i+1}${changed?' with changes':''}">${tools}${body}</article>`;
  }
  bind(){
    for(const cell of this.m.root.querySelectorAll('[data-md-cell]')){
      cell.onclick=e=>{if(e.target.closest('button,summary,details,textarea,a,input'))return;if(!globalThis.getSelection?.()?.isCollapsed)return;if(this.active!==cell.dataset.mdCell){this.active=cell.dataset.mdCell;this.m.renderContent();}};
      cell.ondblclick=e=>{if(e.target.closest('button,summary,details,textarea,a,input'))return;this.edit(cell.dataset.mdCell);};
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
    this.m.draft.blocks=updateMarkdownBlock(this.m.draft.blocks,id,value);this.m.changed(true);for(const button of this.m.root?.querySelectorAll('[data-md-action="requirement"]')||[])button.disabled=true;
  }
  travel(direction){const h=this.histories.get(this.editing);if(!h)return;const index=h.index+direction;if(index<0||index>=h.values.length)return;h.index=index;this.change(this.editing,h.values[index],false);const area=this.m.q('[data-md-source]');area.value=h.values[index];area.focus();}
  format(kind){const area=this.m.q('[data-md-source]');if(!area)return;const x=formatSelection(area.value,area.selectionStart,area.selectionEnd,kind);this.change(this.editing,x.source);area.value=x.source;area.focus();area.setSelectionRange(x.start,x.end);}
  async action(action,node){
    const id=node.closest('[data-md-cell]')?.dataset.mdCell||this.active,index=this.m.draft.blocks.findIndex(b=>b.id===id),b=this.m.draft.blocks[index];
    if(action==='original')return this.m.locateBlock(b);
    if(action==='requirement'&&b?.role==='document_information')return;
    if(action==='requirement')return this.m.requirements.start(id);
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
