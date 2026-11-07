"""Series-owned forward candidate preparation on Alembic's normal migration lifecycle."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from alembic.autogenerate import produce_migrations
from alembic.migration import MigrationContext
from pglast import ast
from sqlalchemy import text

from .alembic_defaults import compare_default, compare_type
from .alembic_defaults import plugin as defaults_plugin
from .alembic_indexes import plugin as indexes_plugin
from .alembic_native import plugin as native_plugin
from .companion_projection_native import companion_projection_definitions
from .metadata import SCHEMAS, metadata
from .native_objects import (
    NativeAuthoringError,
    NativeDefinition,
    NativeIdentity,
    NativeObject,
    definition_from_sql,
    prepare_native_authoring,
    semantic_namespace_owner,
)
from .prepared_sql import prepare_sql


def _shape_definition(connection, sql, *, source):
    prepared = prepare_sql(sql, source=source)
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) == ("ops", "pdf_native_record_shape"):
            return definition_from_sql(
                connection, prepared.excerpt(index), source=source, owner="corpus_sem_publisher"
            )
    raise NativeAuthoringError(f"{source}: native record shape declaration is absent")


def _context_definition(connection, sql, *, source):
    prepared = prepare_sql(sql, source=source)
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) == ("ops", "pdf_record_context_rows"):
            return definition_from_sql(
                connection, prepared.excerpt(index), source=source, owner="corpus_sem_publisher"
            )
    raise NativeAuthoringError(f"{source}: native context rows declaration is absent")


# Existing PDF declarations join the forward native object lifecycle when this scope
# starts owning their semantics. Their predecessor is always the frozen0065 source.
_PDF_PAYLOAD_FUNCTIONS = frozenset(
    {
        "adopt_pdf_batch",
        "prepare_pdf_build",
        # Freeze owns the publication fence; source changes must reach the same
        # frozen0065 backfill and exact forward admission as the other PDF kernels.
        "freeze_pdf_build",
        "resume_pdf_build",
        "adopt_pdf_companion",
        "read_pdf_frozen_rows",
        "read_pdf_published_revision",
        "read_pdf_published_validation",
        "adopt_pdf_access",
        "record_pdf_native_validation",
        "validate_pdf_build",
        "lookup_pdf_validation",
        "seal_pdf_build",
        "pdf_validation_contract",
        "pdf_projection_contract",
        "pdf_check_access_correspondence",
        "pdf_identity_stream_scalar",
        "pdf_identity_ascii_string",
        "pdf_identity_companion_scalar",
        "pdf_record_logical_identity",
        "read_pdf_record_rows",
        "read_pdf_record_context_rows",
        "publish_source_view",
        "validate_projected_table_captions",
        "validate_native_frame_source",
        "publish_pdf_region_artifact",
        "pdf_record_scope_health",
        "publish_pdf_observation",
    }
)


def _pdf_payload_definitions(connection, sql, *, source):
    from .native_function_signatures import function_signature
    from .native_inventory import update_function_inventory

    inventory = {}
    prepared = update_function_inventory(inventory, sql)
    definitions = {}
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        name = tuple(part.sval for part in statement.funcname or ())
        if len(name) != 2 or name[0] != "ops" or name[1] not in _PDF_PAYLOAD_FUNCTIONS:
            continue
        descriptor = inventory[function_signature(statement)]
        definition = definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source,
            owner=descriptor["owner"],
            grants=tuple((role, "EXECUTE", False) for role in descriptor["execute_roles"]),
        )
        # CREATE OR REPLACE can recur in a frozen collection; the last declaration
        # is the source authority, while the inventory carries its cumulative ACL.
        definitions[definition.identity] = definition
    return tuple(definitions.values())


def _publication_view_definitions(connection, sql, *, source):
    """Own current published views with their frozen predecessors and explicit ACLs."""
    prepared = prepare_sql(sql, source=source)
    definitions = {}
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if (
            isinstance(statement, ast.ViewStmt)
            and statement.view is not None
            and statement.view.schemaname == "ops"
            and statement.view.relname
            in {
                "pdf_selected_product",
                "pdf_published_item",
                "pdf_published_region",
                "pdf_published_coverage",
            }
        ):
            roles = ("corpus_sem_writer", "corpus_sem_reader", "corpus_sem_evaluator")
            if statement.view.relname == "pdf_selected_product":
                roles = (*roles, "corpus_sem_admitter")
            definition = definition_from_sql(
                connection,
                prepared.excerpt(index),
                source=source,
                owner="corpus_sem_publisher",
                grants=tuple((role, "SELECT", False) for role in roles),
            )
            definitions[definition.identity] = definition
    if len(definitions) != 4:
        raise NativeAuthoringError(f"{source}: current published view declaration is absent")
    return tuple(definitions.values())


def _execution_task_definitions(connection, function_sql, trigger_sql, *, source):
    """Own the existing guard and its declared dependent trigger together."""
    definitions = []
    owner = semantic_namespace_owner(connection)
    for sql, kind in ((function_sql, "function"), (trigger_sql, "trigger")):
        prepared = prepare_sql(sql, source=source)
        for index, raw in enumerate(prepared.statements):
            statement = raw.stmt
            selected = (
                kind == "function"
                and isinstance(statement, ast.CreateFunctionStmt)
                and tuple(part.sval for part in statement.funcname or ())
                == ("ops", "guard_execution_task")
            ) or (
                kind == "trigger"
                and isinstance(statement, ast.CreateTrigStmt)
                and statement.trigname == "zz_execution_task"
                and statement.relation is not None
                and statement.relation.schemaname == "ops"
                and statement.relation.relname == "task"
            )
            if selected:
                definitions.append(
                    replace(
                        definition_from_sql(
                            connection,
                            prepared.excerpt(index),
                            source=source,
                            owner=owner,
                            # Frozen0026_admission.sql:153 grants this capability;
                            # subsequent CREATE OR REPLACE declarations retain it.
                            grants=(("corpus_sem_publisher", "EXECUTE", False),)
                            if kind == "function"
                            else (),
                        ),
                        role_bindings=(("$migration_owner", "sem_namespace_owner"),),
                        bind_owner=True,
                    )
                )
    if len(definitions) != 2:
        raise NativeAuthoringError("execution task guard requires its frozen dependent trigger")
    return tuple(definitions)


def _task_call_definition(
    connection,
    sql,
    *,
    name,
    source,
    grants=(("corpus_sem_writer", "EXECUTE", False),),
    schema="ops",
):
    """Select the existing singular ABI; overloaded owners select all explicitly."""
    return _task_call_definitions(
        connection, sql, name=name, source=source, grants=grants, schema=schema, _first_only=True
    )[0]


def _task_call_definitions(
    connection,
    sql,
    *,
    name,
    source,
    grants=(("corpus_sem_writer", "EXECUTE", False),),
    schema="ops",
    _first_only=False,
):
    """Bind every declared overload with its own normalized ABI and ACL facts."""
    definitions = []
    prepared = prepare_sql(sql, source=source)
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) == (schema, name):
            definitions.append(
                definition_from_sql(
                    connection,
                    prepared.excerpt(index),
                    source=source,
                    owner="corpus_sem_publisher",
                    grants=grants,
                )
            )
            if _first_only:
                break
    if definitions:
        return tuple(definitions)
    raise NativeAuthoringError(f"native task-call ABI declaration is absent: {name}")


def _release_guard_definitions(connection, sql, *, source):
    prepared = prepare_sql(sql, source=source)
    definitions = []
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) in {("sem", "require_archive_bytes"), ("sem", "require_execution_projection")}:
            definitions.append(
                definition_from_sql(
                    connection,
                    prepared.excerpt(index),
                    source=source,
                    owner="corpus_sem_publisher",
                )
            )
    if len(definitions) != 2:
        raise NativeAuthoringError(f"{source}: complete release guards are absent")
    return tuple(definitions)


# Only these retired entry points leave the current runtime. Their definitions are
# recovered from frozen declarations, never adopted from a deployed catalog.
_RETIRED_SOURCE_FUNCTIONS = frozenset(
    {
        ("kb", "check_offsets"),
        ("data", "structural_public_statement"),
        ("ops", "dossier_contribution_members"),
        ("eval", "assign_document_split"),
        *(
            ("eval", name)
            for name in (
                "add_reference_unit",
                "record_reference_evaluation",
                "record_reference_pass",
                "relocate_reference_frame",
                "reference_snapshot",
            )
        ),
        *(
            ("ops", name)
            for name in (
                "parsing_origin_known",
                "publish_integrated_pdf",
                "publish_layered_parsing_product",
                "publish_native_document",
                "publish_parsing_product",
                "publish_pdf_inline_reports",
                "record_source_frame",
                "register_native_pdf",
                "register_parsing_source",
                "require_parsing_product",
                "source_locator_segment",
                "source_statement_locator",
                "validate_pdf_ocr_pages",
                "legacy_integrated_source_context",
                "integrated_source_context",
            )
        ),
    }
)
_CURRENT_SOURCE_GUARDS = {
    ("eval", "create_reference_set"): "closure.sql",
    ("data", "begin_stage"): "transport.sql",
    ("data", "publish_contract_batch"): "transport.sql",
    ("data", "end_stage"): "closure.sql",
    ("data", "validate_state"): "source_record_graph.sql",
    ("data", "publish_batch"): "record_publication.sql",
    ("eval", "guard_scientific_decisions"): "execution_projection.sql",
    ("sem", "require_execution_operation"): "execution_projection.sql",
    ("ops", "guard_task_method_contract"): "current_operation_guards.sql",
    ("ops", "require_atomic_evaluation"): "current_operation_guards.sql",
    ("data", "is_bound_statement"): "closure.sql",
    ("data", "publish_derived_batch_v2"): "derived_publication.sql",
    ("data", "check_evidence_source"): "closure.sql",
    ("data", "validate_occurrence_context"): "closure.sql",
    ("data", "validate_entity_source"): "closure.sql",
    ("data", "validate_pre_inference_state"): "closure.sql",
    ("data", "finish_pre_context_evaluation"): "native_finalization.sql",
    ("data", "validate_identity_exclusions"): "exclusions.sql",
    ("ops", "guard_task_lifecycle"): "execution_guards.sql",
    ("ops", "guard_execution_run"): "execution_guards.sql",
    ("ops", "validate_measurement_definition"): "source_views.sql",
    ("ops", "add_source_task_dependency"): "source_views.sql",
    ("ops", "select_reused_source_views"): "source_views.sql",
    ("ops", "valid_reuse"): "task_dependency_scope.sql",
}


def _source_guard_predecessors(connection):
    """Normalize bounded frozen source guards/retirements and their dependent triggers."""
    from .migrations import ALEMBIC_DIR
    from .native_function_signatures import function_signature
    from .native_inventory import update_function_inventory

    owner = semantic_namespace_owner(connection)
    if owner is None:
        raise NativeAuthoringError("source guard authoring requires its semantic owner")
    inventory, functions, triggers = {}, {}, {}
    selected = (
        _RETIRED_SOURCE_FUNCTIONS
        | set(_CURRENT_SOURCE_GUARDS)
        | {("sem", "require_archive_bytes"), ("sem", "require_execution_projection")}
    )
    for path in sorted(ALEMBIC_DIR.joinpath("versions").glob("semantic_0[0-9][0-9][0-9]_*.sql")):
        sql = path.read_text().replace("__MIGRATION_OWNER__", owner)
        prepared = update_function_inventory(inventory, sql, owner=owner)
        for index, raw in enumerate(prepared.statements):
            stmt = raw.stmt
            if isinstance(stmt, ast.CreateFunctionStmt):
                name = tuple(part.sval for part in stmt.funcname or ())
                if name in selected:
                    declaration = prepared.excerpt(index)
                    if not stmt.replace:
                        declaration = declaration.replace(
                            "CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1
                        )
                    functions[function_signature(stmt)] = (path.name, declaration)
            elif isinstance(stmt, ast.CreateTrigStmt):
                name = tuple(part.sval for part in stmt.funcname or ())
                if name in selected:
                    definition = definition_from_sql(
                        connection,
                        prepared.excerpt(index),
                        source=path.name,
                    )
                    from .native_catalog import relation_owner

                    parent = definition.identity.schema + "." + str(definition.identity.relation)
                    parent_owner = connection.scalar(relation_owner(parent))
                    if parent_owner is None and parent not in metadata.tables:
                        continue  # Its explicitly retired table already left this realization.
                    if parent_owner not in {owner, "corpus_sem_publisher"}:
                        raise NativeAuthoringError(
                            "source trigger has an unsupported owning relation"
                        )
                    definition = replace(definition, owner=parent_owner)
                    if parent_owner == owner:
                        definition = replace(
                            definition,
                            bind_owner=True,
                            role_bindings=(("$migration_owner", "sem_namespace_owner"),),
                        )
                    triggers[definition.identity] = (name, definition)
    definitions = []
    for signature, (source, sql) in functions.items():
        if signature not in inventory:
            continue  # The frozen source explicitly removed that overload.
        facts = inventory[signature]
        # Frozen0017 executes its routine suffix under the publisher in the Python
        # wrapper (0017_entity_source.py), outside the SQL file's own role statements.
        # Carry that declared context when this existing guard first becomes managed.
        if (
            source == "semantic_0017_entity_source.sql"
            and signature == "data.validate_entity_source(text,text)"
        ):
            facts = {**facts, "owner": "corpus_sem_publisher"}
        definition = definition_from_sql(
            connection,
            sql,
            source=source,
            owner=facts["owner"],
            grants=tuple((role, "EXECUTE", False) for role in facts["execute_roles"]),
        )
        if (definition.identity.schema, definition.identity.name) in {
            ("sem", "require_archive_bytes"),
            ("sem", "require_execution_projection"),
            ("sem", "require_execution_operation"),
        }:
            # Frozen0033 creates these under the migration owner before the later
            # publisher-owned replacements; CREATE OR REPLACE retains that EXECUTE.
            definition = replace(
                definition,
                grants=(*definition.grants, (owner, "EXECUTE", False)),
                role_bindings=(("$migration_owner", "sem_namespace_owner"),),
            )
        if definition.owner == owner:
            definition = replace(
                definition,
                bind_owner=True,
                role_bindings=(("$migration_owner", "sem_namespace_owner"),),
            )
        definitions.append(definition)
    definitions.extend(item for _, item in triggers.values())
    return tuple(definitions), triggers


def _current_source_guard_definitions(connection):
    predecessors, triggers = _source_guard_predecessors(connection)
    result = []
    for item in predecessors:
        key = (item.identity.schema, item.identity.name)
        if item.identity.kind != "function" or key not in _CURRENT_SOURCE_GUARDS:
            continue
        path = Path(__file__).with_name("sql").joinpath(_CURRENT_SOURCE_GUARDS[key])
        if path.name == "transport.sql":
            from .routines import transport_sql

            sql = transport_sql("corpus_sem_writer")
        elif key == ("data", "end_stage"):
            from .routines import stage_disposal_sql

            sql = path.read_text().replace("{transport_disposal}", stage_disposal_sql())
        elif key == ("data", "validate_pre_inference_state"):
            from .routines import stage_verification_sql

            sql = path.read_text().replace(
                "{typed_value_stage_verify}", stage_verification_sql("typed_value")
            )
        elif path.name == "derived_publication.sql":
            from .native_products import derived_publication_sql

            sql = derived_publication_sql()
        else:
            sql = path.read_text()
        prepared = prepare_sql(sql, source=path.name)
        declaration = next(
            prepared.excerpt(index)
            for index, raw in enumerate(prepared.statements)
            if isinstance(raw.stmt, ast.CreateFunctionStmt)
            and tuple(part.sval for part in raw.stmt.funcname or ()) == key
        )
        result.append(replace(item, sql=declaration, source=path.name + ":current source custody"))
    result.extend(item for name, item in triggers.values() if name in _CURRENT_SOURCE_GUARDS)
    return tuple(result)


def series_predecessor_definitions(connection):
    """Bounded predecessor source; never infer desired meaning from a deployed catalog."""
    from .migrations import ALEMBIC_DIR

    path = ALEMBIC_DIR / "versions/semantic_0065_reconciliation.sql"
    sql = path.read_text()
    guard = ALEMBIC_DIR / "versions/semantic_0053_positioned_syntax.sql"
    trigger = ALEMBIC_DIR / "versions/semantic_0023_execution.sql"
    completion = ALEMBIC_DIR / "versions/semantic_0050_native_evidence.sql"
    direction = ALEMBIC_DIR / "versions/semantic_0029_reference_boundaries.sql"
    return (
        _shape_definition(connection, sql, source=path.name),
        _context_definition(connection, sql, source=path.name),
        *_pdf_payload_definitions(connection, sql, source=path.name),
        *_publication_view_definitions(connection, sql, source=path.name),
        *_execution_task_definitions(
            connection,
            guard.read_text(),
            trigger.read_text(),
            source="frozen0053/0023 execution task",
        ),
        _task_call_definition(
            connection, guard.read_text(), name="claim_tasks", source="frozen0053 claim"
        ),
        _task_call_definition(
            connection, sql, name="select_source_view", source="frozen0065 source selection"
        ),
        _task_call_definition(
            connection, completion.read_text(), name="complete_task", source="frozen0050 complete"
        ),
        _task_call_definition(
            connection,
            direction.read_text(),
            name="record_direction",
            source="frozen0029 direction",
        ),
    )


def series_native_definitions(connection, *, include_selected=True):
    from .pdf_integrated_native import observation_publication_sql
    from .pdf_publication_native import (
        _native_shape_guard,
        pdf_record_logical_identity_sql,
        publication_sql,
        source_view_sql,
    )
    from .pdf_staging_native import stage_native_sql
    from .published_document import published_reader_definitions

    access_sql = Path(__file__).with_name("sql") / "pdf_record_access_correspondence.sql"
    payload_sql = (
        stage_native_sql()
        + "\n"
        + publication_sql()
        + "\n"
        + pdf_record_logical_identity_sql()
        + "\n"
        + access_sql.read_text()
        + "\n"
        + source_view_sql()
        + "\n"
        + observation_publication_sql()
    )
    definitions = [
        *_release_guard_definitions(
            connection,
            Path(__file__).with_name("sql").joinpath("closure.sql").read_text()
            + "\n"
            + Path(__file__)
            .with_name("sql")
            .joinpath("execution_projection_check.sql")
            .read_text(),
            source="current release guards",
        ),
        _shape_definition(connection, _native_shape_guard(), source="native-record-shape:forward"),
        _context_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("pdf_record_context.sql").read_text(),
            source="pdf_record_context.sql:forward",
        ),
        *companion_projection_definitions(connection),
        *published_reader_definitions(connection),
        *_pdf_payload_definitions(connection, payload_sql, source="pdf-payloads:forward"),
        *_publication_view_definitions(
            connection, payload_sql, source="pdf-published-views:forward"
        ),
    ]
    from .migrations import ALEMBIC_DIR

    definitions.extend(
        _execution_task_definitions(
            connection,
            Path(__file__).with_name("sql").joinpath("execution_guards.sql").read_text(),
            ALEMBIC_DIR.joinpath("versions/semantic_0023_execution.sql").read_text(),
            source="execution task:forward",
        )
    )
    definitions.append(
        _task_call_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("execution_projection.sql").read_text(),
            name="claim_tasks",
            source="native claim:forward",
        )
    )
    from .native_consumer_native import native_task_completion_sql

    record_publication = (
        Path(__file__).with_name("sql").joinpath("record_publication.sql").read_text()
    )
    reference_sql = Path(__file__).with_name("sql").joinpath("record_references.sql").read_text()
    reuse_sql = Path(__file__).with_name("sql").joinpath("task_dependency_scope.sql").read_text()
    for name in ("task_dependency_scope",):
        definitions.append(
            _task_call_definition(
                connection, reuse_sql, name=name, source="operation-scoped reuse:forward"
            )
        )
    split_sql = Path(__file__).with_name("sql").joinpath("split_decisions.sql").read_text()
    runtime_sql = Path(__file__).with_name("sql").joinpath("runtime_bindings.sql").read_text()
    for schema, name, grants in (
        ("sem", "validate_runtime_binding", ()),
        ("sem", "register_runtime_binding", (("corpus_sem_writer", "EXECUTE", False),)),
        ("sem", "require_runtime_binding", ()),
        ("ops", "create_run", (("corpus_sem_writer", "EXECUTE", False),)),
    ):
        definitions.append(
            _task_call_definition(
                connection,
                runtime_sql,
                name=name,
                schema=schema,
                grants=grants,
                source="runtime binding custody:forward",
            )
        )
    definitions.append(
        _task_call_definition(
            connection,
            split_sql,
            name="assign_document_split_decision",
            source="split decisions:forward",
            schema="eval",
            grants=(("corpus_sem_evaluator", "EXECUTE", False),),
        )
    )
    definitions.append(
        _task_call_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("closure.sql").read_text(),
            name="has_record_assertion_support",
            schema="data",
            source="direct reading support:forward",
            grants=(),
        )
    )
    # The SQL correctness overload resolves this dependency at CREATE time.
    definitions.append(
        _task_call_definition(
            connection,
            reference_sql,
            name="record_reference_comparison_record",
            source="source record comparison:forward",
            schema="eval",
            grants=(),
        )
    )
    policy_sql = Path(__file__).with_name("sql").joinpath("record_policy.sql").read_text()
    for schema, name, roles in (
        ("eval", "record_policy_prediction_frame", ("corpus_sem_evaluator",)),
        ("eval", "record_policy_field_meaning", ()),
        ("eval", "record_policy_field_evidence", ()),
        ("eval", "record_policy_full_correct", ()),
        ("eval", "validate_record_policy_product", ()),
        ("sem", "require_record_policy_binding", ()),
    ):
        definitions.extend(
            _task_call_definitions(
                connection,
                policy_sql,
                name=name,
                schema=schema,
                source="record policy:forward",
                grants=tuple((role, "EXECUTE", False) for role in roles),
            )
        )
    reference_roles = {
        "record_reference_contract": (),
        "validate_reference_source_scope": (),
        "record_reference_physical_source": (),
        "record_reference_applicability": ("corpus_sem_evaluator",),
        "record_reference_unit_binding": ("corpus_sem_evaluator",),
        "record_reference_anchor_allowed": (),
        "assign_record_reference_origin": ("corpus_sem_evaluator",),
        "record_reference_source_binding": ("corpus_sem_evaluator",),
        "create_source_record_reference_set": ("corpus_sem_evaluator",),
        "validate_source_record_reference_frame": (),
        "record_source_record_reference_pass": ("corpus_sem_evaluator",),
        "source_record_gap_evidence": ("corpus_sem_evaluator",),
        "validate_source_record_reference_evaluation": (),
        "record_source_record_reference_evaluation": ("corpus_sem_evaluator",),
        "require_record_fitting_principal": ("corpus_sem_fitter",),
        "read_record_fitting_references": ("corpus_sem_fitter",),
        "source_record_author_packet": ("corpus_sem_evaluator",),
    }
    for name, roles in reference_roles.items():
        definitions.extend(
            _task_call_definitions(
                connection,
                reference_sql,
                name=name,
                source="source record references:forward",
                grants=tuple((role, "EXECUTE", False) for role in roles),
                schema="eval",
            )
        )
    operation_assessment_sql = (
        Path(__file__).with_name("sql").joinpath("operation_assessment.sql").read_text()
    )
    for name, roles in {
        "create_operation_reference_set": ("corpus_sem_evaluator",),
        "validate_operation_reference_frame": (),
        "record_operation_reference_pass": ("corpus_sem_evaluator",),
        "operation_author_packet": ("corpus_sem_evaluator",),
        "validate_operation_reference_evaluation": (),
        "record_operation_reference_evaluation": ("corpus_sem_evaluator",),
        "operation_review_export": ("corpus_sem_evaluator",),
    }.items():
        definitions.extend(
            _task_call_definitions(
                connection,
                operation_assessment_sql,
                name=name,
                source="operation assessment:forward",
                schema="eval",
                grants=tuple((role, "EXECUTE", False) for role in roles),
            )
        )
    from corpus_structure.evaluate.operation_fitting import operation_event_fitting_native_sql

    for name, roles in {
        "operation_event_fit_frame": ("corpus_sem_evaluator", "corpus_sem_fitter"),
        "record_operation_event_fit": ("corpus_sem_evaluator", "corpus_sem_fitter"),
        "read_operation_event_fit": (
            "corpus_sem_evaluator",
            "corpus_sem_fitter",
        ),
    }.items():
        definitions.extend(
            _task_call_definitions(
                connection,
                operation_event_fitting_native_sql(),
                name=name,
                source="operation event fitting:forward",
                schema="eval",
                grants=tuple((role, "EXECUTE", False) for role in roles),
            )
        )
    definitions.extend(
        _task_call_definitions(
            connection,
            operation_event_fitting_native_sql(),
            name="read_operation_event_parameters",
            source="ordinary operation fit parameters:forward",
            schema="ops",
            grants=tuple(
                (role, "EXECUTE", False)
                for role in ("corpus_sem_reader", "corpus_sem_evaluator", "corpus_sem_fitter")
            ),
        )
    )
    review_sql = Path(__file__).with_name("sql").joinpath("review_assessments.sql").read_text()
    for name in (
        "review_history_preflight",
        "operation_review_history_bounded",
        "structural_review_history_bounded",
        "operation_review_history",
        "record_review_exposure",
        "create_structural_reference_set",
        "record_structural_reference_pass",
        "structural_review_history",
        "record_structural_review_exposure",
        "record_feature_fit_review_exposure",
    ):
        definitions.extend(
            _task_call_definitions(
                connection,
                review_sql,
                name=name,
                source="operation review history:forward",
                schema="eval",
                grants=()
                if name == "review_history_preflight"
                else (("corpus_sem_evaluator", "EXECUTE", False),),
            )
        )
    definitions.append(
        _task_call_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("source_views.sql").read_text(),
            name="select_source_view",
            source="original source selection:forward",
            schema="ops",
        )
    )
    dossier_sql = Path(__file__).with_name("sql").joinpath("dossier_contributions.sql").read_text()
    for name in (
        "retained_contribution_roots",
        "resolve_retained_source_contributions",
        "resolve_retained_source_contribution",
        "dossier_contribution_member_from_retained",
        "dossier_contribution_member",
        "dossier_contribution_members",
    ):
        definitions.extend(
            _task_call_definitions(
                connection,
                dossier_sql,
                name=name,
                source="dossier source contributions:forward",
                schema="ops",
                grants=tuple(
                    (role, "EXECUTE", False) for role in ("corpus_sem_reader", "corpus_sem_writer")
                )
                if name == "resolve_retained_source_contribution"
                else (),
            )
        )
    structural_sql = Path(__file__).with_name("sql").joinpath("structural_products.sql").read_text()
    for name in (
        "validate_structural_source",
        "validate_structural_input",
        "resolve_retained_component",
        "resolve_retained_structural_report",
        "resolve_retained_relationship_decision",
        "validate_component_targets",
        "component_semantic_target",
        "artifact_alias_fields",
        "artifact_alias_span_source_value",
        "artifact_source_records",
        "artifact_external_nominations",
        "artifact_lexical_score",
        "validate_artifact_identity",
        "structural_threshold_field",
        "structural_compare_lexical",
        "comparison_literal",
        "comparison_member",
        "comparison_groups",
        "structural_grouped_comparison",
        "structural_dossier",
        "definition_role_candidates",
        "definition_model_components",
        "clause_model_axis",
        "validate_clause_classification",
        "validate_structural_product_report",
    ):
        definitions.extend(
            _task_call_definitions(
                connection,
                structural_sql,
                name=name,
                source="structural products:forward",
                schema="ops",
                grants=tuple(
                    (role, "EXECUTE", False) for role in ("corpus_sem_reader", "corpus_sem_writer")
                )
                if name
                in {
                    "validate_structural_source",
                    "validate_structural_input",
                    "resolve_retained_component",
                    "resolve_retained_structural_report",
                    "resolve_retained_relationship_decision",
                    "validate_component_targets",
                    "component_semantic_target",
                }
                else (),
            )
        )
    for name in (
        "source_contribution_occurrence",
        "validate_source_anchor_coordinates",
        "validate_source_table_note_scope",
        "predicate_role_anchor_match",
        "predicate_cue_host_matches",
        "predicate_token_texts",
        "predicate_cue_recipe_matches",
        "predicate_cross_block_host_matches",
        "validate_source_predicates",
        "validate_witnessed_formula_links",
        "validate_named_source_links",
        "named_link_nominal",
        "validate_named_annotation_links",
        "validate_scope_inheritance",
        "clause_model_concordance",
        "validate_source_contribution_report",
        "project_source_contributions",
        "contextual_identity_value",
        "contextual_nullable_value",
        "contextual_component_section",
        "contextual_section_headings",
        "validate_contextual_selection",
    ):
        definitions.extend(
            _task_call_definitions(
                connection,
                native_task_completion_sql(),
                name=name,
                source="independent contributions:forward",
                grants=tuple(
                    (role, "EXECUTE", False) for role in ("corpus_sem_reader", "corpus_sem_writer")
                )
                if name in {"contextual_component_section", "contextual_section_headings"}
                else (),
            )
        )
    for name in (
        "record_feature_score",
        "record_source_float",
        "record_source_json",
        "record_json_meaning",
        "validate_record_admission_overlay",
        "validate_record_reading_cut",
        "validate_source_record_structure",
        "validate_record_relationships",
        "validate_record_projection",
        "validate_record_projection_cut",
        "validate_local_assertions",
        "local_semantic_grade_evidence",
        "local_semantic_case_matches",
        "local_semantic_assertion_value",
        "local_semantic_publication_candidates",
        "validate_local_semantic_assertions",
    ):
        definitions.append(
            _task_call_definition(
                connection,
                record_publication,
                name=name,
                source="record publication:forward",
                grants=(("corpus_sem_writer", "EXECUTE", False),)
                if name == "local_semantic_publication_candidates"
                else (),
                schema="data",
            )
        )

    definitions.append(
        _task_call_definition(
            connection,
            native_task_completion_sql(),
            name="validate_source_record_coordinates",
            source="source record coordinates:forward",
            grants=(),
        )
    )
    definitions.append(
        _task_call_definition(
            connection,
            native_task_completion_sql(),
            name="validate_source_record_report",
            source="source record custody:forward",
            grants=(),
        )
    )
    definitions.append(
        _task_call_definition(
            connection,
            native_task_completion_sql(),
            name="record_captured_recognition_text",
            source="captured recognition:forward",
            grants=tuple(
                (role, "EXECUTE", False)
                for role in ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
            ),
        )
    )
    definitions.append(
        _task_call_definition(
            connection,
            native_task_completion_sql(),
            name="complete_task",
            source="native completion:forward",
        )
    )
    definitions.append(
        _task_call_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("directions.sql").read_text(),
            name="record_direction",
            source="native direction:forward",
        )
    )
    from .native_sql_body import published_revision_definition, published_validation_definition

    definitions = [
        published_revision_definition(item)
        if item.identity.schema == "ops" and item.identity.name == "read_pdf_published_revision"
        else published_validation_definition(item)
        if item.identity.schema == "ops" and item.identity.name == "read_pdf_published_validation"
        else item
        for item in definitions
    ]
    # SQL-language readers resolve their provider and PL/pgSQL declarations resolve
    # the view's composite type during CREATE, after the managed scope was dropped.
    providers = (
        "read_pdf_published_revision",
        "pdf_selected_product",
        "pdf_published_item",
        "pdf_published_region",
        "pdf_published_coverage",
    )
    definitions = [
        *(item for name in providers for item in definitions if item.identity.name == name),
        *(item for item in definitions if item.identity.name not in providers),
    ]
    if include_selected:
        from .pdf_selected_source_native import selected_source_reader_sql

        prepared = prepare_sql(selected_source_reader_sql(), source="selected-source-v1")
        for index, statement in enumerate(prepared.statements):
            if isinstance(statement.stmt, ast.CreateFunctionStmt):
                definitions.append(
                    definition_from_sql(
                        connection,
                        prepared.excerpt(index),
                        source="selected-source-v1",
                        owner="corpus_sem_publisher",
                        grants=tuple(
                            (role, "EXECUTE", False)
                            for role in (
                                "corpus_sem_reader",
                                "corpus_sem_writer",
                                "corpus_sem_evaluator",
                            )
                        ),
                    )
                )
    definitions.extend(_current_source_guard_definitions(connection))
    structural_publication = (
        Path(__file__).with_name("sql").joinpath("structural_publication.sql").read_text()
    )
    for name in (
        "structural_citation",
        "structural_citations",
        "structural_definition_component",
        "retained_definition_citations",
        "structural_public_clause_field",
        "structural_public_statement",
        "structural_publication_candidates",
        "validate_structural_assertions",
    ):
        definitions.append(
            _task_call_definition(
                connection,
                structural_publication,
                name=name,
                source="structural publication:forward",
                schema="data",
                grants=(("corpus_sem_writer", "EXECUTE", False),)
                if name == "structural_publication_candidates"
                else (),
            )
        )
    from .record_projection import RECORD_ROW_TYPES

    # Accepted record rows and origin assignments are append-only, like existing
    # public semantic content. The guard joins the same managed native lifecycle.
    for relation in (
        "sem.runtime_binding",
        "data.local_assertion",
        "data.local_semantic_assertion",
        "data.structural_assertion",
        *("data." + name for name in RECORD_ROW_TYPES),
        "kb.source_contribution_operation",
        "kb.source_contribution",
        "kb.source_contribution_endpoint",
        "kb.source_contribution_anchor",
        "eval.reference_origin_group",
        "eval.reference_origin_source",
    ):
        definitions.append(
            definition_from_sql(
                connection,
                "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON "
                + relation
                + " FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation()",
                source="record immutability:forward",
                owner="corpus_sem_publisher",
            )
        )
    return tuple(definitions)


def _admission_definitions(connection, sql, *, source):
    prepared = prepare_sql(sql, source=source)
    definitions = []
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        name = tuple(part.sval for part in statement.funcname or ())
        if name not in {
            ("data", "execution_contract_descriptor"),
            ("data", "require_execution_release"),
        }:
            continue
        roles = (
            ("corpus_sem_admitter",)
            if name[1] == "execution_contract_descriptor"
            else (
                "corpus_sem_writer",
                "corpus_sem_reader",
                "corpus_sem_evaluator",
                "corpus_sem_admitter",
            )
        )
        if name[1] == "require_execution_release":
            # Frozen 0026_admission.sql:373 grants EXECUTE to __MIGRATION_OWNER__.
            # Later CREATE OR REPLACE declarations retain this explicit historical
            # capability. The guard itself resolves owner_name through sem.nspowner.
            migration_owner = semantic_namespace_owner(connection)
            if migration_owner is None:
                raise NativeAuthoringError("native admission requires its semantic namespace owner")
            roles = tuple(dict.fromkeys((*roles, migration_owner)))
        definition = definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source + ":" + name[1],
            owner="corpus_sem_publisher",
            grants=tuple((role, "EXECUTE", False) for role in roles),
        )
        if name[1] == "require_execution_release":
            definition = replace(
                definition, role_bindings=(("$migration_owner", "sem_namespace_owner"),)
            )
        definitions.append(definition)
    if len(definitions) != 2:
        raise NativeAuthoringError(
            f"{source}: admission requires its descriptor and enforcing guard"
        )
    return tuple(definitions)


def candidate_admission_sql(
    connection,
    products,
    native_objects,
    *,
    retire=frozenset(),
    predecessor=None,
    predecessor_state: Path | None = None,
    predecessor_source=None,
    target_metadata=metadata,
):
    from .contracts import compile_execution_model, trusted_execution_inputs
    from .native_products import current_authoring_provenance
    from .source_view_native import native_admission_sql

    # A descriptor cannot include its own body hash. The enforcing guard is not
    # self-referential: its source is independent of the descriptor literal.
    selected = tuple(
        item
        for item in native_objects
        if (item.identity.schema, item.identity.name) != ("data", "execution_contract_descriptor")
    )
    source = predecessor_source or _predecessor_source(
        connection, predecessor=predecessor, predecessor_state=predecessor_state
    )
    desired = {item.identity for item in selected}
    physical_sources = target_metadata.info.get("physical_sources")
    execution = (
        compile_execution_model(trusted_execution_inputs(physical_sources=physical_sources))
        if physical_sources
        else None
    )
    return native_admission_sql(
        definition_sql(products),
        model=execution,
        base_admission=source.admission,
        authoring_provenance=current_authoring_provenance(execution),
        native_objects=selected,
        target_metadata=target_metadata,
        retire=retire | (source.retirements - desired),
    )


def load_native_state(path: Path, *, digest: str | None = None) -> tuple[NativeObject, ...]:
    content = path.read_bytes()
    if digest is not None and sha256(content).hexdigest() != digest:
        raise NativeAuthoringError(f"{path.name}: native predecessor state digest differs")
    return _parse_native_state(content, path)[0]


def _parse_native_state(content: bytes, path: Path):
    try:
        payload = json.loads(content)
        if payload["version"] != 1 or not isinstance(payload["desired"], list):
            raise ValueError("unsupported native state format")
        objects = tuple(NativeObject.from_payload(value) for value in payload["desired"])
        if len({item.identity for item in objects}) != len(objects):
            raise ValueError("duplicate native identity")
        if "operations" in payload and not isinstance(payload["operations"], list):
            raise ValueError("native operations must be a list")
        return objects, payload
    except (KeyError, TypeError, ValueError) as error:
        raise NativeAuthoringError(
            f"{path.name}: invalid frozen native predecessor state: {error}"
        ) from error


def _read_revision_artifact(path: Path, digest: str) -> bytes:
    content = path.read_bytes()
    if sha256(content).hexdigest() != digest:
        raise NativeAuthoringError(f"{path.name}: frozen revision artifact digest differs")
    return content


def _current_revision_artifact(connection, filename_attribute: str, digest_attribute: str):
    """Locate only declared, hash-bound predecessor source, never a live descriptor."""
    from alembic.script import ScriptDirectory

    from .migrations import alembic_config, current_revision

    revision = current_revision(connection)
    if revision is None:
        raise NativeAuthoringError("native authoring requires a declared current revision")
    if revision == "semantic_0065":
        return None
    script = ScriptDirectory.from_config(alembic_config()).get_revision(revision)
    if script is None:
        raise NativeAuthoringError("native authoring requires a declared current revision")
    filename = getattr(script.module, filename_attribute, None)
    digest = getattr(script.module, digest_attribute, None)
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not isinstance(digest, str)
    ):
        raise NativeAuthoringError(
            "current revision lacks frozen native artifact: " + filename_attribute
        )
    return Path(script.path).parent / filename, digest


def current_native_state(connection, explicit: Path | None = None):
    """Read the current revision's declared immutable desired state, never live adoption."""
    if explicit is not None:
        return load_native_state(explicit)
    source = _current_revision_artifact(connection, "NATIVE_STATE_FILE", "NATIVE_STATE_SHA256")
    return None if source is None else load_native_state(source[0], digest=source[1])


@dataclass(frozen=True)
class _PredecessorSource:
    objects: tuple[NativeObject | NativeDefinition, ...] | None
    admission: str
    retirements: frozenset[NativeIdentity] = frozenset()

    def permits_backfill(self, identity: NativeIdentity) -> bool:
        if identity in self.retirements:
            return False
        if identity.kind == "trigger":
            from .source_view_native import _admission_descriptor

            return identity.schema + "." + str(identity.relation) in set(
                _admission_descriptor(self.admission)["physical_relations"]
            )
        if identity.kind != "function":
            return True
        from .source_view_native import _admission_descriptor

        return identity.qualified in {
            item["signature"] for item in _admission_descriptor(self.admission)["functions"]
        }


def _predecessor_source(connection, *, predecessor=None, predecessor_state=None):
    """Keep transitions and admission on one declared predecessor authority."""
    from .migrations import ALEMBIC_DIR
    from .source_view_native import _admission_descriptor

    if predecessor is not None and predecessor_state is not None:
        raise NativeAuthoringError(
            "select source predecessors or a frozen predecessor state, not both"
        )
    state = None
    if predecessor is not None:
        objects = tuple(predecessor)
        admission = None
    elif predecessor_state is not None:
        objects, state = _parse_native_state(predecessor_state.read_bytes(), predecessor_state)
        admission = None
    else:
        state_source = _current_revision_artifact(
            connection, "NATIVE_STATE_FILE", "NATIVE_STATE_SHA256"
        )
        if state_source is None:
            return _PredecessorSource(
                None, ALEMBIC_DIR.joinpath("versions/semantic_0065_admission.sql").read_text()
            )
        content = _read_revision_artifact(*state_source)
        objects, state = _parse_native_state(content, state_source[0])
        admission_source = _current_revision_artifact(
            connection, "NATIVE_ADMISSION_FILE", "NATIVE_ADMISSION_SHA256"
        )
        if admission_source is None:
            raise NativeAuthoringError("native predecessor admission source is absent")
        admission = _read_revision_artifact(*admission_source).decode()
    declared_admission = tuple(
        item
        for item in objects
        if (item.identity.schema, item.identity.name)
        in {("data", "execution_contract_descriptor"), ("data", "require_execution_release")}
    )
    if len(declared_admission) != 2:
        raise NativeAuthoringError(
            "explicit native predecessor must include its descriptor and enforcing guard"
        )
    state_admission = "\n".join(
        statement.rstrip(";\n") + ";"
        for item in declared_admission
        for statement in (item.statements if isinstance(item, NativeObject) else item.install_sql)
    )
    if admission is not None and (
        _admission_descriptor(admission) != _admission_descriptor(state_admission)
    ):
        raise NativeAuthoringError("frozen native state and admission descriptor differ")
    retirements = (
        frozenset()
        if state is None
        else frozenset(
            NativeIdentity.from_payload(item["before"]["identity"])
            for item in state.get("operations", ())
            if item["after"] is None and item["before"] is not None
        )
    )
    return _PredecessorSource(objects, admission or state_admission, retirements)


def _order_physical_retirement(upgrade_ops):
    """Remove FK dependencies before native replacement and stored relation retirement."""
    from alembic.operations import ops

    from .alembic_native import NativeTransitionOp

    native = [item for item in upgrade_ops.ops if isinstance(item, NativeTransitionOp)]
    drops = [item for item in upgrade_ops.ops if isinstance(item, ops.DropTableOp)]
    ordinary = [
        item
        for item in upgrade_ops.ops
        if not isinstance(item, (NativeTransitionOp, ops.DropTableOp))
    ]
    constraints = []
    for item in drops:
        # Alembic's reflected table ordering may contain cycles. These constraints
        # leave with their explicitly removed table, so retire their edges first.
        relation = item.to_table()
        constraints.extend(
            ops.DropConstraintOp.from_constraint(constraint)
            for constraint in sorted(
                relation.foreign_key_constraints, key=lambda constraint: str(constraint.name)
            )
        )
    upgrade_ops.ops[:] = [*ordinary, *constraints, *native, *drops]


def _prepare_series_authoring(
    connection,
    *,
    predecessor=None,
    predecessor_state: Path | None = None,
    retire=frozenset(),
    recreate=frozenset(),
    include_selected=True,
    target_metadata=metadata,
    owned_authoring=False,
):
    """Normalize native definitions against the authoring transaction row types."""
    products = series_native_definitions(connection, include_selected=include_selected)
    source = _predecessor_source(
        connection, predecessor=predecessor, predecessor_state=predecessor_state
    )
    frozen_before = source.objects
    if frozen_before is not None:
        product_predecessor = tuple(
            item
            for item in frozen_before
            if (item.identity.schema, item.identity.name)
            not in {
                ("data", "execution_contract_descriptor"),
                ("data", "require_execution_release"),
            }
        )
    else:
        product_predecessor = series_predecessor_definitions(connection)
    if frozen_before is not None:
        known = {item.identity for item in product_predecessor}
        desired = {item.identity for item in products}
        newly_managed = tuple(
            item
            for item in series_predecessor_definitions(connection)
            if item.identity not in known
            and item.identity in desired
            and source.permits_backfill(item.identity)
        )
        if newly_managed:
            # Normalization uses frozen declarations, never adoption of deployed
            # bodies. The transition still refuses an unexpected live predecessor.
            normalized = prepare_native_authoring(
                connection, newly_managed, owned_authoring=owned_authoring
            ).desired
            product_predecessor = (*product_predecessor, *normalized)
    if frozen_before is not None:
        extra, _ = _source_guard_predecessors(connection)
        known = {item.identity for item in product_predecessor}
        extra = tuple(
            item
            for item in extra
            if item.identity not in known and source.permits_backfill(item.identity)
        )
        if extra:
            normalized = prepare_native_authoring(
                connection, extra, owned_authoring=owned_authoring
            ).desired
            product_predecessor = (*product_predecessor, *normalized)
    desired_identities = {item.identity for item in products}
    retired_source = frozenset(
        item.identity
        for item in product_predecessor
        if item.identity not in desired_identities
        and (
            (item.identity.schema, item.identity.name) in _RETIRED_SOURCE_FUNCTIONS
            or item.identity.kind == "trigger"
        )
    )
    retire = retire | retired_source
    product_authoring = prepare_native_authoring(
        connection,
        products,
        predecessor=product_predecessor,
        retire=retire,
        recreate=recreate,
        owned_authoring=owned_authoring,
    )
    admission_before = (
        tuple(
            item
            for item in frozen_before
            if (item.identity.schema, item.identity.name)
            in {("data", "execution_contract_descriptor"), ("data", "require_execution_release")}
        )
        if frozen_before is not None
        else _admission_definitions(
            connection,
            source.admission,
            source="semantic_0065_admission.sql",
        )
    )
    if len(admission_before) != 2:
        raise NativeAuthoringError(
            "frozen native state must include its descriptor and enforcing guard"
        )
    first_admission = candidate_admission_sql(
        connection,
        products,
        product_authoring.desired,
        retire=retire,
        predecessor_source=source,
        target_metadata=target_metadata,
    )
    guard_definition = next(
        item
        for item in _admission_definitions(
            connection, first_admission, source="native-admission:forward"
        )
        if item.identity.name == "require_execution_release"
    )
    old_guard = next(
        item for item in admission_before if item.identity.name == "require_execution_release"
    )
    guard_authoring = prepare_native_authoring(
        connection,
        (guard_definition,),
        predecessor=(old_guard,),
        owned_authoring=owned_authoring,
    )
    admission = candidate_admission_sql(
        connection,
        products,
        (*product_authoring.desired, *guard_authoring.desired),
        retire=retire,
        predecessor_source=source,
        target_metadata=target_metadata,
    )
    admission_after = _admission_definitions(
        connection, admission, source="native-admission:forward"
    )
    authoring = prepare_native_authoring(
        connection,
        (*products, *admission_after),
        predecessor=(*product_predecessor, *admission_before),
        retire=retire,
        recreate=recreate,
        owned_authoring=owned_authoring,
    )
    return authoring


def _physical_check_contract(connection, target_metadata, authoring):
    """Normalize declared CHECKs through PostgreSQL, never enroll live table drift."""
    from sqlalchemy import CheckConstraint

    from .source_view_native import _admission_descriptor

    descriptor = next(
        item for item in authoring.desired if item.identity.name == "execution_contract_descriptor"
    )
    expected = _admission_descriptor(
        "\n".join(statement.rstrip(";\n") + ";" for statement in descriptor.statements)
    )
    present = connection.scalar(
        text("SELECT source_digest FROM sem.physical_contract WHERE physical_id=:physical"),
        {"physical": expected["physical_id"]},
    )
    if present is not None:
        if present != expected["physical_checks_source_digest"]:
            raise NativeAuthoringError(
                "physical CHECK identity already has another source contract"
            )
        return None
    preparer = connection.dialect.identifier_preparer
    checks = []
    for relation in sorted(target_metadata.tables.values(), key=lambda item: item.fullname):
        constraints = sorted(
            (item for item in relation.constraints if isinstance(item, CheckConstraint)),
            key=lambda item: str(item.name),
        )
        if not constraints:
            continue
        columns = [
            preparer.quote(item.name) + " " + item.type.compile(dialect=connection.dialect)
            for item in relation.columns
        ]
        columns.extend(
            "CONSTRAINT " + preparer.format_constraint(item) + " CHECK (" + str(item.sqltext) + ")"
            for item in constraints
        )
        connection.exec_driver_sql(
            "CREATE TEMP TABLE semantic_candidate_check (" + ",".join(columns) + ") ON COMMIT DROP",
            execution_options={"no_parameters": True},
        )
        for name, expression in connection.exec_driver_sql(
            "SELECT conname,pg_get_expr(conbin,conrelid) FROM pg_constraint "
            "WHERE conrelid='pg_temp.semantic_candidate_check'::regclass AND co"
            "ntype='c' ORDER BY conname"
        ):
            checks.append(dict(relation=relation.fullname, name=name, expression=expression))
        connection.exec_driver_sql("DROP TABLE pg_temp.semantic_candidate_check")

    def literal(value):
        return "'" + value.replace("'", "''") + "'"

    return (
        "INSERT INTO sem.physical_contract(physical_id,checks,source_digest) VALUES ("
        + literal(expected["physical_id"])
        + ","
        + literal(json.dumps(checks, sort_keys=True))
        + "::jsonb,"
        + literal(expected["physical_checks_source_digest"])
        + ")"
    )


def prepare_series_candidate(
    connection,
    *,
    predecessor=None,
    predecessor_state: Path | None = None,
    retire=frozenset(),
    recreate=frozenset(),
    include_selected=True,
    target_metadata=metadata,
    owned_authoring=False,
):
    """Produce ordinary and selected native operations together; no revision/file is written."""
    if not owned_authoring:
        raise NativeAuthoringError(
            "native preparation requires an explicitly owned authoring database"
        )
    # Native triggers require their real parent row types during PostgreSQL
    # normalization. These new-table prerequisites exist only inside a savepoint;
    # rollback precedes normal Alembic comparison, so CREATEs remain explicit.
    existing = set(
        connection.scalars(
            text(
                "SELECT n.nspname || '.' || c.relname FROM pg_class c "
                "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p')"
            )
        )
    )
    new_tables = [item for item in target_metadata.sorted_tables if item.fullname not in existing]
    scaffolding = connection.begin_nested()
    try:
        previous = connection.exec_driver_sql("SELECT current_user").scalar_one()
        previous_sql = "SET LOCAL ROLE " + connection.dialect.identifier_preparer.quote(previous)
        for relation in new_tables:
            # Migration authority creates cross-owner foreign keys, including
            # evaluator tables referencing ops cuts; runtime roles need no DDL ACLs.
            connection.exec_driver_sql(previous_sql)
            target_metadata.create_all(connection, tables=[relation], checkfirst=False)
        connection.exec_driver_sql(previous_sql)
        for relation in new_tables:
            connection.exec_driver_sql(
                "ALTER TABLE "
                + connection.dialect.identifier_preparer.format_table(relation)
                + " OWNER TO corpus_sem_publisher"
            )
        # The runtime reuse kernel binds the expanded existing run row type. Like
        # new tables above, this prerequisite is rolled back before Alembic's diff.
        run = target_metadata.tables.get("ops.run")
        if (
            run is not None
            and "runtime_id" in run.c
            and connection.scalar(
                text(
                    "SELECT NOT EXISTS(SELECT FROM pg_attribute WHERE attrelid='ops.run'::regclass "
                    "AND attname='runtime_id' AND NOT attisdropped)"
                )
            )
        ):
            connection.exec_driver_sql("ALTER TABLE ops.run ADD COLUMN runtime_id text")
        authoring = _prepare_series_authoring(
            connection,
            predecessor=predecessor,
            predecessor_state=predecessor_state,
            retire=retire,
            recreate=recreate,
            include_selected=include_selected,
            target_metadata=target_metadata,
            owned_authoring=owned_authoring,
        )
        physical_contract = _physical_check_contract(connection, target_metadata, authoring)
    finally:
        scaffolding.rollback()
    context = MigrationContext.configure(
        connection,
        opts={
            "include_schemas": True,
            "include_name": lambda name, kind, parents: (
                name in SCHEMAS if kind == "schema" else True
            ),
            "compare_server_default": compare_default,
            "compare_type": compare_type,
            "autogenerate_plugins": [
                "alembic.autogenerate.*",
                "alembic.ext.checkconstraint_byname",
                defaults_plugin.name,
                indexes_plugin.name,
                native_plugin.name,
            ],
            "native_authoring": authoring,
        },
    )
    candidate = produce_migrations(context, target_metadata)
    if candidate.upgrade_ops is not None:
        from alembic.operations.ops import (
            CreateForeignKeyOp,
            CreateTableOp,
            ExecuteSQLOp,
            MigrateOperation,
            ModifyTableOps,
        )
        from sqlalchemy.schema import AddConstraint

        previous = connection.exec_driver_sql("SELECT current_user").scalar_one()
        restore = "SET LOCAL ROLE " + connection.dialect.identifier_preparer.quote(previous)
        publisher = "SET LOCAL ROLE corpus_sem_publisher"
        ordered: list[MigrateOperation] = []
        created = []
        for item in candidate.upgrade_ops.ops:
            if isinstance(item, CreateTableOp):
                created.append(item)
            if isinstance(item, ModifyTableOps) and item.schema == "eval":
                for change in item.ops:
                    if (
                        isinstance(change, CreateForeignKeyOp)
                        and change.source_table == "reference_set"
                        and change.referent_table == "run"
                        and change.kw.get("referent_schema") == "ops"
                        and change.local_cols == ["source_run_id"]
                        and change.remote_cols == ["id"]
                    ):
                        # This source-only FK crosses existing owner boundaries.
                        # Preserve a pre-existing capability; remove only the
                        # column privilege introduced for this one DDL statement.
                        foreign_key = str(
                            AddConstraint(change.to_constraint()).compile(
                                dialect=connection.dialect
                            )
                        ).replace("'", "''")
                        ordered.append(
                            ExecuteSQLOp(
                                "DO $reference_fk$ DECLARE previous_name text:=current_user; "
                                "introduced boolean:=NOT has_column_privilege("
                                "'corpus_sem_publisher','ops.run','id','REFERENCES'); BEGIN "
                                "IF introduced THEN GRANT REFERENCES(id) ON ops.run TO corpus_s"
                                "em_publisher; END IF; "
                                "SET LOCAL ROLE corpus_sem_publisher; EXECUTE '"
                                + foreign_key
                                + "'; "
                                "EXECUTE format('SET LOCAL ROLE %I',previous_name); "
                                "IF introduced THEN REVOKE REFERENCES(id) ON ops.run FROM corpu"
                                "s_sem_publisher; END IF; "
                                "END $reference_fk$"
                            )
                        )
                    else:
                        group = ModifyTableOps(item.table_name, [change], schema=item.schema)
                        ordered.extend((ExecuteSQLOp(publisher), group, ExecuteSQLOp(restore)))
            else:
                ordered.append(item)
        # Keep migration-owned FK creation intact before transferring new data
        # tables. No runtime principal receives direct mutation or reference ACLs.
        for item in created:
            relation = item.to_table()
            name = connection.dialect.identifier_preparer.format_table(relation)
            ordered.append(ExecuteSQLOp("ALTER TABLE " + name + " OWNER TO corpus_sem_publisher"))
        publisher_work: list[MigrateOperation] = []
        if physical_contract is not None:
            publisher_work.append(ExecuteSQLOp(physical_contract))
        for item in created:
            relation = item.to_table()
            name = connection.dialect.identifier_preparer.format_table(relation)
            roles = target_metadata.tables[relation.fullname].info.get(
                "read_roles",
                [
                    "corpus_sem_writer",
                    "corpus_sem_reader",
                    "corpus_sem_admitter",
                    "corpus_sem_evaluator",
                ],
            )
            if roles:
                publisher_work.append(
                    ExecuteSQLOp(
                        "GRANT SELECT ON "
                        + name
                        + " TO "
                        + ",".join(
                            connection.dialect.identifier_preparer.quote(role) for role in roles
                        )
                    )
                )
        # Fitting is protected; ordinary parameter reads use their owned ops port.
        for role in ("corpus_sem_fitter",):
            if (
                connection.scalar(
                    text("SELECT has_schema_privilege(:role,'eval','USAGE')"), {"role": role}
                )
                is not True
            ):
                publisher_work.append(ExecuteSQLOp("GRANT USAGE ON SCHEMA eval TO " + role))
        if (
            connection.scalar(
                text("SELECT has_schema_privilege('corpus_sem_reader','eval','USAGE')")
            )
            is True
        ):
            publisher_work.append(
                ExecuteSQLOp("REVOKE USAGE ON SCHEMA eval FROM corpus_sem_reader")
            )
        if publisher_work:
            ordered.extend((ExecuteSQLOp(publisher), *publisher_work, ExecuteSQLOp(restore)))
        candidate.upgrade_ops.ops[:] = ordered
        _order_physical_retirement(candidate.upgrade_ops)
    return candidate, authoring


def definition_sql(definitions) -> str:
    """Inspection/admission input; frozen revisions execute serialized native operations."""
    return "\n".join(
        statement.rstrip(";\n") + ";" for item in definitions for statement in item.install_sql
    )
