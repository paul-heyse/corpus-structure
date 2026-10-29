"""Packs, the schema version, the lookup, `KeySchema`, the name map and the compilers (P0-S-1).

Schema and rules §3.1 to §3.3, §6. The external batches (the S0-R2 v1 reference in both forms, the
worked examples, `fixtures/s0`) are the independent control (coordinator decision 24): authored by
people and agents against the guideline, not derived from these compilers. jsonschema agreeing with
Pydantic on the exported schemas is **derivation conformance**, not an independent oracle: both
judge one model's projection, so a shared mistake passes both. Expectations about the pack
(identity roles, case policies, reference items) are written by hand from the pack files.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis_jsonschema import from_schema
from jsonschema import Draft7Validator, Draft202012Validator
from pydantic import ValidationError
from referencing import Registry, Resource

from corpus_structure.core.batch import StoredQualifiers
from corpus_structure.core.candidates import KeyedCandidateSet
from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind, document_key
from corpus_structure.core.keys import KeyContext, LabelRules, key_claims
from corpus_structure.core.vocab import CanonicalForm, CaseRule, KeyRole
from corpus_structure.schema.batches import decoding_problems
from corpus_structure.schema.compile import CompiledSchema, compile_paths, compile_schema
from corpus_structure.schema.lookup import name_map
from corpus_structure.schema.pack import CORE_RULES, PackError, load_pack, schema_version

REPO = Path(__file__).resolve().parents[4]
STATISTICS = REPO / "domains" / "statistics"
MINIMAL = REPO / "fixtures" / "packs" / "minimal"
S0R2 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s0r2"
UNITS = ("T1", "T2", "T3", "T4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12")


@pytest.fixture(scope="module")
def stats() -> CompiledSchema:
    return compile_paths([STATISTICS])


@pytest.fixture(scope="module")
def minimal() -> CompiledSchema:
    return compile_paths([MINIMAL])


def copy_pack(tmp_path: Path, src: Path = STATISTICS) -> Path:
    dst = tmp_path / src.name
    shutil.copytree(src, dst)
    return dst


# --- The schema version and determinism --------------------------------------------------------

HASHES = (
    "import sys; from pathlib import Path\n"
    "from corpus_structure.schema.compile import compile_paths\n"
    "c = compile_paths([Path(sys.argv[1])])\n"
    "print(c.schema_version, *(a.hash for a in c.artifacts))"
)


def test_hashes_are_equal_across_processes_hash_seeds_and_load_paths(tmp_path: Path) -> None:
    def run(path: str, cwd: Path, seed: str) -> str:
        env = {**os.environ, "PYTHONHASHSEED": seed}
        out = subprocess.run(
            [sys.executable, "-c", HASHES, path],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout

    absolute = run(str(STATISTICS), tmp_path, "1")
    relative = run("domains/statistics", REPO, "2")
    assert absolute == relative and len(absolute.split()) == 6


def test_the_version_covers_parsed_content_and_the_model_revision(tmp_path: Path) -> None:
    pack = copy_pack(tmp_path)
    base = schema_version([load_pack(pack)], CORE_RULES, "rev-a")
    assert schema_version([load_pack(pack)], CORE_RULES, "rev-b") != base  # a model revision
    schema = pack / "schema" / "statistics.yaml"
    text = schema.read_text(encoding="utf-8")
    schema.write_text(
        "# a comment-only edit\n" + text.replace("\n", "  # x\n", 3), encoding="utf-8"
    )
    assert schema_version([load_pack(pack)], CORE_RULES, "rev-a") == base
    schema.write_text(text.replace("Statistics schema v0", "Statistics schema v0, edited"))
    assert schema_version([load_pack(pack)], CORE_RULES, "rev-a") != base  # a description edit


def test_yaml_order_floats_and_dates(tmp_path: Path) -> None:
    pack = copy_pack(tmp_path, MINIMAL)
    rules = pack / "schema" / "rules.yaml"
    base = schema_version([load_pack(pack)], CORE_RULES, "r")
    data = rules.read_text(encoding="utf-8")
    reordered = "derive: []\ntables: {}\nguideline: []\n" + data.replace(
        "guideline: []\ntables: {}\nderive: []\n", ""
    )
    rules.write_text(reordered, encoding="utf-8")
    assert schema_version([load_pack(pack)], CORE_RULES, "r") == base
    rules.write_text(data.replace("tables: {}", "tables: {limits: {max: 0.5}}"), encoding="utf-8")
    with_float = load_pack(pack)
    assert with_float.rules_data["tables"]["limits"]["max"] == "0.5"  # its canonical decimal
    rules.write_text(data.replace("tables: {}", "tables: {limits: {since: 2026-01-31}}"))
    with pytest.raises(PackError, match="YAML date"):
        load_pack(pack)


# --- Pack validity ------------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("linkml-lint") is None, reason="blocked: linkml (dev) missing")
@pytest.mark.parametrize(
    "schema", [STATISTICS / "schema/statistics.yaml", MINIMAL / "schema/minimal.yaml"]
)
def test_each_pack_file_lints_clean(schema: Path, tmp_path: Path) -> None:
    # the pack imports `core`, which the loader maps to the model's file; lint sees it beside it
    shutil.copy(schema, tmp_path / schema.name)
    shutil.copy(REPO / "python/corpus-structure/src/corpus_structure/model/core.yaml", tmp_path)
    lint = shutil.which("linkml-lint")
    assert lint is not None
    out = subprocess.run(
        [lint, "--config", str(REPO / "domains/.linkmllint.yaml"), str(tmp_path / schema.name)],
        capture_output=True,
        text=True,
        check=False,
    )
    errors = [line for line in out.stdout.splitlines() if line.lstrip().startswith("error")]
    assert errors == [], out.stdout


def _edit(
    tmp_path: Path, old: str, new: str, src: Path = STATISTICS, file: str | None = None
) -> Path:
    pack = copy_pack(tmp_path, src)
    path = pack / "schema" / (file or f"{src.name}.yaml")
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return pack


@pytest.mark.parametrize(
    ("old", "new", "problem"),
    [
        (
            "ci:scope: global\n      ci:extract: mention\n\n  FamilyConstruction",
            "ci:scope: global\n      ci:colour: red\n\n  FamilyConstruction",
            "ci:colour is not in the declaration vocabulary",
        ),
        (
            "ci:qualifiers: param_values\n      ci:identity_qualifiers: param_values",
            "ci:qualifiers: param_values modality\n      ci:identity_qualifiers: param_values",
            "modality is a core qualifier",
        ),
        (
            "ci:qualifiers: base\n      ci:identity_qualifiers: base",
            "ci:qualifiers: base nowhere\n      ci:identity_qualifiers: base",
            "lists 'nowhere', which is no declared qualifier",
        ),
        (
            "ci:param_map: param_values",
            "ci:param_map: transform",
            "ci:param_map 'transform' is not a listed map qualifier",
        ),
        (
            "ci:parameter_class: family",
            "ci:parameter_class: symbol",
            "ci:parameter_class 'symbol' is no identity slot",
        ),
        (
            '    description: The transformation, as a formula in the base variable. "e^Y".\n'
            "    annotations: {ci:role: qualifier}",
            '    description: The transformation, as a formula in the base variable. "e^Y".\n'
            "    annotations: {ci:role: qualifier, ci:key_role: meaning}",
            "ci:key_role meaning contradicts transformation_of's ci:identity_qualifiers",
        ),
        (
            '    description: The transformation, as a formula in the base variable. "e^Y".\n'
            "    annotations: {ci:role: qualifier}",
            '    description: The transformation, as a formula in the base variable. "e^Y".\n'
            "    annotations: {ci:role: qualifier, ci:case: preserve}",
            "ci:case stands on a string-ranged slot",
        ),
        (
            "  ParameterRole:\n    description: The role a parameter plays in its family.",
            "  Sides:\n    description: Pack polarity.\n    inherits: [Polarity]\n"
            "    permissible_values: {neutral: {description: Neither.}}\n"
            "  ParameterRole:\n    description: The role a parameter plays in its family.",
            "extend Polarity, a static set",
        ),
        (
            "  ParameterRole:\n    description: The role a parameter plays in its family.",
            "  Kinds:\n    description: Pack kinds.\n    inherits: [StatementKind]\n"
            "    permissible_values: {theorem: {description: Again.}}\n"
            "  ParameterRole:\n    description: The role a parameter plays in its family.",
            "'theorem' collides with StatementKind's member",
        ),
    ],
)
def test_each_vocabulary_error_class_is_a_pack_error(
    tmp_path: Path, old: str, new: str, problem: str
) -> None:
    with pytest.raises(PackError) as caught:
        load_pack(_edit(tmp_path, old, new))
    assert any(problem in p for p in caught.value.problems), caught.value.problems


def test_rules_files_are_checked_for_structure(tmp_path: Path) -> None:
    pack = _edit(tmp_path, "tables: {}", "tables: {}\nmacros: {}", MINIMAL, "rules.yaml")
    with pytest.raises(PackError, match="macros: Extra inputs"):
        load_pack(pack)


# --- External data in both forms ------------------------------------------------------------------


def v1_canonical(raw: dict[str, Any]) -> dict[str, Any]:
    """S4's V1 and V2 rewrites: `{t: entity, ref}` becomes `{ref}`; a `Statement` in `entities[]`
    becomes an `outside` statement item (record `s4.batch-validation`)."""

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if node.get("t") == "entity" and set(node) == {"t", "ref"}:
                return {"ref": node["ref"]}
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    out = walk(copy.deepcopy(raw))
    out.pop("envelope", None)
    keep = []
    for e in out.get("entities", []):
        if e["type"] == "Statement":
            out.setdefault("statements", []).append(
                {"local_ref": e["local_ref"], "kind": "theorem", "anchor": "outside"}
            )
        else:
            keep.append(e)
    out["entities"] = keep
    return out


def prefixed_names(raw: dict[str, Any], compiled: CompiledSchema) -> dict[str, Any]:
    """A stored v1 batch with every schema element prefixed (X2-01), through the name map."""
    names = compiled.names
    b = v1_canonical(raw)
    for e in b["entities"]:
        e["type"] = names.prefixed(e["type"])
        e["identity"] = {names.prefixed(k): v for k, v in e.get("identity", {}).items()}
    for c in b.get("claims", []):
        c["predicate"] = names.prefixed(c["predicate"])
        c["qualifiers"] = {names.prefixed(k): v for k, v in c.get("qualifiers", {}).items()}
        if c["object"].get("t") == "enum":
            c["object"]["enum"] = names.prefixed(c["object"]["enum"])
    return b


@pytest.mark.parametrize("unit", UNITS)
def test_the_v1_reference_validates_in_both_forms(stats: CompiledSchema, unit: str) -> None:
    model = json.loads((S0R2 / "reference_model_v1" / f"{unit}.json").read_text(encoding="utf-8"))
    stats.batches.validate(json.dumps(v1_canonical(model)), "model")
    stored = json.loads((S0R2 / "reference_v1" / f"{unit}.json").read_text(encoding="utf-8"))
    stats.batches.validate(json.dumps(prefixed_names(stored, stats)), "stored")
    local = v1_canonical(stored)  # the stored form takes prefixed names only
    if local.get("claims"):
        with pytest.raises(ValidationError):
            stats.batches.validate(json.dumps(local), "stored")


def test_the_v1_forms_s4_rewrote_are_refused_at_their_path(stats: CompiledSchema) -> None:
    def errors(unit: str) -> list[str]:
        raw = (S0R2 / "reference_model_v1" / f"{unit}.json").read_text(encoding="utf-8")
        with pytest.raises(ValidationError) as caught:
            stats.batches.validate(raw, "model")
        return [".".join(map(str, e["loc"])) for e in caught.value.errors()]

    assert "claims.3.construction_formula.qualifiers.base_variable.t" in errors("T1")  # V1
    assert "entities.5.type" in errors("U6")  # V2: Statement in entities[]


@pytest.mark.parametrize("name", sorted(p.name for p in (REPO / "fixtures/s0").glob("*.json")))
def test_the_s0_batches_and_worked_examples_validate(stats: CompiledSchema, name: str) -> None:
    batch = json.loads((REPO / "fixtures/s0" / name).read_text(encoding="utf-8"))["batch"]
    stats.batches.validate(json.dumps(batch), "model")
    for example in stats.packs[0].examples:
        stats.batches.validate(json.dumps(example.batch), "model")


# --- Exported schemas (derivation conformance) ---------------------------------------------------


def test_every_exported_schema_checks_and_carries_its_id(stats: CompiledSchema) -> None:
    kinds = ("batch.model_facing", "batch.stored", "batch.decoding")
    resources = []
    for kind in kinds:
        schema = stats.artifact("json_schema", kind).body
        Draft202012Validator.check_schema(schema)
        assert schema["$id"].endswith(f"batch.{kind.split('.')[1]}.json")
        resources.append((schema["$id"], Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    for kind in kinds:
        assert registry.contents(stats.artifact("json_schema", kind).body["$id"])


def test_jsonschema_agrees_with_pydantic_on_the_external_batches(stats: CompiledSchema) -> None:
    validator = Draft202012Validator(stats.artifact("json_schema", "batch.model_facing").body)
    for unit in UNITS:
        raw = json.loads((S0R2 / "reference_model_v1" / f"{unit}.json").read_text(encoding="utf-8"))
        for batch in (raw, v1_canonical(raw)):
            try:
                stats.batches.validate(json.dumps(batch), "model")
                pydantic_ok = True
            except ValidationError:
                pydantic_ok = False
            errors = sorted(validator.iter_errors(batch), key=lambda e: list(e.absolute_path))
            assert pydantic_ok == (not errors), (unit, [e.message[:80] for e in errors[:3]])


def draft7(schema: dict[str, Any], depth: int = 2) -> dict[str, Any]:
    """A draft-7 copy for hypothesis-jsonschema, which resolves non-recursive references only:
    `$defs` become `definitions`, discriminators go, and the recursive condition definitions are
    unrolled `depth` levels, the last keeping only the leaf nodes."""
    defs = schema["$defs"]
    recursive = {
        n
        for n in defs
        if n.startswith("Authored")
        and n.removeprefix("Authored") in ("Condition", "And", "Or", "Not", "Forall")
    }
    out: dict[str, Any] = {}

    def rewrite(node: Any, level: int) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                if name in recursive:
                    return {"$ref": f"#/definitions/{name}_{min(level, depth)}"}
                return {"$ref": f"#/definitions/{name}"}
            return {k: rewrite(v, level) for k, v in node.items() if k != "discriminator"}
        if isinstance(node, list):
            return [rewrite(v, level) for v in node]
        return node

    for name, body in defs.items():
        if name not in recursive:
            out[name] = rewrite(body, 0)
    for level in range(depth + 1):
        for name in recursive:
            body = rewrite(defs[name], level + 1)
            if name == "AuthoredCondition" and level == depth:
                body = {
                    "oneOf": [
                        b for b in body["oneOf"] if not any(r in json.dumps(b) for r in recursive)
                    ]
                }
            out[f"{name}_{level}"] = body
    top = {k: rewrite(v, 0) for k, v in schema.items() if k not in ("$defs", "$schema", "$id")}
    return {"$schema": "http://json-schema.org/draft-07/schema#", "definitions": out, **top}


def test_the_draft7_copy_is_a_draft7_schema(stats: CompiledSchema) -> None:
    Draft7Validator.check_schema(draft7(stats.artifact("json_schema", "batch.model_facing").body))


@pytest.fixture(scope="module")
def drawn(stats: CompiledSchema) -> st.SearchStrategy[Any]:
    return from_schema(draft7(stats.artifact("json_schema", "batch.model_facing").body))


@settings(max_examples=15, deadline=None, suppress_health_check=list(HealthCheck))
@given(data=st.data())
def test_what_pydantic_accepts_of_schema_draws_satisfies_the_schema(
    stats: CompiledSchema, drawn: st.SearchStrategy[Any], data: st.DataObject
) -> None:
    instance = data.draw(drawn)
    validator = Draft202012Validator(stats.artifact("json_schema", "batch.model_facing").body)
    try:
        model = stats.batches.validate(json.dumps(instance), "model")
    except ValidationError:
        return  # a model rule the schema cannot state (local refs, spans, bindings)
    dumped = json.loads(stats.batches.adapters["model"].dump_json(model))
    assert not list(validator.iter_errors(dumped))


def test_the_decoding_form_passes_its_assertions(stats: CompiledSchema) -> None:
    decoding = stats.artifact("json_schema", "batch.decoding").body
    assert decoding_problems(decoding) == []
    seeded = copy.deepcopy(decoding)
    seeded["$defs"]["Formula"]["if"] = {"required": ["latex"]}
    assert decoding_problems(seeded) == ["#/$defs/Formula/if: forbidden keyword"]


# --- The reference ------------------------------------------------------------------------------

# The information items of S4's reference diff (`s4.reference-diff`), written from the S0-R2
# reference and the pack files: what an author must find in the reference.
REFERENCE_ITEMS = (
    "## 1. Entity types",
    "## 2. Predicates",
    "## 3. Statement roles and modality",
    "## 4. Qualifiers",
    "## 5. Enumerations",
    "## 6. Exact shapes",
    "## 7. Worked examples",
    "`DistributionFamily`",
    "`FamilyConstruction`",
    "`FamilyParameter`",
    "`RandomVariable`",
    "`Concept`",
    "family, canonical_name",
    "extent",
    "`has_distribution`",
    "`defined_as`",
    "`takes_values_in`",
    "`has_parameter`",
    "`parameter_role`",
    "`parameter_domain`",
    "`identical_parameter`",
    "`derived_parameter`",
    "`special_case_of`",
    "`transformation_of`",
    "`limit_of`",
    "`member_of_construction`",
    "`construction_formula`",
    "`support`",
    "`pdf`",
    "`cdf`",
    "`mgf`",
    "`mean_value`",
    "`variance_value`",
    "`definition_formula`",
    "`defines`",
    "`proves`",
    "`follows_from`",
    "`refers_to`",
    "`unschematized`",
    "symmetric",
    "transitive",
    "roles_by_kind",
    "modality_by_role",
    "premise: supposed",
    "definiens: defined",
    "`modality` (core)",
    "`polarity` (core)",
    "`conditions` (core)",
    "`param_values`",
    "`param_mapping`",
    "`param_symbols`",
    "`asserted`",
    "`positive`",
    "**ParameterRole:**",
    "**ClaimModality:**",
    "**StatementKind:**",
    "`ambiguous`",
    "`primary`",
    "`supporting`",
    "`condition`",
    "`independent`",
    "`identically_distributed`",
    "`iid`",
    '"op": "pred"',
    '"bind": "param_of"',
    '"sentence": "s1"',
    "### E1",
    "### E2",
    "### E3",
    "Packet:",
    "Batch:",
)


def test_the_reference_carries_every_information_item(stats: CompiledSchema) -> None:
    text = stats.artifact("annotator_reference", "reference").body
    missing = [item for item in REFERENCE_ITEMS if item not in text]
    assert missing == []
    for example in stats.packs[0].examples:
        assert example.packet.rstrip() in text


# --- KeySchema, names and generality ------------------------------------------------------------


def test_the_compiled_key_schema_is_the_packs(stats: CompiledSchema) -> None:
    roles = {
        s.name: (s.key_role, s.canonical)
        for specs in stats.key_schema.qualifiers.values()
        for s in specs
    }
    assert roles["stat:param_values"] == (KeyRole.IDENTITY, CanonicalForm.MAP)
    assert roles["stat:param_constraints"] == (KeyRole.IDENTITY, CanonicalForm.CONDITION)
    assert roles["stat:transform"] == (KeyRole.IDENTITY, CanonicalForm.TOKEN_FORM)
    assert roles["stat:base"] == (KeyRole.IDENTITY, CanonicalForm.ENTITY_KEY)
    for meaning in ("stat:param_mapping", "stat:limit", "stat:base_variable", "stat:param_symbols"):
        assert roles[meaning][0] is KeyRole.MEANING
    assert stats.key_schema.label_case == {"stat:RandomVariable": CaseRule.PRESERVE}
    assert stats.key_schema.slot_case == {"stat:canonical_name": CaseRule.PRESERVE}
    assert stats.key_schema.identity_keys == {
        "stat:FamilyParameter": ("stat:family", "stat:canonical_name")
    }
    assert stats.key_schema.entity_identity == {"stat:FamilyParameter": ("stat:family",)}
    assert stats.key_schema.symmetric_predicates == {
        "independent",
        "identically_distributed",
        "iid",
    }
    assert "core:proves" in stats.key_schema.predicates
    assert stats.key_schema.map_values["stat:ParamMapping"].canonical is CanonicalForm.IDENTIFIER
    assert stats.lookup.predicates["special_case_of"].transitive
    assert stats.lookup.predicates["identical_parameter"].symmetric


def test_a_pack_modality_extends_claim_modality_with_its_own_properties(
    minimal: CompiledSchema,
) -> None:
    """Core members keep their properties under their enum, pack members under theirs."""
    ks = minimal.key_schema
    assert ks.modality_properties["attribution_identifying"] == {"cited", "min:reported"}
    assert ks.modality_properties["premise_forming"] == {"supposed"}
    modalities = [m.stored for m in minimal.lookup.version_sets["ClaimModality"].members]
    assert modalities[-1] == "min:reported" and "reported" not in modalities
    assert StoredQualifiers.model_validate({"core:modality": "min:reported"})
    # the compiled KeySchema keys attribution under the pack modality
    text = "Run it."
    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=len(text))
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(sentence,))
    ctx = KeyContext(
        document_key("p", "x.html", "0" * 64),
        RenditionContent(canonical_text=text, document=root),
        "x.html",
    )

    def key(modality: str, who: str) -> str:
        cands = KeyedCandidateSet.model_validate(
            {
                "entities": [
                    {"id": n, "type": "min:Gadget", "label": n, "scope": "global"}
                    for n in ("G", who)
                ],
                "claims": [
                    {
                        "id": "c",
                        "predicate": "min:runs_at",
                        "subject": "G",
                        "object": {"t": "formula", "latex": "v"},
                        "evidence": [{"start": 0, "end": 1, "role": "primary"}],
                        "qualifiers": {"core:modality": modality, "core:attribution": {"ref": who}},
                    }
                ],
            }
        )
        return key_claims(cands, ctx, ks, LabelRules()).claims["c"]

    assert key("min:reported", "S") != key("min:reported", "J")
    assert key("asserted", "S") == key("asserted", "J")


def test_the_minimal_pack_compiles_to_every_artifact(minimal: CompiledSchema) -> None:
    assert {(a.compiler, a.kind) for a in minimal.artifacts} == {
        ("schema_tables", "tables"),
        ("json_schema", "batch.model_facing"),
        ("json_schema", "batch.stored"),
        ("json_schema", "batch.decoding"),
        ("annotator_reference", "reference"),
    }
    tables = minimal.artifact("schema_tables", "tables").body
    assert {"value": "min:instruction", "properties": ["claim_bearing"]} in tables["statement_kind"]
    assert any(r["rule_id"] == "min.settings_known" for r in tables["schema_rule"])
    assert minimal.key_schema.slot_case == {"min:setting_name": CaseRule.PRESERVE}
    stored = {
        "unit_ref": "E1",
        "statements": [{"local_ref": "st1", "kind": "min:instruction", "anchor": ["seg:x"]}],
    }
    minimal.batches.validate(json.dumps(stored), "stored")


def test_two_packs_sharing_a_local_name_are_refused_with_both_names() -> None:
    with pytest.raises(PackError) as caught:
        compile_schema([load_pack(STATISTICS), load_pack(MINIMAL)])
    assert caught.value.problems == [
        "local name 'has_parameter' names min:has_parameter and stat:has_parameter"
        " in one schema version"
    ]


def test_the_name_map_round_trips_every_element(stats: CompiledSchema) -> None:
    names = name_map(list(stats.packs))
    for local, prefixed in names.to_prefixed.items():
        assert names.local(prefixed) == local
    assert names.prefixed("has_distribution") == "stat:has_distribution"
    assert (
        names.prefixed("Statement") == "core:Statement"
        and names.prefixed("modality") == "core:modality"
    )


def test_ci_schema_compile_prints_the_artifacts(cli, tmp_path: Path) -> None:
    result = cli(
        "schema", "compile", "--domains", str(REPO / "domains"), "--json", "--out", str(tmp_path)
    )
    assert result.exit_code == 0, result.output
    out = json.loads(result.stdout)
    assert out["packs"] == ["statistics"] and len(out["artifacts"]) == 5
    assert (tmp_path / "annotator_reference.reference.md").exists()
    refused = cli("schema", "compile", "--domains", str(tmp_path), "--domain", "nothere")
    assert refused.exit_code == 1 and "no pack schema" in refused.stderr
