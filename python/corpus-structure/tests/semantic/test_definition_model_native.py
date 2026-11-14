"""Independent controls for directed model definition attachment replay."""

import json
import struct
import sys
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text


def test_located_request_binds_ordered_schema_and_exact_inference(commit_db_engine):
    policy = {
        "request_version": "located-model-request-1",
        "definition": {"bare": ['{"entities":[', {"field": "term_entity"}, "]}"]},
        "inference": {"operation": "batch_extract", "include_spans": True},
    }
    profile = {
        "snapshot": "/acquired",
        "checkpoint": "checkpoint",
        "timeout_seconds": 120.0,
        "artifact_hashes": [["z", "last"], ["a", "first"]],
    }
    config = {
        "profile": profile,
        "description_arm": "bare",
        "term_entity": '\u03b1 "term"',
        "threshold": 0.5,
        "evaluation_overlap": "nested",
    }
    expected = [
        "located-model-request-1",
        "r",
        "native-local-v1",
        '{"entities":["\u03b1 \\"term\\""]}',
        {
            "checkpoint": "checkpoint",
            "timeout_seconds": "120",
            "artifact_hashes": [["a", "first"], ["z", "last"]],
        },
        [["structure.definition_components/10", "context", "digest", " \u03b1\t\u03b2"]],
        "0.5",
        "nested",
        True,
        {"operation": "batch_extract", "include_spans": True},
    ]
    expected_key = sha256(
        json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    with commit_db_engine.connect() as conn, conn.begin():
        query = text(
            "SELECT ops.located_model_request('r','structure.definition_components/10',"
            "CAST(:policy AS jsonb),CAST(:config AS jsonb),'context','digest',:body)"
        )
        params = {
            "policy": json.dumps(policy),
            "config": json.dumps(config),
            "body": " \u03b1\t\u03b2",
        }
        assert conn.scalar(query, params) == expected_key
        assert (
            conn.scalar(
                query,
                {
                    **params,
                    "config": json.dumps(
                        {
                            **config,
                            "evaluation_overlap": "allow",
                        }
                    ),
                },
            )
            != expected_key
        )


def _literal_hash(value):
    # Independent native reference bytes, deliberately not the producer's hash helper.
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _literal_current_observation():
    profile = {
        "snapshot": "/acquired",
        "checkpoint": "checkpoint",
        "timeout_seconds": 120.0,
        "artifact_hashes": [["z", "last"], ["a", "first"]],
        "device": "cuda",
        "dtype": "float32",
        "execution_profile": "exact-numerical-identity",
    }
    policy = {
        "request_version": "located-model-request-2",
        "definition": {"bare": ['{"entities":[', {"field": "term_entity"}, "]}"]},
        "inference": {"operation": "batch_extract", "include_spans": True},
    }
    config = dict(profile=profile, description_arm="bare", term_entity="term", threshold=0.5)
    header = {
        "release": "r",
        "version": "native-local-v1",
        "declaration": '{"entities":["term"]}',
        "profile": {
            "checkpoint": "checkpoint",
            "timeout_seconds": "120",
            "artifact_hashes": [["a", "first"], ["z", "last"]],
            "device": "cuda",
            "dtype": "float32",
            "execution_profile": "exact-numerical-identity",
        },
        "threshold": "0.5",
        "overlap": "flat",
        "evaluation": False,
        "inference": {"operation": "batch_extract", "include_spans": True},
    }
    member = _literal_hash(
        [
            "located-model-member-2",
            "structure.definition_components/10",
            "context",
            "digest",
            " \u03b1\t\u03b2",
        ]
    )
    key = _literal_hash(["located-model-request-2", header, [member]])
    receipt = dict(version=2, header=header, members=[member], digest=key)
    report = dict(
        request_digest=key,
        computation=key,
        raw_json='{"entities":{}}',
        effective_profile_json='{"device":"cuda","dtype":"float32"}',
        batch_receipt_json=json.dumps(receipt),
        member_ordinal=0,
    )
    report["observation_digest"] = _literal_hash(
        [
            "located-model-observation-2",
            key,
            0,
            member,
            report["raw_json"],
            report["effective_profile_json"],
        ]
    )
    return policy, config, receipt, report


def test_located_v2_native_and_python_requests_match_independent_header_member_bytes(
    commit_db_engine,
):
    from corpus_structure.methods.model_observation import batch_receipt, report_observation_digest

    policy, config, receipt, report = _literal_current_observation()
    pack = SimpleNamespace(
        release="r", version="native-local-v1", declaration_json=receipt["header"]["declaration"]
    )
    member = SimpleNamespace(
        operation="structure.definition_components/10",
        context_id="context",
        context_digest="digest",
        text=" \u03b1\t\u03b2",
    )
    assert (
        batch_receipt(pack, config["profile"], (member,), 0.5, "flat", False, policy["inference"])
        == receipt
    )
    assert report_observation_digest(report) == report["observation_digest"]
    query = text(
        "SELECT ops.located_model_request('r','structure.definition_components/10',"
        "CAST(:policy AS jsonb),CAST(:config AS jsonb),'context','digest',:body)"
    )
    with commit_db_engine.connect() as conn, conn.begin():
        params = dict(policy=json.dumps(policy), config=json.dumps(config), body=" \u03b1\t\u03b2")
        assert conn.scalar(query, params) == receipt["digest"]
        # Every inference and normalized-profile field participates, including native policy.
        changed = deepcopy(config)
        changed["profile"]["execution_profile"] = "different-numerical-identity"
        assert conn.scalar(query, {**params, "config": json.dumps(changed)}) != receipt["digest"]
        changed_policy = deepcopy(policy)
        changed_policy["inference"]["include_spans"] = False
        assert (
            conn.scalar(query, {**params, "policy": json.dumps(changed_policy)})
            != receipt["digest"]
        )
        assert (
            conn.scalar(
                query,
                {**params, "policy": json.dumps({**policy, "request_version": "unsupported"})},
            )
            is None
        )


def test_located_native_observation_checks_legacy_and_full_v2_commitments(commit_db_engine):
    _, _, receipt, report = _literal_current_observation()
    query = text("SELECT ops.located_model_observation_matches(CAST(:report AS jsonb),:request)")
    with commit_db_engine.connect() as conn, conn.begin():

        def matches(candidate, key=report["request_digest"]):
            return conn.scalar(query, dict(report=json.dumps(candidate), request=key))

        assert matches(report) is True
        # A generic batch receipt binds its actual member ordinal, not always zero.
        members = ["b" * 64, receipt["members"][0]]
        key = _literal_hash(["located-model-request-2", receipt["header"], members])
        second = {
            **report,
            "request_digest": key,
            "computation": key,
            "member_ordinal": 1,
            "batch_receipt_json": json.dumps(
                dict(version=2, header=receipt["header"], members=members, digest=key)
            ),
            "observation_digest": _literal_hash(
                [
                    "located-model-observation-2",
                    key,
                    1,
                    members[1],
                    report["raw_json"],
                    report["effective_profile_json"],
                ]
            ),
        }
        assert matches(second, key) is True
        assert matches({**second, "member_ordinal": 0}, key) is False
        legacy = {
            key: value
            for key, value in report.items()
            if key not in {"batch_receipt_json", "member_ordinal"}
        }
        legacy["observation_digest"] = _literal_hash(
            [legacy["request_digest"], legacy["raw_json"], legacy["effective_profile_json"]]
        )
        assert matches(legacy) is True
        # Legacy history remains valid, but cannot acquire an invented batch ordinal.
        assert matches({**legacy, "member_ordinal": 0}) is False
        assert (
            matches({**report, "computation": "physical-cohort-instead-of-client-request"}) is False
        )
        assert matches({**report, "observation_digest": legacy["observation_digest"]}) is False
        assert matches({**report, "raw_json": "{}"}) is False
        assert matches({**report, "effective_profile_json": "{}"}) is False
        assert matches({**report, "raw_json": {}}) is False
        for ordinal in (-1, 1, True, 0.0, "0", None, 2**63):
            assert matches({**report, "member_ordinal": ordinal}) is False
        for raw_receipt in ("not-json", "[]", "null", "{}"):
            assert matches({**report, "batch_receipt_json": raw_receipt}) is False
        changed_receipts: list[dict[str, Any]] = []
        changed_receipts.append({**receipt, "extra": "not-declared"})
        changed_receipts.append({key: value for key, value in receipt.items() if key != "version"})
        for version in (1, True, 2.0, "2"):
            changed_receipts.append({**receipt, "version": version})
        changed_receipts.extend(
            [
                {**receipt, "header": {**receipt["header"], "threshold": "0.7"}},
                {**receipt, "members": ["f" * 64]},
                {**receipt, "digest": "f" * 64},
            ]
        )
        for changed in changed_receipts:
            assert matches({**report, "batch_receipt_json": json.dumps(changed)}) is False
        # Recompute all hashes for malformed shapes: their own hashes cannot make them valid.
        malformed = [
            ({**receipt["header"], "extra": True}, receipt["members"]),
            (
                {key: value for key, value in receipt["header"].items() if key != "profile"},
                receipt["members"],
            ),
            ({**receipt["header"], "evaluation": "false"}, receipt["members"]),
            (receipt["header"], []),
            (receipt["header"], receipt["members"] * 2),
            (receipt["header"], ["not-a-member-hash"]),
            (receipt["header"], ["A" * 64]),
        ]
        for header, members in malformed:
            key = _literal_hash(["located-model-request-2", header, members])
            altered = {
                **report,
                "request_digest": key,
                "computation": key,
                "batch_receipt_json": json.dumps(
                    dict(version=2, header=header, members=members, digest=key)
                ),
                "observation_digest": _literal_hash(
                    [
                        "located-model-observation-2",
                        key,
                        0,
                        members[0] if members else "",
                        report["raw_json"],
                        report["effective_profile_json"],
                    ]
                ),
            }
            assert matches(altered, key) is False


def test_current_definition_window_refuses_legacy_or_missing_batch_receipt(commit_db_engine):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.releases import persist_release
    from semantic.native_record_fixtures import prepare_record_source

    preparation = prepare_record_source()
    passage = dict(passage_id="p", start=0, end=4, text="term", scope="literal-source")
    config = dict(
        use_model=True,
        target_ids=["p"],
        profile=dict(
            snapshot="/acquired",
            checkpoint="checkpoint",
            timeout_seconds=120.0,
            max_input_bytes=65536,
            artifact_hashes=[["a", "first"]],
            device="cuda",
            dtype="float32",
        ),
        description_arm="bare",
        term_entity="term",
        content_entity="content",
        attachment_relation="attachment",
        threshold=0.5,
    )
    digest = _literal_hash(passage)
    with commit_db_engine.connect() as conn, conn.begin():
        persist_release(conn, *preparation.preparation_inputs, preparation.prepared)
        release = preparation.prepared.release_id
        policy = conn.scalar(
            text("SELECT ops.model_observation_policy(:release)"), dict(release=release)
        )
        assert policy["request_version"] == "located-model-request-2"
        declaration = "".join(
            json.dumps(config[part["field"]], ensure_ascii=False)
            if isinstance(part, dict)
            else part
            for part in policy["definition"]["bare"]
        )
        member = _literal_hash(
            [
                "located-model-member-2",
                "structure.definition_components/10",
                "definition-target:" + digest,
                digest,
                "term",
            ]
        )
        header = dict(
            release=release,
            version="native-local-v1",
            declaration=declaration,
            profile={key: value for key, value in config["profile"].items() if key != "snapshot"},
            threshold="0.5",
            overlap="flat",
            evaluation=False,
            inference=policy["inference"],
        )
        header["profile"]["timeout_seconds"] = "120"
        request = _literal_hash(["located-model-request-2", header, [member]])
        report = dict(
            passage_id="p",
            window_start=0,
            window_end=4,
            context_digest=digest,
            request_digest=request,
            computation=request,
            raw_json="{}",
            effective_profile_json="{}",
            batch_receipt_json=json.dumps(
                dict(version=2, header=header, members=[member], digest=request)
            ),
            member_ordinal=0,
            observation_digest=_literal_hash(
                ["located-model-observation-2", request, 0, member, "{}", "{}"]
            ),
        )
        detail = dict(
            schema_declaration=declaration,
            raw_reports=[report],
            window_outcomes=[
                dict(passage_id="p", start=0, end=4, request_digest=request, status="returned")
            ],
        )
        query = text(
            "SELECT ops.validate_definition_window_requests("
            ":release,CAST(:detail AS jsonb),CAST(:config AS jsonb),CAST(:passages AS jsonb))"
        )
        params = dict(
            release=release, config=json.dumps(config), passages=json.dumps({"p": passage})
        )
        conn.execute(query, {**params, "detail": json.dumps(detail)})
        legacy = {
            key: value
            for key, value in report.items()
            if key not in {"batch_receipt_json", "member_ordinal"}
        }
        legacy["observation_digest"] = _literal_hash([request, "{}", "{}"])
        for candidate in (
            legacy,
            {**report, "batch_receipt_json": None},
            {**report, "member_ordinal": 1},
        ):
            with pytest.raises(DBAPIError, match="selected request"), conn.begin_nested():
                conn.execute(
                    query, {**params, "detail": json.dumps({**detail, "raw_reports": [candidate]})}
                )


def test_native_model_report_preserves_exact_binary_profile_and_scores(commit_db_engine):
    values = (
        120.0,
        0.1,
        -0.0,
        float.fromhex("0x0.0000000000001p-1022"),
        float.fromhex("0x0.fffffffffffffp-1022"),
        sys.float_info.min,
        sys.float_info.max,
    )
    with commit_db_engine.connect() as conn, conn.begin():
        for value in values:
            actual = conn.scalar(
                text("SELECT float8send(data.record_source_float(CAST(:value AS jsonb)))"),
                {"value": json.dumps({"kind": "float", "hexadecimal": value.hex()})},
            )
            assert actual == struct.pack("!d", value)


def test_native_model_components_need_directed_provider_attachment(commit_db_engine):
    passage = {
        "passage_id": "p",
        "text": "term means content",
        "start": 0,
        "end": 18,
        "scope": "s",
    }
    term = {"start": 0, "end": 4, "text": "term"}
    content = {"start": 11, "end": 18, "text": "content"}
    raw = {
        "entities": {
            "term": [
                {**term, "interpretation": "definition"},
                {**term, "interpretation": {"label": "explanation"}},
                {**term, "interpretation": "unsupported"},
            ],
            "content": [content],
        },
        "relation_extraction": {"attachment": [{"head": term, "tail": content}] * 2},
    }
    config = {
        "description_arm": "bare",
        "use_model": True,
        "profile": {"timeout_seconds": "120"},
        "target_ids": ["p"],
        "term_entity": "term",
        "content_entity": "content",
        "attachment_relation": "attachment",
    }
    entry = {
        "passage_id": "p",
        "window_start": 0,
        "window_end": 18,
        "computation": "provider",
        "profile": "profile",
        "pack": "pack",
        "context_id": "definition-target:context",
        "context_digest": "context",
        "preparation": {"synthetic_suffix": ".", "consumed_text": "term means content."},
        "raw_json": json.dumps(raw),
    }
    detail = {
        "version": "located-definition-extraction-5",
        "description_arm": "bare",
        "overlap_policy": "flat",
        "profile": {"timeout_seconds": 120.0},
        "profile_fingerprint": "profile",
        "pack_fingerprint": "pack",
        "raw_reports": [entry],
    }
    with commit_db_engine.connect() as conn, conn.begin():

        def replay():
            return conn.execute(
                text("""
                    WITH inputs AS (
                        SELECT CAST(:detail AS jsonb) AS d, CAST(:config AS jsonb) AS c,
                               CAST(:passages AS jsonb) AS p
                    )
                    SELECT roles, ops.definition_model_components(d,c,p,roles)
                    FROM inputs CROSS JOIN LATERAL (
                        SELECT ops.definition_role_candidates(d,c,p) AS roles
                    ) exact
                """),
                {
                    "detail": json.dumps(detail),
                    "config": json.dumps(config),
                    "passages": json.dumps({"p": passage}),
                },
            ).one()

        roles, (component,) = replay()
        assert len(roles) == 4
        assert component["term"] == {**term, "passage_id": "p"}
        assert component["content"] == {**content, "passage_id": "p"}
        assert component["interpretation"] == "explanation"
        assert component["basis"] == "model_reading"
        raw["relation_extraction"]["attachment"] = [{"head": content, "tail": term}]
        entry["raw_json"] = json.dumps(raw)
        assert replay() == (roles, [])


def test_genuine_definition_spans_require_named_cue_custody(commit_db_engine):
    import pytest
    from sqlalchemy.exc import DBAPIError

    term = dict(passage_id="p", start=0, end=4, text="term")
    content = dict(passage_id="p", start=11, end=18, text="content")
    named = dict(term=term, content=content, basis="matched_cue", interpretation="definition")
    weak = {**named, "basis": "unqualified", "interpretation": "unresolved"}
    with commit_db_engine.connect() as conn, conn.begin():
        check = text("""
            SELECT ops.validate_definition_basis(
              CAST(:component AS jsonb),
              jsonb_build_object('passage_id','p','text','term means content','start',0,'end',18),
              '{}', jsonb_build_object('use_named_candidates',true), '{}')
            """)
        with (
            pytest.raises(DBAPIError, match="exact retained primary witness"),
            conn.begin_nested(),
        ):
            conn.execute(check, {"component": json.dumps(named)})
        conn.execute(check, {"component": json.dumps(weak)})
        with pytest.raises(DBAPIError, match="unsupported interpretation"), conn.begin_nested():
            conn.execute(check, {"component": json.dumps({**weak, "interpretation": "definition"})})


def test_native_definition_scope_uses_retained_act_and_content_ownership(commit_db_engine):
    from dataclasses import replace

    import pytest
    from annotation_support import ControlledPipeline, item
    from methods.primary_reading_fixture import primary_product

    from corpus_structure.ingest import annotations
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.annotation_rules import AnnotationRuleMatch, LocatedRole
    from corpus_structure.methods.definition_applicability import definition_scopes
    from corpus_structure.methods.predicate_frames import predicate_frames
    from corpus_structure.semantic.identity import canonical_bytes

    with commit_db_engine.connect() as conn:

        def supported(words, heads, deps, pos, lemmas, act, *, bindings=None, indices=None):
            # Retain the independent token/head/POS/lemma fixture through the real
            # upstream native and source-reading owners; consumers never re-recognize it.
            controlled = ControlledPipeline()
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(annotations, "pipeline", lambda _: controlled)
                (product,) = annotations.annotate((item(controlled, words, start=0),))
            assert [words[t.start : t.end] for t in product.tokens] == words.split()
            product = replace(
                product,
                tokens=tuple(
                    replace(token, head=head, dependency=dep, pos=tag, lemma=lemma)
                    for token, head, dep, tag, lemma in zip(
                        product.tokens, heads, deps, pos, lemmas, strict=True
                    )
                ),
            )
            product = primary_product(
                words, product, AnnotationProfile(), native_profile=controlled.selection().native
            )
            roles = [
                LocatedRole(
                    "defining_cue",
                    "act",
                    act,
                    "exact",
                    (act,),
                    ((product.tokens[act].start, product.tokens[act].end),),
                    "complete",
                )
            ]
            indices = indices or {}
            for role, binding in (bindings or {}).items():
                head = indices[binding["node"]]
                nodes = {head}
                if binding.get("expansion") == "subtree":
                    for _ in product.tokens:
                        nodes.update(
                            i for i, token in enumerate(product.tokens) if token.head in nodes
                        )
                ordered = tuple(sorted(nodes))
                roles.append(
                    LocatedRole(
                        role,
                        binding["node"],
                        head,
                        binding.get("expansion", "exact"),
                        ordered,
                        ((product.tokens[ordered[0]].start, product.tokens[ordered[-1]].end),),
                        "complete",
                    )
                )
            match = AnnotationRuleMatch(
                "defining",
                "independent-scope",
                "dependency",
                (act,),
                ((0, len(words)),),
                (),
                (),
                product.dependency_digest,
                tuple(roles),
            )
            result = predicate_frames(words, (product,))
            assert not result.issues
            scope = definition_scopes((match,), result, content_role="defining_content")[match]
            wire = {
                canonical_bytes(pin.values()).decode(): layer.payload
                for pin, layer in product.primary_layers.items()
            }
            # The native guard projects precisely the retained scope endpoints and
            # choices, rather than duplicating the removed linguistic classifier.
            for reference in scope.primary_scope:
                assert (
                    conn.scalar(
                        text("""
                    WITH input AS (SELECT CAST(:layers AS jsonb) layers,CAST(:ref AS jsonb) ref)
                    SELECT ops.primary_characterization_choices(
                        layers,ref,ops.primary_characterization_node(layers,ref),'[]')
                    FROM input
                """),
                        dict(layers=json.dumps(wire), ref=json.dumps(reference.values())),
                    )
                    is True
                )
            return scope.disposition == "supported"

        assert supported(
            "X is defined by : F .",
            (2, 2, 2, 2, 2, 2, 2),
            ("nsubjpass", "auxpass", "ROOT", "agent", "punct", "dobj", "punct"),
            ("NOUN", "AUX", "VERB", "ADP", "PUNCT", "NOUN", "PUNCT"),
            ("x", "be", "define", "by", ":", "f", "."),
            2,
        )
        assert not supported(
            "If heads occur , X is defined by : F .",
            (2, 2, 6, 6, 6, 6, 6, 6, 6, 6, 6),
            (
                "mark",
                "nsubj",
                "advcl",
                "punct",
                "nsubjpass",
                "auxpass",
                "ROOT",
                "agent",
                "punct",
                "dobj",
                "punct",
            ),
            (
                "SCONJ",
                "NOUN",
                "VERB",
                "PUNCT",
                "NOUN",
                "AUX",
                "VERB",
                "ADP",
                "PUNCT",
                "NOUN",
                "PUNCT",
            ),
            ("if", "head", "occur", ",", "x", "be", "define", "by", ":", "f", "."),
            6,
        )
        assert not supported(
            "Huygens claimed that we define X as a value .",
            (1, 1, 4, 4, 1, 4, 4, 8, 6, 1),
            ("nsubj", "ROOT", "mark", "nsubj", "ccomp", "dobj", "prep", "det", "pobj", "punct"),
            ("PROPN", "VERB", "SCONJ", "PRON", "VERB", "NOUN", "ADP", "DET", "NOUN", "PUNCT"),
            ("Huygens", "claim", "that", "we", "define", "x", "as", "a", "value", "."),
            4,
        )
        assert supported(
            "We define X as a value that does not change .",
            (1, 1, 1, 1, 5, 3, 9, 9, 9, 5, 1),
            (
                "nsubj",
                "ROOT",
                "dobj",
                "prep",
                "det",
                "pobj",
                "nsubj",
                "aux",
                "neg",
                "relcl",
                "punct",
            ),
            ("PRON", "VERB", "NOUN", "ADP", "DET", "NOUN", "PRON", "AUX", "PART", "VERB", "PUNCT"),
            ("we", "define", "x", "as", "a", "value", "that", "do", "not", "change", "."),
            1,
            bindings={"defining_content": {"node": "content", "expansion": "subtree"}},
            indices={"content": 5},
        )
        assert not supported(
            "We define X to be 1 if heads occur .",
            (1, 1, 1, 4, 1, 4, 8, 8, 4, 1),
            ("nsubj", "ROOT", "dobj", "aux", "xcomp", "attr", "mark", "nsubj", "advcl", "punct"),
            ("PRON", "VERB", "NOUN", "PART", "AUX", "NUM", "SCONJ", "NOUN", "VERB", "PUNCT"),
            ("we", "define", "x", "to", "be", "1", "if", "head", "occur", "."),
            1,
            bindings={
                "defining_content": {"node": "content", "expansion": "exact"},
                "defining_content_predicate": {"node": "predicate", "expansion": "exact"},
            },
            indices={"content": 5, "predicate": 4},
        )
        assert not supported(
            "If F is ready and X is valid , then Y is defined by : Z .",
            (2, 2, 6, 2, 6, 6, 12, 6, 12, 12, 12, 12, 12, 12, 12, 12, 12),
            (
                "mark",
                "nsubj",
                "advcl",
                "acomp",
                "cc",
                "nsubj",
                "ccomp",
                "acomp",
                "punct",
                "advmod",
                "nsubjpass",
                "auxpass",
                "ROOT",
                "agent",
                "punct",
                "dobj",
                "punct",
            ),
            (
                "SCONJ",
                "NOUN",
                "AUX",
                "ADJ",
                "CCONJ",
                "NOUN",
                "AUX",
                "ADJ",
                "PUNCT",
                "ADV",
                "NOUN",
                "AUX",
                "VERB",
                "ADP",
                "PUNCT",
                "NOUN",
                "PUNCT",
            ),
            (
                "if",
                "f",
                "be",
                "ready",
                "and",
                "x",
                "be",
                "valid",
                ",",
                "then",
                "y",
                "be",
                "define",
                "by",
                ":",
                "z",
                ".",
            ),
            12,
        )
