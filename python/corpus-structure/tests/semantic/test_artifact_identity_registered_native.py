"""Current declared artifact custody, exact numeric policy and witness refusal.

PDF contents are controlled. Source admission, navigation, CPU replies, claims,
completion and selected reads are real; no provider/scientific standing is asserted.
"""

from copy import deepcopy

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import DeclaredArtifactDeclaredRelationship, DeclaredArtifactIdentityProduct
from corpus_structure.serve.structural_products import SelectedStructuralRequest, inspect_selected_structures
from semantic.current_artifact_support import ARTIFACT, CONSTRUCTIONS, artifact_recipe, artifact_stream, companion_source
from semantic.current_pdf_source_support import PROJECT, _current_pdf_source, admit_current_target
from semantic.structural_admission_native_support import execute, request, selected
from semantic.structural_production_native_support import produce_source_reports, selected_for_source

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


@pytest.mark.parametrize("typed", [False, True], ids=("canonical-config", "exact-revision-cross-work"))
def test_current_artifact_numeric_policy_exact_witness_and_atomic_cpu_output_refusal(
    scenario_seeds, tmp_path, monkeypatch, typed
):
    rows = tuple(("caption", value) for value in EDITIONS) + (("text", CROSS_WORK_REFERENCE),) if typed else (("text", "12"),)

    def stream(self, original, **options):
        return artifact_stream(rows, self, original, **options)

    with _current_pdf_source(scenario_seeds, tmp_path, monkeypatch, stream=stream) as source:
        kernel = admit_current_target(source, artifact_recipe(tmp_path / "recipe"), tmp_path / "consumer")
        literal = "\n".join(value for _, value in rows)
        _, first, first_products, _ = produce_source_reports(source, kernel, CONSTRUCTIONS, text=literal)
        originals = [first]
        constructions = list(selected_for_source(kernel, first_products,
            "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct", first))
        works = ["controlled-book"]
        if typed:
            other = companion_source(source, tmp_path / "other-original", monkeypatch, (("caption", CROSS_WORK_CAPTION),))
            _, second, second_products, _ = produce_source_reports(other, kernel, CONSTRUCTIONS, text=CROSS_WORK_CAPTION)
            assert second.row["original_source"] != first.row["original_source"]
            originals.append(second)
            works.append("other-book")
            constructions.extend(selected_for_source(kernel, second_products,
                "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct", second))
        assert len(constructions) == len(originals)
        parameters = dict(selections=[dict(source_reference=canonical_bytes([value.row["product_id"], value.row["member_id"]]).decode(),
            passage_id=work, start=0, end=len(value.body["text"]), scope="controlled native source", source_work=work,
            mapping_provenance="actual controlled source fixture") for value, work in zip(originals, works, strict=True)],
            title_threshold=70.5, policy=dict(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05))
        pending = request(kernel, (ARTIFACT,), first.context,
            source_sets=(FrozenSourceSet("artifact-sources", tuple(value.entry() for value in originals)),
                FrozenSourceSet("artifact-constructions", tuple(value.entry() for value in constructions)),
                FrozenSourceSet("artifact-nominations", ())),
            selections=(DemandOperationSelection(operation=ARTIFACT, parameters=parameters),),
            inference="exact-native-artifact-policy-and-witness-cohort")
        retained = DataOperationStorage.retain_data_completion_intent
        attempted = []

        def intercept(storage, payload):
            with kernel.engine.connect() as connection:
                operation = connection.scalar(text("SELECT operation_id FROM ops.data_request WHERE id=:id"), {"id": payload["request_id"]})
            if operation == ARTIFACT and not attempted:
                bad = deepcopy(payload)
                body = decode_semantic_value(bad["completion"]["outputs"][0]["product"]["body"])
                identity = body["artifact_identity"]
                if typed:
                    declaration = next(value for value in identity["declared_relationships"] if value["kind"] == "supersedes")
                    old_key = DeclaredArtifactDeclaredRelationship.model_validate(declaration).identity
                    declaration["kind"] = "same_lineage"
                    new_key = DeclaredArtifactDeclaredRelationship.model_validate(declaration).identity
                    for pair in identity["pairs"]:
                        pair["dependencies"] = sorted("artifact-declaration:" + new_key if value == "artifact-declaration:" + old_key else value for value in pair["dependencies"])
                else:
                    identity["policy"]["prior"] = 0.2
                # Keep internal domain consistency; the refusal must bind the actual
                # released inputs/CPU observation rather than a malformed model.
                DeclaredArtifactIdentityProduct.model_validate(identity)
                bad["completion"]["outputs"][0]["product"]["body"] = semantic_value(body)
                assert bad["completion"]["execution_evidence"] == payload["completion"]["execution_evidence"]
                counts = text("SELECT (SELECT count(*) FROM ops.data_completion_intent),(SELECT count(*) FROM kb.data_product),"
                    "(SELECT count(*) FROM ops.data_derivation),(SELECT count(*) FROM ops.data_publication_receipt)")
                with kernel.engine.connect() as connection:
                    before = connection.execute(counts).one()
                    claim = connection.execute(text("SELECT status,attempt,claimed_by FROM ops.task WHERE id=:id"),
                        {"id": payload["task_id"]}).one()
                    assert claim == ("running", payload["attempt"], payload["holder"])
                with pytest.raises(DBAPIError, match="artifact publication differs"), storage.connection.begin_nested():
                    retained(storage, bad)
                with kernel.engine.connect() as connection:
                    assert connection.execute(counts).one() == before
                    assert connection.execute(text("SELECT status,attempt,claimed_by FROM ops.task WHERE id=:id"),
                        {"id": payload["task_id"]}).one() == claim
                attempted.append(payload["request_id"])
            return retained(storage, payload)

        monkeypatch.setattr(DataOperationStorage, "retain_data_completion_intent", intercept)
        demand, result = execute(kernel, pending)
        assert len(attempted) == 1 and result.receipt_count == 1
        (report,) = selected(kernel, demand["demand_id"], kind="urn:corpus:structural:DeclaredArtifactReport")
        product = report.body["artifact_identity"]
        assert product["standing"] == "candidate_relative_private"
        assert product["policy"] == parameters["policy"]
        assert all(type(value) is float for value in product["policy"].values())
        with kernel.engine.connect() as connection:
            basis = connection.scalar(text("SELECT ops.ddo_cpu_input_basis(r) FROM ops.data_request r WHERE id=:id"), {"id": attempted[0]})
        actual_parameters = decode_semantic_value(basis)["parameters"]
        assert type(actual_parameters["title_threshold"]) is float and actual_parameters["title_threshold"] == 70.5
        assert actual_parameters["policy"] == parameters["policy"]
        assert all(type(value) is float for value in actual_parameters["policy"].values())
        with kernel.purpose("read").begin() as connection:
            page = inspect_selected_structures(connection, SelectedStructuralRequest(project_id=PROJECT,
                demand_id=demand["demand_id"], roots=(report.root,)))
        assert page["standing"] == "private_proposal" and page["public_admission"] == "not-established"
        (observed,) = page["reports"]
        assert observed["availability"] == "observed"
        assert DeclaredArtifactIdentityProduct.model_validate(observed["report"]["artifact_identity"]) == DeclaredArtifactIdentityProduct.model_validate(product)
        if typed:
            declarations = {value["kind"]: value for value in product["declared_relationships"]}
            assert set(declarations) == {"reference", "supersedes"}
            witness = declarations["supersedes"]
            assert witness["outcome"] == "witnessed_candidate"
            assert witness["origin"]["text"] == " (supersedes Table 5.1 in numbering namespace Main revision old)"
            (endpoint,) = witness["targets"]
            records = {value["contribution_id"]: value for value in product["records"]}
            assert records[witness["source_id"]]["revision"]["value"] == "new"
            assert records[endpoint["record_id"]]["revision"]["value"] == "old"
            pair_key = sorted((witness["source_id"], endpoint["record_id"]))
            (pair,) = [value for value in product["pairs"] if [value["left"], value["right"]] == pair_key]
            assert "external_pairs" in pair["candidate_routes"] and pair["revision_relation"] == "different_observed"
            aliases = {value["artifact"]["controlled_code"]: value["artifact"] for value in records.values()}
            assert aliases["5.1"]["alias_state"] == "unknown"
            assert aliases["6.1"]["alias_state"] == "observed" and aliases["6.1"]["alias_occurrences"][0]["text"] == "Counts Grid"
            assert aliases["6.2"]["alias_state"] == "known_empty" and aliases["6.2"]["alias_absence"]["text"] == "aliases: none"
            citation = declarations["reference"]
            (target,) = citation["targets"]
            assert records[citation["source_id"]]["artifact"]["source_work"] == "controlled-book"
            assert records[target["record_id"]]["artifact"]["source_work"] == "other-book"
            assert target["work_cue"]["text"] == " (work: other-book)"
            pair_key = sorted((citation["source_id"], target["record_id"]))
            (pair,) = [value for value in product["pairs"] if [value["left"], value["right"]] == pair_key]
            assert pair["candidate_routes"] == ["external_pairs"]
            assert pair["score_status"] == "excluded" and pair.get("model_probability") is None
        else:
            assert product["pairs"] == [] and product["declared_relationships"] == []
