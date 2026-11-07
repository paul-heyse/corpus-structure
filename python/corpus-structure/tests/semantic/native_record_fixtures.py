"""Small controlled native publications for maintained source-consumer journeys."""

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from importlib.resources import files
from math import sqrt
from types import SimpleNamespace
from typing import Any

import pyarrow as pa
import pytest
import yaml
from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel, TableCell, TableData
from pydantic import BaseModel, create_model
from sqlalchemy import insert, select

from corpus_structure.core.method import ObservationDraft, SourceViewDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, TaskUnitType
from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_health import FormulaOutcome
from corpus_structure.ingest.pdf_hierarchy import snapshot
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.methods.contextual_embeddings import (
    EncodedVector,
    EncoderProfile,
    identity,
)
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.contextual_links import (
    RelationshipConstraint,
    RelationshipWitness,
    select_relationships,
)
from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
)
from corpus_structure.semantic.contextual_storage import (
    enrichment_report,
)
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import bind_result, observation_inputs
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    complete_unit_result,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product, store_pdf_original
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, begin_pdf_build
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.source_views import store_source_view
from corpus_structure.semantic.types import PreparedRelease


def qualified_view_draft(draft, release_id):
    from dataclasses import replace

    from corpus_structure.ingest.pdf_hierarchy import section_text_recipe, section_view_key

    recipe = section_text_recipe(draft.native_product, analysis_eligible=draft.analysis_eligible)
    return replace(
        draft,
        key=section_view_key(
            release_id,
            draft.native_product,
            draft.section_pointer,
            draft.membership,
            draft.analysis_eligible,
            recipe,
        ),
        recipe_bytes=recipe,
    )


def publish_native_record_fixture(
    engine, directory, *, task_id, attempt, holder, product, document
):
    """Exercise the production stage/freeze/validate/seal phases with the fixture's native graph."""
    values = product.values()
    with engine.begin() as conn:
        build = begin_pdf_build(
            conn,
            task_id=task_id,
            attempt=attempt,
            holder=holder,
            source_digest=sha256(product.original).hexdigest(),
            recipe_digest=sha256(product.recipe_bytes).hexdigest(),
            schema_digest=sha256(product.schema_bytes).hexdigest(),
            replay_key="fixture-records:" + values["product_key"],
        )
    result = StreamingPdfResult(
        document,
        PdfStreamSpool(directory / "pages"),
        values["health"]["conversion"],
        tuple(values["health"].get("issues", ())),
        product.recipe_bytes,
        tuple(
            FormulaOutcome(row["pointer"], row["outcome"], row.get("error"))
            for row in values["health"].get("formula_outcomes", ())
        ),
    )
    for replay in result.write_record_batches(
        directory / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
    ):
        with pa.memory_map(str(replay.path), "r") as source:
            batches = pa.ipc.open_file(source)
            for index in range(batches.num_record_batches):
                with engine.begin() as conn:
                    adopt_pdf_batch(
                        conn,
                        build,
                        f"{replay.family}:{index}",
                        {
                            replay.family: (batches.get_batch(index),),
                        },
                    )
    with engine.begin() as conn:
        health = dict(values["health"])
        outcomes = health.pop("formula_outcomes", ())
        wrapper = dict(health, source_scope=values["source_scope"])
        for key in ("page_start", "page_end"):
            if key in values:
                wrapper[key] = values[key]
        adopt_pdf_companion_batch(conn, build, "health", (wrapper,), "fixture-health")
        if values.get("parent_task_id") is not None:
            adopt_pdf_companion_batch(
                conn,
                build,
                "input",
                (
                    dict(
                        role="structural",
                        task_id=values["parent_task_id"],
                        product_key=values["parent_product_key"],
                        content_digest=values["parent_digest"],
                    ),
                ),
                "fixture-parent",
            )
        metadata = []
        for kind, records in (
            ("formula_outcomes", outcomes),
            *(
                (kind, values.get(kind, ()))
                for kind in (
                    "derivation_mappings",
                    "cell_reports",
                    "inline_alignment_reports",
                    "recognition_coverage",
                    "inline_candidate_pages",
                )
            ),
            ("runtime_report", (values["runtime_report"],) if "runtime_report" in values else ()),
        ):
            metadata.extend(
                dict(kind=kind, ordinal=index, value=value) for index, value in enumerate(records)
            )
        if metadata:
            adopt_pdf_companion_batch(conn, build, "native_metadata", metadata, "fixture-metadata")
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        return seal_pdf_build(conn, frozen, values["product_key"])


class RawReport(BaseModel):
    source_text: str


def prepare_record_source(*, bundle_transform=None, additional_methods=()):
    """Pure original inputs and prepared release; no database, PDF or task effects."""
    schema = dict(
        id="https://example/private-records",
        name="private_records",
        imports=["core"],
        prefixes={"ex": "https://example/"},
        default_prefix="ex",
        classes={
            "FixtureConditionalField": dict(
                is_a="RequiredLiteralRecordField",
                rules=[
                    dict(
                        preconditions=dict(
                            slot_conditions=dict(state=dict(equals_string="present"))
                        ),
                        postconditions=dict(
                            slot_conditions=dict(
                                reason=dict(required=True, equals_string="source-read")
                            )
                        ),
                    )
                ],
            ),
            "FixtureRecordFields": dict(
                is_a="SemanticRecordFields",
                attributes={
                    "family": dict(equals_string="table"),
                    "occurrence_recipe": dict(equals_string="source-anchor-membership-1"),
                    "value": dict(range="FixtureConditionalField", required=True, inlined=True),
                    "location": dict(
                        range="RequiredNativeRecordField", required=True, inlined=True
                    ),
                },
            ),
        },
    )
    bundle = observation_inputs(
        SourceBundle(
            "domain",
            (
                SourceArtifact(
                    "core",
                    files("corpus_structure").joinpath("model/semantic/core.yaml").read_bytes(),
                ),
                SourceArtifact("domain", yaml.safe_dump(schema).encode()),
            ),
        )
    )
    if bundle_transform is not None:
        bundle = bundle_transform(bundle)
    dependencies = domain_rule_inputs(ResolvedDependencies(), b"rules: []\n")
    bundle, dependencies = analytical_inputs(bundle, dependencies)
    from .method_dimensions_support import fixture_execution_inputs

    dependencies = composed_dependencies(
        dependencies,
        fixture_execution_inputs(
            "private.source",
            "private.records",
            *additional_methods,
        ),
    )
    profile = PreparationProfile(version="semantic-2")
    prepared = prepare_release(bundle, dependencies, profile)
    return RecordPreparation(bundle, dependencies, profile, prepared)


@dataclass(frozen=True)
class RecordPreparation:
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    prepared: PreparedRelease

    @property
    def preparation_inputs(self):
        return self.bundle, self.dependencies, self.profile


def build_record_source(
    admin,
    writer,
    directory,
    preparation,
    *,
    include_blank_cell=False,
    record_method_spec=None,
    sibling_captions=(),
    sibling_references=(),
    project_id="private-records",
):
    """Publish the selected pure preparation and acquire one leased record task."""
    bundle, dependencies, profile = preparation.preparation_inputs
    prepared = preparation.prepared
    semantic_db_engine, semantic_writer_engine, tmp_path = admin, writer, directory
    realization = "private-input" if project_id == "private-records" else f"{project_id}-input"
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id=project_id))
        conn.execute(
            insert(table("data.realization")).values(
                project_id=project_id,
                realization_id=realization,
                release_id=prepared.release_id,
            )
        )
    original, recipe = b"%PDF-1.7\nprivate source record fixture", b'{"recipe":"private-records-1"}'
    if project_id != "private-records":
        original += b"\n" + project_id.encode()
    doc = DoclingDocument(name="Two independent native cells")
    section = doc.add_group(label=GroupLabel.SECTION, name="Measurements")
    native_table = doc.add_table(
        parent=section,
        data=TableData(
            num_rows=1,
            num_cols=3 if include_blank_cell else 2,
            table_cells=[
                TableCell(
                    text="" if column == 2 else "12",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=column,
                    end_col_offset_idx=column + 1,
                )
                for column in range(3 if include_blank_cell else 2)
            ],
        ),
    )
    sibling = doc.add_group(label=GroupLabel.SECTION, name="Other source")
    sibling_texts = (*sibling_captions, *sibling_references) or ("12",)
    sibling_items = tuple(
        doc.add_text(
            label=DocItemLabel.CAPTION if position < len(sibling_captions) else DocItemLabel.TEXT,
            text=literal,
            orig=literal,
            parent=sibling,
        )
        for position, literal in enumerate(sibling_texts)
    )
    sibling_projection = "\n".join(sibling_texts)
    sibling_pieces = []
    offset = 0
    for item, literal in zip(sibling_items, sibling_texts, strict=True):
        if offset:
            sibling_pieces.append(dict(kind="synthetic_separator", start=offset, end=offset + 1))
            offset += 1
        sibling_pieces.append(
            dict(
                kind="native_text",
                item_ref=item.self_ref,
                source_field="text",
                start=offset,
                end=offset + len(literal),
            )
        )
        offset += len(literal)
    native_schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    payload = publication_payload(
        PdfConversion(
            sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
        ),
        product_key="native",
        schema_digest=sha256(native_schema).hexdigest(),
        section_refs=frozenset((section.self_ref, sibling.self_ref)),
    )
    product = prepare_pdf_product(payload, original, native_schema, recipe)
    writer = semantic_writer_engine
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id=project_id,
            binding=OperationBinding(prepared.release_id, realization, 0, b"{}"),
            kind="full",
            options={},
            code_commit="private-records-test",
        )
        method = SimpleNamespace(
            name="private.source",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("PrivateSourceConfig"),
        )
        config = record_method(
            conn, method, "default", {}, "private-source-config", prepared=prepared
        )
        path = tmp_path / "source.pdf"
        path.write_bytes(original)
        document = register_document(
            conn,
            project_id=project_id,
            source_uri="source.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        source_task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="source.pdf",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="private-source")[0]
        store_pdf_original(
            conn,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            original=original,
            recipe_bytes=recipe,
        )
    published = publish_native_record_fixture(
        writer,
        tmp_path / "native",
        task_id=source_task,
        attempt=claim.attempt,
        holder="private-source",
        product=product,
        document=doc,
    )
    reference = ProductReference(source_task, "native", published.logical_digest)
    with writer.begin() as conn:
        draft = SourceViewDraft(
            "private-view",
            document,
            reference,
            section.self_ref,
            "direct",
            "12\n12",
            (
                dict(
                    kind="native_text",
                    item_ref=native_table.self_ref,
                    source_field="cell_text",
                    cell_index=0,
                    start=0,
                    end=2,
                ),
                dict(kind="synthetic_separator", start=2, end=3),
                dict(
                    kind="native_text",
                    item_ref=native_table.self_ref,
                    source_field="cell_text",
                    cell_index=1,
                    start=3,
                    end=5,
                ),
            ),
            (section.self_ref, native_table.self_ref),
            (),
            dict(payload["health"], formula_outcomes=[]),
            b'{"view":"cells"}',
        )
        draft = qualified_view_draft(draft, prepared.release_id)
        view = store_source_view(
            conn,
            run_id=run,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            draft=draft,
            position=0,
        )
        other = SourceViewDraft(
            "other-view",
            document,
            reference,
            sibling.self_ref,
            "direct",
            sibling_projection,
            tuple(sibling_pieces),
            (sibling.self_ref, *(item.self_ref for item in sibling_items)),
            (),
            dict(payload["health"], formula_outcomes=[]),
            b'{"view":"other"}',
        )
        other = qualified_view_draft(other, prepared.release_id)
        other_view = store_source_view(
            conn,
            run_id=run,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            draft=other,
            position=1,
        )
        complete_task(
            conn,
            task_id=source_task,
            attempt=claim.attempt,
            holder="private-source",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        record_method_ = record_method_spec or SimpleNamespace(
            name="private.records",
            version="1",
            family="record",
            tier="deterministic",
            confidence_source=None,
            unit_type=TaskUnitType.SOURCE_VIEW,
            Config=create_model("PrivateRecordConfig"),
        )
        record_config = record_method(
            conn, record_method_, "default", {}, "private-config", prepared=prepared
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=record_config,
            stage="record",
            unit_type="source_view",
            unit_id=view,
            unit_key="private-unit",
            input_hash="private-input-hash",
        )
        held = claim_tasks(conn, run_id=run, config_id=record_config, holder="records")[0]
        view_row = dict(
            conn.execute(
                select(table("kb.source_view")).where(table("kb.source_view").c.id == view)
            )
            .mappings()
            .one()
        )
        task_row = dict(
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
            .mappings()
            .one()
        )
    return SimpleNamespace(
        project_id=project_id,
        prepared=prepared,
        preparation_inputs=preparation.preparation_inputs,
        writer=writer,
        run=run,
        task=task,
        held=held,
        view=view,
        other_view=other_view,
        source_task=source_task,
        view_row=view_row,
        task_row=task_row,
        method=record_method_,
        table=native_table.self_ref,
        sibling=sibling_items[0].self_ref,
    )


def candidate(case, cell=0, *, projected=False, coarse=False):
    row = case.view_row
    pin = dict(
        source="private-unit",
        native_product_task_id=row["native_task_id"],
        product_key=row["native_product_key"],
        product_digest=row["native_content_digest"],
        projection_digest=row["projection_digest"],
        recipe_digest=row["recipe_digest"],
        source_view_id=row["id"],
    )
    pointer = f"{case.table}/data/table_cells/{cell}"
    literal: dict[str, Any] = dict(
        pin=pin,
        space="selected_projection" if projected else "native",
        pointer=pointer,
        precision="coarse" if coarse else "exact",
        source_piece="12",
    )
    if not coarse:
        literal.update(start=cell * 3 if projected else 0, end=cell * 3 + 2 if projected else 2)
    location = dict(pin=pin, space="native", pointer=pointer, precision="item")
    anchors, evidence, fields = [], [], []
    for role, anchor, usage in (("value", literal, "literal"), ("location", location, "native")):
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors.append(anchor)
        support = dict(role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],))
        support["set_id"] = evidence_set_identity(support)
        evidence.append(support)
        field = dict(
            role=role,
            kind="literal" if role == "value" else "native",
            state="present",
            meaning_changing=True,
            evidence_status="available",
            evidence_sets=(support["set_id"],),
            value=dict(kind="decimal", lexical="12")
            if role == "value"
            else dict(kind="native_location", pointer=pointer),
        )
        if role == "value":
            field["original"] = "12"
            field["reason"] = "source-read"
        fields.append(field)
    record = dict(
        contract="FixtureRecordFields",
        family="table",
        occurrence_recipe="source-anchor-membership-1",
        pin=pin,
        occurrence_anchors=(location["anchor_id"],),
        standing="candidate",
        policy_version="private-1",
        anchors=tuple(anchors),
        evidence_sets=tuple(evidence),
        fields=tuple(fields),
    )
    return identities(case, record)


def identities(case, record):
    record["record_id"] = record_identity(case.prepared.release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


def unit(case):
    payload = RawReport(source_text="12\n12")
    return UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
        outcome=ObservationOutcome.PRODUCED,
        observations=(
            ObservationDraft(
                kind=ObservationKind.RECORD,
                payload=payload,
                payload_class=RawReport,
                payload_version="1",
                source_view_id=case.view,
            ),
        ),
    )


def complete(case, conn, records):
    return complete_unit_result(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        method=case.method,
        configuration_hash="private-config",
        source="private-unit",
        result=unit(case),
        records=records,
    )


def bypass(case, conn, records):
    bound = bind_result(
        case.prepared,
        source="private-unit",
        method=case.method.name,
        operation_version="1",
        configuration_hash="private-config",
        input_hash="private-input-hash",
        invocation_key=case.task_row["invocation_key"],
        result=unit(case),
    )
    envelope = bound.model_dump(mode="json", exclude={"observations"})
    envelope["records"] = json.loads(json.dumps(records))
    item = bound.model_dump(mode="python")["observations"][0]
    return complete_task(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        observations=(
            dict(
                payload_definition="SourceObservation",
                item_key=item["item_key"],
                observation_key=item["observation_key"],
                payload=item,
                kind=item["family"],
                source_view_id=case.view,
                outcome=item["outcome"],
            ),
        ),
        envelope=envelope,
    )


@pytest.fixture
def private_source_options():
    return {}


@pytest.fixture
def private_preparation():
    return prepare_record_source()


@pytest.fixture
def private_source(
    semantic_db_engine, semantic_writer_engine, tmp_path, request, private_source_options
):
    options = private_source_options | getattr(request, "param", {})
    method = options.get("record_method")
    preparation = prepare_record_source(
        bundle_transform=options.get("bundle_transform"),
        additional_methods=options.get("additional_methods", ()),
    )
    return build_record_source(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        preparation,
        include_blank_cell=options.get("include_blank_cell", False),
        record_method_spec=method,
        sibling_captions=options.get("sibling_captions", ()),
        sibling_references=options.get("sibling_references", ()),
    )


def contribution_drafts(case):
    record = candidate(case)
    anchor = record["anchors"][0]
    # This fixture's independently authored native cell spells exactly 12 at [0,2).
    assert anchor["pointer"] == case.table + "/data/table_cells/0"
    assert anchor["start"] == 0 and anchor["end"] == 2 and anchor["source_piece"] == "12"
    occurrence = dict(
        contract="RetainedContributionSemantics",
        kind="occurrence",
        semantic_type="table.cell_value",
        operation_key="locate-cell-1",
        item_key="cell/0",
        pin=record["pin"],
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
        disposition="unassessed",
        standing="retained_private",
        score_state="missing",
    )
    occurrence["contribution_id"] = contribution_identity(occurrence)
    proposal = dict(
        occurrence,
        kind="proposal",
        semantic_type="unresolved.unit",
        item_key="unit/0",
        disposition="unresolved",
    )
    proposal["contribution_id"] = contribution_identity(proposal)
    operations = (
        dict(
            operation_key="locate-cell-1",
            question="inspect_cell",
            operation_version="1",
            outcome="succeeded",
            inspected_count=1,
            emitted_count=2,
        ),
        dict(
            operation_key="absent-1",
            question="inspect_caption",
            operation_version="1",
            outcome="empty",
            inspected_count=1,
            emitted_count=0,
        ),
    )
    coordinates = (dict(pin=record["pin"], space="native", pointer=anchor["pointer"], text="12"),)
    result = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
        outcome=ObservationOutcome.PRODUCED,
        contribution_operations=operations,
        contributions=(occurrence, proposal),
        contribution_coordinate_texts=coordinates,
    )
    return result


def complete_contributions(case, conn, result):
    return complete_unit_result(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        method=case.method,
        configuration_hash="private-config",
        source="private-unit",
        result=result,
    )


def contribution_envelope(case, result):
    return bind_result(
        case.prepared,
        source="private-unit",
        method=case.method.name,
        operation_version="1",
        configuration_hash="private-config",
        input_hash="private-input-hash",
        invocation_key=case.task_row["invocation_key"],
        result=result,
    ).model_dump(mode="json", exclude={"observations"})


def bypass_contributions(case, conn, raw):
    # Encode immutable SourceValue tuple collections as their actual JSON wire
    # arrays without applying semantic validation to the deliberate bad payload.
    from corpus_structure.semantic.identity import canonical_bytes

    return complete_task(
        conn,
        task_id=case.task,
        attempt=case.held.attempt,
        holder="records",
        prepared=case.prepared,
        observations=(),
        outcome="done",
        envelope=json.loads(canonical_bytes(raw)),
    )


def curated_case(original, *, extra_targets=(), config_hash="private-config", target_version=None):
    targets = (
        RegistryTarget(
            target_id="t1",
            label="12",
            description="The numeral twelve printed in the supplied cell.",
            type_name="numeral",
            parent="numbers",
        ),
        RegistryTarget(
            target_id="t2",
            label="7",
            description="The numeral seven as a different source-reported number.",
            type_name="numeral",
            parent="numbers",
        ),
    )
    if target_version is not None:
        targets = tuple(t.model_copy(update={"effective_version": target_version}) for t in targets)
    targets = (*targets, *extra_targets)
    method = SimpleNamespace(**vars(original.method))
    method.name = "private.contextual"
    method.Config = create_model(
        "PrivateContextualConfig", registry_targets=(tuple[RegistryTarget, ...], ...)
    )
    params = dict(registry_targets=[t.model_dump(mode="json") for t in targets])
    with original.writer.begin() as conn:
        config = record_method(
            conn, method, "default", params, config_hash, prepared=original.prepared
        )
        task = create_task(
            conn,
            run_id=original.run,
            config_id=config,
            stage="record",
            unit_type="source_view",
            unit_id=original.view,
            unit_key="private-unit",
            input_hash="private-input-hash",
        )
        held = claim_tasks(conn, run_id=original.run, config_id=config, holder="records")[0]
        task_row = dict(
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
            .mappings()
            .one()
        )
    return SimpleNamespace(
        **(
            vars(original)
            | dict(
                method=method,
                task=task,
                held=held,
                task_row=task_row,
                registry_targets=targets,
                configuration_hash=config_hash,
            )
        )
    )


def contextual_result(case, *, cached=(), effective_version=None, competing=False):
    result = contribution_drafts(case)
    assert result.contributions is not None
    assert result.contribution_operations is not None
    occurrence_id = result.contributions[0]["occurrence_id"]
    evidence = result.contributions[0]["contribution_id"]
    profile = EncoderProfile(
        "constructed/native-contract", "a" * 40, 2, "query: ", "passage: ", "mean"
    )

    registry_id, targets = registry_input(case.registry_targets)

    def vector(object_id, values, representation_digest="", source_binding="private-unit"):
        digest = "b" * 64
        vector_id = identity(
            "context-vector",
            [object_id, source_binding, profile.profile_id, digest, representation_digest],
        )
        return EncodedVector(
            vector_id,
            object_id,
            source_binding,
            profile.profile_id,
            digest,
            values,
            representation_digest,
        )

    query = vector(occurrence_id, (1.0, 0.0))
    inv = freeze_inventory(
        targets, source_selection=registry_id, scope="chapter5", effective_version=effective_version
    )
    target_vectors = {item.vector.object_id: item.vector for item in cached}
    for index, target in enumerate(targets):
        if target.target_id not in target_vectors:
            values = (
                (1.0, 0.0) if index == 0 else ((0.0, 1.0) if index == 1 else (sqrt(0.5), sqrt(0.5)))
            )
            target_vectors[target.target_id] = vector(
                target.target_id, values, target.representation_digest, target.source_binding
            )
    ranked = sorted(target_vectors.values(), key=lambda v: (-v.values[0], v.object_id))
    lists = fuse_candidates(
        occurrence_id=occurrence_id,
        query=query,
        inventory=inv,
        channels={"dense": tuple(ChannelHit(v.object_id, v.values[0]) for v in ranked)},
    )
    witness = RelationshipWitness(
        "w",
        occurrence_id,
        "t1",
        "denotes",
        "private-unit",
        "chapter5",
        effective_version,
        (evidence,),
        "explicit_source_cue",
    )
    decision = select_relationships(
        candidates=lists,
        inventory=inv,
        source_binding="private-unit",
        scope="chapter5",
        effective_version=effective_version,
        witnesses=(
            witness,
            replace(witness, witness_id="competing-sense", target_id=inv.targets[1].target_id),
        )
        if competing
        else (witness,),
        constraints=(RelationshipConstraint("sense", ("denotes",), "usage", "concept", "one"),),
    )
    report = enrichment_report(
        curated_registry_id=registry_id,
        profiles=(profile,),
        vectors=(query, *target_vectors.values()),
        vector_reuse=tuple(item.reuse for item in cached),
        inventories=(inv,),
        candidate_lists=(lists,),
        relationship_decisions=(decision,),
    )
    operations = tuple(
        dict(op, **({"contextual_enrichment": report} if i == 0 else {}))
        for i, op in enumerate(result.contribution_operations)
    )
    contributions = result.contributions
    return (
        replace(result, contribution_operations=operations, contributions=contributions),
        query,
        inv,
    )


def refresh_record_identities(case, record):
    """Rebuild only derived identifiers after a deliberately changed source input."""
    anchor_ids = {}
    for anchor in record["anchors"]:
        old = anchor["anchor_id"]
        anchor["anchor_id"] = anchor_identity(anchor)
        anchor_ids[old] = anchor["anchor_id"]
    record["occurrence_anchors"] = tuple(anchor_ids[a] for a in record["occurrence_anchors"])
    set_ids = {}
    for support in record["evidence_sets"]:
        old = support["set_id"]
        support["anchors"] = tuple(anchor_ids[a] for a in support["anchors"])
        support["set_id"] = evidence_set_identity(support)
        set_ids[old] = support["set_id"]
    for field in record["fields"]:
        field["evidence_sets"] = tuple(set_ids[e] for e in field["evidence_sets"])
    return identities(case, record)


def complete_absent_and_empty_reports(case):
    with case.writer.begin() as conn:
        complete_unit_result(
            conn,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            result=unit(case),
        )
        task = create_task(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            stage="record",
            unit_type="source_view",
            unit_id=case.view,
            unit_key="private-unit-empty",
            input_hash="empty",
        )
        held = claim_tasks(
            conn, run_id=case.run, config_id=case.task_row["method_config_id"], holder="empty"
        )[0]
        complete_unit_result(
            conn,
            task_id=task,
            attempt=held.attempt,
            holder="empty",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit-empty",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit-empty"),
                outcome=ObservationOutcome.EMPTY,
            ),
            records=(),
        )
        return task
