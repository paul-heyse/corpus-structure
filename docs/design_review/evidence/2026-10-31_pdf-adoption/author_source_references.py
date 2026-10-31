"""Independent source-only A/B/C reference authoring for six frozen PDF facts.

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
import time
import uuid
from contextlib import suppress
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text
from jsonschema.validators import validator_for

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import (
    locate_proposal, native_frame_from_dict, proposal_packet,
)
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view, resolve_native_sections, selected_source_views
from corpus_structure.semantic.source_frames import load_source_frame
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
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


def write_new(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value)


def frozen_cases() -> dict:
    """Local expectations are never included in any provider input."""
    result = {}
    for key, (name, digest) in FROZEN.items():
        raw = (HERE / name).read_bytes()
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
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("prepare requires a new reference-only directory")
    exported = {}
    settings = Settings()
    # No data.fact/data.membership/eval/production output reads occur in this path.
    with open_runtime_engine(settings, "ci-source-only-reference", purpose="read") as engine:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            run = conn.execute(select(table("ops.run")).where(table("ops.run").c.id == args.run_id)).mappings().one()
            release = open_release(conn, run["release_id"])
            references = selected_source_views(conn, args.run_id)
            views = {ref.id: load_source_view(conn, ref.id) for ref in references if ref.analysis_eligible}
            catalog = {identity: next(item["name"] for item in view.items if item["self_ref"] == view.ref.section_pointer) for identity, view in views.items()}
            selected = resolve_native_sections(catalog, [topic["section"] for topic in TOPICS.values()])
            for key, identity in zip(TOPICS, selected, strict=True):
                view = views[identity]
                document = conn.execute(select(table("kb.document")).where(table("kb.document").c.id == view.ref.document_id)).mappings().one()
                if document["project_id"] != run["project_id"] or document["content_hash"] != expected[key]["source_sha256"]:
                    raise ValueError("selected source does not match frozen original/project")
                if view.ref.membership != "descendants":
                    raise ValueError("reference topics require the intact descendant section view")
                frames, tasks, configs, methods = map(table, ("ops.native_source_frame", "ops.task", "ops.method_config", "ops.method"))
                header = conn.execute(
                    select(frames.c.task_id, frames.c.packet_hash)
                    .join(tasks, tasks.c.id == frames.c.task_id)
                    .join(configs, configs.c.id == tasks.c.method_config_id)
                    .join(methods, methods.c.id == configs.c.method_id)
                    .where(tasks.c.run_id == args.run_id, frames.c.source_view_id == view.ref.id)
                    .order_by((methods.c.name == "agent.opus").desc(), tasks.c.id)
                ).mappings().first()
                if header is None:
                    raise ValueError("adopted source lacks its immutable prepared native packet frame")
                frame = load_source_frame(conn, header["task_id"])
                if frame.source_view_id != view.ref.id or frame.native_product != view.ref.native_product or frame.text != view.text:
                    raise ValueError("stored source frame differs from selected native view")
                packet = proposal_packet(release, frame, guideline=run["guideline"], configuration={"reference_scope": "six-frozen-source-facts", "packet_cap_chars": 18000}, known_classes={})
                exported[key] = {
                    "frame": asdict(frame),
                    "parts": {part.name: part.text for part in packet.parts()},
                    "packet_hash": packet.hash,
                    "frame_task_id": header["task_id"],
                    "source_packet_hash": header["packet_hash"],
                    "source_case": key, "topic": TOPICS[key],
                }
            batch_schema = release.json_schema("AgentAuthoredBatch", mode="serialization")
            domain_definitions = [asdict(definition) for definition in release.definitions if definition.iri.startswith("https://corpus-structure.dev/domains/statistics/") or definition.name in {"Entity", "Statement", "MathematicalExpression", "Value"}]
            manifest = {
                "run_id": args.run_id, "release_id": release.release_id, "project_id": run["project_id"],
                "created_unix": time.time(), "scope": "partial fidelity universe: two intact sections, six frozen source facts only",
                "frozen_inputs": {key: {"name": name, "sha256": digest} for key, (name, digest) in FROZEN.items()},
                "frames": {key: {"sha256": sha256(canonical_bytes(value["frame"])).hexdigest(), "reference_packet_hash": value["packet_hash"], "source_packet_hash": value["source_packet_hash"], "frame_task_id": value["frame_task_id"], "source_view_id": value["frame"]["source_view_id"]} for key, value in exported.items()},
                "database_reads": "selected native source views/items, original document identity, run input/release only; no predictions",
            }
    write_new(output / "manifest.json", canonical_bytes(manifest))
    write_new(output / "sources.json", canonical_bytes(exported))
    write_new(output / "domain-definitions.json", canonical_bytes(domain_definitions))
    write_new(output / "response.schema.json", canonical_bytes(response_schema(batch_schema)))
    for key, value in expected.items():
        source = HERE / value["reference_image"]
        image = source.read_bytes()
        write_new(output / f"source-{key}.png", image)
    print(json.dumps(manifest, indent=2))


def provider_environment() -> dict[str, str]:
    # Credentials for the provider remain available; database/checkout context does not.
    return {key: value for key, value in os.environ.items() if not key.startswith(("CORPUS_", "PG", "DATABASE", "UV_")) and key not in {"CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "PWD", "OLDPWD", "BASH_ENV"}}


def provider_pass(directory: Path, kind: str, *, model: str, timeout: float, sources: dict, schema: dict, previous: dict | None = None) -> dict:
    command = shutil.which("claude")
    if command is None:
        raise RuntimeError("authenticated Claude CLI is required")
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    schema_text = canonical_bytes(schema).decode()
    if len(schema_text.encode()) > 100_000:
        raise ValueError("schema exceeds safe single CLI argument size; do not weaken the rich schema")
    instructions = (
        "Author an independent source-only reference for precisely the six supplied topics. "
        "Use the rendered original PDF pages for mathematical source meaning, and the complete pinned native frames for exact evidence addresses. "
        "Output the supplied rich AgentAuthoredBatch schema for each intact source unit, including locally declared entities, statements, conditions, bindings and evidence. "
        "Scope claims to the named topics, plus necessary source-stated premises/entity declarations; do not extract other facts from the larger section. "
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
        instructions += "You are fresh adjudicator C. Independently compare A and B with the original source; resolve differences from source evidence. Do not merely take their intersection. Record unresolved differences honestly in notes. "
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
        write_new(directory / f"{kind}.invocation.json", canonical_bytes({"session_id": session, "model": model, "pass_kind": kind, "prompt_digest": sha256(message).hexdigest(), "schema_digest": sha256(canonical_bytes(schema)).hexdigest(), "independent_prior_passes": [] if previous is None else list(previous), "database_credentials_forwarded": False, "tools": [], "mcp_servers": [], "timeout": timeout}))
        process = subprocess.Popen(argv, cwd=isolated, env=provider_environment(), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = process.communicate(input=message, timeout=timeout)
        except BaseException:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
            write_new(directory / f"{kind}.interrupted.stdout.json", stdout)
            write_new(directory / f"{kind}.interrupted.stderr.txt", stderr)
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


def author(args) -> None:
    frozen = frozen_cases()
    directory = args.input.resolve()
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if args.run_id != manifest["run_id"]:
        raise ValueError("explicit adopted run does not match prepared source frames")
    sources = json.loads((directory / "sources.json").read_bytes())
    schema = json.loads((directory / "response.schema.json").read_bytes())
    for key, source in sources.items():
        if sha256(canonical_bytes(source["frame"])).hexdigest() != manifest["frames"][key]["sha256"]:
            raise ValueError("prepared source frame changed")
    with open_runtime_engine(Settings(), "ci-source-reference-release", purpose="read") as engine:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            release = open_release(conn, manifest["release_id"])
    values = {}
    for kind in ("A", "B", "C"):
        values[kind] = provider_pass(directory, kind, model=args.model, timeout=args.timeout, sources=sources, schema=schema, previous=values.copy() if kind == "C" else None)
        validate_pass(release, sources, values[kind], directory, kind)
    # Only after all independent sessions finish do local frozen expected values enter comparison.
    actual = {row["id"]: row for row in values["C"]["assertions"]}
    comparisons = []
    for key, expected in frozen.items():
        for row in expected["assertions"]:
            found = actual[row["id"]]
            comparisons.append({"id": row["id"], "expected_latex": row["latex"], "authored_latex": found["latex"], "latex_exact": row["latex"] == found["latex"], "expected_conditions": row.get("conditions", []), "authored_conditions": found["conditions"], "conditions_exact": row.get("conditions", []) == found["conditions"]})
    passed = all(row["latex_exact"] and row["conditions_exact"] for row in comparisons)
    result = {"outcome": "passed" if passed else "failed", "scope": manifest["scope"], "comparison": "exact frozen lexical values/conditions; no tuning or provider retry", "comparisons": comparisons, "registration": "not_run; root registers retained batches after completed extraction through evaluate.semantic.record_pass"}
    write_new(directory / "frozen-comparison.json", canonical_bytes(result))
    print(json.dumps(result, indent=2))
    if not passed:
        raise SystemExit(2)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepared = commands.add_parser("prepare")
    prepared.add_argument("--run-id", type=int, required=True)
    prepared.add_argument("--output", type=Path, required=True)
    authored = commands.add_parser("author")
    authored.add_argument("--run-id", type=int, required=True)
    authored.add_argument("--input", type=Path, required=True)
    authored.add_argument("--model", required=True)
    authored.add_argument("--timeout", type=float, default=900)
    args = parser.parse_args()
    if args.run_id < 1:
        raise ValueError("a concrete adopted run ID is required")
    (prepare if args.command == "prepare" else author)(args)

if __name__ == "__main__":
    main()
