"""Grade a completed run against explicitly supplied, source-only authored references.

The historical transfer fixture and existing grades are unchanged. Invocation always names the
new run, project and fixture; no historical run is selected by a default in this script.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.evidence import RenditionContent, SegmentKind
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.evaluate.semantic import (
    ReferenceError,
    create_reference_set,
    record_pass,
    reference_evaluate,
    split_documents,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import ProposalFrame, ProposalSentence
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    original = args.fixture.read_bytes()
    fixture = json.loads(original)
    # A single batch retains its exact original bytes; a trace collection gives each batch
    # its own explicitly authored byte representation without consulting predicted answers.
    batches = fixture if isinstance(fixture, list) else [fixture]
    authored = [json.dumps(batch, ensure_ascii=False).encode() for batch in batches]
    if not isinstance(fixture, list):
        authored = [original]
    keys = [batch["unit_ref"] for batch in batches]
    if len(set(keys)) != len(keys):
        raise ReferenceError("reference fixture repeats a source unit")
    with (
        open_runtime_engine(Settings(), "ci-regeneration-reference", purpose="evaluate") as engine,
        engine.begin() as conn,
    ):
        runs = table("ops.run")
        release_id = conn.execute(
            select(runs.c.release_id).where(
                runs.c.id == args.run, runs.c.project_id == args.project
            )
        ).scalar_one()
        split_documents(conn, args.project, release_id=release_id)
        documents, splits = table("kb.document"), table("eval.document_split")
        pages = {parse_locator(key).page for key in keys}
        assigned = set(
            conn.execute(
                select(splits.c.split)
                .join(documents, splits.c.source_uri == documents.c.source_uri)
                .where(
                    splits.c.project_id == args.project,
                    documents.c.project_id == args.project,
                    documents.c.meta["page"].astext.in_(pages),
                )
            ).scalars()
        )
        if len(assigned) != 1:
            raise ReferenceError("all fixture pages must belong to one bound document split")
        reference = create_reference_set(
            conn,
            project_id=args.project,
            source_run_id=args.run,
            label=args.label,
            split=assigned.pop(),
            size=len(keys),
            forced=keys,
        )
        if set(reference["units"]) != set(keys):
            raise ReferenceError("sample policy requires source units not authored by this fixture")
        units, renditions = table("eval.reference_unit"), table("kb.rendition")
        for batch, raw in zip(batches, authored, strict=True):
            unit_id = reference["units"][batch["unit_ref"]]
            source = conn.execute(
                select(renditions)
                .join(units, units.c.rendition_id == renditions.c.id)
                .where(units.c.id == unit_id)
            ).mappings().one()
            content = RenditionContent.model_validate(source["content"])
            index = LocatorIndex(content, parse_locator(batch["unit_ref"]).page)
            sentences = {}
            for family in ("claims", "unsupported", "identity_exclusions"):
                for item in batch.get(family, ()):
                    for citation in item["evidence"]:
                        matches = [
                            (segment, locator)
                            for segment, locator in index
                            if segment.kind == SegmentKind.SENTENCE
                            and content.canonical_text[segment.start:segment.end]
                            == citation["quote"]
                        ]
                        if len(matches) != 1:
                            raise ReferenceError(
                                "reference quotation must independently locate one source sentence"
                            )
                        segment, locator = matches[0]
                        sentence = ProposalSentence(
                            citation["sentence"], str(locator), segment.start, segment.end
                        )
                        previous = sentences.setdefault(sentence.id, sentence)
                        if previous != sentence:
                            raise ReferenceError("reference sentence id has conflicting quotations")
            frame = ProposalFrame(
                batch["unit_ref"], content.canonical_text, tuple(sentences.values())
            )
            record_pass(
                conn,
                unit_id=unit_id,
                pass_kind="C",
                actor="automated-independent-fixture",
                authored=raw,
                frame=frame,
            )
        grade = reference_evaluate(
            conn, project_id=args.project, run_id=args.run, set_id=reference["set_id"]
        )
        print(grade.model_dump_json())


if __name__ == "__main__":
    main()
