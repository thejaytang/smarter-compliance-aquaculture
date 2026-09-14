"""Static HTML parser: typed DOM graph, exact text atoms, geometry, and link relations."""
from collections import defaultdict
from hashlib import sha256
import json
from urllib.parse import unquote,urlsplit
from bs4 import BeautifulSoup, Tag, NavigableString, Comment
from ..contracts.html import HtmlDocument,HtmlNode,HtmlAtom,HtmlOmission,HtmlList,HtmlLink
from .html_profiles import select_profile
from .html_tables import build_table

PARSER_VERSION='html-dom/2.1.0'


def _kind(tag):
    classes=set(tag.get('class',[]))
    if 'kapittel' in classes: return 'section'
    if 'paragraf' in classes: return 'clause'
    if 'fotnote' in classes or 'popup-inner' in classes: return 'footnote'
    if 'footnote-link' in classes: return 'footnote_reference'
    if tag.name in ['h1','h2','h3','h4','h5','h6']: return 'heading'
    return {'p':'paragraph','table':'table','tr':'table_row','td':'table_cell','th':'table_cell',
            'ul':'list','ol':'list','li':'list_item','dl':'definition_list','dt':'definition_term',
            'dd':'definition','a':'link','img':'image','figure':'figure','figcaption':'caption',
            'caption':'caption','br':'line_break','hr':'thematic_break','nav':'navigation',
            'button':'control','input':'control','select':'control','option':'control',
            'summary':'disclosure_heading','details':'disclosure','sup':'superscript',
            'sub':'subscript','title':'title'}.get(tag.name,'container' if tag.name in ['div','section','article','main','header','footer'] else 'inline')


def parse_document(raw,source,config):
    if sha256(raw).hexdigest()!=source.content_hash: raise ValueError('snapshot_hash_mismatch')
    encoding=config.get('encoding','utf-8-sig')
    try: text=raw.decode(encoding,errors='strict')
    except (LookupError,UnicodeError) as exc: raise ValueError('html_decode_failed') from exc
    if '\ufffd' in text or '\x00' in text: raise ValueError('html_invalid_text')
    if len(raw)>64*1024*1024: raise ValueError('html_size_limit')
    soup=BeautifulSoup(text,'lxml',preserve_whitespace_tags={'html'})
    profile,roots=select_profile(soup,config.get('template','auto'))
    # Build locators once on the original DOM. Never mutate evidence to simplify parsing.
    paths={}; counts=defaultdict(lambda:defaultdict(int))
    for el in soup.find_all(True):
        counts[id(el.parent)][el.name]+=1
        component=f'{el.name}:nth-of-type({counts[id(el.parent)][el.name]})'
        prefix=paths.get(id(el.parent),'')
        paths[id(el)]=(prefix+' > ' if prefix else '')+component
    ids={}; nodes=[]; atoms=[]; omitted=[]; elements=[]; issues=[]; headings=[]
    def visit(el,parent_id,role):
        locator=paths[id(el)]
        if el.name in ('script','style'):
            content=''.join(str(x) for x in el.descendants if isinstance(x,NavigableString))
            omitted.append(HtmlOmission(locator=locator,tag=el.name,reason='non_content_'+el.name,text_sha256=sha256(content.encode()).hexdigest()))
            return
        nid=source.snapshot_id+':'+sha256(locator.encode()).hexdigest()[:20]
        ids[id(el)]=nid;elements.append(el)
        kind=_kind(el); classes=set(el.get('class',[]))
        if el.name=='nav' or el.name=='ds-breadcrumbs' or 'nav-block' in classes: role='navigation'
        if 'sidebar--filters' in classes or kind=='control': role='control'
        if el.name=='title' or el.get('id')=='documentMeta':role='metadata'
        level=int(el.name[1]) if kind=='heading' else None
        if level is not None and role=='content':
            while headings and headings[-1][0]>=level:headings.pop()
        section=headings[-1][1] if headings else None
        attributes={str(k):v if isinstance(v,list) else str(v) for k,v in el.attrs.items()}
        nodes.append(HtmlNode(id=nid,locator=locator,parent_id=parent_id,ordinal=len(nodes),tag=el.name,
                              kind=kind,attributes=attributes,role=role,heading_level=level,section_id=section))
        if level is not None and role=='content':headings.append((level,nid))
        index=0
        for child in el.children:
            if isinstance(child,Tag):visit(child,nid,role)
            elif isinstance(child,Comment):
                omitted.append(HtmlOmission(locator=locator,tag='#comment',reason='comment',text_sha256=sha256(str(child).strip().encode()).hexdigest()))
            elif isinstance(child,NavigableString):
                index+=1
                if str(child):
                    atoms.append(HtmlAtom(id=f'{nid}:text:{index}',node_id=nid,text_index=index,text=str(child)))
    for root in roots:
        headings.clear();visit(root,None,'content')
    if len(nodes)>200000:raise ValueError('html_node_limit')
    tables=[build_table(el,ids) for el in elements if el.name=='table']
    lists=[]
    for el in elements:
        if el.name in ('ul','ol'):
            lists.append(HtmlList(node_id=ids[id(el)],ordered=el.name=='ol',item_node_ids=[ids[id(c)] for c in el.find_all('li',recursive=False)]))
        elif el.name=='table' and 'listeItem' in el.get('class',[]):
            cells=[c for c in el.find_all('td') if c.find_parent('table') is el]
            lists.append(HtmlList(node_id=ids[id(el)],ordered=True,item_node_ids=[ids[id(el)]],source_label_node_ids=[ids[id(cells[0])]] if cells else []))
    by_source_id=defaultdict(list)
    for node in nodes:
        if node.attributes.get('id'):by_source_id[node.attributes['id']].append(node.id)
    for raw_id,targets in by_source_id.items():
        if len(targets)>1:issues.append('duplicate_source_id:'+raw_id)
    links=[]
    for el in elements:
        nid=ids[id(el)]
        if el.name=='a' and el.has_attr('href'):
            target=el['href'];parsed=urlsplit(target)
            if target.startswith('#'):
                targets=by_source_id.get(unquote(target[1:]),[])
                links.append(HtmlLink(node_id=nid,target=target,target_node_ids=targets,relation='internal',status='resolved' if len(targets)==1 else 'ambiguous' if targets else 'missing'))
            elif parsed.scheme.lower() in ('javascript','data','vbscript'):
                links.append(HtmlLink(node_id=nid,target=target,target_node_ids=[],relation='blocked_scheme',status='blocked'))
            else:
                links.append(HtmlLink(node_id=nid,target=target,target_node_ids=[],relation='external',status='external_not_fetched'))
        if 'footnote-link' in el.get('class',[]):
            targets=[ids[id(x)] for x in el.select('.popup-inner') if id(x) in ids]
            links.append(HtmlLink(node_id=nid,target='embedded:.popup-inner',target_node_ids=targets,relation='embedded_footnote',status='resolved' if targets else 'missing'))
        if el.has_attr('data-footnote-name'):
            links.append(HtmlLink(node_id=nid,target=el['data-footnote-name'],target_node_ids=[],relation='modal_footnote',status='missing'))
            issues.append('interactive_footnote_target_not_resolved:'+nid)
    for table in tables:issues.extend(table.issues)
    if any(l.status in ('missing','ambiguous') for l in links):issues.append('unresolved_or_ambiguous_links')
    if profile=='asc':issues.append('conditional_display_preserved_not_evaluated')
    if any(n.kind=='image' for n in nodes):issues.append('image_content_not_transcribed')
    return HtmlDocument(source=source,parser_version=PARSER_VERSION,
        config_hash=sha256(json.dumps(config,sort_keys=True).encode()).hexdigest(),profile=profile,encoding=encoding,
        root_node_ids=[ids[id(r)] for r in roots],nodes=nodes,atoms=atoms,tables=tables,lists=lists,links=links,
        omitted=omitted,issues=list(dict.fromkeys(issues)))
