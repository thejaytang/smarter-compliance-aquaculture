"""Body-only candidate selection, with retained exclusion evidence.

Never applies to saved human blocks. Unknown content stays for human review;
source snapshots and pre-filter parser artifacts remain unchanged.
"""
from copy import deepcopy
from collections import defaultdict
import re

VERSION='body-content/1'
TOC_TITLE=re.compile(r'^(?:table\s+of\s+contents|contents|innhold(?:sfortegnelse)?|innhald(?:sliste)?|目录|目錄)\s*[:.]?$',re.I)
TOC_ENTRY=re.compile(r'^.{2,180}?(?:\.{2,}|…+|\s{2,})\s*(?:\d+|[ivxlcdm]+)\s*$',re.I)
BODY_HEADING=re.compile(r'^(?:(?:chapter|kapittel|section|part|annex|appendix)\s+[\dIVXLC]+\b|§\s*\d+|\d+(?:\.\d+)+\s+|第[一二三四五六七八九十百\d]+[章节条])',re.I)
EXCLUDED_TOKENS={'toc','table-of-contents','tableofcontents','documenttoc','contents-menu','cover','cover-page','titlepage','title-page','documentmeta','cookie-banner','cookie-consent','breadcrumbs','breadcrumb','sidebar--filters'}

def toc_table(block):
    rows=block.get('table',{}).get('rows',[])
    entries=[row for row in rows if len(row)>=2 and any(str(c).strip() for c in row[:-1]) and re.fullmatch(r'(?:\d+|[ivxlcdm]+)',str(row[-1]).strip(),re.I)]
    return len(entries)>=2 and len(entries)>=.6*len(rows)

def select_body(blocks,kind,raw=None):
    reasons={};by_id={b['id']:b for b in blocks}
    if kind=='html' and raw is not None:
        from bs4 import BeautifulSoup
        from ..formats.html import dom_path
        soup=BeautifulSoup(raw,'lxml');nodes={dom_path(el):el for el in soup.find_all(True)}
        roots=soup.select('#documentBody')
        if len(roots)!=1:
            roots=soup.select('main')
        if len(roots)!=1:
            roots=soup.select('article')
        root=roots[0] if len(roots)==1 else None
        # Linked notes can live outside the main document subtree.
        notes=[]
        if root:
            for link in root.select('a[href^="#"]'):
                target=soup.find(id=link['href'][1:])
                if target is not None and any('footnote' in str(x).lower() for x in [target.get('role',''),target.get('class',[]),target.get('id','')]):notes.append(target)
        for block in blocks:
            node=nodes.get((block.get('source_refs') or [{}])[0].get('locator'))
            if node is None:continue
            ancestry=[node,*node.parents]
            for el in ancestry:
                attrs=getattr(el,'attrs',{}) or {}
                tokens={str(attrs.get('id','')).lower(),*[str(x).lower() for x in attrs.get('class',[])]}
                if el.name in {'nav','button','input','select'} or attrs.get('role') in {'navigation','doc-toc','doc-cover','button','search'} or tokens&EXCLUDED_TOKENS:
                    reasons[block['id']]='html_navigation_toc_or_frontmatter';break
                if el.name in {'header','footer'} and not any(getattr(p,'name',None) in {'article','main'} or (getattr(p,'attrs',{}) or {}).get('id')=='documentBody' for p in el.parents):
                    reasons[block['id']]='html_page_chrome';break
            if block['id'] not in reasons and root is not None and not any(el is root for el in ancestry) and not any(any(el is note for el in ancestry) for note in notes):
                reasons[block['id']]='outside_document_body'
    # Textual TOCs also occur in untagged HTML and native PDF. Require a named
    # TOC plus page-leader entries, never a fixed count of initial pages.
    toc_indices=[i for i,b in enumerate(blocks) if TOC_TITLE.fullmatch(b.get('text','').strip())]
    toc_pages=set()
    for start in toc_indices:
        entries=[]
        for b in blocks[start+1:]:
            text=b.get('text','').strip()
            if toc_table(b):
                entries.append(b);break
            if TOC_ENTRY.fullmatch(text) or TOC_TITLE.fullmatch(text):entries.append(b)
            elif not text:continue
            else:break
        if len(entries)>=2 or any(toc_table(b) for b in entries):
            reasons[blocks[start]['id']]='table_of_contents_heading'
            for b in entries:reasons[b['id']]='table_of_contents_entry'
            for b in [blocks[start],*entries]:
                page=(b.get('source_refs') or [{}])[0].get('page')
                if page is not None:toc_pages.add(page)
    # Some PDF engines join a short TOC into one paragraph. Only discard
    # the joined cell when every nonempty line is a TOC title or page entry.
    for b in blocks:
        lines=[x.strip() for x in b.get('text','').splitlines() if x.strip()]
        if any(TOC_TITLE.fullmatch(x) for x in lines) and sum(bool(TOC_ENTRY.fullmatch(x)) for x in lines)>=2 and all(TOC_TITLE.fullmatch(x) or TOC_ENTRY.fullmatch(x) for x in lines):
            reasons[b['id']]='joined_table_of_contents'
            page=(b.get('source_refs') or [{}])[0].get('page')
            if page is not None:toc_pages.add(page)
    if kind=='pdf':
        pages=defaultdict(list)
        for b in blocks:pages[(b.get('source_refs') or [{}])[0].get('page')].append(b)
        # Conservative continuation: most lines must have TOC leaders.
        for page,items in sorted(pages.items(),key=lambda x:x[0] or 0):
            texts=[b for b in items if b.get('text','').strip()]
            entries=[b for b in texts if TOC_ENTRY.fullmatch(b['text'].strip())]
            if page and page-1 in toc_pages and len(entries)>=3 and len(entries)>=.7*len(texts):
                for b in entries:reasons[b['id']]='table_of_contents_continuation'
                toc_pages.add(page)
        if toc_pages:
            first=min(toc_pages)
            for page,items in pages.items():
                if not page or not page<first<=8:continue
                texts=[b.get('text','').strip() for b in items if b.get('text','').strip()]
                if texts and len(texts)>=2 and len(texts)<=20 and sum(len(t.split()) for t in texts)<=120 and any(re.search(r'\b(?:edition|version|published|copyright|ISBN|20\d{2})\b|©',t,re.I) for t in texts) and not any(re.match(r'^(?:foreword|preface|introduction|scope|forord|innledning|前言|引言)\b',t,re.I) for t in texts) and all(len(t.split())<30 and not BODY_HEADING.match(t) and not re.search(r'\b(?:shall|must|skal|må)\b',t,re.I) for t in texts):
                    for b in items:reasons[b['id']]='cover_before_identified_toc'
        # Only repeated marginal strings qualify as page chrome.
        repeated=defaultdict(list)
        for b in blocks:
            ref=(b.get('source_refs') or [{}])[0];box=ref.get('bbox');size=ref.get('page_size')
            if box and size and (box[3]<size[1]*.06 or box[1]>size[1]*.94):
                repeated[re.sub(r'\d+','#',b.get('text','').strip())].append(b)
        for text,items in repeated.items():
            if text and len(text)<120 and not re.search(r'\b(?:shall|must|skal|må)\b',text,re.I) and len({(b.get('source_refs') or [{}])[0].get('page') for b in items})>=3:
                for b in items[1:] if BODY_HEADING.match(items[0].get('text','')) else items:reasons[b['id']]='repeated_page_header_or_footer'
    result=[]
    for item in blocks:
        if item['id'] in reasons:continue
        b=deepcopy(item)
        if kind=='pdf' and b['type']=='text' and len(b.get('text',''))<=160 and '\n' not in b.get('text','') and BODY_HEADING.match(b['text']) and not re.search(r'\b(?:shall|must|skal)\b',b['text'],re.I):
            b.update(type='heading',level=1 if re.match(r'^(?:chapter|kapittel|part|annex|appendix)\b',b['text'],re.I) else 2)
        seen=set()
        while b.get('parent_id') in reasons and b['parent_id'] not in seen:
            seen.add(b['parent_id']);b['parent_id']=by_id[b['parent_id']].get('parent_id')
        b['dependencies']=[x for x in b.get('dependencies',[]) if x not in reasons]
        result.append(b)
    evidence={'version':VERSION,'excluded_count':len(reasons),'retained_count':len(result),
        'excluded':[{'block':deepcopy(b),'reason':reasons[b['id']]} for b in blocks if b['id'] in reasons],
        'policy':'Recognized non-body content is excluded only from the candidate; originals and exclusion evidence are retained. Ambiguous content requires human review.'}
    return result,evidence
