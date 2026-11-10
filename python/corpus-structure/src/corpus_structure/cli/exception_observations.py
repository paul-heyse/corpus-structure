"""A bounded typed selection of structlog's native exception trace shape."""

from __future__ import annotations

from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict

from corpus_structure._diagnostic_capture import safe_text


class OmittedExceptionDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["omitted"] = "omitted"
    path: str
    reason: str


class ExceptionFrame(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    filename: str
    lineno: int
    name: str


class ExceptionStack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    exc_type: str
    exc_value: str
    exc_notes: tuple[str, ...] = ()
    is_cause: bool = False
    is_group: bool = False
    frames: tuple[ExceptionFrame | OmittedExceptionDetail, ...] = ()
    exceptions: tuple[ExceptionTrace | OmittedExceptionDetail, ...] = ()
    syntax_error: dict[str, Any] | None = None
    omissions: tuple[OmittedExceptionDetail, ...] = ()


class ExceptionTrace(BaseModel):
    """Root stack first, then native cause/context stacks; locals are never retained."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    owner: Literal["structlog_exception"] = "structlog_exception"
    chain_order: Literal["raised_then_causes_or_contexts"] = "raised_then_causes_or_contexts"
    stacks: tuple[ExceptionStack | OmittedExceptionDetail, ...]
    omissions: tuple[OmittedExceptionDetail, ...] = ()


ExceptionStack.model_rebuild()
_NATIVE = structlog.tracebacks.ExceptionDictTransformer(
    show_locals=False, max_frames=12, use_rich=False
)


def _within_transform_bounds(error: BaseException) -> bool:
    """Preflight the native eager group/chain traversal without revisiting exception nodes."""
    pending = [(error, 0)]
    seen: set[int] = set()
    while pending:
        current, depth = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if len(seen) > 32 or depth > 4 or len(getattr(current, "__notes__", ())) > 16:
            return False
        if isinstance(current, BaseExceptionGroup):
            if len(current.exceptions) > 16:
                return False
            pending.extend((child, depth + 1) for child in current.exceptions)
        linked = current.__cause__ or (
            None if current.__suppress_context__ else current.__context__
        )
        if linked is not None:
            pending.append((linked, depth + 1))
    return True


def select_exception(
    native: Any, *, normalization_omissions: tuple[str, ...] = ()
) -> ExceptionTrace:
    """Decode native dictionaries, preserving omitted branches as explicit typed alternatives."""

    def omission(path: str, reason: str) -> OmittedExceptionDetail:
        return OmittedExceptionDetail(path=path, reason=reason)

    def trace(stacks: Any, path: str, depth: int) -> ExceptionTrace:
        if not isinstance(stacks, list) or depth > 4:
            return ExceptionTrace(stacks=(omission(path, "native trace omitted by bounds"),))
        selected: list[ExceptionStack | OmittedExceptionDetail] = []
        for index, item in enumerate(stacks[:16]):
            located = f"{path}[{index}]"
            if not isinstance(item, dict) or not isinstance(item.get("exc_type"), str):
                selected.append(omission(located, "native stack omitted by normalization"))
                continue
            omitted = []
            frames: list[ExceptionFrame | OmittedExceptionDetail] = []
            raw_frames = item.get("frames", [])
            if isinstance(raw_frames, list):
                for frame_index, frame in enumerate(raw_frames[:12]):
                    if isinstance(frame, dict) and all(
                        key in frame for key in ("filename", "lineno", "name")
                    ):
                        frames.append(
                            ExceptionFrame.model_validate(
                                {key: frame[key] for key in ("filename", "lineno", "name")}
                            )
                        )
                    else:
                        frames.append(
                            omission(
                                f"{located}.frames[{frame_index}]", "frame omitted by normalization"
                            )
                        )
                if len(raw_frames) > 12:
                    omitted.append(omission(located + ".frames", "frame limit 12"))
            else:
                omitted.append(omission(located + ".frames", "frames omitted by normalization"))
            children: list[ExceptionTrace | OmittedExceptionDetail] = []
            raw_children = item.get("exceptions", [])
            if isinstance(raw_children, list):
                for child_index, child in enumerate(raw_children[:16]):
                    children.append(trace(child, f"{located}.exceptions[{child_index}]", depth + 1))
                if len(raw_children) > 16:
                    children.append(omission(located + ".exceptions", "group child limit 16"))
            else:
                children.append(
                    omission(located + ".exceptions", "group children omitted by normalization")
                )
            notes = item.get("exc_notes", [])
            selected.append(
                ExceptionStack(
                    exc_type=item["exc_type"],
                    exc_value=item.get("exc_value", "[omitted]"),
                    exc_notes=tuple(note for note in notes[:16] if isinstance(note, str))
                    if isinstance(notes, list)
                    else (),
                    is_cause=item.get("is_cause", False),
                    is_group=item.get("is_group", False),
                    frames=tuple(frames),
                    exceptions=tuple(children),
                    syntax_error=item.get("syntax_error")
                    if isinstance(item.get("syntax_error"), dict)
                    else None,
                    omissions=tuple(omitted),
                )
            )
        if len(stacks) > 16:
            selected.append(omission(path, "exception chain limit 16"))
        return ExceptionTrace(stacks=tuple(selected))

    result = trace(native, "$.exception", 0)
    return result.model_copy(
        update={
            "omissions": tuple(
                omission("$.exception", message) for message in normalization_omissions
            )
        }
    )


def transform_exception(exc_info: Any) -> ExceptionTrace:
    """Retain native semantics when bounded; disclose an oversized group/chain at its root."""
    from corpus_structure.cli.observations import normalize

    try:
        error = exc_info[1]
        omitted = not _within_transform_bounds(error)
        if omitted:
            # Do not recursively transform an oversized original graph. A plain surrogate
            # carries only its root text/notes; the native transformer still owns frames,
            # type naming and syntax. The lost graph is explicitly unavailable.
            surrogate = Exception(structlog.tracebacks.safe_str(error))
            for note in getattr(error, "__notes__", ())[:16]:
                surrogate.add_note(safe_text(structlog.tracebacks.safe_str(note)))
            raw = _NATIVE((exc_info[0], surrogate, exc_info[2]))
            raw[0]["is_group"] = isinstance(error, BaseExceptionGroup)
        else:
            raw = _NATIVE(exc_info)
        safe, omissions = normalize(raw, max_bytes=24000)
        selected = select_exception(safe, normalization_omissions=omissions)
        if omitted:
            selected = selected.model_copy(
                update={
                    "omissions": (
                        *selected.omissions,
                        OmittedExceptionDetail(
                            path="$.exception",
                            reason="group/chain/note traversal limit; root retained",
                        ),
                    )
                }
            )
        return selected
    except Exception as error:
        return ExceptionTrace(
            stacks=(
                OmittedExceptionDetail(
                    path="$.exception",
                    reason="native transformation unavailable: " + type(error).__name__,
                ),
            )
        )
