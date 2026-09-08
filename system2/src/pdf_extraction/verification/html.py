"""Independent lxml-based source fidelity checks for HTML v2.
Does not import or call the HTML extractor, its walkers, rules, or table builder.
"""
from collections import Counter,defaultdict
from hashlib import sha256
from urllib.parse import unquote,urlsplit
from lxml import html,etree
from ..contracts.html import HTML_PROFILES,HtmlDocument


def verify_html(raw: bytes, document: HtmlDocument) -> dict:
    errors=[]
    def check(condition,code):
        if not condition:errors.append(code)
    check(sha256(raw).hexdigest()==document.source.content_hash,'source_hash_mismatch')
    check(document.confidence is None and document.review_policy=='review_required','document_policy_mismatch')
    tree=html.document_fromstring(raw.decode(document.encoding,errors='strict'))
    matching=[p for p,s in HTML_PROFILES.items() if tree.xpath(s['identity_xpath'])]
    check(matching==[document.profile],'profile_mismatch')
    if document.profile not in HTML_PROFILES:return {'status':'failed','errors':errors+['unknown_profile']}
    roots=[]
    for selector in HTML_PROFILES[document.profile]['roots_xpath']:
        found=tree.xpath(selector)
        check(len(found)<=1 and (bool(found) or selector=='/html/head/title'),'content_root_count')
        roots.extend(found)
    paths={}; element_by_path={}
    for el in tree.iter():
        if not isinstance(el.tag,str):continue
        siblings=el.getparent()
        if siblings is None:path=f'{el.tag}:nth-of-type(1)'
        else:
            # Use libxml sibling axis, independent of BeautifulSoup's locator construction.
            index=1+len(el.xpath('preceding-sibling::'+el.tag))
            path=paths[siblings]+' > '+f'{el.tag}:nth-of-type({index})'
        paths[el]=path;element_by_path[path]=el
    source_nodes=[];source_atoms=[];source_omissions=[]
    def traverse(el,parent_path):
        if el.tag in ('script','style'):
            content=''.join(el.itertext())
            source_omissions.append((paths[el],el.tag,'non_content_'+el.tag,sha256(content.encode()).hexdigest()))
            return
        source_nodes.append((paths[el],parent_path,el))
        index=0
        if el.text is not None:
            index+=1
            if el.text:source_atoms.append((paths[el],index,el.text))
        for child in el:
            if isinstance(child,etree._Comment):
                source_omissions.append((paths[el],'#comment','comment',sha256((child.text or '').strip().encode()).hexdigest()))
            elif isinstance(child.tag,str):traverse(child,paths[el])
            if child.tail is not None:
                index+=1
                if child.tail:source_atoms.append((paths[el],index,child.tail))
    for root in roots:traverse(root,None)
    nodes={n.id:n for n in document.nodes};by_path={n.locator:n for n in document.nodes}
    check(len(nodes)==len(document.nodes)==len(by_path),'duplicate_node_identity')
    check([nodes[r].locator if r in nodes else None for r in document.root_node_ids]==[paths[r] for r in roots],'root_boundary_mismatch')
    check([n.locator for n in document.nodes]==[p for p,_,_ in source_nodes],'node_omission_or_order_mismatch')
    outline=[];roles={}
    for position,(path,parent,el) in enumerate(source_nodes):
        node=by_path.get(path)
        if node is None:continue
        check((nodes[node.parent_id].locator if node.parent_id in nodes else None)==parent,'dom_parent_mismatch:'+path)
        check(node.tag==el.tag,'source_tag_mismatch:'+path)
        check(node.id==document.source.snapshot_id+':'+sha256(path.encode()).hexdigest()[:20],'unstable_source_node_id:'+path)
        check(node.ordinal==position,'node_ordinal_mismatch:'+path)
        classes=set(el.get('class','').split())
        tag_kinds={'p':'paragraph','table':'table','tr':'table_row','td':'table_cell','th':'table_cell','ul':'list','ol':'list','li':'list_item','dl':'definition_list','dt':'definition_term','dd':'definition','a':'link','img':'image','figure':'figure','figcaption':'caption','caption':'caption','br':'line_break','hr':'thematic_break','nav':'navigation','button':'control','input':'control','select':'control','option':'control','summary':'disclosure_heading','details':'disclosure','sup':'superscript','sub':'subscript','title':'title'}
        if 'kapittel' in classes:expected_kind='section'
        elif 'paragraf' in classes:expected_kind='clause'
        elif classes & {'fotnote','popup-inner'}:expected_kind='footnote'
        elif 'footnote-link' in classes:expected_kind='footnote_reference'
        elif el.tag in ('h1','h2','h3','h4','h5','h6'):expected_kind='heading'
        else:expected_kind=tag_kinds.get(el.tag,'container' if el.tag in ('div','section','article','main','header','footer') else 'inline')
        check(node.kind==expected_kind,'structural_type_mismatch:'+path)
        if parent is None:outline=[]
        role=roles.get(parent,'content')
        if el.tag in ('nav','ds-breadcrumbs') or 'nav-block' in classes:role='navigation'
        if 'sidebar--filters' in classes or expected_kind=='control':role='control'
        if el.tag=='title' or el.get('id')=='documentMeta':role='metadata'
        roles[path]=role
        check(node.role==role,'source_role_mismatch:'+path)
        level=int(el.tag[1]) if expected_kind=='heading' else None
        if level is not None and role=='content':
            while outline and outline[-1][0]>=level:outline.pop()
        check(node.section_id==(outline[-1][1] if outline else None),'heading_context_mismatch:'+path)
        if level is not None and role=='content':outline.append((level,node.id))
        canonical_attrs={k:' '.join(v) if isinstance(v,list) else v for k,v in node.attributes.items()}
        source_attrs=dict(el.attrib)
        if 'class' in source_attrs:source_attrs['class']=' '.join(source_attrs['class'].split())
        check(canonical_attrs==source_attrs,'source_attributes_mismatch:'+path)
        check(node.confidence is None and node.review_policy=='review_required','unjustified_auto_accept:'+path)
        if el.tag in ('h1','h2','h3','h4','h5','h6'):
            check(node.kind=='heading' and node.heading_level==int(el.tag[1]),'heading_structure_mismatch:'+path)
        elif el.tag in ('td','th'):check(node.kind in ('table_cell','footnote'),'cell_type_mismatch:'+path)
    check(all(a.id==a.node_id+':text:'+str(a.text_index) for a in document.atoms),'unstable_atom_id')
    actual_atoms=[(nodes[a.node_id].locator if a.node_id in nodes else None,a.text_index,a.text) for a in document.atoms]
    check(actual_atoms==source_atoms,'text_omission_duplicate_reorder_or_mutation')
    check(len({a.id for a in document.atoms})==len(document.atoms),'duplicate_atom_identity')
    check(all(a.confidence is None and a.review_policy=='review_required' for a in document.atoms),'atom_policy_mismatch')
    actual_omissions=[(o.locator,o.tag,o.reason,o.text_sha256) for o in document.omitted]
    check(Counter(actual_omissions)==Counter(source_omissions),'unjustified_or_missing_omission')
    included={el for _,_,el in source_nodes}
    source_tables=[el for _,_,el in source_nodes if el.tag=='table']
    tables={nodes[t.node_id].locator:t for t in document.tables if t.node_id in nodes}
    check(set(tables)=={paths[t] for t in source_tables} and len(tables)==len(document.tables),'table_omission_or_duplicate')
    cell_total=0;table_issues=[]
    for source_table in source_tables:
        t=tables.get(paths[source_table])
        if t is None:continue
        rows=[r for r in source_table.iter('tr') if next(r.iterancestors('table'),None) is source_table]
        check(t.row_count==len(rows),'table_row_count_mismatch:'+paths[source_table])
        expected=[]
        for ri,row in enumerate(rows):
            expected.extend((paths[c],ri,c.tag=='th') for c in row if c.tag in ('td','th'))
        actual=[(nodes[c.node_id].locator if c.node_id in nodes else None,c.row,c.is_header) for c in t.cells]
        cell_total+=len(expected)
        check(actual==expected,'table_cell_omission_or_order_mismatch:'+paths[source_table])
        check(t.confidence is None and t.review_policy=='review_required','table_policy_mismatch:'+paths[source_table])
        expected_cells=[];expected_issues=[];occupied=set();maximum=0
        groups=[]
        for ri,row in enumerate(rows):
            if not groups or row.getparent() is not rows[ri-1].getparent():groups.append([ri,ri+1])
            else:groups[-1][1]=ri+1
        group_ends={ri:end for start,end in groups for ri in range(start,end)}
        for ri,row in enumerate(rows):
            group_end=group_ends[ri]
            column=0
            for el in row:
                if el.tag not in ('td','th'):continue
                node=by_path.get(paths[el])
                if node is None:continue
                try:
                    rs=int(el.get('rowspan','1'));cs=int(el.get('colspan','1'))
                    if rs==0:rs=group_end-ri
                    if not (1<=rs<=group_end-ri and 1<=cs<=1000):raise ValueError()
                except ValueError:
                    expected_issues.append('invalid_or_unsupported_span:'+node.id)
                    expected_cells.append((node.id,ri,None,None,None,el.tag=='th'))
                    continue
                while (ri,column) in occupied:column+=1
                slots={(rr,cc) for rr in range(ri,ri+rs) for cc in range(column,column+cs)}
                if slots & occupied:expected_issues.append('overlapping_span:'+node.id)
                occupied.update(slots)
                expected_cells.append((node.id,ri,column,rs,cs,el.tag=='th'))
                column+=cs;maximum=max(maximum,column)
        check([(c.node_id,c.row,c.column,c.rowspan,c.colspan,c.is_header) for c in t.cells]==expected_cells,
              'cell_geometry_mismatch:'+paths[source_table])
        check(all(c.confidence is None and c.review_policy=='review_required' for c in t.cells),'table_cell_policy_mismatch:'+paths[source_table])
        check(t.issues==expected_issues,'table_issue_inventory_mismatch:'+paths[source_table])
        check(t.column_count==(None if expected_issues else maximum),'table_width_mismatch:'+paths[source_table])
        table_issues.extend(expected_issues)
    source_lists=[el for _,_,el in source_nodes if el.tag in ('ul','ol') or (el.tag=='table' and 'listeItem' in el.get('class','').split())]
    listing={nodes[l.node_id].locator:l for l in document.lists if l.node_id in nodes}
    check(set(listing)=={paths[l] for l in source_lists} and len(listing)==len(document.lists),'list_omission_or_duplicate')
    for el in source_lists:
        li=listing.get(paths[el])
        if li is None:continue
        check(li.confidence is None and li.review_policy=='review_required','list_policy_mismatch:'+paths[el])
        expected=[paths[c] for c in el if c.tag=='li'] if el.tag!='table' else [paths[el]]
        check([nodes[n].locator if n in nodes else None for n in li.item_node_ids]==expected,'list_items_mismatch:'+paths[el])
        check(li.ordered==(el.tag!='ul'),'list_order_type_mismatch:'+paths[el])
        labels=[]
        if el.tag=='table':
            cells=[c for c in el.iter('td') if next(c.iterancestors('table'),None) is el]
            if cells:labels=[by_path[paths[cells[0]]].id]
        check(li.source_label_node_ids==labels,'list_label_mismatch:'+paths[el])
    # Target resolution is rebuilt from source IDs, not trusted from the artifact.
    targets_by_id=defaultdict(list)
    for path,_,el in source_nodes:
        if el.get('id') and path in by_path:targets_by_id[el.get('id')].append(by_path[path].id)
    for link in document.links:
        if link.node_id not in nodes:continue
        el=element_by_path.get(nodes[link.node_id].locator)
        if el is None:continue
        if link.target.startswith('#'):
            targets=targets_by_id.get(unquote(link.target[1:]),[])
            expected_status='resolved' if len(targets)==1 else 'ambiguous' if targets else 'missing'
            check(link.target_node_ids==targets and link.status==expected_status and link.relation=='internal','internal_link_target_mismatch')
        elif link.target=='embedded:.popup-inner':
            target_elements=el.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," popup-inner ")]')
            targets=[by_path[paths[e]].id for e in target_elements if paths[e] in by_path]
            check(link.target_node_ids==targets and link.status==('resolved' if targets else 'missing'),'footnote_target_mismatch')
        elif el.get('data-footnote-name')==link.target:
            check(link.relation=='modal_footnote' and link.status=='missing' and not link.target_node_ids,'unfounded_modal_resolution')
        elif urlsplit(link.target).scheme.lower() in ('javascript','data','vbscript'):
            check(link.relation=='blocked_scheme' and link.status=='blocked' and not link.target_node_ids,'active_link_not_blocked')
        else:
            check(link.relation=='external' and link.status=='external_not_fetched' and not link.target_node_ids,'unfounded_external_resolution')
        check(link.confidence is None and link.review_policy=='review_required','link_policy_mismatch')
    # All links must be present.

    expected_links=[]
    for path,_,el in source_nodes:
        if el.tag=='a' and el.get('href') is not None:expected_links.append((path,el.get('href')))
        if 'footnote-link' in el.get('class','').split():expected_links.append((path,'embedded:.popup-inner'))
        if el.get('data-footnote-name') is not None:expected_links.append((path,el.get('data-footnote-name')))
    check(Counter((nodes[l.node_id].locator if l.node_id in nodes else None,l.target) for l in document.links)==Counter(expected_links),'link_or_footnote_omission')
    expected_issues=['duplicate_source_id:'+sid for sid,targets in targets_by_id.items() if len(targets)>1]
    unresolved=False
    for path,_,el in source_nodes:
        if el.get('data-footnote-name') is not None:
            node=by_path.get(path)
            if node is not None:expected_issues.append('interactive_footnote_target_not_resolved:'+node.id)
            unresolved=True
        if el.tag=='a' and el.get('href','').startswith('#'):
            if len(targets_by_id.get(unquote(el.get('href')[1:]),[]))!=1:unresolved=True
        if 'footnote-link' in el.get('class','').split():
            if not el.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," popup-inner ")]'):unresolved=True
    expected_issues.extend(table_issues)
    if unresolved:expected_issues.append('unresolved_or_ambiguous_links')
    if document.profile=='asc':expected_issues.append('conditional_display_preserved_not_evaluated')
    if any(el.tag=='img' for _,_,el in source_nodes):expected_issues.append('image_content_not_transcribed')
    check(document.issues==list(dict.fromkeys(expected_issues)),'document_issue_inventory_mismatch')
    from .html_tokens import verify_raw_text
    token_report=verify_raw_text(raw,document)
    check(token_report['status']=='passed','independent_raw_token_text_mismatch')
    return {'schema_version':'html-verification/1','verifier_version':'html-source/2.1.0','status':'passed' if not errors else 'failed',
            'source_sha256':sha256(raw).hexdigest(),'canonical_model_sha256':sha256(document.model_dump_json().encode()).hexdigest(),
            'raw_token_check':token_report,
            'profile':document.profile,'node_count':len(source_nodes),'text_atom_count':len(source_atoms),
            'table_count':len(source_tables),'cell_count':cell_total,'list_count':len(source_lists),
            'errors':list(dict.fromkeys(errors)),
            'meaning':'Static DOM source fidelity and structural consistency only; human review and semantic/domain acceptance remain separate.'}
