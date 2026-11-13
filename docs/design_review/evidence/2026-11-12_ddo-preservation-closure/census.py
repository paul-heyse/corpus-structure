"""DDO-00 metadata selection; never read artifact, source, answer or result bodies.

Run from the repository root with uv run python PATH/census.py. The only writes are
this folder's raw metadata inventory. This is a bounded census, not migration tooling.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ROW_BOUND = 100_000
FILE_BOUND = 100_000
METADATA_BYTES = 16_777_216

# Reviewed projections of physical.yaml. No wildcard rows, payload, content,
# authored, projection, frame, source_frame, context, result or option fields.
PROJECTIONS = {
    "data.project": "project_id active_release_id generation selected_result_run_id",
    "data.realization": "realization_id project_id release_id state data_revision",
    "sem.release": "release_id parent_release_id content_digest profile",
    "sem.release_finalization": "release_id content_digest",
    "sem.runtime_binding": "release_id runtime_id",
    "sem.artifact": "release_id artifact_name media_type content_digest",
    "sem.input": "release_id input_kind input_name content_digest",
    "sem.deployment_admission": "release_id physical_id deployment_id kind content_digest",
    "sem.sql_admission": "release_id input_kind input_name physical_id content_digest",
    "sem.physical_contract": "physical_id source_digest",
    "ops.run": (
        "id project_id release_id input_realization_id input_revision "
        "dependency_digest kind phase status code_commit result_realization_id "
        "sealed runtime_id"
    ),
    "ops.task": (
        "id run_id release_id stage unit_type unit_id unit_key method_config_id "
        "input_hash packet_hash reused_task_id status attempt result_digest "
        "invocation_key"
    ),
    "ops.task_dependency": "task_id dependency_task_id kind",
    "ops.method": "id name version family tier configuration_schema_digest",
    "ops.method_config": "id method_id name config_hash",
    "ops.completed_result": (
        "run_id release_id output_realization_id cut_id batch_id "
        "dependency_digest source_receipts proof_receipts"
    ),
    "ops.input_cut": "id run_id name final release_id source_revision",
    "ops.cut_task": "cut_id task_id origin_task_id",
    "ops.run_source_view": "run_id source_view_id supersedes_source_view_id position",
    "kb.document": "id project_id key source_uri content_hash original_path mime",
    "kb.source_artifact": "artifact_digest",
    "kb.source_view": (
        "id key document_id release_id native_task_id native_product_key "
        "native_content_digest projection_digest recipe_digest "
        "native_build_id native_revision_id analysis_eligible"
    ),
    "ops.source_build": "task_id release_id artifact_digest recipe_digest",
    "ops.pdf_product": (
        "task_id product_key content_digest kind artifact_digest release_id contract_digest"
    ),
    "ops.pdf_product_artifact": "task_id product_key artifact_digest",
    "ops.pdf_product_input": (
        "task_id product_key input_index role input_task_id input_product_key input_content_digest"
    ),
    "ops.pdf_product_body": "task_id product_key recipe_digest",
    "ops.pdf_record_document": (
        "product_id revision_id release_id source_digest "
        "mapping_profile contract_version native_schema_digest "
        "root_id"
    ),
    "ops.pdf_artifact_stream": (
        "product_id revision_id stream_id byte_length "
        "serialization_sha256 byte_root encoding_profile"
    ),
    "ops.pdf_published_revision": (
        "build_id task_id product_key logical_digest release_id source_digest "
        "schema_digest recipe_digest frozen_digest kind"
    ),
    "ops.pdf_build_validation": (
        "build_id frozen_digest logical_digest contract_digest native_callbacks "
        "native_contract_digest"
    ),
    "ops.pdf_frozen_build": "build_id frozen_digest kind",
    "ops.pdf_native_validation": "build_id frozen_digest contract_digest passed",
    "ops.pdf_visual_index": "task_id product_key artifact_digest row_count",
    "kb.pdf_relation_endpoint": (
        "task_id product_key relation_id endpoint_index role target_task_id "
        "target_product_key target_content_digest occurrence_id"
    ),
    "ops.native_region_artifact": (
        "task_id native_task_id native_product_key native_content_digest pointer "
        "region_index recipe_digest artifact_digest native_build_id "
        "native_revision_id"
    ),
    "ops.native_source_frame": (
        "task_id packet_hash unit_ref source_view_id "
        "product_task_id product_key product_digest "
        "projection_digest recipe_digest"
    ),
    "ops.native_source_frame_source": (
        "task_id unit_ref source_view_id product_task_id product_key product_digest "
        "projection_digest recipe_digest section_pointer membership role"
    ),
    "ops.characterization_product": (
        "task_id product_key content_digest kind release_id runtime_id base_task_id "
        "base_product_key base_content_digest"
    ),
    "ops.pdf_stage_build": (
        "build_id task_id run_id release_id source_digest "
        "recipe_digest schema_digest replay_key attempt state"
    ),
    "ops.pdf_stage_document": (
        "product_id revision_id release_id source_digest "
        "mapping_profile contract_version native_schema_digest "
        "root_id"
    ),
    "ops.pdf_stage_artifact_stream": (
        "product_id revision_id stream_id byte_length serialization_sha256 byte_root "
        "encoding_profile"
    ),
    "ops.pdf_stage_receipt": "build_id replay_key content_digest row_count",
    "ops.pdf_stage_recipe": (
        "task_id source_digest root_recipe_digest stage_recipe_digest release_id"
    ),
    "eval.reference_set": "id project_id release_id source_run_id split",
    "eval.reference_unit": "id set_id rendition_id source_view_id projection_digest",
    "eval.reference_pass": "id unit_id pass_kind content_digest",
    "eval.reference_frame": (
        "id pass_id version rendition_id rendition_digest parent_id "
        "source_view_id projection_digest"
    ),
    "eval.reference_item": "id pass_id frame_id item_kind",
    "eval.reference_evaluation": "id project_id run_id set_id content_digest",
    "eval.structural_reference_set": "id project_id release_id frame_digest",
    "eval.structural_reference_pass": "id set_id pass_kind content_digest",
    "eval.operation_event_fit": (
        "id project_id evaluation_id run_id cut_id release_id set_id "
        "source_frame_digest content_digest"
    ),
    "eval.review_exposure": (
        "id project_id set_id group_set_id partition purpose recipient_class exposed_at"
    ),
    "eval.split_decision": "decision_id project_id release_id digest",
    "eval.document_split": "id project_id source_uri split decision_id",
    "eval.reference_origin_group": "project_id origin_group partition",
    "eval.reference_origin_source": "project_id source_uri origin_group",
}


def file_state(path: Path) -> dict:
    """lstat only: do not open artifact bytes or follow symlink custody."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"state": "missing"}
    return {
        "state": "symlink_unresolved" if stat.S_ISLNK(info.st_mode) else "present",
        "kind": "directory" if stat.S_ISDIR(info.st_mode) else "file",
        "bytes": info.st_size,
        "mtime_ns": info.st_mtime_ns,
    }


def metadata(path: Path) -> tuple[dict | None, dict]:
    before = file_state(path)
    if before["state"] != "present" or before["bytes"] > METADATA_BYTES:
        return None, before
    data = path.read_bytes()
    after = file_state(path)
    if before != after:
        return None, {"state": "changed_during_read"}
    try:
        value = json.loads(data)
    except ValueError, UnicodeError:
        return None, {**before, "state": "unreadable_metadata"}
    if not isinstance(value, dict):
        return None, {**before, "state": "unsupported_metadata"}
    return value, {**before, "sha256": hashlib.sha256(data).hexdigest()}


def bounded_files(root: Path, filename: str):
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not Path(directory, d).is_symlink())
        if Path(directory) == HERE:
            dirs[:] = []
            continue
        if filename in files:
            count += 1
            if count > FILE_BOUND:
                raise RuntimeError("manifest file bound exceeded")
            yield Path(directory, filename)


IDENTITY_KEYS = {
    "run_id",
    "source_run_id",
    "cut_id",
    "task_id",
    "selected_task_id",
    "release_id",
    "source_release_id",
    "prediction_release_id",
    "source_view_id",
    "project_id",
    "realization_id",
    "data_revision",
    "product_id",
    "revision_id",
    "build_id",
    "product_key",
    "content_digest",
    "source_digest",
    "recipe_digest",
    "schema_digest",
    "contract_digest",
    "frame_digest",
    "set_id",
    "evaluation_id",
    "reference_set_id",
    "baseline_evaluation_id",
    "revised_evaluation_id",
    "selected_evaluation_ids",
    "selection_release_id",
    "producer_release_id",
    "capture_id",
    "resume_run",
}


def identities(value, prefix="") -> list[dict]:
    """Select identity fields inside an already identified metadata schema only.

    This does not infer graph edges from arbitrary JSON strings or open relation files.
    """
    found = []
    if isinstance(value, dict):
        for key, item in value.items():
            address = f"{prefix}.{key}" if prefix else key
            if key in IDENTITY_KEYS and isinstance(item, (str, int, list)):
                found.append({"field": address, "value": item})
            elif isinstance(item, (dict, list)):
                found.extend(identities(item, address))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(identities(item, f"{prefix}[{index}]"))
    return found


def external_census(settings: Settings) -> dict:
    managed_root = settings.ci_results or ROOT / "build/ci"
    evidence_root = ROOT / "docs/design_review/evidence"
    manifests = []
    # Only exact manifest.json metadata under declared local roots. Model/provider
    # caches are excluded: their own payload formats are not review/managed metadata.
    for scan_root in (ROOT / "build", evidence_root):
        for path in bounded_files(scan_root, "manifest.json"):
            if any(part in {"models", ".venv", "node_modules"} for part in path.parts):
                continue
            value, state = metadata(path)
            item = {"path": str(path.relative_to(ROOT)), "metadata": state}
            if value is None:
                item["classification"] = "sealed_pending_consumer"
            elif {"id", "action", "artifacts"} <= value.keys() and isinstance(
                value["artifacts"], dict
            ):
                item.update(
                    kind="managed" if path.parent.parent == managed_root else "archived_managed",
                    id=value["id"],
                    action=value["action"],
                    outcome=value.get("outcome"),
                    stage=value.get("stage"),
                    settled=value.get("settled"),
                    holds=value.get("holds", []),
                )
                account = value.get("operation_account") or {}
                item["custody"] = {
                    "cleanup": account.get("cleanup"),
                    "custody_unsettled": (value.get("details") or {}).get("custody_unsettled"),
                    "acquired_target": account.get("acquired_target"),
                    "predecessor": account.get("predecessor"),
                    "reached_revision": account.get("reached_revision"),
                }
                item["references"] = identities(value.get("scope", {})) + identities(account)
                item["references"].extend(
                    {"field": "details." + key, "value": item_value}
                    for key, item_value in (value.get("details") or {}).items()
                    if key in IDENTITY_KEYS and isinstance(item_value, (str, int))
                )
                item["artifacts"] = [
                    {"role": role, "path": member, **file_state(path.parent / member)}
                    for role, member in value["artifacts"].items()
                ]
                item["classification"] = "preserve_sealed"
                item["consumer"] = (
                    "ci results inspection/delivery/recovery; declared holds; retained "
                    "failure account"
                )
            elif str(value.get("format", "")).startswith("progressive-review-bundle-"):
                item.update(
                    kind="review",
                    format=value["format"],
                    selection_digest=value.get("selection_digest"),
                    completeness=value.get("completeness"),
                    references=identities(value.get("selection", {})),
                    classification="preserve_sealed",
                    consumer=(
                        "detached review inspection/replay under original format and"
                        " archived contract"
                    ),
                )
                item["artifacts"] = []
                for relation, spec in value.get("relations", {}).items():
                    for encoding, member in spec.get("files", {}).items():
                        if isinstance(member, dict) and isinstance(member.get("path"), str):
                            item["artifacts"].append(
                                {
                                    "relation": relation,
                                    "encoding": encoding,
                                    "path": member["path"],
                                    "sha256": member.get("sha256"),
                                    "declared_bytes": member.get("bytes"),
                                    **file_state(path.parent / member["path"]),
                                }
                            )
            elif value.get("format") in {
                "semantic-export-1",
                "semantic-export-2",
                "semantic-export-4",
                "pdf-companion-export-v2",
                "enriched-document-review-v1",
            }:
                item.update(
                    kind="export",
                    format=value["format"],
                    logical_digest=value.get("logical_digest"),
                    classification="preserve_sealed",
                    consumer=(
                        "serve.export/companion_export and detached "
                        "enriched-document review under original format"
                    ),
                    references=[],
                    artifacts=[],
                )
                for key in ("binding", "pin", "selection", "layers"):
                    item["references"].extend(identities(value.get(key, {}), key))
                for key in ("producer_release_id",):
                    if key in value:
                        item["references"].append({"field": key, "value": value[key]})
                for table_key in ("relations", "families", "files"):
                    for name, member in value.get(table_key, {}).items():
                        member_path = (
                            member.get("file", member.get("path"))
                            if isinstance(member, dict)
                            else None
                        )
                        if isinstance(member_path, str):
                            item["artifacts"].append(
                                {
                                    "relation": name,
                                    "path": member_path,
                                    "sha256": member.get("sha256"),
                                    **file_state(path.parent / member_path),
                                }
                            )
            else:
                item.update(
                    kind="other_manifest",
                    classification="sealed_pending_consumer",
                    format=value.get("format") if isinstance(value.get("format"), str) else None,
                    references=[
                        {"field": key, "value": value[key]}
                        for key in IDENTITY_KEYS
                        if key in value and isinstance(value[key], (str, int))
                    ],
                    consumer=(
                        "enclosing retained evidence record if referenced; otherwise unresolved"
                    ),
                )
            if "/tmp/pytest/" in item["path"]:
                item.update(
                    classification="disposable_generated_fixture",
                    consumer=(
                        "pytest temporary fixture; regenerate through named test directory in path"
                    ),
                    database_match=(
                        "synthetic test target; do not infer current database membership from numeric"
                        " IDs"
                    ),
                )
            manifests.append(item)
    if not managed_root.is_relative_to(ROOT / "build"):
        # An explicit alternate store must be included, never silently ignored.
        raise RuntimeError(
            "configured alternate managed store requires explicit scan-root amendment"
        )
    records = []
    for path in sorted(evidence_root.glob("*/records/*.json")):
        if HERE in path.parents:
            continue
        value, state = metadata(path)
        entry = {
            "path": str(path.relative_to(ROOT)),
            "metadata": state,
            "classification": "preserve_sealed",
            "consumer": "retained evidence record and cited package",
        }
        if value is not None:
            entry.update(
                {
                    key: value.get(key)
                    for key in (
                        "id",
                        "package",
                        "status",
                        "outcome",
                        "consumed_by",
                        "depends_on",
                        "supersedes",
                        "superseded_by",
                    )
                }
            )
            entry["files"] = [
                {
                    "direction": direction,
                    "path": member["path"],
                    "sha256": member.get("sha256"),
                    **file_state(path.parents[1] / member["path"]),
                }
                for direction in ("inputs", "outputs")
                for member in value.get(direction, [])
            ]
        records.append(entry)
    return {
        "scan_roots": [str(ROOT / "build"), str(evidence_root)],
        "configured_managed_root": str(managed_root),
        "manifests": manifests,
        "evidence_records": records,
        "limits": (
            "Per-file stable metadata read; no cross-filesystem snapshot. No "
            "artifact-byte integrity verification. No arbitrary JSON/reference "
            "crawl. Unrecorded outside deliveries cannot be enumerated from these "
            "owners."
        ),
    }


def summarize(result: dict) -> dict:
    relations = result["relations"]
    manifests = result["external"]["manifests"]
    run_ids = {row["id"] for row in relations["ops.run"]}
    completed_ids = {row["run_id"] for row in relations["ops.completed_result"]}
    releases = {row["release_id"] for row in relations["sem.release"]}
    source_views = {row["id"] for row in relations["kb.source_view"]}
    task_ids = {row["id"] for row in relations["ops.task"]}
    matched = []
    external = []
    for manifest in manifests:
        if manifest["classification"] == "disposable_generated_fixture":
            continue
        for ref in manifest.get("references", []):
            field, value = ref["field"].rsplit(".", 1)[-1], ref["value"]
            population = (
                {
                    "run_id": run_ids,
                    "source_run_id": run_ids,
                    "resume_run": run_ids,
                    "release_id": releases,
                    "source_release_id": releases,
                    "prediction_release_id": releases,
                    "producer_release_id": releases,
                    "selection_release_id": releases,
                    "source_view_id": source_views,
                    "task_id": task_ids,
                    "selected_task_id": task_ids,
                }
            ).get(field)
            if population is not None and isinstance(value, (str, int)):
                entry = {"manifest": manifest["path"], **ref}
                (matched if value in population else external).append(entry)
    missing = [
        {"manifest": item["path"], "classification": item["classification"], **member}
        for item in manifests
        for member in item.get("artifacts", [])
        if member["state"] != "present"
    ]
    recovery = []
    for row in relations["ops.run"]:
        if row["id"] in completed_ids:
            continue
        consumers = [
            item["path"]
            for item in manifests
            if item.get("action") in {"run.resume", "regenerate", "run.characterize"}
            and item["classification"] != "disposable_generated_fixture"
            and any(
                ref["field"] == "details.run_id" and ref["value"] == row["id"]
                for ref in item.get("references", [])
            )
        ]
        recovery.append(
            {
                "run_id": row["id"],
                "release_id": row["release_id"],
                "status": row["status"],
                "runtime_id": row["runtime_id"],
                "classification": "preserve_sealed" if consumers else "sealed_pending_consumer",
                "recovery_consumer_manifests": consumers,
            }
        )
    policies = [
        {
            "roots": (
                "kb.document; kb.source_artifact; ops.source_build; kb.source_view; "
                "native published build/record/stream metadata"
            ),
            "classification": "preserve_original_custody_and_sealed_interpretation",
            "consumer": (
                "semantic.source_views.load_source_view; serve.review_bundle "
                "original source/proof and detached replay; protected unit/frame "
                "source bindings"
            ),
            "action": (
                "Preserve all selected IDs/digests and original "
                "native/source/recipe/schema/contract releases, including mixed "
                "original/derived artifact pool; no in-place re-key or "
                "regeneration."
            ),
        },
        {
            "roots": (
                "eval.reference_*; eval.structural_reference_*; "
                "eval.operation_event_fit; review_exposure; split/origin metadata"
            ),
            "classification": "preserve_protected_sealed",
            "consumer": (
                "evaluate.reference/report comparison, archived immutable "
                "assessments and source-only/protected review custody"
            ),
            "action": (
                "Preserve questions/answers unmodified within their existing "
                "database interpretation; this census reads only identity/frame "
                "digests and links. Future changed addresses require reviewed "
                "correspondence."
            ),
        },
        {
            "roots": (
                "all ops.completed_result rows and "
                "input_cut/cut_task/source/runtime/release closure"
            ),
            "classification": "preserve_sealed",
            "consumer": (
                "retained completion receipts; ci/native/serve readers; review "
                "bundle selected run/cut/task; independent retained evidence"
            ),
            "action": (
                "Preserve exact completion metadata/receipts, archived "
                "sem.input/artifact/runtime interpretation and original "
                "task/product dependencies. No selected correspondence or "
                "disposable production completion."
            ),
        },
        {
            "roots": "incomplete run and open/frozen stage workspaces",
            "classification": "preserve_sealed_or_sealed_pending_consumer",
            "consumer": (
                "exact manifested resume/characterize/regenerate references "
                "listed per run; unknown recovery intent remains unresolved"
            ),
            "action": (
                "Quarantine unknown recovery intent; no inferred recovery consumer and no disposal."
            ),
        },
        {
            "roots": "external.manifests and external.evidence_records",
            "classification": "per_manifest_or_preserve_sealed_evidence",
            "consumer": (
                "owning record package/consumed_by, managed result "
                "inspection/recovery or detached format reader, retained failure "
                "evidence"
            ),
            "action": (
                "Preserve metadata and referenced member directories/files in "
                "original format. Generated pytest temporary fixtures alone are "
                "disposable through their concrete test consumer."
            ),
        },
    ]
    digests = {row["artifact_digest"] for row in relations["kb.source_artifact"]}
    artifact_links = [
        (relation, row, column)
        for relation, columns in {
            "ops.source_build": ("artifact_digest", "recipe_digest"),
            "ops.pdf_product": ("artifact_digest",),
            "ops.pdf_product_artifact": ("artifact_digest",),
            "ops.pdf_visual_index": ("artifact_digest",),
            "ops.native_region_artifact": ("artifact_digest", "recipe_digest"),
        }.items()
        for row in relations[relation]
        for column in columns
    ]
    product_keys = {
        (row["task_id"], row["product_key"], row["content_digest"])
        for row in relations["ops.pdf_product"]
    }
    product_links = [
        (
            "kb.source_view",
            row["id"],
            (row["native_task_id"], row["native_product_key"], row["native_content_digest"]),
        )
        for row in relations["kb.source_view"]
    ]
    product_links.extend(
        (
            "ops.pdf_product_input",
            (row["task_id"], row["product_key"], row["input_index"]),
            (row["input_task_id"], row["input_product_key"], row["input_content_digest"]),
        )
        for row in relations["ops.pdf_product_input"]
    )
    return {
        "observed_at": result["observed_at"],
        "target": result["target"],
        "revision": result["revision"],
        "counts": result["counts"],
        "foreign_keys": len(result["foreign_keys"]),
        "external_counts": result["external_counts"],
        "evidence_records": len(result["external"]["evidence_records"]),
        "policies": policies,
        "manifest_classifications": dict(Counter(item["classification"] for item in manifests)),
        "document_original_path_states": [
            {
                "document_id": row["id"],
                "content_hash": row["content_hash"],
                "original_path": row["original_path"],
                **file_state(ROOT / row["original_path"]),
            }
            for row in relations["kb.document"]
            if row["original_path"]
        ],
        "completed_run_ids": sorted(completed_ids),
        "protected_set_ids": [row["id"] for row in relations["eval.reference_set"]],
        "incomplete_runs": recovery,
        "unpublished_stage_builds": [
            row for row in relations["ops.pdf_stage_build"] if row["state"] != "published"
        ],
        "candidate_current_database_identity_matches": matched,
        "external_or_historical_identity_references": external,
        "identity_matching_limits": (
            "An ID match alone does not prove target/contract identity. Detached "
            "historical bundles remain sealed under their own digest and interpretation; "
            "unmatched historical IDs do not authorize restoration guesses."
        ),
        "missing_or_symlink_artifacts": missing,
        "missing_evidence_files": [
            {"record": item["path"], **member}
            for item in result["external"]["evidence_records"]
            for member in item.get("files", [])
            if member["state"] != "present"
        ],
        "artifact_link_checks": {
            "examined": len(artifact_links),
            "missing": [
                {
                    "relation": relation,
                    "identity": {key: row[key] for key in ("task_id", "product_key") if key in row},
                    "column": column,
                    "digest": row[column],
                }
                for relation, row, column in artifact_links
                if row[column] not in digests
            ],
        },
        "source_and_input_product_link_checks": {
            "examined": len(product_links),
            "missing": [
                {"relation": relation, "identity": identity, "product": product}
                for relation, identity, product in product_links
                if product not in product_keys
            ],
        },
        "protected_unsettled_result": [
            item for item in manifests if item.get("id") == "0a78c71ce1a949e38e906c9c5392c1f3"
        ],
        "correspondence_selections": [],
        "production_disposable_selections": [],
        "closure": (
            "metadata selection and conservative classification only; destructive "
            "adoption/recovery proof remains open"
        ),
    }


def run() -> None:
    settings = Settings()
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "statement_timeout_seconds": 15,
        "row_bound_per_relation": ROW_BOUND,
        "projections": PROJECTIONS,
        "relations": {},
    }
    with open_runtime_engine(settings, purpose="maintenance") as engine, engine.connect() as conn:
        conn.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        conn.execute(text("SET LOCAL statement_timeout = '15s'"))
        result["target"] = dict(
            conn.execute(
                text(
                    (
                        "SELECT current_database() AS database, current_user AS principal, "
                        "current_setting('server_version') AS version, "
                        "current_setting('port') AS port, transaction_timestamp() AS "
                        "transaction_time, pg_current_snapshot()::text AS snapshot, (SELECT "
                        "oid FROM pg_database WHERE datname=current_database()) AS "
                        "database_oid, (SELECT system_identifier::text FROM "
                        "pg_control_system()) AS system_identifier"
                    )
                )
            )
            .mappings()
            .one()
        )
        if (
            result["target"]["database"] != "corpus_structure_dev"
            or result["target"]["port"] != "5434"
        ):
            raise RuntimeError("unexpected acquired target")
        result["revision"] = list(
            conn.execute(
                text("SELECT version_num FROM public.semantic_alembic_version ORDER BY version_num")
            ).scalars()
        )
        result["foreign_keys"] = [
            dict(row)
            for row in conn.execute(
                text(
                    (
                        "SELECT n.nspname AS source_schema,c.relname AS "
                        "source_table,t.conname AS constraint_name,tn.nspname AS "
                        "target_schema,tc.relname AS target_table,pg_get_constraintdef(t.oid)"
                        " AS definition FROM pg_constraint t JOIN pg_class c ON "
                        "c.oid=t.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace JOIN "
                        "pg_class tc ON tc.oid=t.confrelid JOIN pg_namespace tn ON "
                        "tn.oid=tc.relnamespace WHERE t.contype='f' AND n.nspname IN "
                        "('data','sem','ops','kb','eval') ORDER BY 1,2,3 LIMIT 2001"
                    )
                )
            ).mappings()
        ]
        if len(result["foreign_keys"]) > 2000:
            raise RuntimeError("foreign key bound exceeded")
        for relation, columns in PROJECTIONS.items():
            selected = ",".join(columns.split())
            # The relation/column names are fixed reviewed literals above, not user input.
            ordering = columns.split()[0]
            rows = [
                dict(row)
                for row in conn.execute(
                    text(
                        f"SELECT {selected} FROM {relation} ORDER BY {ordering} LIMIT {ROW_BOUND + 1}"
                    )
                ).mappings()
            ]
            if len(rows) > ROW_BOUND:
                raise RuntimeError(f"row bound exceeded: {relation}")
            result["relations"][relation] = rows
        conn.rollback()
    result["external"] = external_census(settings)
    result["counts"] = {name: len(rows) for name, rows in result["relations"].items()}
    result["external_counts"] = dict(
        Counter(item.get("kind", "unreadable") for item in result["external"]["manifests"])
    )
    # Compact raw JSON keeps this all-identity census materially smaller; named
    # projections and summary.json supply its bounded reader-facing views.
    (HERE / "raw/inventory.json").write_text(
        json.dumps(result, separators=(",", ":"), default=str) + "\n"
    )
    (HERE / "raw/summary.json").write_text(
        json.dumps(summarize(result), indent=2, default=str) + "\n"
    )
    print(
        json.dumps(
            {
                "database": result["target"],
                "revision": result["revision"],
                "counts": result["counts"],
                "foreign_keys": len(result["foreign_keys"]),
                "external_counts": result["external_counts"],
                "evidence_records": len(result["external"]["evidence_records"]),
            },
            default=str,
        )
    )


if __name__ == "__main__":
    run()
