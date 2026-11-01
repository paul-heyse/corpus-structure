"""Native section selectors bind one numbered occurrence before subtree expansion."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from corpus_structure.semantic.operations import SourceReadRefused
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import (
    normalized_native_section_title,
    resolve_native_sections,
    scope_source_views,
)

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
    assert normalized_native_section_title(" 1.2— FUNCTIONS. ") == "1.2 functions"
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


def test_reader_resolves_catalog_before_descendant_and_maximal_root_selection():
    product = ProductReference(2, "organized", "a" * 64)
    selected = []
    rows = []
    for index, (pointer, title) in enumerate(CATALOG.items(), 1):
        selected.append(
            SimpleNamespace(
                id=index, native_product=product, section_pointer=pointer, membership="descendants"
            )
        )
        rows.append(dict(id=index, section={"self_ref": pointer, "name": title}, ancestors=[]))
    selected.append(
        SimpleNamespace(
            id=10,
            native_product=product,
            section_pointer="#/groups/child",
            membership="descendants",
        )
    )
    rows.append(
        dict(
            id=10,
            section={"self_ref": "#/groups/child", "name": "Operations"},
            ancestors=[{"self_ref": "#/groups/11", "name": "1.1: Sets"}],
        )
    )
    conn = Mock()
    conn.execute.return_value.mappings.return_value = rows
    scope = {"sections": SELECTORS, "include_descendants": True}
    assert [ref.section_pointer for ref in scope_source_views(conn, selected, scope)] == [
        "#/groups/11",
        "#/groups/12",
        "#/groups/13",
        "#/groups/18",
        "#/groups/56",
    ]
    with pytest.raises(SourceReadRefused, match="ambiguous native section selector"):
        scope_source_views(conn, selected, dict(scope, sections=["Functions"]))
