"""Captured current installation inputs for fresh roots and exact frozen successors.

This builds from the same captured LinkML sources and compiler as normal metadata.
It neither replays a historical migration nor authorizes a database transition.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import MetaData

from .types import SourceArtifact

if TYPE_CHECKING:
    from .native_products import NativeAuthoringInputs


def target_task_guard_sql(protocol: bytes, checks: str) -> str:
    """Share the existing request/lease/receipt checks, with no legacy task branch."""
    from .data_operation_protocol import render_data_task_guard

    return render_data_task_guard(
        protocol,
        """
CREATE OR REPLACE FUNCTION ops.guard_execution_task() RETURNS trigger
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $task$
BEGIN
 IF NEW.data_request_id IS NULL OR NEW.data_generation IS NULL THEN
 RAISE EXCEPTION 'physical task requires declared request generation' USING ERRCODE='23514'; END IF;
-- {data_request_task_checks}
END $task$;
""",
        checks=checks,
    )


@dataclass(frozen=True)
class TargetInstallation:
    """One exact physical/native capture; preparation grants no deployment authority."""

    metadata: MetaData
    pdf_sources: tuple[SourceArtifact, ...]
    authoring_inputs: NativeAuthoringInputs


def capture_target_installation(
    selected: MetaData, *, logical_sources: dict[str, bytes] | None = None
) -> TargetInstallation:
    from .closure_native import closure_native_sql
    from .data_operation_storage import native_logical_sources
    from .native_products import capture_native_authoring_inputs
    from .pdf_binary_identity_native import pdf_artifact_identity_sql, pdf_binary_identity_sql
    from .pdf_domain import PREFIX, pdf_domain_sources

    logical = native_logical_sources() if logical_sources is None else logical_sources
    pdf_sources = pdf_domain_sources(
        physical_sources=selected.info["physical_sources"],
        linkml_types=selected.info["physical_linkml_types"],
        actions_source=SourceArtifact(PREFIX + "native/actions.yaml", logical["pdf-actions.yaml"]),
    )
    inputs = capture_native_authoring_inputs(
        target_metadata=selected,
        pdf_sources=pdf_sources,
        logical_sources=logical,
        extra_sources=(
            SourceArtifact("authoring/target_installation.py", Path(__file__).read_bytes()),
            SourceArtifact("authoring/closure-native.sql", closure_native_sql(selected).encode()),
            SourceArtifact(
                "authoring/closure-native.py",
                Path(__file__).with_name("closure_native.py").read_bytes(),
            ),
            SourceArtifact(
                "authoring/pdf-descriptor.sql",
                Path(__file__).with_name("sql").joinpath("pdf_descriptor.sql").read_bytes(),
            ),
            SourceArtifact(
                "authoring/pdf-record-identity.sql",
                pdf_binary_identity_sql().encode(),
            ),
            SourceArtifact(
                "authoring/pdf-record-artifact-identity.sql",
                pdf_artifact_identity_sql(selected).encode(),
            ),
            SourceArtifact(
                "authoring/pdf-captured-recognition.sql",
                Path(__file__)
                .with_name("sql")
                .joinpath("source_record_recognition.sql")
                .read_bytes(),
            ),
        ),
    )
    return TargetInstallation(selected, pdf_sources, inputs)


def target_physical_prerequisites(connection, installation: TargetInstallation):
    """The table-free current function used by the PDF body CHECK declaration."""
    from .native_authoring import _task_call_definition

    source = next(
        item.content.decode()
        for item in installation.authoring_inputs.sources
        if item.name == "authoring/pdf-descriptor.sql"
    )
    return (
        _task_call_definition(
            connection,
            source,
            schema="ops",
            name="pdf_product_descriptor",
            source="target-current:PDF descriptor CHECK prerequisite",
            grants=(),
        ),
    )


def target_pdf_sql(installation: TargetInstallation) -> str:
    from .pdf_completion_native import pdf_completion_native_sql
    from .pdf_contracts import _context_from_domain
    from .pdf_domain import CONTRACT, PdfDomainContract
    from .pdf_integrated_native import observation_publication_sql
    from .pdf_publication_native import publication_sql
    from .pdf_record_access_native import pdf_access_correspondence_sql
    from .pdf_record_digest_native import pdf_record_logical_identity_sql
    from .pdf_record_proof_native import pdf_record_proof_sql
    from .pdf_selected_source_native import selected_source_reader_sql
    from .pdf_staging_native import stage_native_sql

    contract = next(source for source in installation.pdf_sources if source.name == CONTRACT)
    context = _context_from_domain(
        None,
        PdfDomainContract(
            contract.content,
            tuple(source for source in installation.pdf_sources if source.name != CONTRACT),
        ),
    )
    return "\n".join(
        (
            next(
                source.content.decode()
                for source in installation.authoring_inputs.sources
                if source.name == "authoring/pdf-record-identity.sql"
            ),
            next(
                source.content.decode()
                for source in installation.authoring_inputs.sources
                if source.name == "authoring/pdf-record-artifact-identity.sql"
            ),
            stage_native_sql(
                target_metadata=installation.metadata, pdf_sources=installation.pdf_sources
            ),
            publication_sql(target_metadata=installation.metadata, pdf_domain=context.domain),
            pdf_record_logical_identity_sql(target_metadata=installation.metadata),
            pdf_record_proof_sql(installation.metadata),
            pdf_access_correspondence_sql(installation.metadata),
            observation_publication_sql(context, target_metadata=installation.metadata),
            next(
                source.content.decode()
                for source in installation.authoring_inputs.sources
                if source.name == "authoring/pdf-captured-recognition.sql"
            ),
            pdf_completion_native_sql(installation.metadata),
            selected_source_reader_sql(
                target_metadata=installation.metadata, pdf_domain=context.domain
            ),
        )
    )


def target_native_definitions(connection, installation: TargetInstallation):
    """Declare current owners directly; no frozen predecessors or legacy series catalog."""
    from .archive_native import archive_native_definitions
    from .companion_projection_native import companion_projection_definitions
    from .data_operation_storage import data_operation_native_definitions
    from .native_authoring import (
        _context_definition,
        _pdf_payload_definitions,
        _publication_view_definitions,
        _release_guard_definitions,
        _shape_definition,
        _task_call_definition,
    )
    from .native_objects import definition_from_sql
    from .native_sql_body import published_revision_definition, published_validation_definition
    from .published_document import published_reader_definitions

    selected = installation.metadata
    sql = Path(__file__).with_name("sql")
    definitions = []
    captured = {item.name: item.content for item in installation.authoring_inputs.sources}
    for filename, schema, name, roles in (
        ("identity.sql", "data", "canonical_json", ()),
        ("identity.sql", "data", "decimal_canonical", ()),
        ("closure.sql", "data", "require_float_lexical", ()),
        ("closure.sql", "sem", "require_admission_caller", ()),
        ("closure-native.sql", "sem", "refuse_immutable_mutation", ()),
        ("closure-native.sql", "sem", "guard_finalized_insert", ()),
        ("closure-native.sql", "sem", "record_deployment_admission", ("corpus_sem_admitter",)),
        ("closure-native.sql", "sem", "record_sql_admission", ("corpus_sem_admitter",)),
        ("closure-native.sql", "sem", "activate_release", ("corpus_sem_admitter",)),
        (
            "closure.sql",
            "data",
            "require_runtime_principal",
            (
                "corpus_sem_reader",
                "corpus_sem_writer",
                "corpus_sem_evaluator",
                "corpus_sem_admitter",
            ),
        ),
        ("scientific_layout.sql", "sem", "require_scientific_layout", ()),
    ):
        definitions.append(
            _task_call_definition(
                connection,
                captured["authoring/scientific-layout.sql"].decode()
                if filename == "scientific_layout.sql"
                else captured["authoring/closure-native.sql"].decode()
                if filename == "closure-native.sql"
                else sql.joinpath(filename).read_text(),
                name=name,
                schema=schema,
                source="target-current:" + filename,
                grants=tuple((role, "EXECUTE", False) for role in roles),
            )
        )
    definitions.extend(
        data_operation_native_definitions(
            connection,
            target_metadata=selected,
            sources=installation.authoring_inputs.native_sources,
        )
    )
    definitions.extend(archive_native_definitions(connection, target_metadata=selected))
    definitions.extend(
        _release_guard_definitions(
            connection,
            sql.joinpath("closure.sql").read_text()
            + "\n"
            + captured["authoring/execution-projection-check.sql"].decode(),
            source="target-current:release archive guards",
        )
    )
    for name in ("validate_runtime_binding", "register_runtime_binding", "require_runtime_binding"):
        definitions.append(
            _task_call_definition(
                connection,
                captured["authoring/runtime-bindings.sql"].decode(),
                schema="sem",
                name=name,
                source="target-current:runtime binding",
                grants=tuple(
                    (role, "EXECUTE", False)
                    for role in ("corpus_sem_writer", "corpus_sem_admitter")
                )
                if name == "register_runtime_binding"
                else (),
            )
        )
    payload = target_pdf_sql(installation)
    definitions.extend(
        (
            _shape_definition(connection, payload, source="target-current:PDF shape"),
            _context_definition(
                connection,
                sql.joinpath("pdf_record_context.sql").read_text(),
                source="target-current:PDF context",
            ),
            *_pdf_payload_definitions(connection, payload, source="target-current:PDF publication"),
            *_publication_view_definitions(connection, payload, source="target-current:PDF views"),
            *published_reader_definitions(connection, target_metadata=selected),
            *companion_projection_definitions(connection, target_metadata=selected),
        )
    )
    definitions = [
        published_revision_definition(item, target_metadata=selected)
        if item.identity.name == "read_pdf_published_revision"
        else published_validation_definition(item, target_metadata=selected)
        if item.identity.name == "read_pdf_published_validation"
        else item
        for item in definitions
    ]
    # SQL-language bodies bind provider functions/views at CREATE time. Keep
    # these established PDF prerequisites ahead of their dependent readers.
    providers = (
        "read_pdf_published_revision",
        "pdf_companion_field_bytes",
        "pdf_companion_body",
        "pdf_selected_product",
        "pdf_published_item",
        "pdf_published_region",
        "pdf_published_coverage",
    )
    definitions = [
        *(item for name in providers for item in definitions if item.identity.name == name),
        *(item for item in definitions if item.identity.name not in providers),
    ]
    protocol = selected.info["physical_sources"]["data-operation-native.yaml"]
    definitions.append(
        definition_from_sql(
            connection,
            target_task_guard_sql(
                protocol, sql.joinpath("data_operation_task_checks.sql").read_text()
            ),
            source="target-current:request task fence",
            owner="corpus_sem_publisher",
        )
    )
    definitions.append(
        definition_from_sql(
            connection,
            "CREATE TRIGGER zz_execution_task BEFORE INSERT OR UPDATE ON ops.task "
            "FOR EACH ROW EXECUTE FUNCTION ops.guard_execution_task()",
            source="target-current:request task fence",
            owner="corpus_sem_publisher",
        )
    )
    for relation in sorted(selected.tables.values(), key=lambda item: item.fullname):
        quoted = connection.dialect.identifier_preparer.format_table(relation)
        if (
            relation.info.get("immutability") in {"intrinsic", "immutable", "deployment"}
            or relation.fullname == "sem.physical_contract"
        ):
            # DDO intrinsic relations already receive this exact guard from
            # data_operation_native_definitions; the final identity check is exact.
            definitions.append(
                definition_from_sql(
                    connection,
                    "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON "
                    + quoted
                    + " FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation()",
                    source="target-current:physical immutability",
                    owner="corpus_sem_publisher",
                )
            )
        if relation.fullname in {"ops.pdf_shared_stream", "ops.pdf_shared_stream_part"}:
            for events, level, name in (
                (
                    "INSERT OR UPDATE OR DELETE"
                    if relation.name == "pdf_shared_stream_part"
                    else "UPDATE OR DELETE",
                    "ROW",
                    "pdf_shared_content_mutation",
                ),
                ("TRUNCATE", "STATEMENT", "pdf_shared_content_truncate"),
            ):
                definitions.append(
                    definition_from_sql(
                        connection,
                        f"CREATE TRIGGER {name} BEFORE {events} ON {quoted} "
                        f"FOR EACH {level} EXECUTE FUNCTION ops.pdf_shared_stream_mutation_guard()",
                        source="target-current:pending and verified PDF bytes",
                        owner="corpus_sem_publisher",
                    )
                )
        if relation.info.get("archive_role") is not None:
            definitions.append(
                definition_from_sql(
                    connection,
                    "CREATE TRIGGER finalized_release BEFORE INSERT ON "
                    + quoted
                    + " FOR EACH ROW EXECUTE FUNCTION sem.guard_finalized_insert()",
                    source="target-current:finalized archive",
                    owner="corpus_sem_publisher",
                )
            )
    unique = {}
    for item in definitions:
        if item.identity in unique:
            previous = unique[item.identity]
            if (
                previous.sql,
                previous.owner,
                previous.grants,
                previous.enabled,
                previous.role_bindings,
                previous.bind_owner,
            ) != (
                item.sql,
                item.owner,
                item.grants,
                item.enabled,
                item.role_bindings,
                item.bind_owner,
            ):
                raise ValueError(
                    "target native declaration differs under repeated identity: "
                    + item.identity.qualified
                )
        unique[item.identity] = item
    return tuple(unique.values())


def target_admission_descriptor(installation: TargetInstallation, native_objects):
    """Derive complete current descriptor roots without inheriting historical inventory."""
    from pglast import ast, parse_sql

    from .native_products import relation_descriptor

    selected = installation.metadata
    triggers = []
    for item in native_objects:
        if item.identity.kind != "trigger":
            continue
        (raw,) = parse_sql(item.catalog["definition"])
        trigger = raw.stmt
        if (
            not isinstance(trigger, ast.CreateTrigStmt)
            or trigger.args
            or trigger.columns
            or trigger.whenClause is not None
            or trigger.events is None
            or trigger.timing is None
            or trigger.row is None
        ):
            raise ValueError(
                "target guards require their declared unconditional no-argument trigger shape"
            )
        if item.identity.relation is None:
            raise ValueError("target trigger requires its exact parent relation")
        function = ".".join(part.sval for part in trigger.funcname or ())
        triggers.append(
            dict(
                relation=item.identity.schema + "." + item.identity.relation,
                name=item.identity.name,
                function=function + "()",
                type=trigger.events | trigger.timing | int(trigger.row),
                columns=[],
                when=None,
                args="",
                deferrable=trigger.deferrable,
                deferred=trigger.initdeferred,
            )
        )
    return dict(
        tables=[
            relation_descriptor(table)
            for table in sorted(selected.tables.values(), key=lambda table: table.fullname)
        ],
        functions=[],
        views=[],
        indexes=[],
        checks=[],
        triggers=triggers,
        readers=[
            dict(relation=table.fullname, roles=relation_descriptor(table)["read_roles"])
            for table in sorted(selected.tables.values(), key=lambda table: table.fullname)
        ],
    )


@contextmanager
def target_authoring_scratch(connection, installation: TargetInstallation):
    """Supply the declared empty archive/PDF row layouts for static authoring only."""
    from pglast import ast
    from pglast.stream import RawStream
    from sqlalchemy import text

    from .archive_transport import archive_tables, scratch_name
    from .native_objects import NativeAuthoringError
    from .pdf_shared_streams import pdf_scratch_specs

    relations = [
        (scratch_name(relation), relation) for relation in archive_tables(installation.metadata)
    ]
    preparer = connection.dialect.identifier_preparer
    savepoint = connection.begin_nested()
    try:
        for spec in pdf_scratch_specs(installation.metadata):
            if (
                connection.scalar(text("SELECT to_regclass(:name)"), {"name": spec.qualified_name})
                is not None
            ):
                raise NativeAuthoringError(
                    "target static authoring requires unused scratch context: " + spec.name
                )
            statement = spec.create_statement()
            if isinstance(statement, ast.Node):
                connection.exec_driver_sql(RawStream()(statement))
            else:
                connection.execute(statement)
            connection.exec_driver_sql(RawStream()(spec.owner_statement()))
        for name, relation in relations:
            quoted = preparer.quote(name)
            if (
                connection.scalar(text("SELECT to_regclass(:name)"), {"name": "pg_temp." + quoted})
                is not None
            ):
                raise NativeAuthoringError(
                    "target static authoring requires unused scratch context: " + name
                )
            connection.exec_driver_sql(
                "CREATE TEMP TABLE "
                + quoted
                + " (LIKE "
                + preparer.format_table(relation)
                + " INCLUDING CONSTRAINTS) ON COMMIT DROP"
            )
            connection.exec_driver_sql(
                "ALTER TABLE pg_temp." + quoted + " OWNER TO corpus_sem_publisher"
            )
        yield
    finally:
        savepoint.rollback()


def prepare_target_authoring(
    connection,
    installation: TargetInstallation,
    *,
    physical_prerequisites=(),
    predecessor=(),
    retire=frozenset(),
    recreate=frozenset(),
    owned_authoring=False,
):
    """Normalize captured target declarations against their explicit frozen predecessor."""
    from .native_admission import native_admission_sql
    from .native_authoring import (
        _declared_physical_catalog,
        current_admission_definitions,
        definition_sql,
    )
    from .native_objects import (
        NativeAuthoring,
        NativeAuthoringError,
        native_sql_script,
        prepare_native_authoring,
    )
    from .native_products import admission_kernel

    products = (
        *target_native_definitions(connection, installation),
        *current_admission_definitions(
            connection,
            admission_kernel(),
            source="target-current:admission guard",
            require_descriptor=False,
        ),
    )
    fixed = {item.identity for item in physical_prerequisites}
    if fixed & (retire | recreate):
        raise NativeAuthoringError(
            "CHECK-bound target prerequisites require an explicit physical transition"
        )
    before_complete = tuple(item for item in predecessor if item.identity not in fixed)
    before_products = tuple(
        item
        for item in before_complete
        if (item.identity.schema, item.identity.name) != ("data", "execution_contract_descriptor")
    )
    product_ids = {item.identity for item in before_products}
    normalized = prepare_native_authoring(
        connection,
        products,
        predecessor=before_products,
        retire=retire & product_ids,
        recreate=recreate & product_ids,
        owned_authoring=owned_authoring,
    )
    sql = native_admission_sql(
        native_sql_script(
            statement for item in physical_prerequisites for statement in item.statements
        )
        + "\n"
        + definition_sql(products),
        inputs=installation.authoring_inputs,
        base_descriptor=target_admission_descriptor(
            installation, (*physical_prerequisites, *normalized.desired)
        ),
        native_objects=(*physical_prerequisites, *normalized.desired),
        target_metadata=installation.metadata,
        physical_catalog=_declared_physical_catalog(connection, installation.metadata),
    )
    admission = current_admission_definitions(connection, sql, source="target-current:admission")
    complete = (*products[:-1], *admission)
    with target_authoring_scratch(connection, installation):
        remaining = prepare_native_authoring(
            connection,
            complete,
            predecessor=before_complete,
            retire=retire,
            recreate=recreate,
            owned_authoring=owned_authoring,
            check_plpgsql=frozenset(
                item.identity for item in complete if item.identity.kind == "function"
            ),
            check_plpgsql_triggers=frozenset(
                item.identity for item in complete if item.identity.kind == "trigger"
            ),
        )
    return NativeAuthoring(
        desired=(*physical_prerequisites, *remaining.desired),
        predecessor=predecessor,
        retire=retire,
        recreate=recreate,
    )


def target_database_privileges_sql() -> str:
    """Current root policy: only the protected publisher needs session scratch."""
    from sqlalchemy.dialects.postgresql import dialect

    from .alembic_privileges import PUBLISHER, PURPOSE_ROLES

    quote = dialect().identifier_preparer.quote
    revoke = "REVOKE TEMP ON DATABASE %I FROM PUBLIC," + ",".join(map(quote, PURPOSE_ROLES))
    grant = "GRANT TEMP ON DATABASE %I TO " + quote(PUBLISHER)
    return (
        "DO $target_database$ BEGIN EXECUTE format('"
        + revoke.replace("'", "''")
        + "',current_database()); EXECUTE format('"
        + grant.replace("'", "''")
        + "',current_database()); END $target_database$"
    )


def target_predecessor_descriptor(predecessor):
    """Read the complete registered target declaration, never installed desired meaning."""
    from .native_admission import _admission_descriptor
    from .native_authoring import authored_admission_sql
    from .native_objects import NativeAuthoring, NativeAuthoringError, NativeObject

    if not predecessor or any(not isinstance(item, NativeObject) for item in predecessor):
        raise NativeAuthoringError(
            "target successor requires exact frozen native predecessor objects"
        )
    frozen = NativeAuthoring(desired=predecessor, predecessor=predecessor)
    admission = authored_admission_sql(frozen)
    descriptor = _admission_descriptor(admission)
    legacy = {"ops.run", "ops.method", "ops.method_config", "kb.source_view", "data.fact"}
    if "analytical_abi" in descriptor or legacy & {
        item["relation"] for item in descriptor["tables"]
    }:
        raise NativeAuthoringError("target successor refuses a legacy-series predecessor")
    expected_functions = {item["signature"] for item in descriptor["functions"]} | {
        "data.execution_contract_descriptor()"
    }
    expected_views = {item["relation"] for item in descriptor["views"]}
    expected_triggers = {(item["relation"], item["name"]) for item in descriptor["triggers"]}
    if (
        {item.identity.qualified for item in predecessor if item.identity.kind == "function"}
        != expected_functions
        or {item.identity.qualified for item in predecessor if item.identity.kind == "view"}
        != expected_views
        or {
            (item.identity.schema + "." + (item.identity.relation or ""), item.identity.name)
            for item in predecessor
            if item.identity.kind == "trigger"
        }
        != expected_triggers
    ):
        raise NativeAuthoringError(
            "target successor requires its complete frozen native predecessor inventory"
        )
    return descriptor, admission


def prepare_target_successor(
    connection,
    installation: TargetInstallation,
    *,
    predecessor,
    retire=frozenset(),
    recreate=frozenset(),
    owned_authoring=False,
    data_steps=(),
    predecessor_revision=None,
):
    """Prepare a current successor from one exact registered target state.

    The caller authenticates registration custody before supplying its frozen
    objects. This checks their actual installed state and never adopts live bodies.
    """
    from pglast import parse_sql

    from .native_authoring import (
        _physical_check_contract,
        compare_declared_candidate,
        physical_row_type_context,
        verify_frozen_catalog,
    )
    from .native_objects import NativeAuthoringError, admit_native

    if not owned_authoring:
        raise NativeAuthoringError("target successor preparation requires owned authoring custody")
    descriptor, admission = target_predecessor_descriptor(predecessor)
    admit_native(connection, predecessor)
    verify_frozen_catalog(connection, admission)
    previous = {item.identity: item for item in predecessor}
    prerequisites = []
    for declared in target_physical_prerequisites(connection, installation):
        frozen = previous.get(declared.identity)
        desired = declared.install_sql
        if (
            frozen is None
            or frozen.statements[:1] != desired[:1]
            or tuple(map(parse_sql, frozen.statements[1:])) != tuple(map(parse_sql, desired[1:]))
        ):
            raise NativeAuthoringError(
                f"CHECK-bound target prerequisite {declared.identity.qualified} "
                "change requires an explicit physical transition"
            )
        prerequisites.append(frozen)
    with physical_row_type_context(connection, installation.metadata):
        authoring = prepare_target_authoring(
            connection,
            installation,
            physical_prerequisites=tuple(prerequisites),
            predecessor=predecessor,
            retire=retire,
            recreate=recreate,
            owned_authoring=True,
        )
        physical_contract = _physical_check_contract(connection, installation.metadata, authoring)
    return compare_declared_candidate(
        connection,
        target_metadata=installation.metadata,
        authoring=authoring,
        old_descriptor=descriptor,
        physical_contract=physical_contract,
        data_steps=data_steps,
        predecessor_revision=predecessor_revision,
    )


def require_empty_target(connection) -> None:
    """Refuse unregistered application state or migration history for an explicit root."""
    from sqlalchemy import text

    from .native_objects import NativeAuthoringError

    present = tuple(
        connection.scalars(
            text(
                "SELECT nspname FROM pg_namespace WHERE nspname IN ('meta','sem','data','ops','kb','eval') ORDER BY nspname"
            )
        )
    )
    if present:
        raise NativeAuthoringError(
            "fresh target preparation refuses existing application namespaces: " + ",".join(present)
        )
    if connection.scalar(
        text(
            "SELECT to_regclass('public.alembic_version') IS NOT NULL OR "
            "to_regclass('public.semantic_alembic_version') IS NOT NULL"
        )
    ):
        raise NativeAuthoringError("fresh target preparation refuses existing migration history")


def prepare_target_candidate(
    connection, installation: TargetInstallation, *, owned_authoring=False, data_steps=()
):
    """Prepare a fresh root on an owned empty target, preserving normal Alembic custody."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.operations.ops import ExecuteSQLOp
    from sqlalchemy.schema import CreateSchema

    from .alembic_native import NativeTransitionOp
    from .alembic_privileges import table_policy
    from .native_authoring import _physical_check_contract, compare_declared_candidate
    from .native_objects import NativeAuthoringError, prepare_native_authoring

    if not owned_authoring:
        raise NativeAuthoringError("fresh target preparation requires owned authoring custody")
    require_empty_target(connection)
    declared_schemas = {table.schema for table in installation.metadata.tables.values()}
    if None in declared_schemas:
        raise NativeAuthoringError("fresh target tables require explicit schemas")
    schemas = sorted(schema for schema in declared_schemas if schema is not None)
    quote = connection.dialect.identifier_preparer.quote
    schema_sql = [
        statement
        for schema in schemas
        for statement in (
            str(CreateSchema(schema).compile(dialect=connection.dialect)),
            "GRANT USAGE,CREATE ON SCHEMA " + quote(schema) + " TO corpus_sem_publisher",
        )
    ]
    scaffolding = connection.begin_nested()
    try:
        for statement in schema_sql:
            connection.exec_driver_sql(statement)
        prerequisites = target_physical_prerequisites(connection, installation)
        prerequisite_authoring = prepare_native_authoring(
            connection,
            prerequisites,
            predecessor=(),
            owned_authoring=True,
            check_plpgsql=frozenset(item.identity for item in prerequisites),
        )
        operations = Operations(MigrationContext.configure(connection))
        for item in prerequisite_authoring.desired:
            operations.invoke(NativeTransitionOp(None, item))
        installation.metadata.create_all(connection, checkfirst=False)
        for relation in installation.metadata.tables.values():
            connection.exec_driver_sql(
                "ALTER TABLE "
                + connection.dialect.identifier_preparer.format_table(relation)
                + " OWNER TO "
                + quote(table_policy(relation)["owner"])
            )
        authoring = prepare_target_authoring(
            connection,
            installation,
            physical_prerequisites=prerequisite_authoring.desired,
            owned_authoring=True,
        )
        physical_contract = _physical_check_contract(connection, installation.metadata, authoring)
    finally:
        scaffolding.rollback()
    candidate, authoring = compare_declared_candidate(
        connection,
        target_metadata=installation.metadata,
        authoring=authoring,
        old_descriptor=dict(tables=[], privileges=[]),
        physical_contract=physical_contract,
        data_steps=data_steps,
    )
    if candidate.upgrade_ops is None:
        raise NativeAuthoringError("fresh target preparation produced no migration body")
    prerequisite_ids = {item.identity for item in prerequisite_authoring.desired}
    early = [
        item
        for item in candidate.upgrade_ops.ops
        if isinstance(item, NativeTransitionOp) and item.identity in prerequisite_ids
    ]
    if {item.identity for item in early} != prerequisite_ids:
        raise NativeAuthoringError(
            "fresh target migration lost its physical function prerequisites"
        )
    candidate.upgrade_ops.ops[:] = [
        ExecuteSQLOp(target_database_privileges_sql()),
        *(ExecuteSQLOp(statement) for statement in schema_sql),
        *early,
        *(item for item in candidate.upgrade_ops.ops if item not in early),
    ]
    return candidate, authoring
