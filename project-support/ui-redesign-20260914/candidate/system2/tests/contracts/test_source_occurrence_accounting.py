from itertools import product

from pdf_extraction.verification.occurrence_accounting import _maximum_assignment
from pdf_extraction.verification.source_comparison import compare


def original(lines):
    return dict(page_index=0, width=600, height=800, unverified=[],
                lines=[dict(text=text, bbox=bounds, engine=engine) for text,bounds,engine in lines])


def output(identity,text,bounds):
    return dict(id=identity,unit_id=identity,text=text,references=[dict(page_index=0,bbox=bounds)])


def test_single_output_occurrence_cannot_cover_two_original_obligations():
    p=original([('Do not exceed 15 mg.',[20,20,200,40],'poppler'),
                ('Do not exceed 15 mg.',[20,100,200,120],'poppler')])
    result=compare(p,[output('wide','Do not exceed 15 mg.',[0,0,600,800])])
    issue=next(f for f in result['findings'] if f['code']=='source_occurrence_shortfall')
    assert issue['severity']=='critical'
    assert len(issue['source_regions'])==2
    assert all(x['required_occurrences']==2 and x['matched_occurrences']==1 for x in issue['occurrence_checks'])
    assert result['confidence'] is None and result['acceptance']=='not_assessed'


def test_repeated_text_retained_in_multiline_output_is_not_a_shortfall():
    p=original([('Record water temperature.',[20,20,200,40],'poppler'),
                ('Record water temperature.',[20,60,200,80],'poppler')])
    assert compare(p,[output('both','Record water temperature. Record water temperature.',[20,20,200,80])])['findings']==[]


def test_assignment_can_reassign_first_match_to_preserve_a_later_match():
    p=original([('Record',[20,20,100,40],'poppler'),('Record',[20,60,100,80],'poppler')])
    records=[output('both','Record',[20,20,100,80]),output('first','Record',[20,20,100,40])]
    assert compare(p,records)['findings']==[]


def test_engine_observations_do_not_double_the_required_count():
    p=original([('Record',[20,20,100,40],'poppler'),('Record',[20,20,100,40],'tesseract')])
    assert compare(p,[output('one','Record',[20,20,100,40])])['findings']==[]


def test_total_token_count_does_not_override_spatial_capacity():
    p=original([('Record',[20,20,100,40],'poppler'),('Record',[20,60,100,80],'poppler'),
                ('Record',[20,100,100,120],'poppler')])
    records=[output('first-two','Record',[20,20,100,80]),output('last','Record Record',[20,100,100,120])]
    issues=compare(p,records)['findings']
    shortfall=next(f for f in issues if f['code']=='source_occurrence_shortfall')
    assert shortfall['occurrence_checks'][0]['matched_occurrences']==2


def test_parallel_column_ownership_is_located_abstention():
    p=original([('INDICATOR',[20,20,100,40],'poppler'),('REQUIREMENT',[300,20,450,40],'poppler')])
    wide=[0,0,600,100]
    records=[output('left','REQUIREMENT',wide),output('right','INDICATOR',wide)]
    result=compare(p,records)
    assert result['findings']==[]
    assert len(result['unverified'])==1
    assert all(u['code']=='output_spatial_ownership_ambiguous' and len(u['source_regions'])==2 for u in result['unverified'])
    exact=[output('left','INDICATOR',[20,20,100,40]),output('right','REQUIREMENT',[300,20,450,40])]
    assert compare(p,exact)['unverified']==[]


def test_maximum_assignment_matches_exhaustive_small_graph_oracle():
    # Enumerating distinct assignments is independent of the flow algorithm.
    for flags in product((False,True),repeat=9):
        neighbors={i:[j for j in range(3) if flags[3*i+j]] for i in range(3)}
        best=0
        for assignment in product((None,0,1,2),repeat=3):
            chosen=[j for j in assignment if j is not None]
            if len(chosen)!=len(set(chosen)):
                continue
            if all(j is None or j in neighbors[i] for i,j in enumerate(assignment)):
                best=max(best,len(chosen))
        assert _maximum_assignment({i:1 for i in range(3)},{i:1 for i in range(3)},neighbors)==best
    assert _maximum_assignment({0:2,1:2},{0:1,1:3},{0:[0],1:[0]})==1
