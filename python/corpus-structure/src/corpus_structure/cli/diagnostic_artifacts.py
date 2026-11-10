"""Optional diagnostic custody through the existing managed result owner."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from hashlib import sha256

from corpus_structure.semantic.identity import canonical_bytes

ROLE = "diagnostic-report"
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


def publish_diagnostic(invocation, report):
    from corpus_structure.semantic.operation_reporting import _validation_presentation

    data = report.model_dump(mode="json", exclude_none=True)
    evidence = data.get("evidence", {})
    members = []
    if evidence.get("content") is not None:
        content = evidence["content"]
        members.append(
            dict(
                name="engine",
                media_type=evidence["media_type"],
                sensitivity=evidence["sensitivity"],
                content=content,
                digest=sha256(content.encode()).hexdigest(),
            )
        )
    document = dict(version=1, report=data, members=members)
    content = canonical_bytes(document)
    if len(content) > MAX_ARTIFACT_BYTES:
        raise ValueError("diagnostic artifact exceeds the custody byte limit")
    path = invocation.directory / "diagnostic-report.json"
    path.write_bytes(content)
    invocation.publish(ROLE, path)
    digest = sha256(content).hexdigest()
    invocation.stage(invocation.manifest.stage, diagnostic_sha256=digest)
    fields = {
        key: value
        for key, value in data.items()
        if key not in {"report_version", "report_schema_digest"}
    }
    fields["evidence"] = dict(
        kind="managed",
        engine=evidence.get("engine", "boundary"),
        media_type="application/json",
        digest=digest,
        sensitivity=evidence.get("sensitivity", "safe"),
        result_id=invocation.id,
        artifact_role=ROLE,
        member="report",
    )
    limits = fields["presentation"]
    return _validation_presentation(
        fields,
        detail="correction_detail" in fields,
        max_errors=limits["max_errors"],
        max_depth=limits["max_depth"],
        max_bytes=limits["max_bytes"],
    )


def read_diagnostic(store, result_id, *, raw_evidence=False, max_bytes=MAX_ARTIFACT_BYTES):
    from corpus_structure.cli.managed import ResultError

    if type(max_bytes) is not int or not 1024 <= max_bytes <= MAX_ARTIFACT_BYTES:
        raise ResultError("diagnostic read limit exceeds supported range")
    with store.lease(result_id):
        manifest = store.show(result_id)
        expected = manifest.details.get("diagnostic_sha256")
        if not isinstance(expected, str):
            raise ResultError("diagnostic digest is unavailable in this invocation")
        with store.open_artifact(result_id, ROLE) as (_, fd), os.fdopen(os.dup(fd), "rb") as stream:
            content = stream.read(max_bytes + 1)
        if len(content) > max_bytes or sha256(content).hexdigest() != expected:
            raise ResultError("diagnostic bytes exceed the limit or differ from retained digest")
        try:
            document = json.loads(content)
            if (
                type(document["version"]) is not int
                or document["version"] != 1
                or set(document) != {"version", "report", "members"}
            ):
                raise ValueError("unsupported diagnostic artifact")
            if (
                document["report"].get("evidence", {}).get("sensitivity") == "raw"
                and not raw_evidence
            ):
                raise ResultError("raw diagnostic retrieval requires --raw-evidence")
            for member in document["members"]:
                if sha256(member["content"].encode()).hexdigest() != member["digest"]:
                    raise ValueError("diagnostic member digest differs")
                if member["sensitivity"] == "raw" and not raw_evidence:
                    raise ResultError("raw diagnostic retrieval requires --raw-evidence")
        except ResultError:
            raise
        except (KeyError, TypeError, ValueError) as error:
            raise ResultError("diagnostic artifact is malformed or corrupt") from error
        return document


@contextmanager
def diagnostic_scope(
    ctx,
    *,
    action,
    json,
    retain=False,
    detail=False,
    raw_evidence=False,
    max_errors=100,
    max_depth=8,
    max_bytes=262144,
    expected=(),
):
    from contextlib import ExitStack

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.cli.managed import result_store
    from corpus_structure.semantic.execution_admission import ExecutionAdmissionError
    from corpus_structure.semantic.refusals import FailureContext
    from corpus_structure.semantic.releases import ReleaseConflict
    from corpus_structure.semantic.types import PreparationError

    failure = FailureContext(
        correction_detail=detail,
        raw_evidence=raw_evidence,
        max_errors=max_errors,
        max_depth=max_depth,
        max_bytes=max_bytes,
    )
    with ExitStack() as stack:
        invocation = (
            stack.enter_context(result_store(ctx).operation(action, account=True))
            if retain
            else None
        )
        with failure_boundary(
            json,
            expected=(
                PreparationError,
                ReleaseConflict,
                ExecutionAdmissionError,
                *expected,
            ),
            context=failure,
            operation=invocation,
        ):
            from corpus_structure.semantic.correction_detail import _detail_limits
            from corpus_structure.semantic.refusals import SemanticRefusal

            try:
                _detail_limits(max_errors, max_depth, max_bytes)
            except ValueError as error:
                raise SemanticRefusal("Invalid correction presentation limits.") from error
            try:
                yield failure, invocation
            except Exception as error:
                if invocation is not None:
                    try:
                        failure.retained_validation = publish_diagnostic(
                            invocation, failure.report(error)
                        )
                        failure.retained_error = error
                    except Exception as publication_error:
                        failure.diagnostic_unavailable = (
                            "Diagnostic retrieval was not established: publication failed ("
                            + type(publication_error).__name__
                            + ")."
                        )
                        invocation.stage(
                            "diagnostic-publication-failed",
                            diagnostic_unavailable=type(publication_error).__name__,
                        )
                raise
