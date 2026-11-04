"""Receipt-pinned successor consumer journeys; transport/custody, not a quality oracle.

Defaults require every M1 family at accepted standing. Repeat --required-standing
candidate for a diagnostic candidate journey, or supply both standings. Missing
requirements are partial, never successful empty journeys. --validate-only is inert.
The predecessor runners and their retained outputs are immutable inputs.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import traceback
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.query import ReadLimit, read_snapshot
from corpus_structure.semantic.record_queries import RecordReadLimit, read_completed_record_projection
from corpus_structure.semantic.records import source_record_address
from corpus_structure.semantic.refusals import WrongBinding
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.record_results import RecordRequest, serve_record_results
from corpus_structure.serve.record_support import serve_record_support
from corpus_structure.settings import Settings
from run_consumers import HERE, REPO, Journey, dump, normalize

FAMILIES = ("definition", "measurement", "assertion", "table", "formula_context")
SEMANTIC_PIN = ("release_id", "realization_id", "data_revision")


def key(row):
    return row["record_id"], row["interpretation_id"]


def product_pin(pin):
    return pin["native_product_task_id"], pin["product_key"], pin["product_digest"]


def refusal_body(wire):
    """Read the registered adapter's typed error, without matching message text."""
    for block in wire.content:
        if getattr(block, "type", None) == "text":
            try:
                value = json.loads(block.text)
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict) and isinstance(value.get("code"), str):
                return value
    return {}


def load_receipt(path, run, release):
    receipt = json.loads(path.read_bytes())
    publication = receipt["publication"]
    if receipt.get("outcome", "passed") != "passed":
        raise ValueError("completed receipt has not passed")
    if receipt["source_run_id"] != run or publication["run_id"] != run:
        raise ValueError("receipt/publication run differs from --run")
    if receipt["release_id"] != release:
        raise ValueError("receipt release differs from --release")
    cut = receipt["source_cut_id"]
    if type(cut) is not int or cut <= 0 or publication["cut_id"] != cut:
        raise ValueError("receipt/publication completed cut differs")
    report = receipt["report"]
    if report["run_id"] != run or report.get("release_id", release) != release:
        raise ValueError("source report run/release differs")
    if not publication["realization_id"] or type(publication["data_revision"]) is not int:
        raise ValueError("completed publication has no exact binding")
    if receipt.get("execution_scope") == "source_custody_only" or receipt.get(
        "model_execution", "actual_native_CPU"
    ) != "actual_native_CPU":
        raise ValueError("receipt does not describe an actual CPU result")
    product = receipt["native_product"]
    # Validate the exact native product locator through its owned request contract.
    NativeSourceRequest(run_id=run, **product)
    return receipt


def source_hashes():
    paths = [HERE / name for name in (
        "run_successor_consumers.py", "run_consumers.py", "complete_census.py", "inspect_custody.py"
    )]
    paths += [REPO / "python/corpus-structure/src/corpus_structure" / name for name in (
        "serve/record_results.py", "serve/record_support.py", "serve/native_source.py",
        "serve/record_export.py", "semantic/record_queries.py", "semantic/record_projection.py",
        "intervene/record_tools.py", "intervene/semantic_server.py", "cli/records.py",
    )]
    return {str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


class SuccessorJourney(Journey):
    def __init__(self, output, args, receipt):
        super().__init__(output, args.run, receipt["native_product"])
        self.args, self.receipt = args, receipt
        self.missing = []
        self.selections = []
        self.source_cache = {}
        self.census_complete = False

    def require(self, name, condition, detail=None):
        self.check(name, condition, detail)
        if not condition:
            raise ValueError(name)

    def partial(self, name, detail):
        self.missing.append(dict(name=name, detail=detail))
        self.results.append(dict(name=name, outcome="partial", detail=detail))

    def pinned(self, page):
        publication = self.receipt["publication"]
        return (
            page.run_id == self.run
            and page.cut_id == self.receipt["source_cut_id"]
            and page.binding["release_id"] == self.args.release
            and all(page.binding[name] == publication[name] for name in SEMANTIC_PIN[1:])
        )

    def cli_arguments(self, request):
        arguments = ["--limit", str(request.limit), "--page-bytes", str(request.page_bytes)]
        for field, option in (
            ("family", "--family"), ("standing", "--standing"), ("record_id", "--record"),
            ("interpretation_id", "--interpretation"), ("cursor", "--cursor"),
        ):
            value = getattr(request, field)
            if value is not None:
                arguments.extend((option, str(value)))
        return arguments

    async def compare(self, client, name, request, expected, label):
        wire, size = await self.tool(client, name, request, label)
        budget = request.page_bytes if isinstance(request, RecordRequest) else request.max_bytes
        self.check(label + "_registered_equality", not wire.is_error and wire.structured_content == expected.model_dump(mode="json"))
        self.check(label + "_whole_envelope", not wire.is_error and size <= budget,
                   dict(envelope_bytes=size, budget=budget))
        return wire, size

    async def record_refusals(self, engine, client, request, expected, label, name):
        tight = request.model_copy(update={"page_bytes": 1})
        operation = serve_record_results if name == "records" else serve_record_support
        try:
            with read_snapshot(engine) as conn:
                operation(conn, tight)
        except RecordReadLimit as error:
            dump(self.output / (label + "-small.query.json"), dict(code=type(error).__name__, message=str(error)))
            self.check(label + "_small_query_typed_refusal", True)
        else:
            self.check(label + "_small_query_typed_refusal", False)
        wire, _ = await self.tool(client, name, tight, label + "-small")
        body = refusal_body(wire)
        self.check(label + "_small_registered_typed_refusal", wire.is_error and body.get("code") == "RecordReadLimit", body)

        # Semantic-body admission and complete SDK-envelope admission are separate.
        body_size = len(expected.model_dump_json().encode())
        wire, size = await self.tool(client, name, request, label + "-envelope-baseline")
        if wire.is_error or size <= body_size:
            self.check(label + "_envelope_baseline", False)
            return
        envelope_tight = request.model_copy(update={"page_bytes": max(body_size, size - 1)})
        with read_snapshot(engine) as conn:
            admitted = operation(conn, envelope_tight)
        self.check(label + "_semantic_body_admitted", admitted == expected)
        refused, _ = await self.tool(client, name, envelope_tight, label + "-envelope-refusal")
        body = refusal_body(refused)
        self.check(label + "_whole_envelope_typed_refusal", refused.is_error and body.get("code") == "ReadLimit" and body.get("reason") == "oversized_item", body)

    async def census(self, engine, client, projection):
        request = RecordRequest(run_id=self.run, limit=self.args.page_size)
        expected = {key(asdict(row)) for row in projection.rows["source_record"]}
        records, cursors = {}, set()
        first = None
        for ordinal in range(self.args.max_pages):
            label = f"census-{ordinal:04d}"
            with read_snapshot(engine) as conn:
                page = serve_record_results(conn, request)
            dump(self.output / (label + ".query.json"), page.model_dump(mode="json"))
            self.require(label + "_receipt_pin", self.pinned(page))
            self.require(label + "_projection_pin", page.projection_digest == projection.projection_digest)
            if first is None:
                first = page
            self.require(label + "_stable_binding", (page.binding, page.cut_id) == (first.binding, first.cut_id))
            await self.compare(client, "records", request, page, label)
            self.check(label + "_cli_equality", self.cli(label + "-cli", ["list", *self.cli_arguments(request)]) == page.model_dump(mode="json"))
            for answer in page.records:
                identity = key(answer.record)
                self.require(label + "_unique_" + str(len(records)), identity not in records)
                records[identity] = answer
            if page.next_cursor is None:
                self.census_complete = True
                self.check("census_terminal_page", page.population_paging_complete)
                break
            if ordinal == 0:
                changed = request.model_copy(update={"cursor": page.next_cursor, "family": "measurement"})
                try:
                    with read_snapshot(engine) as conn:
                        serve_record_results(conn, changed)
                except WrongBinding as error:
                    dump(self.output / "changed-selection.query.json", dict(code=type(error).__name__, message=str(error)))
                    self.check("changed_selection_query_typed_refusal", True)
                else:
                    self.check("changed_selection_query_typed_refusal", False)
                refused, _ = await self.tool(client, "records", changed, "changed-selection")
                body = refusal_body(refused)
                self.check("changed_selection_registered_typed_refusal", refused.is_error and body.get("code") == "WrongBinding" and body.get("reason") == "wrong_query", body)
            self.require(label + "_cursor_progress", page.next_cursor not in cursors)
            cursors.add(page.next_cursor)
            request = request.model_copy(update={"cursor": page.next_cursor})
        if not self.census_complete:
            self.partial("census_page_bound", dict(max_pages=self.args.max_pages, records=len(records), next_cursor=request.cursor))
        actual = set(records)
        self.check("census_unique_projected_identities", actual <= expected)
        if self.census_complete:
            self.check("census_exact_projected_identities", actual == expected,
                       dict(expected=len(expected), actual=len(actual), missing=sorted(expected - actual), unexpected=sorted(actual - expected)))
        dump(self.output / "census-identities.json", sorted(actual))
        return first, records

    def support_checks(self, answer, support, label, standing):
        self.require(label + "_unique_support_record", len(support.records) == 1)
        entry = support.records[0]
        self.check(label + "_support_identity", (entry.record_id, entry.interpretation_id, entry.family, entry.admission) == (*key(answer.record), answer.record["family"], standing))
        self.check(label + "_scientific_comparison_unmodeled", support.scientific_support_opposition.availability == "unmodeled")
        fields = {field["role"]: field for field in answer.record["fields"]}
        self.check(label + "_all_field_states_preserved", len(entry.fields) == len(fields) and all(
            field.source_reading == {k: v for k, v in fields[field.role].items() if k != "alternatives"}
            and list(field.retained_alternatives) == fields[field.role].get("alternatives", [])
            for field in entry.fields
        ))
        assertions = {row["role"]: row["fact_id"] for row in answer.assertions}
        if standing == "accepted" and (not fields or set(assertions) != set(fields)):
            self.partial(label + "_missing_asserted_field_facts", dict(identity=key(answer.record), missing_roles=sorted(set(fields) - set(assertions)), unexpected_roles=sorted(set(assertions) - set(fields))))
        anchors = {row["anchor_id"]: row for row in answer.record["anchors"]}
        evidence_sets = {row["set_id"]: row for row in answer.record["evidence_sets"]}
        for field in entry.fields:
            field_label = label + "_field_" + field.role
            if standing != "accepted":
                self.check(field_label + "_not_admitted", field.fact_availability == "not_admitted" and field.asserted_field_fact is None and not field.supports and not field.evidence)
                continue
            if field.role not in assertions:
                continue
            if standing == "accepted":
                if not (field.fact_availability == "published_selected_source_reading" and field.asserted_field_fact is not None and field.supports and field.evidence):
                    self.partial(field_label + "_missing_selected_support", field.model_dump(mode="json"))
                    continue
                self.check(field_label + "_fact_identity", field.asserted_field_fact.fact_id == assertions[field.role])
                evidence = {row.evidence_id: row for row in field.evidence}
                self.check(field_label + "_support_evidence_identity", set(evidence) == {value for row in field.supports for value in row.evidence_ids})
                expected_links = {(set_id, anchor_id) for set_id in fields[field.role].get("evidence_sets", []) for anchor_id in evidence_sets[set_id]["anchors"]}
                actual_links = {(row.source.set_id, row.source.anchor_id) for row in field.evidence if row.source is not None}
                self.check(field_label + "_exact_evidence_sets_anchors", bool(expected_links) and actual_links == expected_links)
                for ordinal, row in enumerate(field.evidence):
                    custody = row.source
                    self.check(field_label + f"_custody_{ordinal}", custody is not None and
                               (custody.record_id, custody.interpretation_id, custody.role) == (*key(answer.record), field.role)
                               and custody.anchor_id in anchors
                               and custody.source_view_id == answer.record["pin"]["source_view_id"]
                               and json.loads(custody.native_address or "null") == {
                                   k: v for k, v in anchors[custody.anchor_id].items()
                                   if k in {"space", "pointer", "precision", "start", "end"}
                               })

    async def source_read(self, engine, client, request, label):
        cache_key = request.model_dump_json()
        if cache_key in self.source_cache:
            return self.source_cache[cache_key]
        with read_snapshot(engine) as conn:
            response = inspect_native_source(conn, request)
        dump(self.output / (label + ".query.json"), response.model_dump(mode="json"))
        self.check(label + "_healthy_selected_source", response.outcome == "source_ready" and response.release_id == self.args.release and response.selection == request and bool(response.rows) and response.population_complete and response.next_cursor is None)
        await self.compare(client, "inspect_source", request, response, label)
        self.check(label + "_cli_equality", self.source_cli(label + "-cli", request) == response.model_dump(mode="json"))
        tight = request.model_copy(update={"max_bytes": 1})
        try:
            with read_snapshot(engine) as conn:
                inspect_native_source(conn, tight)
        except ReadLimit as error:
            dump(self.output / (label + "-small.query.json"), dict(code=type(error).__name__, reason=error.reason, message=str(error)))
            self.check(label + "_small_query_typed_refusal", True)
        else:
            self.check(label + "_small_query_typed_refusal", False)
        refused, _ = await self.tool(client, "inspect_source", tight, label + "-small")
        body = refusal_body(refused)
        self.check(label + "_small_registered_typed_refusal", refused.is_error and body.get("code") == "ReadLimit", body)
        self.source_cache[cache_key] = response
        return response

    async def inspect_selected_sources(self, engine, client, answer, label):
        expected = {}
        for anchor in answer.record["anchors"]:
            pin = anchor["pin"]
            pointer, cell = source_record_address(anchor["pointer"])
            identity = (*product_pin(pin), pointer, cell)
            expected[identity] = anchor
        actual = {(r.task_id, r.product_key, r.content_digest, r.pointer, r.cell_index): r for r in answer.source_requests}
        self.check(label + "_exact_anchor_source_handles", set(actual) == set(expected))
        if not expected:
            self.partial(label + "_missing_source_anchors", dict(identity=key(answer.record)))
        dump(self.output / (label + "-expected-handles.json"), [dict(handle=list(identity), anchor=anchor) for identity, anchor in expected.items()])
        for ordinal, (identity, request) in enumerate(actual.items()):
            source_label = label + f"-source-{ordinal:03d}"
            try:
                self.require(source_label + "_receipt_product", request.run_id == self.run and identity[:3] == (self.product["task_id"], self.product["product_key"], self.product["content_digest"]))
                response = await self.source_read(engine, client, request, source_label)
                self.check(source_label + "_exact_pointer", len(response.rows) == 1 and response.rows[0]["pointer"] == request.pointer)
                if request.view == "cell":
                    self.check(source_label + "_exact_cell", response.rows[0]["cell_index"] == request.cell_index)
                    parent, cell = request.pointer, expected[identity]["pointer"]
                    companion = response.companion
                    self.check(source_label + "_exact_cell_parent_companion", companion is not None and {r["occurrence_id"] for r in companion["occurrences"]} == {parent, cell})
                elif response.rows[0].get("native", {}).get("label") == "formula":
                    formula_request = request.model_copy(update={"view": "formula"})
                    formula = await self.source_read(engine, client, formula_request, source_label + "-formula")
                    native = response.rows[0]["native"]
                    self.check(source_label + "_formula_original_recognized", len(formula.rows) == 1 and formula.rows[0]["original_text"] == native.get("orig") and formula.rows[0]["recognized_latex"] == native.get("text"))
                    self.check(source_label + "_formula_companion", formula.companion == response.companion)
            except (ReadLimit, RecordReadLimit) as error:
                dump(self.output / (source_label + "-refusal.json"), dict(code=type(error).__name__, reason=getattr(error, "reason", None), message=str(error)))
                self.partial(source_label + "_required_source_budget_refusal", dict(code=type(error).__name__, request=request.model_dump(mode="json")))
                refused, _ = await self.tool(client, "inspect_source", request, source_label + "-refusal")
                body = refusal_body(refused)
                self.check(source_label + "_registered_budget_refusal", refused.is_error and body.get("code") == type(error).__name__, body)

    async def selected_journeys(self, engine, client, records):
        for family in self.args.required_family:
            for standing in self.args.required_standing:
                label = family + "-" + standing
                matches = [answer for _, answer in sorted(records.items()) if answer.record["family"] == family and len(answer.admission) == 1 and answer.admission[0]["decision"] == standing]
                if not matches:
                    self.partial(label + "_required_record_absent", dict(family=family, standing=standing, census_complete=self.census_complete))
                    continue
                # Deterministic source-only choice; no labels, model execution or grading.
                answer = matches[0]
                self.selections.append(dict(family=family, standing=standing, record_id=key(answer.record)[0], interpretation_id=key(answer.record)[1]))
                request = RecordRequest(run_id=self.run, family=family, standing=standing, record_id=key(answer.record)[0], interpretation_id=key(answer.record)[1], limit=1)
                try:
                    with read_snapshot(engine) as conn:
                        detail = serve_record_results(conn, request)
                        support = serve_record_support(conn, request)
                    dump(self.output / (label + "-detail.query.json"), detail.model_dump(mode="json"))
                    dump(self.output / (label + "-support.query.json"), support.model_dump(mode="json"))
                    self.require(label + "_same_selected_record", detail.records == (answer,) and support.page == detail)
                    self.require(label + "_receipt_pin", self.pinned(detail))
                    for name, expected, command in (("records", detail, "list"), ("record_support", support, "support")):
                        await self.compare(client, name, request, expected, label + "-" + command)
                        self.check(label + "_" + command + "_cli_equality", self.cli(label + "-" + command + "-cli", [command, *self.cli_arguments(request)]) == expected.model_dump(mode="json"))
                        await self.record_refusals(engine, client, request, expected, label + "-" + command, name)
                    self.support_checks(answer, support, label, standing)
                    await self.inspect_selected_sources(engine, client, answer, label)
                except (ReadLimit, RecordReadLimit) as error:
                    self.partial(label + "_required_journey_budget_refusal", dict(code=type(error).__name__, reason=getattr(error, "reason", None), message=str(error)))
                except Exception:
                    (self.output / (label + ".failure.txt")).write_text(traceback.format_exc())
                    self.check(label + "_journey", False)
        dump(self.output / "selected-identities.json", self.selections)

    def exports(self, projection, first, identities):
        query_rows = {name: normalize([asdict(row) for row in rows]) for name, rows in projection.rows.items()}
        dump(self.output / "query-relations.json", query_rows)
        for format in ("jsonl", "parquet"):
            try:
                destination = self.output / ("export-" + format)
                exported = self.cli("cli-export-" + format, ["export", "--format", format, "--out", str(destination)])
                manifest = json.loads((destination / "manifest.json").read_bytes())
                self.check(format + "_return_manifest", exported["manifest"] == manifest)
                self.check(format + "_binding", all(manifest["binding"][name] == first.binding[name] for name in SEMANTIC_PIN))
                pin = manifest["record_projection"]
                self.check(format + "_completed_result_pin", (pin["run_id"], pin["cut_id"], pin["projection_digest"]) == (self.run, first.cut_id, first.projection_digest))
                for name, expected in query_rows.items():
                    path = destination / manifest["relations"][name]["file"]
                    if format == "jsonl":
                        actual = [json.loads(line) for line in path.read_bytes().splitlines()]
                    else:
                        import pyarrow.parquet as pq
                        actual = pq.read_table(path).to_pylist()
                    self.check(format + "_exact_relation_" + name, actual == expected, dict(rows=len(actual), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                    if name == "source_record" and self.census_complete:
                        self.check(format + "_exact_census_identities", len(actual) == len(identities) and {key(row) for row in actual} == identities)
                self.check(format + "_coverage", pin["coverage"] == normalize([asdict(row) for row in projection.coverage]))
            except Exception:
                (self.output / ("export-" + format + ".failure.txt")).write_text(traceback.format_exc())
                self.check(format + "_export", False)

    async def run_successor(self, engine):
        # One bounded full projection, then selected-root APIs; no per-record dump.
        with read_snapshot(engine) as conn:
            projection = read_completed_record_projection(conn, run_id=self.run, include_diagnostics=False)
            identity = conn.exec_driver_sql("SELECT current_user,current_database(),inet_server_port()").one()
        dump(self.output / "database-identity.json", list(identity))
        self.require("full_projection_receipt_pin", projection.release_id == self.args.release and projection.cut_id == self.receipt["source_cut_id"] and all(getattr(projection, name) == self.receipt["publication"][name] for name in SEMANTIC_PIN[1:]))
        expected_product = (self.product["task_id"], self.product["product_key"], self.product["content_digest"])
        self.require("full_projection_native_product", all(product_pin(asdict(row)) == expected_product for row in projection.rows["source_record"]))
        server = build_semantic_server(session=SemanticAgentSession(engine, self.run))
        async with Client(server) as client:
            dump(self.output / "registered-tools.json", [tool.name for tool in await client.list_tools()])
            first, records = await self.census(engine, client, projection)
            if not records:
                self.partial("empty_record_population", dict(required_families=self.args.required_family, required_standings=self.args.required_standing))
            await self.selected_journeys(engine, client, records)
        self.exports(projection, first, set(records))
        self.population = dict(records=len(records), projected_records=len(projection.rows["source_record"]), family_counts=dict(Counter(answer.record["family"] for answer in records.values())))


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--completed-receipt", type=Path, required=True)
    parser.add_argument("--output", required=True, help="New leaf directory under this evidence folder's raw/")
    parser.add_argument("--required-family", action="append", choices=FAMILIES)
    parser.add_argument("--required-standing", action="append", choices=("accepted", "candidate"))
    parser.add_argument("--page-size", type=int, default=20, choices=range(1, 101), metavar="1..100")
    parser.add_argument("--max-pages", type=int, default=1000)
    parser.add_argument("--validate-only", action="store_true", help="Validate arguments and receipt only; no output, DB, CLI, MCP or model calls")
    args = parser.parse_args()
    if args.run <= 0 or not 1 <= args.max_pages <= 10_001:
        parser.error("run must be positive and max-pages must be 1..10001")
    if Path(args.output).name != args.output or args.output in {".", "..", ""}:
        parser.error("output must be a unique leaf directory name")
    args.required_family = list(dict.fromkeys(args.required_family or FAMILIES))
    args.required_standing = list(dict.fromkeys(args.required_standing or ("accepted",)))
    return args


def main():
    args = parse_args()
    receipt = load_receipt(args.completed_receipt, args.run, args.release)
    if args.validate_only:
        print(json.dumps(dict(outcome="passed", scope="inert argument/receipt validation only", run=args.run, release=args.release, cut=receipt["source_cut_id"], native_product=receipt["native_product"], required_families=args.required_family, required_standings=args.required_standing)))
        return 0
    output = HERE / "raw" / args.output
    output.mkdir(parents=True, exist_ok=False)
    initial_hashes = source_hashes()
    dump(output / "completed-receipt.json", receipt)
    dump(output / "context.json", dict(date_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(), versions={name: importlib.metadata.version(name) for name in ("fastmcp", "mcp", "sqlalchemy", "pyarrow")}, sources=initial_hashes, completed_receipt_path=str(args.completed_receipt.resolve()), completed_receipt_sha256=hashlib.sha256(args.completed_receipt.read_bytes()).hexdigest(), run_id=args.run, release_id=args.release, required_families=args.required_family, required_standings=args.required_standing, page_size=args.page_size, max_pages=args.max_pages, scope="live read principal; actual subprocess CLI; registered in-process MCP; detached JSONL/Parquet; no external MCP host; no source-quality or policy-efficacy oracle"))
    journey = SuccessorJourney(output, args, receipt)
    try:
        with open_runtime_engine(Settings(), "m1-successor-consumers", purpose="read") as engine:
            asyncio.run(journey.run_successor(engine))
    except (ReadLimit, RecordReadLimit) as error:
        journey.partial("required_population_budget_refusal", dict(code=type(error).__name__, reason=getattr(error, "reason", None), message=str(error)))
    except Exception:
        (output / "failure.txt").write_text(traceback.format_exc())
        journey.check("journey_execution", False)
    final_hashes = source_hashes()
    dump(output / "sources-end.json", final_hashes)
    journey.check("source_files_stable", initial_hashes == final_hashes)
    failed = any(row["outcome"] == "failed" for row in journey.results)
    outcome = "failed" if failed else "partial" if journey.missing else "passed"
    summary = dict(outcome=outcome, date_utc=datetime.now(timezone.utc).isoformat(), run_id=args.run, release_id=args.release, cut_id=receipt["source_cut_id"], native_product=receipt["native_product"], census_complete=journey.census_complete, population=getattr(journey, "population", None), required_families=args.required_family, required_standings=args.required_standing, selected=journey.selections, limits=journey.missing, checks=journey.results, scientific_comparison="unmodeled", scientific_quality="not_established", external_mcp_host="not_run", scope="selected actual receipt-pinned consumer transport and native custody at required standing; no source-quality, policy-efficacy or whole-M1 qualification")
    dump(output / "summary.json", summary)
    print(json.dumps(summary))
    return 1 if failed else 2 if journey.missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
