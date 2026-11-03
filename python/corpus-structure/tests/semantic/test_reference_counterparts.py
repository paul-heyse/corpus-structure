"""Authored current counterparts; archived HTML/legacy counts are not executed here."""

import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.query import Explanation as FactExplanation
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.query_compatibility import open_query_registry
from corpus_structure.serve.explain import explain
from corpus_structure.serve.journey import bind_session, serve_query

from .inventory_reading import inventory_evidence, inventory_reports, inventory_supports
from .reference_scenarios import publish_reference_case

STAT = "https://corpus-structure.dev/domains/statistics/"
TOY = "https://corpus-structure.dev/domains/toy/"


def entity(id, cls, label=None, *, attributes=(), local=False):
    item = {"id": id, "class_iri": cls, "attributes": list(attributes)}
    if label is not None:
        item["label"] = label
    if local:
        item["scope"] = {"extent": "statement", "locator": "reference.pdf#case-0"}
    return item


def attribute(predicate, value):
    return {"predicate": predicate, "value": value}


def text(value):
    return {"kind": "text", "text": value}


def formula(value):
    return {"kind": "formula", "language": "latex", "expression": value}


def claim(id, subject, predicate, obj, **qualification):
    return {
        "id": id,
        "subject": subject,
        "predicate": predicate,
        "object": {"kind": "entity", "target": obj} if isinstance(obj, str) else obj,
        "qualification": {"modality": "asserted", "polarity": True, **qualification},
        "establishment": "stated",
        "statement": "s",
        "statement_role": "conclusion",
    }


def batch(entities, claims, *, kind="narrative"):
    return {
        "entities": entities,
        "claims": claims,
        "statements": [{"id": "s", "kind": kind, "anchor": "replaced-by-source-custody"}],
    }


def rows(conn, registry, run, name="claims", **params):
    answer = serve_query(conn, registry, name, params, run=run, max_rows=100)
    return json.loads(answer.model_dump_json())["rows"]


def test_statistics_aliases_consolidate_current_source_and_serve_one_family(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
):
    paragraph = (
        "The normal distribution, normally distributed, and normal name the same family "
        "with mean mu; gamma distribution, gamma distributed, and gamma distributions name "
        "a distinct family with mean k; standard normal distribution has mean zero."
    )
    spellings = (
        ("n1", "the normal distribution"),
        ("n2", "normally distributed"),
        ("n3", "normal"),
        ("g1", "gamma distribution"),
        ("g2", "gamma distributed"),
        ("g3", "gamma distributions"),
        ("standard", "standard normal distribution"),
    )
    entities = [
        entity(identity, STAT + "DistributionFamily", label) for identity, label in spellings
    ]
    claims = [claim(f"mean-{i}", f"n{i}", STAT + "mean_value", formula("\\mu")) for i in (1, 2, 3)]
    claims += [claim(f"gamma-{i}", f"g{i}", STAT + "mean_value", formula("k")) for i in (1, 2, 3)]
    claims.append(claim("standard-mean", "standard", STAT + "mean_value", formula("0")))
    prepared, run, _ = publish_reference_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        "statistics",
        [(paragraph, batch(entities, claims))],
    )
    registry = open_query_registry(prepared, DOMAINS / "statistics")
    expected_supports = {
        "\\mu": {"claims/0", "claims/1", "claims/2"},
        "k": {"claims/3", "claims/4", "claims/5"},
        "0": {"claims/6"},
    }
    with read_snapshot(semantic_reader_engine) as conn:
        found = rows(conn, registry, run, predicate="stat:mean_value")
        assert len(found) == 3
        facts = {r["fact"]["object"]["expression"]: r["fact"] for r in found}
        assert set(facts) == {"\\mu", "k", "0"}
        assert len({fact["subject"]["entity_id"] for fact in facts.values()}) == 3
        occurrences = json.loads(
            serve_query(
                conn,
                registry,
                "claims",
                {"predicate": "stat:mean_value"},
                run=run,
                projection="occurrence",
            ).model_dump_json()
        )["rows"]
        assert len(occurrences) == 7
        assert len({r["fact"]["occurrence_id"] for r in occurrences}) == 7
        for expression, expected_items in expected_supports.items():
            selected = [
                r["fact"] for r in occurrences if r["fact"]["object"]["expression"] == expression
            ]
            assert {r["subject"]["entity_id"] for r in selected} == {
                facts[expression]["subject"]["entity_id"]
            }
            assert {r["item"] for r in selected} == expected_items
            explanation = explain(conn, run, "claim", facts[expression]["fact_id"])
            assert explanation.binding.release_id == prepared.release_id
            assert isinstance(explanation.detail, FactExplanation)
            reader = bind_session(conn, run)
            assert {
                support.item for support in inventory_supports(reader, explanation.identifier)
            } == expected_items
            linked = {
                e
                for support in inventory_supports(reader, explanation.identifier)
                for e in support.evidence_ids
            }
            assert linked
            assert {
                e.evidence_id for e in inventory_evidence(reader, explanation.identifier)
            } == linked
            assert {e.source_uri for e in inventory_evidence(reader, explanation.identifier)} == {
                "reference.pdf"
            }
            assert all(
                e.source is not None and e.source.source_view_id is not None
                for e in inventory_evidence(reader, explanation.identifier)
            )
            assert inventory_reports(reader, explanation.identifier)
            for observation in inventory_reports(reader, explanation.identifier):
                if observation.payload.get("claims"):
                    assert {
                        e["quote"] for c in observation.payload["claims"] for e in c["evidence"]
                    } == {paragraph}
        for label, expected in (
            ("normal", "\\mu"),
            ("gamma distribution", "k"),
            ("standard normal distribution", "0"),
        ):
            profile = rows(conn, registry, run, "family_profile", family=label)
            assert {
                r["fact"]["object"]["expression"]
                for r in profile
                if r["fact"]["property_iri"] == STAT + "mean_value"
            } == {expected}


def interval(year):
    return {
        "kind": "validity_interval",
        "start": {"kind": "partial_date", "lexical": f"{year}-01-01"},
        "end": {"kind": "partial_date", "lexical": f"{year}-12-31"},
        "start_incl": True,
        "end_incl": True,
    }


def test_toy_current_attribution_provenance_ambiguity_and_temporal_answers(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
):
    paragraph = (
        "The three distinct registered organizations Acme (ORG-101), Acme (ORG-202), "
        "and Acme (org-101) own P-17; ORG-101 owns it in 2020 and 2022, files F1 and F2 "
        "for 2021, records shares 0.5 and 0.8, and is reported by Alpha and Beta."
    )
    entities = [
        entity("asset", TOY + "Asset", "P-17"),
        entity(
            "org",
            TOY + "Organization",
            "Acme",
            attributes=[attribute(TOY + "registry_id", text("ORG-101"))],
        ),
        entity(
            "other",
            TOY + "Organization",
            "Acme",
            attributes=[attribute(TOY + "registry_id", text("ORG-202"))],
        ),
        entity(
            "lower",
            TOY + "Organization",
            "Acme",
            attributes=[attribute(TOY + "registry_id", text("org-101"))],
        ),
        entity("alpha", TOY + "Source", "Alpha"),
        entity("beta", TOY + "Source", "Beta"),
    ]
    claims = [
        claim(f"year{year}", "org", TOY + "owns", "asset", valid_time=interval(year))
        for year in (2020, 2022)
    ]
    claims += [
        claim(f"filing-{f}", "org", TOY + "owns", "asset", valid_time=interval(2021), filing_ref=f)
        for f in ("F1", "F2")
    ]
    claims += [
        claim(f"share-{s}", "org", TOY + "owns", "asset", share={"kind": "number", "number": s})
        for s in ("0.5", "0.8")
    ]
    claims += [
        claim(
            f"report-{who}", "org", TOY + "owns", "asset", modality="toy:reported", attribution=who
        )
        for who in ("alpha", "beta")
    ]
    claims += [
        claim(f"other-owner-{who}", who, TOY + "owns", "asset") for who in ("other", "lower")
    ]
    prepared, run, _ = publish_reference_case(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        "toy",
        [(paragraph, batch(entities, claims, kind="toy:clause"))],
    )
    registry = open_query_registry(prepared, DOMAINS / "toy")
    with read_snapshot(semantic_reader_engine) as conn:
        accepted = rows(conn, registry, run, predicate="toy:owns")
        candidates = rows(conn, registry, run, predicate="toy:owns", include_candidates=True)
        assert len(accepted) == 7
        assert len(candidates) == 9
        assert len({r["fact"]["subject"]["entity_id"] for r in accepted}) == 3
        reports = [
            r["fact"] for r in accepted if r["fact"]["qualification"]["modality"] == "toy:reported"
        ]
        assert len(reports) == 2
        assert len({r["qualification"]["attribution"] for r in reports}) == 2
        shares = [r["fact"] for r in candidates if "share" in r["fact"]["qualification"]]
        assert {r["qualification"]["share"]["number"] for r in shares} == {"0.5", "0.8"}
        assert all(r["fact_id"] not in {x["fact"]["fact_id"] for x in accepted} for r in shares)
        temporal = rows(conn, registry, run, "ownership_at", asset="P-17", date="2020-07-01")
        assert sorted(r["applicability"] for r in temporal) == [
            "established",
            "not_applicable",
            "not_applicable",
            "unknown",
            "unknown",
            "unknown",
            "unknown",
        ]
        filing = next(
            r["fact"]
            for r in accepted
            if r["fact"]["qualification"].get("valid_time", {}).get("start", {}).get("lexical")
            == "2021-01-01"
        )
        explained = explain(conn, run, "claim", filing["fact_id"])
        assert explained.binding.release_id == prepared.release_id
        occurrence = json.loads(
            serve_query(
                conn,
                registry,
                "claims",
                {"predicate": "toy:owns"},
                run=run,
                projection="occurrence",
            ).model_dump_json()
        )["rows"]
        assert {
            r["fact"]["qualification"].get("filing_ref")
            for r in occurrence
            if r["fact"]["fact_id"] == filing["fact_id"]
        } == {"F1", "F2"}


def test_toy_original_inspection_quotes_preserve_nested_roles_and_source_decimal(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
):
    reference = json.loads(
        (
            Path(__file__).resolve().parents[4] / "fixtures/toy/semantic-inspection-reference.json"
        ).read_bytes()
    )
    paragraph = (
        "Inspector Boreal (ORG-202) inspected vessel P-17, held by custodian Acme (ORG-101), "
        "on 2020-07-01. The vessel was intact and its measured cargo quantity was exactly "
        "12.3400 kg, on a dry-mass basis."
    )
    authored = deepcopy(reference)
    positive = authored["claims"][0]
    # Deliberately wrong reports test representation and exact object filtering. Their
    # distinctness is not a claim that source-truth adjudication accepts the changes.
    swapped = deepcopy(positive)
    swapped["id"] = "negative-swapped-roles"
    swapped["object"]["inspector"] = "expected-custodian"
    swapped["object"]["custodian"] = "expected-inspector"
    changed = deepcopy(positive)
    changed["id"] = "negative-changed-custodian"
    changed["object"]["custodian"] = "expected-inspector"
    authored["claims"].extend((swapped, changed))
    authored["statements"] = [{"id": "s", "kind": "toy:clause", "anchor": "source-custody"}]
    for assertion in authored["claims"]:
        assertion.update(statement="s", statement_role="conclusion")
    prepared, run, _ = publish_reference_case(
        semantic_db_engine, semantic_writer_engine, tmp_path, "toy", [(paragraph, authored)]
    )
    registry = open_query_registry(prepared, DOMAINS / "toy")
    with read_snapshot(semantic_reader_engine) as conn:
        registry_rows = rows(conn, registry, run, predicate="toy:registry_id")
        endpoints = {r["fact"]["object"]: r["fact"]["subject"]["entity_id"] for r in registry_rows}
        assert set(endpoints) == {"ORG-101", "ORG-202"}
        assert len(set(endpoints.values())) == 2
        found = rows(conn, registry, run, predicate="toy:inspection")
        assert len(found) == 3
        by_roles = {
            (r["fact"]["object"]["inspector"], r["fact"]["object"]["custodian"]): r["fact"]
            for r in found
        }
        expected = {
            (endpoints["ORG-202"], endpoints["ORG-101"]): ("claims/0", "expected-inspection"),
            (endpoints["ORG-101"], endpoints["ORG-202"]): ("claims/1", "negative-swapped-roles"),
            (endpoints["ORG-202"], endpoints["ORG-202"]): (
                "claims/2",
                "negative-changed-custodian",
            ),
        }
        assert set(by_roles) == set(expected)
        assert len({r["fact_id"] for r in by_roles.values()}) == 3
        for roles, (item, authored_id) in expected.items():
            actual = by_roles[roles]
            obj = actual["object"]
            assert obj["kind"] == "inspection"
            assert obj["details"]["condition"] == "intact"
            measured = obj["details"]["measured_quantity"]
            assert (Decimal(measured["number"]), measured["unit"], measured["basis"]) == (
                Decimal("12.3400"),
                "kg",
                "dry-mass",
            )
            assert actual["qualification"]["valid_time"] == {
                "kind": "validity_interval",
                "start": {"kind": "partial_date", "lexical": "2020-07-01"},
                "end": {"kind": "partial_date", "lexical": "2020-07-01"},
                "start_incl": True,
                "end_incl": True,
            }
            expected_object = {
                "kind": "inspection",
                "inspector": roles[0],
                "custodian": roles[1],
                "details": {
                    "condition": "intact",
                    "measured_quantity": {
                        "kind": "quantity",
                        "number": "12.3400",
                        "unit": "kg",
                        "basis": "dry-mass",
                    },
                },
            }
            filtered = rows(
                conn, registry, run, predicate="toy:inspection", object=json.dumps(expected_object)
            )
            assert [r["fact"]["fact_id"] for r in filtered] == [actual["fact_id"]]
            explanation = explain(conn, run, "claim", actual["fact_id"])
            assert explanation.binding.release_id == prepared.release_id
            assert isinstance(explanation.detail, FactExplanation)
            reader = bind_session(conn, run)
            assert {
                support.item for support in inventory_supports(reader, explanation.identifier)
            } == {item}
            citation_roles = {
                citation.role
                for support in inventory_supports(reader, explanation.identifier)
                for citation in support.citation_roles
            }
            assert citation_roles == {"primary", "supporting"}
            assert len(inventory_evidence(reader, explanation.identifier)) == 2
            matching = [
                c
                for observation in inventory_reports(reader, explanation.identifier)
                for c in observation.payload.get("claims", ())
                if c["id"] == authored_id
            ]
            assert len(matching) == 1
            source_claim = matching[0]
            assert source_claim["object"]["details"]["measured_quantity"]["number"] == "12.3400"
            assert {(e["quote"], e["role"]) for e in source_claim["evidence"]} == {
                (
                    "Inspector Boreal (ORG-202) inspected vessel P-17, "
                    "held by custodian Acme (ORG-101), "
                    "on 2020-07-01.",
                    "primary",
                ),
                (
                    "The vessel was intact and its measured cargo quantity was exactly 12.3400 kg, "
                    "on a dry-mass basis.",
                    "supporting",
                ),
            }
