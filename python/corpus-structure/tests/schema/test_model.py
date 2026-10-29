"""The model: lint, the declaration check, enum expansion, the revision and Stage A's output.

Model and projections §3.1, §3.2, §6. Expectations are written by hand from D1 §5.2, TM §8 and
TM §11, never read back from the generated files they check.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from corpus_structure.core import vocab
from corpus_structure.core._model import names, qualifiers, revision, sql, validators
from corpus_structure.schema import generate, model

MODEL = model.MODEL_DIR


@pytest.fixture(scope="module")
def loaded() -> model.Model:
    return model.load()


def seeded(tmp_path: Path, edit_core=None, edit_system=None) -> model.Model:
    """The model with its YAML edited as data, written beside each other in `tmp_path`."""
    for name, edit in (("core.yaml", edit_core), ("system.yaml", edit_system)):
        data = yaml.safe_load((MODEL / name).read_text(encoding="utf-8"))
        if edit is not None:
            edit(data)
        (tmp_path / name).write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return model.load(tmp_path / "core.yaml", tmp_path / "system.yaml")


# --- Lint and the declaration check ------------------------------------------------------------


def lint_errors(path: Path) -> list[str]:
    """linkml-lint's error lines for one module (its TSV format drops metamodel errors)."""
    lint = shutil.which("linkml-lint")
    assert lint is not None
    out = subprocess.run(
        [lint, "--config", str(MODEL / ".linkmllint.yaml"), str(path)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    return [line for line in out.stdout.splitlines() if line.lstrip().startswith("error")]


@pytest.mark.skipif(shutil.which("linkml-lint") is None, reason="blocked: linkml (dev) missing")
@pytest.mark.parametrize("module", ["core.yaml", "system.yaml"])
def test_the_modules_lint_without_errors(module: str) -> None:
    assert lint_errors(MODEL / module) == []


@pytest.mark.skipif(shutil.which("linkml-lint") is None, reason="blocked: linkml (dev) missing")
def test_lint_reports_a_seeded_metamodel_error(tmp_path: Path) -> None:
    shutil.copy(MODEL / "core.yaml", tmp_path / "core.yaml")
    text = (MODEL / "system.yaml").read_text(encoding="utf-8")
    (tmp_path / "system.yaml").write_text(
        text.replace("  RunStatus:\n", "  RunStatus:\n    bogus: 1\n", 1)
    )
    assert any("'bogus' was unexpected" in line for line in lint_errors(tmp_path / "system.yaml"))


def test_the_model_passes_its_declaration_check(loaded: model.Model) -> None:
    assert model.check(loaded, vocab.MEMBER_PROPERTIES) == []


def _class(data: dict, name: str) -> dict:
    return data["classes"][name]


def _ann(element: dict, tag: str, value: str) -> None:
    element["annotations"][tag] = value


@pytest.mark.parametrize(
    ("edit", "problem"),
    [
        (lambda d: _class(d, "Statement")["annotations"].update({"ci:colour": "red"}),
         "ci:colour is not in the declaration vocabulary"),
        (lambda d: d["slots"]["defines"]["annotations"].update({"ci:record": "x"}),
         "ci:record has no consumer"),
        (lambda d: d["slots"]["hedge"]["annotations"].update({"ci:key_role": "decisive"}),
         "ci:key_role value 'decisive' is not admitted"),
        (lambda d: _ann(d["slots"]["attribution"], "ci:key_role_when", "search_block"),
         "is not a ClaimModality member property"),
        (lambda d: _ann(_class(d, "Evidence"), "ci:invariant", "ordered(start, finish)"),
         "names unknown field 'finish'"),
        (lambda d: _ann(_class(d, "Evidence"), "ci:invariant", "sorted(start, end)"),
         "not an invariant template"),
        (lambda d: d["enums"]["Polarity"].pop("annotations"),
         "declares its ci:lifecycle"),
        (lambda d: d["enums"]["Polarity"]["permissible_values"]["negative"].update(
            {"in_subset": ["search_block"]}), "is used by ['Polarity', 'SegmentKind']"),
        (lambda d: d["slots"]["defines"]["in_subset"].append("premise_forming"),
         "member property premise_forming is also an element subset"),
        (lambda d: d["slots"]["scope"]["annotations"].update({"ci:stored_range": "Nowhere"}),
         "ci:stored_range 'Nowhere' is not a class"),
    ],
)  # fmt: skip
def test_a_seeded_declaration_is_refused(tmp_path: Path, edit, problem: str) -> None:
    problems = model.check(seeded(tmp_path, edit_core=edit), vocab.MEMBER_PROPERTIES)
    assert any(problem in p for p in problems), problems


def test_an_invariant_value_outside_its_enum_is_refused(tmp_path: Path) -> None:
    def edit(d: dict) -> None:
        _class(d, "KbSegment")["annotations"]["ci:invariant"] = (
            "iff_absent(parse_reason, parse_status = fine)"
        )

    problems = model.check(seeded(tmp_path, edit_system=edit))
    assert any("'fine' is not a DelimitingStatus member" in p for p in problems), problems


def test_a_member_property_missing_from_the_generated_set_is_refused(loaded: model.Model) -> None:
    generated = {k: v for k, v in vocab.MEMBER_PROPERTIES.items() if k != "search_block"}
    assert model.check(loaded, generated) == [
        "member property search_block is not in the generated vocabulary"
    ]


# --- Enum expressions (model and projections §3.1) ---------------------------------------------

MODALITIES = """
id: https://example.org/pack
name: pack
default_prefix: pack
prefixes: {linkml: https://w3id.org/linkml/, pack: https://example.org/pack/}
imports: [linkml:types]
subsets:
  premise_forming: {description: p}
  conflict_bearing: {description: c}
  attribution_identifying: {description: a}
enums:
  CoreModality:
    permissible_values:
      asserted: {in_subset: [conflict_bearing]}
      supposed: {in_subset: [premise_forming]}
      cited: {in_subset: [attribution_identifying]}
      posed: {}
  Extra:
    permissible_values:
      hearsay: {in_subset: [attribution_identifying]}
      supposed: {}
  PackModality:
    inherits: [CoreModality]
    include:
      - inherits: [Extra]
      - permissible_values: {asserted: {}, reported: {in_subset: [attribution_identifying]}}
    minus:
      - permissible_values: {posed: {}}
    permissible_values:
      warranted: {in_subset: [conflict_bearing]}
"""


def view(tmp_path: Path, text: str):
    path = tmp_path / "pack.yaml"
    path.write_text(text, encoding="utf-8")
    from linkml_runtime.utils.schemaview import SchemaView

    return SchemaView(str(path))


def test_inherits_include_and_minus_expand_in_order_with_their_properties(tmp_path: Path) -> None:
    members = model.expand_enum(view(tmp_path, MODALITIES), "PackModality")
    assert [(m.text, m.properties, m.defined_in) for m in members] == [
        ("warranted", ("conflict_bearing",), "PackModality"),
        ("asserted", ("conflict_bearing",), "CoreModality"),
        ("supposed", ("premise_forming",), "CoreModality"),
        ("cited", ("attribution_identifying",), "CoreModality"),
        ("hearsay", ("attribution_identifying",), "Extra"),
        ("reported", ("attribution_identifying",), "PackModality"),
    ]  # include's repeats (supposed, asserted) kept once, from their first definition; posed minus


def test_a_pack_member_colliding_with_a_core_member_is_refused(tmp_path: Path) -> None:
    text = MODALITIES.replace("warranted: {in_subset: [conflict_bearing]}", "cited: {}")
    with pytest.raises(model.EnumExpansionError, match="'cited' collides with CoreModality"):
        model.expand_enum(view(tmp_path, text), "PackModality")


# --- The model revision ------------------------------------------------------------------------


def test_the_revision_hashes_the_parsed_files_and_is_logged(
    loaded: model.Model, tmp_path: Path
) -> None:
    current = model.revision(loaded)
    assert (current.label, current.key_scheme) == ("0.3.0", 1)
    assert model.check_log(current, model.read_log()) == []
    reordered = seeded(tmp_path, edit_core=lambda d: d.update(dict(reversed(list(d.items())))))
    assert model.content_hash(*reordered.paths) == current.content_hash  # parsed, not bytes
    described = seeded(tmp_path, edit_core=lambda d: d.update({"description": "other"}))
    assert model.content_hash(*described.paths) != current.content_hash
    assert (current.content_hash, 1) == (revision.CONTENT_HASH, revision.KEY_SCHEME)


def test_a_log_that_does_not_end_at_the_current_revision_is_refused(loaded: model.Model) -> None:
    current = model.revision(loaded)
    log = model.read_log()
    stale = [{**log[0], "content_hash": "0" * 64}]
    assert any("not its logged revision" in p for p in model.check_log(current, stale))
    child = {**log[0], "parent": "1" * 64, "change_record": None}
    assert any("names its parent" in p for p in model.check_log(current, [log[0], child]))
    assert log[0]["parent"] is None and log[0]["change_record"] is None


# --- Stage A's output --------------------------------------------------------------------------


def test_regenerating_reproduces_every_committed_file(loaded: model.Model, tmp_path: Path) -> None:
    files = generate.render(loaded)
    assert set(files) == {
        "core/vocab.py", "core/_model/__init__.py", "core/_model/qualifiers.py",
        "core/_model/names.py", "core/_model/sql.py", "core/_model/validators.py",
        "core/_model/revision.py",
    }  # fmt: skip
    assert generate.drift(files) == []
    generate.write(files, tmp_path)
    edited = tmp_path / "core/vocab.py"
    edited.write_text(edited.read_text().replace('"supposed"', '"supposd"'), encoding="utf-8")
    assert generate.drift(files, tmp_path) == ["core/vocab.py"]  # a hand edit fails


_TM_11 = (
    # the vocab.py sets of F2b, as they were
    "VersionState SchemaClassKind EntityScope SlotRole RuleGroup RuleSeverity MethodFamily "
    "MethodTier PolicyChain RunKind RunStatus EmbeddingTarget TaskUnitType TaskStatus "
    "ObservationKind ObservationOutcome AliasKind StatementRole ClaimStatus Establishment "
    "EvidenceRole LinkType MeasurementScope InterventionKind ExperimentDecision DocumentSplit "
    "GoldenSplit GoldenUnitStatus GoldenPass GoldenItemType AlignmentTarget AlignmentTier "
    "ResultTier "
    # TM §11's additions
    "ClaimModality Polarity ScopeExtent EntityExtent BindKind ParseOutcome DelimitingStatus "
    "SegmentKind Stage SkipReason MarkupKind InterventionTargetKind JudgmentTargetKind "
    "JudgmentDecision JudgmentConfidence VerificationVerdict DropReason FrameFailureReason "
    "ConfidenceSource ConfidenceState StatementKind GpuMode AgentMode"
)
TM_11 = _TM_11.split()


def test_every_modelled_closed_set_is_generated() -> None:
    missing = [name for name in TM_11 if not isinstance(getattr(vocab, name, None), type)]
    assert missing == []
    assert not hasattr(vocab, "SegmentParseStatus")  # merged into DelimitingStatus
    assert "gaps" in vocab.PolicyChain and "span" in vocab.TaskUnitType
    assert [m.value for m in vocab.SkipReason] == [
        "scope", "limit", "budget", "prerequisite_failed", "run_cancelled"
    ]  # fmt: skip
    assert (
        vocab.LIFECYCLE[vocab.ClaimModality]
        == vocab.LIFECYCLE[vocab.StatementKind]
        == (vocab.Lifecycle.SCHEMA_VERSION)
    )
    assert vocab.LIFECYCLE[vocab.SegmentKind] is vocab.Lifecycle.STATIC


def test_member_properties_are_the_declared_sets() -> None:
    K, M = vocab.SegmentKind, vocab.ClaimModality
    assert {M.SUPPOSED} == vocab.PREMISE_FORMING
    assert {M.CITED} == vocab.ATTRIBUTION_IDENTIFYING
    assert {M.ASSERTED, M.DEFINED} == vocab.CONFLICT_BEARING
    assert set(vocab.StatementKind) - {"proof", "solution"} == vocab.CLAIM_BEARING
    assert {K.UNIT, K.DETAILS} == vocab.STATEMENT_ANCHOR
    assert {K.PARAGRAPH, K.HEADING, K.LIST_ITEM, K.CAPTION} == vocab.SEARCH_BLOCK
    assert {K.DOCUMENT, K.SECTION} == vocab.SECTION_LIKE and {K.HEADING} == vocab.SECTION_LABEL
    assert {K.SENTENCE} == vocab.CITABLE_SENTENCE
    # the email kinds carry roles (TM §11)
    assert K.EMAIL_MESSAGE in vocab.ANNOTATION_UNIT and K.EMAIL_MESSAGE in vocab.CONTAINER
    assert K.QUOTED_BLOCK in vocab.CONTAINER
    assert sql.SEARCH_BLOCK_IN == "('paragraph', 'list_item', 'heading', 'caption')"


def test_the_core_qualifier_specifications() -> None:
    """D1 §5.2 and TM §8, written out."""
    expected = {
        "core:modality": ("identity", None, vocab.ClaimModality.ASSERTED, "member", "column"),
        "core:polarity": ("identity", None, vocab.Polarity.POSITIVE, "member", "column"),
        "core:hedge": ("meaning", None, qualifiers.MISSING, "text_form", "json"),
        "core:attribution": ("meaning", "attribution_identifying", qualifiers.MISSING,
                             "entity_key", "column"),
        "core:conditions": ("identity", None, qualifiers.MISSING, "condition", "json"),
        "core:scope": ("meaning", None, qualifiers.MISSING, "scope", "json"),
        "core:valid_time": ("identity", None, qualifiers.MISSING, "interval", "json"),
    }  # fmt: skip
    got = {
        q.name: (q.key_role, q.key_role_when, q.default, q.canonical, q.store)
        for q in qualifiers.CORE_QUALIFIERS
    }
    assert got == expected
    assert all(q.case == "fold" for q in qualifiers.CORE_QUALIFIERS)
    assert qualifiers.BY_NAME["core:scope"].range == "StoredScope"
    assert tuple(expected) == names.STORED_QUALIFIERS
    assert names.LOCAL_TO_PREFIXED["proves"] == "core:proves"
    assert names.PREFIXED_TO_LOCAL["core:Statement"] == "Statement"


def test_generated_validators_apply_the_declared_templates() -> None:
    class Row:
        def __init__(self, **kw: object) -> None:
            self.__dict__.update(kw)

    validators.kb_segment(Row(start_offset=2, end_offset=2, parse_status="ok", parse_reason=None))
    with pytest.raises(ValueError, match="parse_reason is absent exactly when parse_status is ok"):
        validators.kb_segment(
            Row(start_offset=0, end_offset=1, parse_status="ok", parse_reason="x")
        )
    with pytest.raises(ValueError, match="start_offset 3 > end_offset 2"):
        validators.kb_segment(
            Row(start_offset=3, end_offset=2, parse_status="ok", parse_reason=None)
        )
    with pytest.raises(ValueError, match="empty or reversed"):
        validators.span(Row(start_offset=2, end_offset=2))
    validators.citation_frame(Row(version=1, parent=None))
    with pytest.raises(ValueError, match="parent is absent exactly when version is 1"):
        validators.citation_frame(Row(version=2, parent=None))
    with pytest.raises(ValueError, match="resolved_to is given only when type"):
        validators.kb_entity(Row(scope="global", scope_segment=None, type="stat:T", kind=None,
                                 resolved_to=7))  # fmt: skip
    assert validators.INVARIANTS["KbSegment"] == (
        "iff_absent(parse_reason, parse_status = ok)", "ordered_eq(start_offset, end_offset)"
    )  # fmt: skip
