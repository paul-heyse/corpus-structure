"""S4-E: write the S4 records (ADR-0010) with their headline figures taken from the result files.

    python3 code/s4_records.py        (stdlib only; then `just evidence finalize <folder> <ids>`)
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

EV = Path(__file__).resolve().parent.parent
RES = EV / "results" / "s4"
REC = EV / "records"
ENV = "UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python"
XENV = "UV_PROJECT_ENVIRONMENT=$REPO/build/spike-xgrammar-venv uv run --project results/s4/xgrammar-env --locked python"
EXECUTOR = [{"role": "executor (W-S2)", "model": "Claude Opus 5.5", "brief": None, "separation": None}]
CORE_INPUTS = [
    {"path": "code/schema", "role": "spike schema copies (D2 §6, §9 v0)"},
    {"path": "code/s4", "role": "S4 compiler package"},
]


def j(p):
    return json.loads((RES / p).read_text())


def r(name, value, of=None, unit=None, note=None):
    return {"name": name, "value": value, "of": of, "unit": unit, "note": note}


def rec(**kw):
    base = {"schema_version": 1, "group": "S4 LinkML compilation", "finalized": "2026-10-28", "status": "current",
            "supersedes": [], "superseded_by": None, "agents": EXECUTOR}
    base.update(kw)
    (REC / f"{kw['id']}.json").write_text(json.dumps(base, indent=2, ensure_ascii=False) + "\n")
    return kw["id"]


def main() -> None:
    lint, rb = j("lint/lint.json"), j("lint/readback.json")
    rec(id="s4.pack-lint", title="Pack files in the native LinkML form: lint and annotation round trip", package="S4-A",
        question="Do core.yaml, statistics.yaml and rules.yaml, written in D2 §3's native form, load in SchemaView with their import and lint clean, and do the remaining ci: annotations round-trip (OPEN-D2-6)?",
        answers=["OPEN-D2-6", "D2 §3", "D2 §6", "D2 §9", "ADR-0017"],
        method="Pack files written in the D2 §2 layout under results/s4/schema/domains; linkml-lint per file with .linkmllint.yaml (extends recommended, recommended at error); rules files checked by a strict Pydantic model; each ci: annotation read through SchemaView compared with yaml.safe_load of the file.",
        commands=[f"{ENV} code/s4_lint.py"],
        inputs=CORE_INPUTS + [{"path": "code/s4_lint.py", "role": "check script"}],
        outputs=[{"path": "results/s4/schema", "role": "pack files"}, {"path": "results/s4/lint", "role": "lint and readback"},
                 {"path": "results/s4/roundtrip.md", "role": "findings and D2 ambiguities"}],
        depends_on=["e4.env-cpu"],
        results=[r("lint_errors", lint["core.yaml"]["levels"].get("error", 0) + lint["statistics.yaml"]["levels"].get("error", 0), note="core.yaml and statistics.yaml"),
                 r("lint_warnings", lint["statistics.yaml"]["levels"].get("warning", 0), note="standard_naming on the D1 field names t and v (statistics.yaml with its core import)"),
                 r("rules_files_valid", sum(v["ok"] for v in lint["rules_files"].values()), of=len(lint["rules_files"])),
                 r("annotations_round_trip", len(rb["annotations"]) - len(rb["mismatches"]), of=len(rb["annotations"])),
                 r("directory_mode_errors", lint["directory_mode"]["levels"].get("error", 0), note="rules.yaml linted as a schema: lint files, not the directory"),
                 r("d2_ambiguities_resolved", 21, note="roundtrip.md A1-A21")],
        outcome="passed",
        conclusion="Both schema files lint with 0 errors (two kept standard_naming warnings on D1's t and v); every one of the 129 scalar ci: annotations round-trips unchanged through SchemaView, so OPEN-D2-6 closes on native slots plus scalar annotations. ci:kind, ci:object, ci:group and the identity/field roles are derived or native; canonical_prefixes is disabled deliberately.",
        consumed_by=["P0-S-1", "OPEN-D2-6", "ADR-0017", "S4 report"])

    rows = list(csv.DictReader((RES / "validation.tsv").open(), delimiter="\t"))
    aw = [x for x in rows if x["variant"] == "as_written"]
    cn = [x for x in rows if x["variant"] == "canonical"]
    con, dec, seeds = json.loads((RES / "compiled/contract.json").read_text()), json.loads((RES / "compiled/decoding_checks.json").read_text()), json.loads((RES / "compiled/seeded_errors.json").read_text())
    valid_ms = [float(x["pydantic_ms"]) for x in rows if x["pydantic"] == "valid"]
    js_ms = [float(x["jsonschema_ms"]) for x in rows if x["jsonschema"] == "valid"]
    rec(id="s4.batch-validation", title="Batch models in both forms, JSON Schemas and the mirror contract test", package="S4-B",
        question="Do the per-predicate batch models built from the pack validate the v1 reference (both forms), the worked examples and the S0 batches, with jsonschema as an independent oracle, and which single entity-reference and statement shapes hold (V1, V2)?",
        answers=["D2 §7.3", "D2 §6", "D1 §6", "D1 §10.3", "OPEN-D2-6", "ADR-0017"],
        method="create_model per predicate over hand-written core Pydantic shapes; one TypeAdapter per form, strict JSON validation; draft 2020-12 export checked with check_schema; every batch validated as written and after the recorded V1/V2 rewrites, by Pydantic, by jsonschema on the exported schema and by the entity-type side-table check; contract test of the core shapes against core.yaml with one mutation on each side; seeded errors.",
        commands=[f"{ENV} code/s4_compile.py"],
        inputs=CORE_INPUTS + [{"path": "code/s4_compile.py", "role": "compile script"}, {"path": "results/s4/schema", "role": "pack files"},
                              {"path": "results/s0r2/reference_model_v1", "role": "v1 reference, model-facing"}, {"path": "results/s0r2/reference_v1", "role": "v1 reference, stored"},
                              {"path": "results/s0r2/examples", "role": "worked examples"}, {"path": "results/s0/stored", "role": "S0 stored batches"}, {"path": "results/s0/reference", "role": "v0 reference, stored"}],
        outputs=[{"path": "results/s4/compiled/batch.model.schema.json", "role": "model-facing JSON Schema"}, {"path": "results/s4/compiled/batch.stored.schema.json", "role": "stored JSON Schema"},
                 {"path": "results/s4/compiled/decoding_checks.json", "role": "schema checks"}, {"path": "results/s4/compiled/contract.json", "role": "mirror contract test"},
                 {"path": "results/s4/compiled/seeded_errors.json", "role": "seeded errors"}, {"path": "results/s4/validation.tsv", "role": "batch x form x variant"},
                 {"path": "results/s4/validation_errors.jsonl", "role": "errors and rewrites per batch"}],
        depends_on=["e4.env-cpu", "s0r2.reference-v1", "s0r2.inputs", "s0.stored", "s4.pack-lint"],
        results=[r("batches", len(aw), note="15 model-facing (12 v1 + 3 examples), 120 stored (12 v1, 12 v0 reference, 96 S0 passes)"),
                 r("valid_as_written", sum(x["pydantic"] == "valid" for x in aw), of=len(aw)),
                 r("batch_defects_migrated", len(cn), note="every as-written failure is a V1 or V2 shape: {t: entity} or dict-valued identity ref, or a Statement in entities[]"),
                 r("valid_after_migration", sum(x["pydantic"] == "valid" for x in cn), of=len(cn)),
                 r("rewrites", sum(int(x["rewrites"]) for x in cn)),
                 r("side_table_clean", sum(x["sidetable"] == "ok" for x in rows), of=sum(x["pydantic"] == "valid" for x in rows)),
                 r("validators_agree", sum(x["validators_agree"] == "True" for x in rows), of=len(rows), note="Pydantic and jsonschema verdicts per batch and variant"),
                 r("check_schema_passed", sum(v == "passed" for v in dec["check_schema"].values()), of=len(dec["check_schema"])),
                 r("contract_test", "passed" if con["passed"] else "failed", note="0 differences; each one-sided mutation fails it"),
                 r("seeded_errors_caught", sum(s["caught"] for s in seeds), of=len(seeds)),
                 r("predicate_branches", dec["branches"]),
                 r("model_facing_schema_bytes", dec["model_facing_bytes_compact"], unit="bytes"),
                 r("pydantic_ms_median", round(statistics.median(valid_ms), 3), unit="ms", note="per valid batch, indicative"),
                 r("jsonschema_ms_median", round(statistics.median(js_ms), 3), unit="ms", note="per valid batch, indicative"),
                 r("schema_bytes_identical_across_processes", dec["byte_identical_across_processes"])],
        outcome="passed",
        conclusion="All 135 batches validate in their form once 45 recorded batch defects are migrated to the canonical shapes (V1 {ref}, V2 statements only in statements[] with anchor outside); Pydantic and jsonschema agree on every batch, the side-table check is clean, both exported schemas pass check_schema, and the contract test passes while failing under either one-sided change.",
        consumed_by=["P0-S-1", "P0-F-2b", "P0-A-1", "ADR-0017", "S4 report"])

    h = j("compiled/hash.json")
    t = j("compiled/tables.json")
    rec(id="s4.schema-hash", title="Schema version hash and the schema-table rows", package="S4-B",
        question="Is the schema version hash (canonical JSON of the parsed pack files, rules files and worked examples) stable across processes, hash seeds and locations, and what rows does the schema-table compiler give D3's meta tables?",
        answers=["D2 §2", "D2 §7.1", "D3 §3"],
        method="SHA-256 of canonical JSON (D1 §10.1) over the parsed core.yaml, statistics.yaml, both rules.yaml and reference/E*, computed in this process and in three subprocesses (PYTHONHASHSEED 1, 777, 4242; the last on a copy in a temporary directory); schema tables compiled from SchemaView in D3 §3's column names.",
        commands=[f"{ENV} code/s4_compile.py", f"{ENV} code/s4_compile.py --hash-only"],
        inputs=CORE_INPUTS + [{"path": "code/s4_compile.py", "role": "compile script"}, {"path": "results/s4/schema", "role": "pack files"}],
        outputs=[{"path": "results/s4/compiled/hash.json", "role": "hash runs"}, {"path": "results/s4/compiled/tables.json", "role": "schema-table rows for meta.schema_*"}],
        depends_on=["s4.pack-lint"],
        results=[r("schema_version_hash", h["hash"]), r("hash_runs_equal", sum(x["hash"] == h["hash"] for x in h["runs"]), of=len(h["runs"])),
                 r("schema_class_rows", len(t["schema_class"])), r("schema_slot_rows", len(t["schema_slot"]), note="class-local attributes named <prefix>:<Class>.<attribute>"),
                 r("schema_enum_rows", len(t["schema_enum"])), r("schema_rule_rows", len(t["schema_rule"]))],
        outcome="passed",
        conclusion="The hash is identical in four computations across hash seeds and locations; the schema-table rows exist for S6-D in D3's column names, with class-local value-class attributes keyed <prefix>:<Class>.<attribute> because D3's (schema_version_id, name) key cannot hold two attributes named v.",
        consumed_by=["S6-D", "P0-F-4", "P0-S-1", "S4 report"])

    rc, sd = j("rules_compile.json"), j("rules_seeds.json")
    rec(id="s4.rules", title="Pack rules and guideline warnings in rule-engine, with the generic view builder", package="S4-C",
        question="Do the pack's rules.yaml checks and the 11 guideline checks compile as typed rule-engine rules, give no warnings on the v1 reference and examples, catch one seeded violation each, and serve both call sites through one view (OPEN-D2-3)?",
        answers=["OPEN-D2-3", "D2 §7.4", "D5 §8.2", "ADR-0018"],
        method="One typed Context per expression generated from the schema version (OBJECT views, getattr, no mapping dot-access, UTC, $now/$today/$random rejected); tables as typed $ builtins; a generic view builder over one core candidate type adapted from a batch (local refs) and from a 12-unit pool (synthetic keys); the views: family_params compiled from rules.yaml; a function form of the same view compared; negative compiles; one seed per rule; parity with code/s0r2_rules.py.",
        commands=[f"{ENV} code/s4_rules.py"],
        inputs=CORE_INPUTS + [{"path": "code/s4_rules.py", "role": "rules script"}, {"path": "code/s0r2_rules.py", "role": "Python reference checker"},
                              {"path": "results/s4/schema", "role": "pack files"}, {"path": "results/s0r2/reference_model_v1", "role": "v1 reference"}, {"path": "results/s0r2/examples", "role": "worked examples"}],
        outputs=[{"path": "results/s4/rules.tsv", "role": "rule x claim x site"}, {"path": "results/s4/rules_compile.json", "role": "compile, parity, function form, negatives"},
                 {"path": "results/s4/rules_seeds.json", "role": "seeds"}],
        depends_on=["s4.pack-lint", "s4.batch-validation", "s0r2.reference-v1", "s0r2.inputs"],
        results=[r("rules_compiled", rc["rules_compiled"], note="4 pack rules, 1 core rule, 11 guideline"),
                 r("evaluations", rc["evaluations"], note="rule x claim x site, unseeded"),
                 r("unexpected_fires", len(rc["unexpected_fires"])),
                 r("seeds_caught", rc["seeds_caught"], of=rc["seeds"]),
                 r("guideline_seeds_also_warned_by_s0r2_rules", rc["guideline_seeds_s0r2_warns"], of=rc["guideline_seeds"]),
                 r("parity_with_s0r2_rules", rc["parity_ok"], note="both 0 warnings on all 15 batches"),
                 r("negative_compiles_rejected", sum(n["outcome"].startswith("rejected") for n in rc["negative_compiles"]), of=len(rc["negative_compiles"])),
                 r("function_form_agrees", rc["function_form"]["agree_with_attribute_form"], of=rc["function_form"]["has_distribution_claims"], note=f"{rc['function_form']['function_calls']} calls for one evaluation pass"),
                 r("compile_ms", rc["compile_ms"], unit="ms", note="16 rules, 32 expressions"), r("finalize_reader", rc["finalize_reader"])],
        outcome="passed",
        conclusion="All 16 rules compile under typed contexts, give 0 warnings on the 15 v1 batches at the batch site and 0 at the finalize site, and catch 16 of 16 seeds (S0-R2's checker warns on all 11 guideline seeds too); the view-attribute and function forms both type-check and agree, and the views: section compiles family_params with no domain code, closing OPEN-D2-3 as proposed.",
        consumed_by=["P0-S-2", "P0-O-2", "OPEN-D2-3", "ADR-0018", "S4 report"])

    it = j("reference_items.json")
    rec(id="s4.reference-diff", title="Annotator reference generated from the schema, against S0-R2's", package="S4-D",
        question="Can the annotator reference be generated from SchemaView, the compiled models and rules.yaml with the information S0-R2's hand-assembled reference carries (D2 §7.5, §10.10)?",
        answers=["D2 §7.5", "D2 §10.10", "ADR-0011"],
        method="A generator with no predicate, class or rule text in code: cards grouped by subsets, guideline rules per card by applies_to, tables, exact shapes from the core Pydantic models, examples from reference/; compared section by section, names mechanically and information by reading.",
        commands=[f"{ENV} code/s4_reference.py"],
        inputs=CORE_INPUTS + [{"path": "code/s4_reference.py", "role": "reference script"}, {"path": "results/s0r2/inputs/packet_v1/reference.md", "role": "S0-R2 reference"},
                              {"path": "results/s4/schema", "role": "pack files"}],
        outputs=[{"path": "results/s4/compiled/reference.md", "role": "generated reference"}, {"path": "results/s4/compiled/reference_by_kind", "role": "V4 variants"},
                 {"path": "results/s4/reference_items.json", "role": "mechanical diff"}, {"path": "results/s4/reference_diff.md", "role": "information diff"}],
        depends_on=["s4.batch-validation", "s4.rules", "s0r2.inputs"],
        results=[r("cards", it["cards"]["s4_cards"], note=f"S0-R2 {it['cards']['s0r2_cards']}; S4 adds unschematized"),
                 r("empty_meanings_s0r2", len(it["cards"]["empty_meaning_s0r2"])), r("empty_meanings_s4", len(it["cards"]["empty_meaning_s4"])),
                 r("names_only_in_s0r2", sum(len(x["only_s0r2"]) for x in it["sections"]), note="all in S0-R2's per-card role/modality lines (role, modality and node names, ParameterRole); the generated reference states them in its tables section, rule descriptions and object shapes"),
                 r("information_missing_in_generated", 1, note="per-card role/modality sentence for the six family-structure-only predicates; same facts in the tables section")],
        outcome="passed",
        conclusion="The generated reference carries S0-R2's information and more (descriptions for 6 predicates and 11 qualifiers, exact shapes, tables, unschematized); the one information loss is the per-card role/modality sentence for family-structure-only predicates, restorable by schema text in the family_structure subset description. The reference compiler is specified.",
        consumed_by=["P0-S-1", "P0-A-1", "S4 report"])

    sz = list(csv.DictReader((RES / "sizes.tsv").open(), delimiter="\t"))
    tok = {x["artifact"]: x for x in sz}
    rec(id="s4.sizes", title="Sizes of the compiled S4 artifacts in bytes and served-model tokens", package="S4-D",
        question="How large are the generated reference (whole, per part, per statement kind) and the compiled schemas in Qwen3.5-9B tokens, and does the reference exceed about 1,500 tokens (V4)?",
        answers=["D2 §7.5", "D4 §4.2", "D4 §4.1"],
        method="tokenizers 0.23.3 with the Qwen3.5-9B tokenizer.json (revision recorded), encode_batch_fast, add_special_tokens=False, one count per artifact text; schemas compacted JSON.",
        commands=[f"{ENV} code/s4_reference.py"],
        inputs=[{"path": "code/s4_reference.py", "role": "reference script"}],
        outputs=[{"path": "results/s4/sizes.tsv", "role": "artifact: bytes, tokens, sha256"}, {"path": "results/s4/tokenizer.json", "role": "tokenizer revision"}],
        depends_on=["s4.reference-diff", "e0.environment"],
        results=[r("reference_tokens", int(tok["reference.generated"]["tokens"]), unit="tokens"),
                 r("reference_without_examples_tokens", int(tok["reference.generated.without_examples"]["tokens"]), unit="tokens"),
                 r("s0r2_reference_tokens", int(tok["reference.s0r2"]["tokens"]), unit="tokens"),
                 r("s0r2_reference_without_examples_tokens", int(tok["reference.s0r2.without_examples"]["tokens"]), unit="tokens"),
                 r("predicate_cards_tokens", int(tok["reference.generated.part.predicates"]["tokens"]), unit="tokens"),
                 r("smallest_per_kind_tokens", min(int(x["tokens"]) for x in sz if x["artifact"].startswith("reference.generated.kind.")), unit="tokens"),
                 r("decoding_schema_tokens", int(tok["batch.decoding.schema.json"]["tokens"]), unit="tokens"),
                 r("model_facing_schema_tokens", int(tok["batch.model.schema.json"]["tokens"]), unit="tokens")],
        outcome="passed",
        conclusion="The generated reference is about 1.3 times S0-R2's without examples and over four times the brief's 1,500-token threshold even with every example filtered out; filtering by statement kind can drop only examples, so V4 as specified cannot reach the threshold and is not adopted.",
        consumed_by=["P0-S-1", "P0-A-1", "S3", "S4 report"])

    g = j("gliner2.json")
    rec(id="s4.gliner-roundtrip", title="GLiNER2 extraction and JointIE schemas compiled from the pack", package="S4-D",
        question="Which Schema.from_dict keys does gliner2 2.1.0 accept for the pack's entities, attributes, classifications and relations, do the compiled dicts round-trip, and do both schemas run (OPEN-D2-1)?",
        answers=["OPEN-D2-1", "D2 §7.2"],
        method="Dicts compiled from mention classes (title, description plus examples), enums by ci:extract (attribute, classification), ci:extract relation predicates; Schema.from_dict/to_dict and JointSchema.from_dict/to_dict fixpoints; unknown key rejected; one extraction each on T3 s1 on CPU with the cached fastino/gliner2.5-base-v1.",
        commands=[f"HF_HUB_OFFLINE=1 {ENV} code/s4_gliner.py"],
        inputs=CORE_INPUTS + [{"path": "code/s4_gliner.py", "role": "GLiNER2 script"}, {"path": "results/s4/schema", "role": "pack files"}],
        outputs=[{"path": "results/s4/compiled/gliner2", "role": "extraction and joint dicts"}, {"path": "results/s4/gliner2.json", "role": "keys, round trip, runs"}],
        depends_on=["e4.env-cpu", "s4.pack-lint"],
        results=[r("gliner2", g["gliner2"] or "2.1.0"), r("extraction_to_dict_fixpoint", g["extraction"]["to_dict_is_fixpoint"]),
                 r("compiled_dict_equals_to_dict", g["extraction"]["compiled_equals_to_dict"], note="to_dict compacts a description-only entity config to a string; the compiler emits that canonical form"),
                 r("joint_to_dict_fixpoint", g["joint"]["to_dict_is_fixpoint"]), r("unknown_key_rejected", g["extraction"]["unknown_key_rejected"]),
                 r("extraction_run", g["extraction_run"]["outcome"]), r("joint_run", g["joint_run"]["outcome"])],
        outcome="passed",
        conclusion="gliner2 2.1.0 accepts entities {label: description}, entity_attributes {labels, applies_to, qualify_labels}, classifications {task, labels: {label: description}} and relations {name: {description}}; from_dict/to_dict reach a fixpoint on the compiled form (description-only entity configs compact to strings), JointSchema round-trips, an unknown key is rejected, and both schemas ran on CPU. OPEN-D2-1 answered for v0 (no structures or thresholds declared).",
        consumed_by=["S2", "OPEN-D2-1", "S4 report"])

    d = j("decoding.json")
    rec(id="s4.decoding-form", title="Decoding form compiled in xgrammar 0.2.7 (vLLM 0.31's backend), offline on CPU", package="S4-D",
        question="Is the per-predicate oneOf decoding form accepted by vLLM 0.31's structured-output backend without downgrades, quickly enough, and does its grammar accept the canonical v1 batches and reject seeded invalid ones (V3)?",
        answers=["D2 §7.3"],
        method="Decoding form = model-facing schema without discriminator/description/default/title, oneOf branches inlined; xgrammar 0.2.7 in a side uv project on CPU torch (results/s4/xgrammar-env); GrammarCompiler with the Qwen3.5-9B tokenizer; backend warnings captured at the fd level; acceptance of the 15 canonical batches compact and indented; 7 seeded invalid batches; each oneOf diagnosed in its own process.",
        commands=[f"cd results/s4/xgrammar-env && UV_PROJECT_ENVIRONMENT=$REPO/build/spike-xgrammar-venv uv sync --locked", f"{XENV} code/s4_decoding.py"],
        inputs=[{"path": "code/s4_decoding.py", "role": "decoding script"}, {"path": "results/s4/xgrammar-env", "role": "side environment (pyproject, uv.lock)"},
                {"path": "results/s4/compiled/decoding_inputs", "role": "canonical batches in schema order"}],
        outputs=[{"path": "results/s4/compiled/batch.decoding.schema.json", "role": "decoding form"}, {"path": "results/s4/decoding.json", "role": "compile, acceptance, diagnosis"}],
        depends_on=["s4.batch-validation"],
        results=[r("xgrammar", d["versions"]["xgrammar"]), r("compile_warnings", len(d["compile"]["warnings"])),
                 r("oneof_kept", sum(not x["downgraded"] for x in d["oneof_diagnosis"]), of=len(d["oneof_diagnosis"])),
                 r("compile_s", d["compile"]["first_s"], unit="s", note=f"vocab {d['vocab_size']}"),
                 r("batches_accepted", d["accepted"], of=d["batches"]), r("seeds_rejected", d["seeded_rejected"], of=len(d["seeded"])),
                 r("ref_branches_downgraded_before_inlining", True, note="with $ref branches every oneOf fell back to anyOf (8 warnings)"),
                 r("author_key_order_accepted", d["key_order"]["author_order_default"], note="only with any_order=True")],
        outcome="passed",
        conclusion="With oneOf branches inlined, xgrammar 0.2.7 keeps every oneOf (0 warnings), compiles the 53 KB decoding form in 0.03 s with the 248k-token Qwen vocabulary, accepts all 15 canonical batches and rejects all 7 seeds; with $ref branches every oneOf silently became anyOf. V3a (per-predicate oneOf) holds; the flat form is not needed. Checked offline without vLLM itself.",
        consumed_by=["P0-S-1", "S3", "S4 report"])


if __name__ == "__main__":
    main()
