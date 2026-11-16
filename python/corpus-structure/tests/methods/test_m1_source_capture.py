"""The explicit M1 source-rule arm cannot borrow candidate roles across clauses."""

from types import SimpleNamespace

import pytest
import yaml

from corpus_structure.methods.m1_source_capture import RecordCaptureRule
from methods.domain_configuration import candidate_configuration
from methods.m1_producer_support import (
    ROOT,
    ControlledDecoder,
    candidate_fixture_inputs,
    candidate_fixture_product,
    view,
)


@pytest.fixture(scope="module")
def rules():
    path = ROOT / "docs/design_review/evidence/2026-11-09_dma-source-rule-capture"
    path = path / "capture-rules.yaml"
    return tuple(RecordCaptureRule.model_validate(row) for row in yaml.safe_load(path.read_text()))


def compare(monkeypatch, text, rules):
    source = view(text)

    decoder = ControlledDecoder("empty")
    cfg = candidate_configuration(ROOT / "domains/statistics", "default")
    ctx = SimpleNamespace(check_active=lambda: None)
    baseline = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=ctx.check_active), decoder
    )
    captured = candidate_fixture_product(
        candidate_fixture_inputs(source, cfg, check_active=ctx.check_active),
        decoder,
        source_capture_rules=rules,
    )
    assert not baseline.records
    assert baseline.parse_detail is not None and captured.parse_detail is not None
    assert "comparison_arm" not in baseline.parse_detail
    assert captured.parse_detail["comparison_arm"] == "exact-source-rule-capture-1"
    return tuple(captured.records or ())


def test_nominal_content_is_bound_with_its_restrictive_clause(monkeypatch, rules):
    text = "The audit team publishes reports about vendors whose contracts expire."
    (record,) = compare(monkeypatch, text, rules)
    fields = {row["role"]: row for row in record["fields"]}
    assert record["standing"] == "candidate"
    assert fields["subject"]["original"] == "The audit team"
    assert fields["predicate"]["original"] == "publishes reports about"
    assert fields["object"]["original"] == "vendors whose contracts expire"
    assert fields["polarity"]["value"]["label"] == "positive"
    assert fields["modality"]["value"]["label"] == "asserted"
    assert fields["condition"]["state"] == "unresolved"
    assert all(anchor["pointer"] == "#/texts/1" for anchor in record["anchors"])
    assert any(
        dep.startswith("source-record-capture:") for dep in record["computation_dependencies"]
    )


@pytest.mark.parametrize(
    "text",
    [
        "The audit team does not publish reports about vendors whose contracts expire.",
        "The audit team publishes reports. A reviewer wrote about vendors whose contracts expire.",
        "Chapter 1",
    ],
)
def test_source_rule_refuses_negated_disjoint_or_heading_like_inputs(monkeypatch, rules, text):
    assert compare(monkeypatch, text, rules) == ()
