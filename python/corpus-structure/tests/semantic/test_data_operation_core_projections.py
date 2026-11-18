"""One captured Core projection supplies native SQL and decoder row shape."""

import pglast
import pytest
from sqlalchemy.dialects.postgresql import JSONB, dialect

from corpus_structure.semantic.data_operation_projections import (
    binding_branches,
    binding_columns,
    cancellation_scopes,
    capture_projection_sources,
    member_columns,
    read_page,
    read_scope_rows,
)
from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql
from corpus_structure.semantic.metadata import get_metadata


def _compile(query):
    return str(
        query.compile(dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True})
    )


def test_core_builders_own_return_shape_and_keep_scoped_native_parameters():
    computed, original = map(_compile, binding_branches(get_metadata()))
    scopes = _compile(read_scope_rows(get_metadata()))
    page = _compile(read_page(get_metadata()))
    assert {column.name for column in binding_columns()} == {
        column.name for column in binding_columns(decoder=True)
    }
    assert "provider_identity" in member_columns()
    columns = {column.name: column.type for column in binding_columns()}
    assert isinstance(columns["analyzed_scope"], JSONB)
    for source in (scopes, _compile(cancellation_scopes(get_metadata())), computed, original, page):
        assert pglast.parse_sql(source)
    assert "support_closure" in scopes
    assert "data_derivation_original_support" in scopes
    assert "p_operation" in computed
    assert "after_key" in page and "LIMIT lim" in page
    assert "ops.ddo_episode_provider_identity" in computed


def test_dependency_free_waiting_watermark_filters_local_publications_by_actual_role():
    from pglast import ast
    from pglast.visitors import Visitor

    from corpus_structure.semantic.data_operation_projections import _unconstrained_watermark_uses

    query = _compile(
        _unconstrained_watermark_uses(
            get_metadata(), get_metadata().tables["ops.data_obligation"].alias("waiting_obligation")
        )
    )
    parsed = pglast.parse_sql(query)
    assert parsed and isinstance(parsed[0].stmt, ast.SelectStmt)
    assert "watermark_local_use.demand_id = d.id" in query
    assert "watermark_local_product.project_id = d.project_id" in query
    assert (
        "jsonb_array_length(watermark_unconstrained_operation.value['dependencies']) = 0" in query
    )
    assert "accepted_kind_contracts" in query and "source_set" in query
    assert "IS NULL" in query and "waiting_obligation.analyzed_scope" in query
    assert "watermark_local_later.obligation_id = watermark_local_use.obligation_id" in query
    # Authorization routines refuse, rather than returning false. Their actual
    # evaluation must stay behind immutable role/context eligibility.
    conditions = parsed[0].stmt.whereClause
    assert isinstance(conditions, ast.BoolExpr) and conditions.args
    authorization = conditions.args[-1]
    assert isinstance(authorization, ast.CaseExpr)
    assert authorization.args
    assert isinstance(authorization.args[0].expr, ast.CaseExpr)
    disclosure = authorization.args[0].result
    assert isinstance(disclosure, ast.CaseExpr) and disclosure.args
    assert isinstance(disclosure.args[0].result, ast.BoolExpr)
    calls = set()

    class Calls(Visitor):
        def visit_FuncCall(self, ancestors, node):
            calls.add(tuple(part.sval for part in node.funcname))

    Calls()(parsed[0])
    assert {
        ("ops", "ddo_binding_subject"),
        ("ops", "ddo_binding_source"),
        ("ops", "ddo_kind_access"),
        ("ops", "ddo_body_access"),
    } <= calls
    page = _compile(read_page(get_metadata()))
    assert "watermark_local_use" in page and "watermark_prerequisites" in page


def test_selected_cut_disclosure_is_pinned_before_any_role_reacquisition():
    from sqlalchemy import select
    from sqlalchemy.schema import CreateTable

    from corpus_structure.semantic.data_operation_projections import (
        cut_selection_projection,
        read_access_universes,
        read_selection,
    )

    receipt = get_metadata().tables["ops.data_demand_read"]
    assert not receipt.c.public_disclosure.nullable
    assert receipt.c.public_disclosure.server_default is not None
    assert "public_disclosure BOOLEAN DEFAULT false NOT NULL" in _compile(CreateTable(receipt))
    for query in (
        select(read_selection()),
        cut_selection_projection(),
        read_access_universes(get_metadata()),
        read_page(get_metadata()),
    ):
        compiled = _compile(query)
        assert pglast.parse_sql(compiled)
        assert "boundary.public_disclosure" in compiled
        assert "pg_has_role" not in compiled
        assert "SESSION_USER" not in compiled


def test_native_authority_classification_has_no_reopening_principal_dependency():
    from pglast import ast

    from corpus_structure.semantic.native_sql_body import body_source
    from corpus_structure.semantic.prepared_sql import prepare_sql
    from corpus_structure.semantic.record_policy_native import record_policy_native_sql

    statements = prepare_sql(record_policy_native_sql(), source="pinned-authority-disclosure")
    leaf = next(
        statement.stmt
        for statement in statements.statements
        if isinstance(statement.stmt, ast.CreateFunctionStmt)
        and statement.stmt.funcname
        and statement.stmt.funcname[-1].sval == "ddo_policy_authority_leaf"
    )
    classifier = body_source(leaf)
    assert pglast.parse_sql(classifier)
    assert "pg_has_role" not in classifier
    assert "SESSION_USER" not in classifier
    assert "native_receipt" in classifier and "native_output" in classifier


def test_public_family_replies_guard_full_scoped_intent_presentation():
    from pglast import ast

    from corpus_structure.semantic.native_sql_body import body_source
    from corpus_structure.semantic.prepared_sql import prepare_sql
    from corpus_structure.semantic.source_admission_native import source_admission_native_sql
    from corpus_structure.semantic.visual_read_native import visual_read_programs

    programs = (
        source_admission_native_sql(get_metadata()),
        visual_read_programs(get_metadata(), b"{}"),
    )
    bodies = {
        statement.stmt.funcname[-1].sval: body_source(statement.stmt)
        for source in programs
        for statement in prepare_sql(source, source="family-cut-presentation").statements
        if isinstance(statement.stmt, ast.CreateFunctionStmt) and statement.stmt.funcname
    }
    for name in (
        "read_selected_pdf_source",
        "read_selected_pdf_observations",
        "read_selected_visual_evidence",
    ):
        assert "boundary.public_disclosure" in bodies[name]
        assert "ops.ddo_authorize('evaluator')" in bodies[name]


def test_native_sql_uses_frozen_core_products_without_ambient_builder(monkeypatch):
    captured = native_protocol_sources()
    first = native_sql(captured)
    import corpus_structure.semantic.data_operation_projections as projections

    monkeypatch.setattr(
        projections,
        "capture_projection_sources",
        lambda: (_ for _ in ()).throw(AssertionError("ambient builder")),
    )
    assert native_sql(captured) == first
    assert "__DDO_" not in first
    assert pglast.parse_sql(first)


def test_captured_sql_scope_projection_follows_its_domain_function_providers():
    from pglast import ast
    from pglast.visitors import Visitor

    from corpus_structure.semantic.native_sql_body import body_source
    from corpus_structure.semantic.prepared_sql import prepare_sql

    captured = native_protocol_sources()
    scope_source = next(
        source for source in captured if source.name == "native/data-operation-support-scopes.sql"
    )
    assert "CREATE OR REPLACE FUNCTION ops.ddo_support_scopes" in scope_source.content.decode()
    prepared = prepare_sql(native_sql(captured), source="scope-provider-installation-order")
    declarations = {
        tuple(part.sval for part in statement.stmt.funcname or ()): (index, statement.stmt)
        for index, statement in enumerate(prepared.statements)
        if isinstance(statement.stmt, ast.CreateFunctionStmt)
    }
    index, scope = declarations[("ops", "ddo_support_scopes")]
    assert (
        next(option.arg.sval for option in scope.options or () if option.defname == "language")
        == "sql"
    )
    calls = set()

    class Calls(Visitor):
        def visit_FuncCall(self, ancestors, node):
            calls.add(tuple(part.sval for part in node.funcname))

    Calls()(prepare_sql(body_source(scope), source="captured-scope-body").private_tree())
    providers = {
        ("ops", "ddo_record_grade_dependency_scopes"),
        ("ops", "ddo_record_fit_dependency_scopes"),
        ("ops", "ddo_operation_event_dependency_scopes"),
    }
    # These are the actual captured body calls, not a source-order smoke test.
    assert providers <= calls
    assert all(declarations[provider][0] < index for provider in providers)
    assert declarations[("ops", "ddo_scope")][0] < index
    population = ("ops", "ddo_discovery_role_population")
    visibility = ("ops", "ddo_read_visible")
    index, discovery = declarations[population]
    calls.clear()
    Calls()(prepare_sql(body_source(discovery), source="captured-discovery-body").private_tree())
    assert visibility in calls
    assert declarations[visibility][0] < index
    assert (
        declarations[("ops", "ddo_scope")][0]
        < declarations[("ops", "ddo_original_admission_valid")][0]
    )


def test_core_projection_capture_consumes_explicit_counterfactual_metadata_without_ambient_fallback(
    monkeypatch,
):
    import pytest
    import yaml

    import corpus_structure.schema.physical as physical

    sources = dict(get_metadata().info["physical_sources"])
    types = get_metadata().info["physical_linkml_types"]
    document = yaml.safe_load(sources["data-operation-physical.yaml"])
    document["classes"]["data_obligation"]["attributes"]["counterfactual_marker"] = {
        "range": "string"
    }
    sources["data-operation-physical.yaml"] = yaml.safe_dump(document).encode()
    proposed = physical.compile_physical(sources, linkml_types=types)
    assert "counterfactual_marker" in proposed.tables["ops.data_obligation"].c

    def unavailable(*args, **kwargs):
        raise AssertionError("ambient physical acquisition")

    monkeypatch.setattr(physical, "physical_source_closure", unavailable)
    monkeypatch.setattr(physical, "linkml_types_source", unavailable)
    captured = capture_projection_sources(
        physical_sources=proposed.info["physical_sources"],
        linkml_types=proposed.info["physical_linkml_types"],
    )
    assert "data_obligation.counterfactual_marker" in _compile(read_page(proposed))
    assert (
        next(
            source.content
            for source in captured
            if source.name == "native/projection-physical/data-operation-physical.yaml"
        )
        == sources["data-operation-physical.yaml"]
    )
    with pytest.raises(ValueError, match="captured LinkML types"):
        capture_projection_sources(physical_sources=sources)
    with pytest.raises(ValueError, match="physical closure"):
        capture_projection_sources(physical_sources={}, linkml_types=types)


@pytest.mark.parametrize("change", ["retire", "rename", "reclassify"])
def test_intrinsic_trigger_inventory_follows_captured_target_classes_without_ambient_fallback(
    change, monkeypatch, tmp_path
):
    import yaml

    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic import data_operation_storage as storage
    from corpus_structure.semantic.metadata import get_metadata

    sources = dict(get_metadata().info["physical_sources"])
    declaration = yaml.safe_load(sources["data-operation-physical.yaml"])
    name = "data_attempt_failure"
    if change == "retire":
        declaration["classes"].pop(name)
    elif change == "rename":
        declaration["classes"]["renamed_attempt_failure"] = declaration["classes"].pop(name)
    else:
        declaration["classes"][name]["annotations"]["ph:immutability"] = "physical"
    sources["data-operation-physical.yaml"] = yaml.safe_dump(declaration).encode()
    proposed = compile_physical(sources, linkml_types=get_metadata().info["physical_linkml_types"])
    # This table has no incoming foreign keys; each proposed physical declaration
    # remains coherent independently of the fixed current read function's support.
    assert proposed.sorted_tables
    monkeypatch.setattr(storage, "_ROOT", tmp_path / "unavailable-installed-model")
    names = {
        relation.fullname
        for relation in storage.data_operation_immutable_relations(proposed, sources)
    }
    assert "ops.data_attempt_failure" not in names
    assert "ops.data_derivation" in names
    assert ("ops.renamed_attempt_failure" in names) is (change == "rename")
    # Retaining a captured intrinsic declaration while changing only mutable
    # metadata cannot silently reclassify it or borrow the installed table.
    if change == "rename":
        proposed.tables["ops.renamed_attempt_failure"].info["immutability"] = "physical"
        with pytest.raises(ValueError, match="differs from captured class"):
            storage.data_operation_immutable_relations(proposed, sources)
