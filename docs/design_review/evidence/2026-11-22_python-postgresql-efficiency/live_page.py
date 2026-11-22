"""Compare the raw and acquired projection of the same admitted synthetic page."""

import json
import sys
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "python/corpus-structure/tests"))

from semantic.demand_result_support import demand_result_page  # noqa: E402

from corpus_structure.semantic.data_operation_json import json_bytes  # noqa: E402
from corpus_structure.semantic.data_operation_wire import validate_native_wire  # noqa: E402
from corpus_structure.semantic.demand_queries import DemandQueryRequest  # noqa: E402
from corpus_structure.semantic.demand_query_projection import (  # noqa: E402
    prepare_demand_projection_inputs,
    selected_query_rows,
)
from corpus_structure.semantic.demand_results import DemandResult  # noqa: E402
from corpus_structure.semantic.demand_wire import (  # noqa: E402
    captured_demand_wire_validator,
    decode_wire_demand_result,
)


def tagged_body(depth, width):
    result = ["string", "one"]
    for _ in range(depth):
        result = ["sequence", [result]]
    return result if width == 1 else ["sequence", [result] * width]


def timed(function, *args, **kwargs):
    start = perf_counter()
    value = function(*args, **kwargs)
    return value, round((perf_counter() - start) * 1000, 3)


def cut_bytes(page):
    return page.cut.content


def refused(function, *args):
    try:
        function(*args)
    except ValueError:
        return True
    return False


def compare_negative_inputs(raw):
    pages = {
        name: deepcopy(raw)
        for name in (
            "absent_release",
            "boolean_generation",
            "unexpected_product_field",
            "unknown_value_tag",
            "noncanonical_integer",
            "missing_tag_payload",
        )
    }
    del pages["absent_release"]["release_id"]
    pages["boolean_generation"]["obligations"][0]["generation"] = True
    pages["unexpected_product_field"]["uses"][0]["products"][0]["unexpected"] = "x"
    for name, body in (
        ("unknown_value_tag", ["not-a-tag", "one"]),
        ("noncanonical_integer", ["integer", "01"]),
        ("missing_tag_payload", ["string"]),
    ):
        pages[name]["uses"][0]["products"][0]["body"] = body
    return {
        name: dict(
            admission_refused=refused(validate_native_wire, "read_demand_result", "output", page),
            generated_refused=refused(decode_wire_demand_result, json_bytes(page)),
        )
        for name, page in pages.items()
    }


def main():
    raw = demand_result_page()
    selection = json_bytes(
        DemandQueryRequest(demand_id="demand:A", project_id="project:A").selection()
    )
    # The captured validator and both projection branches warm before measurement.
    assert captured_demand_wire_validator() is not None
    options = {"decimal_fixed_point_digits": 100}
    prepare_demand_projection_inputs(json_bytes(raw), selection, **options)
    prepare_demand_projection_inputs(DemandResult._from_native(raw, b"{}"), selection, **options)
    samples = []
    for depth, width in ((10, 1), (14, 1), (18, 1), (20, 1), (8, 8), (8, 32), (8, 128)):
        probe = deepcopy(raw)
        probe["uses"][0]["products"][0]["body"] = tagged_body(depth, width)
        admitted, first = timed(validate_native_wire, "read_demand_result", "output", probe)
        content, serialize = timed(json_bytes, admitted)
        retained = DemandResult(content)
        _, retained_cut = timed(cut_bytes, retained)
        existing, second = timed(prepare_demand_projection_inputs, content, selection, **options)
        acquired, snapshot = timed(DemandResult._from_native, admitted, b"{}")
        _, acquired_cut = timed(cut_bytes, acquired)
        candidate, reuse = timed(prepare_demand_projection_inputs, acquired, selection, **options)
        assert acquired.content == content
        assert acquired.cut.content == retained.cut.content
        assert candidate.page is acquired.projection_snapshot
        assert list(selected_query_rows(candidate)) == list(selected_query_rows(existing))
        samples.append(
            dict(
                depth=depth,
                width=width,
                bytes=len(content),
                first_admission_ms=first,
                old_serialization_ms=serialize,
                old_cut_ms=retained_cut,
                old_projection_ms=second,
                acquired_serialization_and_freeze_ms=snapshot,
                acquired_cut_ms=acquired_cut,
                acquired_projection_ms=reuse,
            )
        )
    print(
        json.dumps(
            {
                "python": sys.version.split()[0],
                "pydantic": version("pydantic"),
                "samples": samples,
                "negative_inputs": compare_negative_inputs(raw),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
