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


def test_unrepresented_link_subtree_is_disclosed_without_reconstructing_it():
    error = RuntimeError("root")
    current = error
    for _ in range(40):
        linked = RuntimeError("linked")
        current.__cause__ = linked
        current = linked
    trace = transform_exception((type(error), error, None))
    (omission,) = trace.omissions
    assert omission.path == "$.original.__cause__" and "subtree" in omission.reason
    assert "traversal limit" not in omission.reason
    assert trace.stacks[0].frames == ()


def raised(error):
    try:
        raise error
    except Exception as caught:
        return caught


@pytest.mark.parametrize("branch", ("cause", "context", "fallback_context"))
def test_native_reachable_oversized_group_is_bounded_before_native_walk(monkeypatch, branch):
    from corpus_structure.cli import exception_observations

    group = raised(ExceptionGroup("large", [ValueError(str(index)) for index in range(17)]))
    error = RuntimeError("wrapper")
    if branch == "cause":
        error.__cause__ = group
    else:
        error.__context__ = group
        if branch == "fallback_context":
            error.__cause__ = ValueError("never raised")
        error.__suppress_context__ = False
    native = exception_observations._NATIVE
    calls = []

    def guarded(exc_info):
        calls.append(exc_info[1])
        assert exc_info[1] is not error
        return native(exc_info)

    monkeypatch.setattr(exception_observations, "_NATIVE", guarded)
    trace = transform_exception((type(error), error, None))
    assert len(calls) == 1 and calls[0] is not error
    assert any("traversal limit" in item.reason for item in trace.omissions)
    assert trace.stacks[0].exc_type == "RuntimeError"
    if branch == "fallback_context":
        assert any(item.path == "$.original.__cause__" for item in trace.omissions)


def test_bounded_fallback_context_keeps_native_group_and_original_cause_omission():
    context = raised(ExceptionGroup("context", [LookupError("member")]))
    error = RuntimeError("wrapper")
    error.__cause__ = ValueError("never raised")
    error.__context__ = context
    error.__suppress_context__ = False
    trace = transform_exception((type(error), error, None))
    root, linked = trace.stacks
    assert root.exc_type == "RuntimeError"
    assert linked.exc_type == "ExceptionGroup" and linked.is_group and not linked.is_cause
    assert linked.exceptions[0].stacks[0].exc_type == "LookupError"
    (omission,) = trace.omissions
    assert omission.path == "$.original.__cause__" and "no traceback" in omission.reason


def test_suppressed_context_does_not_inflate_native_traversal():
    context = raised(ExceptionGroup("hidden", [ValueError(str(index)) for index in range(17)]))
    error = RuntimeError("wrapper")
    error.__cause__ = ValueError("never raised")
    error.__context__ = context
    assert error.__suppress_context__
    trace = transform_exception((type(error), error, None))
    assert len(trace.stacks) == 1 and trace.stacks[0].exc_type == "RuntimeError"
    (omission,) = trace.omissions
    assert omission.path == "$.original.__cause__" and "no traceback" in omission.reason


def test_native_child_before_shared_context_preserves_original_omission_location():
    child = raised(RuntimeError("child"))
    child.__cause__ = ValueError("never raised")
    error = ExceptionGroup("group", [child])
    error.__context__ = child
    trace = transform_exception((type(error), error, None))
    assert len(trace.stacks) == 1
    assert trace.stacks[0].exceptions[0].stacks[0].exc_type == "RuntimeError"
    (omission,) = trace.omissions
    assert omission.path == "$.original.exceptions[0].__cause__"
