"""Current selected domain semantics and exact native literal custody, not linguistic accuracy."""

from datetime import date
from decimal import Decimal

import pytest
from evaluate.declared_record_native_support import project_context, run_readings

from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.rich_queries import (
    ClaimsQuery,
    ConstructionProfileQuery,
    EntityQuery,
    FamilyProfileQuery,
    OwnershipAtQuery,
)
from semantic.record_publication_native_support import (
    query_publication,
)
from semantic.record_publication_native_support import (
    rich_publication as rich_publication,
)
from semantic.rich_domain_native_support import (
    publish_domain,
    toy_recipe,
)
from semantic.rich_domain_native_support import (
    toy_publication as toy_publication,
)
from semantic.rich_domain_preservation_support import DomainGraph, inspection, t1, t2, t4


def test_actual_toy_native_recipe_retains_its_own_qualification_and_rules(tmp_path):
    from corpus_structure.semantic.statement_types import effective_bindings
    from semantic.data_operation_kernel_support import prepare_kernel

    prepared = prepare_kernel(toy_recipe(tmp_path))
    assert effective_bindings(prepared.prepared)["qualification"] == "ToyQualification"
    assert all(item.complete for item in prepared.model.implementation_slices)


@pytest.mark.parametrize("case", ("T1", "T2", "T4"))
def test_native_selected_statistics_profiles_preserve_exact_domain_cases(rich_publication, case):
    journey = rich_publication
    if case == "T1":
        entities = {"LS": "FamilyConstruction", "scale": "FamilyParameter", "Z": "RandomVariable"}
    elif case == "T2":
        entities = {
            "normal": "DistributionFamily",
            "X": "RandomVariable",
            **{
                key: "FamilyParameter"
                for key in ("location", "scale", "mean", "standard_deviation")
            },
        }
    else:
        entities = {
            "lognormal": "DistributionFamily",
            "normal": "DistributionFamily",
            "Y": "RandomVariable",
            **{key: "FamilyParameter" for key in ("mu", "sigma", "exp_mu_scale")},
        }
    graph = DomainGraph(
        (journey.kernel.prepared, journey.kernel.model, "StatisticsQualification"),
        entities,
        context=project_context(journey, "rich.consolidate"),
    )
    {"T1": t1, "T2": t2, "T4": t4}[case](graph)
    publication = publish_domain(journey, graph, inference="exact-domain-" + case)
    query = (
        ConstructionProfileQuery(name="construction_profile", construction="LS")
        if case == "T1"
        else FamilyProfileQuery(
            name="family_profile", family="normal" if case == "T2" else "lognormal"
        )
    )
    rows = query_publication(publication, query)["rows"]
    decoded = [(row["fact"], decode_semantic_value(row["object"])) for row in rows]
    if case == "T1":
        assert (
            query_publication(
                publication, EntityQuery(name="entity", class_name="DistributionFamily")
            )["rows"]
            == []
        )
        assert {
            row["entity"]["entity_id"]
            for row in query_publication(
                publication, EntityQuery(name="entity", class_name="FamilyConstruction")
            )["rows"]
        } == {"LS"}
        construction = next(
            row for row in rows if row["fact"]["predicate"].endswith("/construction_formula")
        )
        qualification = decode_semantic_value(construction["occurrences"][0]["qualification"])
        assert qualification["base_variable"] == "Z"
        assert qualification["condition"]["kind"] == "member"
        assert qualification["condition"]["set"]["expression"] == "(0, \\infty)"
        assert not any(fact["predicate"].endswith("/member_of_construction") for fact, _ in decoded)
    elif case == "T2":
        assert {
            (fact["subject_entity"], value)
            for fact, value in decoded
            if fact["predicate"].endswith("/identical_parameter")
        } == {("location", "mean"), ("scale", "standard_deviation")}
        assert {
            fact["subject_entity"]
            for fact, _ in decoded
            if fact["predicate"].endswith("/has_parameter")
        } == {"normal"}
    else:
        assert {
            (fact["subject_entity"], value)
            for fact, value in decoded
            if fact["predicate"].endswith("/parameter_role")
        } == {("sigma", "shape")}
        assert (
            next(
                value for fact, value in decoded if fact["predicate"].endswith("/derived_parameter")
            )["expression"]
            == "e^\\mu"
        )
        assert not any(fact["predicate"].endswith("/identical_parameter") for fact, _ in decoded)


def test_native_toy_filing_occurrences_keep_attribution_valid_time_and_nested_roles(
    toy_publication,
):
    journey = toy_publication
    graph = DomainGraph(
        (journey.kernel.prepared, journey.kernel.model, "ToyQualification"),
        {
            "owner": "Organization",
            "inspector": "Organization",
            "custodian": "Organization",
            "other": "Organization",
            "source": "Source",
            "other-source": "Source",
            "asset": "Asset",
        },
        context=project_context(journey, "rich.consolidate"),
    )
    qualification = dict(
        modality="toy:reported",
        polarity=True,
        attribution="source",
        filing_ref="A",
        valid_time=dict(
            kind="validity_interval", start=dict(kind="partial_date", lexical="2020-07")
        ),
    )
    for name, extra in (
        ("A", {}),
        ("B", {"filing_ref": "B"}),
        ("attributed", {"attribution": "other-source"}),
        (
            "dated",
            {
                "valid_time": dict(
                    kind="validity_interval", start=dict(kind="partial_date", lexical="2021-07")
                )
            },
        ),
    ):
        graph.add(name, "owner", "owns", "asset", qualification={**qualification, **extra})
    graph.add("inspection", "asset", "inspection", inspection())
    publication = publish_domain(journey, graph, inference="exact-toy-domain")
    rows = query_publication(publication, ClaimsQuery(name="claims", population="retained"))["rows"]
    ownership = [row for row in rows if row["fact"]["predicate"].endswith("/owns")]
    same = next(row for row in ownership if len(row["occurrences"]) == 2)
    assert len(ownership) == 3
    assert {
        decode_semantic_value(item["qualification"])["filing_ref"] for item in same["occurrences"]
    } == {"A", "B"}
    assert len({item["occurrence_id"] for item in same["occurrences"]}) == 2
    assert {
        decode_semantic_value(item["qualification"])["attribution"]
        for row in ownership
        for item in row["occurrences"]
    } == {"source", "other-source"}
    assert {
        decode_semantic_value(item["qualification"])["valid_time"]["start"]["lexical"]
        for row in ownership
        for item in row["occurrences"]
    } == {"2020-07", "2021-07"}
    nested = next(
        decode_semantic_value(row["object"])
        for row in rows
        if row["fact"]["predicate"].endswith("/inspection")
    )
    assert (nested["inspector"], nested["custodian"]) == ("inspector", "custodian")
    assert nested["details"]["measured_quantity"] == dict(
        kind="quantity", number=Decimal("12.3400"), unit="kg", basis="dry-mass"
    )
    temporal = query_publication(
        publication,
        OwnershipAtQuery(name="ownership_at", asset="asset", date=date(2020, 7, 1)),
        limit=1,
    )
    assert temporal["rows"][0]["applicability"] == "unknown"
    continuation = query_publication(
        publication,
        OwnershipAtQuery(name="ownership_at", asset="asset", date=date(2020, 7, 1)),
        cursor=temporal["cursor"],
    )
    assert len(continuation["rows"]) == 3
    assert {row["applicability"] for row in continuation["rows"]} == {"unknown"}
    assert temporal["cut_id"] == continuation["cut_id"] and temporal["root"] == continuation["root"]
    assert (
        len(
            {
                row["occurrence"]["occurrence_id"]
                for row in [*temporal["rows"], *continuation["rows"]]
            }
        )
        == 4
    )
    assert (
        query_publication(
            publication,
            OwnershipAtQuery(name="ownership_at", asset="unselected-asset", date=date(2020, 7, 1)),
        )["rows"]
        == []
    )


def test_native_record_reading_retains_original_decimal_spelling(
    scenario_seeds, tmp_path, monkeypatch
):
    from evaluate import declared_record_native_support as support
    from evaluate.declared_rich_native_support import rich_policy_recipe

    from semantic.rich_domain_native_support import decimal_source_stream

    monkeypatch.setattr(support, "controlled_table_stream", decimal_source_stream)
    with support.current_record_policy_journey(
        scenario_seeds, tmp_path, monkeypatch, recipe=rich_policy_recipe(tmp_path)
    ) as journey:
        source = journey.sources[0]
        readings = run_readings(
            journey,
            (source,),
            policy=None,
            family="measurement",
            inference="native-decimal-spelling",
        )
        ((_, raw),) = readings.raw
        complete = [
            member["body"]
            for member in raw["members"]
            if member["body"]["candidate_type"] == "record"
            and next(
                field for field in member["body"]["fields"] if field["role"] == "original_value"
            )["state"]
            == "present"
        ]
        assert len(complete) == 2
        assert {row["text"] for row in raw["coordinate_texts"]} == {"12.3400"}
        for record in complete:
            field = next(field for field in record["fields"] if field["role"] == "original_value")
            assert field["original"] == "12.3400"
            assert field["value"] == dict(kind="decimal", lexical="12.3400")
            assert Decimal(field["original"]) == Decimal("12.34")
            assert {
                anchor["source_piece"] for anchor in record["anchors"] if "source_piece" in anchor
            } == {"12.3400"}
            assert all(anchor["pin"] == raw["source_pin"] for anchor in record["anchors"])
