"""Frozen actual source -> CPU report -> released private candidate shape/location check."""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from corpus_structure.methods.gliner import GlinerInput, GlinerProfile
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.record_assembly import (
    NativeRecordGroup,
    RoleInput,
    assemble_records,
)
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import (
    NativeFrameSource,
    NativeProposalFrame,
    ProposalSentence,
)
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    target = HERE / f"attempt-{args.attempt:05d}.json"
    if args.attempt < 1 or target.exists():
        raise ValueError("select a new positive attempt; retained attempts are immutable")
    main_evidence = args.main_root / "docs/design_review/evidence/2026-11-03_m1-gliner-runtime"
    source_path = main_evidence / "mapped-context-00001.json"
    profile_path = main_evidence / "attempt-00005.json"
    receipt = dict(
        outcome="failed",
        claim=(
            "actual frozen-source/CPU/private candidate shape and location integration only; "
            "no accepted release admission, publication, source-reading accuracy or all-family qualification"
        ),
        verified_date="2026-11-03",
        source_context_sha256=digest(source_path),
        profile_input_sha256=digest(profile_path),
        implementation_sha256={
            name: digest(ROOT / "python/corpus-structure/src/corpus_structure" / name)
            for name in (
                "methods/record_assembly.py",
                "methods/record_packs.py",
                "methods/gliner.py",
                "methods/gliner_worker.py",
                "semantic/source_contexts.py",
                "semantic/record_contracts.py",
            )
        },
        helper_sha256=digest(Path(__file__)),
        database_access="not_requested",
    )
    worker = None
    try:
        frozen = json.loads(source_path.read_text())
        frame_values = dict(frozen["primary"])
        frame_values["native_product"] = ProductReference(**frame_values["native_product"])
        frame_values["sentences"] = tuple(
            ProposalSentence(**row) for row in frame_values["sentences"]
        )
        if "context_sources" in frame_values:
            if frame_values["context_sources"]:
                raise ValueError("probe does not flatten proposal-frame ancestor contexts")
            frame_values["context_sources"] = ()
            frame = NativeProposalFrame(**frame_values)
        else:
            frame = NativeFrameSource(**frame_values)
        if frozen["related"] or frozen["retrievals"]:
            raise ValueError("probe explicitly supports this frozen single-source context only")
        context = NativeSourceContext(
            frame,
            (),
            tuple(SourceSlice(**row) for row in frozen["pieces"]),
            frozen["purpose"],
            frozen["policy"],
            frozen["terminal_reason"],
            max_chars=frozen["max_chars"],
            max_pieces=frozen["max_pieces"],
            max_sources=frozen["max_sources"],
            version=frozen["version"],
        )
        if (
            context.dependency_digest != frozen["dependency_digest"]
            or context.text != frozen["text"]
        ):
            raise ValueError("frozen context reconstruction differs")
        prepared = prepare_release(
            observation_inputs(
                SourceBundle(
                    "statistics_semantic",
                    (
                        SourceArtifact(
                            "statistics_semantic",
                            (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                        ),
                        SourceArtifact(
                            "semantic_core",
                            (
                                ROOT
                                / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                            ).read_bytes(),
                        ),
                    ),
                )
            )
        )
        profile_values = json.loads(profile_path.read_text())["profile"]
        profile_values["snapshot"] = Path(profile_values["snapshot"])
        profile_values["artifact_hashes"] = tuple(
            tuple(entry) for entry in profile_values["artifact_hashes"]
        )
        profile = GlinerProfile(**profile_values)
        pack = family_pack(
            prepared,
            contract="DefinitionRecordFields",
            anchor_role="term",
            descriptions={
                "term": "The locally defined statistical term",
                "defining_text": "The exact passage defining or explaining that term",
            },
        )
        receipt.update(
            release_id=prepared.release_id,
            pack=asdict(pack),
            context_digest=context.dependency_digest,
            source_pin=asdict(frame.native_product),
        )
        worker = GlinerWorker(profile)
        (report,) = worker.extract(pack, (GlinerInput.from_context(context),))
        receipt["report"] = asdict(report)
        supplements = {
            index: NativeRecordGroup(
                (RoleInput("scope", native_pointer="#/groups/4265"),),
                "actual frozen source-view section scope",
            )
            for index, _ in enumerate(report.raw.get("definition", []))
        }
        result = assemble_records(
            prepared,
            context,
            pack,
            report,
            contract="DefinitionRecordFields",
            anchor_role="term",
            policy_version="m1-private-component-only",
            supplements=supplements,
        )
        receipt.update(
            records=[row.model_dump(mode="json") for row in result.records],
            diagnostics=[asdict(row) for row in result.diagnostics],
            dependencies=result.dependencies,
            candidate_count=len(result.records),
            coordinate_texts=result.coordinate_texts,
        )
        if not result.records:
            receipt.update(
                outcome="partial",
                terminal_reason="actual CPU report produced no independently located private candidate occurrence",
            )
        else:
            receipt.update(
                outcome="passed",
                terminal_reason="actual CPU candidates passed released private shape and coordinate binding; unresolved fields remain explicit",
            )
    except Exception as error:
        receipt.update(
            error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc()
        )
    finally:
        if worker is not None:
            worker.close()
            receipt["worker_joined"] = worker.closed and worker.pid is None
        with target.open("x") as handle:
            json.dump(receipt, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    print(
        json.dumps(
            {
                name: receipt.get(name)
                for name in ("outcome", "candidate_count", "terminal_reason", "worker_joined")
            }
        )
    )
    if receipt["outcome"] == "failed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
