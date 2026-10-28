"""S4-B: schema tables, schema version hash, both batch JSON Schemas and the decoding form, the mirror
contract test, and validation of every listed batch in both validators (brief steps 3 and 5).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_compile.py
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_compile.py --hash-only [domains]

Writes results/s4/schema/domains/statistics/reference/E*/ (the worked examples in canonical shape),
results/s4/compiled/ (tables.json, batch.model.schema.json, batch.stored.schema.json,
batch.decoding.schema.json, decoding_checks.json, contract.json, hash.json, seeded_errors.json) and
results/s4/validation.tsv with validation_errors.jsonl.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s4 import paths  # noqa: E402
from s4.hashing import schema_version_hash, sha256_canonical  # noqa: E402

if len(sys.argv) > 1 and sys.argv[1] == "--hash-only":
    print(schema_version_hash(Path(sys.argv[2]) if len(sys.argv) > 2 else paths.DOMAINS))
    sys.exit(0)

from jsonschema import Draft202012Validator  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from s4 import contract  # noqa: E402
from s4.batch_models import FORMS, BatchCompiler, decoding_form, structural_checks  # noqa: E402
from s4.pack import Pack  # noqa: E402
from s4.sidetable import canonicalize, side_table_check  # noqa: E402
from s4.tables import schema_tables  # noqa: E402

COMPILER_VERSION = "s4-0.1"


def dump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_examples() -> list[str]:
    notes = []
    for f in sorted((paths.R2 / "examples").glob("E*.json")):
        b, _ = paths.load_batch(f)
        cb, n = canonicalize(b)
        d = paths.PACK_REFERENCE / f.stem
        d.mkdir(parents=True, exist_ok=True)
        (d / "batch.json").write_text(json.dumps(cb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        shutil.copyfile(paths.EXAMPLE_PACKETS / f"{f.stem}.md", d / "packet.md")
        notes += [f"{f.stem}: {x}" for x in n]
    return notes


def hash_runs() -> dict:
    here = schema_version_hash()
    runs = []
    env = dict(os.environ)
    for seed in ("1", "777"):
        env["PYTHONHASHSEED"] = seed
        out = subprocess.run([sys.executable, __file__, "--hash-only"], capture_output=True, text=True, env=env, check=True)
        runs.append({"PYTHONHASHSEED": seed, "location": "results/s4/schema/domains", "hash": out.stdout.strip()})
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / "elsewhere" / "domains"
        shutil.copytree(paths.DOMAINS, copy)
        env["PYTHONHASHSEED"] = "4242"
        out = subprocess.run([sys.executable, __file__, "--hash-only", str(copy)], capture_output=True, text=True, env=env, check=True)
        runs.append({"PYTHONHASHSEED": "4242", "location": "a copy in a temporary directory", "hash": out.stdout.strip()})
    return {"hash": here, "runs": runs, "stable": all(r["hash"] == here for r in runs)}


def schema_bytes_stable() -> bool:
    code = ("import sys,json,hashlib;sys.path.insert(0,'code');from s4.pack import Pack;from s4.batch_models import BatchCompiler;"
            "b=BatchCompiler(Pack());print(hashlib.sha256(json.dumps([b.json_schema('model'),b.json_schema('stored')],sort_keys=False).encode()).hexdigest())")
    outs = set()
    for seed in ("3", "11"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        outs.add(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=paths.EV, check=True).stdout.strip())
    return len(outs) == 1


def contract_runs(pack: Pack) -> dict:
    real = contract.compare(pack)
    mut_p = contract.compare(pack, contract.mutated_pydantic())
    with tempfile.TemporaryDirectory() as td:
        copy = Path(td) / "domains"
        shutil.copytree(paths.DOMAINS, copy)
        core = copy / "core" / "schema" / "core.yaml"
        t = core.read_text()
        t = t.replace("      v: {required: true, description: The text.}",
                      "      v: {required: true, description: The text.}\n      lang: {description: A language tag.}")
        core.write_text(t)
        mut_l = contract.compare(Pack(copy / "statistics" / "schema" / "statistics.yaml"))
    return {"real": real, "mutation_pydantic_drops_NumberValue_basis": mut_p, "mutation_linkml_adds_TextValue_lang": mut_l,
            "passed": not real and bool(mut_p) and bool(mut_l)}


def pyd_errors(e: ValidationError) -> list[dict]:
    return [{"loc": ".".join(map(str, x["loc"])), "type": x["type"], "msg": x["msg"]} for x in e.errors()]


def validate_all(pack: Pack, bc: BatchCompiler, schemas: dict) -> tuple[list[dict], list[dict]]:
    validators = {f: Draft202012Validator(schemas[f]) for f in FORMS}
    rows, details = [], []
    for set_name, form, files in paths.batch_sets():
        for f in files:
            raw, _ = paths.load_batch(f)
            canon, rewrites = canonicalize(raw)
            for variant, b in (("as_written", raw), ("canonical", canon)):
                if variant == "canonical" and not rewrites:
                    continue
                text = json.dumps(b, ensure_ascii=False)
                t0 = time.perf_counter()
                try:
                    bc.validate(text, form)
                    perr = []
                except ValidationError as e:
                    perr = pyd_errors(e)
                pms = (time.perf_counter() - t0) * 1000
                t0 = time.perf_counter()
                jerr = sorted(validators[form].iter_errors(b), key=lambda e: list(e.absolute_path))
                jms = (time.perf_counter() - t0) * 1000
                side = side_table_check(b, pack, form) if not perr else None
                rows.append({
                    "set": set_name, "unit": f.stem, "form": form, "variant": variant,
                    "rewrites": len(rewrites) if variant == "canonical" else 0,
                    "claims": len(b.get("claims", [])),
                    "pydantic": "valid" if not perr else "invalid", "pydantic_errors": len(perr),
                    "jsonschema": "valid" if not jerr else "invalid", "jsonschema_errors": len(jerr),
                    "sidetable": "not_run" if side is None else ("ok" if not side else "issues"),
                    "sidetable_issues": 0 if side is None else len(side),
                    "validators_agree": (not perr) == (not jerr),
                    "pydantic_ms": round(pms, 3), "jsonschema_ms": round(jms, 3),
                    "first_error": (perr[0]["loc"] + " " + perr[0]["type"]) if perr else (side[0] if side else ""),
                })
                details.append({"set": set_name, "unit": f.stem, "variant": variant,
                                "rewrites": rewrites if variant == "canonical" else [],
                                "pydantic": perr, "jsonschema": [{"path": e.json_path, "msg": e.message[:300]} for e in jerr[:20]],
                                "sidetable": side})
    return rows, details


def seeded(bc: BatchCompiler, schemas: dict, pack: Pack) -> list[dict]:
    """Seeded errors on a valid batch: the Pydantic location and the jsonschema best match."""
    from jsonschema.exceptions import best_match

    b, _ = paths.load_batch(paths.R2 / "reference_model_v1" / "T3.json")
    b, _ = canonicalize(b)
    seeds = []

    def seed(name, mutate):
        x = json.loads(json.dumps(b))
        mutate(x)
        side = None
        try:
            bc.validate(json.dumps(x), "model")
            pl = "accepted"
            side = side_table_check(x, pack, "model")
        except ValidationError as e:
            er = e.errors()[0]
            pl = ".".join(map(str, er["loc"])) + " " + er["type"]
        bm = best_match(Draft202012Validator(schemas["model"]).iter_errors(x))
        seeds.append({"seed": name, "pydantic": pl, "jsonschema_best_match": None if bm is None else f"{bm.json_path} {bm.message[:120]}",
                      "sidetable": side, "caught": pl != "accepted" or bool(side)})

    seed("unknown predicate", lambda x: x["claims"][0].__setitem__("predicate", "has_distrib"))
    seed("modality not in enum", lambda x: x["claims"][0]["qualifiers"].__setitem__("modality", "assumed"))
    seed("qualifier not allowed for the predicate", lambda x: x["claims"][0]["qualifiers"].__setitem__("transform", {"t": "formula", "latex": "e^Y"}))
    fc = next(i for i, c in enumerate(b["claims"]) if c["object"].get("t") == "formula")
    seed("binding without its claim", lambda x: x["claims"][fc]["object"]["symbols"].__setitem__("q", {"bind": "param_of", "param": "mean"}))
    seed("bare LaTeX string in a formula position", lambda x: x["claims"][fc].__setitem__("object", "a + b \\mu"))
    seed("subject of the wrong class (side table)", lambda x: x["claims"][0].__setitem__("subject", next(e["local_ref"] for e in x["entities"] if e["type"] == "DistributionFamily")))
    seed("object ref that does not resolve (side table)", lambda x: x["claims"][0]["object"].__setitem__("ref", "nowhere"))
    seed("variable binding naming a global entity (side table)", lambda x: x["claims"][fc]["object"]["symbols"].__setitem__("q", {"bind": "variable", "entity": next(e["local_ref"] for e in x["entities"] if e["scope"] == "global")}))
    seed("param_of naming a missing map entry (side table)", lambda x: x["claims"][fc]["object"]["symbols"].__setitem__("q", {"bind": "param_of", "claim": x["claims"][0]["local_ref"], "param": "kurtosis"}))
    seed("global entity with an extent (side table)", lambda x: next(e for e in x["entities"] if e["scope"] == "global").__setitem__("extent", "section"))
    seed("entity as a value (V1)", lambda x: x["claims"][0].__setitem__("object", {"t": "entity", "ref": x["claims"][0]["object"].get("ref", "X")}))
    seed("null for an absent field", lambda x: x["claims"][0].__setitem__("statement_role", None))
    seed("Statement in entities[] (V2)", lambda x: x["entities"].append({"local_ref": "st9", "type": "Statement", "label": "the last result", "scope": "local", "extent": "section"}))
    return seeds


def main() -> int:
    paths.COMPILED.mkdir(parents=True, exist_ok=True)
    example_notes = write_examples()
    pack = Pack()
    t0 = time.perf_counter()
    bc = BatchCompiler(pack)
    build_ms = (time.perf_counter() - t0) * 1000
    schemas = {f: bc.json_schema(f) for f in FORMS}
    schemas["decoding"] = decoding_form(schemas["model"])
    check = {}
    for f, s in schemas.items():
        name = f"batch.{f}.schema.json"
        (paths.COMPILED / name).write_text(json.dumps(s, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            Draft202012Validator.check_schema(s)
            check[f] = "passed"
        except Exception as e:  # noqa: BLE001
            check[f] = f"failed: {e}"
    dec = structural_checks(schemas["decoding"])
    dec["check_schema"] = check
    dec["model_facing_bytes_compact"] = len(json.dumps(schemas["model"], separators=(",", ":")))
    dec["stored_bytes_compact"] = len(json.dumps(schemas["stored"], separators=(",", ":")))
    dec["branches"] = len(pack.predicates)
    dec["build_ms"] = round(build_ms, 1)
    dec["byte_identical_across_processes"] = schema_bytes_stable()
    dump(paths.COMPILED / "decoding_checks.json", dec)

    hashes = hash_runs()
    dump(paths.COMPILED / "hash.json", hashes)
    tables = schema_tables(pack)
    artifacts = []
    for f in ("model", "stored", "decoding"):
        artifacts.append({"compiler": "json_schema", "compiler_version": COMPILER_VERSION, "kind": f"batch.{'model_facing' if f == 'model' else f}",
                          "hash": sha256_canonical(schemas[f])})
    artifacts.append({"compiler": "schema_tables", "compiler_version": COMPILER_VERSION, "kind": "tables", "hash": sha256_canonical(tables)})
    sv = pack.sv.schema
    tables_doc = {
        "schema_version": {"domain": "statistics", "label": str(sv.version), "content_hash": hashes["hash"],
                           "source_files": sorted(__import__("s4.hashing", fromlist=["x"]).schema_sources())},
        "compiled_artifact": artifacts,
        **tables,
    }
    dump(paths.COMPILED / "tables.json", tables_doc)

    con = contract_runs(pack)
    dump(paths.COMPILED / "contract.json", con)

    rows, details = validate_all(pack, bc, schemas)
    cols = list(rows[0])
    (paths.RES / "validation.tsv").write_text("\t".join(cols) + "\n" + "".join("\t".join(str(r[c]) for c in cols) + "\n" for r in rows), encoding="utf-8")
    (paths.RES / "validation_errors.jsonl").write_text("".join(json.dumps(d, ensure_ascii=False, sort_keys=True) + "\n" for d in details), encoding="utf-8")
    dump(paths.COMPILED / "seeded_errors.json", seeded(bc, schemas, pack))
    dump(paths.COMPILED / "example_rewrites.json", example_notes)
    # the 15 model-facing batches in canonical shape, as the compiled model dumps them (schema property
    # order, defaults omitted): the inputs of the decoding-form acceptance check (code/s4_decoding.py)
    di = paths.COMPILED / "decoding_inputs"
    di.mkdir(exist_ok=True)
    for set_name, form, files in paths.batch_sets():
        if form != "model":
            continue
        for f in files:
            b = canonicalize(paths.load_batch(f)[0])[0]
            m = bc.validate(json.dumps(b), "model")
            (di / f"{f.stem}.json").write_text(json.dumps(m.model_dump(mode="json", exclude_none=True), ensure_ascii=False) + "\n", encoding="utf-8")

    print("hash", hashes)
    print("tables", {k: len(v) for k, v in tables.items()})
    print("check_schema", check, "decoding", {k: dec[k] for k in ("issues", "json_depth", "oneOf", "anyOf", "bytes_compact")})
    print("contract", con["passed"], con["real"], len(con["mutation_pydantic_drops_NumberValue_basis"]), len(con["mutation_linkml_adds_TextValue_lang"]))
    by = {}
    for r in rows:
        k = (r["set"], r["variant"])
        v = by.setdefault(k, [0, 0, 0, 0])
        v[0] += 1
        v[1] += r["pydantic"] == "valid"
        v[2] += r["sidetable"] == "ok"
        v[3] += r["validators_agree"]
    for k, v in by.items():
        print(k, "batches", v[0], "pydantic valid", v[1], "sidetable ok", v[2], "validators agree", v[3])
    return 0


if __name__ == "__main__":
    sys.exit(main())
