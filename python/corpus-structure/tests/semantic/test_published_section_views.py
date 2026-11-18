"""Independent selected-only source construction, custody and report controls."""

from typing import Any

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
            source_digest="f" * 64,
            release_id="producer",
        )
        self.requests = []

    def sections(self, *, after=None, section_pointer=None, membership="direct", limit=None):
        assert (after, section_pointer, membership, limit) == (None, None, "direct", None)
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
    from pglast import ast, enums, parse_plpgsql, parse_sql
    from pglast.stream import RawStream
    from sqlalchemy.dialects.postgresql import dialect

    statements = published_read_statements()
    selectors = {
        "sections": (),
        "section_nodes": ("p_section", "p_membership"),
        "items": ("p_pointers",),
        "region": ("p_pointer", "p_region_index"),
        "section_reports": ("p_pointers", "p_sections"),
        "item_page": ("p_section", "p_membership", "p_pointer", "p_after", "p_limit"),
        "regions": ("p_pointer",),
        "region_batch": ("p_pointers",),
        "item_ancestors": ("p_pointer",),
    }
    assert set(statements) == set(selectors)
    for statement in statements.values():
        params = statement.compile(dialect=dialect()).params
        assert {"_native_build_id", "_native_revision_id"} <= params.keys()
    parsed = parse_sql(published_readers_sql())
    declarations = [raw.stmt for raw in parsed if isinstance(raw.stmt, ast.CreateFunctionStmt)]
    assert len(declarations) == 18
    grants = [raw.stmt for raw in parsed if isinstance(raw.stmt, ast.GrantStmt)]
    assert len(grants) == 45  # Each private/public pair revokes PUBLIC and grants three readers.
    for declaration in declarations:
        assert declaration.funcname and declaration.parameters and declaration.returnType
        name = declaration.funcname[-1].sval
        private = name.endswith("_rows")
        family = name.removeprefix("read_pdf_published_").removesuffix("_rows")
        arguments = tuple(parameter.name for parameter in declaration.parameters if parameter.mode != enums.FunctionParameterMode.FUNC_PARAM_TABLE)
        expected = ("p_build", "p_revision") if private else ("p_task", "p_product", "p_digest")
        assert arguments == (*expected, *selectors[family])
        assert declaration.returnType.setof
        assert tuple(parameter.name for parameter in declaration.parameters if parameter.mode == enums.FunctionParameterMode.FUNC_PARAM_TABLE) == tuple(statements[family].selected_columns.keys())
        options = {option.defname: option.arg for option in declaration.options or ()}
        assert options["volatility"].sval == "stable"
        allowed = {
            role.rolename for grant in grants if grant.is_grant
            and any(target.objname[-1].sval == name for target in grant.objects or ())
            for role in grant.grantees or ()
        }
        if private:
            assert options["language"].sval == "sql"
            assert "security" not in options or not options["security"].boolval
            assert declaration.sql_body is not None and "as" not in options
            assert allowed == set()
        else:
            assert options["language"].sval == "plpgsql"
            assert options["security"].boolval
            assert allowed == {"corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator"}
            assert parse_plpgsql(RawStream()(declaration))
            body = options["as"][0].sval
            assert body.index("INTO STRICT published") < body.index("PERFORM ops.require_pdf_operation") < body.index("RETURN QUERY")
            assert "'read_native_source'" in body
            if family != "sections":
                assert body.index("ERRCODE = '22023'") < body.index("RETURN QUERY")


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


class ResidualBodyReader(SelectedReader):
    def __init__(self, *, headings=True, residual=True):
        super().__init__()
        self.headings = headings
        self.residual = residual

    def sections(self, **kwargs):
        return super().sections(**kwargs) if self.headings else []

    def section_nodes(self, section, membership):
        if section != "#/body":
            return super().section_nodes(section, membership)
        self.requests.append((section, membership))
        assert membership == "direct"
        children = ([{"$ref": "#/texts/prefix"}] if self.residual else []) + (
            [{"$ref": "#/groups/1"}] if self.headings else []
        )
        rows: list[dict[str, Any]] = [
            dict(
                pointer="#/body",
                role="selected",
                native_json=dict(
                    self_ref="#/body", label="unspecified", content_layer="body", children=children
                ),
            )
        ]
        if self.residual:
            rows.append(
                dict(
                    pointer="#/texts/prefix",
                    role="selected",
                    native_json=dict(
                        self_ref="#/texts/prefix",
                        label="text",
                        text="Unheaded source prefix",
                        content_layer="body",
                        children=[],
                        parent={"$ref": "#/body"},
                    ),
                )
            )
        return rows

    def section_reports(self, pointers, sections):
        return []


def test_default_full_selection_includes_exact_unheaded_body_without_section_duplication():
    reader = ResidualBodyReader()
    drafts = published_section_drafts(
        reader,
        document_id=1,
        selections=(),
        membership="direct",
        scope=None,
        consumer_release="consumer",
    )
    assert reader.requests == [
        ("#/body", "direct"),
        ("#/groups/1", "direct"),
        ("#/groups/2", "direct"),
    ]
    assert [d.section_pointer for d in drafts] == ["#/body", "#/groups/1", "#/groups/2"]
    assert [d.text for d in drafts] == ["Unheaded source prefix", "x=1", ""]
    assert drafts[0].items == ("#/body", "#/texts/prefix") and drafts[0].membership == "direct"
    assert "#/groups/1" not in drafts[0].items
    assert drafts[0].health["inline_coverage"] == "unknown"


def test_default_no_heading_source_uses_authentic_body_scope_without_organization():
    reader = ResidualBodyReader(headings=False)
    (draft,) = published_section_drafts(
        reader,
        document_id=1,
        selections=(),
        membership="descendants",
        scope=None,
        consumer_release="consumer",
    )
    assert draft.section_pointer == "#/body" and draft.membership == "direct"
    assert draft.text == "Unheaded source prefix" and draft.ancestors == ()
    assert all(not pointer.startswith("#/groups") for pointer in draft.items)


def test_explicit_section_selection_omits_residual_and_empty_root_is_not_a_new_view():
    reader = ResidualBodyReader()
    drafts = published_section_drafts(
        reader,
        document_id=1,
        selections=("Target",),
        membership="direct",
        scope=None,
        consumer_release="consumer",
    )
    assert len(drafts) == 2 and all(d.section_pointer != "#/body" for d in drafts)
    assert all(pointer != "#/body" for pointer, _ in reader.requests)
    reader = ResidualBodyReader(residual=False)
    drafts = published_section_drafts(
        reader,
        document_id=1,
        selections=(),
        membership="direct",
        scope=None,
        consumer_release="consumer",
    )
    assert len(drafts) == 2 and all(d.section_pointer != "#/body" for d in drafts)


def test_explicit_native_section_scope_does_not_expand_to_root_body():
    rows = SelectedReader().sections()
    assert select_published_sections(
        rows, (), "descendants", dict(kind="native_sections", sections=["Target"])
    ) == ("#/groups/1",)


@pytest.mark.parametrize(
    "family,expected",
    [
        ("items", "p_pointers IS NULL OR array_position(p_pointers,NULL) IS NOT NULL"),
        ("region_batch", "p_pointers IS NULL OR array_position(p_pointers,NULL) IS NOT NULL"),
        ("section_reports", "p_pointers IS NULL OR p_sections IS NULL OR array_position(p_pointers,NULL) IS NOT NULL OR array_position(p_sections,NULL) IS NOT NULL"),
        ("region", "p_pointer IS NULL OR p_region_index IS NULL OR p_region_index<0"),
        ("item_page", "p_membership IS NULL OR p_membership NOT IN ('direct','descendants') OR p_after IS NULL OR p_after< -1 OR p_limit IS NULL OR p_limit<1 OR p_limit>1000"),
        ("regions", "p_pointer IS NULL"),
        ("item_ancestors", "p_pointer IS NULL"),
        ("section_nodes", """p_section IS NULL OR p_membership IS NULL OR p_membership NOT IN ('direct','descendants')
        OR NOT EXISTS(SELECT 1 FROM kb.pdf_record_access a
        WHERE a.product_id=published.build_id AND a.revision_id=published.build_id AND a.pointer=p_section
        AND (a.label IN ('section','chapter') OR (p_section='#/body' AND p_membership='direct'
        AND a.parent_pointer IS NULL AND a.content_layer='body' AND a.native_json->>'self_ref'='#/body')))"""),
    ],
)
def test_published_reader_selector_refusals_preserve_independent_predicates(family, expected):
    from pglast import parse_sql
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.sql.elements import ClauseElement

    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_program import Raise, core_variable
    from corpus_structure.semantic.published_document import (
        _published_read_guards,
        _published_read_selectors,
    )

    statement = published_read_statements()[family]
    publication = metadata.tables["ops.pdf_published_revision"]
    published = {field.name: core_variable("published", field.type, field.name) for field in publication.c}
    (guard,) = _published_read_guards(family, _published_read_selectors(family, statement), metadata.tables["kb.pdf_record_access"], published)
    assert isinstance(guard.condition, ClauseElement)
    actual = str(guard.condition.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
    assert parse_sql("SELECT " + actual)[0].stmt == parse_sql("SELECT " + expected)[0].stmt
    (refusal,) = guard.then
    assert isinstance(refusal, Raise) and refusal.sqlstate == "22023"
