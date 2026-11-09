"""Capture only frozen source windows and exact ordered native anchors."""

import json
import re
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.operation_assessment import (
    OperationEvaluationFrameV2,
    OperationSourceOpportunity,
    encode_frame,
)
from corpus_structure.semantic.contributions import anchor_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import selected_source_views
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
SOURCE_RUN = 478
SOURCE_CUT = 595
PROJECT = "nce-grinstead-snell-full-book"
SPECS = {
    "definition_target": (
        415,
        (811, 907),
        {
            "term": "random variable",
            "cue": "is simply",
            "content": "an expression whose value is the outcome of a particular experiment",
        },
    ),
    "definition_use": (417, (637, 699), {"focal": "random variable", "local_variable": "X"}),
    "conditional_frequency": (
        415,
        (2427, 2630),
        {
            "outer_premise": (
                "if we have a probability p that an experiment will result in outcome A"
            ),
            "inner_premise": "if we repeat this experiment a large number of times",
            "lexical_host": "expect",
            "modality": "should expect",
            "approximation": "about p",
        },
    ),
    "gambler": (
        437,
        (27850, 28039),
        {
            "antecedent": "A gambler",
            "focal": "She",
            "possessive": "her",
            "distinct_owned_entity": "her capital",
            "first_value": "M",
            "second_value": "0",
        },
    ),
    "roulette": (419, (47316, 47345), {"loss_role": "losing", "amount": "1", "unit": "dollar"}),
    "fair_coin": (421, (18091, 18193), {"literal": "1/8", "qualifier": "If the coin is fair"}),
    "negative_binomial": (423, (7420, 7508), {"focal": "negative binomial distribution"}),
    "exponential_density": (423, (8767, 9217), {"focal": "exponential density"}),
}
FRAME_SPECS = {
    "definition_use": (
        "contextual_link_assessment_v1",
        "2",
        {"definition_use": "source_backed_definition_link"},
    ),
    "conditional_frequency": (
        "qualification_scope_v1",
        "2",
        {"conditional_frequency": "nested_condition_host"},
    ),
    "gambler": ("local_referent_choice_v1", "2", {"gambler": "exact_local_referent"}),
    "roulette": (
        "literal_completion_v1",
        "2",
        {
            "roulette_amount": "written_loss_amount",
            "roulette_unit": "written_loss_unit",
            "roulette_role": "written_loss_role",
        },
    ),
    "fair_coin": ("literal_completion_v1", "2", {"fair_coin": "complete_probability_magnitude"}),
}
GUIDELINE = "pm2-named-workflow-source-1"
OLD_VIEWS = {
    "definition_target": 383,
    "gambler": 405,
    "roulette": 387,
    "fair_coin": 389,
    "negative_binomial": 391,
    "exponential_density": 391,
}


def exact_anchor(text, pieces, extent, pin, literal):
    left, right = extent
    pattern = rf"(?<!\w){re.escape(literal)}(?!\w)"
    matches = list(re.finditer(pattern, text[left:right]))
    if len(matches) != 1:
        raise ValueError(
            f"reference is missing or ambiguous in the frozen window: {literal!r} {extent}"
        )
    relative = matches[0].start()
    start = left + relative
    end = start + len(literal)
    anchors = []
    cursor = start
    for piece in pieces:
        left, right = max(start, piece["start"]), min(end, piece["end"])
        if left >= right:
            continue
        if left != cursor or piece["kind"] != "native_text":
            raise ValueError(f"unmapped or non-native source fragment for {literal!r} at {cursor}")
        value = {
            "pin": pin,
            "pointer": piece["item_ref"],
            "space": "native",
            "precision": "exact",
            "start": left - piece["start"],
            "end": right - piece["start"],
            "source_piece": text[left:right],
        }
        anchors.append({**value, "anchor_id": anchor_identity(value)})
        cursor = right
    if cursor != end:
        raise ValueError(f"incomplete native source fragments for {literal!r}")
    return {"native_anchors": anchors, "projection_extent": [start, end]}


def main():
    checkpoint = PARENT / "2026-11-09_pm2-structuring-execution" / "raw" / "source-preparation.json"
    receipt = json.loads(checkpoint.read_bytes())
    if (receipt["run_id"], receipt["cut_id"]) != (SOURCE_RUN, SOURCE_CUT):
        raise ValueError("unexpected source preparation receipt")
    stored = table("kb.source_view")
    runs = table("ops.run")
    ids = {spec[0] for spec in SPECS.values()} | set(OLD_VIEWS.values())
    with (
        open_runtime_engine(Settings(), "pm2-workflow-source-only", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        project, release = conn.execute(
            select(runs.c.project_id, runs.c.release_id).where(runs.c.id == SOURCE_RUN)
        ).one()
        if (project, release) != (PROJECT, receipt["release_id"]):
            raise ValueError("source run disagrees with the project or release pin")
        selected = {ref.id: ref for ref in selected_source_views(conn, SOURCE_RUN)}
        historical_m1 = {
            (ref.projection_digest, ref.recipe_digest, ref.native_product): ref.id
            for ref in selected_source_views(conn, 407)
        }
        rows = {
            row.id: row
            for row in conn.execute(
                select(
                    stored.c.id,
                    stored.c.key,
                    stored.c.projection_digest,
                    stored.c.recipe_digest,
                    stored.c.native_task_id,
                    stored.c.native_product_key,
                    stored.c.native_content_digest,
                    stored.c.projection["text"].as_string().label("body"),
                    stored.c.projection["pieces"].label("pieces"),
                ).where(stored.c.id.in_(sorted(ids)))
            )
        }
    cases = {}
    for name, (view, extent, literals) in SPECS.items():
        ref = selected[view]
        row = rows[view]
        if (row.key, row.projection_digest, row.recipe_digest) != (
            ref.key,
            ref.projection_digest,
            ref.recipe_digest,
        ):
            raise ValueError(f"view {view} disagrees with the selected source")
        pin = {
            "source": ref.key,
            "source_view_id": view,
            "native_product_task_id": ref.native_product.task_id,
            "product_key": ref.native_product.product_key,
            "product_digest": ref.native_product.content_digest,
            "projection_digest": ref.projection_digest,
            "recipe_digest": ref.recipe_digest,
        }
        old = OLD_VIEWS.get(name)
        if old is not None and (
            rows[old].projection_digest,
            rows[old].recipe_digest,
            rows[old].body,
            rows[old].native_task_id,
            rows[old].native_product_key,
            rows[old].native_content_digest,
        ) != (
            row.projection_digest,
            row.recipe_digest,
            row.body,
            row.native_task_id,
            row.native_product_key,
            row.native_content_digest,
        ):
            raise ValueError(f"historical view {old} does not match new projection {view}")
        cases[name] = {
            "pin": pin,
            "extent": list(extent),
            "source_text": row.body[extent[0] : extent[1]],
            "historical_corresponding_view": old,
            "m1_corresponding_view": historical_m1.get(
                (ref.projection_digest, ref.recipe_digest, ref.native_product)
            ),
            "anchors": {
                role: exact_anchor(row.body, row.pieces, extent, pin, literal)
                for role, literal in literals.items()
            },
        }
    templates = {}
    for key, (question, version, opportunities) in FRAME_SPECS.items():
        row = cases[key]
        pin, (left, right) = row["pin"], row["extent"]
        related = (cases["definition_target"]["pin"],) if key == "definition_use" else ()
        frame = OperationEvaluationFrameV2(
            unit=pin["source"],
            release_id=receipt["release_id"],
            guideline_version=GUIDELINE,
            rubric_version=GUIDELINE,
            context_policy="pm2-named-workflow-exact-scope-1",
            operation_question=question,
            operation_version=version,
            domain="statistics",
            direction="source_first",
            pin=pin,
            anchor_ids=(),
            related_pins=related,
            anchor_scopes=(),
            contribution_ids=(),
            source_group="grinstead-snell",
            partition="development",
            inspected_scope=f"view {pin['source_view_id']} chars {left}:{right}",
            opportunities=tuple(
                OperationSourceOpportunity(
                    case, pin["source_view_id"], left, right, facet, "stated"
                )
                for case, facet in opportunities.items()
            ),
            exposure_history=("Known Grinstead–Snell development source; not held out.",),  # noqa: RUF001
        )
        templates[key] = encode_frame(frame)
    print(
        canonical_bytes(
            {
                "project": PROJECT,
                "run_id": SOURCE_RUN,
                "cut_id": SOURCE_CUT,
                "release_id": receipt["release_id"],
                "partition": "development",
                "cases": cases,
                "d1_frame_templates": templates,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
