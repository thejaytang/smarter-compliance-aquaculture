from dataclasses import replace
import pytest
from pdf_extraction.types import NativeObject, NativePage
from pdf_extraction.routing.native_spacing import coalesce


def page(tokens=('Qua','lity'),fonts=('F1','F2')):
    words=[];chars=[];x=0
    for i,(token,font) in enumerate(zip(tokens,fonts)):
        words.append(NativeObject(str(i),token,(x,0,x+len(token),10),font_key=font))
        for c in token:
            chars.append(NativeObject('c'+str(len(chars)),c,(x,0,x+1,10),object_type='character',font_key=font));x+=1
    return NativePage(0,100,100,words=words,characters=chars)


def test_exact_characters_join_font_fragments_without_mutating_source():
    p=page();before=list(p.words);words,ops=coalesce(p)
    assert [w.text for w in words]==['Quality']
    assert p.words==before and ops[0]['source_word_ids']==['0','1']


def test_chain_preserves_punctuation_characters():
    p=page(('(','Yes/No',')'),('F1','F2','F1'))
    assert [w.text for w in coalesce(p)[0]]==['(Yes/No)']


@pytest.mark.parametrize('case',['space','no_characters','different_line','gap','same_font','ocr','conflicting_character'])
def test_abstains_without_unambiguous_native_evidence(case):
    p=page()
    if case=='space':p.characters.insert(3,NativeObject('space',' ',(3,0,3,10),object_type='character'))
    if case=='no_characters':p.characters=[]
    if case=='different_line':p.words[1]=replace(p.words[1],bbox_points=(0,11,4,21))
    if case=='gap':p.words[1]=replace(p.words[1],bbox_points=(4,0,8,10))
    if case=='same_font':p.words[1]=replace(p.words[1],font_key='F1')
    if case=='ocr':p.words[1]=replace(p.words[1],from_ocr=True)
    if case=='conflicting_character':p.characters[0]=replace(p.characters[0],text='X')
    assert len(coalesce(p)[0])==2 and not coalesce(p)[1]
