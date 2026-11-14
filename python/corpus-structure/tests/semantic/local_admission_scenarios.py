"""Recipe-owned sealed local and independently judged record publication scenarios."""

import json
from dataclasses import asdict, dataclass, replace
from types import MappingProxyType
from typing import Any

import pytest
from scenario_recipes import register_scenario_builder
from sqlalchemy import select, text

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrameV2,
    OperationSourceOpportunity,
    create_reference_set,
    record_pass,
    reference_evaluate,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.local_semantic_admission import CONTEXT_POLICY, QUESTION, RUBRIC
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.operations import (
    OperationBinding,
    create_run,
    create_task,
    read_original,
    seal_cut,
)
from semantic.native_record_fixtures import (
    ClaimedRecordSource,
    RecordSourceRecipe,
    build_record_recipe,
    claim_record_source,
    complete_contributions,
    contribution_drafts,
)
from semantic.reference_scenarios import expected_reading
from semantic.witnessed_scenario_support import completed_relationship_case

_BASE_RECORD_SOURCE = RecordSourceRecipe()
_CONTEXTUAL_RECORD_SOURCE = RecordSourceRecipe(
    composition="reference", additional_methods=("private.contextual",)
)


@dataclass(frozen=True, kw_only=True)
class JudgedRecordSource(ClaimedRecordSource):
    semantic_reference: tuple
    semantic_grade: tuple
    semantic_grades: tuple


@dataclass(frozen=True)
class LocalWitnessRecipe:
    source: RecordSourceRecipe = _BASE_RECORD_SOURCE


@dataclass(frozen=True)
class JudgedSourceRecipe:
    partition: str = "development"
    judgment: str = "supported"
    partial: bool = False
    cases: int = 1
    grades: int = 1
    provider_profile: str = "controlled_relationship"
    source: RecordSourceRecipe = _CONTEXTUAL_RECORD_SOURCE

    def __post_init__(self):
        if self.provider_profile != "controlled_relationship":
            raise ValueError("unknown judged-source provider profile")
        if self.cases < 1 or self.grades < 1:
            raise ValueError("judged-source populations must be positive")


@dataclass(frozen=True)
class LocalPublicationStage:
    case: Any
    run: Any
    cut: Any
    grades: tuple = ()

    @property
    def seed_files(self):
        # Native originals are retained artifacts; controlled provider paths are
        # build-only inputs and no provider runs again on these publication clones.
        return ()

    def validate_clone(self, admin):
        if self.case.writer is not None or self.case.clone is not None:
            raise ValueError("publication seed stage retains live consumer resources")
        with admin.connect() as connection:
            documents, artifacts = table("kb.document"), table("kb.source_artifact")
            assert (
                connection.scalar(
                    select(artifacts.c.artifact_digest)
                    .select_from(
                        documents.join(
                            artifacts, artifacts.c.artifact_digest == documents.c.content_hash
                        )
                    )
                    .where(documents.c.id == self.case.document)
                )
                is not None
            )
            read_original(connection, self.case.document, prepared=self.case.prepared)
            cuts, runs, tasks = table("ops.input_cut"), table("ops.run"), table("ops.task")
            assert connection.execute(
                select(cuts.c.run_id, cuts.c.final, runs.c.sealed)
                .join(runs, runs.c.id == cuts.c.run_id)
                .where(cuts.c.id == self.cut)
            ).one() == (self.run, True, True)
            assert connection.execute(
                select(tasks.c.status, tasks.c.invocation_key).where(tasks.c.id == self.case.task)
            ).one() == ("done", self.case.invocation_key)
            for identity, digest in self.grades:
                assert (
                    connection.scalar(
                        select(table("eval.reference_evaluation").c.content_digest).where(
                            table("eval.reference_evaluation").c.id == identity
                        )
                    )
                    == digest
                )

    def bind(self, writer, *, clone=None):
        return replace(self.case, writer=writer, clone=clone), self.run, self.cut


def build_local_witness_recipe(recipe, admin, writer, directory, *, purpose_engine=None):
    case = claim_record_source(
        build_record_recipe(recipe.source, admin, writer, directory), writer=writer
    )
    with writer.begin() as connection:
        complete_contributions(case, connection, contribution_drafts(case))
        cut = seal_cut(connection, case.run, "local-source-final", final=True)
    return LocalPublicationStage(replace(case, writer=None, clone=None), case.run, cut)


def build_judged_source(original_case, selected, evaluator, monkeypatch, directory):
    partition = selected.get("partition", "development")
    linked = completed_relationship_case(original_case, monkeypatch, directory)
    from corpus_structure.orchestrate.commands import finalize_bound_run

    finalize_bound_run(original_case.writer, linked.outcome.run_id, "semantic-source-private")
    case = replace(original_case, run=linked.outcome.run_id)
    with case.writer.connect() as conn:
        tasks, configs, methods = (
            table(n) for n in ("ops.task", "ops.method_config", "ops.method")
        )
        task_row = dict(
            conn.execute(
                select(tasks)
                .join(configs, configs.c.id == tasks.c.method_config_id)
                .join(methods, methods.c.id == configs.c.method_id)
                .where(tasks.c.run_id == case.run, methods.c.name == "retrieve.contextual")
            )
            .mappings()
            .one()
        )
        case = replace(
            case,
            task_row=MappingProxyType(task_row),
            task=task_row["id"],
            record_config=task_row["method_config_id"],
            invocation_key=task_row["invocation_key"],
        )
        cut = conn.scalar(
            select(table("ops.completed_result").c.cut_id).where(
                table("ops.completed_result").c.run_id == case.run
            )
        )
    source = linked.completed.source
    citation = dict(
        source=dict(
            project_id="private-records",
            native_product_key=source.native_product_key,
            native_content_digest=source.native_content_digest,
            projection_digest=source.projection_digest,
            recipe_digest=source.recipe_digest,
            coordinate_version=2,
        ),
        start=0,
        end=2,
        text="12",
        scope="controlled-source",
    )
    target_meaning = dict(
        term=citation, content=citation, interpretation="definition", scope="controlled-source"
    )
    with evaluator.begin() as conn:
        uri = conn.scalar(
            select(table("kb.document").c.source_uri).where(
                table("kb.document").c.id == case.view_row["document_id"]
            )
        )
        assign_origin(
            conn,
            project_id="private-records",
            origin_group="relationship-control",
            partition=partition,
            source_uris=(uri,),
            provenance={"source": "controlled native12"},
        )
        split_documents(
            conn,
            "private-records",
            SplitConfig(forced_dev={uri: "controlled source"}),
            release_id=case.prepared.release_id,
        )
        logical = source_binding(
            conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=cut
        )
        reading, old_frame = expected_reading(case, logical)
        anchor = reading["anchors"][0]
        frame = OperationEvaluationFrameV2(
            source_group="relationship-control",
            partition=partition,
            inspected_scope=case.table + "/data/table_cells/0",
            opportunities=(
                OperationSourceOpportunity(
                    "relationship", case.view, 0, 2, "relationship", "stated"
                ),
            ),
            unit=old_frame.unit,
            release_id=case.prepared.release_id,
            guideline_version="relationship-control-2",
            rubric_version=RUBRIC,
            context_policy=CONTEXT_POLICY,
            operation_question=QUESTION,
            operation_version="2",
            domain="scientific-source",
            direction="source_first",
            pin=old_frame.pin,
            anchor_ids=(anchor["anchor_id"],),
            anchor_scopes=old_frame.anchor_scopes,
        )
        created = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=case.run,
            source_cut_id=cut,
            label="controlled-relationship",
            legacy_split="dev",
            guideline=frame.guideline_version,
            guideline_text="Resolve only numeral12 to declared target12.",
            partition=partition,
            frames={frame.unit: frame},
            sampling=dict(
                seed=1,
                strata={frame.unit: "controlled"},
                inclusion_probabilities={frame.unit: 1},
                provenance={"selection": "controlled native12"},
                cohort="native-relationship-control",
            ),
        )
        unit = conn.scalar(
            select(table("eval.reference_unit").c.id).where(
                table("eval.reference_unit").c.set_id == created["set_id"]
            )
        )
        expected = OperationCase(
            case_id="numeral12-denotation",
            facet="relationship",
            anchor_ids=(anchor["anchor_id"],),
            inspected_scope=case.table + "/data/table_cells/0",
            source_state="stated",
            judgment="supported",
            alternatives=(
                dict(
                    semantic_type="contextual.relationship",
                    value=source_value(
                        json.loads(
                            canonical_bytes(
                                dict(
                                    relation="denotes",
                                    scope="controlled-source",
                                    effective_version=None,
                                    target=target_meaning,
                                )
                            )
                        )
                    ),
                ),
            ),
            explanation=(
                "Controlled source cell12 denotes the independently "
                "specified source-backed numeral attachment."
            ),
            assessor_provenance={"assistance": "none; independent fixed expectation"},
        )
        if "judgment" in selected:
            expected = replace(expected, judgment=selected["judgment"])
        if selected.get("partial"):
            expected = replace(
                expected, alternatives=({"semantic_type": "contextual.relationship"},)
            )
        payload = dict(
            protocol=PROTOCOL,
            release_id=frame.release_id,
            unit_ref=frame.unit,
            guideline=frame.guideline_version,
            rubric_version=RUBRIC,
            context_policy=CONTEXT_POLICY,
            operation_question=QUESTION,
            operation_version="2",
            domain=frame.domain,
            direction="source_first",
            reason="Independent controlled source expectation",
            cases=[
                asdict(replace(expected, case_id=f"numeral12-denotation-{index}"))
                if selected.get("cases", 1) > 1
                else asdict(expected)
                for index in range(selected.get("cases", 1))
            ],
            adjudication_passes=[],
        )
        a = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="denotation-A",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        b = record_pass(
            conn,
            unit_id=unit,
            pass_kind="B",
            actor="denotation-B",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        payload["adjudication_passes"] = [a, b]
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="denotation-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        grade = reference_evaluate(
            conn, project_id="private-records", run_id=case.run, set_id=created["set_id"]
        )
        digest = conn.scalar(
            select(table("eval.reference_evaluation").c.content_digest).where(
                table("eval.reference_evaluation").c.id == grade.id
            )
        )
        semantic_reference = (unit, frame, payload)
        semantic_grade = (grade.id, digest)
        semantic_grades = [semantic_grade]
        for _ in range(selected.get("grades", 1) - 1):
            additional = reference_evaluate(
                conn, project_id="private-records", run_id=case.run, set_id=created["set_id"]
            )
            additional_digest = conn.scalar(
                select(table("eval.reference_evaluation").c.content_digest).where(
                    table("eval.reference_evaluation").c.id == additional.id
                )
            )
            semantic_grades.append((additional.id, additional_digest))
    case = JudgedRecordSource(
        **vars(case),
        semantic_reference=semantic_reference,
        semantic_grade=semantic_grade,
        semantic_grades=tuple(semantic_grades),
    )
    with case.writer.begin() as conn:
        origin_run = (
            conn.execute(select(table("ops.run")).where(table("ops.run").c.id == case.run))
            .mappings()
            .one()
        )
        manifest = json.loads(bytes(origin_run["dependencies"])) | {
            "local_semantic_admission": [
                dict(evaluation_id=identity, evaluation_digest=content)
                for identity, content in case.semantic_grades
            ]
        }
        run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(
                case.prepared.release_id,
                origin_run["input_realization_id"],
                origin_run["input_revision"],
                canonical_bytes(manifest),
            ),
            kind="full",
            options={},
            code_commit="semantic-publication-followup",
        )
        conn.execute(
            text("SELECT ops.select_source_view(:r,:old,:v)"),
            dict(r=run, old=case.run, v=case.view),
        )
        selected = create_task(
            conn,
            run_id=run,
            config_id=case.task_row["method_config_id"],
            stage="record",
            unit_type="source_view",
            unit_id=case.view,
            unit_key=case.task_row["unit_key"],
            input_hash=case.task_row["input_hash"],
        )
        assert conn.execute(
            select(table("ops.task").c.status, table("ops.task").c.reused_task_id).where(
                table("ops.task").c.id == selected
            )
        ).one() == ("reused", case.task)
        final = seal_cut(conn, run, "judged-publication-final", final=True)
    return case, run, final


def build_judged_recipe(recipe, admin, writer, directory, *, purpose_engine):
    original = claim_record_source(
        build_record_recipe(recipe.source, admin, writer, directory), writer=writer
    )
    evaluator = purpose_engine("evaluate")
    with pytest.MonkeyPatch.context() as patch:
        case, run, cut = build_judged_source(
            original,
            dict(
                partition=recipe.partition,
                judgment=recipe.judgment,
                partial=recipe.partial,
                cases=recipe.cases,
                grades=recipe.grades,
            ),
            evaluator,
            patch,
            directory,
        )
    return LocalPublicationStage(
        replace(case, writer=None, clone=None), run, cut, case.semantic_grades
    )


register_scenario_builder(LocalWitnessRecipe, build_local_witness_recipe)
register_scenario_builder(JudgedSourceRecipe, build_judged_recipe)
