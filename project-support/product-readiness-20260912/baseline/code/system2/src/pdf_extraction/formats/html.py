"""Pure HTML structure extraction. This module does not infer Requirements."""
from hashlib import sha256
import json
from bs4 import BeautifulSoup, Tag, Comment
from ..contracts.source import HtmlStructure, Snapshot, StructureNode
from .html_rules import clean, parse_metadata, parse_chapter, parse_paragraph, chapter_heading

PARSER_VERSION = 'lovdata-html/0.1.2'

class HtmlError(ValueError):
    pass

def dom_path(element: Tag) -> str:
    parts = []
    while isinstance(element, Tag) and element.name != '[document]':
        index = 1 + len(list(element.find_previous_siblings(element.name)))
        parts.append(f'{element.name}:nth-of-type({index})')
        element = element.parent
    return ' > '.join(reversed(parts))

def parse_lovdata_legacy(raw: bytes, source: Snapshot, config: dict) -> HtmlStructure:
    if sha256(raw).hexdigest() != source.content_hash:
        raise HtmlError('snapshot_hash_mismatch')
    try:
        text = raw.decode(config['encoding'], errors='strict')
    except (UnicodeError, LookupError) as exc:
        raise HtmlError('html_decode_failed') from exc
    if '\ufffd' in text or '\x00' in text:
        raise HtmlError('html_invalid_text')
    soup = BeautifulSoup(text, 'lxml')
    metas, bodies = soup.select(config['metadata']), soup.select(config['body'])
    if len(metas) != 1 or len(bodies) != 1:
        raise HtmlError('html_template_mismatch')
    meta, body = metas[0], bodies[0]
    nodes, issues = [], []
    def add(element, kind, data, parent=None):
        locator = dom_path(element)
        identity = source.snapshot_id + ':' + sha256(locator.encode()).hexdigest()[:16]
        nodes.append(StructureNode(id=identity, kind=kind, parent_id=parent, locator=locator, data=data))
        return identity
    title = meta.find('h1')
    add(meta, 'document_metadata', {'title':clean(title.get_text()) if title else '', 'metadata':parse_metadata(meta)})
    structure_nodes = {}
    represented_headings = set()
    paragraphs = 0
    for div in body.find_all('div'):
        classes = div.get('class', [])
        if 'kapittel' not in classes and 'paragraf' not in classes:
            continue
        ancestor = div.find_parent('div', class_='kapittel')
        owner = div.find_parent('div', class_=['kapittel', 'paragraf'])
        parent = structure_nodes.get(dom_path(owner)) if owner else None
        try:
            if 'kapittel' in classes:
                heading = chapter_heading(div)
                if heading is not None:
                    represented_headings.add(id(heading))
                data = parse_chapter(div, source.snapshot_id)
                structure_nodes[dom_path(div)] = add(div, 'chapter', data, parent)
            else:
                data = parse_paragraph(div, source.snapshot_id, ancestor.get('id') if ancestor else None)
                # Preserve text outside <p> as source evidence too; do not silently drop tables.
                data['visible_text'] = clean(div.get_text(' ', strip=True))
                if not data['text']:
                    issues.append('paragraph_without_p_text:' + dom_path(div))
                structure_nodes[dom_path(div)] = add(div, 'paragraph', data, parent)
                paragraphs += 1
        except (ValueError, TypeError) as exc:
            raise HtmlError('html_invalid_structure_level') from exc
    if not paragraphs or not any(n.kind == 'paragraph' and n.data['text'] for n in nodes):
        raise HtmlError('html_empty_result')
    # Explicit coverage signal for content outside handled structural elements.
    for text_node in body.find_all(string=True):
        if isinstance(text_node, Comment) or not str(text_node).strip() or text_node.parent.name in {'script','style'}:
            continue
        if text_node.find_parent('div', class_='paragraf'):
            continue
        if any(id(p) in represented_headings for p in text_node.parents):
            continue
        issues.append('unrepresented_body_text:' + dom_path(text_node.parent))
    return HtmlStructure(source=source, parser_version=PARSER_VERSION,
                         config_hash=sha256(json.dumps(config, sort_keys=True).encode()).hexdigest(),
                         encoding=config['encoding'], nodes=nodes, issues=list(dict.fromkeys(issues)))


def parse_html(raw: bytes, source: Snapshot, config: dict):
    """Versioned entry: explicit old template retains v1; auto/new profiles use v2."""
    if config.get('template') == 'lovdata-document-v1':
        return parse_lovdata_legacy(raw, source, config)
    from .html_document import parse_document
    return parse_document(raw, source, config)
