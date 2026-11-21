"""Model-owned original producer and immutable recovery contributor custody."""

import json

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    MetaData,
    Table,
    Text,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    literal,
    not_,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, aggregate_order_by, insert

from corpus_structure.schema.integrity import role_name

from .metadata import get_metadata
from .native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    native_privilege_sql,
    native_sql_script,
)
from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    Sql,
    column_type,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration

# The lowering contract supplies the derived code basis plus explicit schemas
# and codecs. Transport custody remains outside these producing inputs.
SPOOL_MATERIAL_PREFIX = "pdf-domain/implementation/pdf/lowering/"
SPOOL_REQUIRED_MATERIAL = frozenset(
    SPOOL_MATERIAL_PREFIX + name
    for name in ("code/meaning.json", "schema/docling-native.json", "codec/inline-candidates.arrow")
)


def spool_material_document(content: bytes) -> dict:
    """Project archived lowering custody; absence is never inferred equivalence."""
    document = json.loads(content)
    if (
        set(document) != {"profile", "compiler_policy", "code_identity", "inputs", "libraries"}
        or document["profile"] not in {"pdf-record-lowering-contract-v2", "pdf-record-lowering-contract-v3"}
        or not isinstance(document.get("code_identity"), dict)
        or document["code_identity"].get("complete") is not True
        or not isinstance(document["libraries"], dict)
        or not document["libraries"]
    ):
        raise ValueError("PDF spool has no supported original lowering snapshot")
    if document["profile"] == "pdf-record-lowering-contract-v3" and (
        document["code_identity"].get("scope") != "docling-standard-pdf-stream-v1"
    ):
        raise ValueError("PDF spool lowering snapshot does not admit this producer scope")
    inputs = document["inputs"]
    if (
        not isinstance(inputs, list)
        or any(not isinstance(item, dict) or set(item) != {"name", "sha256"} for item in inputs)
        or len({item["name"] for item in inputs}) != len(inputs)
    ):
        raise ValueError("PDF spool lowering inventory is not exact")
    selected = sorted(
        (item for item in inputs if item["name"].startswith(SPOOL_MATERIAL_PREFIX)),
        key=lambda item: item["name"],
    )
    if not SPOOL_REQUIRED_MATERIAL.issubset({item["name"] for item in selected}):
        raise ValueError("PDF spool is missing original output-contract snapshots")
    return {"profile": document["profile"], "libraries": document["libraries"], "inputs": selected}


def pdf_spool_native_programs(
    *, target_metadata: MetaData | None = None
) -> tuple[ProgramDeclaration, ...]:
    """Compile current spool fences from the supplied captured physical model."""
    model = get_metadata() if target_metadata is None else target_metadata
    build = model.tables["ops.pdf_stage_build"]
    producers = model.tables["ops.pdf_spool_producer"]
    contributors = model.tables["ops.pdf_spool_contributor"]
    runtime = model.tables["sem.runtime_binding"]
    inputs = model.tables["sem.input"]
    origins = model.tables["ops.data_execution_origin"]
    requests = model.tables["ops.data_request"]
    originals = model.tables["ops.original_source_admission"]

    def value(name, field):
        return core_variable(name, field.type)

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    def obj(**pairs):
        return func.jsonb_build_object(
            *(part for name, item in pairs.items() for part in (literal(name), item))
        )

    def digest(raw):
        return func.encode(func.sha256(raw), "hex")

    def json_digest(*parts):
        return digest(func.convert_to(cast(func.jsonb_build_array(*parts), Text()), "UTF8"))

    def json_bytes(raw):
        return cast(func.convert_from(raw, "UTF8"), JSONB())

    def refuse(condition, message, state="P0001"):
        return If(condition, (Raise(message, state),))

    def request_material_projection(snapshot):
        # An admission ID is current authorization custody. Its immutable selected
        # facts determine the output, after the exact recorded admission is valid.
        support = snapshot["binding"]["support"]
        support_rows = (
            func.jsonb_array_elements(
                case(
                    (func.jsonb_typeof(support) == "array", support),
                    else_=cast(literal("[]"), JSONB()),
                )
            )
            .table_valued(column("value", JSONB()), with_ordinality="ordinal")
            .render_derived(name="spool_support")
        )
        item = support_rows.c.value
        admission = originals.alias("spool_original")
        joined = support_rows.outerjoin(admission, admission.c.id == item["admission_id"].astext)
        is_original = item["kind"].astext == "original-source"
        valid = func.coalesce(
            func.ops.ddo_original_admission_valid(
                admission.table_valued(), literal(None), type_=Boolean()
            ),
            False,
        )
        invalid_original = (
            select(1)
            .select_from(joined)
            .where(
                is_original,
                or_(
                    admission.c.id.is_(None),
                    admission.c.reference["kind"].astext.is_distinct_from("original-document"),
                    admission.c.project_id.is_distinct_from(snapshot["project_id"].astext),
                    admission.c.source_reference.is_distinct_from(item["source_reference"].astext),
                    ~valid,
                ),
            )
            .exists()
        )
        material = obj(
            **{
                name: admission.c[name]
                for name in (
                    "project_id",
                    "source_reference",
                    "reference",
                    "selectors",
                    "product_id",
                    "subject",
                    "original_source",
                    "analyzed_scope",
                    "evidence",
                )
            }
        )
        projected = case(
            (is_original, item.op("-")("admission_id").concat(obj(admission_material=material))),
            else_=item,
        )
        support_material = (
            select(
                func.coalesce(
                    func.jsonb_agg(aggregate_order_by(projected, support_rows.c.ordinal)),
                    cast(literal("[]"), JSONB()),
                )
            )
            .select_from(joined)
            .scalar_subquery()
        )
        return case(
            (
                or_(
                    snapshot.is_(None),
                    func.jsonb_typeof(support).is_distinct_from("array"),
                    invalid_original,
                ),
                cast(literal(None), JSONB()),
            ),
            else_=obj(
                **{
                    name: snapshot[name]
                    for name in (
                        "project_id",
                        "operation_id",
                        "subject",
                        "subject_definition",
                        "original_source",
                        "analyzed_scope",
                        "replicate",
                    )
                },
                binding=obj(
                    **{
                        name: snapshot["binding"][name]
                        for name in (
                            "inputs",
                            "parameters",
                            "request_inputs",
                            "inference",
                            "execution_profile",
                            "populations",
                        )
                    },
                    support=support_material,
                ),
            ),
        )

    def request_material(snapshot):
        return func.ops.pdf_spool_request_material(snapshot, type_=JSONB())

    def matching_requests(prior, current):
        old, new = request_material(prior), request_material(current)
        return and_(old.is_not(None), new.is_not(None), old.is_not_distinct_from(new))

    def material_producer(producer):
        for name in (
            "runtime_id",
            "runtime_manifest_digest",
            "request_id",
            "generation",
            "release_id",
            "definition_identity",
            "definition",
            "pdf_domain_digest",
        ):
            producer = producer.op("-")(name)
        return producer

    def recovery_key(snapshot, producer, source, recipe, schema):
        return json_digest(
            request_material(snapshot), material_producer(producer), source, recipe, schema
        )

    def current_request(producer):
        definitions = model.tables["sem.data_operation_definition"]
        return (
            select(
                func.to_jsonb(requests.table_valued(), type_=JSONB()).concat(
                    obj(subject_definition=definitions.c.subject_definition)
                )
            )
            .select_from(
                requests.join(
                    definitions,
                    and_(
                        definitions.c.release_id == requests.c.release_id,
                        definitions.c.operation_id == requests.c.operation_id,
                    ),
                )
            )
            .where(requests.c.id == producer["request_id"].astext)
            .scalar_subquery()
        )

    def origin_snapshot():
        return origins.c.request_snapshot.concat(
            obj(subject_definition=origins.c.definition_snapshot["subject_definition"])
        )

    def origin_request(origin_id):
        return select(origin_snapshot()).where(origins.c.id == origin_id).scalar_subquery()

    empty_array = cast(literal("[]"), JSONB())
    p_build, p_task, p_attempt, p_holder, p_runtime = (
        value(name, field)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
            ("p_runtime", runtime.c.runtime_id),
        )
    )
    fence_fields = (
        ("p_build", build.c.build_id),
        ("p_task", build.c.task_id),
        ("p_attempt", build.c.attempt),
        ("p_holder", build.c.holder),
    )
    runtime_field = ("p_runtime", runtime.c.runtime_id)
    programs = []

    def routine(name, fields, statements, locals_, *, result=None, output=()):
        parameters = tuple(Parameter(name, column_type(field)) for name, field in fields)
        programs.append(
            NativeRoutine(
                "ops",
                name,
                parameters=parameters,
                returns=result or column_type(producers.c.producer_id),
                table_columns=tuple((name, column_type(field)) for name, field in output),
                body=Block(tuple(statements), tuple(locals_)),
                security_definer=True,
                search_path=("pg_catalog", "pg_temp"),
            )
        )

    # The native producer-basis routine owns its composite output. SELECT alias.*
    # retains every admitted field, including additions, without a second codec.
    basis = (
        func.ops.read_pdf_producer_basis(p_task, p_attempt, p_holder, p_runtime)
        .table_valued()
        .alias("spool_basis")
    )
    basis_row = core_relation_row(Table("spool_basis", MetaData()))
    require_build = Assign("b", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder))
    require_operation = Perform(
        func.ops.require_pdf_operation(row("b", build, "release_id"), "stage_pdf_producer")
    )
    material_request = core_variable("p_request", JSONB())
    routine(
        "pdf_spool_request_material",
        (("p_request", requests.c.binding),),
        (Return(request_material_projection(material_request)),),
        (),
        result=pg_type("jsonb"),
    )

    device, inode, premises_bytes = (
        value(name, field)
        for name, field in (
            ("p_device", producers.c.writer_device),
            ("p_inode", producers.c.writer_inode),
            ("p_premises", producers.c.premises_bytes),
        )
    )
    premises, identity = core_variable("premises_", JSONB()), value("id_", producers.c.producer_id)
    routine(
        "register_pdf_spool_producer",
        (
            *fence_fields,
            runtime_field,
            ("p_device", producers.c.writer_device),
            ("p_inode", producers.c.writer_inode),
            ("p_premises", producers.c.premises_bytes),
        ),
        (
            require_build,
            require_operation,
            SelectInto(select(basis_row).select_from(basis), ("basis_",), strict=True),
            Assign("premises_", json_bytes(premises_bytes)),
            refuse(
                or_(
                    device.is_(None),
                    device < 0,
                    inode.is_(None),
                    inode < 1,
                    premises["producer"].is_distinct_from(
                        func.to_jsonb(core_variable("basis_", JSONB()))
                    ),
                    premises["source_digest"].astext.is_distinct_from(
                        row("b", build, "source_digest")
                    ),
                    premises["native_recipe_digest"].astext.is_distinct_from(
                        row("b", build, "recipe_digest")
                    ),
                    premises["native_schema_digest"].astext.is_distinct_from(
                        row("b", build, "schema_digest")
                    ),
                    func.coalesce(premises["payload_schema_digest"].astext, "").bool_op("!~")(
                        "^[0-9a-f]{64}$"
                    ),
                    func.jsonb_typeof(premises["packages"]).is_distinct_from("array"),
                    func.jsonb_array_length(premises["packages"]) == 0,
                ),
                "PDF spool producer premises differ from admitted native basis",
                "23514",
            ),
            Assign(
                "origin_id_",
                func.ops.register_data_execution_origin(
                    obj(
                        request_id=premises["producer"]["request_id"].astext,
                        generation=premises["producer"]["generation"],
                        task_id=p_task,
                        attempt=p_attempt,
                        holder=p_holder,
                        runtime_id=p_runtime,
                    ),
                    type_=JSONB(),
                )["payload"]["origin_id"].astext,
            ),
            Assign("request_snapshot_", origin_request(core_variable("origin_id_", Text()))),
            refuse(
                request_material(core_variable("request_snapshot_", JSONB())).is_(None),
                "PDF spool producer lacks valid original support material",
                "23514",
            ),
            Assign("id_", json_digest(p_build, p_task, p_attempt, p_holder, device, inode)),
            Sql(
                insert(producers)
                .values(
                    producer_id=identity,
                    build_id=p_build,
                    task_id=p_task,
                    attempt=p_attempt,
                    holder=p_holder,
                    writer_device=device,
                    writer_inode=inode,
                    premises_bytes=premises_bytes,
                    execution_origin_id=core_variable("origin_id_", Text()),
                    recovery_key=recovery_key(
                        core_variable("request_snapshot_", JSONB()),
                        premises["producer"],
                        premises["source_digest"],
                        premises["native_recipe_digest"],
                        premises["native_schema_digest"],
                    ),
                )
                .on_conflict_do_nothing()
            ),
            SelectInto(
                select(core_relation_row(producers)).where(producers.c.producer_id == identity),
                ("prior",),
                strict=True,
            ),
            refuse(
                row("prior", producers, "premises_bytes").is_distinct_from(premises_bytes),
                "PDF spool producer replay differs",
                "23514",
            ),
            Return(identity),
        ),
        (
            Local("b", build),
            Local("basis_", pg_type("record")),
            Local("premises_", pg_type("jsonb")),
            Local("id_", column_type(producers.c.producer_id)),
            Local("origin_id_", pg_type("text")),
            Local("request_snapshot_", pg_type("jsonb")),
            Local("prior", producers),
        ),
    )
    p_producer, manifest_bytes, selected_bytes = (
        value(name, field)
        for name, field in (
            ("p_producer", producers.c.producer_id),
            ("p_manifest", contributors.c.manifest_bytes),
            ("p_selected", contributors.c.selected_replays),
        )
    )
    (
        original,
        current_basis,
        current_premises,
        header,
        declaration,
        entry,
        selected,
        replay,
        inventory,
    ) = (
        core_variable(name, JSONB())
        for name in (
            "original_",
            "current_basis_",
            "current_premises_",
            "header_",
            "declaration_",
            "entry_",
            "selected_",
            "replay_",
            "inventory_",
        )
    )
    lines, line = core_variable("lines_", ARRAY(Text())), core_variable("line_", Text())
    manifest_text = func.convert_from(manifest_bytes, "UTF8")
    manifest_digest, selection_digest, contributor_id = (
        value(name, field)
        for name, field in (
            ("manifest_", contributors.c.manifest_digest),
            ("selection_", contributors.c.selection_digest),
            ("id_", contributors.c.contributor_id),
        )
    )
    manifest_lines = (
        func.unnest(lines)
        .table_valued(column("value", Text()), with_ordinality="ordinal")
        .render_derived(name="manifest_line")
    )
    selected_rows = (
        func.jsonb_array_elements(selected)
        .table_valued(column("value", JSONB()))
        .render_derived(name="selected_replay")
    )
    inventory_rows = (
        func.jsonb_array_elements(inventory)
        .table_valued(column("value", JSONB()))
        .render_derived(name="inventory_member")
    )

    def material_domain_projection(release, domain_digest, name):
        lower, domain = inputs.alias(name + "_lowering"), inputs.alias(name + "_domain")
        document = json_bytes(lower.c.content)
        domain_document = json_bytes(domain.c.content)
        entries = (
            func.jsonb_array_elements(document["inputs"])
            .table_valued(column("value", JSONB()))
            .render_derived(name=name + "_input")
        )
        selected = entries.c.value["name"].astext.startswith(SPOOL_MATERIAL_PREFIX)
        selected_inputs = (
            select(
                func.jsonb_agg(aggregate_order_by(entries.c.value, entries.c.value["name"].astext))
            )
            .select_from(entries)
            .where(selected)
            .correlate(lower)
            .scalar_subquery()
        )
        declared = (
            func.jsonb_array_elements(domain_document["inputs"])
            .table_valued(column("value", JSONB()))
            .render_derived(name=name + "_declared")
        )
        required = tuple(
            select(1)
            .select_from(entries)
            .where(
                entries.c.value["name"].astext == required,
                func.coalesce(entries.c.value["sha256"].astext, "").bool_op("~")("^[0-9a-f]{64}$"),
            )
            .correlate(lower)
            .exists()
            for required in sorted(SPOOL_REQUIRED_MATERIAL)
        )
        return (
            select(
                obj(
                    profile=document["profile"],
                    libraries=document["libraries"],
                    inputs=selected_inputs,
                )
            )
            .select_from(lower.join(domain, lower.c.release_id == domain.c.release_id))
            .where(
                lower.c.release_id == release,
                lower.c.input_kind == "dependency",
                domain.c.input_kind == "dependency",
                lower.c.input_name == "pdf-domain/implementation/pdf/lowering-contract.json",
                domain.c.input_name == "pdf-domain/contract.json",
                lower.c.content_digest == digest(lower.c.content),
                domain.c.content_digest == digest(domain.c.content),
                domain.c.content_digest == domain_digest,
                document["profile"].astext.in_(("pdf-record-lowering-contract-v2", "pdf-record-lowering-contract-v3")),
                document["code_identity"]["complete"] == cast(literal("true"), JSONB()),
                or_(
                    document["profile"].astext == "pdf-record-lowering-contract-v2",
                    document["code_identity"]["scope"].astext == "docling-standard-pdf-stream-v1",
                ),
                document["code_identity"]["sha256"].astext.bool_op("~")("^[0-9a-f]{64}$"),
                func.jsonb_typeof(document["libraries"]) == "object",
                document["libraries"] != cast(literal("{}"), JSONB()),
                *required,
                select(1)
                .select_from(declared)
                .where(
                    declared.c.value["name"].astext == lower.c.input_name,
                    declared.c.value["sha256"].astext == lower.c.content_digest,
                )
                .correlate(domain, lower)
                .exists(),
            )
            .scalar_subquery()
        )

    material_release = core_variable("p_release", inputs.c.release_id.type)
    material_digest = core_variable("p_domain_digest", inputs.c.content_digest.type)
    routine(
        "pdf_spool_material_identity",
        (("p_release", inputs.c.release_id), ("p_domain_digest", inputs.c.content_digest)),
        (Return(material_domain_projection(material_release, material_digest, "material_pdf")),),
        (),
        result=pg_type("jsonb"),
    )

    def material_domains_match(prior, current):
        old = func.ops.pdf_spool_material_identity(
            prior["release_id"].astext, prior["pdf_domain_digest"].astext
        )
        new = func.ops.pdf_spool_material_identity(
            current["release_id"].astext, current["pdf_domain_digest"].astext
        )
        return func.coalesce(old == new, False)

    def retired_producer(producer, premises):
        failures = model.tables["ops.data_attempt_failure"]
        return (
            select(1)
            .select_from(failures)
            .where(
                failures.c.request_id == premises["producer"]["request_id"].astext,
                failures.c.generation
                == cast(premises["producer"]["generation"].astext, failures.c.generation.type),
                failures.c.task_id == row(producer, producers, "task_id"),
                failures.c.attempt == row(producer, producers, "attempt"),
                failures.c.holder == row(producer, producers, "holder"),
            )
            .exists()
        )

    # Discovery is only an authenticated candidate hint. Full manifest custody and
    # selected-file correspondence are independently enforced at contribution.
    candidate_premises = json_bytes(producers.c.premises_bytes)
    current_producer = core_variable("candidate_basis_", JSONB())
    failures = model.tables["ops.data_attempt_failure"]
    candidate_retired = (
        select(1)
        .select_from(failures)
        .where(
            failures.c.request_id == candidate_premises["producer"]["request_id"].astext,
            failures.c.generation
            == cast(
                candidate_premises["producer"]["generation"].astext, failures.c.generation.type
            ),
            failures.c.task_id == producers.c.task_id,
            failures.c.attempt == producers.c.attempt,
            failures.c.holder == producers.c.holder,
        )
        .exists()
    )
    candidate_output = (
        ("build_id", producers.c.build_id),
        ("task_id", producers.c.task_id),
        ("producer_id", producers.c.producer_id),
        ("attempt", producers.c.attempt),
        ("holder", producers.c.holder),
        ("writer_device", producers.c.writer_device),
        ("writer_inode", producers.c.writer_inode),
        ("premises_bytes", producers.c.premises_bytes),
    )
    candidate_result = pg_type("record")
    candidate_result.setof = True
    routine(
        "read_pdf_spool_recovery_candidates",
        (*fence_fields, runtime_field, ("p_premises", producers.c.premises_bytes)),
        (
            require_build,
            require_operation,
            SelectInto(select(basis_row).select_from(basis), ("basis_",), strict=True),
            Assign("candidate_basis_", func.to_jsonb(core_variable("basis_", JSONB()))),
            Assign("candidate_premises_", json_bytes(premises_bytes)),
            Assign("request_snapshot_", current_request(current_producer)),
            refuse(
                request_material(core_variable("request_snapshot_", JSONB())).is_(None),
                "PDF recovery lacks valid original support material",
                "23514",
            ),
            refuse(
                or_(
                    core_variable("candidate_premises_", JSONB())["producer"].is_distinct_from(
                        current_producer
                    ),
                    *(
                        core_variable("candidate_premises_", JSONB())[name].astext.is_distinct_from(
                            row("b", build, field)
                        )
                        for name, field in (
                            ("source_digest", "source_digest"),
                            ("native_recipe_digest", "recipe_digest"),
                            ("native_schema_digest", "schema_digest"),
                        )
                    ),
                ),
                "PDF recovery premises differ from current native basis",
                "23514",
            ),
            Assign(
                "candidate_recovery_key_",
                recovery_key(
                    core_variable("request_snapshot_", JSONB()),
                    current_producer,
                    func.to_jsonb(row("b", build, "source_digest")),
                    func.to_jsonb(row("b", build, "recipe_digest")),
                    func.to_jsonb(row("b", build, "schema_digest")),
                ),
            ),
            ReturnQuery(
                select(*(field for _, field in candidate_output))
                .select_from(
                    producers.join(origins, origins.c.id == producers.c.execution_origin_id)
                )
                .where(
                    candidate_retired,
                    candidate_premises.op("-")("producer").is_not_distinct_from(
                        core_variable("candidate_premises_", JSONB()).op("-")("producer")
                    ),
                    producers.c.recovery_key
                    == value("candidate_recovery_key_", producers.c.recovery_key),
                    producers.c.execution_origin_id.is_not(None),
                    matching_requests(
                        origin_snapshot(), core_variable("request_snapshot_", JSONB())
                    ),
                    material_producer(candidate_premises["producer"]).is_not_distinct_from(
                        material_producer(current_producer)
                    ),
                    material_domains_match(candidate_premises["producer"], current_producer),
                    candidate_premises["source_digest"].astext == row("b", build, "source_digest"),
                    candidate_premises["native_recipe_digest"].astext
                    == row("b", build, "recipe_digest"),
                    candidate_premises["native_schema_digest"].astext
                    == row("b", build, "schema_digest"),
                )
                .order_by(
                    producers.c.task_id.desc(), producers.c.attempt.desc(), producers.c.producer_id
                )
                .limit(64)
            ),
        ),
        (
            Local("b", build),
            Local("basis_", pg_type("record")),
            Local("candidate_basis_", pg_type("jsonb")),
            Local("candidate_premises_", pg_type("jsonb")),
            Local("request_snapshot_", pg_type("jsonb")),
            Local("candidate_recovery_key_", column_type(producers.c.recovery_key)),
        ),
        result=candidate_result,
        output=candidate_output,
    )

    routine(
        "register_pdf_spool_contributor",
        (
            *fence_fields,
            runtime_field,
            ("p_producer", producers.c.producer_id),
            ("p_manifest", contributors.c.manifest_bytes),
            ("p_selected", contributors.c.selected_replays),
        ),
        (
            require_build,
            require_operation,
            SelectInto(select(basis_row).select_from(basis), ("current_",), strict=True),
            SelectInto(
                select(core_relation_row(producers)).where(producers.c.producer_id == p_producer),
                ("producer_",),
                strict=True,
            ),
            Assign("original_", json_bytes(row("producer_", producers, "premises_bytes"))),
            Assign(
                "current_basis_",
                material_producer(func.to_jsonb(core_variable("current_", JSONB()))),
            ),
            SelectInto(
                select(json_bytes(producers.c.premises_bytes)).where(
                    producers.c.build_id == p_build,
                    producers.c.attempt == p_attempt,
                    producers.c.holder == p_holder,
                ),
                ("current_premises_",),
                strict=True,
            ),
            Assign(
                "original_request_",
                origin_request(row("producer_", producers, "execution_origin_id")),
            ),
            Assign("current_request_", current_request(current_premises["producer"])),
            refuse(
                request_material(core_variable("current_request_", JSONB())).is_(None),
                "PDF contribution lacks valid original support material",
                "23514",
            ),
            refuse(
                or_(
                    ~or_(
                        and_(
                            row("producer_", producers, "build_id") == p_build,
                            row("producer_", producers, "task_id") == p_task,
                            row("producer_", producers, "attempt") == p_attempt,
                            row("producer_", producers, "holder") == p_holder,
                            original.is_not_distinct_from(current_premises),
                        ),
                        and_(
                            retired_producer("producer_", original),
                            row("producer_", producers, "execution_origin_id").is_not(None),
                            matching_requests(
                                core_variable("original_request_", JSONB()),
                                core_variable("current_request_", JSONB()),
                            ),
                            material_producer(original["producer"]).is_not_distinct_from(
                                current_basis
                            ),
                            material_domains_match(
                                original["producer"], current_premises["producer"]
                            ),
                        ),
                    ),
                    original["source_digest"].astext.is_distinct_from(
                        row("b", build, "source_digest")
                    ),
                    original["native_recipe_digest"].astext.is_distinct_from(
                        row("b", build, "recipe_digest")
                    ),
                    original["native_schema_digest"].astext.is_distinct_from(
                        row("b", build, "schema_digest")
                    ),
                    original.op("-")("producer").is_distinct_from(
                        current_premises.op("-")("producer")
                    ),
                ),
                "PDF spool contributor has no matching original producer",
                "23514",
            ),
            refuse(
                or_(
                    manifest_bytes.is_(None),
                    func.octet_length(manifest_bytes) == 0,
                    func.right(manifest_text, 1) != "\n",
                ),
                "PDF spool manifest has no durable complete entries",
                "23514",
            ),
            Assign("lines_", func.string_to_array(func.rtrim(manifest_text, "\n"), "\n")),
            refuse(func.cardinality(lines) < 2, "PDF spool manifest lacks producer declaration"),
            Assign("header_", cast(lines[1], JSONB())),
            Assign("declaration_", cast(lines[2], JSONB())),
            refuse(
                or_(
                    header["version"].astext.is_distinct_from("pdf-build-spool-1"),
                    header["build_id"].astext.is_distinct_from(
                        row("producer_", producers, "build_id")
                    ),
                    *(
                        cast(header[key].astext, field.type).is_distinct_from(
                            row("producer_", producers, field.name)
                        )
                        for key, field in (
                            ("task_id", producers.c.task_id),
                            ("attempt", producers.c.attempt),
                        )
                    ),
                    header["holder"].astext.is_distinct_from(row("producer_", producers, "holder")),
                    *(
                        cast(header["writer"][key].astext, field.type).is_distinct_from(
                            row("producer_", producers, field.name)
                        )
                        for key, field in (
                            ("device", producers.c.writer_device),
                            ("inode", producers.c.writer_inode),
                        )
                    ),
                    declaration["producer_id"].astext.is_distinct_from(p_producer),
                    declaration["premises"].is_distinct_from(original),
                ),
                "PDF manifest differs from immutable original producer custody",
                "23514",
            ),
            # Ordered UNNEST is the original FOREACH over lines_[3:], retaining
            # duplicate manifest entries and the no-entry termination case.
            ForQuery(
                ("line_",),
                select(manifest_lines.c.value)
                .where(manifest_lines.c.ordinal >= 3)
                .order_by(manifest_lines.c.ordinal),
                (
                    Assign("entry_", cast(line, JSONB())),
                    If(
                        entry.bool_op("?")("replay"),
                        (
                            Assign(
                                "inventory_",
                                inventory.concat(func.jsonb_build_array(entry["replay"])),
                            ),
                        ),
                        (
                            refuse(
                                not_(entry.bool_op("?")("completion")),
                                "PDF spool manifest entry is not declared",
                            ),
                        ),
                    ),
                ),
            ),
            Assign("selected_", json_bytes(selected_bytes)),
            refuse(
                or_(
                    func.jsonb_typeof(selected).is_distinct_from("array"),
                    func.jsonb_array_length(selected) == 0,
                ),
                "PDF spool contributor selected no files",
            ),
            ForQuery(
                ("replay_",),
                select(selected_rows.c.value),
                (
                    refuse(
                        or_(
                            not_(
                                exists(
                                    select(1)
                                    .select_from(inventory_rows)
                                    .where(inventory_rows.c.value == replay)
                                )
                            ),
                            func.coalesce(replay["digest"].astext, "").bool_op("!~")(
                                "^[0-9a-f]{64}$"
                            ),
                            cast(replay["byte_length"].astext, BigInteger()) < 0,
                            func.nullif(replay["path"].astext, "").is_(None),
                        ),
                        "selected PDF replay differs from original manifest membership",
                        "23514",
                    ),
                ),
            ),
            refuse(
                func.jsonb_array_length(selected).is_distinct_from(
                    select(
                        func.count(selected_rows.c.value["path"].astext.distinct())
                    ).scalar_subquery()
                ),
                "PDF spool contributor repeats a selected path",
            ),
            Assign("manifest_", digest(manifest_bytes)),
            Assign("selection_", digest(selected_bytes)),
            Assign("id_", json_digest(p_build, p_producer, manifest_digest, selection_digest)),
            Sql(
                insert(contributors)
                .values(
                    contributor_id=contributor_id,
                    build_id=p_build,
                    producer_id=p_producer,
                    manifest_digest=manifest_digest,
                    selection_digest=selection_digest,
                    manifest_bytes=manifest_bytes,
                    selected_replays=selected_bytes,
                    adopter_attempt=p_attempt,
                    adopter_holder=p_holder,
                )
                .on_conflict_do_nothing()
            ),
            SelectInto(
                select(core_relation_row(contributors)).where(
                    contributors.c.contributor_id == contributor_id
                ),
                ("prior",),
                strict=True,
            ),
            refuse(
                or_(
                    row("prior", contributors, "manifest_bytes").is_distinct_from(manifest_bytes),
                    row("prior", contributors, "selected_replays").is_distinct_from(selected_bytes),
                ),
                "PDF contributor replay differs",
            ),
            Return(contributor_id),
        ),
        (
            Local("b", build),
            Local("producer_", producers),
            Local("current_", pg_type("record")),
            *(
                Local(name, pg_type("jsonb"))
                for name in (
                    "original_",
                    "current_basis_",
                    "current_premises_",
                    "original_request_",
                    "current_request_",
                    "header_",
                    "declaration_",
                    "entry_",
                    "selected_",
                    "replay_",
                )
            ),
            Local("inventory_", pg_type("jsonb"), empty_array),
            Local("lines_", column_type(Column("lines_", ARRAY(Text())))),
            Local("line_", pg_type("text")),
            Local("id_", column_type(contributors.c.contributor_id)),
            Local("manifest_", column_type(contributors.c.manifest_digest)),
            Local("selection_", column_type(contributors.c.selection_digest)),
            Local("prior", contributors),
        ),
    )
    output = (
        ("producer_id", producers.c.producer_id),
        ("task_id", producers.c.task_id),
        ("producer_attempt", producers.c.attempt),
        ("producer_holder", producers.c.holder),
        ("runtime_id", runtime.c.runtime_id),
        ("runtime_manifest_digest", inputs.c.content_digest),
        ("manifest_digest", contributors.c.manifest_digest),
        ("selection_digest", contributors.c.selection_digest),
        ("adopter_attempt", contributors.c.adopter_attempt),
        ("adopter_holder", contributors.c.adopter_holder),
    )
    producer_json = json_bytes(producers.c.premises_bytes)["producer"]
    summary = obj(
        producer_id=producers.c.producer_id,
        task_id=producers.c.task_id,
        producer_attempt=producers.c.attempt,
        producer_holder=producers.c.holder,
        runtime_id=producer_json["runtime_id"].astext,
        runtime_manifest_digest=producer_json["runtime_manifest_digest"].astext,
        manifest_digest=contributors.c.manifest_digest,
        selection_digest=contributors.c.selection_digest,
        adopter_attempt=contributors.c.adopter_attempt,
        adopter_holder=contributors.c.adopter_holder,
    )
    aggregate = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        summary,
                        producers.c.producer_id,
                        contributors.c.manifest_digest,
                        contributors.c.selection_digest,
                    )
                ),
                empty_array,
            )
        )
        .select_from(
            contributors.join(producers, producers.c.producer_id == contributors.c.producer_id)
        )
        .where(contributors.c.build_id == p_build)
    )
    summary_parameters = (Parameter("p_build", column_type(build.c.build_id)),)
    programs.append(
        NativeRoutine(
            "ops",
            "pdf_spool_contributors",
            parameters=summary_parameters,
            returns=pg_type("jsonb"),
            body=aggregate,
            volatility="stable",
            search_path=("pg_catalog", "pg_temp"),
        )
    )
    returned = (
        func.jsonb_to_recordset(func.ops.pdf_spool_contributors(p_build))
        .table_valued(*(column(name, field.type) for name, field in output))
        .render_derived(name="r", with_types=True)
    )
    result = pg_type("record")
    result.setof = True
    routine(
        "read_pdf_spool_contributors",
        fence_fields,
        (
            Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)),
            refuse(
                not_(
                    exists(
                        select(1)
                        .select_from(build)
                        .where(build.c.build_id == p_build, build.c.task_id == p_task)
                    )
                ),
                "PDF contributor read has no owned build",
            ),
            ReturnQuery(
                select(returned).order_by(
                    returned.c.producer_id, returned.c.manifest_digest, returned.c.selection_digest
                )
            ),
        ),
        (),
        result=result,
        output=output,
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="native/pdf-staging.sql",
            owner=role_name("publisher"),
            access=(
                INTERNAL_PROGRAM
                if routine.name
                in {
                    "pdf_spool_contributors",
                    "pdf_spool_material_identity",
                    "pdf_spool_request_material",
                }
                else NativeProgramAccess(purposes=("write",))
            ),
        )
        for routine in programs
    )


def pdf_spool_native_sql(*, target_metadata: MetaData | None = None) -> str:
    """Render the unchanged captured source from its typed owner declarations."""
    programs = pdf_spool_native_programs(target_metadata=target_metadata)
    return (
        native_sql_script(
            (
                *(program.routine.render() for program in programs),
                *(
                    native_privilege_sql(program.identity, "PUBLIC", grant=False)
                    for program in programs
                ),
                *(
                    native_privilege_sql(program.identity, role_name("writer"), "execute")
                    for program in programs
                    if program.access.purposes
                ),
            )
        )
        + "\n"
    )
