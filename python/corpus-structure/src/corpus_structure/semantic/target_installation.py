"""Captured current installation inputs for fresh roots and exact frozen successors.

This builds from the same captured LinkML sources and compiler as normal metadata.
It neither replays a historical migration nor authorizes a database transition.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from sqlalchemy import MetaData

from corpus_structure.caches import declare
from corpus_structure.schema.integrity import role_name

from .types import SourceArtifact

if TYPE_CHECKING:
    from .code_identity import CodeIdentity
    from .native_objects import NativeDefinition
    from .native_products import NativeAuthoringInputs
    from .native_program_registry import ProgramDeclaration, RenderedProgram


@dataclass(frozen=True)
class FoundationPrograms:
    identity: str
    closure: str
    native_closure: str
    programs: tuple[RenderedProgram, ...]


def foundation_programs(
    target: MetaData | None = None, *, value_codec_source: bytes | None = None
) -> FoundationPrograms:
    """Generate the primitive programs used by current target installation."""
    from .closure_native import closure_foundation_parts, closure_native_parts
    from .data_operation_value_native import canonical_identity_programs
    from .metadata import get_metadata
    from .native_objects import NativeIdentity, native_sql_script
    from .native_program_registry import render_programs
    from .value_codec import VALUE_CODEC_SOURCE, decimal_digit_limit

    capture = None
    if value_codec_source is not None:
        from corpus_structure.model.compiled import compiled_model

        capture = compiled_model({VALUE_CODEC_SOURCE: value_codec_source})

    selected = get_metadata() if target is None else target
    identity_declarations = canonical_identity_programs(decimal_digits=decimal_digit_limit(capture))
    closure_declarations = closure_foundation_parts(selected)
    intrinsic_declarations = closure_native_parts(selected)
    programs = render_programs(
        (*identity_declarations, *closure_declarations, *intrinsic_declarations),
        registry_schemas=frozenset({"data", "sem"}),
        prerequisites=frozenset(
            {
                NativeIdentity("function", "data", "execution_contract_descriptor"),
                NativeIdentity("function", "data", "prove_execution_release", ("text",)),
            }
        ),
    )
    statements = {program.declaration.identity: program.statement for program in programs}
    intrinsic_statements = tuple(statements[item.identity] for item in intrinsic_declarations)
    return FoundationPrograms(
        identity=native_sql_script(statements[item.identity] for item in identity_declarations),
        closure=native_sql_script(statements[item.identity] for item in closure_declarations),
        native_closure=native_sql_script(intrinsic_statements),
        programs=programs,
    )


def target_task_guard_sql(protocol: bytes, *, target_metadata: MetaData) -> str:
    """Compile the current request/lease/receipt checks from captured physical input."""
    from .data_operation_protocol import data_task_guard_program

    return data_task_guard_program(protocol, target_metadata=target_metadata).render()


@dataclass(frozen=True)
class TargetInstallation:
    """One exact physical/native capture; preparation grants no deployment authority."""

    metadata: MetaData
    pdf_sources: tuple[SourceArtifact, ...]
    authoring_inputs: NativeAuthoringInputs
    foundation: FoundationPrograms
    pdf_descriptor: tuple[ProgramDeclaration, ...]
    pdf_identity: tuple[ProgramDeclaration, ...]
    programs: tuple[NativeDefinition, ...] = ()
    prerequisites: tuple[NativeDefinition, ...] = ()
    rendered_only: bool = False


@dataclass(frozen=True)
class NativeGeneratorInputs:
    """One immutable input snapshot shared by the process and disk program caches."""

    physical_sources: tuple[tuple[str, bytes], ...]
    linkml_types: bytes
    logical_sources: tuple[tuple[str, bytes], ...]
    model_sources: tuple[tuple[str, bytes], ...]
    pdf_actions: SourceArtifact | None
    pdf_sources: tuple[SourceArtifact, ...] | None
    extra_sources: tuple[SourceArtifact, ...]
    resource_sources: tuple[SourceArtifact, ...]
    module_sources: tuple[tuple[str, bytes], ...]
    analysis_runtime: tuple[tuple[str, str], ...]
    native_library_runtime: tuple[tuple[str, str], ...]
    code_identity: CodeIdentity

    @property
    def complete(self) -> bool:
        return self.code_identity.complete


def _installation_key(inputs: NativeGeneratorInputs) -> bytes:
    from .native_program_store import input_key

    if not inputs.complete:
        raise ValueError("native generator identity is incomplete")
    key = input_key(inputs, include_format=False)
    if key is None:
        raise ValueError("native generator identity did not produce an input key")
    return key


@dataclass(frozen=True)
class _GenerationFailure:
    error: Exception


@declare("native-installation", "program_sets", key=_installation_key)
def _held_target_installation(inputs: NativeGeneratorInputs):
    from corpus_structure.schema.physical import compile_physical

    owned = compile_physical(dict(inputs.physical_sources), linkml_types=inputs.linkml_types)
    try:
        from .native_program_store import input_key, load_installation, save_installation

        key = input_key(inputs, include_format=True)
        retained = None if key is None else load_installation(key, owned)
        if retained is not None:
            return retained
        result = _build_target_installation(owned, inputs)
        if key is not None:
            save_installation(key, result)
        return result
    except (ValueError, TypeError) as error:
        return _GenerationFailure(error)


def capture_target_installation(
    selected: MetaData,
    *,
    logical_sources: dict[str, bytes] | None = None,
    pdf_actions: SourceArtifact | None = None,
    pdf_sources: tuple[SourceArtifact, ...] | None = None,
    extra_sources: tuple[SourceArtifact, ...] = (),
) -> TargetInstallation:
    from corpus_structure.model.compiled import running_model

    from .data_operation_storage import capture_native_package_resource, native_logical_sources
    from .determinants import analysis_runtime, determinant_version
    from .native_program_store import (
        capture_generator_code,
        capture_generator_custody,
        capture_generator_sources,
    )

    if not selected.info.get("physical_sources") or not isinstance(
        selected.info.get("physical_linkml_types"), bytes
    ):
        raise ValueError("native installation requires captured physical inputs and LinkML types")
    if pdf_sources is not None and pdf_actions is not None:
        raise ValueError("select PDF action input or an already captured PDF source cohort")
    model = running_model()
    model_inputs = tuple(sorted(model.sources.items()))
    logical = (
        native_logical_sources(model_sources=dict(model_inputs))
        if logical_sources is None
        else logical_sources
    )
    code_identity = capture_generator_code()
    resource_sources = (capture_native_package_resource(),)
    inputs = NativeGeneratorInputs(
        physical_sources=tuple(sorted(selected.info["physical_sources"].items())),
        linkml_types=selected.info["physical_linkml_types"],
        logical_sources=tuple(sorted(logical.items())),
        model_sources=model_inputs,
        pdf_actions=pdf_actions,
        pdf_sources=pdf_sources,
        extra_sources=tuple(extra_sources),
        resource_sources=resource_sources,
        module_sources=capture_generator_sources(code_identity),
        analysis_runtime=analysis_runtime(),
        native_library_runtime=tuple(
            (name, determinant_version(name))
            for name in ("pglast", "sqlalchemy", "linkml-runtime", "networkx")
        ),
        code_identity=code_identity,
    )
    if not inputs.complete:
        return _render_uncached(inputs)
    with capture_generator_custody(inputs.code_identity):
        result = _held_target_installation(inputs)
    if isinstance(result, _GenerationFailure):
        raise result.error
    return result


def _render_uncached(inputs: NativeGeneratorInputs) -> TargetInstallation:
    from corpus_structure.schema.physical import compile_physical

    owned = compile_physical(dict(inputs.physical_sources), linkml_types=inputs.linkml_types)
    try:
        return _build_target_installation(owned, inputs)
    except (ValueError, TypeError) as error:
        raise error


def _build_target_installation(
    selected: MetaData, inputs: NativeGeneratorInputs
) -> TargetInstallation:
    from .data_operation_compiler_native import data_operation_native_descriptor_program
    from .data_operation_wire import wire_operations
    from .native_objects import native_sql_script
    from .native_products import _capture_native_authoring_inputs, bind_program_manifest
    from .native_program_registry import ProgramManifest, program_closures, render_programs
    from .native_program_store import captured_source
    from .pdf_binary_identity_native import (
        pdf_artifact_identity_programs,
        pdf_binary_identity_programs,
    )
    from .pdf_descriptor_native import pdf_descriptor_programs
    from .pdf_domain import PREFIX, pdf_domain_sources
    from .source_record_recognition_native import source_record_recognition_sql

    logical = dict(inputs.logical_sources)
    pdf_sources = inputs.pdf_sources
    if pdf_sources is not None and inputs.pdf_actions is not None:
        raise ValueError("select PDF action input or an already captured PDF source cohort")
    if pdf_sources is None:
        pdf_sources = pdf_domain_sources(
            physical_sources=selected.info["physical_sources"],
            linkml_types=selected.info["physical_linkml_types"],
            actions_source=inputs.pdf_actions
            or SourceArtifact(PREFIX + "native/actions.yaml", logical["pdf-actions.yaml"]),
            include_producer=False,
            model_sources=dict(inputs.model_sources),
            analysis_versions=inputs.analysis_runtime,
        )
    foundation = foundation_programs(selected, value_codec_source=logical["value-codec.yaml"])
    descriptor = pdf_descriptor_programs()
    binary = pdf_binary_identity_programs()
    artifact = pdf_artifact_identity_programs(selected)
    authoring_inputs = _capture_native_authoring_inputs(
        target_metadata=selected,
        pdf_sources=pdf_sources,
        logical_sources=logical,
        model_sources=dict(inputs.model_sources),
        captured_module_sources=dict(inputs.module_sources),
        resource_sources=inputs.resource_sources,
        native_library_runtime=inputs.native_library_runtime,
        extra_sources=(
            *inputs.extra_sources,
            SourceArtifact(
                "authoring/native-program-registry.py",
                captured_source(inputs, "semantic/native_program_registry.py"),
            ),
            SourceArtifact(
                "authoring/target_installation.py",
                captured_source(inputs, "semantic/target_installation.py"),
            ),
            SourceArtifact("authoring/identity.sql", foundation.identity.encode()),
            SourceArtifact("authoring/closure.sql", foundation.closure.encode()),
            SourceArtifact("authoring/closure-native.sql", foundation.native_closure.encode()),
            SourceArtifact(
                "authoring/closure-native.py",
                captured_source(inputs, "semantic/closure_native.py"),
            ),
            SourceArtifact(
                "authoring/pdf-descriptor.sql",
                (native_sql_script(item.render() for item in descriptor) + "\n").encode(),
            ),
            SourceArtifact(
                "authoring/pdf-descriptor.py",
                captured_source(inputs, "semantic/pdf_descriptor_native.py"),
            ),
            SourceArtifact(
                "authoring/pdf-record-identity.sql",
                (native_sql_script(item.render() for item in binary) + "\n").encode(),
            ),
            SourceArtifact(
                "authoring/pdf-record-artifact-identity.sql",
                (native_sql_script(item.render() for item in artifact) + "\n").encode(),
            ),
            SourceArtifact(
                "authoring/pdf-captured-recognition.sql",
                source_record_recognition_sql(selected).encode(),
            ),
            SourceArtifact(
                "authoring/pdf-captured-recognition.py",
                captured_source(inputs, "semantic/source_record_recognition_native.py"),
            ),
        ),
    )
    provisional = TargetInstallation(
        selected, pdf_sources, authoring_inputs, foundation, descriptor, (*binary, *artifact)
    )
    products = target_program_definitions(None, provisional)
    definitions = (*target_physical_prerequisites(None, provisional), *products)
    manifest = ProgramManifest.from_definitions(definitions)
    closures = program_closures(
        definitions,
        (item["name"] for item in wire_operations(authoring_inputs.native_sources)),
    )
    native_descriptor = render_programs(
        (data_operation_native_descriptor_program(manifest.kernel_digest, closures),),
        registry_schemas=frozenset({"sem", "data", "ops"}),
    )[0].declared_definition
    return replace(
        provisional,
        authoring_inputs=bind_program_manifest(authoring_inputs, manifest, closures),
        programs=(native_descriptor, *products),
        prerequisites=tuple(definitions[: len(definitions) - len(products)]),
    )


def target_physical_prerequisites(connection, installation: TargetInstallation):
    """The table-free current function used by the PDF body CHECK declaration."""
    from .native_program_registry import render_programs

    if installation.prerequisites:
        return installation.prerequisites
    return tuple(
        item.definition(connection)
        for item in render_programs(
            installation.pdf_descriptor, registry_schemas=frozenset({"ops"})
        )
    )


def target_trigger_programs(target: MetaData):
    from .data_operation_storage import data_operation_immutable_relations
    from .native_objects import native_before_trigger
    from .native_program_registry import RelationProgramDeclaration

    owner = role_name("publisher")

    def trigger(relation, name, routine, source, events, *, row=False):
        return RelationProgramDeclaration(
            native_before_trigger(relation, name, routine, events=events, row=row),
            source,
            owner,
        )

    programs = [
        trigger(
            target.tables["ops.task"],
            "zz_execution_task",
            ("ops", "guard_execution_task"),
            "target-current:request task fence",
            ("insert", "update"),
            row=True,
        )
    ]
    intrinsic = set(data_operation_immutable_relations(target, target.info["physical_sources"]))
    pending = {
        item
        for item in target.tables.values()
        if item.info.get("immutability") == "pending-content"
    }
    for relation in sorted(target.tables.values(), key=lambda item: item.fullname):
        if (
            relation in intrinsic
            or relation.info.get("immutability") in {"intrinsic", "immutable", "deployment"}
            or relation.fullname == "sem.physical_contract"
        ):
            programs.append(
                trigger(
                    relation,
                    "semantic_immutable",
                    ("sem", "refuse_immutable_mutation"),
                    "target-current:physical immutability",
                    ("update", "delete", "truncate"),
                )
            )
        if relation.info.get("frontier_guard") == "guarded":
            programs.append(
                trigger(
                    relation,
                    "ddo_read_frontier_guard",
                    ("ops", "ddo_refuse_post_acquisition_graph_write"),
                    "data-operation pinned frontier:forward",
                    ("insert", "update", "delete", "truncate"),
                )
            )
        if relation in pending:
            is_component = any(
                foreign.column.table in pending and foreign.column.table is not relation
                for foreign in relation.foreign_keys
            )
            for events, row, name in (
                (
                    ("insert", "update", "delete") if is_component else ("update", "delete"),
                    True,
                    "pdf_shared_content_mutation",
                ),
                (("truncate",), False, "pdf_shared_content_truncate"),
            ):
                programs.append(
                    trigger(
                        relation,
                        name,
                        ("ops", "pdf_shared_stream_mutation_guard"),
                        "target-current:pending and verified PDF bytes",
                        events,
                        row=row,
                    )
                )
        if relation.info.get("archive_role") is not None:
            programs.append(
                trigger(
                    relation,
                    "finalized_release",
                    ("sem", "guard_finalized_insert"),
                    "target-current:finalized archive",
                    ("insert",),
                    row=True,
                )
            )
    return tuple(programs)


def _declaration_installation(installation: TargetInstallation) -> TargetInstallation:
    """Build typed generator trees only when a caller explicitly asks for declarations."""
    from .archive_projection_native import (
        execution_projection_check_program,
        scientific_layout_program,
    )
    from .data_operation_protocol import data_task_guard_program
    from .pdf_binary_identity_native import (
        pdf_artifact_identity_programs,
        pdf_binary_identity_programs,
    )
    from .pdf_descriptor_native import pdf_descriptor_programs

    selected = installation.metadata
    captured = {source.name: source.content for source in installation.authoring_inputs.sources}
    foundation = foundation_programs(
        selected, value_codec_source=captured["native/value-codec.yaml"]
    )
    guards = (
        execution_projection_check_program(selected),
        scientific_layout_program(selected),
        data_task_guard_program(
            selected.info["physical_sources"]["data-operation-native.yaml"],
            target_metadata=selected,
        ),
    )
    return replace(
        installation,
        foundation=foundation,
        authoring_inputs=replace(installation.authoring_inputs, guard_programs=guards),
        pdf_descriptor=pdf_descriptor_programs(),
        pdf_identity=(*pdf_binary_identity_programs(), *pdf_artifact_identity_programs(selected)),
        rendered_only=False,
    )


def target_native_declarations(installation: TargetInstallation):
    """Bring every native owner into one program graph before rendering."""
    from .archive_native import archive_native_programs
    from .companion_projection_native import companion_projection_programs
    from .data_operation_storage import data_operation_native_programs
    from .native_admission_release import admission_programs
    from .native_objects import NativeAuthoringError
    from .pdf_companion_adoption_native import companion_adoption_programs
    from .pdf_completion_native import pdf_completion_native_programs
    from .pdf_contracts import _context_from_domain
    from .pdf_domain import CONTRACT, PdfDomainContract
    from .pdf_domain_native import pdf_domain_native_programs
    from .pdf_identity_frames_native import pdf_identity_frame_programs
    from .pdf_integrated_native import observation_publication_programs
    from .pdf_publication_native import publication_native_programs
    from .pdf_record_access_native import pdf_access_correspondence_programs
    from .pdf_record_digest_native import pdf_record_logical_identity_programs
    from .pdf_record_proof_native import pdf_record_proof_programs
    from .pdf_selected_source_native import selected_source_reader_programs
    from .pdf_shared_stream_queries import shared_stream_queries_programs
    from .pdf_shared_stream_writes import shared_stream_writes_programs
    from .pdf_shared_streams import part_wire_contract_programs
    from .pdf_spool_native import pdf_spool_native_programs
    from .pdf_staging_native import stage_native_programs
    from .pdf_target_identity_native import logical_target_identity_programs
    from .published_document import published_readers_programs
    from .runtime_binding_native import runtime_binding_programs
    from .source_record_recognition_native import (
        source_record_recognition_program,
        source_record_recognition_sql,
    )

    selected = installation.metadata
    if installation.rendered_only:
        installation = _declaration_installation(installation)
    domain = PdfDomainContract(
        next(item.content for item in installation.pdf_sources if item.name == CONTRACT),
        tuple(item for item in installation.pdf_sources if item.name != CONTRACT),
    )
    context = _context_from_domain(None, domain)
    captured = {item.name: item.content for item in installation.authoring_inputs.sources}
    if (
        installation.foundation.identity.encode() != captured["authoring/identity.sql"]
        or installation.foundation.closure.encode() != captured["authoring/closure.sql"]
        or installation.foundation.native_closure.encode()
        != captured["authoring/closure-native.sql"]
    ):
        raise NativeAuthoringError(
            "foundation declarations differ from their captured install statements"
        )
    if (
        source_record_recognition_sql(selected).encode()
        != captured["authoring/pdf-captured-recognition.sql"]
    ):
        raise NativeAuthoringError("recognition declaration differs from its captured install SQL")
    return (
        *(item.declaration for item in installation.foundation.programs),
        *installation.authoring_inputs.guard_programs,
        *installation.pdf_identity,
        *archive_native_programs(target_metadata=selected),
        *runtime_binding_programs(selected),
        *target_trigger_programs(selected),
        *admission_programs(selected),
        *data_operation_native_programs(
            target_metadata=selected,
            sources=installation.authoring_inputs.native_sources,
            pdf_domain=domain,
        ),
        *pdf_domain_native_programs(sources=installation.pdf_sources, target_metadata=selected),
        *part_wire_contract_programs(selected),
        *shared_stream_queries_programs(selected),
        *shared_stream_writes_programs(selected),
        *stage_native_programs(target_metadata=selected),
        *pdf_spool_native_programs(target_metadata=selected),
        *publication_native_programs(selected, domain),
        *companion_adoption_programs(context, selected),
        *pdf_record_logical_identity_programs(target_metadata=selected),
        *logical_target_identity_programs(selected),
        *pdf_identity_frame_programs(selected),
        *pdf_record_proof_programs(selected),
        *pdf_access_correspondence_programs(selected),
        *observation_publication_programs(context, target_metadata=selected),
        source_record_recognition_program(selected),
        *pdf_completion_native_programs(selected),
        *selected_source_reader_programs(target_metadata=selected, pdf_domain=domain),
        *published_readers_programs(target_metadata=selected),
        *companion_projection_programs(target_metadata=selected, domain=domain),
    )


def target_admission_descriptor(installation: TargetInstallation, native_objects):
    """Derive complete current descriptor roots without inheriting historical inventory."""
    from pglast import ast, parse_sql

    from .native_products import relation_descriptor
    from .native_program_registry import ProgramManifest

    selected = installation.metadata
    manifest = ProgramManifest.from_definitions(tuple(native_objects))
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
        program_manifest=manifest.inventory,
        kernel_identity=manifest.kernel_identity,
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
    from sqlalchemy import Text, bindparam, func, select

    from .archive_native import archive_scratch_specs
    from .native_objects import NativeAuthoringError
    from .pdf_shared_streams import pdf_scratch_specs

    specs = (
        *pdf_scratch_specs(installation.metadata),
        *archive_scratch_specs(installation.metadata),
    )
    present = select(func.to_regclass(bindparam("name", type_=Text())))
    savepoint = connection.begin_nested()
    try:
        for spec in specs:
            if connection.scalar(present, {"name": spec.qualified_name}) is not None:
                raise NativeAuthoringError(
                    "target static authoring requires unused scratch context: " + spec.name
                )
            statement = spec.create_statement()
            if isinstance(statement, ast.Node):
                connection.exec_driver_sql(RawStream()(statement))
            else:
                connection.execute(statement)
            connection.exec_driver_sql(RawStream()(spec.owner_statement()))
        yield
    finally:
        savepoint.rollback()


def target_program_definitions(connection, installation: TargetInstallation):
    """Collect current programs using their typed declarations and exact authorities."""
    if installation.programs:
        return installation.programs

    from .native_program_registry import EXECUTION_DESCRIPTOR, OPERATION_DESCRIPTOR, render_programs

    declarations = target_native_declarations(installation)
    prerequisites = {
        EXECUTION_DESCRIPTOR,
        *(program.identity for program in installation.pdf_descriptor),
    }
    if OPERATION_DESCRIPTOR not in {program.identity for program in declarations}:
        prerequisites.add(OPERATION_DESCRIPTOR)
    return tuple(
        item.definition(connection)
        for item in render_programs(
            declarations,
            registry_schemas=frozenset({"data", "ops", "sem", "kb", "cp", "eval"}),
            prerequisites=frozenset(prerequisites),
        )
    )


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
    from .native_admission import describe_native_admission, execution_descriptor_program
    from .native_authoring import (
        _declared_physical_catalog,
        definition_sql,
    )
    from .native_objects import (
        NativeAuthoring,
        NativeAuthoringError,
        native_sql_script,
        prepare_native_authoring,
    )
    from .native_program_registry import PROGRAM_MANIFEST_SOURCE, ProgramManifest, render_programs

    products = target_program_definitions(connection, installation)
    captured_manifest = next(
        item.content
        for item in installation.authoring_inputs.native_sources
        if item.name == PROGRAM_MANIFEST_SOURCE
    )
    if (
        ProgramManifest.from_definitions((*physical_prerequisites, *products)).content
        != captured_manifest
    ):
        raise NativeAuthoringError(
            "server-resolved native declarations differ from the captured program manifest"
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
    descriptor = describe_native_admission(
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
    rendered = render_programs(
        (execution_descriptor_program(descriptor),), registry_schemas=frozenset({"data"})
    )
    complete = (*products, rendered[0].definition(connection))
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
    from .native_authoring import frozen_admission_sql
    from .native_objects import NativeAuthoringError, NativeObject

    if not predecessor or any(not isinstance(item, NativeObject) for item in predecessor):
        raise NativeAuthoringError(
            "target successor requires exact frozen native predecessor objects"
        )
    admission = frozen_admission_sql(predecessor)
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


def _prerequisite_check_transitions(installation, identities):
    """Use the declared CHECKs for an explicit prerequisite recreation."""
    from alembic.operations.ops import CreateCheckConstraintOp, DropConstraintOp
    from pglast import parse_sql
    from pglast.visitors import Visitor
    from sqlalchemy import CheckConstraint

    from corpus_structure.schema.relational import physical_expression_sql

    from .alembic_privileges import OwnedOperationsOp, table_policy
    from .native_objects import NativeAuthoringError

    names = {(identity.schema, identity.name) for identity in identities}

    class Calls(Visitor):
        def __init__(self):
            super().__init__()
            self.found = set()

        def visit_FuncCall(self, ancestors, node):
            name = tuple(part.sval for part in node.funcname)
            if name in names:
                self.found.add(name)

    before, after, covered = [], [], set()
    for table in sorted(installation.metadata.tables.values(), key=lambda item: item.fullname):
        for check in sorted(table.constraints, key=lambda item: str(item.name)):
            if not isinstance(check, CheckConstraint):
                continue
            calls = Calls()
            calls(parse_sql("SELECT " + physical_expression_sql(check.sqltext)))
            if calls.found:
                owner = table_policy(table)["owner"]
                if owner is None:
                    raise NativeAuthoringError("physical check transition requires its table owner")
                before.append(OwnedOperationsOp(owner, [DropConstraintOp.from_constraint(check)]))
                after.append(
                    OwnedOperationsOp(owner, [CreateCheckConstraintOp.from_constraint(check)])
                )
                covered.update(calls.found)
    if covered != names:
        raise NativeAuthoringError("prerequisite recreation lacks its declared physical checks")
    return before, after


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
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from pglast import parse_sql

    from .native_authoring import (
        _physical_check_contract,
        compare_declared_candidate,
        physical_row_type_context,
        verify_frozen_catalog,
    )
    from .native_objects import NativeAuthoringError, admit_native, prepare_native_authoring
    from .native_products import current_admission_fields

    if not owned_authoring:
        raise NativeAuthoringError("target successor preparation requires owned authoring custody")
    descriptor, admission = target_predecessor_descriptor(predecessor)
    admit_native(connection, predecessor)
    verify_frozen_catalog(connection, admission)
    previous = {item.identity: item for item in predecessor}
    prerequisites = []
    replacements = []
    for declared in target_physical_prerequisites(connection, installation):
        frozen = previous.get(declared.identity)
        desired = declared.install_sql
        if frozen is not None and declared.identity in recreate:
            replacements.append(declared)
            continue
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
    replacement_ids = frozenset(declared.identity for declared in replacements)
    if replacements and (
        descriptor["physical_checks_source_digest"]
        != current_admission_fields(
            installation.authoring_inputs, target_metadata=installation.metadata
        )["physical_checks_source_digest"]
    ):
        raise NativeAuthoringError("prerequisite recreation requires the retained CHECK contract")
    before_checks, after_checks = (
        _prerequisite_check_transitions(installation, replacement_ids) if replacements else ([], [])
    )
    with physical_row_type_context(connection, installation.metadata):
        if replacements:
            operations = Operations(MigrationContext.configure(connection))
            for effect in before_checks:
                operations.invoke(effect)
            replacement = prepare_native_authoring(
                connection,
                tuple(replacements),
                predecessor=tuple(previous[item.identity] for item in replacements),
                owned_authoring=True,
                check_plpgsql=replacement_ids,
            )
            prerequisites.extend(replacement.desired)
        authoring = prepare_target_authoring(
            connection,
            installation,
            physical_prerequisites=tuple(prerequisites),
            predecessor=predecessor,
            retire=retire,
            recreate=recreate - replacement_ids,
            owned_authoring=True,
        )
        if replacements:
            authoring = replace(authoring, recreate=recreate)
        physical_contract = _physical_check_contract(connection, installation.metadata, authoring)
    candidate, authored = compare_declared_candidate(
        connection,
        target_metadata=installation.metadata,
        authoring=authoring,
        old_descriptor=descriptor,
        physical_contract=physical_contract,
        data_steps=data_steps,
        predecessor_revision=predecessor_revision,
    )
    if candidate.upgrade_ops is not None and replacements:
        # The CHECK drops take and retain the table locks before the native
        # changes. Adding the declared checks validates every retained row.
        candidate.upgrade_ops.ops[:0] = before_checks
        candidate.upgrade_ops.ops.extend(after_checks)
    return candidate, authored


def require_empty_target(connection) -> None:
    """Refuse unregistered application state or migration history for an explicit root."""
    from sqlalchemy import or_, select

    from .native_catalog import namespace, pg
    from .native_objects import NativeAuthoringError

    present = tuple(
        connection.scalars(
            select(namespace.c.nspname)
            .where(namespace.c.nspname.in_(("meta", "sem", "data", "ops", "kb", "eval")))
            .order_by(namespace.c.nspname)
        )
    )
    if present:
        raise NativeAuthoringError(
            "fresh target preparation refuses existing application namespaces: " + ",".join(present)
        )
    if connection.scalar(
        select(
            or_(
                pg.to_regclass("public.alembic_version").is_not(None),
                pg.to_regclass("public.semantic_alembic_version").is_not(None),
            )
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
    from .alembic_privileges import PUBLISHER, table_policy
    from .native_authoring import _physical_check_contract, compare_declared_candidate
    from .native_objects import (
        NativeAuthoringError,
        NativeIdentity,
        execute_native_sql,
        native_owner_sql,
        native_privilege_sql,
        prepare_native_authoring,
    )

    if not owned_authoring:
        raise NativeAuthoringError("fresh target preparation requires owned authoring custody")
    require_empty_target(connection)
    declared_schemas = {table.schema for table in installation.metadata.tables.values()}
    if None in declared_schemas:
        raise NativeAuthoringError("fresh target tables require explicit schemas")
    schemas = sorted(schema for schema in declared_schemas if schema is not None)
    schema_sql = [
        statement
        for schema in schemas
        for statement in (
            str(CreateSchema(schema).compile(dialect=connection.dialect)),
            native_privilege_sql(NativeIdentity("schema", schema, schema), PUBLISHER, "USAGE"),
            native_privilege_sql(NativeIdentity("schema", schema, schema), PUBLISHER, "CREATE"),
        )
    ]
    scaffolding = connection.begin_nested()
    try:
        for statement in schema_sql:
            execute_native_sql(connection, statement)
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
            owner = table_policy(relation)["owner"]
            if owner is None:
                raise NativeAuthoringError("declared physical table requires its owner")
            identity = NativeIdentity("table", str(relation.schema), relation.name)
            execute_native_sql(connection, native_owner_sql(identity, owner))
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
