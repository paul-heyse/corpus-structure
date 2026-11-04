"""Inspect retained formula contexts and compare source-only interval budgets."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from sqlalchemy import select

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.pdf_hierarchy import project_section_nodes
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.source_preparation import POLICY, prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    task, config, run = map(table, ("ops.task", "ops.method_config", "ops.run"))
    with (
        open_runtime_engine(Settings(), "m1-formula-ancestor-probe", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        row = conn.execute(select(task.c.unit_id, config.c.params, run.c.release_id)
            .join(config, config.c.id == task.c.method_config_id)
            .join(run, run.c.id == task.c.run_id).where(task.c.id == 27, task.c.run_id == 10)
        ).mappings().one()
        reader = BoundReader(conn, 10, open_release(conn, row["release_id"]), analysis=False,
                             read_budget=PublishedReadBudget(40_000, 256 * 1024**2))
        view = reader.source_view(row["unit_id"])
        params = row["params"]
        profile = AnnotationProfile(SentenceConfig.model_validate(params["sentences"]))
        annotations, errors, _ = consume_annotations(reader, view, profile)
        retained = reader.source_result(view.ref.id, "extract.m1_candidates")
        assert retained is not None
        detail = retained["parse_detail"]
        primary = {node["self_ref"]: node for node in view.items}
        nodes = {node["self_ref"]: node for node in (*view.items, *view.ancestors)}
        formula_rows = []
        for index, old in enumerate(detail["contexts"]):
            if old["families"] != ["formula_context"]:
                continue
            pointer = old["region"]
            chain, current, seen = [], nodes[pointer], {pointer}
            while (parent := current.get("parent", {}).get("$ref")) in nodes and parent not in seen:
                seen.add(parent)
                current = nodes[parent]
                item = dict(pointer=parent, label=current.get("label"), in_primary=parent in primary,
                            declared_child=any(c.get("$ref") in seen - {parent}
                                               for c in current.get("children", ())))
                try:
                    projected = project_section_nodes(primary, "", parent, "descendant",
                                                      section_refs=frozenset((parent,)))
                    item.update(chars=len(projected.text), intervals=len(projected.pieces),
                                has_text_beyond_formula=bool(projected.text.replace(
                                    view.text[old["start"]:old["end"]], "", 1).strip()))
                except (ValueError, KeyError, TypeError):
                    item["projection"] = "unavailable_in_primary"
                chain.append(item)
            formula_rows.append(dict(
                context=index, pointer=pointer, old_start=old["start"], old_end=old["end"],
                old_chars=old["end"] - old["start"], old_pieces=old.get("pieces", ()),
                old_retrievals=old.get("retrievals", ()),
                annotation_block_ids=[a.block_id for a in annotations
                                      if a.block_id in {pointer, *(r["pointer"] for r in chain)}],
                chain=chain,
            ))
        comparisons = []
        for bound in (64, 128):
            prepared = prepare_source(
                view, profile=profile, persisted_annotations=annotations, annotation_errors=errors,
                reader=reader, max_chars=2048, max_pieces=bound,
                max_annotation_chars=params["max_annotation_chars"],
                read_budget=PublishedReadBudget(40_000, 256 * 1024**2),
            )
            serialized, refused = [], []
            for index, selection in enumerate(prepared.selections):
                try:
                    context = selection.context(prepared.source, related=prepared.related,
                        preparation=prepared.preparation, max_chars=2048, max_pieces=bound)
                    serialized.append(dict(index=index, family=selection.families,
                        chars=len(context.text), intervals=len(context.intervals),
                        extra_chars=len(context.text) - (selection.end - selection.start),
                        local_dispositions=selection.local_dispositions))
                except ValueError as error:
                    refused.append(dict(index=index, reason=str(error)))
            comparisons.append(dict(
                max_chars=2048, max_pieces=bound, selections=len(prepared.selections),
                family_counts=dict(Counter(f for s in prepared.selections for f in s.families)),
                region_outcomes=dict(Counter(r.outcome for r in prepared.regions)),
                local_resource_limits=sum(d[1] == "resource_limit" for s in prepared.selections
                                          for d in s.local_dispositions),
                retrieval_resource_limits=sum(r.outcome.value == "resource_limit"
                                              for s in prepared.selections for r in s.retrievals),
                serialized=serialized, serialization_refusals=refused,
            ))
        result = dict(run_id=10, task_id=27, source_view_id=view.ref.id,
            release_id=row["release_id"], projection_digest=view.ref.projection_digest,
            stored_policy=detail["policy"], current_policy=POLICY,
            stored_formula_contexts=len(formula_rows), formulas=formula_rows, comparisons=comparisons,
            scope="retained source/annotation preparation only; no model or scientific claim")
    path = Path(sys.argv[1])
    with path.open("xb") as stream:
        stream.write(canonical_bytes(result))
    print(json.dumps(dict(stored_formula_contexts=len(formula_rows), comparisons=[
        {k: v for k, v in c.items() if k != "serialized"} for c in comparisons
    ])))


if __name__ == "__main__":
    main()
