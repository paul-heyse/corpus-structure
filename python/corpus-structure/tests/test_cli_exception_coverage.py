"""Original exception links omitted by the native transformer stay explicitly unknown."""

import pytest

from corpus_structure.cli.exception_observations import transform_exception


@pytest.mark.parametrize("nested", (False, True))
@pytest.mark.parametrize("link", ("__cause__", "__context__"))
def test_native_unrepresented_original_link_is_located_without_invented_frames(nested, link):
    child = RuntimeError("child")
    setattr(child, link, ValueError("linked but never raised"))
    if link == "__context__":
        child.__suppress_context__ = False
    error = ExceptionGroup("group", [child]) if nested else child
    trace = transform_exception((type(error), error, None))
    path = ("$.original.exceptions[0]." if nested else "$.original.") + link
    assert any(item.path == path and "no traceback" in item.reason for item in trace.omissions)
    assert trace.stacks[0].frames == ()
    if nested:
        branch = trace.stacks[0].exceptions[0]
        assert branch.stacks[0].exc_type == "RuntimeError" and branch.stacks[0].frames == ()
    else:
        assert len(trace.stacks) == 1 and trace.stacks[0].exc_type == "RuntimeError"


def test_oversized_original_link_graph_keeps_existing_root_and_bounded_omissions():
    error = RuntimeError("root")
    current = error
    for _ in range(40):
        linked = RuntimeError("linked")
        current.__cause__ = linked
        current = linked
    trace = transform_exception((type(error), error, None))
    assert len(trace.omissions) <= 33
    assert any("traversal limit" in item.reason for item in trace.omissions)
    assert trace.stacks[0].frames == ()
