"""Pure template rules adapted from Parser v1.py.txt; no IO or shared datasets.
Ownership fixes are recorded in docs/reports/07-nonpdf-module-regression.md.
"""
from copy import deepcopy


def clean(text):
    return ' '.join((text or '').replace('\xa0', ' ').split())


def parse_metadata(meta):
    metadata = {}
    for row in meta.select('table.meta tr'):
        th, td = row.find('th'), row.find('td')
        if th and td:
            metadata[clean(th.get_text())] = clean(td.get_text())
    return metadata


def extract_references(element):
    refs = []
    kinds = {'lov':'law', 'forskrift':'regulation', 'eu':'eu', 'external':'external'}
    for anchor in element.select('a.reference'):
        ref_id = anchor.get('data-id')
        if ref_id:
            refs.append({'reference_id':ref_id,
                         'reference_type':kinds.get(ref_id.split('/')[0], 'other'),
                         'text':clean(anchor.get_text())})
    return refs


def extract_list_items(element):
    items = []
    for table in element.select('table.listeItem'):
        cells = [cell for cell in table.find_all('td') if cell.find_parent('table') is table]
        if len(cells) < 2:
            continue
        level = int(table.get('data-level', 1))
        if level < 1:
            raise ValueError('invalid_list_level')
        content = deepcopy(cells[1])
        for nested in content.select('table.listeItem'):
            nested.decompose()
        items.append({'level':level, 'parent_level':level-1 if level>1 else None,
                      'label':clean(cells[0].get_text()),
                      'text':clean(content.get_text())})
    return items


def extract_footnotes(element):
    return [{'text':text} for note in element.select('td.fotnote')
            if (text := clean(note.get_text(' ', strip=True)))]


def chapter_heading(div):
    return next((h for h in div.find_all(['h1','h2','h3','h4'])
                 if h.find_parent('div', class_='kapittel') is div
                 and h.find_parent('div', class_='paragraf') is None), None)


def parse_chapter(div, law_id):
    heading = chapter_heading(div)
    level = int(div.get('data-level', 1))
    if level < 1:
        raise ValueError('invalid_chapter_level')
    return {'law_id':law_id, 'chapter_id':div.get('id'), 'level':level,
            'title':clean(heading.get_text()) if heading else ''}


def parse_paragraph(div, law_id, chapter_id):
    # Descendant clauses own their text/references/lists/footnotes independently.
    own = deepcopy(div)
    for child in own.select('div.paragraf'):
        child.decompose()
    value, title = own.select_one('.paragrafValue'), own.select_one('.paragrafTittel')
    text = [clean(p.get_text(' ', strip=True)) for p in own.find_all('p')
            if 'share-paragraf-title' not in p.get('class', [])]
    return {'law_id':law_id, 'chapter_id':chapter_id, 'paragraph_id':div.get('id'),
            'paragraph_number':clean(value.get_text()) if value else '',
            'title':clean(title.get_text()) if title else '',
            'text':'\n'.join(t for t in text if t),
            'list_items':extract_list_items(own), 'references':extract_references(own),
            'footnotes':extract_footnotes(own)}
