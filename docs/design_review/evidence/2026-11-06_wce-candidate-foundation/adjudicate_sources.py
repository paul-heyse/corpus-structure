"""C adjudication of selected source-only questions before new producer outputs.

The selected literal cases and reasons below are authored judgments, not a
majority-vote transformation. Unselected A/B proposals remain unadjudicated.
"""

import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
REASONS = {
    "marginal-term": "The source explicitly names marginal distribution in the univariate-without-regard-to-other-value definition.",
    "marginal-content": "The complete quoted sentence supplies the marginal-distribution distinction; no dependence/independence conclusion is added.",
    "continuous-marginal-scope": "The cue explicitly restricts the following integral construction to continuous bivariate variables.",
    "discrete-marginal-scope": "The cue explicitly restricts the following summation construction to discrete variates.",
    "independence-cue": "The source says are said to be independent and immediately supplies an if-clause criterion.",
    "independence-content": "The quoted if-clause describes independence; mathematical equivalence beyond this source statement is not judged.",
    "dependence-cue": "The local subject refers to two univariates which are not independent; the cue names that case dependent.",
    "conditional-name": "Such probabilities is an anaphoric reference to preceding given-information probabilities. The naming cue is located; full endpoint resolution remains separate.",
    "conditional-denominator": "The nonzero condition is explicitly stated for the immediately preceding conditional probability ratio; it is not a condition on every equation in the source.",
    "continuous-conditional-scope": "The quoted cue introduces the continuous conditional-density construction.",
    "mean-term": "The quoted heading/term is located. The role is mean, not a population-mean identity claim.",
    "mean-content": "The exact quoted division describes the mean in the local definition; it does not establish a particular usage's applicability.",
    "median-content": "The source gives half-smaller/half-larger wording as its median definition. No generalized quantile convention is inferred.",
    "mode-content": "The source defines the mode by greatest frequency and separately warns it need not be unique.",
    "normal-use-condition": "The histogram/probability-plot normal approximation is a condition on the recommendation, not a normal-density definition.",
    "normal-use-conclusion": "Reasonable to use is conditional guidance, not an obligation or universal correctness assertion.",
    "cauchy-countercontext": "The passage explains failure of the mean as a typical-value measure for Cauchy; it is a countercontext, not an explicit exception clause within the normal condition.",
    "sample-mean-symbol": "The source locally declares Y-bar to be the sample mean; retain the bar and do not equate it with population mean.",
    "sample-sd-symbol": "The source locally declares s to be sample standard deviation.",
    "sample-size-symbol": "The source locally declares N to be sample size.",
    "confidence-interpretation-negative": "The source explicitly rejects the quoted probability reading. It is a negative interpretation, not positive support for that reading.",
    "rejection-threshold": "The source states strict greater-than 1.9723 for this particular absolute-T example; do not generalize the threshold or replace > with >=.",
}


def spans(value):
    if isinstance(value, dict):
        if {"passage_id", "start", "end", "text"} <= value.keys():
            yield value
        for item in value.values():
            yield from spans(item)
    elif isinstance(value, list):
        for item in value:
            yield from spans(item)


def main():
    packet = json.loads((RAW / "source-opportunities-001.json").read_bytes())
    passages = {p["passage_id"]: p for p in packet["passages"]}
    authors = {kind: json.loads((RAW / f"source-author-{kind}-001.json").read_bytes()) for kind in ("A", "B")}
    audits = []
    for kind, author in authors.items():
        for proposal in author["opportunities"]:
            identifier = proposal.get("id", proposal.get("opportunity_id"))
            rows = list(spans(proposal))
            failures = [s for s in rows if s["passage_id"] not in passages or passages[s["passage_id"]]["text"][s["start"]:s["end"]] != s["text"]]
            notes = []
            content, cue = proposal.get("content_location"), proposal.get("cue_location")
            if content and cue and not (content["start"] <= cue["start"] < cue["end"] <= content["end"]):
                notes.append("cue lies outside authored content; exact string match alone does not establish this local attachment")
            if kind == "B" and identifier == "B-038":
                notes.append("content_spans split a string into isolated characters at unrelated first occurrences; reject that content assembly; separately located threshold spans remain inspectable")
            audits.append({"author": kind, "proposal_id": identifier, "exact_span_count": len(rows), "invalid_spans": failures, "context_issues": notes, "disposition": "selected fragment judgments below only; other semantic proposals remain unadjudicated"})
    cases = []
    for opportunity in packet["opportunities"]:
        if opportunity["opportunity_id"] not in REASONS:
            raise ValueError("missing independently authored C rationale")
        relevant = []
        for kind, author in authors.items():
            for proposal in author["opportunities"]:
                if any(s["passage_id"] == opportunity["passage_id"] and s["start"] < opportunity["end"] and opportunity["start"] < s["end"] for s in spans(proposal)):
                    relevant.append({"author": kind, "proposal_id": proposal.get("id", proposal.get("opportunity_id"))})
        cases.append({**opportunity, "case_id": "C-" + opportunity["opportunity_id"], "location_judgment": "supported", "role_judgment": "supported", "attachment_judgment": "unassessed", "reason": REASONS[opportunity["opportunity_id"]], "related_author_proposals": relevant})
    result = {
        "protocol": "wce-source-adjudication-1", "author": "C", "date": "2026-11-06",
        "parents": {kind: {"file": f"source-author-{kind}-001.json", "sha256": sha256((RAW / f"source-author-{kind}-001.json").read_bytes()).hexdigest()} for kind in ("A", "B")},
        "source_author_input_sha256": sha256((RAW / "source-author-input-001.json").read_bytes()).hexdigest(),
        "partition": "development", "producer_outputs_inspected": False,
        "basis": "source text, independently authored A/B and explicit C source reasons; no majority promotion",
        "cases": cases, "author_proposal_audit": audits,
        "limits": ["Only 22 selected location/role facets adjudicated; all endpoint attachment and later applicability remain unassessed.", "A and B propose different populations; neither population is silently called complete.", "Some exact located cues attach to unrelated first occurrences; those source-role bindings are not accepted.", "No native frame/pass or public eligibility established by this raw evidence file.", "Source groups are exposed development material; no held-out or statistical calibration claim."],
    }
    with (RAW / "source-author-C-001.json").open("xb") as stream:
        stream.write(canonical_bytes(result) + b"\n")
    print(json.dumps({"outcome": "passed", "selected_cases": len(cases), "author_proposals": len(audits), "invalid_span_proposals": sum(bool(a["invalid_spans"]) for a in audits), "context_issue_proposals": sum(bool(a["context_issues"]) for a in audits)}))


if __name__ == "__main__":
    main()
