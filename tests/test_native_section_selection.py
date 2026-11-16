"""Native section selectors bind one numbered occurrence before subtree expansion."""


import pytest

from corpus_structure.semantic.refusals import SourceReadRefused
from corpus_structure.ingest.pdf_hierarchy import resolve_native_sections


CATALOG = {
    "#/groups/11": "1.1: Sets",
    "#/groups/12": "1.2: Functions",
    "#/groups/13": "1.3: Relations",
    "#/groups/18": "1.8: Combinatorial Structures",
    "#/groups/56": "5.6: The Normal Distribution",
    "#/groups/22": "2.2: Functions",
    "#/groups/23": "2.3: Relations",
    "#/groups/66": "6.6: The Normal Distribution",
    "#/groups/72": "Functions",
}
SELECTORS = (
    "1.1: Sets",
    "1.2: Functions",
    "1.3: Relations",
    "1.8: Combinatorial Structures",
    "5.6: The Normal Distribution",
)


def test_numbered_selectors_do_not_expand_to_repeated_titles():
    assert resolve_native_sections(CATALOG, SELECTORS) == (
        "#/groups/11",
        "#/groups/12",
        "#/groups/13",
        "#/groups/18",
        "#/groups/56",
    )
    assert resolve_native_sections(CATALOG, ["1.2 — functions!"]) == ("#/groups/12",)


@pytest.mark.parametrize("selector", ["Functions", "Relations", "The Normal Distribution"])
def test_unnumbered_alias_requires_unique_available_occurrence(selector):
    with pytest.raises(SourceReadRefused, match="ambiguous native section selector"):
        resolve_native_sections(CATALOG, [selector])


def test_unique_unnumbered_aliases_preserve_existing_selection():
    catalog = {"s": "1.1: Sets", "o": "1.1.1: Operations"}
    assert resolve_native_sections(catalog, ["Sets", "Operations"]) == ("s", "o")
    with pytest.raises(SourceReadRefused, match="unavailable"):
        resolve_native_sections(catalog, ["1.2: Sets"])



def test_descendant_selection_retains_only_maximal_actual_roots():
    from corpus_structure.ingest.pdf_section_views import select_published_sections

    rows = [dict(pointer=key, name=title, ancestors=[]) for key, title in CATALOG.items()]
    rows.append(dict(pointer="#/groups/child", name="Operations", ancestors=["#/groups/11"]))
    scope = dict(kind="native_sections", sections=(*SELECTORS, "Operations"))
    assert select_published_sections(rows, (), "descendants", scope) == (
        "#/groups/11", "#/groups/12", "#/groups/13", "#/groups/18", "#/groups/56"
    )
    assert select_published_sections(rows, (), "direct", dict(kind="native_sections", sections=("1.1: Sets",))) == ("#/groups/11", "#/groups/child")
