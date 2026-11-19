"""Compile original-byte custody and exact sealed PDF source capture proofs."""

from sqlalchemy import Boolean, Text, and_, case, column, func, literal, or_, select
from sqlalchemy.dialects.postgresql import JSONB, array

from corpus_structure.schema.integrity import role_name

from .data_operation_support import OriginalDocumentRef
from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    core_variable,
    pg_type,
)
from .native_program import literal as pg_literal
from .native_program_registry import ProgramDeclaration


def source_capture_native_programs(target) -> tuple[ProgramDeclaration, ...]:
    document = target.tables["kb.document"]
    artifact = target.tables["kb.source_artifact"]
    request = target.tables["ops.data_request"]
    derivation = target.tables["ops.data_derivation"]
    output = target.tables["ops.data_derivation_output"]
    intent = target.tables["ops.data_completion_intent"]
    product = target.tables["kb.data_product"]
    definition = target.tables["sem.data_operation_definition"]
    reference = core_variable("p_reference", JSONB())
    project = core_variable("p_project", Text())
    product_id = core_variable("p_product", Text())
    derivation_id = core_variable("p_derivation", Text())
    source = core_variable("p_source", Text())
    read = core_variable("p_read", Text())
    body = core_variable("body", JSONB())
    coordinate = core_variable("coordinate", JSONB())
    original = core_variable("original", artifact.c.content.type)
    receipts = core_variable("receipts", JSONB())
    receipt = core_variable("receipt", JSONB())
    expected = core_variable("expected", JSONB())
    consumer = core_variable("consumer", Text())
    producer = core_variable("producer", Text())
    object_ = func.jsonb_build_object

    def field(local, table, name):
        return core_variable(local, table.c[name].type, name)

    def routine(name, parameters, steps, locals_=(), *, access=INTERNAL_PROGRAM):
        routine = NativeRoutine(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type("jsonb"),
            body=Block(steps, locals_),
            volatility="stable",
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )
        return ProgramDeclaration(
            routine,
            source="data-operation-source-admission:forward",
            owner=role_name("publisher"),
            access=access,
        )

    def refuse(condition, message, *, state="23514"):
        return If(condition, (Raise(message, state),))

    document_view = routine(
        "ddo_original_document_view",
        (Parameter("p_reference", pg_type("jsonb")),),
        (
            Perform(
                func.ops.ddo_fields(
                    reference, array(list(OriginalDocumentRef.model_fields), type_=Text())
                )
            ),
            refuse(
                reference["kind"].astext.is_distinct_from("original-document"),
                "original document reference discriminator differs",
                state="P0001",
            ),
            SelectInto(
                select(document).where(
                    *(
                        document.c[column] == reference[key].astext
                        for column, key in (
                            ("project_id", "project_id"),
                            ("key", "document_key"),
                            ("content_hash", "content_hash"),
                            ("mime", "mime"),
                        )
                    )
                ),
                ("document",),
                strict=True,
            ),
            SelectInto(
                select(artifact.c.content).where(
                    artifact.c.artifact_digest == field("document", document, "content_hash")
                ),
                ("original",),
                strict=True,
            ),
            refuse(
                func.encode(func.sha256(original), "hex").is_distinct_from(
                    field("document", document, "content_hash")
                ),
                "original document retained byte digest differs",
                state="P0001",
            ),
            Assign(
                "body",
                object_(
                    "document",
                    field("document", document, "key"),
                    "content_hash",
                    field("document", document, "content_hash"),
                    "mime",
                    field("document", document, "mime"),
                ),
            ),
            Assign("coordinate", object_("document", field("document", document, "key"))),
            Return(
                object_(
                    "body",
                    body,
                    "meaning_body",
                    func.data.ddo_normalize(func.data.record_json_meaning(body)),
                    "subject_definition",
                    "original-document",
                    "subject",
                    literal("original-document:").concat(func.ops.ddo_digest(coordinate)),
                    "original_source",
                    field("document", document, "key"),
                    "analyzed_scope",
                    object_(
                        "document", field("document", document, "key"), "scope", "whole-document"
                    ),
                    "evidence",
                    object_(
                        "reference",
                        reference,
                        "document_id",
                        field("document", document, "id"),
                        "document_content_hash",
                        field("document", document, "content_hash"),
                        "source_uri",
                        field("document", document, "source_uri"),
                        "original_path",
                        field("document", document, "original_path"),
                    ),
                )
            ),
        ),
        (
            Local("document", document),
            Local("original", pg_type("bytea")),
            Local("body", pg_type("jsonb")),
            Local("coordinate", pg_type("jsonb")),
        ),
    )
    pdf_receipt = routine(
        "ddo_pdf_derivation_receipt",
        (
            Parameter("p_project", pg_type("text")),
            Parameter("p_product", pg_type("text")),
            Parameter("p_derivation", pg_type("text")),
            Parameter("p_source", pg_type("text"), pg_literal(None)),
            Parameter("p_read", pg_type("ops", "data_demand_read"), pg_literal(None)),
        ),
        (
            refuse(
                ~func.ops.ddo_node_valid("episode", derivation_id, read, type_=Boolean()),
                "PDF derivation support is not admitted at selected read",
            ),
            SelectInto(
                select(derivation)
                .select_from(derivation.join(output, output.c.derivation_id == derivation.c.id))
                .where(
                    derivation.c.id == derivation_id,
                    output.c.product_id == product_id,
                    output.c.member_id.is_(None),
                ),
                ("derivation",),
                strict=True,
            ),
            Assign(
                "producer",
                func.ops.ddo_pdf_producing_request(field("derivation", derivation, "id")),
            ),
            refuse(
                or_(
                    field("producer", request, "project_id").is_distinct_from(project),
                    source.is_not(None)
                    & field("producer", request, "original_source").is_distinct_from(source),
                ),
                "PDF producer is outside exact qualified selected source",
            ),
            Perform(func.ops.ddo_authorize_request(producer)),
            refuse(
                ~select(definition.c.operation_id)
                .where(
                    definition.c.release_id == field("derivation", derivation, "release_id"),
                    definition.c.operation_id == field("producer", request, "operation_id"),
                    func.coalesce(definition.c.command_class == "pdf", False),
                )
                .exists(),
                "selected source derivation is not an exact approved native PDF command",
            ),
            Perform(
                func.ops.require_pdf_operation(
                    field("producer", request, "release_id"), "read_native_source"
                )
            ),
            SelectInto(
                select(intent).where(intent.c.id == field("derivation", derivation, "intent_id")),
                ("intent",),
                strict=True,
            ),
            SelectInto(
                select(product).where(
                    product.c.id == product_id,
                    product.c.project_id == project,
                    product.c.original_source == field("producer", request, "original_source"),
                ),
                ("product",),
                strict=True,
            ),
            Assign(
                "receipts", field("intent", intent, "payload")["execution_evidence"]["pdf_receipts"]
            ),
            refuse(
                or_(
                    func.jsonb_typeof(receipts).is_distinct_from("array"),
                    func.jsonb_array_length(receipts) != 1,
                ),
                "selected PDF capture lacks one retained sealed publication",
            ),
            Assign("receipt", receipts[0]),
            Assign(
                "expected",
                func.ops.pdf_publication_projection(
                    receipt,
                    field("intent", intent, "producer_task_id"),
                    field("intent", intent, "producer_attempt"),
                    field("intent", intent, "producer_holder"),
                ),
            ),
            refuse(
                or_(
                    func.data.ddo_json(
                        field("product", product, "canonical_body")
                    ).is_distinct_from(expected),
                    expected["document"].astext.is_distinct_from(
                        field("producer", request, "original_source")
                    ),
                ),
                "selected PDF capture body differs from actual sealed publication",
            ),
            Return(receipt),
        ),
        (
            Local("producer", request),
            Local("derivation", derivation),
            Local("intent", intent),
            Local("product", product),
            *(Local(name, pg_type("jsonb")) for name in ("receipts", "receipt", "expected")),
        ),
    )
    capture = routine(
        "ddo_pdf_capture_source",
        (
            Parameter("p_request", pg_type("text")),
            Parameter("p_project", pg_type("text")),
            Parameter("p_product", pg_type("text")),
            Parameter("p_derivation", pg_type("text")),
        ),
        (
            SelectInto(
                select(request).where(
                    request.c.id == core_variable("p_request", request.c.id.type),
                    request.c.project_id == project,
                ),
                ("consumer",),
                strict=True,
            ),
            Return(
                func.ops.ddo_pdf_capture_source_for_request(
                    consumer, project, product_id, derivation_id
                )
            ),
        ),
        (Local("consumer", request),),
        access=NativeProgramAccess(purposes=("write",)),
    )
    selected_inputs = (
        func.jsonb_array_elements(field("consumer", request, "binding")["inputs"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="selected_input")
    )
    selected_support = (
        func.jsonb_array_elements(field("consumer", request, "binding")["support"])
        .table_valued(column("value", JSONB()))
        .render_derived(name="selected_support")
    )
    selected_proof = case(
        (
            and_(
                selected_inputs.c.value["product_id"].astext == product_id,
                selected_inputs.c.value["member_id"].astext.is_(None),
            ),
            func.ops.ddo_single_input_support_episode(selected_inputs.c.value) == derivation_id,
        ),
        else_=False,
    )
    capture_for_request = routine(
        "ddo_pdf_capture_source_for_request",
        (
            Parameter("consumer", pg_type("ops", "data_request")),
            Parameter("p_project", pg_type("text")),
            Parameter("p_product", pg_type("text")),
            Parameter("p_derivation", pg_type("text")),
        ),
        (
            refuse(
                field("consumer", request, "project_id").is_distinct_from(project),
                "PDF source consumer changes its qualified project",
            ),
            Perform(func.ops.ddo_authorize_request(consumer)),
            refuse(
                or_(
                    ~select(selected_inputs.c.value).where(selected_proof).exists(),
                    ~select(selected_support.c.value)
                    .where(selected_support.c.value["derivation_id"].astext == derivation_id)
                    .exists(),
                ),
                "PDF source is outside exact selected computational support",
            ),
            Return(
                func.ops.ddo_pdf_derivation_receipt(
                    project,
                    product_id,
                    derivation_id,
                    field("consumer", request, "original_source"),
                )
            ),
        ),
    )
    return document_view, pdf_receipt, capture, capture_for_request


def source_capture_native_sql(target) -> str:
    """Render captured source proofs from their owned declarations."""
    return (
        ";\n".join(item.routine.render() for item in source_capture_native_programs(target)) + ";\n"
    )
