"""S4-D (reference part): generate the annotator reference, list its information against S0-R2's
reference.md section by section, and size every S4 artifact with the served Qwen tokenizer (step 8).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_reference.py

Writes results/s4/compiled/reference.md (and reference_by_kind/<kind>.md, the V4 filtered variants),
results/s4/reference_items.json (the mechanical part of the diff: names present in one and not the
other, per section) and results/s4/sizes.tsv. results/s4/reference_diff.md is written by hand from
reference_items.json and a reading of both documents.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from s4 import paths  # noqa: E402
from s4.batch_models import BatchCompiler  # noqa: E402
from s4.pack import Pack  # noqa: E402
from s4.reference import generate, load_examples  # noqa: E402


def sections(md: str) -> dict[str, str]:
    out, cur = {}, "head"
    for line in md.splitlines():
        m = re.match(r"^## (\d+)\. (.+)", line)
        if m:
            cur = m.group(2).strip().lower()
        out[cur] = out.get(cur, "") + line + "\n"
    return out


def names(text: str) -> set[str]:
    return set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", text))


def tokenizer():
    from tokenizers import Tokenizer

    tj = paths.QWEN / "tokenizer.json"
    return Tokenizer.from_file(str(tj)), {"repo": "Qwen/Qwen3.5-9B", "revision": paths.QWEN.name,
                                           "tokenizer_json_sha256": hashlib.sha256(tj.read_bytes()).hexdigest()}


def main() -> int:
    pack = Pack()
    bc = BatchCompiler(pack)
    ex = load_examples()
    parts = generate(pack, bc, ex)
    ref = "".join(parts.values())
    (paths.COMPILED / "reference.md").write_text(ref, encoding="utf-8")
    kinds = sorted({s["kind"] for _, b in ex.values() for s in b.get("statements", [])})
    bykind = {}
    (paths.COMPILED / "reference_by_kind").mkdir(exist_ok=True)
    for k in pack.enum_values("StatementKind"):
        p = generate(pack, bc, ex, kinds={k})
        bykind[k] = "".join(p.values())
        (paths.COMPILED / "reference_by_kind" / f"{k}.md").write_text(bykind[k], encoding="utf-8")

    old = paths.SR_REFERENCE_MD.read_text(encoding="utf-8")
    so, sn = sections(old), sections(ref)
    pairs = [("entity types", "entity types"), ("predicates", "predicates"), ("qualifiers", "qualifiers"),
             ("enumerations", "enumerations"), ("values and condition nodes", "exact shapes"), ("worked examples", "worked examples"),
             (None, "statement roles and modality")]
    items = []
    for a, b in pairs:
        na, nb = names(so.get(a, "")) if a else set(), names(sn.get(b, ""))
        items.append({"s0r2_section": a, "s4_section": b, "only_s0r2": sorted(na - nb), "only_s4": sorted(nb - na), "both": len(na & nb)})
    preds_old = re.findall(r"^#### `(\w+)`", old, re.M)
    preds_new = re.findall(r"^#### `(\w+)`", ref, re.M)
    cards = {"s0r2_cards": len(preds_old), "s4_cards": len(preds_new), "only_s0r2": sorted(set(preds_old) - set(preds_new)),
             "only_s4": sorted(set(preds_new) - set(preds_old)),
             "empty_meaning_s0r2": re.findall(r"#### `(\w+)`\n\n[^\n]*\n- \*\*Meaning:\*\* \n", old),
             "empty_meaning_s4": re.findall(r"#### `(\w+)`\n\n[^\n]*\n- \*\*Meaning:\*\* \n", ref)}
    examples_same = {}
    for eid, (_, b) in ex.items():
        orig = json.loads((paths.R2 / "examples" / f"{eid}.json").read_text())
        examples_same[eid] = orig == b
    (paths.RES / "reference_items.json").write_text(json.dumps({"sections": items, "cards": cards,
                                                                "examples_identical_to_s0r2": examples_same,
                                                                "example_statement_kinds": kinds}, indent=1) + "\n")

    tok, tinfo = tokenizer()
    arts = [("reference.generated", ref), ("reference.generated.without_examples", "".join(v for k, v in parts.items() if k != "examples"))]
    arts += [(f"reference.generated.part.{k}", v) for k, v in parts.items()]
    arts += [("reference.s0r2", old), ("reference.s0r2.without_examples", old.split("## 6. Worked examples")[0])]
    arts += [(f"reference.generated.kind.{k}", v) for k, v in bykind.items()]
    for f in ("batch.model.schema.json", "batch.stored.schema.json", "batch.decoding.schema.json", "tables.json"):
        p = paths.COMPILED / f
        if p.exists():
            arts.append((f, json.dumps(json.loads(p.read_text()), separators=(",", ":"), ensure_ascii=False)))
    gd = paths.COMPILED / "gliner2"
    for f in sorted(gd.glob("*.json")) if gd.exists() else []:
        arts.append((f"gliner2/{f.name}", json.dumps(json.loads(f.read_text()), separators=(",", ":"), ensure_ascii=False)))
    enc = tok.encode_batch_fast([t for _, t in arts], add_special_tokens=False)
    hash_ = json.loads((paths.COMPILED / "hash.json").read_text())
    lines = ["artifact\tbytes\ttokens\tsha256"]
    for (n, t), e in zip(arts, enc, strict=True):
        lines.append(f"{n}\t{len(t.encode('utf-8'))}\t{len(e.ids)}\t{hashlib.sha256(t.encode('utf-8')).hexdigest()}")
    lines.append(f"schema_version_hash\t\t\t{hash_['hash']}")
    lines.append(f"schema_version_hash_stable\t\t\t{hash_['stable']}")
    (paths.RES / "sizes.tsv").write_text("\n".join(lines) + "\n")
    (paths.RES / "tokenizer.json").write_text(json.dumps(tinfo, indent=1) + "\n")
    for l_ in lines:
        print(l_[:120])
    print(json.dumps(items, indent=0)[:3000])
    print(cards, examples_same)
    return 0


if __name__ == "__main__":
    sys.exit(main())
