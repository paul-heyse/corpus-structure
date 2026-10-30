"""T2 (stored batch -> keyed candidate set) and T4 (candidate -> rule view) (P0-S-2; §3.6, §6).

- **T2.** The adapter agrees with foundations' T2 declaration applied mechanically
  (`tests/core/translate.py`) on real stored batches; an `outside` item reaches the set as an
  `ExternalReference` node, never as `None`; math delimiters are normalized.
- **T4 completeness.** Every field of each candidate type is mapped to view attributes or declared
  omitted, and every attribute of the compiled claim-view language is filled by a mapped field or
  declared introduced (DP-08).
- **Cross-claim facts.** The six readings P2's engines implement, the linear index (counted reads,
  not timing), the finalize readings, and the bound on a pathological formula with
  `methods.math` never imported.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import typing
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core import candidates as C
from corpus_structure.core import values as V
from corpus_structure.core.batch import StoredBatch
from corpus_structure.core.candidates import AWAITING, UNKEYED, KeyedCandidateSet
from corpus_structure.core.translations import Omitted
from corpus_structure.core.vocab import MathKind, ParseOutcome
from corpus_structure.schema.compile import CompiledSchema
from corpus_structure.schema.tables import expand_applies_to
from corpus_structure.validate.adapter import candidates_from_batch, normalize_delimiters
from corpus_structure.validate.runner import run_rules
from corpus_structure.validate.views import (
    OBJECT_PATH,
    T4,
    Reading,
    build_views,
    defined_symbol,
    index_symbols,
)

HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load("validate_support", HERE / "support.py")
translate = _load("validate_translate", HERE.parent / "core/translate.py")
REN = "ren:" + "0" * 32


def stored_model(stats: CompiledSchema, raw: dict[str, Any]) -> Any:
    return stats.batches.validate(json.dumps(raw), "stored")


# --- T2 -----------------------------------------------------------------------------------------


@pytest.mark.parametrize("unit", support.V1_UNITS)
def test_the_adapter_agrees_with_the_t2_declaration(stats: CompiledSchema, unit: str) -> None:
    raw = support.stored_v1(unit, stats)
    raw["rendition"] = raw.get("rendition", REN)
    batch = stored_model(stats, raw)
    ours = candidates_from_batch(batch, stats)
    declared = translate.candidate_set(StoredBatch.model_validate(raw))
    assert ours.model_dump(mode="json") == declared.model_dump(mode="json")


def test_an_outside_item_is_an_external_reference_and_never_none(stats: CompiledSchema) -> None:
    raw, _ = support.stored_s0("U6")
    cs = candidates_from_batch(stored_model(stats, raw), stats)
    (ref,) = cs.references
    assert (ref.id, ref.key, ref.resolved_to) == ("e_last_result", UNKEYED, AWAITING)
    assert all(s.id != "e_last_result" for s in cs.statements)
    view = next(v for v in build_views(cs, stats, "batch") if v.id == "c_follows")
    assert view.object is not None and view.object.type == "core:ExternalReference"


def test_math_delimiters_are_normalized_and_the_latex_kept(stats: CompiledSchema) -> None:
    assert {
        normalize_delimiters(x)
        for x in ("$a + b$", "\\(a + b\\)", "\\[ a + b \\]", "$$a + b$$", "a + b")
    } == {"a + b"}
    assert normalize_delimiters("$a$ and $b$") == "$a$ and $b$"
    raw = support.stored_v1("T3", stats)
    c = next(c for c in raw["claims"] if c["local_ref"] == "c_aX_def")
    c["object"]["latex"] = "\\(" + c["object"]["latex"] + "\\)"
    cs = candidates_from_batch(stored_model(stats, raw), stats)
    claim = next(c for c in cs.claims if c.id == "c_aX_def")
    assert isinstance(claim.object, V.Formula)
    assert claim.object.latex == "a + b X"


# --- T4 completeness ----------------------------------------------------------------------------


def _source_fields(source: str) -> set[str]:
    if source == "StoredValue":
        members = typing.get_args(typing.get_args(V.StoredValue.__value__)[0])
        return {f for m in members for f in m.model_fields}
    return set(getattr(C, source).model_fields)


def test_t4_maps_every_candidate_field_and_fills_every_view_attribute(
    stats: CompiledSchema,
) -> None:
    problems = []
    filled: dict[str, set[str]] = {}
    for m in T4:
        source = _source_fields(m.source)
        if set(m.fields) != source:
            problems.append(
                f"{m.source}: unmapped {sorted(source - set(m.fields))}, "
                f"not a field {sorted(set(m.fields) - source)}"
            )
        out = filled.setdefault(m.target, set(m.introduced))
        out |= set(m.introduced)
        for image in m.fields.values():
            if not isinstance(image, Omitted):
                out |= {image} if isinstance(image, str) else set(image)
    assert problems == []
    language = stats.rules.claim.languages["finalize"]
    views = set(stats.rules.claim.views)
    for target, attrs in filled.items():
        expected = set(language.objects[target]) - (views if target == "Claim" else set())
        assert attrs - {"<views:>"} == expected, target


def test_every_view_attribute_is_readable_at_both_sites(stats: CompiledSchema) -> None:
    raw, _ = support.stored_s0("T3")
    cs = candidates_from_batch(stored_model(stats, raw), stats)
    for site in ("batch", "finalize"):
        language = stats.rules.claim.languages[site]
        for view in build_views(cs, stats, site):
            for attr in language.objects["Claim"]:
                getattr(view, attr)
            for attr in language.objects["Qualifiers"]:
                getattr(view.qualifiers, attr)
            if view.value is not None:
                for attr in language.objects["Value"]:
                    getattr(view.value, attr)


# --- Cross-claim facts: the six readings ---------------------------------------------------------


def _entities() -> list[dict[str, Any]]:
    return [
        {
            "id": "X",
            "type": "stat:RandomVariable",
            "label": "X",
            "scope": "local",
            "extent": "statement",
            "scope_segment": "seg:x",
            "symbol": "X_i",
        },
        {"id": "F", "type": "stat:DistributionFamily", "label": "normal", "scope": "global"},
        {
            "id": "P",
            "type": "stat:FamilyParameter",
            "label": "mean of F",
            "scope": "global",
            "identity": {"stat:family": "F", "stat:canonical_name": "mean"},
        },
    ]


def _claim(id_: str, predicate: str, subject: str, obj: dict[str, Any], **kw: Any) -> dict:
    return {"id": id_, "predicate": predicate, "subject": subject, "object": obj, **kw}


def _set(claims: list[dict[str, Any]], **kw: Any) -> KeyedCandidateSet:
    return KeyedCandidateSet.model_validate(
        {
            "renditions": [REN],
            "entities": _entities(),
            "claims": claims,
            "statements": [{"id": "st", "kind": "theorem", "anchor": ["seg:x"]}],
            **kw,
        }
    )


def _views(stats: CompiledSchema, cs: KeyedCandidateSet) -> dict[str, Any]:
    return {v.id: v for v in build_views(cs, stats, "finalize")}


def test_same_slot_counts_two_statementless_claims_as_one_statement(stats: CompiledSchema) -> None:
    cs = _set(
        [
            _claim("a", "stat:has_distribution", "X", {"ref": "F"}),
            _claim("b", "stat:has_distribution", "X", {"ref": "F"}),
            _claim("c", "stat:has_distribution", "X", {"ref": "F"}, statement="st"),
        ]
    )
    v = _views(stats, cs)
    assert (v["a"].same_slot, v["b"].same_slot, v["c"].same_slot) == (("b",), ("a",), ())


def test_alternative_of_lists_only_claims_of_the_input(stats: CompiledSchema) -> None:
    cs = _set(
        [
            _claim("a", "stat:has_distribution", "X", {"ref": "F"}),
            _claim("b", "stat:has_distribution", "X", {"ref": "F"}),
        ],
        alternatives=[{"refs": ["a", "b", "gone"], "reason": "either"}],
    )
    v = _views(stats, cs)
    assert (v["a"].alternative_of, v["b"].alternative_of) == (("b",), ("a",))


def test_views_facts_read_every_claim_given_and_only_input_entities(stats: CompiledSchema) -> None:
    claims = [
        _claim("d", "stat:has_distribution", "X", {"ref": "F"}),
        _claim("hp", "stat:has_parameter", "F", {"ref": "P"}),
        # the caller's filter decides statuses: every source claim given is read
        _claim("hp_st", "stat:has_parameter", "F", {"ref": "st"}),  # a statement: no entity
        _claim("e", "stat:has_distribution", "X", {"ref": "P"}),  # applicable, nothing matches
        _claim("hp2", "stat:has_parameter", "X", {"ref": "P"}),  # not applicable
    ]
    v = _views(stats, _set(claims))
    assert v["d"].family_params == ("mean",)
    assert v["e"].family_params == ()  # every applicable claim has the fact, empty when unmatched
    assert v["hp2"].family_params == ()
    applies = set(expand_applies_to(stats.lookup, "stat:has_distribution"))
    assert {c.predicate for c in _set(claims).claims if c.id in ("d", "e")} <= applies


def test_views_are_served_from_one_index_linear_in_claims(stats: CompiledSchema) -> None:
    n = 5000
    entities = []
    claims = []
    for i in range(n):
        entities += [
            {
                "id": f"X{i}",
                "type": "stat:RandomVariable",
                "label": "X",
                "scope": "local",
                "extent": "statement",
                "scope_segment": "seg:x",
            },
            {"id": f"F{i}", "type": "stat:DistributionFamily", "label": f"f{i}", "scope": "global"},
            {
                "id": f"P{i}",
                "type": "stat:FamilyParameter",
                "label": f"p{i}",
                "scope": "global",
                "identity": {"stat:family": f"F{i}", "stat:canonical_name": f"p{i}"},
            },
        ]
        claims += [
            _claim(f"hp{i}", "stat:has_parameter", f"F{i}", {"ref": f"P{i}"}),
            _claim(f"d{i}", "stat:has_distribution", f"X{i}", {"ref": f"F{i}"}),
        ]
    cs = KeyedCandidateSet.model_validate(
        {"renditions": [REN], "entities": entities, "claims": claims}
    )
    views = build_views(cs, stats, "finalize")
    assert len(views) == 2 * n
    values = [v.family_params for v in views]
    assert values[1] == ("p0",) and values[-1] == (f"p{n - 1}",)
    assert views.cross.built == {"family_params": n}  # the source claims, indexed once
    assert views.cross.reads == n  # one lookup per applicable view, no scan


# --- Token-derived facts and readings ------------------------------------------------------------


def test_token_derived_symbol_facts() -> None:
    assert index_symbols("X_i") == ("i",) and index_symbols("X_{ij}") == ("i", "j")
    assert index_symbols("X") == () and index_symbols(None) == ()
    assert defined_symbol("Y = a + b X") == "Y" and defined_symbol("\\mu_1 = 0") == "\\mu_1"
    assert defined_symbol("a + b X") is None and defined_symbol("x == y") is None
    assert defined_symbol("x \\leq 1") is None


def _value_claims() -> list[dict[str, Any]]:
    return [
        _claim("f_ok", "stat:defined_as", "X", {"t": "formula", "latex": "a"}),
        _claim("f_set", "stat:defined_as", "X", {"t": "formula", "latex": "\\R"}),
        _claim("f_rel", "stat:defined_as", "X", {"t": "formula", "latex": "a < b"}),
        _claim("s_form", "stat:support", "X", {"t": "set", "latex": "a + b"}),
        _claim("dom_ok", "stat:parameter_domain", "P", {"t": "set", "latex": "\\R"}),
        _claim("dom_bad", "stat:parameter_domain", "P", {"t": "set", "latex": "\\frac{"}),
        _claim("dom_none", "stat:parameter_domain", "P", {"t": "set", "latex": "(0, 1)"}),
    ]


READINGS = {
    ("f_ok", OBJECT_PATH): Reading(ParseOutcome.OK, MathKind.FORMULA),
    ("f_set", OBJECT_PATH): Reading(ParseOutcome.OK, MathKind.SET),  # a set in a Formula slot
    ("f_rel", OBJECT_PATH): Reading(ParseOutcome.OK, MathKind.RELATION),  # a relation
    ("s_form", OBJECT_PATH): Reading(ParseOutcome.OK, MathKind.FORMULA),  # a formula as a set
    ("dom_ok", OBJECT_PATH): Reading(ParseOutcome.OK, MathKind.SET),
    ("dom_bad", OBJECT_PATH): Reading(ParseOutcome.FAILED),
}


def test_the_reading_rules_on_hand_made_readings(stats: CompiledSchema) -> None:
    cs = _set(_value_claims())
    views = build_views(cs, stats, "finalize", READINGS)
    outcome = run_rules(views, stats, "finalize").by_rule()
    assert outcome["core.value_kind_matches_slot"] == {"f_set", "f_rel", "s_form"}
    assert outcome["stat.domain_is_set"] == {"dom_bad", "dom_none"}  # unread: no parse status
    batch = run_rules(build_views(cs, stats, "batch", READINGS), stats, "batch").by_rule()
    assert "core.value_kind_matches_slot" not in batch and "stat.domain_is_set" not in batch


BOUND_SCRIPT = """
import json, sys, time
sys.path.insert(0, {here!r})
from validate_bound import run
start = time.perf_counter()
run()
math = [m for m in sys.modules if m.startswith("corpus_structure.methods.math")]
print(json.dumps({{"seconds": time.perf_counter() - start, "math": math}}))
"""


def test_a_pathological_formula_completes_the_batch_site_without_the_grammar(
    tmp_path: Path,
) -> None:
    (tmp_path / "validate_bound.py").write_text(
        f"""
import copy, importlib.util, sys
spec = importlib.util.spec_from_file_location("validate_support", {str(HERE / "support.py")!r})
support = importlib.util.module_from_spec(spec)
sys.modules["validate_support"] = support
spec.loader.exec_module(support)
from corpus_structure.schema.compile import compile_paths
from corpus_structure.validate.runner import check_stored

def run():
    stats = compile_paths([support.REPO / "domains/statistics"])
    batch, _, _ = support.s0("T3")
    b = copy.deepcopy(batch)
    claim = next(c for c in b["claims"] if c["local_ref"] == "c_aX_def")
    claim["object"]["latex"] = "Y = " + "{{" * 20000 + "a + b X" + "}}" * 20000 + "^" * 5000
    out = check_stored(support.spanless_stored(b, stats), stats)
    assert out.report.ok and out.rules is not None, out.report.lines()
    assert any(f.rule == "guideline.formula_excludes_defined_variable" for f in out.rules.findings)
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-c", BOUND_SCRIPT.format(here=str(tmp_path))],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["math"] == []  # validate never imports the grammar (P0CL-14)
    assert out["seconds"] < 30.0  # the bound includes compiling the version in a cold process


# --- Precomputed pool facts (P2's `views` step) --------------------------------------------------


def _pool_facts(views: Any, names: list[str]) -> list[tuple[Any, ...]]:
    return [(v.id, v.same_slot, v.alternative_of, *(getattr(v, n) for n in names)) for v in views]


@pytest.mark.parametrize("engine_name", ["python", "duckdb"])
def test_the_engines_facts_give_the_same_views_as_the_builders_own(
    stats: CompiledSchema, engine_name: typing.Literal["python", "duckdb"]
) -> None:
    from corpus_structure.pool.harness import engine as make_engine
    from corpus_structure.validate.views import engine_facts

    engine = make_engine(engine_name)
    names = list(stats.rules.claim.views)
    sets = [
        _set(
            [
                _claim("d", "stat:has_distribution", "X", {"ref": "F"}),
                _claim("d2", "stat:has_distribution", "X", {"ref": "F"}),
                _claim("hp", "stat:has_parameter", "F", {"ref": "P"}),
                _claim("hp_st", "stat:has_parameter", "F", {"ref": "st"}),
                _claim("e", "stat:has_distribution", "X", {"ref": "P"}, statement="st"),
            ],
            alternatives=[{"refs": ["d", "d2", "gone"], "reason": "either"}],
        )
    ]
    for unit in support.V1_UNITS:
        raw = support.stored_v1(unit, stats)
        sets.append(candidates_from_batch(stored_model(stats, raw), stats))
    for cs in sets:
        own = build_views(cs, stats, "finalize")
        facts = engine_facts(engine, cs, stats)
        given = build_views(cs, stats, "finalize", facts=facts)
        assert _pool_facts(given, names) == _pool_facts(own, names)
    close = getattr(engine, "close", None)
    if close is not None:
        close()


@pytest.mark.parametrize("site", ["batch", "finalize"])
def test_rule_qualifier_defaults_equal_explicit_members(stats: CompiledSchema, site: str) -> None:
    omitted = _claim("structural", "core:proves", "st", {"ref": "st"})
    explicit = {**omitted, "qualifiers": {"core:modality": "asserted", "core:polarity": "positive"}}
    outcomes = []
    for claim in (omitted, explicit):
        views = build_views(_set([claim]), stats, site)
        qualifiers = views[0].qualifiers
        # The rule language declares STRING, not Python enum objects. Native
        # rule-engine evaluation must receive the same primitives for both forms.
        modality, polarity = vars(qualifiers)["modality"], vars(qualifiers)["polarity"]
        assert type(modality) is str and modality == "asserted"
        assert type(polarity) is str and polarity == "positive"
        outcomes.append(run_rules(views, stats, site))
    assert outcomes[0] == outcomes[1]
    assert outcomes[0].findings == ()
