"""Write `fixtures/s0`: the S0-R2 v1 reference batches as authored batches with citation frames.

    uv run python fixtures/s0/build.py

Provenance only (foundations §3.7, P0-F-3): the committed JSON files are the authority; rerun this
script only to change the conversion. It reads the spike results as data and imports no spike code:

- `results/s0r2/reference_model_v1/<U>.json`, the model-facing v1 reference batches, and
  `decisions_v1.json`, the adjudication decisions that touched them;
- `results/s0r2/sample.json`, each spike unit's page, parts and sentence offsets (the packet's
  `sN` numbering, `inputs/packet_v1/units/<U>.md`) and standing-context offsets (`cN`);
- the frozen S1 renditions the references are stored on (`results/s1/canonical/<page>.txt`,
  `results/s1/segments/<page>.jsonl`, `results/s1/sentences/<page>.provisional.jsonl`,
  `results/s1/renditions.json`).

Each S1 rendition is rebuilt as a `RenditionContent` (diagnostic attributes dropped as in
`python/corpus-structure/tests/data/locators/build.py`, sentence segments added under their parent
keys) and indexed with the product locator generator, `corpus_structure.core.locators`. The unit
key is the unit segment's generated locator; each cited sentence id maps to its sentence's
generated locator and exact canonical text.

Changes to the batches, each recorded in the file's provenance:
- `unit_ref` is the unit key, not the spike's `T1`…`U12`;
- S4's V1: `{"t": "entity", "ref": r}` becomes `{"ref": r}` (T1, U5, U11);
- S4's V2: U6's `Statement` entity `e_last_result` becomes a `statements[]` item, kind `theorem`,
  anchor `outside`; its R04 descriptor (citing sentence and quote) sits in `external_references`
  beside the batch until P0-F-2e gives the authored `outside` item its descriptor field;
- T1 is split into its two annotation units (foundations §3.7).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from corpus_structure.core.batch import AuthoredBatch, CitationFrame, cited_sentences
from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind
from corpus_structure.core.locators import LocatorIndex

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPIKES = Path("docs/design_review/evidence/2026-10-28_design-spikes")
S0R2 = SPIKES / "results/s0r2"
S1 = SPIKES / "results/s1"
UNITS = ("T1", "T2", "T3", "T4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12")
DIAGNOSTIC = frozenset({"tag", "sid", "sourceline", "roles"})
EXTERNAL_PENDING = (
    "R04 / target model §7 T1 descriptor of an authored `outside` statement: the citing sentence "
    "and quote, and the author's link target when there is one. Held beside the batch because the "
    "current AuthoredStatement has no descriptor field; P0-F-2e validates it and decides its "
    "place (migrate this field then)."
)

# T1's split (foundations §3.7): the lead-in paragraph keeps the assumption and its items; the
# definition unit `#dfn1` keeps the definition and redeclares Z, which its claims bind.
T1_LEAD_IN = {
    "statements": {"st1"},
    "entities": {"Z"},
    "claims": {"c_Z_values"},
    "unsupported": {"u_prob_space", "u_components", "u_Z_on_space"},
}
T1_DFN1 = {
    "statements": {"st2"},
    "entities": {"Z", "X", "LS", "p_loc", "p_scale"},
    "claims": {
        "c_defines", "c_X_def", "c_constr", "c_hp_loc", "c_hp_scale", "c_dom_loc", "c_dom_scale"
    },
    "unsupported": set(),
}  # fmt: skip
T1_SPLIT_NOTE = (
    "The spike's T1 is two annotation units. The lead-in file holds st1, Z, c_Z_values and the "
    "three unsupported items (all on s1-s3); the #dfn1 file holds st2 and the definition's claims "
    "and redeclares Z (local, extent section) because c_X_def and c_constr bind it. Sentence ids "
    "stay as authored (s4-s6 in the #dfn1 file); the frame makes them absolute."
)


def stem(page: str) -> str:
    return page.removesuffix(".html").replace("/", "__")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def load_rendition(page: str) -> RenditionContent:
    """The S1 rendition of `page` with its provisional sentence segments, as `RenditionContent`."""
    text = (REPO / S1 / "canonical" / f"{stem(page)}.txt").read_text(encoding="utf-8")
    rows = read_jsonl(REPO / S1 / "segments" / f"{stem(page)}.jsonl")
    rows += read_jsonl(REPO / S1 / "sentences" / f"{stem(page)}.provisional.jsonl")
    nodes: dict[str, dict[str, Any]] = {}
    for row in rows:
        node: dict[str, Any] = {
            "kind": row["kind"],
            "start": row["start"],
            "end": row["end"],
            "parse_status": row.get("parse_status", "ok"),
            "attrs": {k: v for k, v in row.get("attrs", {}).items() if k not in DIAGNOSTIC},
            "children": [],
        }
        if row.get("parse_reason") is not None:
            node["parse_reason"] = row["parse_reason"]
        nodes[row["key"]] = node
    roots = []
    for row in rows:
        parent = row["parent"]
        (roots if parent is None else nodes[parent]["children"]).append(nodes[row["key"]])
    (root,) = roots
    return RenditionContent.model_validate({"canonical_text": text, "document": root})


class Page:
    def __init__(self, page: str) -> None:
        self.page = page
        self.content = load_rendition(page)
        self.index = LocatorIndex(self.content, page)
        self.by_span: dict[tuple[SegmentKind, int, int], Segment] = {
            (s.kind, s.start, s.end): s for s in self.content.document.walk()
        }
        self.unit_keys = {u.key for u in self.index.annotation_units().units}

    def segment(self, kind: SegmentKind, start: int, end: int) -> Segment:
        return self.by_span[(kind, start, end)]

    def frame_entry(self, start: int, end: int) -> dict[str, str]:
        segment = self.segment(SegmentKind.SENTENCE, start, end)
        return {"locator": self.index.unit_key(segment), "text": self.content.text(segment)}


def migrate_v1(node: Any, path: str, log: list[str]) -> Any:
    """S4 V1: an entity reference is `{"ref": r}`, never `{"t": "entity", "ref": r}`."""
    if isinstance(node, dict):
        if set(node) == {"t", "ref"} and node["t"] == "entity":
            log.append(f"V1 {path}: {{t: entity, ref}} -> {{ref}}")
            return {"ref": node["ref"]}
        return {k: migrate_v1(v, f"{path}/{k}", log) for k, v in node.items()}
    if isinstance(node, list):
        return [migrate_v1(v, f"{path}/{i}", log) for i, v in enumerate(node)]
    return node


def migrate_v2(batch: dict[str, Any], log: list[str]) -> dict[str, dict[str, Any]]:
    """S4 V2: a `Statement` entity becomes an `outside` statement; returns its descriptors."""
    external: dict[str, dict[str, Any]] = {}
    kept = []
    for entity in batch["entities"]:
        if entity["type"] != "Statement":
            kept.append(entity)
            continue
        ref = entity["local_ref"]
        batch["statements"].append({"local_ref": ref, "kind": "theorem", "anchor": "outside"})
        log.append(
            f"V2 entity {ref} (Statement, {entity['label']!r}) -> statements[] anchor outside, "
            "kind theorem"
        )
        external[ref] = {"label": entity["label"]}
    batch["entities"] = kept
    return external


def descriptor(batch: dict[str, Any], ref: str, label: str, packet: dict[str, str]) -> dict:
    """The citing sentence and quote of an `outside` statement: the sentence of the evidence of
    the claim that names it, where the label occurs."""
    for claim in batch["claims"]:
        if claim["object"] == {"ref": ref} or claim["subject"] == ref:
            for evidence in claim["evidence"]:
                sentence = evidence["sentence"]
                if label in packet[sentence]:
                    return {"sentence": sentence, "quote": label}
    raise SystemExit(f"no citing sentence quotes {label!r} for {ref}")


def packet_sentences(unit: str) -> dict[str, str]:
    """The `[sN]`/`[cN]` lines of the spike packet, for locating a descriptor's quote."""
    text = (REPO / S0R2 / "inputs/packet_v1/units" / f"{unit}.md").read_text(encoding="utf-8")
    return dict(re.findall(r"^\[([sc][0-9]+)\] (.*)$", text, flags=re.MULTILINE))


def subset(batch: dict[str, Any], keep: dict[str, set[str]]) -> dict[str, Any]:
    out = copy.deepcopy(batch)
    for kind, refs in keep.items():
        out[kind] = [item for item in out[kind] if item["local_ref"] in refs]
        missing = refs - {item["local_ref"] for item in out[kind]}
        if missing:
            raise SystemExit(f"T1 split: {kind} {sorted(missing)} not in the batch")
    if out["alternatives"]:
        raise SystemExit("T1 split: alternatives are not assigned")
    return out


def sentence_order(sentence: str) -> tuple[str, int]:
    return (1 if sentence.startswith("c") else 0, int(sentence[1:]))


def write(name: str, record: dict[str, Any]) -> None:
    AuthoredBatch.model_validate(record["batch"])
    CitationFrame.model_validate(record["frame"])
    out = HERE / f"{name}.json"
    out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out.relative_to(REPO)}: {record['unit_key']}")


def main() -> None:
    sample = json.loads((REPO / S0R2 / "sample.json").read_text(encoding="utf-8"))
    decisions = json.loads(
        (REPO / S0R2 / "reference_model_v1/decisions_v1.json").read_text(encoding="utf-8")
    )
    renditions = json.loads((REPO / S1 / "renditions.json").read_text(encoding="utf-8"))
    pages: dict[str, Page] = {}
    for unit in UNITS:
        info = sample["units"][unit]
        page_name = info["page"]
        page = pages.setdefault(page_name, Page(page_name))
        source = S0R2 / "reference_model_v1" / f"{unit}.json"
        raw = json.loads((REPO / source).read_text(encoding="utf-8"))
        log: list[str] = []
        batch = migrate_v1(raw, "", log)
        labels = migrate_v2(batch, log)
        packet = packet_sentences(unit)
        external = {
            ref: descriptor(batch, ref, value["label"], packet) for ref, value in labels.items()
        }
        offsets = {s["id"]: (s["start"], s["end"]) for p in info["parts"] for s in p["sentences"]}
        offsets |= {c["id"]: (c["start"], c["end"]) for c in info["context"]}
        provenance_base = {
            "spike_unit": unit,
            "source": str(source),
            "packet": str(S0R2 / "inputs/packet_v1/units" / f"{unit}.md"),
            "stored_reference": str(S0R2 / "reference_v1" / f"{unit}.json"),
            "rendition": {
                "page": page_name,
                "source_uri": renditions[page_name]["source_uri"],
                "spike_document_key": info["document_key"],
                "spike_rendition_key": info["rendition_key"],
                "built_from": str(S1),
                "sentences": "results/s1/sentences/<page>.provisional.jsonl "
                f"({sample['sentence_variant']})",
            },
            "decisions": [
                {"item": d["item"], "decision": d["decision"]}
                for d in decisions
                if d["unit"] == unit
            ],
            "migrations": log,
        }
        if unit == "T1":
            lead, dfn = info["parts"]
            parts = [("T1-leadin", lead, T1_LEAD_IN, []), ("T1-dfn1", dfn, T1_DFN1, None)]
        else:
            (part,) = info["parts"]
            parts = [(unit, part, None, None)]
        for name, part, keep, decisions_here in parts:
            kind = SegmentKind(part["kind"])
            segment = page.segment(kind, part["start"], part["end"])
            unit_key = page.index.unit_key(segment)
            if unit_key not in page.unit_keys:
                raise SystemExit(f"{name}: {unit_key} is not an annotation unit")
            body = subset(batch, keep) if keep is not None else copy.deepcopy(batch)
            body["unit_ref"] = unit_key
            validated = AuthoredBatch.model_validate(body)
            cited = set(cited_sentences(validated))
            cited |= {d["sentence"] for d in external.values()}
            frame = {s: page.frame_entry(*offsets[s]) for s in sorted(cited, key=sentence_order)}
            provenance = copy.deepcopy(provenance_base)
            if decisions_here is not None:
                provenance["decisions"] = decisions_here
            if unit == "T1":
                provenance["split"] = T1_SPLIT_NOTE
            record: dict[str, Any] = {"unit_key": unit_key, "batch": body, "frame": frame}
            if external:
                record["external_references"] = {
                    "pending": EXTERNAL_PENDING,
                    "descriptors": external,
                }
            record["provenance"] = provenance
            write(name, record)


if __name__ == "__main__":
    main()
