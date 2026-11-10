"""Optional diagnostic custody through the existing managed result owner."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.identity import canonical_bytes

ROLE = "diagnostic-report"
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


def diagnostic_document(report, *, prepared=None, sources=(), raw_evidence=False) -> dict[str, Any]:
    """Retain exact supplied inputs; current checkout files are never a substitute."""
    data = (
        report.model_dump(mode="json", exclude_none=True)
        if hasattr(report, "model_dump")
        else report
    )
    evidence = data.get("evidence", {})
    members = []
    if evidence.get("content") is not None:
        text = evidence["content"]
        members.append(
            dict(
                name="engine",
                media_type=evidence["media_type"],
                sensitivity=evidence["sensitivity"],
                content=text,
                digest=sha256(text.encode()).hexdigest(),
            )
        )
    document = dict(version=1, report=data, members=members)
    if not sources and prepared is None:
        return document
    expected = dict(json.loads(prepared.manifest)["sources"]) if prepared is not None else None
    provenance = dict(
        sources=[],
        contributors=[],
        contributors_status="unavailable",
        source_binding="prepared_manifest" if prepared is not None else "acquired_input",
    )
    if prepared is not None:
        metadata = prepared.inspection_metadata
        provenance["contributors_status"] = metadata.get("status", "unavailable")
        seen = set()
        for item in metadata.get("classes", {}).values():
            for owner in (item, *item.get("properties", {}).values()):
                for row in owner.get("contributors", ()):
                    selected = {
                        key: row[key] for key in ("module", "path", "source_digest", "role")
                    }
                    identity = canonical_bytes(selected)
                    if identity not in seen:
                        provenance["contributors"].append(selected)
                        seen.add(identity)
    for index, source in enumerate(sources):
        if expected is not None and expected.get(source.name) != source.digest:
            raise ValueError("diagnostic source differs from prepared manifest")
        record = dict(
            module=source.name,
            digest=source.digest,
            availability="withheld",
            reason="Raw source bytes were not requested at collection.",
        )
        if raw_evidence:
            try:
                text = source.content.decode("utf-8")
            except UnicodeDecodeError:
                record.update(availability="unavailable", reason="Source is not UTF-8 text.")
            else:
                member = dict(
                    name=f"source:{index}",
                    media_type="text/yaml",
                    sensitivity="raw",
                    content=text,
                    digest=source.digest,
                )
                if (
                    len(canonical_bytes(document)) + len(canonical_bytes(member))
                    < MAX_ARTIFACT_BYTES - 65536
                ):
                    members.append(member)
                    record.update(
                        availability="available",
                        reason="Exact acquired bytes retained.",
                        member=member["name"],
                    )
                else:
                    record.update(
                        availability="omitted",
                        reason="Source exceeds remaining custody byte budget.",
                    )
        provenance["sources"].append(record)
    # Bound descriptive provenance independently; never shorten source identities.
    if len(canonical_bytes(provenance)) > 32768:
        provenance["contributors"] = []
        provenance["contributors_status"] = "omitted"
        provenance["reason"] = "Contributor detail exceeds custody metadata bound."
    text = canonical_bytes(provenance).decode()
    members.append(
        dict(
            name="provenance",
            media_type="application/json",
            sensitivity="safe",
            content=text,
            digest=sha256(text.encode()).hexdigest(),
        )
    )
    return document


def publish_diagnostic(invocation, report, *, prepared=None, sources=(), raw_evidence=False):
    from corpus_structure.semantic.operation_reporting import _validation_presentation

    document = diagnostic_document(
        report, prepared=prepared, sources=sources, raw_evidence=raw_evidence
    )
    data = document["report"]
    evidence = data.get("evidence", {})
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
            from corpus_structure.semantic.diagnostic_selection import decode_diagnostic_document

            decode_diagnostic_document(document)
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
                            invocation,
                            failure.report(error),
                            prepared=failure.prepared,
                            sources=failure.sources,
                            raw_evidence=raw_evidence,
                        )
                        failure.retained_error = error
                    except Exception as publication_error:
                        failure.diagnostic_unavailable = (
                            "Diagnostic retrieval was not established: publication failed ("
                            + type(publication_error).__name__
                            + ")."
                        )
                        try:
                            invocation.stage(
                                "diagnostic-publication-failed",
                                diagnostic_unavailable=type(publication_error).__name__,
                            )
                        except Exception as stage_error:
                            error.add_note(
                                "Diagnostic failure stage unavailable: "
                                + type(stage_error).__name__
                            )
                raise
