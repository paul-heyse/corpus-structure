"""Private composition respects exact retained membership and provider roles."""

import pytest

from corpus_structure.semantic.contribution_queries import ContributionInventory
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve import review_bundle
from corpus_structure.serve.contributions import ContributionRequest, _interpretations

PIN = {"source": "source-a", "source_view_id": 2}
SCOPE = {"pin": PIN, "projection_extent": [10, 70], "scope_digest": "a" * 64}


def _operation(task, question, *, outcome="succeeded"):
    return {
        "selected_task_id": task,
        "origin_task_id": task - 1,
        "source_view_id": 2,
        "source": "source-a",
        "operation_key": f"op-{task}",
        "operation_version": "1",
        "question": question,
        "cut_member": True,
        "outcome": outcome,
    }


def _row(op, key, semantic_type, *, value=None, members=(), missing=(), located=False):
    identity = f"{key}-id"
    return {
        **{
            key: op[key]
            for key in (
                "selected_task_id",
                "origin_task_id",
                "source_view_id",
                "operation_key",
                "cut_member",
            )
        },
        "pin": PIN,
        "item_key": key,
        "contribution_id": identity,
        "semantic_type": semantic_type,
        "value": source_value(
            {
                **(value or {}),
                "location_keys": [*members, *missing],
                "unlocated_members": list(missing),
            }
        ),
        "members": tuple(f"{member}-id" for member in members),
        "anchors": ({"anchor_id": f"{key}-anchor", "space": "native", "precision": "exact"},)
        if located
        else (),
        **({"occurrence_id": f"{key}-occurrence"} if located else {}),
    }


def _facets(ops, rows):
    inventory = ContributionInventory((), tuple(ops), (), False, tuple(rows))
    return {
        row["contribution_id"]: row["composition"]
        for row in _interpretations(inventory)
        if "composition" in row
    }


def test_parser_join_preserves_roles_and_located_parts_when_siblings_are_missing():
    operation = _operation(10, "pm2.hanlp.frames")
    other = _operation(20, "pm2.hanlp.frames")
    host = _row(
        operation,
        "host",
        "linguistic.predicate_frame",
        value={
            "predicate": "verb",
            "focus": "verb",
            "dependency_arguments": [{"role": "nsubj:pass", "location": "subject"}],
            "srl_frames": [
                {"predicate": "verb", "arguments": [{"role": "ARG1", "location": "subject"}]}
            ],
        },
        members=("verb",),
        missing=("subject",),
    )
    cue = _row(
        operation,
        "cue",
        "linguistic.qualifier_cue",
        value={"location": "condition", "marker": "if", "candidates": ["host"]},
        members=("condition", "if", "host"),
    )
    products = (
        host,
        cue,
        _row(operation, "condition", "source_occurrence", located=True),
        _row(operation, "verb", "source_occurrence", located=True),
        # A row in another operation has the same key and identity but is not this member.
        _row(other, "if", "source_occurrence", located=True),
    )
    parts = _facets((operation, other), products)
    assert [(role["role"], role["state"]) for role in parts["cue-id"]["roles"]] == [
        ("cue", "source_located"),
        ("marker", "outside_selection"),
        ("host", "retained"),
    ]
    assert parts["cue-id"]["roles"][2]["reference"]["contribution_id"] == "host-id"
    assert [
        (role["role_family"], role["role"], role["state"]) for role in parts["host-id"]["roles"]
    ] == [
        ("frame", "predicate", "source_located"),
        ("frame", "focus", "source_located"),
        ("native_dependency", "nsubj:pass", "source_unavailable"),
        ("native_srl", "PRED", "source_located"),
        ("native_srl", "ARG1", "source_unavailable"),
    ]
    with pytest.raises(SemanticRefusal, match="original source member"):
        substituted = {
            **_row(operation, "if", "source_occurrence", located=True),
            "pin": {**PIN, "source": "other-source"},
        }
        _facets((operation, other), (*products, substituted))
    with pytest.raises(SemanticRefusal, match="exact producing operation"):
        _facets((other,), products)


def test_discourse_returns_only_located_members_of_the_selected_ordered_arm():
    operation = _operation(10, "pm2.dipo.discourse")
    root = _row(
        operation,
        "tree",
        "dipo.tree",
        value={
            "root": [0, 4],
            "arm": "learned",
            "splits": [
                {"left": [0, 2], "right": [2, 4], "nuclearity": "NS", "relation": "background"},
                {"left": [0, 1], "right": [1, 2], "nuclearity": "NN", "relation": "joint"},
                {"left": [2, 3], "right": [3, 4], "nuclearity": "SN", "relation": "elaboration"},
            ],
        },
        members=tuple(f"edu-{i}" for i in range(4)),
    )
    edus = tuple(
        _row(
            operation,
            f"edu-{i}",
            "dipo.edu",
            value={"edu": i, "arm": "learned", "location_key": f"location-{i}"},
            **({"members": (f"location-{i}",)} if i < 3 else {"missing": ("location-3",)}),
        )
        for i in range(4)
    )
    extents = tuple(
        _row(operation, f"location-{i}", "source_occurrence", located=True) for i in range(3)
    )
    parts = _facets((operation,), (root, *edus, *extents))
    context = parts["edu-0-id"]["discourse_context"]
    assert context["sibling"] == [1, 2]
    assert context["omitted"] == [{"range": [2, 4], "reason": "unmapped_edu"}]
    assert [item["contribution_id"] for item in context["neighbors"]] == ["edu-1-id"]
    assert context["tree"]["contribution_id"] == "tree-id"
    assert "relation" not in context
    assert parts["edu-3-id"]["discourse_context"]["reason"] == "focal_edu_unmapped"
    assert _facets((operation,), (*edus, *extents))["edu-0-id"]["discourse_context"] == {
        "outcome": "unavailable",
        "reason": "tree_outside_selection",
    }


def _located(op, key, start, end, literal):
    row = _row(op, key, "source_occurrence", located=True)
    row["anchors"][0].update(pointer="#/texts/0", start=start, end=end, source_piece=literal)
    return row


def test_retained_host_and_srl_modifier_do_not_require_complete_svo():
    op = _operation(10, "pm2.hanlp.frames")
    verb = _located(op, "verb", 10, 14, "wait")
    qualifier = _located(op, "qualifier", 20, 27, "if busy")
    marker = _located(op, "marker", 20, 22, "if")
    temporal = _located(op, "temporal", 15, 19, "soon")
    clause_extent = _located(op, "extent", 0, 19, "Operators wait soon")
    frame = _row(
        op,
        "frame",
        "linguistic.predicate_frame",
        value={
            "sentence": 0,
            "predicate": "verb",
            "focus": "verb",
            "dependency_arguments": [],
            "srl_frames": [
                {"predicate": "verb", "arguments": [{"role": "ARGM-TMP", "location": "temporal"}]}
            ],
        },
        members=("verb", "temporal"),
    )
    cue = _row(
        op,
        "cue",
        "linguistic.qualifier_cue",
        value={
            "kind": "condition",
            "location": "qualifier",
            "marker": "marker",
            "candidates": ["frame"],
        },
        members=("qualifier", "marker", "frame"),
    )
    clause = _row(
        op,
        "clause",
        "linguistic.constituent",
        value={"sentence": 0, "label": "S", "location": "extent"},
        members=("extent",),
    )
    selected = (frame, cue, clause, verb, qualifier, marker, temporal, clause_extent)
    result = _facets((op,), selected)
    (association,) = result["cue-id"]["qualifier_host_candidates"]
    assert association["status"] == "candidate"
    assert association["host"]["anchor_ids"] == ("verb-anchor",)
    assert association["qualifier"]["anchor_ids"] == ("qualifier-anchor",)
    (modifier,) = result["frame-id"]["modifier_candidates"]
    assert modifier["modifier"]["role"] == "ARGM-TMP"
    assert modifier["modifier"]["anchor_ids"] == ("temporal-anchor",)
    assert result["frame-id"]["clause_containment"][0]["clause"]["contribution_id"] == "clause-id"
    without_host = _facets((op,), tuple(row for row in selected if row is not verb))
    assert "qualifier_host_candidates" not in without_host["cue-id"]
    assert "modifier_candidates" not in without_host["frame-id"]


def test_maverick_nominal_comparator_reuses_only_exact_selected_phrase_evidence():
    maverick = _operation(10, "pm2.maverick.coreference")
    hanlp = _operation(20, "pm2.hanlp.frames")
    earliest = _located(maverick, "earliest-extent", 0, 12, "A supervisor")
    nearest = _located(maverick, "near-extent", 17, 20, "She")
    focal = _located(maverick, "focal-extent", 24, 27, "her")
    mentions = tuple(
        _row(
            maverick,
            key,
            "maverick.mention",
            value={"first": i, "last": i + length},
            members=(extent["item_key"],),
        )
        for key, extent, i, length in (
            ("earliest", earliest, 0, 1),
            ("near", nearest, 4, 0),
            ("focal", focal, 7, 0),
        )
    )
    cluster = _row(
        maverick,
        "cluster",
        "maverick.cluster",
        value={"member_keys": [row["item_key"] for row in mentions]},
        members=tuple(row["item_key"] for row in mentions),
    )
    phrase_extent = _located(hanlp, "phrase-extent", 0, 12, "A supervisor")
    phrase_extent["anchors"][0]["anchor_id"] = earliest["anchors"][0]["anchor_id"]
    phrase = _row(
        hanlp,
        "phrase",
        "linguistic.constituent",
        value={"sentence": 0, "label": "NP", "location": "phrase-extent"},
        members=("phrase-extent",),
    )
    cluster_rows = (cluster, *mentions, earliest, nearest, focal)
    result = _facets((maverick, hanlp), (*cluster_rows, phrase_extent, phrase))
    comparison = result["focal-id"]["local_referent_candidates"]
    assert comparison["nearest"]["mention"]["contribution_id"] == "near-id"
    assert comparison["nominal"]["mention"]["contribution_id"] == "earliest-id"
    assert comparison["nominal"]["phrase"]["origin_task_id"] == 19
    assert comparison["status"] == "candidate"
    assert (
        _facets((maverick,), cluster_rows)["focal-id"]["local_referent_candidates"]["nominal"]
        is None
    )


def test_interpretation_projects_exact_focus_and_candidates_without_admission():
    op = _operation(10, "qualification_scope_v1")

    def ref(key):
        return {
            "contribution_id": "source-contribution:" + key * 64,
            "project_id": "project",
            "release_id": "release",
            "run_id": 3,
            "cut_id": 4,
            "result_revision": 1,
            "selected_task_id": 2,
            "origin_task_id": 1,
            "runtime_fingerprint": "runtime",
        }

    reading = _row(
        op,
        "question",
        "interpretation.qualification_scope_v1",
        value={
            "state": "proposed",
            "assessed_scope": SCOPE,
            "focus": ref("a"),
            "native_answer": {"probabilities": {"no_match": 0.1, "a": 0.8, "b": 0.1}},
            "selected_keys": ["a"],
            "candidates": [
                {"key": "a", "semantic_type": "linguistic.predicate_frame", "reference": ref("b")},
                {"key": "b", "semantic_type": "linguistic.predicate_frame", "reference": ref("c")},
            ],
        },
    )
    composition = _facets((op,), (reading,))["question-id"]
    assert composition["standing"] == "retained_private"
    assert composition["assessed_scope"] == SCOPE
    focus, no_match, choice, alternative = composition["roles"]
    assert (focus["role"], focus["reference"]) == ("focus", ref("a"))
    assert (no_match["role_family"], no_match["state"]) == ("released_option", "alternative")
    assert (choice["state"], choice["reference"]) == ("model_selected", ref("b"))
    assert (alternative["state"], alternative["reference"]) == ("alternative", ref("c"))


def test_binary_observation_keeps_scope_and_criteria_without_a_literal_witness():
    operation = _operation(10, "relation_interpretation_v1")
    binary = {
        "direction": "negative",
        "positive_probability": 0.4,
        "positive_criterion": "Explicitly presented as a reason.",
        "negative_criterion": "No reason is presented.",
    }
    meaning = {
        "answer_kind": "noul",
        "state": "observed_negative",
        "native_answer": {"noul": 0.4},
        "binary_observation": binary,
    }
    reading = _row(
        operation,
        "question",
        "interpretation.relation_interpretation_v1",
        value={**meaning, "assessed_scope": SCOPE},
    )
    composition = _facets((operation,), (reading,))["question-id"]
    assert composition["assessed_scope"] == SCOPE
    assert composition["binary_observation"] == binary
    assert composition["roles"] == []
    with pytest.raises(SemanticRefusal, match="differs from its source pin"):
        substituted = {**SCOPE, "pin": {**PIN, "source_view_id": 9}}
        _facets(
            (operation,),
            (
                _row(
                    operation,
                    "question",
                    "interpretation.relation_interpretation_v1",
                    value={**meaning, "assessed_scope": substituted},
                ),
            ),
        )


@pytest.mark.parametrize("contract_mode", ("legacy", "typed", "malformed_typed"))
def test_detached_interpretation_requires_original_candidate_and_selected_membership(
    monkeypatch, contract_mode
):
    release, project, runtime = "release-a", "project-a", "runtime-a"
    candidate = {"semantic_type": "linguistic.predicate_frame", "pin": PIN}
    contracts = ()
    if contract_mode != "legacy":
        from .test_record_contracts import release_inputs

        prepared = release_inputs()[2]
        contract = "PM2HanLPFrameContributionV1"
        candidate.update(
            contract=contract,
            kind="proposal",
            operation_key="frame-op",
            value=source_value(
                dict(
                    scheme="hanlp-ud-ptb-propbank-1",
                    sentence=0 if contract_mode == "typed" else "0",
                    predicate_token=0,
                    syntactic_head=0,
                    predicate="verb",
                    focus="verb",
                    voice="active",
                    dependency_arguments=[],
                    srl_frames=[],
                    location_keys=["verb"],
                    unlocated_members=["verb"],
                )
            ),
        )
        contracts = (
            {
                "release_id": release,
                "contribution_payload_contracts": {
                    "linguistic.predicate_frame": dict(
                        contract=contract, schema=prepared.json_schema(contract)
                    )
                },
            },
        )
    candidate["contribution_id"] = contribution_identity(candidate)
    ref = {
        "contribution_id": candidate["contribution_id"],
        "project_id": project,
        "release_id": release,
        "run_id": 1,
        "cut_id": 8,
        "result_revision": 2,
        "selected_task_id": 10,
        "origin_task_id": 9,
        "runtime_fingerprint": runtime,
    }
    reading = {
        "semantic_type": "interpretation.qualification_scope_v1",
        "pin": PIN,
        "value": source_value(
            {
                "candidates": [
                    {
                        "key": "offered",
                        "semantic_type": "linguistic.predicate_frame",
                        "reference": ref,
                    },
                ]
            }
        ),
    }
    reading["contribution_id"] = contribution_identity(reading)
    source_scope = dict(
        run_id=1,
        cut_id=8,
        project_id=project,
        binding={
            "release_id": release,
            "data_revision": 2,
        },
    )
    scopes = {0: source_scope, 1: {**source_scope, "run_id": 2, "cut_id": 9}}
    metadata = dict(origin_project_id=project, runtime_fingerprint=runtime, cut_member=True)
    key = (0, 10, 9, candidate["contribution_id"])
    reading_key = (1, 20, 19, reading["contribution_id"])
    selected = {
        key: {**candidate, **metadata, "origin_run_id": 1},
        reading_key: {**reading, **metadata, "origin_run_id": 2, "method": "extract.pm2_d1"},
    }
    reports = [
        dict(
            project_id=project,
            runtime_fingerprint=runtime,
            unit_type="source_view",
            origin_run_id=run,
            origin_task_id=task,
            body={
                "release_id": release,
                "contributions": [raw],
                "contribution_operations": [
                    {"operation_key": "frame-op", "question": "pm2.hanlp.frames"}
                ]
                if task == 9
                else [],
            },
        )
        for run, task, raw in [(1, 9, candidate), (2, 19, reading)]
    ]
    monkeypatch.setattr(
        review_bundle,
        "_detached_relation",
        lambda _root, _manifest, name: {"reports": reports, "contracts": contracts}.get(name, ()),
    )
    verify = review_bundle._verify_interpretation_closure
    if contract_mode == "malformed_typed":
        with pytest.raises(ValueError, match="parser payload differs from its released contract"):
            verify(None, {}, scopes, selected)
        return
    assert len(verify(None, {}, scopes, selected)) == 1
    with pytest.raises(ValueError, match="selected endpoint inventory missing"):
        verify(None, {}, scopes, {reading_key: selected[reading_key]})
    with pytest.raises(ValueError, match="original retained contents"):
        verify(
            None,
            {},
            scopes,
            {
                **selected,
                reading_key: {
                    **selected[reading_key],
                    "value": source_value({"candidates": []}),
                },
            },
        )


def test_detached_closure_refuses_query_context_without_v11_custody(tmp_path):
    destination = tmp_path / "unverifiable"
    selection = review_bundle.ReviewSelection(
        selections=(ContributionRequest(run_id=1, selected_task_id=2),)
    )
    report = {
        "origin_task_id": 2,
        "method": "retrieve.contextual",
        "configuration": {"query_context": {"recipe": "located-frame-1", "bindings": []}},
        "body": {},
    }
    with pytest.raises(ValueError, match="differs from contextual operation 11"):
        review_bundle.write_review_bundle(selection, destination, [("reports", report)])
    assert not destination.exists()
