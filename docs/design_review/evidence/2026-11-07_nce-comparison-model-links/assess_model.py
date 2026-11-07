"""Compare exact held source judgments across matched retained GLiNER arms."""

import argparse
import json
from pathlib import Path

from corpus_structure.semantic.structural_products import StructuralProductReport


def structural(path):
    return StructuralProductReport.model_validate_json((path / "product.json").read_bytes())


def span_key(span):
    return span.passage_id, span.start, span.end, span.text


def evaluate_definition(path):
    product = structural(path).definition_components
    if product is None:
        raise ValueError("selected arm has no definition component report")
    cases = json.loads((path / "source-judgments.json").read_bytes())
    roles = {(role.role, *span_key(role.span)) for role in product.role_candidates or ()}
    attachments = {
        (span_key(item.term), span_key(item.content), item.interpretation)
        for item in product.components
        if item.basis == "model_reading"
    }
    windows = sorted(
        {
            (item.span.passage_id, item.window_start, item.window_end)
            for item in product.role_candidates or ()
        }
    )
    selected = {}
    for case in cases:
        expected = case["corrected_alternatives"][0]
        passage_id = f"benefit:{case['source_pin']['source']['source_view_id']}"
        term, content = (
            (passage_id, expected[role]["start"], expected[role]["end"], expected[role]["text"])
            for role in ("term", "content")
        )
        selected[passage_id] = {
            "expected_term_returned": ("term", *term) in roles,
            "expected_content_returned": ("content", *content) in roles,
            "expected_attachment_returned": (term, content, expected["interpretation"])
            in attachments,
            "model_attachments": [
                {"term": a, "content": b, "interpretation": standing}
                for a, b, standing in sorted(attachments)
                if a[0] == passage_id
            ],
        }
    return {
        "roles_with_exact_locations": len(roles),
        "windows_with_roles": windows,
        "stages": [stage.model_dump(mode="json") for stage in product.stages],
        "cases": selected,
    }


def evaluate_classification(path, selection):
    product = structural(path).clause_classification
    if product is None:
        raise ValueError("selected arm has no clause classification report")
    expected = {
        (passage_id, *extent): function
        for _, passage_id, extent, function in selection["judgments"]
    }
    readings = []
    for item in product.readings:
        key = (item.focus.passage_id, item.focus.start, item.focus.end)
        judgment = expected.pop(key)
        function = "reference" if judgment == "reported_reference" else judgment
        presentation = {"attribution", "historical"} if judgment == "reported_reference" else set()
        readings.append(
            {
                "expected_function": function,
                "expected_presentation": sorted(presentation),
                "function_matches": any(
                    label.accepted and label.label == function for label in item.function
                ),
                "expected_presentation_retained": sorted(
                    presentation & {label.label for label in item.presentation if label.accepted}
                ),
                **item.model_dump(mode="json", exclude={"selection"}),
            }
        )
    if expected:
        raise ValueError("clause arm omitted a selected focus")
    return {"policy": product.context_policy, "readings": readings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("classification_selection", type=Path)
    args = parser.parse_args()
    result = {"definitions": {}, "classification": {}}
    for arm in ("bare", "described", "flat", "nested", "allow"):
        path = args.root / ("definition-" + arm)
        result["definitions"][arm] = evaluate_definition(path)
    selection = json.loads(args.classification_selection.read_bytes())
    for arm in ("exact_focus", "adjacent_sentences"):
        result["classification"][arm] = evaluate_classification(
            args.root / ("clause-" + arm), selection
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
