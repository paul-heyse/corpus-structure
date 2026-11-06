"""Freeze authentic statistics source opportunities before WCE03 production.

Run from the repository root. Reads native custody through the existing owned
structural-source operation; writes new evidence files exclusively, never updates
source data or historical reference packets.
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCOPE = "wce-statistics-source-opportunities-001"
SELECTION = ((45, 46), (15, 26), (15, 27), (15, 28), (13, 31), (13, 32))

# Authored from original source text, without any new WCE03 producer outputs.
# Each literal is an exact source opportunity; its semantic judgment is separately
# authored. These are neither a matcher configuration nor a learned label set.
OPPORTUNITIES = (
    (26, "marginal-term", "term_location", "marginal distribution", 0),
    (26, "marginal-content", "defining_content", "Probabilities associated with a univariate element of a bivariate without regard to the value of the other univariate element within the same bivariate arise from the marginal distribution of that univariate.", 0),
    (26, "continuous-marginal-scope", "condition", "In the case of continuous bivariate (X, Y)", 0),
    (26, "discrete-marginal-scope", "condition", "In the case of discrete variates X and Y", 0),
    (27, "independence-cue", "defining_cue", "are said to be independent", 0),
    (27, "independence-content", "defining_content", "if the marginal probabilities associated with the outcomes of one variate are not influenced by the observed value of the other variate, and vice versa.", 0),
    (28, "dependence-cue", "defining_cue", "they are said to be dependent", 0),
    (28, "conditional-name", "naming_cue", "Such probabilities are called conditional probabilities.", 0),
    (28, "conditional-denominator", "condition", "provided the denominator Pr[Y ≤ y] is nonzero.", 0),
    (28, "continuous-conditional-scope", "condition", "For continuous random variates", 0),
    (31, "mean-term", "term_location", "mean - the mean", 0),
    (31, "mean-content", "defining_content", "the sum of the data points divided by the number of data points", 0),
    (31, "median-content", "defining_content", "the value of the point which has half the data smaller than that point and half the data larger than that point", 0),
    (31, "mode-content", "defining_content", "the value of the random sample that occurs with the greatest frequency", 0),
    (31, "normal-use-condition", "condition", "if a histogram or normal probability plot indicates that your data are approximated well by a normal distribution", 0),
    (31, "normal-use-conclusion", "conditioned_action", "then it is reasonable to use the mean as the location estimator.", 0),
    (31, "cauchy-countercontext", "explanation", "for the Cauchy distribution the mean is useless as a measure of the typical value", 0),
    (32, "sample-mean-symbol", "symbol_declaration", "Ȳ is the sample mean", 0),
    (32, "sample-sd-symbol", "symbol_declaration", "s is the sample standard deviation", 0),
    (32, "sample-size-symbol", "symbol_declaration", "N is the sample size", 0),
    (32, "confidence-interpretation-negative", "negative_interpretation", "a 95 % confidence interval doesnotmean that there is a 95 % probability", 0),
    (32, "rejection-threshold", "threshold", "Critical region: Reject H0 if |T| > 1.9723", 0),
)


def write_new(name, value):
    with (HERE / "raw" / name).open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def main():
    with open_runtime_engine(Settings(), "wce02-source-freeze", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            rows = tuple(
                dict(row)
                for row in conn.execute(
                    text("SELECT id,projection->>'text' AS body FROM kb.source_view WHERE id=ANY(:ids) ORDER BY id"),
                    {"ids": [view for _, view in SELECTION]},
                ).mappings()
            )
        bodies = {row["id"]: row["body"] for row in rows}
        selections = [
            StructuralPassageSelection(
                run_id=run,
                source_view_id=view,
                passage_id=f"source-view-{view}",
                start=0,
                end=len(bodies[view]),
                scope=SCOPE,
            )
            for run, view in SELECTION
        ]
        sources = prepare_structural_sources(engine, selections)
    opportunities = []
    for view, identifier, facet, literal, occurrence in OPPORTUNITIES:
        body = bodies[view]
        start = -1
        for _ in range(occurrence + 1):
            start = body.index(literal, start + 1)
        opportunities.append(
            {
                "opportunity_id": identifier,
                "passage_id": f"source-view-{view}",
                "facet": facet,
                "start": start,
                "end": start + len(literal),
                "text": literal,
                "source_state": "observed",
                "inspected_scope": "exact quoted span within retained complete selected source view",
            }
        )
    regressions = {}
    baseline = ROOT / "docs/design_review/evidence/2026-11-05_pce-structural-products/raw"
    for name in (
        "production-input-002.json",
        "independent-automatic-C-001.json",
    ):
        path = baseline / name
        regressions[str(path.relative_to(ROOT))] = sha256(path.read_bytes()).hexdigest()
    packet = {
        "protocol": "wce-source-opportunities-1",
        "created": "2026-11-06",
        "scope": SCOPE,
        "direction": "source_first",
        "partition": "development",
        "exposure": "Existing statistics source families and F37 feedback are exposed; no held-out claim.",
        "source_groups": [
            {"origin_group": "grinstead-snell-retained-family", "passages": ["source-view-46"]},
            {"origin_group": "forbes-retained-family", "passages": [f"source-view-{v}" for v in (26, 27, 28)]},
            {"origin_group": "nist-ehandbook-retained-family", "passages": [f"source-view-{v}" for v in (31, 32)]},
        ],
        "sources": [source.model_dump(mode="json", exclude_none=True) for source in sources.sources],
        "passages": [passage.model_dump(mode="json", exclude_none=True) for passage in sources.passages],
        "questions": [
            "Locate source terms, defining/naming cues and defining content independently of candidate production.",
            "Locate conditions, symbol declarations and strict thresholds; judge role separately from location.",
            "Retain missing source opportunities and unavailable annotation mechanisms without inventing semantic absence.",
        ],
        "opportunities": opportunities,
        "coverage_gaps": [
            {"facet": "normal_density_definition", "state": "not_in_selected_retained_sources"},
            {"facet": "standard_normal_definition", "state": "not_in_selected_retained_sources"},
            {"facet": "alternate_normal_parameterizations", "state": "not_in_selected_retained_sources"},
            {"facet": "nested_merged_header_and_note_scope", "state": "not_independently_referenced_in_this_packet"},
        ],
        "exposed_regression_inputs": regressions,
        "producer_executed": False,
        "frozen_before_new_production": True,
        "freeze_script_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "quality_claim": "source_opportunity_authoring_only; independent B/C and WCE03 outputs pending",
    }
    write_new("source-opportunities-001.json", packet)
    write_new(
        "source-freeze-001.json",
        {
            "protocol": "wce-source-freeze-receipt-1",
            "packet_sha256": sha256(canonical_bytes(packet) + b"\n").hexdigest(),
            "sources": len(packet["sources"]),
            "passages": len(packet["passages"]),
            "opportunities": len(opportunities),
            "database_operations": "read_only",
            "producer_executed": False,
        },
    )
    print(json.dumps({"outcome": "passed", "passages": len(packet["passages"]), "opportunities": len(opportunities)}))


if __name__ == "__main__":
    main()
