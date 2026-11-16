"""Exact domain meaning controls; authored inputs do not establish extraction accuracy."""

import json
from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from corpus_structure.semantic.rich_queries import ownership_applicability
from semantic.rich_domain_preservation_support import (
    ROOT,
    DomainGraph,
    domain_source,
    inspection,
    t1,
    t2,
    t4,
)


@pytest.fixture(scope="module")
def statistics_domain():
    return domain_source("statistics")


@pytest.fixture(scope="module")
def toy_domain():
    return domain_source("toy")


def source_quotes(unit):
    """Retained source quotations are independent of the current lowerer's output."""
    target = json.loads((ROOT / "fixtures/trace" / (unit + ".target.json")).read_bytes())
    return tuple(
        evidence["quote"]
        for claim in target["batch"]["claims"]
        for evidence in claim.get("evidence", ())
    )


def plain(value):
    return (
        value.model_dump(mode="python", exclude_unset=True)
        if hasattr(value, "model_dump")
        else value
    )


def test_t1_construction_only_base_variable_and_positive_scale(statistics_domain):
    assert any("location-scale family" in quote for quote in source_quotes("T1"))
    assert any("b \\in (0, \\infty)" in quote for quote in source_quotes("T1"))
    graph = DomainGraph(
        statistics_domain,
        {"LS": "FamilyConstruction", "scale": "FamilyParameter", "Z": "RandomVariable"},
    )
    t1(graph)
    assert graph.classes["LS"] == "FamilyConstruction"
    assert "member_of_construction" not in {
        fact.predicate.rsplit("/", 1)[-1] for fact in graph.lower.facts
    }
    assert graph.object("construction").expression == "a + b Z"
    qualification = plain(graph.qualification("construction"))
    assert qualification["base_variable"] == "Z"
    assert qualification["condition"]["kind"] == "member"
    assert qualification["condition"]["x"]["expression"] == "b"
    assert qualification["condition"]["x"]["bindings"] == (
        {"kind": "family_param", "symbol": "b", "entity": "scale"},
    )
    assert qualification["condition"]["set"]["expression"] == "(0, \\infty)"
    assert graph.object("scale-domain").expression == "(0, \\infty)"
    wrong = DomainGraph(
        statistics_domain,
        {"LS": "FamilyConstruction", "scale": "FamilyParameter", "Z": "DistributionFamily"},
    )
    with pytest.raises(ValueError, match="class membership"):
        t1(wrong)


def test_t2_respectively_pairs_parameters_of_the_family_not_random_variable(statistics_domain):
    assert any(
        "mean and standard deviation, respectively" in quote for quote in source_quotes("T2")
    )
    graph = DomainGraph(
        statistics_domain,
        {
            "normal": "DistributionFamily",
            "X": "RandomVariable",
            **{
                key: "FamilyParameter"
                for key in ("location", "scale", "mean", "standard_deviation")
            },
        },
    )
    t2(graph)
    pairs = {
        (result.fact.subject_entity, graph.object(key))
        for key, result in graph.results.items()
        if result.fact.predicate.endswith("/identical_parameter")
    }
    assert pairs == {("location", "mean"), ("scale", "standard_deviation")}
    assert ("location", "standard_deviation") not in pairs and ("scale", "mean") not in pairs
    assert {
        graph.object(name + "-family")
        for name in ("location", "scale", "mean", "standard_deviation")
    } == {"normal"}
    assert all(
        result.fact.subject_entity == "normal"
        for result in graph.results.values()
        if result.fact.predicate.endswith("/has_parameter")
    )
    assert "has_parameter" not in {
        prop.name for prop in graph.prepared.index.definitions["RandomVariable"].properties
    }
    with pytest.raises(ValueError, match="class membership"):
        graph.add("wrong-family-owner", "location", "family", "X")


def test_t4_lognormal_mu_sigma_shape_and_exponential_scale_have_no_identity_edge(statistics_domain):
    quotes = source_quotes("T4")
    assert any("shape parameter" in quote and "sigma" in quote for quote in quotes)
    assert any("e^\\mu" in quote and "scale parameter" in quote for quote in quotes)
    graph = DomainGraph(
        statistics_domain,
        {
            "lognormal": "DistributionFamily",
            "normal": "DistributionFamily",
            "Y": "RandomVariable",
            **{key: "FamilyParameter" for key in ("mu", "sigma", "exp_mu_scale")},
        },
    )
    t4(graph)
    assert {graph.object("lognormal-" + key) for key in ("mu", "sigma", "exp_mu_scale")} == {
        "mu",
        "sigma",
        "exp_mu_scale",
    }
    assert graph.object("sigma-role") == "shape"
    derived = graph.object("scale-derived")
    assert derived.expression == "e^\\mu"
    assert plain(derived)["bindings"] == (
        {"kind": "constant", "symbol": "e"},
        {"kind": "family_param", "symbol": "\\mu", "entity": "mu"},
    )
    assert graph.object("transformation") == "normal"
    assert plain(graph.qualification("transformation"))["param_mapping"] == {
        "mu": {"key": "mu", "value": "mean"},
        "sigma": {"key": "sigma", "value": "standard_deviation"},
    }
    assert not any(fact.predicate.endswith("/identical_parameter") for fact in graph.lower.facts)


def test_toy_nested_inspector_custodian_roles_and_quantity_meaning_are_not_interchangeable(
    toy_domain,
):
    graph = DomainGraph(
        toy_domain,
        {"asset": "Asset", **{key: "Organization" for key in ("inspector", "custodian", "other")}},
    )
    original = inspection()
    graph.add("original", "asset", "inspection", original)
    swapped = deepcopy(original)
    swapped["inspector"], swapped["custodian"] = swapped["custodian"], swapped["inspector"]
    graph.add("swapped", "asset", "inspection", swapped)
    changed = deepcopy(original)
    changed["custodian"] = "other"
    graph.add("changed", "asset", "inspection", changed)
    assert len({result.fact.object_value for result in graph.results.values()}) == 3
    decoded = plain(graph.object("original"))
    assert (decoded["inspector"], decoded["custodian"]) == ("inspector", "custodian")
    assert plain(graph.object("swapped"))["inspector"] == "custodian"
    assert plain(graph.object("changed"))["custodian"] == "other"
    amount = decoded["details"]["measured_quantity"]
    assert amount == dict(kind="quantity", number=Decimal("12.3400"), unit="kg", basis="dry-mass")
    for label, field, value in (("unit", "unit", "g"), ("basis", "basis", "wet-mass")):
        changed = deepcopy(original)
        changed["details"]["measured_quantity"][field] = value
        graph.add(label, "asset", "inspection", changed)
        assert graph.results[label].fact.object_value != graph.results["original"].fact.object_value
    unknown = deepcopy(original)
    unknown["custodian"] = "not-selected"
    with pytest.raises(ValueError, match="outside its exact selected"):
        graph.add("unknown", "asset", "inspection", unknown)


def test_toy_descriptive_filing_reference_is_separate_from_attribution_and_valid_time_meaning(
    toy_domain,
):
    graph = DomainGraph(
        toy_domain,
        {"owner": "Organization", "source": "Source", "other-source": "Source", "asset": "Asset"},
    )
    qualification = dict(
        modality="toy:reported",
        polarity=True,
        attribution="source",
        filing_ref="filing-A",
        valid_time=dict(
            kind="validity_interval",
            start=dict(kind="partial_date", lexical="2020-07-01"),
            end=dict(kind="partial_date", lexical="2020-07-01"),
            start_incl=True,
            end_incl=True,
        ),
    )
    graph.add("A", "owner", "owns", "asset", qualification=qualification)
    graph.add(
        "B", "owner", "owns", "asset", qualification={**qualification, "filing_ref": "filing-B"}
    )
    graph.add(
        "attributed",
        "owner",
        "owns",
        "asset",
        qualification={**qualification, "attribution": "other-source"},
    )
    later = deepcopy(qualification)
    later["valid_time"]["start"]["lexical"] = later["valid_time"]["end"]["lexical"] = "2021-07-01"
    graph.add("dated", "owner", "owns", "asset", qualification=later)
    assert graph.results["A"].fact.fact_id == graph.results["B"].fact.fact_id
    assert (
        graph.results["A"].observed_qualification_value
        != graph.results["B"].observed_qualification_value
    )
    assert len({graph.results[key].fact.fact_id for key in ("A", "attributed", "dated")}) == 3
    observations = [
        packet.body
        for packet in graph.propositions().members
        if packet.body.member_type == "authored-proposition"
    ]
    assert len(observations) == 4
    assert {plain(graph.qualification(key))["filing_ref"] for key in ("A", "B")} == {
        "filing-A",
        "filing-B",
    }
    assert plain(graph.qualification("dated"))["valid_time"]["start"]["lexical"] == "2021-07-01"


@pytest.mark.parametrize(
    "interval,expected",
    (
        (None, "unknown"),
        ({"kind": "validity_interval"}, "established"),
        ({"start": {"kind": "partial_date", "lexical": "2020-07"}}, "unknown"),
        ({"start": {"kind": "text", "text": "last summer"}}, "unknown"),
        ({"start": {"kind": "partial_date", "lexical": "2020-02-31"}}, "unknown"),
        ({"start": {"kind": "partial_date", "lexical": "2020-07-01"}}, "unknown"),
        (
            {"start": {"kind": "partial_date", "lexical": "2020-07-01"}, "start_incl": False},
            "not_applicable",
        ),
        (
            {"start": {"kind": "partial_date", "lexical": "2020-07-01"}, "start_incl": True},
            "established",
        ),
        ({"start": {"kind": "partial_date", "lexical": "2020-07-02"}}, "not_applicable"),
        ({"end": {"kind": "partial_date", "lexical": "2020-06-30"}}, "not_applicable"),
        (
            {"end": {"kind": "partial_date", "lexical": "2020-07-01"}, "end_incl": False},
            "not_applicable",
        ),
        (
            {"end": {"kind": "partial_date", "lexical": "2020-07-01"}, "end_incl": True},
            "established",
        ),
    ),
)
def test_current_ownership_applicability_keeps_partial_dates_unknown(interval, expected):
    assert ownership_applicability(interval, date(2020, 7, 1)) == expected


def test_current_ownership_date_has_exact_json_query_and_resource_wire():
    from pydantic import TypeAdapter

    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.rich_queries import OwnershipAtQuery, RichQuery
    from corpus_structure.serve.rich_queries import RichQueryRequest

    query = OwnershipAtQuery(name="ownership_at", asset="asset", date=date(2020, 7, 1))
    request = RichQueryRequest(
        demand_id="explicit-demand", project_id="project", product_id="actual-product", query=query
    )
    wire = json_loads(json_bytes(request.model_dump(mode="python")))
    assert wire["query"] == dict(
        name="ownership_at",
        asset="asset",
        date="2020-07-01",
        population="selected",
        include_suppositions=False,
    )
    parsed = TypeAdapter(RichQuery).validate_python(wire["query"])
    assert isinstance(parsed, OwnershipAtQuery) and parsed.date == date(2020, 7, 1)
