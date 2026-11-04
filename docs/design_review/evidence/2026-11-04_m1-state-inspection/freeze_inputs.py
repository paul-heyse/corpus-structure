"""Freeze source-only development canaries and schemas before model calls."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from corpus_structure.methods.gliner import GlinerPack, GlinerProfile
from corpus_structure.methods.m1_source import FAMILIES
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).parent
STATES = {
    "present": "The named record's requested role is explicitly stated and attached to that record in the supplied source text.",
    "unstated": "The role applies to the named record, but the entire supplied source text does not state it for that record.",
    "inapplicable": "The role cannot apply to this named record; not merely missing wording or a missing extraction.",
    "unresolved": "The supplied text leaves ambiguous whether wording states this role or attaches it to the named record.",
}


def write_new(name, value):
    with (HERE / name).open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    result, task, config, views = map(table, (
        "ops.task_result", "ops.task", "ops.method_config", "kb.source_view"))
    release = json.loads((HERE.parent / "2026-11-04_m1-cpu-readings/attempt-010/source-run.json").read_text())["release_id"]
    # Only task 27 in actual development run 10; no reference or final data reads.
    with open_runtime_engine(Settings(), "m1-state-canary-freeze", purpose="read") as engine, engine.connect() as conn:
        row = conn.execute(select(result.c.body, config.c.params).join(
            task, task.c.id == result.c.task_id).join(config, config.c.id == task.c.method_config_id
        ).where(task.c.id == 27, task.c.run_id == 10)).mappings().one()
        detail = source_python(row["body"]["parse_detail"])
        cfg = SimpleNamespace(**row["params"])
        profile = GlinerProfile(Path(cfg.snapshot), cfg.checkpoint, cfg.revision,
                               tuple(tuple(entry) for entry in cfg.artifact_hashes),
                               threads=cfg.threads, timeout_seconds=float(cfg.timeout_seconds))
        source_ids = {piece["source_view_id"] for index in (4, 55, 57)
                      for piece in detail["contexts"][index]["pieces"] if "source_view_id" in piece}
        texts = dict(conn.execute(select(views.c.id, views.c.projection).where(views.c.id.in_(source_ids))).all())
        prepared = open_release(conn, release)
    selected = [
        (4, "definition", "distribution functionm(\\\\omega)", "Literal 'is defined to be' wording in source, first such actual context in task 27; no output-based selection."),
        (55, "definition", '"memoryless" property', "Literal 'is called' naming wording in source, first such actual context in task 27; no output-based selection."),
        (57, "assertion", "a coin", "Explicit source clause says a coin has probability p of heads; source-only assertion canary for predicate versus subject anchors."),
    ]
    frozen = []
    retained = []
    for index, family, name, reason in selected:
        context = detail["contexts"][index]
        text = "".join(piece["text"] if "text" in piece else
                       texts[piece["source_view_id"]]["text"][piece["start"]:piece["end"]]
                       for piece in context["pieces"])
        existing = next(entry["report"] for entry in detail["reports"]
                        if entry.get("context") == index and entry.get("family") == family and "report" in entry)
        consumed = text + existing["preparation"]["synthetic_suffix"]
        if hashlib.sha256(consumed.encode()).hexdigest() != existing["preparation"]["consumed_text_sha256"]:
            raise RuntimeError("reconstructed text differs from actual consumed context")
        contract, anchor = FAMILIES[family]
        pack = family_pack(prepared, contract=contract, anchor_role=anchor,
                           descriptions=cfg.pack_descriptions.get(family), source_inspection=True)
        if pack.fingerprint != existing["pack"]:
            raise RuntimeError("reconstructed baseline schema differs from task 27")
        baseline = json.loads(pack.declaration_json)
        described = json.loads(pack.declaration_json)
        structure = described["structures"][family]
        if family == "assertion":
            structure["anchor"] = "subject"
        else:
            for field in structure["fields"]:
                if field["name"].endswith("__state"):
                    role = field["name"].removesuffix("__state")
                    field["description"] = (
                        f"For each definition record, inspect the entire supplied context for its {role}. "
                        "Classify the relation to that SAME term anchor, not another term. "
                        + " ".join(f"{label}: {meaning}" for label, meaning in STATES.items())
                    )
        roles = ("term", "defining_text") if family == "definition" else ("subject", "predicate", "object")
        questions = {
            "term": f"Does the source explicitly name {name} as the term being defined?",
            "defining_text": f"Does the source explicitly state what {name} means, its defining criterion, or its same-concept naming relation?",
            "subject": f"Does the source explicitly state {name} as the subject of the probability-of-heads assertion?",
            "predicate": f"Does the source explicitly state the predicate relating {name} to its probability of coming up heads?",
            "object": f"Does the source explicitly state the probability value or expression completing the probability-of-heads assertion about {name}?",
        }
        classification = {"classifications": [dict(
            task=role + "__state", labels=STATES, multi_label=False,
            prompt=(questions[role] + " Inspect all supplied text for this named record only. "
                    "Choose present for stated and attached wording; unstated requires an applicable role not stated in this scope; "
                    "choose unresolved for ambiguous meaning or attachment. Do not treat a decoder omission as source absence."),
        ) for role in roles]}
        variants = [dict(name="baseline_actual_pack", schema=baseline),
                    dict(name="described_state_pack" if family == "definition" else "described_subject_anchor", schema=described),
                    dict(name="separate_named_state_classification", schema=classification)]
        for variant in variants:
            candidate_pack = GlinerPack.from_declaration(release, variant["schema"])
            variant["pack_fingerprint"] = candidate_pack.fingerprint
        frozen.append(dict(context_index=index, family=family, named_record=name, selection_reason=reason,
                           context_id=existing["context_id"], context_digest=existing["context_digest"],
                           text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(), source_selection=context,
                           variants=variants))
        retained.append(dict(context_index=index, family=family, report=existing))
    payload = dict(frozen_at=datetime.now(timezone.utc).isoformat(), run_id=10, task_id=27,
                   source_view_ids=sorted(source_ids), source_group="grinstead-snell", scope="feature-fit/development only",
                   release_id=release, maximum_model_calls=9, selection_precedes_new_model_outputs=True,
                   threshold=float(cfg.threshold), profile=asdict(profile), contexts=frozen,
                   quality_claim="not established; no final/reference data read")
    payload["profile"]["snapshot"] = str(payload["profile"]["snapshot"])
    write_new("frozen-inputs.json", payload)
    # Stored baseline reports are retained only after source/schema selection is frozen.
    write_new("retained-baseline-reports.json", retained)
    print(json.dumps({"outcome": "passed", "frozen_contexts": len(frozen), "maximum_calls": 9,
                      "input_sha256": hashlib.sha256((HERE / "frozen-inputs.json").read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
