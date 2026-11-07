"""Independent native custody/replay checks for source-bound artifact identity."""

from pathlib import Path

import pytest
from rapidfuzz.fuzz import ratio
from sqlalchemy import text


def artifact_helper_sql():
    sql = (
        Path(__file__)
        .parents[2]
        .joinpath("src/corpus_structure/semantic/sql/structural_products.sql")
        .read_text()
    )
    return (
        sql[
            sql.index("CREATE OR REPLACE FUNCTION ops.artifact_alias_fields") : sql.index(
                "CREATE OR REPLACE FUNCTION ops.validate_structural_product_report"
            )
        ]
        + """
    ALTER FUNCTION ops.artifact_source_labels(text,integer,text) OWNER TO corpus_sem_publisher;
    ALTER FUNCTION ops.artifact_label_relation(jsonb,jsonb) OWNER TO corpus_sem_publisher;
    ALTER FUNCTION ops.artifact_explicit_reference(text,integer,integer,text,text)
    OWNER TO corpus_sem_publisher;
    """
    )


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
        conn.exec_driver_sql(artifact_helper_sql(), execution_options={"no_parameters": True})
        for left, right in cases:
            value = conn.scalar(
                text("SELECT ops.artifact_lexical_score(:a,:b)"), dict(a=left, b=right)
            )
            expected = ratio(left, right) / 100 if left and right else 0.0
            assert value == expected


def test_native_artifact_source_replay_plans_its_cohort_aggregation(semantic_db_engine):
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(artifact_helper_sql(), execution_options={"no_parameters": True})
        assert (
            conn.scalar(
                text(
                    """SELECT ops.artifact_source_records(
                    '{"sources":[]}', '{"work_bindings":[]}'
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
    from corpus_structure.semantic.artifact_identity import artifact_source_labels

    designator = "Table 5.9"
    raw = designator + suffix
    pointer = "#/texts/8"
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(artifact_helper_sql(), execution_options={"no_parameters": True})
        native = conn.scalar(
            text("SELECT ops.artifact_source_labels(:raw,:offset,:pointer)"),
            dict(raw=raw, offset=len(designator), pointer=pointer),
        )
    python = artifact_source_labels(raw, len(designator), pointer)
    for kind, declared, state, values in zip(
        ("numbering", "revision"), python, states, labels, strict=True
    ):
        assert native[kind] == declared.model_dump(mode="json", exclude_none=True)
        assert native[kind]["state"] == state
        assert [e["text"] for e in native[kind]["evidence"]] == values
        assert all(raw[e["start"] : e["end"]] == e["text"] for e in native[kind]["evidence"])


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
    from corpus_structure.semantic.artifact_identity import explicit_artifact_reference

    from .test_artifact_identity import record

    start = len(prefix)
    end = start + len("Table 5.8")
    pointer = "#/texts/1"
    artifact = record("reference", role="reference").artifact
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(artifact_helper_sql(), execution_options={"no_parameters": True})
        native = conn.scalar(
            text("SELECT ops.artifact_explicit_reference(:raw,:start,:end,:pointer,'table')"),
            dict(raw=literal, start=start, end=end, pointer=pointer),
        )
    observed = explicit_artifact_reference(literal, start, end, pointer, artifact)
    if target is None:
        assert observed is None and native is None
    else:
        assert observed is not None
        assert native == observed.model_dump(mode="json")
        assert native["target_code"] == target
        assert native["target_numbering"] == "Chapter6"
        assert native["cue"]["text"] == literal.removesuffix(".")


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
        explicit_artifact_reference,
        pair_candidates,
        score_pairs,
    )

    from .test_artifact_identity import nomination, record

    reference = record("i", code="5.9", role="reference")
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
    references = artifact_reference_resolutions(records)
    assert references[0].targets == ("g",)
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    nominations = (nomination("a", "d"),)
    cfg = dict(
        work_bindings=[],
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
        records=records,
        pairs=pairs,
        policy=policy,
        external_nominations=nominations,
        explicit_references=references,
        route_counts=artifact_route_counts(pairs),
    ).model_dump(mode="json", exclude_none=True)
    inputs = {"sources": []}
    with semantic_db_engine.connect() as conn, conn.begin():
        conn.exec_driver_sql(artifact_helper_sql(), execution_options={"no_parameters": True})
        literal = json.dumps(
            [r.model_dump(mode="json", exclude_none=True) for r in records]
        ).replace("'", "''")
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.artifact_source_records(inputs jsonb,config jsonb) "
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
            "inputs jsonb,config jsonb,records jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $source$ SELECT '"
            + external_literal
            + "'::jsonb $source$",
            execution_options={"no_parameters": True},
        )
        statement = text(
            "SELECT ops.validate_artifact_identity("
            "CAST(:i AS jsonb),CAST(:c AS jsonb),CAST(:p AS jsonb))"
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
