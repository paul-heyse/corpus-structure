"""Bounded PM2-07 diagnostic; no evaluation or publication authority."""

import json
import runpy
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import yaml

from corpus_structure.methods.definition_applicability import DefinitionComponentsConfig
from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.model_observation import released_pack, released_policy
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import StructuralInput

HERE = Path(__file__).resolve().parent
OLDER = HERE.parent / "2026-11-09_pm2-gliner-boundary"


def score(worker, pack, mapping, spans):
    try:
        return worker.diagnose(pack, mapping, tuple(spans)).raw["explicit"]
    except GlinerRefused as exc:
        return {"refusal": str(exc)}


def main():
    original = runpy.run_path(str(OLDER / "inspect_boundaries.py"))
    adoption = original["ADOPTION"]
    inputs = StructuralInput.model_validate_json((adoption / "target-inputs.json").read_bytes())
    release = json.loads((adoption / "targets-ready.json").read_bytes())["release_id"]
    prepared, layouts = original["prepare"](inputs, release)
    policy = released_policy(prepared)
    defaults = yaml.safe_load(original["CONFIG"].read_bytes())["configs"][
        "extract.m1_candidates"
    ]["default"]
    config = DefinitionComponentsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        target_ids=tuple(p.passage_id for p in inputs.passages),
        profile={
            key: defaults[key]
            for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")
        },
    )
    pack = released_pack(release, policy, config=config.model_dump())
    assert config.profile is not None
    cases = {}
    with closing(GlinerWorker(config.profile)) as worker:
        for passage in inputs.passages:
            retained = layouts[passage.source_ref]
            mapping, clipped = original["read_map"](passage, retained)
            baseline = worker.diagnose(pack, mapping).raw
            proposed = tuple(
                dict.fromkeys(
                    tuple(row["input_chars"])
                    for row in baseline["ordinary"]
                    if row["input_chars"] is not None
                    and not any(
                        a < row["input_chars"][1] and row["input_chars"][0] < b
                        for a, b in clipped
                    )
                )
            )
            independently_nominated = tuple(
                dict.fromkeys(
                    (tok.start - passage.start, tok.end - passage.start)
                    for block in retained.annotations
                    for tok in block.tokens
                    if passage.start <= tok.start < tok.end <= passage.end
                    and tok.role == "prose"
                    and getattr(tok, "pos", None) in {"NOUN", "PROPN", "VERB"}
                )
            )[:12]
            eligible = []
            refused = {}
            for name, span in original["SPANS"][passage.passage_id].items():
                start, end = span
                if any(a < end and start < b for a, b in clipped):
                    refused[name] = "frozen window clips a protected source atom"
                    continue
                check = score(worker, pack, mapping, (span,))
                if isinstance(check, dict):
                    refused[name] = check["refusal"]
                else:
                    eligible.append(span)
            authored = tuple(dict.fromkeys(eligible))
            prefix = proposed[: max(0, 32 - len(independently_nominated))]
            union = tuple(dict.fromkeys(independently_nominated + prefix))
            cases[passage.passage_id] = {
                "scope": mapping.scope_digest,
                "ordinary": len(proposed),
                "independently_nominated": independently_nominated,
                "independent_scores": score(worker, pack, mapping, independently_nominated),
                "union": union,
                "union_scores": score(worker, pack, mapping, union),
                "authored_diagnostic": authored,
                "authored_packed": score(worker, pack, mapping, authored),
                "authored_reordered": score(worker, pack, mapping, authored[::-1]),
                "authored_refusals": refused,
            }
        attribute_results = {}
        for index, sentence in enumerate(
            (
                "The operator approves the change but does not approve the exception.",
                "The operator may close the case, but must not close the audit.",
                "The permit was not signed. The operator approves the request.",
                "The status of the request is unclear.",
            )
        ):
            choices = {
                "polarity": {
                    "labels": ["affirmed", "negated", "unresolved"],
                    "applies_to": ["predicate"],
                    "qualify_labels": True,
                }
            }
            variants = {}
            for name, extra in (("baseline", {}), ("attribute", {"entity_attributes": choices})):
                diagnostic = GlinerPack.from_declaration(
                    release, {"entities": ["predicate"], **extra}, version="native-local-v1"
                )
                (result,) = worker.extract(
                    diagnostic,
                    (GlinerInput(f"predicate-{index}", sha256(sentence.encode()).hexdigest(), sentence),),
                    threshold=0.5,
                )
                variants[name] = result.raw
            attribute_results[sentence] = variants
    print(
        canonical_bytes(
            {
                "release": release,
                "pack": pack.fingerprint,
                "profile": config.profile.fingerprint,
                "scope": inputs.identity,
                "cases": cases,
                "attribute_diagnostic": attribute_results,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
