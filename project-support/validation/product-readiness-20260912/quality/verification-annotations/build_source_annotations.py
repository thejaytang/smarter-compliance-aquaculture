"""Reproduce source-only engineering annotations, never read parser predictions.

Grouping and labels were assigned after visual inspection of the four rendered
pages. Poppler/PDFium assist transcription and geometry only.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import pypdfium2 as pdfium

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
MANIFEST = json.loads((OUT.parent / 'manifest.json').read_text())


def line_inventory(sample, page):
    stem = f'{sample["id"]}-p{page:03}'
    if sample['id'].startswith('pa057'):
        tree = ET.parse(OUT / (stem + '.xhtml'))
        return [dict(text=' '.join(w.text or '' for w in line.findall('{*}word')),
                     bbox=[float(line.attrib[k]) for k in ('xMin', 'yMin', 'xMax', 'yMax')])
                for line in tree.findall('.//{*}line')]
    lines = (OUT / (stem + '.pdfium.txt')).read_text().splitlines()
    result = []
    with pdfium.PdfDocument(ROOT / sample['path']) as doc:
        pg = doc[page - 1]
        height = pg.get_height()
        text = pg.get_textpage()
        for line in lines:
            search = text.search(line.strip())
            found = search.get_next()
            search.close()
            assert found, line
            boxes = [text.get_charbox(i) for i in range(found[0], found[0] + found[1])]
            result.append(dict(text=line.strip(), bbox=[min(b[0] for b in boxes), height-max(b[3] for b in boxes),
                                                        max(b[2] for b in boxes), height-min(b[1] for b in boxes)]))
        text.close()
        pg.close()
    return result


def build(sample, specs):
    src = ROOT / sample['path']
    assert hashlib.sha256(src.read_bytes()).hexdigest() == sample['sha256']
    units, relations, page_records = [], [], []
    for page, definitions, visuals in specs:
        lines = line_inventory(sample, page)
        assigned = []
        current_heading = None
        page_ids = []
        for name, first, last, kind, label, reason in definitions:
            selected = lines[first:last+1]
            assigned.extend(range(first, last+1))
            identity = f'{sample["id"]}-p{page:03}-{name}'
            text = ' '.join(line['text'] for line in selected)
            bbox = [min(line['bbox'][0] for line in selected), min(line['bbox'][1] for line in selected),
                    max(line['bbox'][2] for line in selected), max(line['bbox'][3] for line in selected)]
            unit = dict(id=identity, page_number=page, kind=kind, text=text,
                        bbox=[round(v, 3) for v in bbox], source_assistance_lines=list(range(first, last+1)),
                        visually_checked=True, transcription_uncertainty=[],
                        requirement_judgment=dict(classification=label, reason=reason,
                                                  authority='engineering_only_not_business_review'))
            if kind == 'heading':
                unit['heading_level'] = 2 if re.match(r'^\d+\.\d+', text) else 1
                current_heading = identity
            elif current_heading and kind not in ('footer', 'margin_metadata', 'table_cell'):
                unit['parent_heading_id'] = current_heading
                relations.append(dict(kind='under_heading', parent=current_heading, child=identity))
            units.append(unit)
            page_ids.append(identity)
        assert sorted(assigned) == list(range(len(lines))), (sample['id'], page, 'missing or duplicated native assistance lines', assigned)
        for name, text, bbox, kind in visuals:
            identity = f'{sample["id"]}-p{page:03}-{name}'
            units.append(dict(id=identity, page_number=page, kind=kind, text=text, bbox=bbox,
                              bbox_precision='manual enclosing region, approximately +/- 3 PDF points',
                              visual_evidence=f'{sample["id"]}-p{page:03}.png', visually_checked=True,
                              source_assistance_lines=[], transcription_uncertainty=[],
                              requirement_judgment=dict(classification='context', reason='Publisher identity / document furniture; retained visually, not an aquaculture Requirement.', authority='engineering_only_not_business_review')))
            page_ids.append(identity)
        # Reading order comes from visible position, not PDF extraction order.
        ordered = sorted([u for u in units if u['page_number']==page], key=lambda u:(u['bbox'][1],u['bbox'][0]))
        for n,u in enumerate(ordered):u['reading_order_on_page']=n
        content_order=[u['id'] for u in ordered if u['kind'] not in ('footer','margin_metadata','publisher_mark')]
        for first,second in zip(content_order,content_order[1:]):relations.append(dict(kind='precedes', first=first, second=second))
        page_records.append(dict(page_number=page, page_index=page-1, image=f'{sample["id"]}-p{page:03}.png',
                                 page_size_pdf_points=[595.3200073242188,841.9199829101562],
                                 assisted_line_count=len(lines), assigned_line_count=len(assigned),
                                 visual_only_unit_count=len(visuals), content_unit_count=len(page_ids),
                                 complete_visible_content_inventory=True,
                                 check='Whole rendered page reviewed, including margins, publisher marks, table cells, notes and footer. Blank space and nontext ornamental strokes are not text units.'))
    for u in units:
        critical=[]
        for m in re.finditer(r'\b\d+(?:[.:/_-]\d+)*\b',u['text']):
            critical.append(dict(category='number_or_identifier',text=m.group(),start=m.start(),end=m.end()))
        u['critical_spans']=critical
    return dict(schema_version='source-only-engineering-annotation/1', sample_id=sample['id'],
                source=dict(path=sample['path'],sha256=sample['sha256']),
                scope=dict(page_numbers=sample['pdf_page_numbers'],coordinate_system='PDF points, top-left origin; x0,y0,x1,y1',
                           unit_definition='One visible heading, paragraph, list item, table cell, note, footer field, margin field or publisher mark. Line wrapping within a paragraph does not create additional units.'),
                provenance=dict(annotator='Codex reader_navigation source-only engineering review',business_expert_review=False,
                                parser_predictions_read=False,material_parser_read=False,
                                historical_exposure=sample['exposure'],
                                independence='Withheld from modifications and predictions in this round until this source annotation was frozen; historically exposed and NOT an all-history independent holdout.',
                                rendered_images='Poppler pdftoppm 150 DPI, four pages visually inspected in tool results',
                                text_assistance='PA057: Poppler bbox lines; CS010: direct PDFium text/character boxes after Poppler bbox SIGABRT and unavailable pypdf AES dependency.',
                                independence_limit='PDFium source assistance can share an underlying text engine with the product; visual annotation is separate from its predictions, not a fully independent text engine.'),
                pages=page_records, units=units, structural_relations=relations,
                quality_status='Engineering reference inventory only; no product metric has been computed.',
                uncertainties=[], exclusions=[dict(kind='blank_space_and_nontext_ornament',reason='No visible textual content; publisher logo wordmark retained as its own unit.')])


C='context'; R='requirement'; U='undetermined'
CTX='Source context/definition or document furniture, not a standalone aquaculture obligation; retained for review.'
REQ='Visible complete source clause states an obligation, certification scope restriction or required applicability; engineering label only.'
UNC='Declarative wording can express a normative certificate field; exact business classification needs review.'

pa5=[('title',0,0,'heading',C,CTX),('purpose',1,7,'paragraph',C,CTX),('commission',8,9,'paragraph',C,CTX),
     ('revision-caption',10,10,'caption',C,CTX)]
pa5 += [(f'revision-r{(i-11)//2}-c{(i-11)%2}',i,i,'table_cell',C,CTX) for i in range(11,19)]
pa5 += [('footer-description',19,19,'footer',C,CTX),('page-number',20,20,'footer',C,CTX)]
pa6=[('title',0,0,'heading',C,CTX)]
for name,start,end in [('avdeling',1,4),('brukerhandbok',5,7),('brukstid',8,10),('fellesfunksjon',11,14),('fisk',15,15),('kar',16,16),('komponent',17,18),('landbasert',19,20),('leveringssystem',21,22),('produksjonsenhet',23,24),('note',25,29),('produktsertifikat',30,32),('prosjektering',33,33),('referanseniva',34,35)]:
    pa6.append((name,start,end,'note' if name=='note' else 'definition',C,CTX))
pa6 += [('footer-description',36,36,'footer',C,CTX),('page-number',37,37,'footer',C,CTX)]
pa_visual=[('publisher','FISKERIDIREKTORATET',[70,801,130,809],'publisher_mark')]

cs3=[('intro-heading',4,4,'heading',C,CTX),('edition-scope',5,7,'paragraph',R,REQ),('combined-rules',8,10,'paragraph',R,REQ),
     ('shall-definition',11,12,'paragraph',C,'The clause defines the word shall; it does not itself impose an operational requirement.'),
     ('scope-heading',13,13,'heading',C,CTX),('product-heading',14,14,'heading',C,CTX),
     ('product-list-intro',15,16,'paragraph',R,'Applicability rule together with the four following product-category items; review as one complete scope clause.'),
     ('finfish',17,17,'list_item',C,'Member of preceding complete applicability clause, not a standalone obligation.'),
     ('crustaceans',18,18,'list_item',C,'Member of preceding complete applicability clause, not a standalone obligation.'),
     ('molluscs',19,19,'list_item',C,'Member of preceding complete applicability clause, not a standalone obligation.'),
     ('seaweed',20,20,'list_item',C,'Member of preceding complete applicability clause, not a standalone obligation.'),
     ('seedlings',21,25,'paragraph',R,REQ),('wild-exclusion',26,26,'paragraph',R,REQ),('postharvest',27,29,'paragraph',R,REQ),
     ('scientific-name',30,31,'paragraph',U,UNC),('registration-heading',32,32,'heading',C,CTX),('registration',33,35,'paragraph',R,REQ),
     ('audit-heading',36,36,'heading',C,CTX),('timing-heading',37,37,'heading',C,CTX),('timing',38,40,'paragraph',R,REQ)]
cs4=[('handling-heading',4,4,'heading',C,CTX),('handling',5,7,'paragraph',R,REQ),('duration-heading',8,8,'heading',C,CTX),
     ('duration-a',9,11,'list_item',R,REQ),('duration-b',12,14,'list_item',R,REQ),('duration-c',15,16,'list_item',R,REQ),
     ('duration-d',17,23,'list_item',R,REQ),('copyright-heading',24,24,'heading',C,CTX),
     ('copyright',25,26,'paragraph',C,'Publisher copyright and reproduction terms; preserve as context outside the aquaculture certification obligation inventory.')]
for specs in (cs3,cs4):
    specs.extend([('footer-code',0,0,'footer',C,CTX),('footer-title',1,1,'footer',C,CTX),('page-number',2,2,'footer',C,CTX),('margin-filename',3,3,'margin_metadata',C,CTX)])
cs_visual=[('publisher','GLOBALG.A.P.',[490,10,583,87],'publisher_mark'),
           ('footer-copyright','© GLOBALG.A.P. c/o FoodPLUS GmbH',[420,797,562,805],'footer'),
           ('footer-address','Spichernstrasse 55 | 50672 Cologne, Germany',[390,806,562,814],'footer'),
           ('footer-contact','info@globalgap.org | www.globalgap.org',[392,815,563,824],'footer')]

samples={s['id']:s for s in MANIFEST['samples']}
pa=build(samples['pa057-reserved'],[(5,pa5,pa_visual),(6,pa6,pa_visual)])
cs=build(samples['cs010-reserved'],[(3,cs3,cs_visual),(4,cs4,cs_visual)])

def rel(doc,kind,**values):doc['structural_relations'].append(dict(kind=kind,**values))
table='pa057-reserved-p005-revision-table'
pa['tables']=[dict(id=table,page_number=5,row_count=4,column_count=2,header_rows=[0],merges=[],
                   caption_unit='pa057-reserved-p005-revision-caption')]
for u in pa['units']:
    if '-revision-r' in u['id']:
        m=re.search(r'-r(\d)-c(\d)$',u['id']);u['table_cell']=dict(table_id=table,row=int(m[1]),column=int(m[2]))
        rel(pa,'table_cell_position',unit=u['id'],table_id=table,row=int(m[1]),column=int(m[2]))
for row in range(1,4):
    for col in range(2):rel(pa,'column_header',header=f'pa057-reserved-p005-revision-r0-c{col}',cell=f'pa057-reserved-p005-revision-r{row}-c{col}')
rel(pa,'note_attached_to_definition',note='pa057-reserved-p006-note',definition='pa057-reserved-p006-produksjonsenhet')
for child in ['finfish','crustaceans','molluscs','seaweed']:
    rel(cs,'list_member',parent='cs010-reserved-p003-product-list-intro',child='cs010-reserved-p003-'+child)
for parent,child in [('scope-heading','product-heading'),('audit-heading','timing-heading')]:
    rel(cs,'heading_parent',parent='cs010-reserved-p003-'+parent,child='cs010-reserved-p003-'+child)
for child in ['handling-heading','duration-heading']:
    rel(cs,'heading_parent',parent='cs010-reserved-p003-audit-heading',child='cs010-reserved-p004-'+child)
cs['uncertainties'].append(dict(unit_id='cs010-reserved-p003-scientific-name',kind='requirement_classification',reason=UNC))

critical={
 'pa057-reserved-p005-purpose':[('NS 3424:2012','standard_identifier'),('NS 9416:2013','standard_identifier')],
 'pa057-reserved-p005-commission':[('01.01.18-01.07.18','date_range')],
 'pa057-reserved-p006-brukstid':[('uten at det skal være nødvendig med omfattende reparasjon','negated_condition')],
 'pa057-reserved-p006-fellesfunksjon':[('eller ikke naturlig inngår i en avdeling','negation')],
 'pa057-reserved-p006-referanseniva':[('Dersom en tilstand er dårligere enn referansenivået, regnes det som et avvik.','condition')],
 'cs010-reserved-p003-edition-scope':[('version 6 Smart','version'),('version 6 GFS','version')],
 'cs010-reserved-p003-combined-rules':[('shall be used in combination','obligation')],
 'cs010-reserved-p003-shall-definition':[('The term “shall”','modal_definition')],
 'cs010-reserved-p003-seedlings':[('At all stages','applicability'),('If wild-caught brood stock is used','condition'),('ecologically managed','condition'),('Passive collection of seedlings from the planktonic phase is allowed for molluscs’ spat.','permission_exception')],
 'cs010-reserved-p003-wild-exclusion':[('cannot be achieved','negation'),('not farmed','negation')],
 'cs010-reserved-p003-postharvest':[('by the same legal entity as the farm','applicability'),('in order for the producer to achieve certification','condition')],
 'cs010-reserved-p004-handling':[('Option 2','scope_identifier'),('Option 1','scope_identifier'),('with or without QMS','applicability'),('more than one','threshold'),('while in operation','condition'),('no sampling','prohibition')],
 'cs010-reserved-p004-duration-b':[('no less than one and a half days','duration_threshold'),('excludes the GRASP assessment or any other add-on CB audit','exclusion'),('first year','applicability')],
 'cs010-reserved-p004-duration-c':[('In subsequent years','applicability'),('no less than seven hours on-site','duration_threshold')],
 'cs010-reserved-p004-duration-d':[('minimum duration of seven hours','duration_threshold'),('simplest circumstances','condition'),('no product handling','negation'),('less than five workers','threshold'),('exclude reporting, preparation, and travel (during the CB audit)','exclusion'),('Any other type of operation','condition'),('more than seven hours on-site audit time','duration_threshold'),('also exclude the duration of the GRASP assessment or any other add-on CB audit','exclusion')],
 'cs010-reserved-p004-copyright':[('only in unaltered form','reproduction_condition')],
}
for doc in (pa,cs):
    for unit in doc['units']:
        for phrase,category in critical.get(unit['id'],[]):
            assert phrase in unit['text'], (unit['id'],phrase)
            start=unit['text'].index(phrase)
            unit['critical_spans'].append(dict(text=phrase,start=start,end=start+len(phrase),category=category))
    # Candidate evaluation uses complete source clauses, separate from the
    # content-unit inventory. The scope lead-in and its list are one decision.
    list_children=['cs010-reserved-p003-'+name for name in ['finfish','crustaceans','molluscs','seaweed']]
    by_id={u['id']:u for u in doc['units']}
    evaluation=[]
    for unit in doc['units']:
        if unit['id'] in list_children:
            continue
        source_ids=[unit['id']]
        if unit['id']=='cs010-reserved-p003-product-list-intro':source_ids+=list_children
        evaluation.append(dict(id=unit['id']+'-judgment',content_unit_ids=source_ids,
                               text='\n'.join(by_id[identity]['text'] for identity in source_ids),
                               classification=unit['requirement_judgment']['classification'],
                               reason=unit['requirement_judgment']['reason']))
    covered=[identity for entry in evaluation for identity in entry['content_unit_ids']]
    assert len(covered)==len(set(covered))==len(doc['units']) and set(covered)==set(by_id)
    doc['requirement_evaluation_units']=evaluation
    doc['denominators']=dict(content_units=len(doc['units']),structural_relationships=len(doc['structural_relations']),
                             critical_spans=sum(len(u['critical_spans']) for u in doc['units']),
                             requirement_unit_labels=dict(Counter(u['requirement_judgment']['classification'] for u in doc['units'])),
                             requirement_evaluation_units=len(evaluation),
                             requirement_evaluation_labels=dict(Counter(u['classification'] for u in evaluation)),
                             content_inventory_status='COMPLETE_FOR_FIXED_RENDERED_PAGE_WINDOWS',
                             requirement_precision_recall_status='UNMEASURED: no predictions compared; uncertain classification retained. PA057 has zero positive reference units, so its recall denominator is zero, never 100 percent.',
                             business_gold_status='NOT_BUSINESS_GOLD',
                             rule='Every listed unit remains in the source-content denominator, including publisher/footer units and uncertain Requirement labels. Report text and visual-only strata separately without silently dropping either.')
    dest=OUT/(doc['sample_id']+'-source-annotation.json')
    dest.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
    print(dest.name,doc['denominators'])
