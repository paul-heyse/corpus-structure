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

from .alembic_defaults import compare_default
from .alembic_defaults import plugin as defaults_plugin
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


def _selected_product_definition(connection, sql, *, source):
    """Own the existing selected-product view with its frozen declaration and grants."""
    prepared = prepare_sql(sql, source=source)
    definition = None
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if (
            isinstance(statement, ast.ViewStmt)
            and statement.view is not None
            and statement.view.schemaname == "ops"
            and statement.view.relname == "pdf_selected_product"
        ):
            definition = definition_from_sql(
                connection,
                prepared.excerpt(index),
                source=source,
                owner="corpus_sem_publisher",
                grants=tuple(
                    (role, "SELECT", False)
                    for role in (
                        "corpus_sem_writer",
                        "corpus_sem_reader",
                        "corpus_sem_evaluator",
                        "corpus_sem_admitter",
                    )
                ),
            )
    if definition is None:
        raise NativeAuthoringError(f"{source}: selected PDF product view declaration is absent")
    return definition


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


def _task_call_definition(connection, sql, *, name, source):
    """Bind the existing generated-call ABI to normalized argument/result/ACL facts."""
    prepared = prepare_sql(sql, source=source)
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if isinstance(statement, ast.CreateFunctionStmt) and tuple(
            part.sval for part in statement.funcname or ()
        ) == ("ops", name):
            return definition_from_sql(
                connection,
                prepared.excerpt(index),
                source=source,
                owner="corpus_sem_publisher",
                grants=(("corpus_sem_writer", "EXECUTE", False),),
            )
    raise NativeAuthoringError(f"native task-call ABI declaration is absent: {name}")


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
        _selected_product_definition(connection, sql, source=path.name),
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
        _shape_definition(connection, _native_shape_guard(), source="native-record-shape:forward"),
        _context_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("pdf_record_context.sql").read_text(),
            source="pdf_record_context.sql:forward",
        ),
        *companion_projection_definitions(connection),
        *published_reader_definitions(connection),
        *_pdf_payload_definitions(connection, payload_sql, source="pdf-payloads:forward"),
        _selected_product_definition(
            connection, payload_sql, source="pdf-selected-product:forward"
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
    providers = ("read_pdf_published_revision", "pdf_selected_product")
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
            migration_owner = connection.scalar(
                text("SELECT pg_get_userbyid(nspowner) FROM pg_namespace WHERE nspname='sem'")
            )
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
):
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
    return native_admission_sql(
        definition_sql(products),
        base_admission=source.admission,
        authoring_provenance=current_authoring_provenance(),
        native_objects=selected,
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
    context = MigrationContext.configure(
        connection,
        opts={
            "include_schemas": True,
            "include_name": lambda name, kind, parents: (
                name in SCHEMAS if kind == "schema" else True
            ),
            "compare_server_default": compare_default,
            "autogenerate_plugins": [
                "alembic.autogenerate.*",
                "alembic.ext.checkconstraint_byname",
                defaults_plugin.name,
                native_plugin.name,
            ],
            "native_authoring": authoring,
        },
    )
    return produce_migrations(context, target_metadata), authoring


def definition_sql(definitions) -> str:
    """Inspection/admission input; frozen revisions execute serialized native operations."""
    return "\n".join(
        statement.rstrip(";\n") + ";" for item in definitions for statement in item.install_sql
    )
