"""Freeze native-authenticated normal-source questions before named production."""

import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
source_file = HERE / "intake003/source-packet-002.json"
packet = json.loads(source_file.read_bytes())
assert len(packet["passages"]) == 1
passage = packet["passages"][0]
body = passage["text"]
definitions = (
    ("normal-density-term", "term_location", "The normal density function with parameters µ and σ"),
    ("normal-density-cue", "defining_cue", "is defined as follows:"),
    ("normal-density-formula", "formula_content", r"f _ { X } ( x ) = \frac { 1 } { \sqrt { 2 \pi } \sigma } e ^ { - ( x - \mu ) ^ { 2 } / 2 \sigma ^ { 2 } } \ ."),
    ("normal-location-parameter", "parameter_declaration", 'The parameter µ represents the "center" of the density'),
    ("normal-scale-parameter", "parameter_declaration", 'The parameter σ is a measure of the "spread" of the density, and thus it is assumed to be positive.'),
    ("normal-standard-deviation", "parameter_declaration", "σ is the standard deviation of the density"),
    ("standard-normal-parameters", "parameter_declaration", "Let Z be a normal random variable with parameters µ = 0 and σ = 1."),
    ("standard-normal-definition", "defining_content", "A normal random variable with these parameters is said to be a standard normal random variable."),
    ("normal-affine-transform", "formula_content", r"X = \sigma Z + \mu \ ,"),
    ("standardization-name", "naming_cue", "The process of changing a normal random variable to a standard normal random variable is known as standardization."),
    ("standardization-transform", "formula_content", r"Z = \frac { X - \mu } { \sigma } \ ,"),
)
opportunities = []
for identifier, facet, literal in definitions:
    start = body.index(literal)
    opportunities.append({"opportunity_id": identifier, "facet": facet, "passage_id": passage["passage_id"],
        "start": start, "end": start + len(literal), "text": literal, "source_state": "observed",
        "semantic_judgment": "unassessed; independent source authoring pending"})
shared = {"scope": "wce-statistics-normal-002", "sources": packet["sources"], "passages": packet["passages"],
    "source_packet_sha256": sha256(source_file.read_bytes()).hexdigest(),
    "origin_group": "grinstead-snell", "original_native_partition": "feature_fit; do not reassign",
    "exposure_use": "same already exposed source-family refinement; evaluator authorization remains separately required",
    "producer_outputs_included": False,
    "questions": ["Locate normal-density/standard-normal definitions and parameter declarations; distinguish source quotation from mathematical verification.", "Locate affine transform and standardization; preserve original source coordinates and all recognition limitations."]}
with (RAW / "source-opportunities-002.json").open("xb") as stream:
    stream.write(canonical_bytes({"protocol": "wce-source-opportunities-1", **shared, "opportunities": opportunities,
        "coverage_gaps": ["No explicit variance-versus-standard-deviation alternate parameterization comparison in this source packet.", "CDF extraction includes corrupt trailing text/coefficient; do not silently repair or infer scientific validity.", "No independent merged-header/unit/note reference in this packet."],
        "frozen_before_new_production": True}) + b"\n")
with (RAW / "source-author-input-002.json").open("xb") as stream:
    stream.write(canonical_bytes({"protocol": "wce-source-author-input-1", **shared,
        "author_instruction": "Read these authentic source passages only. Independently locate source-supported definitions, named terms, parameters and transform statements. Separate location, role and attachment. Do not inspect other author passes, proposed opportunity spans or producer outputs. Mathematical/scientific correctness is a different question."}) + b"\n")
print(json.dumps({"outcome": "passed", "opportunities": len(opportunities), "producer_executed": False}))
