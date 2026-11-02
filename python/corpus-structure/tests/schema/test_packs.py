"""Pack validity, pure lookup/key metadata and current composed release artifacts.

External V1 batch and installed CompiledSchema registry controls retired with those APIs.
Independent current reference/evidence controls live in semantic/test_trace_reference_fixture.py,
semantic/test_reference_positions.py and semantic/test_domain_operations.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any
from dataclasses import dataclass
from corpus_structure.core.keys import KeySchema

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
from corpus_structure.schema.lookup import SchemaLookup, build_lookup, compile_key_schema, name_map
from corpus_structure.schema.pack import CORE_RULES, PackError, load_pack, schema_version

REPO = Path(__file__).resolve().parents[4]
STATISTICS = REPO / "domains" / "statistics"
MINIMAL = REPO / "fixtures" / "packs" / "minimal"
S0R2 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s0r2"
REN = "ren:" + "0" * 32  # a rendition reference (D1 §10.1)
UNITS = ("T1", "T2", "T3", "T4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12")


@dataclass(frozen=True)
class PackComponents:
    packs: tuple
    lookup: SchemaLookup
    key_schema: KeySchema


def components(path: Path) -> PackComponents:
    packs = (load_pack(path),)
    lookup = build_lookup(packs)
    return PackComponents(packs, lookup, compile_key_schema(lookup, 1))


@pytest.fixture(scope="module")
def stats() -> PackComponents:
    return components(STATISTICS)


def copy_pack(tmp_path: Path, src: Path = STATISTICS) -> Path:
    dst = tmp_path / src.name
    shutil.copytree(src, dst)
    return dst


# --- The schema version and determinism --------------------------------------------------------

HASHES = (
    "import sys; from pathlib import Path\n"
    "from corpus_structure.semantic.regeneration import prepare_packs\n"
    "c = prepare_packs((Path(sys.argv[1]),))[3]\n"
    "print(c.release_id, *(a.digest for a in c.artifacts))"
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
    assert absolute == relative and absolute.split()[0].startswith("release:")


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


# --- KeySchema, names and generality ------------------------------------------------------------


def test_the_compiled_key_schema_is_the_packs(stats: PackComponents) -> None:
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


def test_two_packs_sharing_a_local_name_are_refused_with_both_names() -> None:
    with pytest.raises(PackError) as caught:
        name_map([load_pack(STATISTICS), load_pack(MINIMAL)])
    assert caught.value.problems == [
        "local name 'has_parameter' names min:has_parameter and stat:has_parameter"
        " in one schema version"
    ]


def test_the_name_map_round_trips_every_element(stats: PackComponents) -> None:
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
    assert out["packs"] == ["statistics"] and out["release_id"].startswith("release:")
    assert out["execution_model_id"] is not None and out["artifacts"]
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "sources").is_dir()
    assert len(list(tmp_path.glob("*.artifact"))) == len(out["artifacts"])
    refused = cli("schema", "compile", "--domains", str(tmp_path), "--domain", "nothere")
    assert refused.exit_code == 1 and "semantic.yaml" in refused.stderr
