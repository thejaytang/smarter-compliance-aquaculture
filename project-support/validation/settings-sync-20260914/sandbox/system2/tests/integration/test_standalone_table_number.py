"""Literal number preservation, not a source-quality or classification claim."""
from copy import deepcopy
import pytest
from pdf_extraction.domains.requirements.table_row_fields import project
from pdf_extraction.review.effective import resolve
from pdf_extraction.review.requirement_subdivision import apply, delivery, SCHEMA, stale
from .test_pdf_repairs import table_units


@pytest.mark.parametrize('label', ['2.1.1', '4.2.1 & 4.2.2', '6.1.2a'])
def test_separate_number_preserves_full_body_and_exact_label(label):
    fields, inline = project([label, 'Measurement', '- Site name - Sampling date'])
    assert fields['identifier'] == label
    assert fields['body'] == label + '\nMeasurement\n- Site name - Sampling date'
    assert fields['criteria'] == '' and inline is False


@pytest.mark.parametrize('label', ['0.01', '2027-12-31', '10 mg/L', 'Requirement', ''])
def test_measurements_dates_and_headers_do_not_become_numbers(label):
    fields, _ = project([label, 'Value'])
    assert 'identifier' not in fields


def test_existing_inline_indicator_fields_are_preserved():
    fields, inline = project(['2.1.3 Number of taxa', '≥ 2 highly abundant taxa'])
    assert inline and fields == {'identifier':'2.1.3','body':'Number of taxa','criteria':'≥ 2 highly abundant taxa'}


def test_effective_existing_row_and_subdivision_retain_number_without_original_write():
    import json
    owner, row = table_units()
    table = json.loads(owner['original']['fields']['body'])
    table['cells'][0]['content'] = {'resolved_text':'2.1.3'}
    table['cells'][1]['content'] = {'resolved_text':'Site name and Sampling date'}
    owner['original']['fields']['body'] = json.dumps(table)
    row.update(version=1, kind='source_text')
    original = deepcopy([owner, row])
    view = resolve(row, {owner['id']:owner, row['id']:row})
    assert view['fields']['identifier'] == '2.1.3'
    assert view['fields']['body'] == '2.1.3\nSite name and Sampling date'
    spans = []
    for phrase in ['Site name','Sampling date']:
        start = view['fields']['body'].index(phrase)
        spans.append(dict(field='body',start=start,end=start+len(phrase),text=phrase))
    request = dict(actor='Engineering validation',request_id='number-test',subdivision_schema=SCHEMA,
                   count_basis='subitems',complete_range_reviewed=True,note='Retain printed number',
                   remainder_reason='Full parent wording retained',subitems=spans)
    split = apply(row,view,{'content_hash':'source'},request)
    envelope = delivery(dict(requirement_id='parent',source={'content_hash':'source'},
                             unit_version=1,references=view['references'],fields=view['fields'],canonical=[]),split)
    assert all(c['parent_original_number']=='2.1.3' and c['original_number'] is None for c in envelope['subitems'])
    assert [owner,row] == original
    row['requirement_subdivision'] = split
    changed = deepcopy(view); changed['fields']['identifier']='2.1.4'
    assert stale(row,changed,{'content_hash':'source'})

