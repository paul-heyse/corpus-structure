"""Exercise the source layout and declaration replay on exact retained native evidence."""

import json
from dataclasses import asdict, replace
from pathlib import Path

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.methods.definition_declaration import replay_declaration_chain
from corpus_structure.methods.pm2_result import pm2_unit_result
from corpus_structure.methods.pm2_source import HANLP_SEAM_LAYOUT
from corpus_structure.orchestrate.pm2_stage import ParserScope, _sentences, _work
from corpus_structure.semantic.analysis_contracts import prepare_text_policy
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.settings import Settings

SIBLINGS = Path(__file__).resolve().parents[1]


def source_view(conn, pin):
    conn.execute(
        select(func.ops.validate_structural_source(literal(pin.model_dump(mode="json"), JSONB)))
    )
    view = load_source_view(
        conn,
        pin.source_view_id,
        analysis=False,
        read_budget=PublishedReadBudget(100_000, 256 * 1024 * 1024),
    )
    return replace(view, analysis_enabled=True, text_policy=prepare_text_policy())


def work(view, pin, startup, extent, layout_policy):
    frame = native_source_frame(view, ())
    return _work(
        ParserScope(
            source=pin,
            extent=extent,
            profile={"provider": "hanlp", "device": "cpu", "startup": startup},
            layout_policy=layout_policy,
        ),
        view,
        frame,
        PreparedNativeSources((frame,), max_sources=1),
        _sentences(view),
    )


def main():
    inputs = StructuralInput.model_validate_json(
        (SIBLINGS / "2026-11-09_pm2-adoption/raw/target-inputs.json").read_bytes()
    )
    canonical, corrected = json.loads(
        (SIBLINGS / "2026-11-09_pm2-definition-hanlp/raw/hanlp-layout.json").read_bytes()
    )
    passage = next(row for row in inputs.passages if row.passage_id == "binomial-distribution")
    density = next(row for row in inputs.passages if row.passage_id == "constant-density")
    pin = next(row for row in inputs.sources if row.identity == passage.source_ref)
    density_pin = next(row for row in inputs.sources if row.identity == density.source_ref)
    with (
        open_runtime_engine(Settings(), "pm2-declaration-chain-probe", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        view = source_view(conn, pin)
        density_view = source_view(conn, density_pin)
        # Archived declarations supply only the typed output shapes for this in-memory probe.
        # The archive is not authorized to settle this new layout or witness.
        prepared = open_release(conn, corrected["analysis_release"])
    old = work(view, pin, canonical["startup"], tuple(canonical["extent"]), None)
    new = work(view, pin, corrected["startup"], tuple(corrected["extent"]), HANLP_SEAM_LAYOUT)
    if old.request != canonical["request"] or new.request != corrected["request"]:
        raise ValueError("this source does not reproduce the two retained native requests")
    density_sentences = [
        row for row in _sentences(density_view) if row[0] < density.end and density.start < row[1]
    ]
    control = work(
        density_view,
        density_pin,
        canonical["startup"],
        (density_sentences[0][0], density_sentences[-1][1]),
        HANLP_SEAM_LAYOUT,
    )
    if control.mapping.layout.outcome != "unchanged":
        raise ValueError("the exact policy changed the constant-density control")
    result = pm2_unit_result(
        new.ref,
        new.mapping,
        profile=new.profile.startup,
        request=new.request,
        reply=corrected["response"],
        question=new.question,
        operation_version=new.method.version,
        input_digest=new.input_digest,
        prepared=prepared,
    )
    body = dict(
        method=new.method.name,
        operation_version=new.method.version,
        input_hash=new.input_digest,
        source=new.ref.unit_key,
        release_id=prepared.release_id,
        contributions=result.contributions,
        contribution_operations=result.contribution_operations,
    )
    naming = next(row for row in result.contributions if row["item_key"] == "s2/predicate/12")
    reference = RetainedContributionRef(
        contribution_id=naming["contribution_id"],
        project_id=pin.project_id,
        release_id=prepared.release_id,
        run_id=1,
        cut_id=1,
        result_revision=0,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="in-memory-fixture-only",
    )
    frame = native_source_frame(view, ())
    component = replay_declaration_chain(body, result.parse_detail, frame, pin, passage, reference)
    # An independently located alternative predicate cannot carry the naming witness.
    alternative = next(row for row in result.contributions if row["item_key"] == "s1/predicate/2")
    try:
        replay_declaration_chain(
            body,
            result.parse_detail,
            frame,
            pin,
            passage,
            reference.model_copy(update={"contribution_id": alternative["contribution_id"]}),
        )
    except ValueError as exc:
        if "different retained predicate" not in str(exc):
            raise
        wrong_predicate = str(exc)
    else:
        raise ValueError("declaration replay accepted a different retained predicate")
    print(
        canonical_bytes(
            {
                "custody": "read-only source; genuine retained CPU HanLP response; in-memory envelope",
                "parser_operations": [old.method.version, new.method.version],
                "input_digests": [old.input_digest, new.input_digest],
                "layout": asdict(new.mapping.layout),
                "constant_density_layout": asdict(control.mapping.layout),
                "term": component.term.model_dump(mode="json"),
                "content": component.content.model_dump(mode="json"),
                "basis": component.declaration_chain.model_dump(mode="json", exclude={"parser"}),
                "wrong_predicate": wrong_predicate,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
