"""Slice expansion preserves recorded selection, and scope resolves source locators."""
import pytest
from corpus_structure.orchestrate.slices import SliceError, expand

DOCS = [{'meta': {'page':'a.html', 'dev':'yes'}}, {'meta':{'page':'b.html','dev':'no'}}]


def test_nested_selectors_are_sorted_and_pages_remove_unit_selection():
    declarations = {'one':['a.html#u'], 'two':[{'include':'one'},'b.html#v'],
                    'pages':[{'pages':['two']}], 'dev':[{'index':'dev'}]}
    assert expand(declarations,'two',DOCS) == ('a.html#u','b.html#v')
    assert expand(declarations,'pages',DOCS) == ('a.html','b.html')
    assert expand(declarations,'dev',DOCS) == ('a.html',)


def test_cycles_and_unknown_names_are_refused():
    with pytest.raises(SliceError,match='cycle'):
        expand({'a':[{'include':'b'}],'b':[{'include':'a'}]},'a',DOCS)
    with pytest.raises(SliceError,match='unknown slice'):
        expand({},'missing',DOCS)


def test_golden_units_are_materialized_at_expansion():
    units = ['a.html#u']
    selected = expand({'dev':[{'golden_set':'p0'}]},'dev',DOCS,lambda label:units)
    units.append('b.html#v')
    assert selected == ('a.html#u',)
