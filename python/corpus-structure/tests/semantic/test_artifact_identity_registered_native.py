"""Ordinary registrar and native completion for numeric configuration and exact witnesses."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.artifact_identity import (
    ArtifactIdentityConfig,
    ArtifactIdentityMethod,
)
from corpus_structure.methods.scoped_relations import SourceWorkBinding
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.artifact_identity import (
    ArtifactDeclaredRelationship,
    ArtifactIdentityProduct,
    ArtifactScoringPolicy,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, OperationConflict
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    export_review_bundle,
    verify_review_bundle,
)
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)

from .native_record_fixtures import (
    build_record_source,
    complete_contributions,
    contribution_drafts,
)
from .native_record_fixtures import (
    private_source as private_source,
)
from .primary_native_support import publish_primary_layers
from .test_companion_export_native import read_settings
from .witnessed_scenario_support import completed_metadata


@pytest.fixture
def private_source_options():
    from corpus_structure.evaluate.record_references import reference_inputs
    from corpus_structure.semantic.characterization import characterization_inputs

    return dict(bundle_transform=lambda bundle: characterization_inputs(reference_inputs(bundle)))


EDITIONS = (
    "Table 5.1 (numbering namespace: Main) (revision: old) Counts",
    "Table 5.2 (numbering namespace: Main) (revision: new)"
    " (supersedes Table 5.1 in numbering namespace Main revision old)",
    'Table 6.1 (alias: "Counts Grid") Results',
    "Table 6.2 (aliases: none) Totals",
)
CROSS_WORK_REFERENCE = (
    "See Table 5.3 (numbering namespace: Main)"
    " (cites Table 8.4 in numbering namespace Main of work other-book)"
)
CROSS_WORK_CAPTION = "Table 8.4 (numbering namespace: Main) (work: other-book) Values"


def retained_source(case, completed, revision, view):
    return ExternalSourceRef(
        project_id=case.project_id,
        run_id=case.run,
        cut_id=completed["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=revision,
        source_view_id=view["id"],
        native_task_id=view["native_task_id"],
        native_product_key=view["native_product_key"],
        native_content_digest=view["native_content_digest"],
        projection_digest=view["projection_digest"],
        recipe_digest=view["recipe_digest"],
        coordinate_version=2,
    )


@pytest.mark.parametrize(
    "private_source",
    [{}, {"sibling_captions": EDITIONS, "sibling_references": (CROSS_WORK_REFERENCE,)}],
    indirect=True,
    ids=("canonical-config", "exact-revision"),
)
def test_registered_artifact_canonical_config_completes_and_policy_forgery_refuses(
    private_source, semantic_db_engine, native_settings, tmp_path, monkeypatch
):
    case = private_source
    with case.writer.begin() as conn:
        primary_pins = list(
            publish_primary_layers(conn, case.run, case.prepared, (case.view, case.other_view))
        )
        complete_contributions(case, conn, contribution_drafts(case))
    finalize_bound_run(case.writer, case.run, "artifact-abi-native-source")
    completed, revision, _runtime = completed_metadata(case, case.run)
    source_views = table("kb.source_view")
    with case.writer.connect() as conn:
        sibling = conn.execute(select(source_views).where(source_views.c.id == case.other_view))
        edition = sibling.mappings().one()
    typed = edition["projection"]["text"] == "\n".join((*EDITIONS, CROSS_WORK_REFERENCE))
    native = edition if typed else case.view_row
    passage_text = edition["projection"]["text"] if typed else "12"
    source = retained_source(case, completed, revision, native)
    selected = [(source, passage_text, "controlled-book")]
    if typed:
        other_path = tmp_path / "cross-work"
        other_path.mkdir()
        other = build_record_source(
            semantic_db_engine,
            case.writer,
            other_path,
            case,
            project_id=case.project_id,
            existing_project=True,
            source_tag="independent-other-book",
            sibling_captions=(CROSS_WORK_CAPTION,),
        )
        with case.writer.begin() as conn:
            primary_pins.extend(
                publish_primary_layers(conn, other.run, other.prepared, (other.other_view,))
            )
            complete_contributions(other, conn, contribution_drafts(other))
            other_view = (
                conn.execute(select(source_views).where(source_views.c.id == other.other_view))
                .mappings()
                .one()
            )
        finalize_bound_run(case.writer, other.run, "artifact-other-native-source")
        other_cut, other_revision, _ = completed_metadata(other, other.run)
        selected.append(
            (
                retained_source(other, other_cut, other_revision, other_view),
                CROSS_WORK_CAPTION,
                "other-book",
            )
        )
    inputs = StructuralInput(
        question="retain an actual controlled artifact cohort under canonical config custody",
        scope="native canonical-config boundary",
        inventory_id="artifact-abi-source",
        policy_id="source-artifact-identity-1",
        sources=tuple(source for source, _, _ in selected),
        passages=tuple(
            StructuralPassage(
                passage_id=work,
                source_ref=source.identity,
                start=0,
                end=len(passage),
                text=passage,
                scope="controlled native source",
            )
            for source, passage, work in selected
        ),
        dependencies=("controlled-native-source",),
    )
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    cfg = ArtifactIdentityConfig(
        inputs=inputs,
        characterization_layers=tuple(pin.values() for pin in primary_pins),
        structural_input_digest=inputs.identity,
        title_threshold=70.5,
        policy=policy,
        work_bindings=tuple(
            SourceWorkBinding(
                native_content_digest=source.native_content_digest,
                source_work=work,
                provenance="actual controlled source fixture",
            )
            for source, _, work in selected
        ),
    )
    method = ArtifactIdentityMethod()
    registry = MethodRegistry(
        [method], MethodsFile(configs={method.name: {"default": cfg.model_dump(mode="json")}})
    )
    resolved = registry.resolve(method.name, "default")
    assert resolved.params["title_threshold"] == "70.5"
    assert resolved.params["policy"] == {
        "prior": "0.1",
        "code_m": "0.9",
        "code_u": "0.01",
        "title_m": "0.8",
        "title_u": "0.05",
    }

    def run():
        return semantic.run_source_methods(
            case.writer,
            project_id="private-records",
            prepared=case.prepared,
            binding=OperationBinding(
                case.prepared.release_id, "artifact-abi-native-source", revision, b"{}"
            ),
            registry=registry,
            graph=Graph(
                ((Stage.ASSEMBLE, (Step(method.name + "/default"),)),), policy_propose=False
            ),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            fresh=(method.name,),
        )

    success = run()
    tasks, results, configs = (
        table(n) for n in ("ops.task", "ops.task_result", "ops.method_config")
    )
    with case.writer.connect() as conn:
        row = (
            conn.execute(
                select(tasks.c.status, configs.c.params, results.c.body)
                .join(configs, configs.c.id == tasks.c.method_config_id)
                .join(results, results.c.task_id == tasks.c.id)
                .where(tasks.c.run_id == success.run_id)
            )
            .mappings()
            .one()
        )
    stored = row["params"]  # Native method_config.params is JSONB, returned as a mapping.
    assert stored == dict(resolved.params)
    assert row["status"] == "done"
    product = row["body"]["structural_product"]["artifact_identity"]
    assert product["policy"] == policy.model_dump(mode="json")
    assert all(isinstance(v, float) for v in product["policy"].values())
    if typed:
        declarations = {witness["kind"]: witness for witness in product["declared_relationships"]}
        assert set(declarations) == {"reference", "supersedes"}
        witness = declarations["supersedes"]
        assert witness["outcome"] == "witnessed_candidate"
        assert witness["origin"]["text"] == (
            " (supersedes Table 5.1 in numbering namespace Main revision old)"
        )
        (endpoint,) = witness["targets"]
        records = {r["contribution_id"]: r for r in product["records"]}
        assert records[witness["source_id"]]["revision"]["value"] == "new"
        assert records[endpoint["record_id"]]["revision"]["value"] == "old"
        pair_key = sorted((witness["source_id"], endpoint["record_id"]))
        (pair,) = [p for p in product["pairs"] if [p["left"], p["right"]] == pair_key]
        assert "external_pairs" in pair["candidate_routes"]
        assert pair["revision_relation"] == "different_observed"
        aliases = {r["artifact"]["controlled_code"]: r["artifact"] for r in records.values()}
        assert aliases["5.1"]["alias_state"] == "unknown"
        assert aliases["6.1"]["alias_state"] == "observed"
        assert aliases["6.1"]["alias_occurrences"][0]["text"] == "Counts Grid"
        assert aliases["6.2"]["alias_state"] == "known_empty"
        assert aliases["6.2"]["alias_absence"]["text"] == "aliases: none"
        citation = declarations["reference"]
        (target,) = citation["targets"]
        assert records[citation["source_id"]]["artifact"]["source_work"] == "controlled-book"
        assert records[target["record_id"]]["artifact"]["source_work"] == "other-book"
        assert target["work_cue"]["text"] == " (work: other-book)"
        pair_key = sorted((citation["source_id"], target["record_id"]))
        (pair,) = [p for p in product["pairs"] if [p["left"], p["right"]] == pair_key]
        assert pair["candidate_routes"] == ["external_pairs"]
        assert pair["score_status"] == "excluded" and pair.get("model_probability") is None
        finalize_bound_run(case.writer, success.run_id, "artifact-abi-native-revision")
        bound, _, _ = completed_metadata(case, success.run_id)
        selection = StructuralExportRequest(
            run_id=success.run_id, cut_id=bound["cut_id"], kind="artifact_identity"
        )
        with read_snapshot(case.writer) as conn:
            page = read_structural_export_page(conn, selection)
        (retained,) = page.reports
        assert retained.artifact_identity == ArtifactIdentityProduct.model_validate(product)
        bundle = tmp_path / "typed-artifact-closure"
        export_review_bundle(
            ReviewSelection(structural_selections=(selection,)),
            bundle,
            read_settings(native_settings, semantic_db_engine),
            exact_closure=True,
        )
        verify_review_bundle(bundle)
    else:
        assert product["pairs"] == []
        assert product["declared_relationships"] == []

    original = ArtifactIdentityMethod.run

    def forged(self, units, configuration, context):
        produced = original(self, units, configuration, context)
        altered = []
        for result in produced:
            payload = json.loads(json.dumps(result.structural_product))
            identity = payload["artifact_identity"]
            if typed:
                declaration = next(
                    d for d in identity["declared_relationships"] if d["kind"] == "supersedes"
                )
                old_key = ArtifactDeclaredRelationship.model_validate(declaration).identity
                declaration["kind"] = "same_lineage"
                new_key = ArtifactDeclaredRelationship.model_validate(declaration).identity
                for pair in identity["pairs"]:
                    pair["dependencies"] = sorted(
                        "artifact-declaration:" + new_key
                        if dep == "artifact-declaration:" + old_key
                        else dep
                        for dep in pair["dependencies"]
                    )
            else:
                identity["policy"]["prior"] = 0.2
            altered.append(replace(result, structural_product=payload))
        return tuple(altered)

    monkeypatch.setattr(ArtifactIdentityMethod, "run", forged)
    match = "artifact typed relationships differ" if typed else "artifact model requires"
    with pytest.raises((DBAPIError, OperationConflict), match=match):
        run()
    with case.writer.connect() as conn:
        failed = (
            conn.execute(
                select(tasks.c.id, tasks.c.status)
                .where(
                    tasks.c.method_config_id
                    == conn.scalar(
                        select(tasks.c.method_config_id).where(tasks.c.run_id == success.run_id)
                    )
                )
                .order_by(tasks.c.id.desc())
                .limit(1)
            )
            .mappings()
            .one()
        )
        assert failed["status"] in {"failed", "cancelled"}
        assert (
            conn.scalar(select(results.c.task_id).where(results.c.task_id == failed["id"])) is None
        )
