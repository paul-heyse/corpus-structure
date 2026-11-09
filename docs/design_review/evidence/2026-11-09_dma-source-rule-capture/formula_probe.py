"""Read both exact native display products and test the released syntax input boundary."""

import json

from sqlalchemy import select

from corpus_structure.methods.contribution_adapter import adapt_formula_syntax
from corpus_structure.methods.math.pdf import FormulaOccurrence
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
)
from corpus_structure.settings import Settings

RUN, CUT, VIEW = 437, 537, 409


def main():
    with (
        open_runtime_engine(Settings(), "dma-subsection-formula-probe", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        run = table("ops.run")
        release = conn.execute(select(run.c.release_id).where(run.c.id == RUN)).scalar_one()
        reader = BoundReader(conn, RUN, open_release(conn, release), cut_id=CUT,
                             analysis=False,
                             read_budget=PublishedReadBudget(100_000, 128 * 1024**2))
        view = reader.source_view(VIEW)
        source = native_source_frame(view, ())
        prepared = PreparedNativeSources((source,), max_sources=1)
        health = {row["pointer"]: row["outcome"] for row in view.health.get("formula_outcomes", ())}
        outputs = []
        for pointer in ("#/texts/21403", "#/texts/21408"):
            (node,) = [item for item in view.items if item["self_ref"] == pointer]
            pieces = [piece for piece in view.pieces if piece.get("item_ref") == pointer]
            start, end = pieces[0]["start"], pieces[-1]["end"]
            context = NativeSourceContext(
                source, (), (SourceSlice(VIEW, start, end),), "formula syntax diagnostic",
                "dma-exact-native-formula-boundary-1", "selected original native display",
                max_chars=4096, max_pieces=16, version=2, preparation=prepared,
            )
            occurrence = FormulaOccurrence(
                view.ref.native_product.content_digest, pointer, node["text"], node.get("orig", ""),
                health.get(pointer, "unknown"),
            )
            outcomes = {}
            for policy in ("recognized_only", "captured_native_text"):
                batch = adapt_formula_syntax(context, occurrence, input_policy=policy)
                outcomes[policy] = {
                    "operations": [
                        {key: operation.get(key) for key in ("question", "outcome", "reason")}
                        for operation in batch.operations
                    ],
                    "retained_syntax_product_types": [item["semantic_type"] for item in batch.contributions],
                }
            outputs.append(dict(pointer=pointer, projected_extent=(start, end),
                                recognition_health=occurrence.recognition_health, outcomes=outcomes))
    print(json.dumps(dict(run=RUN, cut=CUT, view=VIEW, release=release, formulas=outputs,
                          semantic_binding_and_sympy_grade="not_run"), indent=2))


if __name__ == "__main__":
    main()
