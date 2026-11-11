"""Independent native custody/replay checks for source-bound artifact identity."""

import pytest
from rapidfuzz.fuzz import ratio
from sqlalchemy import text


def test_native_indel_replay_matches_actual_rapidfuzz(semantic_db_engine):
    cases = [
        ("Moments", "Moment"),
        ("Table αβ", "Table βα"),
        ("same", "same"),
        ("", "a"),
        (None, "a"),
        ("aba", "baa"),
        ("🧪 \u03b1", "\u03b1 🧪"),
        ("Straße", "STRASSE"),
    ]
    with semantic_db_engine.connect() as conn, conn.begin():
        for left, right in cases:
            value = conn.scalar(
                text("SELECT ops.artifact_lexical_score(:a,:b)"), dict(a=left, b=right)
            )
            expected = ratio(left, right) / 100 if left and right else 0.0
            assert value == expected


def test_native_artifact_source_replay_plans_its_cohort_aggregation(semantic_db_engine):
    with semantic_db_engine.connect() as conn, conn.begin():
        assert (
            conn.scalar(
                text(
                    """SELECT ops.artifact_source_records(
                    '{"sources":[]}', '{"work_bindings":[]}', '{}'
                    )"""
                )
            )
            == []
        )


@pytest.mark.parametrize(
    ("suffix", "states", "labels"),
    [
        (' chapter 5 (alias: "chapter5")', ("unknown", "unknown"), ([], [])),
        (
            "\v(numbering namespace: chapter5) (revision: draft-1)",
            ("observed", "observed"),
            (["chapter5"], ["draft-1"]),
        ),
        (
            " (numbering namespace: Appendix-A) (numbering namespace: Appendix-B)",
            ("unresolved", "unknown"),
            (["Appendix-A", "Appendix-B"], []),
        ),
    ],
)
def test_native_exact_source_numbering_and_revision_cues(
    semantic_db_engine, suffix, states, labels
):
    from .test_named_link_coverage_native import native_navigation_call, primary_fixture

    literal = "Table 5.9" + suffix
    layers, index, physical = primary_fixture(literal, label="caption")
    record = next(
        row for row in index.select("artifact_mention") if row.text("subject") == "Table 5.9"
    )
    with semantic_db_engine.connect() as conn, conn.begin():
        native = native_navigation_call(
            conn,
            "artifact_source_labels",
            layers,
            record.reference.values(),
            physical,
            field_start=0,
        )
    for kind, state, values in zip(("numbering", "revision"), states, labels, strict=True):
        assert native[kind]["state"] == state
        assert [e["text"] for e in native[kind]["evidence"]] == values
        assert all(literal[e["start"] : e["end"]] == e["text"] for e in native[kind]["evidence"])


@pytest.mark.parametrize(
    ("literal", "prefix", "target"),
    [
        ("See Table 5.8 (hereafter Table 6.1 in numbering namespace Chapter6).", "See ", "6.1"),
        (
            "Consult Table 5.8 (also cited as Table 6.1 in numbering namespace Chapter6).",
            "Consult ",
            "6.1",
        ),
        (
            "Do not see Table 5.8 (hereafter Table 6.1 in numbering namespace Chapter6).",
            "Do not see ",
            None,
        ),
        ("See Table 5.8 (hereafter Figure 6.1 in numbering namespace Chapter6).", "See ", None),
    ],
)
def test_native_explicit_reference_cue_matches_source_replay(
    semantic_db_engine, literal, prefix, target
):
    from .test_named_link_coverage_native import native_navigation_call, primary_fixture

    layers, index, physical = primary_fixture(literal)
    references = index.select("artifact_explicit_reference")
    if target is None:
        assert references == ()
        return
    (record,) = references
    with semantic_db_engine.connect() as conn, conn.begin():
        native = native_navigation_call(
            conn,
            "artifact_explicit_reference",
            layers,
            record.reference.values(),
            physical,
            field_start=0,
        )
    assert native["target_code"] == target and native["target_numbering"] == "Chapter6"
    assert native["cue"]["text"] == literal.removesuffix(".")
    assert native["primary_node"] == record.reference.values()


@pytest.mark.parametrize("mutation", (None, "label_text", "target_text", "foreign_source"))
def test_native_artifact_fields_require_literal_primary_operands(semantic_db_engine, mutation):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.identity import canonical_bytes

    from .test_named_link_coverage_native import native_navigation_call, primary_fixture

    literal = "See Table 5.9 (hereafter Table 6.1 in numbering namespace Chapter6)."
    layers, index, physical = primary_fixture(literal)
    (record,) = index.select("artifact_explicit_reference")
    ref = record.reference.values()
    body = layers[canonical_bytes(ref["layer"]).decode()]
    node = next(a for a in body["annotations"] if a["local_id"] == ref["local_id"])
    if mutation == "label_text":
        node["navigation"]["numbering_namespace"] = "Other"
    elif mutation == "target_text":
        node["navigation"]["designator"] = "9.9"
    elif mutation == "foreign_source":
        physical["id"] += 1
    with semantic_db_engine.connect() as conn, conn.begin():
        if mutation is None:
            native = native_navigation_call(
                conn, "artifact_explicit_reference", layers, ref, physical, field_start=0
            )
            assert native["target_code"] == "6.1"
        else:
            with pytest.raises(DBAPIError) as refused:
                native_navigation_call(
                    conn, "artifact_explicit_reference", layers, ref, physical, field_start=0
                )
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"


@pytest.mark.parametrize(
    "suffix, state, aliases",
    (
        (' (alias: "T5") (also called "Control")', "observed", ["T5", "Control"]),
        (" (aliases: none)", "known_empty", []),
        (" no explicit alias", "unknown", []),
    ),
)
def test_native_artifact_aliases_project_retained_literal_occurrences(
    semantic_db_engine, suffix, state, aliases
):
    from .test_named_link_coverage_native import native_navigation_call, primary_fixture

    literal = "Table 5.9" + suffix
    layers, index, physical = primary_fixture(literal, label="caption")
    (record,) = index.select("artifact_mention")
    with semantic_db_engine.connect() as conn, conn.begin():
        native = native_navigation_call(
            conn,
            "artifact_alias_fields",
            layers,
            record.reference.values(),
            physical,
            field_start=0,
        )
    assert native["alias_state"] == state and native["aliases"] == aliases
    assert [span["text"] for span in native["alias_occurrences"]] == aliases
    assert all(
        literal[span["start"] : span["end"]] == span["text"] for span in native["alias_occurrences"]
    )
    if state == "known_empty":
        assert native["alias_absence"]["text"] == "aliases: none"


def test_native_frozen_likelihood_and_routes_after_source_boundary(semantic_db_engine):
    """Source is controlled here; actual source replay is a separate provider journey."""
    import json
    from copy import deepcopy

    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.artifact_identity import (
        ArtifactIdentityProduct,
        ArtifactScoringPolicy,
        artifact_reference_resolutions,
        artifact_route_counts,
        pair_candidates,
        score_pairs,
    )

    from .test_artifact_identity import nomination, record

    reference = record("i", code="5.9", role="reference")
    from corpus_structure.semantic.constructions.navigation import explicit_artifact_reference

    witness = explicit_artifact_reference(
        "See Table 5.9 (hereafter Table 6.1 in numbering namespace chapter5).",
        4,
        13,
        "#/texts/i",
        reference.artifact,
    )
    assert witness is not None
    records = (
        record("a", title="Moments"),
        record("b", title="\t\u00a0Moments\u00a0\n"),
        record("c", title="Moment", code="5.2"),
        record("d", work="foreign", code="5.1"),
        record("e", code="\u0661.\u0662"),
        record("f", code="\u0661.\u0662"),
        record("g", code="6.1", title="abc"),
        record("h", code="6.2", title="abd"),
        reference.model_copy(update={"explicit_reference": witness}),
    )
    from corpus_structure.semantic.characterization import annotation_reference
    from corpus_structure.semantic.product_reference import ProductReference

    def primary_node(identity):
        return annotation_reference(ProductReference(901, "annotation_layer", "e" * 64), identity)

    records = tuple(
        row.model_copy(
            update={
                "primary_node": primary_node(row.contribution_id),
                "artifact": row.artifact.model_copy(
                    update={"primary_node": primary_node(row.contribution_id)}
                ),
                **(
                    {
                        "explicit_reference": row.explicit_reference.model_copy(
                            update={"primary_node": primary_node("explicit")}
                        )
                    }
                    if row.explicit_reference is not None
                    else {}
                ),
            }
        )
        for row in records
    )
    references = artifact_reference_resolutions(records)
    assert references[0].targets == ("g",)
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    nominations = (
        nomination("a", "d").model_copy(update={"primary_node": primary_node("nomination")}),
    )
    cfg = dict(
        work_bindings=[],
        _operation_version="5",
        title_threshold=ratio("abc", "abd"),
        external_nomination_refs=[n.relationship.model_dump(mode="json") for n in nominations],
        exclusions=[],
        policy=policy.model_dump(mode="json"),
    )
    pairs = score_pairs(
        records,
        pair_candidates(
            records,
            external_nominations=nominations,
            explicit_references=references,
            title_threshold=ratio("abc", "abd"),
        ),
        policy,
    )
    product = ArtifactIdentityProduct(
        protocol="artifact-identity-5",
        declared_relationships=(),
        records=records,
        pairs=pairs,
        policy=policy,
        external_nominations=nominations,
        explicit_references=references,
        route_counts=artifact_route_counts(pairs),
    ).model_dump(mode="json", exclude_none=True)
    inputs = {"sources": []}
    with semantic_db_engine.connect() as conn, conn.begin():
        literal = json.dumps(
            [r.model_dump(mode="json", exclude_none=True) for r in records]
        ).replace("'", "''")
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.artifact_source_records("
            "inputs jsonb,config jsonb,primary_sources jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $source$ SELECT '"
            + literal
            + "'::jsonb $source$",
            execution_options={"no_parameters": True},
        )
        external_literal = json.dumps([n.model_dump(mode="json") for n in nominations]).replace(
            "'", "''"
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.artifact_external_nominations("
            "t ops.task,inputs jsonb,config jsonb,records jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $source$ SELECT '"
            + external_literal
            + "'::jsonb $source$",
            execution_options={"no_parameters": True},
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.artifact_declared_relationships("
            "inputs jsonb,records jsonb,primary_sources jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ SELECT '[]'::jsonb $$"
        )
        statement = text(
            "SELECT ops.validate_artifact_identity("
            "NULL::ops.task,CAST(:i AS jsonb),CAST(:c AS jsonb),CAST(:p AS jsonb))"
        )

        def check(value, configuration=cfg):
            conn.execute(
                statement,
                dict(i=json.dumps(inputs), c=json.dumps(configuration), p=json.dumps(value)),
            )

        check(product)
        # Ordinary registry ABI stores float config fields as canonical strings.
        # This helper still tests nonempty likelihood/routes independently of source custody.
        from corpus_structure.orchestrate.registry import canonical_numbers

        canonical_cfg = canonical_numbers(cfg)
        check(product, canonical_cfg)
        for invalid in (
            None,
            True,
            [],
            {},
            "NaN",
            "Infinity",
            "-Infinity",
            "70.0",
            "7e1",
            " 70",
            "1" + "0" * 400,
            -0.1,
            100.1,
        ):
            bad_cfg = deepcopy(canonical_cfg)
            bad_cfg["title_threshold"] = invalid
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(product, bad_cfg)
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"
        # A valid but different threshold must not authenticate this frozen pair/routes output.
        for threshold in ("0", "100"):
            bad_cfg = deepcopy(canonical_cfg)
            bad_cfg["title_threshold"] = threshold
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(product, bad_cfg)
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"
        for invalid in (None, True, [], "policy", {}, {**canonical_cfg["policy"], "extra": "0.1"}):
            bad_cfg = deepcopy(canonical_cfg)
            bad_cfg["policy"] = invalid
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(product, bad_cfg)
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"
        for key in canonical_cfg["policy"]:
            for invalid in (
                None,
                True,
                [],
                {},
                "NaN",
                "Infinity",
                "-Infinity",
                "0",
                "1",
                "0.10",
                "1e-1",
                "1" + "0" * 400,
            ):
                bad_cfg = deepcopy(canonical_cfg)
                bad_cfg["policy"][key] = invalid
                with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                    check(product, bad_cfg)
                assert getattr(refused.value.orig, "sqlstate", None) == "23514"
        for key in ("prior", "code_m", "code_u", "title_m", "title_u"):
            forged = deepcopy(product)
            forged["policy"][key] = 0.2
            with pytest.raises(DBAPIError) as refused, conn.begin_nested():
                check(forged, canonical_cfg)
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"
        # Existing pair-only anchor/exclusion semantics are independently enforced natively.
        guarded_cfg = {**cfg, "known_anchor_ids": ["b", "a"], "exclusions": [["a", "c"]]}
        guarded_pairs = score_pairs(
            records,
            pair_candidates(
                records,
                external_nominations=nominations,
                explicit_references=references,
                title_threshold=ratio("abc", "abd"),
                exclusions=(("a", "c"),),
                known_anchor_ids=("a", "b"),
            ),
            policy,
        )
        guarded = ArtifactIdentityProduct(
            protocol="artifact-identity-5",
            declared_relationships=(),
            records=records,
            pairs=guarded_pairs,
            policy=policy,
            known_anchor_ids=("a", "b"),
            external_nominations=nominations,
            explicit_references=references,
            route_counts=artifact_route_counts(guarded_pairs),
        ).model_dump(mode="json", exclude_none=True)
        check(guarded, guarded_cfg)
        for invalid in (["missing"], ["a", "a"]):
            bad_cfg = {**cfg, "known_anchor_ids": invalid}
            with pytest.raises(DBAPIError), conn.begin_nested():
                check(product, bad_cfg)
        bad = deepcopy(guarded)
        bad["known_anchor_ids"] = []
        with pytest.raises(DBAPIError), conn.begin_nested():
            check(bad, guarded_cfg)
        bad = deepcopy(guarded)
        ab = next(p for p in bad["pairs"] if (p["left"], p["right"]) == ("a", "b"))
        ab["scope_state"] = "compatible"
        with pytest.raises(DBAPIError), conn.begin_nested():
            check(bad, guarded_cfg)
        mutations = []
        bad = deepcopy(product)
        bad["identity_grain"] = "immutable_version"
        mutations.append(bad)
        for key, value in [
            ("candidate_routes", ["external_pairs"]),
            ("lexical_score", 0.2),
            ("model_probability", 0.1),
            ("model_id", "forged"),
        ]:
            bad = deepcopy(product)
            bad["pairs"][0][key] = value
            mutations.append(bad)
        bad = deepcopy(product)
        bad["pairs"].pop()
        mutations.append(bad)
        bad = deepcopy(product)
        bad["pairs"][0]["model_evidence"][0]["value"] = 0
        mutations.append(bad)
        for invalid in (0, 1):
            bad = deepcopy(product)
            configuration = deepcopy(cfg)
            bad["policy"]["prior"] = invalid
            configuration["policy"]["prior"] = invalid
            with pytest.raises(DBAPIError), conn.begin_nested():
                check(bad, configuration)
        for bad in mutations:
            with pytest.raises(DBAPIError), conn.begin_nested():
                check(bad)
