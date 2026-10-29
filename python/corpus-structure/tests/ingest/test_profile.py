"""Source profiles (ingest and math §3.2, §6 P0-I-1a): loading, refusals, the schema-version check
and the agreement of the Matcher with the cssselect→XPath export."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cssselect2
import pytest
import yaml
from lxml.cssselect import CSSSelector

from corpus_structure.core.vocab import SegmentKind, StatementKind, SynthesisObject
from corpus_structure.ingest import profile as profiles
from corpus_structure.ingest.html import parse
from corpus_structure.ingest.profile import (
    BlockHint,
    CorpusIndex,
    DetailsKinds,
    ProfileError,
    ProfileIssue,
    SectionHint,
    SourceProfile,
    SynthesisRule,
    check_profile,
    compile_profile,
    load_profile,
    parse_profile,
)

REPO = Path(__file__).resolve().parents[4]
SYSTEM = REPO / "python/corpus-structure/src/corpus_structure/model/system.yaml"
VENDORED = REPO / "fixtures/trace/corpus/siegrist_random/random"
SPIKE_PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)


def siegrist_data() -> dict[str, Any]:
    return yaml.safe_load((REPO / "sources/siegrist.yaml").read_text(encoding="utf-8"))


def test_the_siegrist_profile_loads_typed_by_core_vocabulary() -> None:
    p = load_profile("siegrist")
    assert (p.version, p.root, p.language) == ("0.1.0", "siegrist_random/random", "english")
    assert p.index == CorpusIndex(
        file="../index/siegrist_sections.tsv", page="path", first_pass="first_pass"
    )
    assert p.sections == ("h3", "h4") and p.unit == "div.unit"
    assert {h.selector: h.statement_kind for h in p.block_hints}["p.Proof"] is StatementKind.PROOF
    assert all(isinstance(h.statement_kind, StatementKind) for h in p.block_hints)
    assert [h for h in p.block_hints if h.claim_bearing is not None] == [
        BlockHint(selector="p.app", statement_kind=StatementKind.REMARK, claim_bearing=False)
    ]
    assert {h.title: h.statement_kind for h in p.section_hints}["Computational Exercises"] is (
        StatementKind.EXERCISE
    )
    assert p.details_kinds.synthesize == (
        SynthesisRule(
            statement_kind=StatementKind.PROOF,
            predicate="core:proves",
            object=SynthesisObject.ENCLOSING_UNIT,
            evidence="summary",
        ),
        SynthesisRule(
            statement_kind=StatementKind.SOLUTION,
            predicate="core:proves",
            object=SynthesisObject.ENCLOSING_UNIT,
            evidence="summary",
        ),
    )
    assert p.orphan_text is SegmentKind.PARAGRAPH
    assert p.math.display_environments == ("align", "align*")
    assert p.math.page_macros == "div.latex"


def _system_class(data: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    return data["classes"][name]["attributes"]


@pytest.mark.parametrize(
    ("model_class", "shape"),
    [
        ("SourceProfile", SourceProfile),
        ("CorpusIndex", CorpusIndex),
        ("BlockHint", BlockHint),
        ("SectionHint", SectionHint),
        ("DetailsKinds", DetailsKinds),
        ("SynthesisRule", SynthesisRule),
    ],
)
def test_the_profile_model_has_the_system_classes_fields(model_class: str, shape: type) -> None:
    """Field for field, with required-ness (the model's interim guard compares more, P0-M-1)."""
    attributes = _system_class(yaml.safe_load(SYSTEM.read_text(encoding="utf-8")), model_class)
    assert list(shape.model_fields) == list(attributes)
    for name, slot in attributes.items():
        required = bool(slot.get("required") or slot.get("identifier"))
        assert shape.model_fields[name].is_required() == required, name


def test_an_invalid_selector_rejects_the_whole_profile() -> None:
    data = siegrist_data()
    data["block_hints"]["p.dfn["] = {"statement_kind": "definition"}
    with pytest.raises(ProfileError, match=r"p\.dfn\[.*does not compile"):
        parse_profile("broken", data)


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (
            lambda d: d["block_hints"].update({"p.Proof": {"statement_kind": "Proof"}}),
            "'Proof' is not a core statement kind",
        ),
        (
            lambda d: d["section_hints"].update({"Exercises": "core:Exercise"}),
            "'core:Exercise' is not a core statement kind",
        ),
        (lambda d: d["details_kinds"].update({"default": "prove"}), "'prove' is not a core"),
        (
            lambda d: d["details_kinds"]["synthesize"]["proof"].update({"predicate": "core:prove"}),
            "'core:prove' is not a core predicate",
        ),
        (
            lambda d: d["details_kinds"]["synthesize"]["proof"].update({"predicate": "proves"}),
            "not a prefixed predicate",
        ),
        (lambda d: d.update({"orphan_text": "para"}), "orphan_text"),
        (lambda d: d.update({"layout": "table.layout"}), "layout: Extra inputs are not permitted"),
        (lambda d: d.update({"applies_to": "nist/**/*.html"}), "must lie under root"),
    ],
)
def test_unknown_core_names_and_keys_are_refused_at_load(edit: Any, message: str) -> None:
    data = siegrist_data()
    edit(data)
    with pytest.raises(ProfileError, match=message):
        parse_profile("edited", data)


def test_a_pack_scoped_kind_loads_and_is_left_to_the_schema_version_check() -> None:
    data = siegrist_data()
    data["block_hints"]["p.lemma"] = {"statement_kind": "stat:lemma"}
    data["details_kinds"]["synthesize"]["stat:lemma"] = {
        "predicate": "stat:supports",
        "object": "enclosing_unit",
        "evidence": "summary",
    }
    p = parse_profile("pack", data)
    assert {h.selector: h.statement_kind for h in p.block_hints}["p.lemma"] == "stat:lemma"


@dataclass(frozen=True)
class SchemaVersion:
    """A hand-made compiled schema version: core members plus one pack-scoped kind."""

    statement_kinds: Collection[str]
    predicates: Collection[str]


CORE_AND_LEMMA = SchemaVersion({k.value for k in StatementKind} | {"stat:lemma"}, {"core:proves"})


def test_check_profile_passes_kinds_the_version_has_and_reports_those_it_lacks() -> None:
    assert check_profile(load_profile("siegrist"), CORE_AND_LEMMA) == ()
    data = siegrist_data()
    data["block_hints"]["p.lemma"] = {"statement_kind": "stat:lemma"}
    data["block_hints"]["p.axiom"] = {"statement_kind": "stat:axiom"}
    data["details_kinds"]["synthesize"]["stat:lemma"] = {
        "predicate": "stat:supports",
        "object": "enclosing_unit",
        "evidence": "summary",
    }
    issues = check_profile(parse_profile("pack", data), CORE_AND_LEMMA)
    assert issues == (
        ProfileIssue("unknown_statement_kind", "block_hints[p.axiom].statement_kind", "stat:axiom"),
        ProfileIssue(
            "unknown_predicate", "details_kinds.synthesize[stat:lemma].predicate", "stat:supports"
        ),
    )


def test_check_profile_reports_a_core_kind_a_version_does_not_carry() -> None:
    version = SchemaVersion({k.value for k in StatementKind} - {"solution"}, {"core:proves"})
    names = {issue.name for issue in check_profile(load_profile("siegrist"), version)}
    assert names == {"solution"}


def test_a_profile_name_is_a_file_name_under_sources(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="lower-case"):
        load_profile("../siegrist")
    with pytest.raises(ProfileError, match="cannot be read"):
        load_profile("absent", tmp_path)
    assert profiles.SOURCES_DIR == REPO / "sources"


@pytest.mark.parametrize("page", SPIKE_PAGES)
def test_the_matcher_and_the_xpath_export_select_the_same_nodes_per_rule(page: str) -> None:
    compiled = compile_profile(load_profile("siegrist"))
    root, _ = parse((VENDORED / page).read_bytes())
    wrappers = list(cssselect2.ElementWrapper.from_html_root(root).iter_subtree())
    for selector, rule in compiled.rules:
        by_matcher = {w.etree_element for w in wrappers if rule in compiled.match(w)}
        by_xpath = set(CSSSelector(selector, translator="html")(root))
        assert by_matcher == by_xpath, (selector, rule.role)
