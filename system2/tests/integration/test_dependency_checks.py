from copy import deepcopy

from pdf_extraction.review.dependency_checks import pending


def unit(uid, dependencies=(), status='pending', kind='source_text'):
    return dict(id=uid, kind=kind, dependencies=list(dependencies), content_status=status,
        original=dict(fields=dict(title=uid, body='Exact source'),
                      references=[dict(page_index=1)], structure=[]), blockers=[])


def test_transitive_prerequisites_are_distinct_and_do_not_mutate_state():
    units=[unit('row',['table','page']),unit('table',['page','context'],'human_accepted'),
           unit('page',kind='coverage'),unit('context',['global']),unit('global',kind='coverage')]
    units[-1]['original']['references']=[dict(locator='whole parsed range')]
    by={u['id']:u for u in units};before=deepcopy(by)
    result=pending(by['row'],by)
    assert [x['unit_id'] for x in result]==['page','context','global']
    assert result[-1]['scope']==['whole parsed range']
    assert result[0]['scope']==['Original page 2']
    assert by==before


def test_missing_and_cyclic_dependencies_remain_visible():
    by={u['id']:u for u in [unit('a',['b','gone']),unit('b',['a'],'human_accepted')]}
    result=pending(by['a'],by)
    assert {x['title'] for x in result}=={'Cyclic dependency','Missing source dependency'}
    assert next(x for x in result if x['unit_id']=='gone')['available'] is False


def test_fully_accepted_prerequisites_are_not_redisplayed_as_pending():
    by={u['id']:u for u in [unit('a',['b']),unit('b',status='machine_accepted')]}
    assert pending(by['a'],by)==[]


def test_cycle_between_accepted_ancestors_is_still_explained():
    by={u['id']:u for u in [unit('a',['b']),unit('b',['c'],'human_accepted'),
                            unit('c',['b'],'human_accepted')]}
    assert [x['title'] for x in pending(by['a'],by)]==['Cyclic dependency']
