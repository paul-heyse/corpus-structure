"""Bounded safe recipe output retained and replayed through managed result custody."""

from __future__ import annotations

import hashlib
import os
import re
import shlex
import stat
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field
from rich.console import Group
from rich.text import Text

from corpus_structure._diagnostic_capture import (
    MAX_RECIPE_STEPS,
    STEP_CHANNEL_BYTES,
    STEP_STREAM_BYTES,
    StepExit,
    StepOutput,
    bounded_safe_output,
    valid_step_output,
)

if TYPE_CHECKING:
    from corpus_structure.cli.managed import Invocation, ResultStore
    from corpus_structure.cli.recipes import RecipeCapture

ROLE = "recipe-output"
# Native step payloads plus two bounded wrapper streams and the versioned envelope.
ARTIFACT_BYTES = STEP_CHANNEL_BYTES + 4 * STEP_STREAM_BYTES + 16384
PAGE_BYTES = 256 * 1024


class RecipeOutputBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    length: int = Field(ge=0, le=ARTIFACT_BYTES)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class RecipeOutputDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    result: str
    recipe: str
    exit_code: int
    wrapper: tuple[StepOutput, ...]
    step_capture: Literal["not_requested", "available", "unavailable"]
    step_capture_reason: str | None = None
    steps: tuple[StepExit, ...] = ()
    missing_steps: tuple[str, ...] = ()
    step_channel_bytes_limit: int = STEP_CHANNEL_BYTES
    artifact_bytes_limit: int = ARTIFACT_BYTES


class RecipeOutputReference(BaseModel):
    availability: Literal["available", "unavailable"]
    read_command: str | None = None
    reason: str | None = None


class RecipeOutputPage(BaseModel):
    version: Literal[1] = 1
    result: str
    recipe: str
    exit_code: int
    stream: Literal["stdout", "stderr"]
    step: str | None = None
    selection: Literal["recipe_wrapper", "native_step"]
    coordinate: Literal["retained_safe_unicode_codepoints"] = "retained_safe_unicode_codepoints"
    after: int
    end: int
    next_after: int | None = None
    text: str
    retained_characters: int
    source_coordinate: Literal["native_bytes", "decoded_process_utf8_bytes"]
    observed_source_bytes: int
    examined_source_bytes: int
    unexamined_source_bytes: int
    retained_safe_bytes: int
    retained_safe_bytes_limit: int
    omitted_safe_bytes: int
    collection_truncated: bool
    authentication_bytes: int
    artifact_bytes_limit: int = ARTIFACT_BYTES
    next_read: str | None = None


def _read_command(result: str, stream: str, step: str | None, after: int | None = None) -> str:
    arguments = ["ci", "results", "output", result, "--stream", stream]
    if step is not None:
        arguments += ["--step", step]
    if after is not None:
        arguments += ["--after", str(after)]
    return shlex.join([*arguments, "--json"])


def retain_output(
    invocation: Invocation,
    recipe: str,
    exit_code: int,
    *,
    stdout: str,
    stderr: str,
    stdout_source_bytes: int,
    stderr_source_bytes: int,
    captured: RecipeCapture | None = None,
) -> RecipeOutputReference:
    """Publish already-safe selections; optional publication never replaces the native outcome."""
    try:
        document = RecipeOutputDocument(
            result=invocation.id,
            recipe=recipe,
            exit_code=exit_code,
            wrapper=tuple(
                bounded_safe_output(
                    stream,
                    safe,
                    source_coordinate="decoded_process_utf8_bytes",
                    observed_source_bytes=observed,
                    examined_source_bytes=observed,
                )
                for stream, safe, observed in (
                    ("stdout", stdout, stdout_source_bytes),
                    ("stderr", stderr, stderr_source_bytes),
                )
            ),
            step_capture="not_requested" if captured is None else captured.availability,
            step_capture_reason=None if captured is None else captured.reason,
            steps=() if captured is None else captured.records,
            missing_steps=() if captured is None else captured.missing_steps,
        )
        encoded = document.model_dump_json().encode()
        if len(encoded) > ARTIFACT_BYTES:
            raise ValueError("recipe output artifact exceeds its byte limit")
        artifact = invocation.directory / "recipe-output.json"
        artifact.write_bytes(encoded)
        artifact.chmod(0o600)
        binding = RecipeOutputBinding(
            length=len(encoded), sha256=hashlib.sha256(encoded).hexdigest()
        )
        invocation.manifest.details["recipe_output"] = binding.model_dump(mode="json")
        invocation.publish(ROLE, artifact)
        preferred = next((step.name for step in document.steps if step.status), None)
        if preferred is None and document.steps:
            preferred = document.steps[0].name
        return RecipeOutputReference(
            availability="available", read_command=_read_command(invocation.id, "stdout", preferred)
        )
    except Exception as error:
        invocation.observe(
            "recipe_output_unavailable",
            "Recipe output retention unavailable",
            reason=type(error).__name__,
        )
        return RecipeOutputReference(
            availability="unavailable",
            reason="Recipe output publication failed: " + type(error).__name__,
        )


def _validate_document(document: RecipeOutputDocument) -> None:
    if (
        document.step_channel_bytes_limit != STEP_CHANNEL_BYTES
        or document.artifact_bytes_limit != ARTIFACT_BYTES
    ):
        raise ValueError("unsupported recipe output bounds")
    if len(document.wrapper) != 2 or {item.stream for item in document.wrapper} != {
        "stdout",
        "stderr",
    }:
        raise ValueError("invalid wrapper streams")
    if len(document.steps) + len(document.missing_steps) > MAX_RECIPE_STEPS:
        raise ValueError("invalid step count")
    names = [step.name for step in document.steps] + list(document.missing_steps)
    if len(set(names)) != len(names) or any(
        not re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", name) for name in names
    ):
        raise ValueError("invalid step identity")
    for step in document.steps:
        if (
            not 0 <= step.status <= 255
            or len(step.outputs) != 2
            or {item.stream for item in step.outputs} != {"stdout", "stderr"}
        ):
            raise ValueError("invalid native step record")
        if any(item.step != step.name for item in step.excerpts):
            raise ValueError("invalid excerpt binding")
    if not all(
        valid_step_output(output)
        for output in (
            *document.wrapper,
            *(output for step in document.steps for output in step.outputs),
        )
    ):
        raise ValueError("invalid retained output accounting")
    if document.step_capture != "available" and (document.steps or document.missing_steps):
        raise ValueError("unavailable capture cannot claim native records")


def read_output(
    store: ResultStore,
    result: str,
    *,
    stream: Literal["stdout", "stderr"],
    step: str | None = None,
    after: int = 0,
    max_bytes: int = PAGE_BYTES,
) -> RecipeOutputPage:
    """Authenticate one settled bounded artifact and select safe text without producer execution."""
    from corpus_structure.cli.managed import ResultError

    if after < 0 or not 4096 <= max_bytes <= 1024 * 1024:
        raise ResultError(
            "recipe output requires a nonnegative character offset and a 4KiB-1MiB response budget"
        )
    with store.lease(result):
        manifest = store.show(result, role=ROLE)
        if ROLE not in manifest.artifacts or "recipe_output" not in manifest.details:
            raise ResultError("retained recipe output unavailable for this result")
        try:
            binding = RecipeOutputBinding.model_validate(manifest.details["recipe_output"])
            with store.open_artifact(result, ROLE) as (_, fd):
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ValueError("recipe output is not a regular file")
                data = os.pread(fd, ARTIFACT_BYTES + 1, 0)
            if len(data) != binding.length or hashlib.sha256(data).hexdigest() != binding.sha256:
                raise ValueError("recipe output digest or length mismatch")
            document = RecipeOutputDocument.model_validate_json(data, strict=True)
            _validate_document(document)
            if document.result != result or manifest.action != "recipe." + document.recipe:
                raise ValueError("recipe output differs from its invocation binding")
        except (ValueError, OSError) as error:
            raise ResultError(
                "retained recipe output is corrupt, unsupported, or unavailable"
            ) from error
        selected = None
        if step is not None:
            native = next((item for item in document.steps if item.name == step), None)
            if native is None:
                raise ResultError("retained output is unavailable for the selected native step")
            selected = next(item for item in native.outputs if item.stream == stream)
        elif document.step_capture == "available" and document.steps:
            if len(document.steps) != 1 or document.missing_steps:
                raise ResultError(
                    "select one native step with --step: "
                    + ", ".join(item.name for item in document.steps)
                )
            step = document.steps[0].name
            selected = next(item for item in document.steps[0].outputs if item.stream == stream)
        elif document.step_capture == "unavailable":
            raise ResultError(
                "native step output unavailable: "
                + (document.step_capture_reason or "capture not established")
            )
        elif document.missing_steps:
            raise ResultError("native step output unavailable: no completed stream capture")
        else:
            selected = next(item for item in document.wrapper if item.stream == stream)
        if after > len(selected.text):
            raise ResultError("recipe output character offset exceeds the retained selection")

        def page(end: int) -> RecipeOutputPage:
            following = end if end < len(selected.text) else None
            return RecipeOutputPage(
                result=result,
                recipe=document.recipe,
                exit_code=document.exit_code,
                stream=stream,
                step=step,
                selection="recipe_wrapper" if step is None else "native_step",
                after=after,
                end=end,
                next_after=following,
                text=selected.text[after:end],
                retained_characters=len(selected.text),
                source_coordinate=selected.source_coordinate,
                observed_source_bytes=selected.observed_source_bytes,
                examined_source_bytes=selected.examined_source_bytes,
                unexamined_source_bytes=selected.unexamined_source_bytes,
                retained_safe_bytes=selected.retained_safe_bytes,
                retained_safe_bytes_limit=selected.retained_safe_bytes_limit,
                omitted_safe_bytes=selected.omitted_safe_bytes,
                collection_truncated=selected.truncated,
                authentication_bytes=len(data),
                next_read=_read_command(result, stream, step, following)
                if following is not None
                else None,
            )

        low, high = after, min(len(selected.text), after + max_bytes)
        if len(page(low).model_dump_json().encode()) > max_bytes:
            raise ResultError("recipe output envelope exceeds response byte budget")
        while low < high:
            middle = (low + high + 1) // 2
            if len(page(middle).model_dump_json().encode()) <= max_bytes:
                low = middle
            else:
                high = middle - 1
        if low == after and after < len(selected.text):
            raise ResultError("recipe output response budget cannot admit the next character")
        return page(low)


def render_output(page: RecipeOutputPage) -> Group:
    parts = [
        Text(page.text),
        Text(f"{page.coordinate}: {page.after}-{page.end}/{page.retained_characters}"),
    ]
    if page.collection_truncated:
        parts.append(Text("Collection was truncated; replay cannot recover omitted output."))
    if page.next_read is not None:
        parts.append(Text(page.next_read))
    return Group(*parts)
