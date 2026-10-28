"""S4-A: load and lint the pack files; read every annotation and native feature back (OPEN-D2-6).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_lint.py

Writes results/s4/lint/ (linkml-lint JSON per schema file, the rules-file check, the directory-mode
run that shows why files are linted one by one) and results/s4/lint/readback.json. The readback is
non-circular: each ci: annotation and native feature as SchemaView returns it is compared with the
value yaml.safe_load reads from the file.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s4 import paths  # noqa: E402
from s4.pack import LIST_ANNOTATIONS, Pack, RulesFile, annotations  # noqa: E402

OUT = paths.RES / "lint"


def lint(target: Path, name: str) -> dict:
    out = OUT / f"{name}.json"
    cmd = ["linkml-lint", "--config", str(paths.LINT_CONFIG), "--format", "json", "-o", str(out), str(target)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    try:
        problems = json.loads(out.read_text() or "[]")
    except json.JSONDecodeError:
        problems = []
    for pr in problems:  # paths relative to the evidence folder, so the file is stable across checkouts
        if "file" in pr:
            pr["file"] = paths.rel(Path(pr["file"]))
    out.write_text(json.dumps(problems, indent=1, sort_keys=True) + "\n")
    levels: dict[str, int] = {}
    for pr in problems:
        levels[pr.get("level", "?")] = levels.get(pr.get("level", "?"), 0) + 1
    return {"target": paths.rel(target), "exit": p.returncode, "levels": levels,
            "problems": [f"{pr.get('level')} {pr.get('rule_name')}: {pr.get('message')}" for pr in problems]}


def raw_annotations(raw: dict) -> list[tuple[str, str, object]]:
    """(element path, tag, value) for every ci: annotation in a parsed schema file."""
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "annotations" and isinstance(v, dict):
                    for tag, val in v.items():
                        out.append(("/".join(path), tag, val))
                else:
                    walk(v, path + [str(k)])

    walk(raw, [])
    return out


def element_of(sv, path: str):
    parts = path.split("/")
    kind, name = parts[0], parts[1]
    if kind == "classes":
        el = sv.get_class(name)
        if len(parts) > 3 and parts[2] == "attributes":
            el = el.attributes[parts[3]]
        return el
    if kind == "slots":
        return sv.get_slot(name)
    if kind == "enums":
        el = sv.get_enum(name)
        if len(parts) > 3 and parts[2] == "permissible_values":
            el = el.permissible_values[parts[3]]
        return el
    raise KeyError(path)


def readback(pack: Pack) -> dict:
    sv = pack.sv
    rows, mismatches = [], []
    for f in (paths.CORE_YAML, paths.PACK_YAML):
        raw = yaml.safe_load(f.read_text())
        for path, tag, val in raw_annotations(raw):
            got = annotations(element_of(sv, path)).get(tag)
            want = tuple(str(val).split()) if tag in LIST_ANNOTATIONS else val
            ok = got == want and type(got) is type(want)
            rows.append({"file": f.name, "element": path, "tag": tag, "yaml": val, "schemaview": got,
                         "type": type(got).__name__, "equal": ok})
            if not ok:
                mismatches.append(rows[-1])
    native = {
        "examples": {c: [e.value for e in sv.get_class(c).examples] for c in sv.all_classes() if sv.get_class(c).examples},
        "unique_keys": {c: {k: list(u.unique_key_slots) for k, u in sv.get_class(c).unique_keys.items()}
                        for c in sv.all_classes() if sv.get_class(c).unique_keys},
        "title": {c: sv.get_class(c).title for c in sv.all_classes() if sv.get_class(c).title},
        "subsets": pack.subsets,
        "symmetric": [s for s in sv.all_slots() if sv.get_slot(s).symmetric],
        "transitive": [s for s in sv.all_slots() if sv.get_slot(s).transitive],
        "equals_string_t": pack.value_classes,
        "ifabsent": {s: sv.get_slot(s).ifabsent for s in sv.all_slots() if sv.get_slot(s).ifabsent},
        "prefixed_names": {p: i.prefixed for p, i in pack.predicates.items()},
    }
    induced = {c: [{"slot": s.name, "range": s.range, "required": bool(s.required), "multivalued": bool(s.multivalued)}
                   for s in sv.class_induced_slots(c)] for c in sorted(sv.all_classes())}
    applicable = {c: pack.applicable_predicates(c) for c in pack.entity_classes}
    return {"imports_closure": sv.imports_closure(), "annotations": rows, "mismatches": mismatches,
            "native": native, "induced_slots": induced, "applicable_predicates": applicable,
            "counts": {"classes": len(sv.all_classes()), "slots": len(sv.all_slots()), "enums": len(sv.all_enums()),
                       "predicates": len(pack.predicates), "qualifiers": len(pack.qualifiers),
                       "annotations": len(rows)}}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pack = Pack()
    results = {
        "core.yaml": lint(paths.CORE_YAML, "core"),
        "statistics.yaml": lint(paths.PACK_YAML, "statistics"),
        "directory_mode": lint(paths.DOMAINS, "directory_mode"),
    }
    rules = {}
    for f in (paths.CORE_RULES, paths.PACK_RULES):
        try:
            d = RulesFile.model_validate(yaml.safe_load(f.read_text()))
            rules[paths.rel(f)] = {"ok": True, "rules": len(d.rules), "guideline": len(d.guideline),
                                   "views": len(d.views), "tables": len(d.tables)}
        except Exception as e:  # noqa: BLE001
            rules[paths.rel(f)] = {"ok": False, "error": str(e)}
    results["rules_files"] = rules
    rb = readback(pack)
    (OUT / "lint.json").write_text(json.dumps(results, indent=1, sort_keys=True) + "\n")
    (OUT / "readback.json").write_text(json.dumps(rb, indent=1, sort_keys=True, default=str) + "\n")
    for k, v in results.items():
        print(k, json.dumps(v)[:400])
    print("annotations read back:", len(rb["annotations"]), "mismatches:", len(rb["mismatches"]))
    for m in rb["mismatches"]:
        print("  MISMATCH", m)
    ok = (not results["core.yaml"]["levels"].get("error") and not results["statistics.yaml"]["levels"].get("error")
          and all(r["ok"] for r in rules.values()) and not rb["mismatches"])
    print("S4-A", "passed" if ok else "failed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
