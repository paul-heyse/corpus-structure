"""Assess the book's exact affine form after reading its settled ordered source witness."""

import argparse
import json
from pathlib import Path

from corpus_structure.evaluate.affine import assess_exact_affine
from corpus_structure.methods.math.prepared import PreparedMathInput
from corpus_structure.methods.scoped_relations import ScopedRelationsOrderedConfig
from corpus_structure.methods.witnessed_source_links import ordered_witness_selection
from corpus_structure.semantic.analysis_contracts import (
    SymbolDeclaration,
    prepare_interpretation_context,
)
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def assess(request, run_id, task_id):
    config = ScopedRelationsOrderedConfig.model_validate(request["configuration"])
    if config.inputs is None or config.ordered_formula_witness is None:
        raise ValueError("request lacks the exact ordered witness input")
    (source,) = config.inputs.sources
    (passage,) = config.inputs.passages
    pin = {
        "source": request["source_key"],
        "source_view_id": source.source_view_id,
        "native_product_task_id": source.native_task_id,
        "product_key": source.native_product_key,
        "product_digest": source.native_content_digest,
        "projection_digest": source.projection_digest,
        "recipe_digest": source.recipe_digest,
    }
    original = ((passage.passage_id, passage.start, passage.end, passage.effective_version),)
    keys = (
        operation_identity(
            "source_witnessed_links",
            "2",
            pin,
            ordered_witness_selection(passage, config.ordered_formula_witness),
        ),
        operation_identity("source_formula_occurrences", "1", pin, original),
    )
    with (
        open_runtime_engine(Settings(), "pm2-settled-affine", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        selected = bind_completed_result(conn, run_id)
        release = selected.prepared
        if release.release_id != request["release"]:
            raise ValueError("settled run differs from the requested release")
        inventory = read_source_contributions(
            conn,
            prepared=release,
            run_id=run_id,
            cut_id=selected.completed_cut_id,
            source_view_id=source.source_view_id,
            selected_task_id=task_id,
            method="structure.scoped_relations",
            method_version="11",
            operation_keys=keys,
            include_details=True,
            limit=20,
        )
    if inventory.more:
        raise ValueError("selected witness read is incomplete")
    rows = {row["contribution_id"]: row for row in inventory.contributions}
    operations = {row["operation_key"]: row for row in inventory.operations}
    (witness,) = [
        op
        for op in operations.values()
        if op["question"] == "source_witnessed_links" and op["operation_version"] == "2"
    ]
    if witness["outcome"] != "succeeded":
        raise ValueError("no settled affirmative ordered declaration")
    (edge,) = [
        row
        for row in rows.values()
        if row["operation_key"] == witness["operation_key"] and row["kind"] == "relation"
    ]
    use, target = (rows[id_] for id_ in edge["members"])

    def exact(row):
        return source_python(row["value"])

    if (
        edge["component"]["attachment_kind"] != "declares"
        or exact(use)["role"] != "formula_symbol"
        or exact(use)["text"] != "Z"
        or len(target["anchors"]) != 2
        or " ".join(exact(target)["text"].split()) != "standard normal random variable"
    ):
        raise ValueError("settled witness differs from the protected source controls")
    formula = "X = σZ + μ"
    a = passage.text.index(formula)
    start = passage.start + a
    parameters = "parameters μ and σ"
    par_start = passage.text.index(parameters)
    by_token = {
        exact(row)["text"]: row
        for row in rows.values()
        if operations[row["operation_key"]]["question"] == "source_formula_occurrences"
        and exact(row)["role"] == "formula_symbol"
        and start <= exact(row)["start"] < exact(row)["end"] <= start + len(formula)
    }
    if (
        set(by_token) != {"X", "Z", "σ", "μ"}
        or by_token["Z"]["contribution_id"] != use["contribution_id"]
    ):
        raise ValueError("formula carrier inventory differs from the ordered witness")
    # X denotes this equation's output only. This mathematical input gives it
    # no separate declaration link or external identity.
    evidence = {
        "X": (by_token["X"]["contribution_id"], exact(by_token["X"])["start"]),
        "Z": (edge["contribution_id"], exact(use)["start"]),
        r"\sigma": (parameters, passage.start + par_start + parameters.index("σ")),
        r"\mu": (parameters, passage.start + par_start + parameters.index("μ")),
    }
    context = prepare_interpretation_context(
        release,
        macros={},
        source_id=source.identity,
        scope=passage.passage_id,
        kind="formula",
        demand="symbolic",
        offset=start,
        declarations=tuple(
            SymbolDeclaration(
                symbol,
                "variable",
                "source",
                witness_ref,
                source.identity,
                passage.passage_id,
                start,
                start + len(formula),
            )
            for symbol, (witness_ref, _evidence_offset) in evidence.items()
        ),
    )
    result = assess_exact_affine(
        PreparedMathInput(context, r"X = \sigma Z + \mu", source_text=formula, source_start=start),
        output="X",
        generator="Z",
        coefficient=r"\sigma",
        offset=r"\mu",
    )
    return dict(
        run_id=run_id,
        cut_id=selected.completed_cut_id,
        task_id=task_id,
        formula=formula,
        ordered_witness=edge["contribution_id"],
        source_roles=evidence,
        assessment=result,
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("request", type=Path)
    cli.add_argument("run_id", type=int)
    cli.add_argument("task_id", type=int)
    args = cli.parse_args()
    print(
        json.dumps(
            assess(json.loads(args.request.read_bytes()), args.run_id, args.task_id),
            indent=2,
            sort_keys=True,
        )
    )
