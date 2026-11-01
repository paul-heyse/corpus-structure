"""Series-owned forward candidate preparation on Alembic's normal migration lifecycle."""

from __future__ import annotations

import json
from dataclasses import replace
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
    NativeObject,
    definition_from_sql,
    prepare_native_authoring,
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
        "adopt_pdf_access",
        "record_pdf_native_validation",
        "validate_pdf_build",
        "lookup_pdf_validation",
        "seal_pdf_build",
        "pdf_validation_contract",
        "pdf_projection_contract",
        "pdf_identity_companion_scalar",
        "pdf_record_logical_identity",
        "read_pdf_record_rows",
        "read_pdf_record_context_rows",
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


def series_predecessor_definitions(connection):
    """Bounded predecessor source; never infer desired meaning from a deployed catalog."""
    from .migrations import ALEMBIC_DIR

    path = ALEMBIC_DIR / "versions/semantic_0065_reconciliation.sql"
    sql = path.read_text()
    return (
        _shape_definition(connection, sql, source=path.name),
        _context_definition(connection, sql, source=path.name),
        *_pdf_payload_definitions(connection, sql, source=path.name),
        _selected_product_definition(connection, sql, source=path.name),
    )


def series_native_definitions(connection, *, include_selected=True):
    from .pdf_publication_native import (
        _native_shape_guard,
        pdf_record_logical_identity_sql,
        publication_sql,
    )
    from .pdf_staging_native import stage_native_sql

    payload_sql = (
        stage_native_sql() + "\n" + publication_sql() + "\n" + pdf_record_logical_identity_sql()
    )
    definitions = [
        _shape_definition(connection, _native_shape_guard(), source="native-record-shape:forward"),
        _context_definition(
            connection,
            Path(__file__).with_name("sql").joinpath("pdf_record_context.sql").read_text(),
            source="pdf_record_context.sql:forward",
        ),
        *companion_projection_definitions(connection),
        *_pdf_payload_definitions(connection, payload_sql, source="pdf-payloads:forward"),
        _selected_product_definition(
            connection, payload_sql, source="pdf-selected-product:forward"
        ),
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


def candidate_admission_sql(connection, products, native_objects):
    from .migrations import ALEMBIC_DIR
    from .native_products import current_authoring_provenance
    from .source_view_native import native_admission_sql

    # A descriptor cannot include its own body hash. The enforcing guard is not
    # self-referential: its source is independent of the descriptor literal.
    selected = tuple(
        item
        for item in native_objects
        if (item.identity.schema, item.identity.name) != ("data", "execution_contract_descriptor")
    )
    return native_admission_sql(
        definition_sql(products),
        base_admission=ALEMBIC_DIR.joinpath("versions/semantic_0065_admission.sql").read_text(),
        authoring_provenance=current_authoring_provenance(),
        native_objects=selected,
    )


def load_native_state(path: Path, *, digest: str | None = None) -> tuple[NativeObject, ...]:
    content = path.read_bytes()
    if digest is not None and sha256(content).hexdigest() != digest:
        raise NativeAuthoringError(f"{path.name}: native predecessor state digest differs")
    try:
        payload = json.loads(content)
        if payload["version"] != 1 or not isinstance(payload["desired"], list):
            raise ValueError("unsupported native state format")
        objects = tuple(NativeObject.from_payload(value) for value in payload["desired"])
        if len({item.identity for item in objects}) != len(objects):
            raise ValueError("duplicate native identity")
        return objects
    except (KeyError, TypeError, ValueError) as error:
        raise NativeAuthoringError(
            f"{path.name}: invalid frozen native predecessor state: {error}"
        ) from error


def current_native_state(connection, explicit: Path | None = None):
    """Read the current revision's declared immutable desired state, never live adoption."""
    if explicit is not None:
        return load_native_state(explicit)
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
    filename = getattr(script.module, "NATIVE_STATE_FILE", None)
    digest = getattr(script.module, "NATIVE_STATE_SHA256", None)
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or not isinstance(digest, str)
    ):
        raise NativeAuthoringError(
            "current revision lacks frozen native state; select --predecessor-state explicitly"
        )
    return load_native_state(Path(script.path).parent / filename, digest=digest)


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
    from .migrations import ALEMBIC_DIR

    products = series_native_definitions(connection, include_selected=include_selected)
    if predecessor is not None and predecessor_state is not None:
        raise NativeAuthoringError(
            "select source predecessors or a frozen predecessor state, not both"
        )
    frozen_before = (
        current_native_state(connection, predecessor_state) if predecessor is None else None
    )
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
        product_predecessor = (
            series_predecessor_definitions(connection) if predecessor is None else predecessor
        )
    if frozen_before is not None:
        known = {item.identity for item in product_predecessor}
        newly_managed = tuple(
            item
            for item in series_predecessor_definitions(connection)
            if item.identity not in known
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
            ALEMBIC_DIR.joinpath("versions/semantic_0065_admission.sql").read_text(),
            source="semantic_0065_admission.sql",
        )
    )
    if len(admission_before) != 2:
        raise NativeAuthoringError(
            "frozen native state must include its descriptor and enforcing guard"
        )
    first_admission = candidate_admission_sql(connection, products, product_authoring.desired)
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
        connection, products, (*product_authoring.desired, *guard_authoring.desired)
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
