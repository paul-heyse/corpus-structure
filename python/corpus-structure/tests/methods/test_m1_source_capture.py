"""The explicit M1 source-rule arm cannot borrow candidate roles across clauses."""

from types import SimpleNamespace

import pytest
import yaml

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.m1_source import M1Candidates
from corpus_structure.methods.m1_source_capture import RecordCaptureRule
from corpus_structure.orchestrate.m1 import registry
from methods.m1_producer_support import ROOT, ControlledDecoder, owned_reader, view


@pytest.fixture(scope="module")
def rules():
    path = ROOT / "docs/design_review/evidence/2026-11-09_dma-source-rule-capture"
    path = path / "capture-rules.yaml"
    return tuple(RecordCaptureRule.model_validate(row) for row in yaml.safe_load(path.read_text()))


def compare(monkeypatch, text, rules):
    source = view(text)
    reader = owned_reader(source)
    method = M1Candidates()
    monkeypatch.setattr(
        method, "_resident", lambda _, *, providers, native_profile: ControlledDecoder("empty")
    )
    cfg = registry(ROOT / "domains/statistics").overlay(method.name, "default")
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    ctx = SimpleNamespace(reader=reader, check_active=lambda: None)
    (baseline,) = method.run((unit,), cfg, ctx)
    (captured,) = method.run_source_rule_capture_comparison((unit,), cfg, ctx, rules)
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
