"""Independent full-section A/B/C references with six frozen original-PDF challenges.

Preparation reads selected source views and their archived release only. Authoring
runs three fresh tool-free Claude sessions; it never reads predictions or writes
reference/production database rows. After extraction, root can register each retained
unit batch through evaluate.semantic.record_pass with its retained native frame.
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed, wait
from contextlib import suppress
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from typing import TypedDict

from sqlalchemy import select, text
from jsonschema.validators import validator_for

from frozen_semantic_values import assess_frozen_values

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import (
    locate_proposal, native_frame_from_dict, native_source_frame, native_frame_source, proposal_packet,
)
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view, resolve_native_sections, selected_source_views
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
FROZEN_SOURCE = HERE.parent / "2026-10-31_pdf-adoption"
FROZEN = {
    "sampling": ("source-only-reference-cases.json", "890dc0a7e87c55347960eb6192518e1b0f96a35de1ea63d2b0daa2327094665f"),
    "normal": ("source-only-normal-reference.json", "e865e4da17ad0140e70805ec5e81e0c5dd9df395fe5ffbbbc85dc69c6e783a57"),
}
# Topics deliberately omit the frozen expected formulas/numeric values/conditions.
TOPICS = {
    "sampling": {
        "section": "1.8: Combinatorial Structures", "physical_page": 85,
        "cases": {
            "ordered-replacement": "Count ordered samples with replacement.",
            "unordered-replacement": "Count unordered samples with replacement.",
            "unordered-no-replacement": "Count unordered samples without replacement.",
            "multinomial-partition": "Count ordered disjoint set partitions with prescribed subset sizes; preserve the source's conditions.",
        },
    },
    "normal": {
        "section": "5.6: The Normal Distribution", "physical_page": 596,
        "cases": {
            "standard-normal-mean": "The source assertion about the mean of the standard normal random variable.",
            "standard-normal-variance": "The source assertion about the variance of that variable.",
        },
    },
}


class SourcePacket(TypedDict):
    frame: dict
    parts: dict[str, str]
    packet_hash: str
    source_case: str
    topic: dict


def write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value)


def frozen_cases() -> dict:
    """Local expectations are never included in any provider input."""
    result = {}
    for key, (name, digest) in FROZEN.items():
        raw = (FROZEN_SOURCE / name).read_bytes()
        if sha256(raw).hexdigest() != digest:
            raise ValueError("frozen reference input changed: " + name)
        value = json.loads(raw)
        if {row["id"] for row in value["assertions"]} != set(TOPICS[key]["cases"]):
            raise ValueError("frozen case universe changed")
        result[key] = value
    return result


def response_schema(batch_schema: dict) -> dict:
    schema = copy.deepcopy(batch_schema)
    definitions = schema.pop("$defs", {})
    schema.pop("$id", None)
    case_ids = [identity for topic in TOPICS.values() for identity in topic["cases"]]
    return {
        "type": "object", "additionalProperties": False,
        "$defs": definitions,
        "required": ["units", "assertions", "notes"],
        "properties": {
            "units": {"type": "array", "minItems": 2, "maxItems": 2, "items": {
                "type": "object", "additionalProperties": False,
                "required": ["source_case", "authored_batch"],
                "properties": {"source_case": {"enum": list(TOPICS)}, "authored_batch": schema},
            }},
            "assertions": {"type": "array", "minItems": 6, "maxItems": 6, "items": {
                "type": "object", "additionalProperties": False,
                "required": ["id", "latex", "conditions", "claim_ids"],
                "properties": {
                    "id": {"enum": case_ids}, "latex": {"type": "string"},
                    "conditions": {"type": "array", "items": {"type": "string"}},
                    "claim_ids": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                },
            }},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
    }


def prepare(args) -> None:
    expected = frozen_cases()
    selection = json.loads(args.selection.read_bytes())
    if selection["run_id"] != args.run_id:
        raise ValueError("reference run differs from the explicitly selected current run")
    selected_pin = {key: selection[key] for key in ("task_id", "product_key", "content_digest")}
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("prepare requires a new reference-only directory")
    exported: dict[str, SourcePacket] = {}
    settings = Settings()
    # No data.fact/data.membership/eval/production output reads occur in this path.
    with open_runtime_engine(settings, "ci-source-only-reference", purpose="read") as engine:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            run = conn.execute(select(table("ops.run")).where(table("ops.run").c.id == args.run_id)).mappings().one()
            release = open_release(conn, run["release_id"])
            references = selected_source_views(conn, args.run_id)
            if any(reference.native_product.values() != selected_pin for reference in references):
                raise ValueError("reference source views differ from the explicit current product pin")
            views = {ref.id: load_source_view(conn, ref.id) for ref in references}
            catalog = {identity: next(item["name"] for item in view.items if item["self_ref"] == view.ref.section_pointer) for identity, view in views.items() if view.ref.analysis_eligible}
            selected = resolve_native_sections(catalog, [topic["section"] for topic in TOPICS.values()])
            for key, identity in zip(TOPICS, selected, strict=True):
                view = views[identity]
                document = conn.execute(select(table("kb.document")).where(table("kb.document").c.id == view.ref.document_id)).mappings().one()
                if document["project_id"] != run["project_id"] or document["content_hash"] != expected[key]["source_sha256"]:
                    raise ValueError("selected source does not match frozen original/project")
                if view.ref.membership != "descendants":
                    raise ValueError("reference topics require the intact descendant section view")
                # Each independent reference owns its own frame over the exact retained
                # source view. No extractor task/frame is a prerequisite or an input.
                frame = native_source_frame(view, ())
                ancestry = [item["self_ref"] for item in view.ancestors]
                parents = [parent for parent in views.values()
                    if parent.ref.membership == "direct"
                    and parent.ref.native_product == view.ref.native_product
                    and parent.ref.section_pointer in ancestry]
                parents.sort(key=lambda parent: ancestry.index(parent.ref.section_pointer))
                frame = replace(frame, context_sources=tuple(
                    native_frame_source(native_source_frame(parent, ())) for parent in parents
                ))
                packet = proposal_packet(release, frame, guideline=run["guideline"], configuration={"reference_scope": "complete-two-intact-native-sections", "packet_cap_chars": 18000}, known_classes={})
                exported[key] = {
                    "frame": asdict(frame),
                    "parts": {part.name: part.text for part in packet.parts()},
                    "packet_hash": packet.hash,
                    "source_case": key, "topic": TOPICS[key],
                }
            batch_schema = release.json_schema("AgentAuthoredBatch", mode="serialization")
            domain_definitions = [asdict(definition) for definition in release.definitions if definition.iri.startswith("https://corpus-structure.dev/domains/statistics/") or definition.name in {"Entity", "Statement", "MathematicalExpression", "Value"}]
            manifest = {
                "run_id": args.run_id, "release_id": release.release_id, "project_id": run["project_id"],
                "native_product": selected_pin,
                "selection_sha256": sha256(args.selection.read_bytes()).hexdigest(),
                "created_unix": time.time(), "scope": "complete supported content of two intact native sections; independent original-PDF fidelity challenge limited to two pages/six frozen facts",
                "frozen_inputs": {key: {"name": name, "sha256": digest} for key, (name, digest) in FROZEN.items()},
                "frames": {key: {"sha256": sha256(canonical_bytes(value["frame"])).hexdigest(), "reference_packet_hash": value["packet_hash"], "source_view_id": value["frame"]["source_view_id"]} for key, value in exported.items()},
                "database_reads": "selected native source views/items, original document identity, run input/release only; no predictions",
                "frame_owner": "independent reference, directly over immutable adopted views; no extractor packet/frame input",
            }
    inputs = {
        "sources.json": canonical_bytes(exported),
        "domain-definitions.json": canonical_bytes(domain_definitions),
        "response.schema.json": canonical_bytes(response_schema(batch_schema)),
        **{f"source-{key}.png": (FROZEN_SOURCE / value["reference_image"]).read_bytes() for key, value in expected.items()},
    }
    manifest["input_digests"] = {name: sha256(value).hexdigest() for name, value in inputs.items()}
    for name, value in inputs.items():
        write_new(output / name, value)
    write_new(output / "manifest.json", canonical_bytes(manifest))
    print(json.dumps(manifest, indent=2))


def provider_environment() -> dict[str, str]:
    # Credentials for the provider remain available; database/checkout context does not.
    return {key: value for key, value in os.environ.items() if not key.startswith(("CORPUS_", "PG", "DATABASE", "UV_")) and key not in {"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "PWD", "OLDPWD", "BASH_ENV"}}


PROVIDER_POLL_SECONDS = 0.2
PROVIDER_CLEANUP_SECONDS = 5.0


def _stop_provider(process):
    """Bound both termination and pipe draining; never inherit the request timeout."""
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM)
    try:
        return process.communicate(timeout=PROVIDER_CLEANUP_SECONDS)
    except subprocess.TimeoutExpired:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        return process.communicate(timeout=PROVIDER_CLEANUP_SECONDS)


def _communicate_provider(process, message, timeout, cancelled):
    deadline = time.monotonic() + timeout
    first = True
    while True:
        if cancelled is not None and cancelled.is_set():
            raise CancelledError("independent author group cancelled")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(process.args, timeout)
        arguments = {"input": message} if first else {}
        first = False
        try:
            return process.communicate(
                **arguments, timeout=min(PROVIDER_POLL_SECONDS, remaining)
            )
        except subprocess.TimeoutExpired:
            continue


def provider_pass(directory: Path, kind: str, *, model: str, timeout: float, max_output_tokens: int, sources: dict, schema: dict, previous: dict | None = None, cancelled: threading.Event | None = None) -> dict:
    command = shutil.which("claude")
    if command is None:
        raise RuntimeError("authenticated Claude CLI is required")
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    schema_text = canonical_bytes(schema).decode()
    if len(schema_text.encode()) > 100_000:
        raise ValueError("schema exceeds safe single CLI argument size; do not weaken the rich schema")
    instructions = (
        "Author an independent source-only reference containing the COMPLETE supported content of BOTH intact supplied native sections. "
        "Use the rendered original PDF pages for mathematical source meaning, and the complete pinned native frames for exact evidence addresses. "
        "Output the supplied rich AgentAuthoredBatch schema for each intact source unit, including locally declared entities, statements, conditions, bindings and evidence. "
        "Follow the archived annotation guideline for ALL supported entities, statements, claims, premises, conditions, bindings, qualifications and explicitly unsupported content in each whole section. "
        "The six named topics are highlighted original-PDF fidelity challenges, NOT a restriction on the full authored batches. "
        "For the rest of each section, completeness is relative to the supplied retained source; do not invent missing native content from general knowledge. "
        "The two original images independently challenge those six highlighted facts only; no full-original-PDF fidelity claim is requested. "
        "Do not guess missing facts, infer a theorem from recognition health, or cite an address absent from the frame. "
        "Cite exact native_evidence:<index> handles and quotes from the supplied unit's native_evidence inventory. "
        "Supplied native_context:<source_view_id>:<local_id> handles retain the ancestor's own coordinates; do not rebase them into the child. "
        "If the original formula differs from recognized text, preserve the source meaning and cite its actual containing native evidence; report the discrepancy in notes. "
        "Every assertion ID must map to one or more actual authored claim IDs in its source batch. "
        "The assertions summary latex must exactly equal the actual linked claim object's expression or exact number. "
        "Represent the requested count/value as that claim's object, with its source conditions and bindings retained. "
        "For the assertions summary, use source LaTex with no outer delimiters, compact spacing, and retain source conditions. "
        "No existing reference answers, extractor predictions, production facts, tools or database are available. "
    )
    if kind == "C":
        instructions += "You are fresh adjudicator C. Adjudicate the COMPLETE content of BOTH sections from the full independent A and B batches and supplied sources. Resolve omissions as well as disagreements from source evidence. Do not merely take their intersection. Record unresolved differences honestly in notes. "
    else:
        instructions += f"You are independent author {kind}; no other author output is supplied. "
    content = [{"type": "text", "text": instructions + "\n" + canonical_bytes({"sources": sources, "domain_definitions": json.loads((directory / 'domain-definitions.json').read_bytes()), **({"independent_authors": previous} if previous is not None else {})}).decode()}]
    for key, topic in TOPICS.items():
        content += [{"type": "text", "text": f"Original physical page {topic['physical_page']} for source_case={key}."}, {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode((directory / f"source-{key}.png").read_bytes()).decode()}}]
    message = canonical_bytes({"type": "user", "message": {"role": "user", "content": content}, "parent_tool_use_id": None}) + b"\n"
    session = str(uuid.uuid4())
    write_new(directory / f"{kind}.input.jsonl", message)
    with tempfile.TemporaryDirectory(prefix=f"source-reference-{kind}-") as isolated:
        config = Path(isolated) / "mcp.json"
        config.write_text('{"mcpServers":{}}')
        argv = [command, "-p", "--model", model, "--input-format", "stream-json", "--output-format", "json", "--json-schema", schema_text, "--session-id", session, "--tools", "", "--strict-mcp-config", "--mcp-config", str(config), "--permission-mode", "dontAsk", "--no-session-persistence", "--max-turns", "8", "--restricted", "--disable-slash-commands", "--setting-sources", "", "--settings", json.dumps({"disableAllHooks": True, "claudeMdExcludes": ["**"], "autoMemoryEnabled": False})]
        write_new(directory / f"{kind}.invocation.json", canonical_bytes({"session_id": session, "model": model, "pass_kind": kind, "prompt_digest": sha256(message).hexdigest(), "schema_digest": sha256(canonical_bytes(schema)).hexdigest(), "independent_prior_passes": [] if previous is None else list(previous), "database_credentials_forwarded": False, "tools": [], "mcp_servers": [], "timeout": timeout, "requested_max_output_tokens": max_output_tokens}))
        environment = provider_environment()
        environment["CLAUDE_CODE_MAX_OUTPUT_TOKENS"] = str(max_output_tokens)
        if cancelled is not None and cancelled.is_set():
            raise CancelledError("independent author cancelled before process launch")
        process = subprocess.Popen(argv, cwd=isolated, env=environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = _communicate_provider(process, message, timeout, cancelled)
        except BaseException as error:
            cleanup_error = None
            try:
                stdout, stderr = _stop_provider(process)
            except BaseException as cleanup:
                cleanup_error = cleanup
                stdout = getattr(cleanup, "output", None) or b""
                stderr = getattr(cleanup, "stderr", None) or b""
                write_new(directory / f"{kind}.cleanup-failed.json", canonical_bytes({
                    "error_type": type(error).__name__, "error": str(error),
                    "cleanup_error": str(cleanup), "pid": process.pid,
                }))
            write_new(directory / f"{kind}.interrupted.stdout.json", stdout)
            write_new(directory / f"{kind}.interrupted.stderr.txt", stderr)
            if cleanup_error is not None:
                raise BaseExceptionGroup(
                    "reference provider failed and cleanup failed", [error, cleanup_error]
                )
            raise
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        write_new(directory / f"{kind}.stdout.json", stdout)
        write_new(directory / f"{kind}.stderr.txt", stderr)
    response = json.loads(stdout)
    if process.returncode or response.get("is_error") or not isinstance(response.get("structured_output"), dict):
        raise RuntimeError(f"reference author {kind} failed/refused; retained raw response")
    if response.get("session_id") != session:
        raise RuntimeError("provider response differs from independent session identity")
    value = response["structured_output"]
    validator_class(schema).validate(value)
    write_new(directory / f"{kind}.structured.json", canonical_bytes(value))
    return value


def authored_passes(release, sources, schema, directory, *, model, timeout, max_output_tokens):
    """Fresh A/B sessions run concurrently; C waits for both main-thread admissions."""
    cancelled = threading.Event()
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="source-author")
    futures = {}
    values = {}
    try:
        for kind in ("A", "B"):
            future = executor.submit(
                provider_pass, directory, kind, model=model, timeout=timeout,
                max_output_tokens=max_output_tokens, sources=sources, schema=schema,
                cancelled=cancelled,
            )
            futures[future] = kind
        for future in as_completed(futures):
            kind = futures[future]
            value = future.result()
            # Placement/scientific policies retain their main-thread deadline owner.
            validate_pass(release, sources, value, directory, kind)
            values[kind] = value
    except BaseException as error:
        cancelled.set()
        for future in futures:
            future.cancel()
        _, pending = wait(
            futures, timeout=2 * PROVIDER_CLEANUP_SECONDS + 2 * PROVIDER_POLL_SECONDS + 1
        )
        settlements = {}
        for future, kind in futures.items():
            if future.cancelled():
                settlements[kind] = {"state": "cancelled_before_execution"}
            elif not future.done():
                settlements[kind] = {"state": "cleanup_pending"}
            else:
                failure = future.exception()
                settlements[kind] = (
                    {"state": "failed", "error_type": type(failure).__name__,
                     "error": str(failure)}
                    if failure is not None else {"state": "returned"}
                )
        write_new(directory / "independent-authors-interrupted.json", canonical_bytes({
            "error_type": type(error).__name__, "error": str(error),
            "pending_cleanup": sorted(futures[future] for future in pending),
            "cleanup_failures": [path.name for path in directory.glob("*.cleanup-failed.json")],
            "completed_admissions": sorted(values), "C_started": False,
            "pass_settlements": settlements,
        }))
        if pending:
            error.add_note("independent author cleanup did not settle within its bounded grace")
        raise
    finally:
        # No context-manager shutdown waiting on a sibling's 1800-second request.
        executor.shutdown(wait=False, cancel_futures=True)
    values = {kind: values[kind] for kind in ("A", "B")}
    values["C"] = provider_pass(
        directory, "C", model=model, timeout=timeout, max_output_tokens=max_output_tokens,
        sources=sources, schema=schema, previous=values.copy(),
    )
    validate_pass(release, sources, values["C"], directory, "C")
    return values


def validate_pass(release, sources: dict, value: dict, directory: Path, kind: str) -> None:
    units = {unit["source_case"]: unit["authored_batch"] for unit in value["units"]}
    if len(value["units"]) != 2 or set(units) != set(TOPICS):
        raise ValueError("reference author omitted/duplicated an intact source unit")
    assertions = {row["id"]: row for row in value["assertions"]}
    if len(value["assertions"]) != 6 or set(assertions) != {identity for topic in TOPICS.values() for identity in topic["cases"]}:
        raise ValueError("reference author changed the six-fact scope")
    for key, batch in units.items():
        frame = native_frame_from_dict(sources[key]["frame"])
        located = locate_proposal(release, batch, frame, known_classes={})
        if not located.clean:
            raise ValueError(f"reference {kind}/{key} citations unresolved: {located.issues}")
        claims = {row["id"]: row for row in batch.get("claims", ())}
        for identity in TOPICS[key]["cases"]:
            if not assertions[identity]["claim_ids"] or not set(assertions[identity]["claim_ids"]) <= claims.keys():
                raise ValueError("reference assertion does not identify actual source-batch claims")
            values = [claims[claim]["object"] for claim in assertions[identity]["claim_ids"]]
            rendered = [str(value["expression"] if "expression" in value else value["number"]) for value in values if "expression" in value or "number" in value]
            if assertions[identity]["latex"] not in rendered:
                raise ValueError("assertion summary differs from its linked rich claim value")
        write_new(directory / f"{kind}.{key}.authored.json", canonical_bytes(batch))
    write_new(directory / f"{kind}.validation.json", canonical_bytes({"outcome": "passed", "scope": "rich release schema, closed local references, exact native citations, six declared assertion links; not a semantic grade"}))


def frozen_diagnostics(frozen: dict, adjudicated: dict, scope: str) -> dict:
    """Report lexical observations without treating them as mathematical proof/refutation."""
    actual = {row["id"]: row for row in adjudicated["assertions"]}
    comparisons = []
    for key, expected in frozen.items():
        for row in expected["assertions"]:
            found = actual[row["id"]]
            comparisons.append({"id": row["id"], "expected_latex": row["latex"], "authored_latex": found["latex"], "latex_exact": row["latex"] == found["latex"], "expected_conditions": row.get("conditions", []), "authored_conditions": found["conditions"], "conditions_exact": row.get("conditions", []) == found["conditions"]})
    lexical_exact = all(row["latex_exact"] and row["conditions_exact"] for row in comparisons)
    return {
        "outcome": "partial",
        "scope": scope,
        "comparison": "frozen lexical diagnostics; no normalization, tuning or provider retry",
        "lexical_exact": lexical_exact,
        "comparisons": comparisons,
        "frozen_source_semantic_assessment": "not_run; lexical equality or difference does not establish mathematical equivalence or source fidelity",
        "extraction_semantic_grade": "not_run; existing evaluator compares complete typed reference/extraction batches with qualified mathematical comparisons, undecided results and field failures",
        "registration": "not_run; root registers retained batches after completed extraction through evaluate.semantic.record_pass",
    }


def author(args) -> None:
    frozen = frozen_cases()
    directory = args.input.resolve()
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if args.run_id != manifest["run_id"]:
        raise ValueError("explicit adopted run does not match prepared source frames")
    for name, digest in manifest["input_digests"].items():
        if sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError("prepared reference input changed: " + name)
    sources = json.loads((directory / "sources.json").read_bytes())
    schema = json.loads((directory / "response.schema.json").read_bytes())
    for key, source in sources.items():
        if sha256(canonical_bytes(source["frame"])).hexdigest() != manifest["frames"][key]["sha256"]:
            raise ValueError("prepared source frame changed")
    with open_runtime_engine(Settings(), "ci-source-reference-release", purpose="read") as engine:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            release = open_release(conn, manifest["release_id"])
    values = authored_passes(
        release, sources, schema, directory, model=args.model, timeout=args.timeout,
        max_output_tokens=args.max_output_tokens,
    )
    # Only after all independent sessions finish do local frozen expected values enter comparison.
    result = frozen_diagnostics(frozen, values["C"], manifest["scope"])
    result["frozen_source_semantic_assessment"] = assess_frozen_values(
        frozen, values["C"], prepared=release
    )
    result["authoring_validation"] = (
        "passed; rich schema, local closure and exact citation admission only"
    )
    write_new(directory / "frozen-comparison.json", canonical_bytes(result))
    print(json.dumps(result, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepared = commands.add_parser("prepare")
    prepared.add_argument("--run-id", type=int, required=True)
    prepared.add_argument("--selection", type=Path, required=True)
    prepared.add_argument("--output", type=Path, required=True)
    authored = commands.add_parser("author")
    authored.add_argument("--run-id", type=int, required=True)
    authored.add_argument("--input", type=Path, required=True)
    authored.add_argument("--model", required=True)
    authored.add_argument("--timeout", type=float, default=1800)
    authored.add_argument("--max-output-tokens", type=int, default=128000)
    args = parser.parse_args()
    if args.command == "author" and (args.max_output_tokens < 1 or args.timeout <= 0):
        raise ValueError("provider limits must be positive")
    if args.run_id < 1:
        raise ValueError("a concrete adopted run ID is required")
    (prepare if args.command == "prepare" else author)(args)

if __name__ == "__main__":
    main()
