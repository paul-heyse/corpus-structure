"""Compile original-document custody against the selected physical model."""

from sqlalchemy import (
    Boolean,
    MetaData,
    and_,
    cast,
    column,
    exists,
    func,
    literal,
    or_,
    select,
    true,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSONB, array, insert

from corpus_structure.schema.integrity import role_name

from .native_objects import native_sql_script
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Perform,
    PerformQuery,
    Raise,
    Return,
    ReturnNext,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    variable,
)

ASSET_DIGEST_BASIS = "source-admission-helper-asset-digest"


def source_original_programs(model: MetaData, asset_digest: str) -> str:
    """Render finalized helper admission and exact binary original registration."""
    from .original_document_contracts import ASSET, CONTRACT, OPERATION, ROLE

    finalization = model.tables["sem.release_finalization"]
    artifact = model.tables["sem.artifact"]
    definition = model.tables["sem.data_operation_definition"]
    project = model.tables["data.project"]
    document = model.tables["kb.document"]
    original = model.tables["kb.source_artifact"]
    release = core_variable("p_release", finalization.c.release_id.type)
    operations = (
        func.jsonb_array_elements(
            cast(func.convert_from(artifact.c.content, "UTF8"), JSONB())["operations"]
        )
        .table_valued(column("value", JSONB()))
        .lateral("operation")
    )
    assets = func.jsonb_array_elements(operations.c.value["assets"]).table_valued(
        column("value", JSONB())
    )
    admitted = exists(
        select(1)
        .select_from(
            artifact.join(operations, true()).join(
                definition,
                and_(
                    definition.c.release_id == artifact.c.release_id,
                    definition.c.operation_id == operations.c.value["semantic_id"].astext,
                ),
            )
        )
        .where(
            artifact.c.release_id == release,
            artifact.c.artifact_name == "data_operations.json",
            operations.c.value["semantic_id"].astext == OPERATION,
            exists(
                select(1)
                .select_from(assets)
                .where(
                    assets.c.value["reference"].astext == ASSET,
                    assets.c.value["contract"].astext == CONTRACT,
                    assets.c.value["role"].astext == ROLE,
                    assets.c.value["content_digest"].astext == asset_digest,
                )
            ),
        )
    )
    require = function(
        "ops",
        "require_source_admission",
        parameters=(Parameter("p_release", column_type(finalization.c.release_id)),),
        returns=pg_type("void"),
        body=Block(
            (
                If(
                    or_(
                        ~exists(
                            select(1)
                            .select_from(finalization)
                            .where(finalization.c.release_id == release)
                        ),
                        ~admitted,
                    ),
                    (
                        Raise(
                            "source admission requires the exact finalized operation/helper asset",
                            "23514",
                        ),
                    ),
                ),
            )
        ),
        security_definer=True,
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )
    writer = func.pg_has_role(
        func.coalesce(func.nullif(func.current_setting("role"), "none"), func.session_user()),
        role_name("writer"),
        "MEMBER",
        type_=Boolean(),
    )
    payload = core_variable("p_payload", JSONB())
    initialize = function(
        "ops",
        "initialize_source_project",
        parameters=(Parameter("p_payload", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        body=Block(
            (
                Perform(func.ops.ddo_fields(payload, array(("project_id", "release_id")))),
                Perform(func.ops.require_source_admission(payload["release_id"].astext)),
                If(
                    ~writer,
                    (Raise("source initialization requires native write purpose", "42501"),),
                ),
                Sql(
                    insert(project)
                    .values(project_id=payload["project_id"].astext)
                    .on_conflict_do_nothing()
                ),
                PerformQuery(
                    select(literal(1))
                    .select_from(project)
                    .where(project.c.project_id == payload["project_id"].astext)
                    .with_for_update()
                ),
                Return(
                    func.jsonb_build_object(
                        "payload",
                        func.jsonb_build_object(
                            "project_id",
                            payload["project_id"].astext,
                            "release_id",
                            payload["release_id"].astext,
                        ),
                    )
                ),
            )
        ),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    fields = ("project_id", "source_uri", "content_hash", "original_path", "mime", "title", "meta")
    parameters = {name: core_variable("p_" + name, document.c[name].type) for name in fields}
    raw = core_variable("p_original", original.c.content.type)
    digest = core_variable("digest", document.c.content_hash.type)
    key = core_variable("document_key", document.c.key.type)
    identity_fields = (
        "project_id",
        "key",
        "source_uri",
        "content_hash",
        "original_path",
        "mime",
        "title",
        "meta",
    )
    expected = {**parameters, "key": key, "content_hash": digest}
    retained_fields = tuple(
        core_variable("retained", document.c[name].type, name) for name in identity_fields
    )
    returns = pg_type("kb", "document")
    returns.setof = True
    registration = function(
        "ops",
        "register_original_document",
        parameters=(
            Parameter("p_release", column_type(finalization.c.release_id)),
            *(Parameter("p_" + name, column_type(document.c[name])) for name in fields),
            Parameter("p_original", column_type(original.c.content)),
        ),
        returns=returns,
        body=Block(
            (
                Perform(func.ops.require_source_admission(release)),
                If(~writer, (Raise("source registration requires native write purpose", "42501"),)),
                If(
                    or_(raw.is_(None), parameters["content_hash"].is_distinct_from(digest)),
                    (Raise("original artifact differs from registered document", "23514"),),
                ),
                Assign(
                    "document_key",
                    literal("doc:").op("||")(
                        func.left(
                            func.ops.ddo_digest(
                                func.jsonb_build_object(
                                    "project",
                                    func.normalize(parameters["project_id"]),
                                    "source_uri",
                                    func.normalize(parameters["source_uri"]),
                                    "content_hash",
                                    digest,
                                )
                            ),
                            32,
                        )
                    ),
                ),
                Sql(
                    insert(document)
                    .values(expected)
                    .on_conflict_do_nothing(index_elements=(document.c.project_id, document.c.key))
                ),
                SelectInto(
                    select(core_relation_row(document))
                    .where(document.c.project_id == parameters["project_id"], document.c.key == key)
                    .with_for_update(read=True),
                    ("retained",),
                    strict=True,
                ),
                If(
                    tuple_(*retained_fields).is_distinct_from(
                        tuple_(*(expected[name] for name in identity_fields))
                    ),
                    (
                        Raise(
                            "source identity denotes another source descriptor",
                            "23505",
                            constraint="original_document_descriptor_identity",
                        ),
                    ),
                ),
                Sql(
                    insert(original)
                    .values(artifact_digest=digest, content=raw)
                    .on_conflict_do_nothing()
                ),
                If(
                    ~exists(
                        select(1)
                        .select_from(original)
                        .where(original.c.artifact_digest == digest, original.c.content == raw)
                    ),
                    (Raise("original artifact identity differs", "23505"),),
                ),
                ReturnNext(variable("retained")),
            ),
            (
                Local(
                    "digest",
                    column_type(document.c.content_hash),
                    func.encode(func.sha256(raw), "hex"),
                ),
                Local("document_key", column_type(document.c.key)),
                Local("retained", document),
            ),
        ),
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )
    return native_sql_script((require, initialize, registration))
