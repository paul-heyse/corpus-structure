"""Independent selected-only source construction, custody and report controls."""

import pytest

from corpus_structure.ingest.pdf_section_views import (
    NoQualifiedSections,
    published_section_drafts,
    select_published_sections,
)
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.published_document import (
    PublishedDocumentBinding,
    published_read_statements,
    published_readers_sql,
)


class SelectedReader(PublishedPdfReader):
    def __init__(self):
        self.reference = ProductReference(42, "integrated", "a" * 64)
        self.revision = dict(
            task_id=42,
            product_key="integrated",
            logical_digest="a" * 64,
            build_id="published-42",
            release_id="producer",
        )
        self.requests = []

    def sections(self):
        return [
            dict(
                pointer="#/groups/1",
                parent_pointer="#/body",
                ordinal=1,
                name="Target",
                label="section",
                content_layer="body",
                ancestors=["#/body"],
            ),
            dict(
                pointer="#/groups/2",
                parent_pointer="#/groups/1",
                ordinal=4,
                name="Nested",
                label="section",
                content_layer="body",
                ancestors=["#/body", "#/groups/1"],
            ),
        ]

    def section_nodes(self, section, membership):
        self.requests.append((section, membership))
        assert membership == "direct"
        if section == "#/groups/2":
            return [
                dict(
                    pointer="#/groups/1",
                    role="ancestor",
                    native_json=dict(self_ref="#/groups/1", label="section", children=[]),
                ),
                dict(
                    pointer="#/groups/2",
                    role="selected",
                    native_json=dict(self_ref="#/groups/2", label="section", children=[]),
                ),
            ]
        assert section == "#/groups/1"
        return [
            dict(
                pointer="#/groups/1",
                role="selected",
                native_json=dict(
                    self_ref="#/groups/1",
                    label="section",
                    content_layer="body",
                    children=[{"$ref": "#/texts/7"}, {"$ref": "#/groups/2"}],
                ),
            ),
            dict(
                pointer="#/texts/7",
                role="selected",
                native_json=dict(
                    self_ref="#/texts/7",
                    label="formula",
                    content_layer="body",
                    text="x=1",
                    children=[],
                    parent={"$ref": "#/groups/1"},
                ),
            ),
        ]

    def iter_companions(self, family):
        assert family == "health"
        yield dict(
            source_scope="whole_document",
            conversion="success",
            display_coverage="partial",
            inline_coverage="complete",
            cell_coverage="complete",
        )
        yield dict(status="source_ready")

    def has_native_metadata(self, kind):
        assert kind == "recognition_coverage"
        return True

    def section_reports(self, pointers, sections):
        if pointers == ("#/groups/2",):
            assert sections == ("#/groups/2", "#/groups/1")
            return []
        assert pointers == ("#/groups/1", "#/texts/7")
        assert sections == ("#/groups/1",)
        return [
            dict(
                local_id="formula_outcomes:77",
                ordinal=77,
                body=dict(
                    kind="formula_outcomes",
                    pointer="#/texts/7",
                    outcome="failed",
                    has_diagnostic=True,
                ),
            )
        ]

    def hydrate_document(self):
        raise AssertionError("whole-book demand is forbidden in selected construction")

    def native_product_values(self, *, include_candidate_pages=True):
        raise AssertionError("native product materialization is forbidden in selected construction")


def test_selected_constructor_uses_exact_closure_and_original_report_locator():
    reader = SelectedReader()
    drafts = published_section_drafts(
        reader,
        document_id=1,
        selections=("Target",),
        membership="direct",
        scope=None,
        consumer_release="consumer",
    )
    assert reader.requests == [("#/groups/1", "direct"), ("#/groups/2", "direct")]
    assert len(drafts) == 2
    assert drafts[0].text == "x=1"
    assert drafts[0].items == ("#/groups/1", "#/texts/7")
    assert drafts[1].items == ("#/groups/2",)
    assert drafts[1].ancestors == ("#/groups/1",)
    assert drafts[0].health["formula_outcomes"] == [
        dict(
            pointer="#/texts/7",
            outcome="failed",
            diagnostic_ref=dict(
                task_id=42,
                product_key="integrated",
                content_digest="a" * 64,
                family="native_metadata",
                local_id="formula_outcomes:77",
            ),
        )
    ]
    assert [
        drafts[0].health[key] for key in ("display_coverage", "inline_coverage", "cell_coverage")
    ] == ["unknown", "unknown", "unknown"]
    assert drafts[0].native_product == reader.reference


class FrontierReader(SelectedReader):
    def __init__(self):
        super().__init__()
        self.frontier_requests = []
        self.frontier_values = {
            "#/texts/8": dict(self_ref="#/texts/8", content_layer="furniture", text="footer"),
            "#/texts/9": dict(self_ref="#/texts/9", content_layer="furniture", text="header"),
        }

    def section_nodes(self, section, membership):
        rows = super().section_nodes(section, membership)
        if section == "#/groups/1":
            for row, pointer in zip(rows, ("#/texts/8", "#/texts/9"), strict=True):
                native = row["native_json"]
                assert isinstance(native, dict)
                children = native["children"]
                assert isinstance(children, list)
                children.append({"$ref": pointer})
        return rows

    def selected_native_items(self, pointers):
        self.frontier_requests.append(pointers)
        return self.frontier_values


def test_body_projection_qualifies_excluded_native_frontier_in_one_exact_batch():
    reader = FrontierReader()
    drafts = published_section_drafts(
        reader,
        document_id=1,
        selections=("Target",),
        membership="direct",
        scope=None,
        consumer_release="consumer",
    )
    assert reader.frontier_requests == [("#/texts/8", "#/texts/9")]
    assert drafts[0].text == "x=1"
    assert drafts[0].pieces == (
        dict(start=0, end=3, kind="native_text", item_ref="#/texts/7", source_field="text"),
    )
    assert drafts[0].items == ("#/groups/1", "#/texts/7")
    assert drafts[0].ancestors == ()
    assert drafts[1].items == ("#/groups/2",)
    outcomes = drafts[0].health["formula_outcomes"]
    assert isinstance(outcomes, list) and len(outcomes) == 1
    outcome = outcomes[0]
    assert isinstance(outcome, dict) and outcome["pointer"] == "#/texts/7"


@pytest.mark.parametrize("fault", ["absent", "extra", "body", "default_body", "identity"])
def test_body_projection_refuses_unqualified_missing_child_frontier(fault):
    reader = FrontierReader()
    if fault == "absent":
        del reader.frontier_values["#/texts/8"]
    elif fault == "extra":
        reader.frontier_values["#/texts/10"] = dict(
            self_ref="#/texts/10", content_layer="furniture", text="unselected"
        )
    elif fault == "body":
        reader.frontier_values["#/texts/8"]["content_layer"] = "body"
    elif fault == "default_body":
        del reader.frontier_values["#/texts/8"]["content_layer"]
    else:
        reader.frontier_values["#/texts/8"]["self_ref"] = "#/different"
    with pytest.raises(ValueError, match="unqualified missing child"):
        published_section_drafts(
            reader,
            document_id=1,
            selections=("Target",),
            membership="direct",
            scope=None,
            consumer_release="consumer",
        )


def test_selector_preserves_ancestry_through_non_section_containers():
    rows = [
        dict(pointer="#/groups/1", name="Parent", ancestors=["#/body"]),
        dict(pointer="#/groups/2", name="Child", ancestors=["#/body", "#/groups/1", "#/groups/99"]),
    ]
    assert select_published_sections(rows, ("Parent",), "direct", None) == (
        "#/groups/1",
        "#/groups/2",
    )
    assert select_published_sections(rows, ("Parent", "Child"), "descendants", None) == (
        "#/groups/1",
    )


def test_only_absent_organization_uses_the_typed_global_recovery_signal():
    with pytest.raises(NoQualifiedSections):
        select_published_sections([], ("Requested after organization",), "direct", None)
    with pytest.raises(ValueError) as missing:
        select_published_sections(
            [
                dict(pointer="#/groups/0", name="Other", ancestors=["#/body"]),
            ],
            ("Missing",),
            "direct",
            None,
        )
    assert not isinstance(missing.value, NoQualifiedSections)


def test_exact_binding_refuses_mismatched_semantic_pin_and_address_placement():
    reader = SelectedReader()
    binding = PublishedDocumentBinding.from_revision(reader.reference, reader.revision)
    assert binding.producer_release_id == "producer"
    with pytest.raises(ValueError, match="exact product pin"):
        PublishedDocumentBinding.from_revision(
            ProductReference(43, "integrated", "a" * 64), reader.revision
        )
    with pytest.raises(ValueError, match="placement differs"):
        binding.require_placement(dict(native_build_id="other", native_revision_id="other"))


def test_finite_readers_resolve_both_placement_coordinates_and_guard_before_projection():
    from pglast import parse_sql
    from sqlalchemy.dialects.postgresql import dialect

    statements = published_read_statements()
    assert set(statements) == {
        "sections",
        "section_nodes",
        "items",
        "region",
        "section_reports",
        "item_page",
        "regions",
        "region_batch",
        "item_ancestors",
    }
    for statement in statements.values():
        params = statement.compile(dialect=dialect()).params
        assert {"_native_build_id", "_native_revision_id"} <= params.keys()
    sql = published_readers_sql()
    assert parse_sql(sql)
    for block in sql.split("CREATE OR REPLACE FUNCTION ")[1:]:
        if block.split("(", 1)[0].endswith("_rows"):
            assert "LANGUAGE sql STABLE SECURITY INVOKER" in block
            assert "BEGIN ATOMIC" in block
            assert "FROM PUBLIC" in block
            assert "GRANT EXECUTE" not in block
            continue
        assert block.index("INTO STRICT published") < block.index("RETURN QUERY")
        assert "published.release_id,'read_native_source'" in block


def test_selected_projection_refuses_absent_consumer_context_before_any_query():
    from unittest.mock import MagicMock

    from sqlalchemy import Connection

    conn = MagicMock(spec=Connection)
    reader = PublishedPdfReader(
        conn, ProductReference(42, "integrated", "a" * 64), revision=SelectedReader().revision
    )
    with pytest.raises(ValueError, match="explicit consumer release"):
        reader.sections()
    conn.execute.assert_not_called()
