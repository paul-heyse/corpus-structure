"""Actual current native source/read/CPU grade and fit journey, controlled conversion.

No old run, task-alias, evaluator ledger or fabricated publication/CPU receipt is
used. Conversion and candidate extraction are controlled; this is native custody
and permission evidence, never provider accuracy or population-quality evidence.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
import yaml
from pdf_controlled_support import ControlledPdfContent, controlled_pdf_converter
from scenario_recipes import register_scenario_builder
from semantic.current_pdf_source_support import current_pdf_recipe
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    Kernel,
    KernelRecipe,
    KernelSeedStage,
    build_kernel,
    execute_captured_kernel_demand,
    split_captured_operations,
)

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "current-record-policy"


def policy_recipe(directory):
    from evaluate.declared_record_candidate_fixture import operation_sources

    from corpus_structure.evaluate.declared_record_policy import (
        protected_record_policy_kind_declarations,
        record_policy_inputs,
        record_policy_operation_sources,
    )
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
    )
    from corpus_structure.semantic.effect_policy import ApprovedEffect
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    from corpus_structure.semantic.reading_resolution_products import (
        reading_resolution_declarations,
        reading_resolution_operation_sources,
    )
    from corpus_structure.semantic.record_policy_authority import (
        AUTHORIZATION_EFFECT,
        AUTHORIZATION_OPERATION,
        record_policy_authorization_sources,
        record_policy_kind_declarations,
    )
    from corpus_structure.semantic.terminology import acquire_terminology

    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    base_dependencies, declared, source = split_captured_operations(captured)
    from statistics_pack_support import statistics_bundle

    statistics_inputs = statistics_bundle()
    statistics = yaml.safe_load(
        next(
            source.content
            for source in statistics_inputs.sources
            if source.name == statistics_inputs.root
        )
    )
    statistics["classes"].pop("TableRecordFields")
    statistics["imports"] = ["core", "policy_fixture_terminology"]
    (terminology_module,), terminology_artifacts, ontology_names = acquire_terminology(
        ROOT / "domains/statistics"
    )
    terminology = yaml.safe_load(terminology_module.content)
    terminology["imports"] = ["core"]
    terminology["name"] = "policy_fixture_terminology"
    terminology_source = SourceArtifact(
        "policy_fixture_terminology", yaml.safe_dump(terminology).encode()
    )
    statistics["name"] = "policy_fixture_families"
    families = SourceArtifact("policy_fixture_families", yaml.safe_dump(statistics).encode())
    table = SourceArtifact(
        "policy_fixture_table",
        yaml.safe_dump(
            {
                "id": "https://example.test/current-record-policy",
                "name": "policy_fixture_table",
                "imports": ["core"],
                "prefixes": {"fixture": "https://example.test/current-record-policy/"},
                "default_prefix": "fixture",
                "classes": {
                    "FixtureCandidateQuestion": {
                        "attributes": {
                            "source_pin_json": {"range": "string", "required": True},
                            "empty": {"range": "boolean", "required": True},
                            "family": {"range": "string", "pattern": "^(table|measurement)$"},
                            "variant": {
                                "range": "string",
                                "pattern": "^(standard|unresolved-value-alternative)$",
                            },
                            "diagnostic_bytes": {
                                "range": "integer",
                                "minimum_value": 0,
                                "maximum_value": 8 * 1024**2,
                            },
                        }
                    },
                    "FixtureLiteralField": {
                        "is_a": "RequiredLiteralRecordField",
                        "rules": [
                            {
                                "preconditions": {
                                    "slot_conditions": {"state": {"equals_string": "present"}}
                                },
                                "postconditions": {
                                    "slot_conditions": {
                                        "reason": {"required": True, "equals_string": "source-read"}
                                    }
                                },
                            }
                        ],
                    },
                    "FixtureRecordFields": {
                        "is_a": "SemanticRecordFields",
                        "attributes": {
                            "family": {"equals_string": "table"},
                            "occurrence_recipe": {"equals_string": "source-anchor-membership-1"},
                            "value": {
                                "range": "FixtureLiteralField",
                                "required": True,
                                "inlined": True,
                            },
                            "location": {
                                "range": "RequiredNativeRecordField",
                                "required": True,
                                "inlined": True,
                            },
                        },
                    },
                },
            }
        ).encode(),
    )
    root = SourceArtifact(
        "policy_fixture_root",
        yaml.safe_dump(
            {
                "id": "urn:corpus:current-policy-fixture-root",
                "name": "policy_fixture_root",
                "imports": [captured.bundle.root, families.name, table.name],
            }
        ).encode(),
    )
    bundle = record_policy_inputs(
        SourceBundle(
            root.name, (*captured.bundle.sources, terminology_source, families, table, root)
        )
    )
    sources = combine_primary_sources(
        source,
        operation_sources(),
        reading_resolution_operation_sources(),
        record_policy_operation_sources(),
        record_policy_authorization_sources(),
    )
    # Replace the explicitly parsed current DDO package; preserve its entire native,
    # physical, helper and generator cut rather than acquiring any legacy catalog.
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            base_dependencies.artifacts + terminology_artifacts,
            base_dependencies.vocabularies,
            (*base_dependencies.ontology_sources, *ontology_names),
        ),
        (
            *declared,
            reading_resolution_declarations(),
            record_policy_kind_declarations(),
            protected_record_policy_kind_declarations(),
        ),
        sources,
    )
    return KernelRecipe(
        "current-record-policy",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        effect_approvals=(
            *original.effect_approvals,
            ApprovedEffect(AUTHORIZATION_OPERATION, AUTHORIZATION_EFFECT.name),
        ),
        captured_inputs=CapturedKernelInputs(bundle, dependencies, captured.profile),
    )


def table_source_content():
    from docling_core.types.doc import DoclingDocument, GroupLabel, TableCell, TableData
    from pdf_controlled_support import ControlledPdfContent

    document = DoclingDocument(name="Independent native two-cell source")
    section = document.add_group(label=GroupLabel.SECTION, name="Measurements")
    document.add_table(
        parent=section,
        data=TableData(
            num_rows=1,
            num_cols=2,
            table_cells=[
                TableCell(
                    text="12",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=column,
                    end_col_offset_idx=column + 1,
                )
                for column in range(2)
            ],
        ),
    )
    return ControlledPdfContent.from_document(document)


@dataclass(frozen=True)
class SourceChoice:
    pin: DeclaredStructuralSource
    body: dict[str, Any]
    context: SubjectContext
    selected_entry: Any = None

    def entry(self):
        if self.selected_entry is None:
            raise ValueError("source choice has no retained selected producing occurrence")
        return self.selected_entry


def selected_product_entries(index, read, product_id, member_id=None):
    from corpus_structure.semantic.data_operation_source_sets import selected_source_entries
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference

    return tuple(
        selected
        for use in index.frontier_rows("uses")
        if use["fate"] == "fulfilled"
        for selected in selected_source_entries(
            index,
            read,
            product_id=product_id,
            member_id=member_id,
            anchor_use_id=use["use_id"],
            support=ComputationalSupportReference(
                derivation_id=use["derivation_id"], admission_use_id=use["use_id"]
            ),
        )
    )


@dataclass
class CurrentRecordPolicyJourney:
    kernel: Kernel
    source_demand: str
    sources: tuple[SourceChoice, ...]
    source_cut: CutSelection

    def selected_products(
        self, engine, demand, *, kind, scope=None, page_rows=100, max_bytes=8 * 1024**2
    ):
        from corpus_structure.evaluate.declared_record_policy import _selected_body
        from corpus_structure.semantic.demand_results import acquired_selected_relations
        from corpus_structure.semantic.selected_support import SelectedReadReference

        names = (kind,) if isinstance(kind, str) else kind
        contracts = {
            identity.key
            for identity in self.kernel.model.identities
            if identity.domain == "kind" and identity.owner in names
        }
        with (
            engine.begin() as connection,
            acquired_selected_relations(
                connection,
                demand,
                project_id=PROJECT,
                scope={} if scope is None else scope,
                page_rows=page_rows,
                max_bytes=max_bytes,
                capture_frontier=True,
            ) as (cut, index),
        ):
            read = SelectedReadReference.from_cut(cut)
            products = []
            for row in index.rows("kb.data_product"):
                if row["kind_contract"] in contracts:
                    _, body = _selected_body(index, row["id"])
                    products.append(
                        (
                            dict(
                                row,
                                _selected_entries=selected_product_entries(index, read, row["id"]),
                            ),
                            body,
                        )
                    )
            uses = tuple(index.frontier_rows("uses"))
            episodes = tuple(index.rows("ops.data_derivation"))
            outputs = tuple(index.rows("ops.data_derivation_output"))
            return cut, tuple(products), uses, episodes, outputs


def _capture_record_policy(kernel, tmp_path, source_count):
    import pypdfium2 as pdfium

    from corpus_structure.core.evidence import document_key
    from corpus_structure.evaluate.declared_record_policy import _selected_body
    from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.data_operation_model import json_context_meaning
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.demand_results import acquired_selected_relations
    from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
    from corpus_structure.semantic.original_documents import (
        acquire_original_document_selection,
        register_original_document,
    )
    from corpus_structure.semantic.selected_support import SelectedReadReference

    with kernel.purpose("write").begin() as connection:
        DataOperationStorage(connection).initialize_source_project(
            {
                "project_id": ProjectId(PROJECT),
                "release_id": ReleaseId(kernel.prepared.release_id),
            }
        )
        originals = []
        for ordinal in range(source_count):
            document = pdfium.PdfDocument.new()
            page = document.new_page(200 + ordinal, 300)
            page.close()
            output = BytesIO()
            document.save(output)
            document.close()
            content = output.getvalue()
            path = tmp_path / f"independent-policy-{ordinal}.pdf"
            path.write_bytes(content)
            register_original_document(
                connection,
                prepared=kernel.prepared,
                project_id=PROJECT,
                source_uri=path.name,
                original_path=str(path),
                original=content,
                mime="application/pdf",
            )
            key = document_key(PROJECT, path.name, sha256(content).hexdigest())
            originals.append(
                acquire_original_document_selection(
                    connection,
                    project_id=PROJECT,
                    document_key=key,
                    name=f"policy-original-{ordinal}",
                )
            )
            path.unlink()
        intent = freeze_demand(
            kernel.model,
            roots=tuple(item.root for item in originals),
            targets=("source.pdf_views/discovery",),
            original_sources=tuple(item.selection() for item in originals),
            inference="current-record-policy-source",
            execution_profile=kernel.recipe.execution_profile,
        )
        demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(
            intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

    # The controlled content yields identical shared stream parts across the
    # originals. This scenario exercises derived record publication, so let
    # each capture publish those parts before another capture reuses them.
    result = execute_captured_kernel_demand(
        kernel,
        demand,
        policy=CharacterizationExecutionPolicy(
            workers=1, max_submissions=1, max_regions=1, max_claims=1
        ),
    )
    assert result.receipt_count == 2 * source_count
    contracts = {
        identity.key
        for identity in kernel.model.identities
        if identity.domain == "kind"
        and identity.owner
        == "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource"
    }
    selected = []
    with (
        kernel.purpose("evaluate").begin() as connection,
        acquired_selected_relations(
            connection, demand, project_id=PROJECT, scope={}, capture_frontier=True
        ) as (
            source_cut,
            index,
        ),
    ):
        source_read = SelectedReadReference.from_cut(source_cut)
        for row in index.rows("kb.data_product_member"):
            if row["kind_contract"] not in contracts:
                continue
            _, body = _selected_body(index, row["product_id"], row["member_id"])
            if not any(item["label"] == "table" for item in body["items"]):
                continue
            coordinate = body["source"]
            pin = DeclaredStructuralSource(
                source=canonical_bytes([row["product_id"], row["member_id"]]).decode(),
                source_product=row["product_id"],
                source_member=row["member_id"],
                subject=row["subject"],
                subject_definition=row["subject_definition"],
                document=coordinate["document"],
                original_source=row["original_source"],
                projection_digest=coordinate["projection"],
                section_pointer=coordinate["section_pointer"],
                membership=coordinate["membership"],
                project_id=PROJECT,
                analyzed_scope_meaning=json_context_meaning(
                    json_bytes(row["analyzed_scope"])
                ).decode(),
                kind_contract=row["kind_contract"],
            )
            (selected_entry,) = selected_product_entries(
                index, source_read, row["product_id"], row["member_id"]
            )
            selected.append(
                SourceChoice(
                    pin,
                    body,
                    SubjectContext(
                        PROJECT,
                        row["subject"],
                        row["original_source"],
                        json_bytes(row["analyzed_scope"]),
                        subject_definition=row["subject_definition"],
                    ),
                    selected_entry,
                )
            )
    # The source-only question selects one actual table-bearing native region
    # per independent original before any candidate, score or label exists.
    by_original = {}
    for item in selected:
        by_original.setdefault(item.pin.original_source, []).append(item)
    selected = [
        min(
            items,
            key=lambda item: (
                len(item.body["items"]),
                item.pin.section_pointer,
                item.pin.membership,
            ),
        )
        for items in by_original.values()
    ]
    assert len(selected) == source_count
    assert len({pin.original_source for pin in (item.pin for item in selected)}) == source_count
    return CurrentRecordPolicyJourney(
        kernel,
        demand,
        tuple(sorted(selected, key=lambda item: item.pin.original_source)),
        source_cut,
    )


@contextmanager
def current_record_policy_journey(
    scenario_seeds, tmp_path, monkeypatch, *, recipe, source_count=4, content=None
):
    with (
        controlled_pdf_converter(table_source_content() if content is None else content),
        scenario_seeds.build_for_consumer(recipe, tmp_path) as clone,
    ):
        kernel = Kernel(clone.admin, clone.stage.preparation, clone.stage.identities, recipe, clone)
        yield _capture_record_policy(kernel, tmp_path, source_count)


@dataclass(frozen=True)
class RecordPublicationCapture:
    content: ControlledPdfContent
    source_count: int = 4


@dataclass(frozen=True)
class RecordPublicationStage:
    kernel: KernelSeedStage
    source_demand: str
    sources: tuple[SourceChoice, ...]
    source_cut: CutSelection

    @property
    def seed_files(self):
        return self.kernel.seed_files

    @property
    def seed_origin(self):
        return {"capture_producer": "controlled-record-publication"}

    def validate_clone(self, admin):
        self.kernel.validate_clone(admin)

    def acquired(self, clone):
        from copy import deepcopy

        stage = self.kernel
        kernel = Kernel(clone.admin, stage.preparation, stage.identities, stage.recipe, clone)
        return CurrentRecordPolicyJourney(
            kernel, self.source_demand, deepcopy(self.sources), self.source_cut
        )


def _build_record_publication(scenario, admin, writer, directory, *, purpose_engine):
    from types import SimpleNamespace

    from semantic.record_publication_native_support import publication_recipe

    recipe = publication_recipe(directory)
    stage = build_kernel(recipe, admin, writer, directory, purpose_engine=purpose_engine)
    kernel = Kernel(
        admin, stage.preparation, stage.identities, recipe, SimpleNamespace(purpose=purpose_engine)
    )
    with controlled_pdf_converter(scenario.content):
        journey = _capture_record_policy(kernel, directory, scenario.source_count)
    return RecordPublicationStage(stage, journey.source_demand, journey.sources, journey.source_cut)


register_scenario_builder(RecordPublicationCapture, _build_record_publication)


@pytest.fixture
def current_record_policy(scenario_seeds, tmp_path, monkeypatch, request):
    with current_record_policy_journey(
        scenario_seeds,
        tmp_path,
        monkeypatch,
        recipe=policy_recipe(tmp_path),
        source_count=getattr(request, "param", 4),
    ) as journey:
        yield journey


def reference_records(journey, selected):
    """Independently author the two complete source cells; never read predictions."""
    from evaluate.declared_record_candidate_fixture import native_cell_coordinate

    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
        record_family_contract,
        record_identity,
    )

    pin = selected.pin.model_dump(mode="json", exclude_none=True)
    (table,) = [item for item in selected.body["items"] if item.get("label") == "table"]
    rows, coordinates = [], []
    for column, cell in enumerate(table["data"]["table_cells"]):
        pointer = f"{table['self_ref']}/data/table_cells/{column}"
        text = cell["text"]
        literal = dict(
            pin=pin,
            space="native",
            pointer=pointer,
            precision="exact",
            start=0,
            end=len(text),
            source_piece=text,
        )
        location = dict(pin=pin, space="native", pointer=pointer, precision="item")
        for anchor in (literal, location):
            anchor["anchor_id"] = anchor_identity(anchor)
        value_set = dict(
            role="value", ordering="ordered", usage="literal", anchors=(literal["anchor_id"],)
        )
        location_set = dict(
            role="location", ordering="ordered", usage="native", anchors=(location["anchor_id"],)
        )
        for evidence in (value_set, location_set):
            evidence["set_id"] = evidence_set_identity(evidence)
        row = dict(
            contract="FixtureRecordFields",
            family="table",
            occurrence_recipe="source-anchor-membership-1",
            pin=pin,
            occurrence_anchors=(location["anchor_id"],),
            standing="accepted",
            policy_version="independent-source-reference-1",
            anchors=(literal, location),
            evidence_sets=(value_set, location_set),
            fields=(
                dict(
                    role="value",
                    kind="literal",
                    state="present",
                    meaning_changing=True,
                    evidence_status="available",
                    evidence_sets=(value_set["set_id"],),
                    value=dict(kind="decimal", lexical=text),
                    original=text,
                    reason="source-read",
                ),
                dict(
                    role="location",
                    kind="native",
                    state="present",
                    meaning_changing=True,
                    evidence_status="available",
                    evidence_sets=(location_set["set_id"],),
                    value=dict(kind="native_location", pointer=pointer),
                ),
            ),
            computation_dependencies=(),
        )
        row["record_id"] = record_identity(
            record_family_contract(journey.kernel.model, row["contract"]), row
        )
        row["interpretation_id"] = interpretation_identity(row)
        journey.kernel.prepared.validate_json("SourceRecord", canonical_bytes(row))
        rows.append(row)
        coordinates.append(
            native_cell_coordinate(
                selected.body, pin, item_pointer=table["self_ref"], cell_index=column
            )
        )
    assert len(rows) == 2
    return tuple(rows), tuple(coordinates)


def project_context(journey, operation):
    return SubjectContext(
        PROJECT,
        "knowledge:" + PROJECT,
        None,
        b"{}",
        subject_definition=journey.kernel.model.operation(operation).subject,
    )


def authored(
    journey,
    name,
    value,
    *,
    kind,
    context,
    author="controlled source-only operator",
    selection_id=None,
):
    from corpus_structure.semantic.data_operation_support import authored_fact_selection

    return authored_fact_selection(
        name,
        value,
        kind_contract=journey.kernel.identities[kind, "kind"],
        context=context,
        author=author,
        selection_id=selection_id or "independent-pass:" + name,
    )


def request(journey, targets, contexts, *, originals=(), source_sets=(), inference):
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import (
        DemandOriginalSelection,
        DemandRoot,
        NativeDemandRequest,
    )
    from corpus_structure.semantic.data_operation_source_sets import source_sets_record

    return NativeDemandRequest(
        project_id=PROJECT,
        release_id=journey.kernel.prepared.release_id,
        runtime_id=journey.kernel.runtime,
        roots=tuple(
            DemandRoot(
                subject=context.subject,
                original_source=context.original_source,
                analyzed_scope=json_loads(context.analyzed_scope),
            )
            for context in contexts
        ),
        targets=targets,
        original_sources={
            item.name: DemandOriginalSelection.model_validate(item.record()) for item in originals
        },
        source_sets=source_sets_record(source_sets),
        inference=inference,
        execution_profile=journey.kernel.recipe.execution_profile,
    )


def retain_references(journey, selected_sources, *, partition, held_out_from=()):
    from corpus_structure.evaluate.declared_record_policy import (
        PROTECTED_NAMESPACE,
        DdoRecordReference,
        DdoRecordReferencePopulationA,
        DdoRecordReferencePopulationB,
        DdoRecordReferencePopulationC,
        DdoRecordReferenceQuestion,
        author_record_policy_inputs,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.reading_resolution_products import reading_recipe_identity
    from corpus_structure.semantic.record_contracts import record_family_contract

    questions = []
    for selected in selected_sources:
        rows, coordinates = reference_records(journey, selected)
        pin = selected.pin.model_dump(mode="json", exclude_none=True)
        frame = dict(
            unit="original-native-two-cell-section",
            release_id=journey.kernel.prepared.release_id,
            guideline_version="complete-native-cell-source-only-1",
            reference_policy_version="independent-source-reference-1",
            prediction_policy_version="m1-grouped-reading-logistic-1",
            pin=pin,
            anchor_ids=sorted(anchor["anchor_id"] for row in rows for anchor in row["anchors"]),
            related_pins=[],
            anchor_scopes=[],
        )
        question = DdoRecordReferenceQuestion(
            project_id=PROJECT,
            partition=partition,
            family="table",
            family_contract=record_family_contract(journey.kernel.model, "FixtureRecordFields"),
            reading_recipe=reading_recipe_identity(journey.kernel.model),
            subset="independent-native-cells",
            source=selected.pin,
            source_release_id=journey.kernel.prepared.release_id,
            source_cut_id=journey.source_cut.identity,
            source_cut_canonical_json=journey.source_cut.content.decode(),
            frame_canonical_json=canonical_bytes(frame).decode(),
            coordinate_texts_canonical_json=canonical_bytes(coordinates).decode(),
            rubric="Entire source cell value and actual native location must both be correct.",
            origin_group="original:" + selected.pin.original_source,
            held_out_from=held_out_from,
        )
        questions.append((question, rows))
    # Three real source-only pass values. B independently re-reads the source;
    # it does not consume A's answer. C records the exact retained A/B judgments.
    a = DdoRecordReferencePopulationA(
        pass_kind="A",
        references=tuple(
            DdoRecordReference(
                question=question,
                pass_kind="A",
                author="controlled operator",
                records_canonical_json=canonical_bytes(rows).decode(),
            )
            for question, rows in questions
        ),
    )
    b = DdoRecordReferencePopulationB(
        pass_kind="B",
        references=tuple(
            DdoRecordReference(
                question=question,
                pass_kind="B",
                author="controlled operator",
                records_canonical_json=canonical_bytes(
                    reference_records(journey, selected)[0]
                ).decode(),
            )
            for (question, _), selected in zip(questions, selected_sources, strict=True)
        ),
    )
    c = DdoRecordReferencePopulationC(
        pass_kind="C",
        references=tuple(
            DdoRecordReference(
                question=question,
                pass_kind="C",
                author="controlled operator",
                records_canonical_json=canonical_bytes(
                    reference_records(journey, selected)[0]
                ).decode(),
                adjudicates=(left.digest, right.digest),
            )
            for (question, _), selected, left, right in zip(
                questions, selected_sources, a.references, b.references, strict=True
            )
        ),
    )
    context = project_context(journey, "record_policy.grade")
    originals = tuple(
        authored(
            journey,
            f"{partition}-pass-{value.pass_kind}",
            value.model_dump(mode="json"),
            kind=PROTECTED_NAMESPACE + type(value).__name__,
            context=context,
        )
        for value in (a, b, c)
    )
    # Freeze actual reference admissions before any prediction for this partition.
    # This incomplete demand has no specification and cannot execute a grade.
    pending = request(
        journey,
        ("record_policy.grade",),
        (context,),
        originals=originals,
        source_sets=(
            FrozenSourceSet.from_selected(
                "record-policy-sources", tuple(source.entry() for source in selected_sources)
            ),
            FrozenSourceSet.from_selected("record-policy-predictions", ()),
        ),
        inference="source-only-predeclaration:" + partition,
    )
    retained = author_record_policy_inputs(
        journey.kernel.purpose("evaluate"), journey.kernel.prepared, request=pending
    )
    assert len(retained["authored_admissions"]) == 3
    assert len({row["admission_id"] for row in retained["authored_admissions"]}) == 3
    return (a, b, c), originals


@dataclass(frozen=True)
class ReadingPopulation:
    specification: Any
    resolved: tuple[tuple[dict[str, Any], dict[str, Any]], ...]
    raw: tuple[tuple[dict[str, Any], dict[str, Any]], ...]
    cut: CutSelection
    demand_id: str


def run_readings(
    journey,
    selected_sources,
    *,
    policy,
    inference,
    empty_sources=(),
    family="table",
    variant="standard",
    diagnostic_bytes=0,
    page_rows=100,
    max_bytes=8 * 1024**2,
):
    from corpus_structure.evaluate.declared_record_policy import (
        DdoRecordGradeSpecification,
        DdoRecordPredictionSelection,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.observations import source_value
    from corpus_structure.semantic.reading_resolution_products import RECIPE
    from corpus_structure.semantic.record_policy import RecordAlgorithm
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    ordinary = "https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoReadingFeaturePolicy"
    if policy is None:
        policy = dict(
            version="reading-feature-policy-2",
            recipe=RECIPE,
            subset="independent-native-cells",
            feature_instances=source_value([]),
        )
    originals = tuple(
        item
        for selected in selected_sources
        for item in (
            authored(
                journey,
                inference + ":question:" + selected.pin.source,
                {
                    "source_pin_json": canonical_bytes(
                        selected.pin.model_dump(mode="json", exclude_none=True)
                    ).decode(),
                    "empty": selected.pin.source in empty_sources,
                    **({"family": family} if family != "table" else {}),
                    **({"variant": variant} if variant != "standard" else {}),
                    **({"diagnostic_bytes": diagnostic_bytes} if diagnostic_bytes else {}),
                },
                kind="https://example.test/current-record-policy/FixtureCandidateQuestion",
                context=selected.context,
            ),
            authored(
                journey,
                inference + ":policy:" + selected.pin.source,
                policy,
                kind=ordinary,
                context=selected.context,
            ),
        )
    )
    pending = request(
        journey,
        ("fixture.record_candidates", "resolve.m1_readings/declared"),
        tuple(source.context for source in selected_sources),
        originals=originals,
        source_sets=(
            FrozenSourceSet.from_selected(
                "fixture-record-sources", tuple(source.entry() for source in selected_sources)
            ),
        ),
        inference=inference,
    )
    retained = author_interpretations(
        journey.kernel.purpose("write"), journey.kernel.prepared, request=pending
    )
    execution = execute_captured_kernel_demand(
        journey.kernel,
        retained["demand_id"],
    )
    assert execution.receipt_count == 2 * len(selected_sources)
    cut, selected_products, uses, episodes, outputs = journey.selected_products(
        journey.kernel.purpose("evaluate"),
        retained["demand_id"],
        kind=(
            "https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoResolvedReadingReport",
            "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport",
        ),
        page_rows=page_rows,
        max_bytes=max_bytes,
    )
    kinds = {
        item.owner: item.key for item in journey.kernel.model.identities if item.domain == "kind"
    }
    products = tuple(
        (row, body)
        for row, body in selected_products
        if row["kind_contract"]
        == kinds[
            "https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoResolvedReadingReport"
        ]
    )
    raw = tuple(
        (row, body)
        for row, body in selected_products
        if row["kind_contract"]
        == kinds[
            "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateInspectionReport"
        ]
    )
    assert len(raw) == len(selected_sources)
    assert len(products) == len(selected_sources)
    selections = []
    for selected in selected_sources:
        (product,) = [
            row
            for row, body in products
            if body["source_pin"] == selected.pin.model_dump(mode="json", exclude_none=True)
        ]
        (output,) = [
            row for row in outputs if row["product_id"] == product["id"] and row["role"] == "result"
        ]
        (episode,) = [row for row in episodes if row["id"] == output["derivation_id"]]
        (use,) = [
            row
            for row in uses
            if row["derivation_id"] == episode["id"] and row["fate"] == "fulfilled"
        ]
        selections.append(
            DdoRecordPredictionSelection(
                source=selected.pin,
                outcome="completed",
                request_id=episode["request_id"],
                obligation_id=use["obligation_id"],
                derivation_id=episode["id"],
                use_id=use["use_id"],
                project_id=PROJECT,
                demand_id=retained["demand_id"],
                read_id=cut.record["read_id"],
                product_id=product["id"],
                expected_cut=cut.identity,
                cut_canonical_json=cut.content.decode(),
            )
        )
    return ReadingPopulation(
        DdoRecordGradeSpecification(
            prediction_selections=tuple(selections), algorithm=RecordAlgorithm()
        ),
        products,
        raw,
        cut,
        retained["demand_id"],
    )


@dataclass(frozen=True)
class SelectedGrade:
    grade: Any
    selection: Any
    product: dict[str, Any]

    def entry(self):
        (entry,) = tuple(
            entry
            for entry in self.product["_selected_entries"]
            if entry.proof.support.admission_use_id == self.selection.use_id
            and entry.proof.support.derivation_id == self.selection.derivation_id
        )
        return entry


def run_grade(
    journey,
    selected_sources,
    populations,
    reference_facts,
    specification,
    predictions,
    *,
    inference,
):
    from corpus_structure.evaluate.declared_record_policy import (
        PROTECTED_NAMESPACE,
        DdoRecordGrade,
        DdoRecordGradeSelection,
        author_record_policy_inputs,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet

    entries = []
    for row, _ in predictions:
        (entry,) = row["_selected_entries"]
        entries.append(entry)
    context = project_context(journey, "record_policy.grade")
    spec = authored(
        journey,
        inference + ":specification",
        specification.model_dump(mode="json"),
        kind=PROTECTED_NAMESPACE + "DdoRecordGradeSpecification",
        context=context,
    )
    pending = request(
        journey,
        ("record_policy.grade",),
        (context,),
        originals=(*reference_facts, spec),
        source_sets=(
            FrozenSourceSet.from_selected(
                "record-policy-sources", tuple(source.entry() for source in selected_sources)
            ),
            FrozenSourceSet.from_selected("record-policy-predictions", tuple(entries)),
        ),
        inference=inference,
    )
    retained = author_record_policy_inputs(
        journey.kernel.purpose("evaluate"), journey.kernel.prepared, request=pending
    )
    result = execute_captured_kernel_demand(
        journey.kernel,
        retained["demand_id"],
        purpose="evaluate",
    )
    assert result.receipt_count == 1
    cut, products, uses, episodes, outputs = journey.selected_products(
        journey.kernel.purpose("evaluate"),
        retained["demand_id"],
        kind=PROTECTED_NAMESPACE + "DdoRecordGrade",
    )
    ((product, body),) = products
    (output,) = [
        row for row in outputs if row["product_id"] == product["id"] and row["role"] == "grade"
    ]
    (episode,) = [row for row in episodes if row["id"] == output["derivation_id"]]
    (use,) = [
        row for row in uses if row["derivation_id"] == episode["id"] and row["fate"] == "fulfilled"
    ]
    grade = DdoRecordGrade.from_selected_body(body)
    selected = DdoRecordGradeSelection(
        project_id=PROJECT,
        demand_id=retained["demand_id"],
        read_id=cut.record["read_id"],
        use_id=use["use_id"],
        derivation_id=episode["id"],
        product_id=product["id"],
        expected_cut=cut.identity,
        cut_canonical_json=cut.content.decode(),
        frame_digest=grade.frame_digest,
    )
    assert tuple(row.source for row in grade.frame.coverage) == tuple(
        source.pin for source in selected_sources
    )
    assert tuple(row.reference.product_id for row in grade.frame.reference_passes[:3]) != ()
    return SelectedGrade(grade, selected, product)


@dataclass(frozen=True)
class FittedJourney:
    journey: CurrentRecordPolicyJourney
    feature: SelectedGrade
    calibration: SelectedGrade
    fitted: dict[str, Any]
    authorization: dict[str, Any]
    authorization_product_id: str
    demand_id: str
    feature_readings: ReadingPopulation
    calibration_readings: ReadingPopulation


def complete_policy_fit(journey):
    from corpus_structure.evaluate.declared_record_policy import (
        PROTECTED_NAMESPACE,
        DdoRecordFeatureFitRequest,
        DdoRecordFitSpecification,
        author_record_policy_inputs,
        prepare_record_feature_policy,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.reading_resolution_products import EVENT_PROCEDURE
    from corpus_structure.semantic.record_policy import RecordAlgorithm
    from corpus_structure.semantic.record_policy_authority import (
        NAMESPACE,
        DdoRecordPolicyApplicability,
    )

    feature_sources, calibration_sources = journey.sources[:2], journey.sources[2:]
    passes, facts = retain_references(journey, feature_sources, partition="feature_fit")
    feature_readings = run_readings(
        journey, feature_sources, policy=None, inference="genuine-feature-readings"
    )
    feature = run_grade(
        journey,
        feature_sources,
        passes,
        facts,
        feature_readings.specification,
        feature_readings.resolved,
        inference="genuine-feature-grade",
    )
    assert len(feature.grade.frame.events) == 8
    assert sum(row.correct for row in feature.grade.frame.events) == 4
    assert {row.source.original_source for row in feature.grade.frame.events} == {
        source.pin.original_source for source in feature_sources
    }
    assumptions = "controlled source-only independent original cell population"
    with journey.kernel.purpose("fit").begin() as connection:
        preliminary = prepare_record_feature_policy(
            connection,
            DdoRecordFeatureFitRequest(
                selection=feature.selection, algorithm=RecordAlgorithm(), assumptions=assumptions
            ),
        )
    assert preliminary["reading_policy"] is not None
    from corpus_structure.semantic.record_policy import FeatureInstance

    frozen = FeatureInstance.model_validate_json(canonical_bytes(preliminary["fit"]["instance"]))
    held_out = (feature.grade.frame_digest,)
    passes, facts = retain_references(
        journey, calibration_sources, partition="final_event_calibration", held_out_from=held_out
    )
    calibration_readings = run_readings(
        journey,
        calibration_sources,
        policy=preliminary["reading_policy"],
        inference="genuine-held-out-readings",
    )
    calibration = run_grade(
        journey,
        calibration_sources,
        passes,
        facts,
        calibration_readings.specification,
        calibration_readings.resolved,
        inference="genuine-held-out-grade",
    )
    assert len(calibration.grade.frame.events) == 8
    assert sum(row.correct for row in calibration.grade.frame.events) == 4
    assert all(row.final_event is not None for row in calibration.grade.frame.events)
    context = project_context(journey, "record_policy.fit")
    spec = DdoRecordFitSpecification(
        feature_selection=feature.selection,
        calibration_selection=calibration.selection,
        frozen_feature=frozen,
        applicability=DdoRecordPolicyApplicability(
            project_id=PROJECT, sources=tuple(source.pin for source in journey.sources)
        ),
        family_contract=feature.grade.frame.family_contract,
        reading_recipe=feature.grade.frame.reading_recipe,
        event_procedure=EVENT_PROCEDURE,
        assumptions=assumptions,
        threshold=0.5,
        threshold_procedure="controlled-predeclared-threshold-1",
    )
    fact = authored(
        journey,
        "exact-fit-specification",
        spec.model_dump(mode="json"),
        kind=PROTECTED_NAMESPACE + "DdoRecordFitSpecification",
        context=context,
    )
    pending = request(
        journey,
        ("record_policy.fit", "record_policy.authorize"),
        (context,),
        originals=(fact,),
        source_sets=(
            FrozenSourceSet.from_selected("record-policy-feature-grades", (feature.entry(),)),
            FrozenSourceSet.from_selected(
                "record-policy-calibration-grades", (calibration.entry(),)
            ),
        ),
        inference="genuine-protected-fit-and-native-authorization",
    )
    retained = author_record_policy_inputs(
        journey.kernel.purpose("evaluate"), journey.kernel.prepared, request=pending
    )
    result = execute_captured_kernel_demand(
        journey.kernel,
        retained["demand_id"],
        purpose="evaluate",
        fit=True,
    )
    assert result.receipt_count == 2
    _, fitted, *_ = journey.selected_products(
        journey.kernel.purpose("evaluate"),
        retained["demand_id"],
        kind=PROTECTED_NAMESPACE + "DdoFittedRecordPolicy",
    )
    _, authorization, *_ = journey.selected_products(
        journey.kernel.purpose("evaluate"),
        retained["demand_id"],
        kind=NAMESPACE + "DdoRecordPolicyAuthorization",
    )
    assert len(fitted) == len(authorization) == 1
    return FittedJourney(
        journey,
        feature,
        calibration,
        fitted[0][1],
        authorization[0][1],
        authorization[0][0]["id"],
        retained["demand_id"],
        feature_readings,
        calibration_readings,
    )


def copy_grade(journey, selected_grade):
    from corpus_structure.evaluate.declared_record_policy import (
        PROTECTED_NAMESPACE,
        DdoRecordGrade,
        DdoRecordGradeSelection,
    )
    from corpus_structure.semantic.data_operation_service import (
        create_native_demand,
    )
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet

    context = SubjectContext(
        PROJECT,
        "controlled-copy:" + PROJECT,
        None,
        b"{}",
        subject_definition=journey.kernel.model.operation("fixture.protected_grade_copy").subject,
    )
    pending = request(
        journey,
        ("fixture.protected_grade_copy",),
        (context,),
        source_sets=(
            FrozenSourceSet.from_selected("fixture-copy-grade", (selected_grade.entry(),)),
        ),
        inference="actual-captured-protected-copy",
    )
    with journey.kernel.purpose("evaluate").begin() as connection:
        demand = create_native_demand(connection, pending)["demand_id"]
    executed = execute_captured_kernel_demand(
        journey.kernel,
        demand,
        purpose="evaluate",
    )
    assert executed.receipt_count == 1
    cut, products, uses, episodes, outputs = journey.selected_products(
        journey.kernel.purpose("evaluate"), demand, kind=PROTECTED_NAMESPACE + "DdoRecordGrade"
    )
    copies = [(row, body) for row, body in products if row["subject"] == context.subject]
    ((product, body),) = copies
    (output,) = [
        row for row in outputs if row["product_id"] == product["id"] and row["role"] == "copy"
    ]
    (episode,) = [row for row in episodes if row["id"] == output["derivation_id"]]
    (use,) = [
        row for row in uses if row["derivation_id"] == episode["id"] and row["fate"] == "fulfilled"
    ]
    copied = DdoRecordGrade.from_selected_body(body)
    assert copied == selected_grade.grade
    assert product["id"] != selected_grade.product["id"]
    selection = DdoRecordGradeSelection(
        project_id=PROJECT,
        demand_id=demand,
        read_id=cut.record["read_id"],
        use_id=use["use_id"],
        derivation_id=episode["id"],
        product_id=product["id"],
        expected_cut=cut.identity,
        cut_canonical_json=cut.content.decode(),
        frame_digest=copied.frame_digest,
    )
    return SelectedGrade(copied, selection, product)


def refuse_exchanged_fitted_body(fitted, monkeypatch):
    """Two legitimate fit requests; tamper only after the second real CPU result."""
    from copy import deepcopy

    from sqlalchemy.exc import DBAPIError

    from corpus_structure.evaluate.declared_record_policy import (
        PROTECTED_NAMESPACE,
        DdoRecordFitSpecification,
        author_record_policy_inputs,
    )
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )

    journey = fitted.journey
    _, specifications, *_ = journey.selected_products(
        journey.kernel.purpose("evaluate"),
        fitted.demand_id,
        kind=PROTECTED_NAMESPACE + "DdoRecordFitSpecification",
    )
    ((_, original),) = specifications
    specification = DdoRecordFitSpecification.model_validate_json(
        canonical_bytes({**original, "threshold": 0.75})
    )
    assert specification.threshold != fitted.fitted["instance"]["threshold"]
    context = project_context(journey, "record_policy.fit")
    fact = authored(
        journey,
        "different-legitimate-fit-specification",
        specification.model_dump(mode="json"),
        kind=PROTECTED_NAMESPACE + "DdoRecordFitSpecification",
        context=context,
    )
    pending = request(
        journey,
        ("record_policy.fit", "record_policy.authorize"),
        (context,),
        originals=(fact,),
        source_sets=(
            FrozenSourceSet.from_selected(
                "record-policy-feature-grades", (fitted.feature.entry(),)
            ),
            FrozenSourceSet.from_selected(
                "record-policy-calibration-grades", (fitted.calibration.entry(),)
            ),
        ),
        inference="actual-different-fit-request-copied-conclusion-refusal",
    )
    retained = author_record_policy_inputs(
        journey.kernel.purpose("evaluate"), journey.kernel.prepared, request=pending
    )
    actual_retain = DataOperationStorage.retain_data_completion_intent
    observed = []

    def exchanged(storage, payload):
        if (
            payload["completion"]["outputs"]
            and payload["completion"]["outputs"][0]["role"] == "fitted"
        ):
            original_completion = payload["completion"]
            actual = decode_semantic_value(original_completion["outputs"][0]["product"]["body"])
            assert actual["instance"]["threshold"] == 0.75
            assert len(original_completion["execution_evidence"]["cpu_receipts"]) == 1
            altered = deepcopy(payload)
            altered["completion"]["outputs"][0]["product"]["body"] = semantic_value(fitted.fitted)
            # The current fit's real CPU/fence evidence stays untouched. This is
            # an adversarial body substitution, never a fabricated CPU receipt.
            assert (
                altered["completion"]["execution_evidence"]
                == original_completion["execution_evidence"]
            )
            try:
                return actual_retain(storage, altered)
            except DBAPIError as error:
                observed.append(error)
                raise
        return actual_retain(storage, payload)

    with monkeypatch.context() as patch:
        patch.setattr(DataOperationStorage, "retain_data_completion_intent", exchanged)
        with pytest.raises(NativeDemandExecutionError):
            execute_captured_kernel_demand(
                journey.kernel,
                retained["demand_id"],
                purpose="evaluate",
                fit=True,
            )
    assert len(observed) == 1
    import psycopg

    original_error = observed[0].orig
    assert isinstance(original_error, psycopg.errors.CheckViolation)
    assert original_error.sqlstate == "23514"
    message = original_error.diag.message_primary or ""
    assert "fitted policy differs from its actual CPU result" in message, message
    # The rejected request never obtains a fit publication or an issuer receipt.
    with journey.kernel.purpose("evaluate").begin() as connection:
        from corpus_structure.semantic.demand_results import read_demand_result

        page = read_demand_result(
            connection, retained["demand_id"], project_id=PROJECT, limit=1000, view="frontier"
        )
        assert all(row["fate"] != "fulfilled" for row in page.record["uses"])
