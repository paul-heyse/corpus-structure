"""Finite effect capabilities of the current owned implementations.

These supported profiles are independent of candidate declarations. Changing a required
profile needs a corresponding implementation change and independent behavioral examples.
They are compatibility requirements, never evidence that hashing code proves its effects.
"""

SUPPORTED_EFFECTS = {
    "read_source_contributions": {
        "effects": (),
        "implementation": "read_source_contributions",
        "transitions": {},
        "version": "1",
    },
    "read_source_records": {
        "effects": (),
        "implementation": "read_source_records",
        "transitions": {},
        "version": "1",
    },
    "reference_operation_set": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_operation_set",
        "transitions": {},
        "version": "1",
    },
    "reference_operation_pass": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_operation_pass",
        "transitions": {},
        "version": "1",
    },
    "reference_operation_grade": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_operation_grade",
        "transitions": {},
        "version": "1",
    },
    "reference_operation_fit": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_operation_fit",
        "transitions": {},
        "version": "1",
    },
    "reference_record_set": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_record_set",
        "transitions": {},
        "version": "1",
    },
    "reference_record_pass": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_record_pass",
        "transitions": {},
        "version": "1",
    },
    "reference_record_grade": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_record_grade",
        "transitions": {},
        "version": "1",
    },
    "reference_record_partition": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_record_partition",
        "transitions": {},
        "version": "1",
    },
    "reference_record_calibrate": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_record_calibrate",
        "transitions": {},
        "version": "1",
    },
    "reference_record_fit": {
        "effects": (),
        "implementation": "reference_record_fit",
        "transitions": {},
        "version": "1",
    },
    "record_direction": {
        "effects": ("atomic_protected_insert",),
        "implementation": "record_direction",
        "transitions": {},
        "version": "1",
    },
    "begin_pdf_build": {
        "effects": ("atomic_private_pdf_stage",),
        "implementation": "begin_pdf_build",
        "transitions": {},
        "version": "1",
    },
    "adopt_pdf_batch": {
        "effects": ("atomic_private_pdf_stage",),
        "implementation": "adopt_pdf_batch",
        "transitions": {},
        "version": "1",
    },
    "inspect_pdf_progress": {
        "effects": (),
        "implementation": "inspect_pdf_progress",
        "transitions": {},
        "version": "1",
    },
    "resume_pdf_build": {
        "effects": ("atomic_private_pdf_stage",),
        "implementation": "resume_pdf_build",
        "transitions": {},
        "version": "1",
    },
    "abandon_pdf_build": {
        "effects": ("atomic_private_pdf_stage",),
        "implementation": "abandon_pdf_build",
        "transitions": {"pdf_private_abandon": ("atomic_private_pdf_stage",)},
        "version": "1",
    },
    "enrich_pdf_math": {
        "effects": (),
        "implementation": "enrich_pdf_math",
        "transitions": {},
        "version": "1",
    },
    "convert_pdf": {
        "effects": (),
        "implementation": "convert_pdf",
        "transitions": {},
        "version": "1",
    },
    "organize_pdf": {
        "effects": (),
        "implementation": "organize_pdf",
        "transitions": {},
        "version": "1",
    },
    "project_pdf_source": {
        "effects": (),
        "implementation": "project_pdf_source",
        "transitions": {},
        "version": "1",
    },
    "publish_source_view": {
        "effects": ("atomic_native_publication",),
        "implementation": "publish_source_view",
        "transitions": {},
        "version": "1",
    },
    "read_source_view": {
        "effects": (),
        "implementation": "read_source_view",
        "transitions": {},
        "version": "1",
    },
    "read_native_source": {
        "effects": (),
        "implementation": "read_native_source",
        "transitions": {},
        "version": "1",
    },
    "capture_native_source_frame": {
        "effects": ("atomic_native_publication",),
        "implementation": "capture_native_source_frame",
        "transitions": {},
        "version": "1",
    },
    "request_native_source": {
        "effects": ("atomic_native_publication",),
        "implementation": "request_native_source",
        "transitions": {},
        "version": "1",
    },
    "publish_pdf_region_artifact": {
        "effects": ("atomic_native_publication",),
        "implementation": "publish_pdf_region_artifact",
        "transitions": {},
        "version": "1",
    },
    "prepare_native_document": {
        "effects": (),
        "implementation": "prepare_native_document",
        "transitions": {},
        "version": "1",
    },
    "retain_pdf_original": {
        "effects": ("atomic_native_publication", "preserve_original_normalized_distinction"),
        "implementation": "retain_pdf_original",
        "transitions": {},
        "version": "1",
    },
    "prepare_parsing_text": {
        "effects": (),
        "implementation": "prepare_parsing_text",
        "transitions": {},
        "version": "1",
    },
    "interpret_parsing_math": {
        "effects": (),
        "implementation": "interpret_parsing_math",
        "transitions": {},
        "version": "1",
    },
    "assess_parsing_math": {
        "effects": (),
        "implementation": "assess_parsing_math",
        "transitions": {},
        "version": "1",
    },
    "activate": {
        "effects": ("atomic_parent_generation_cas",),
        "implementation": "activate",
        "transitions": {},
        "version": "1",
    },
    "admit": {
        "effects": (),
        "implementation": "native_admission",
        "transitions": {},
        "version": "1",
    },
    "archive": {
        "effects": ("persist_exact_archive",),
        "implementation": "archive",
        "transitions": {},
        "version": "1",
    },
    "assemble": {
        "effects": ("private_canonical_assembly",),
        "implementation": "assemble",
        "transitions": {},
        "version": "1",
    },
    "bind_report": {
        "effects": (),
        "implementation": "bind_report",
        "transitions": {},
        "version": "2",
    },
    "capture_analytics": {
        "effects": ("materialize_same_snapshot_before_source_close",),
        "implementation": "capture",
        "transitions": {},
        "version": "1",
    },
    "capture_cut": {
        "effects": ("final_cut_seals_source_atomically", "immutable_cut"),
        "implementation": "cut",
        "transitions": {"run_final_cut": ("capture_final_cut", "seal_source_production")},
        "version": "1",
    },
    "check_submission": {
        "effects": (),
        "implementation": "submission",
        "transitions": {"submission_clean": (), "submission_resubmit": ()},
        "version": "1",
    },
    "claim": {
        "effects": ("atomic_attempt_holder_deadline_change",),
        "implementation": "claim",
        "transitions": {
            "task_claim": (),
            "task_claim_held": (),
            "task_reclaim": (),
            "task_reclaim_held": (),
        },
        "version": "2",
    },
    "close_analysis": {
        "effects": ("attempt_every_owned_teardown", "preserve_failure_and_cancellation"),
        "implementation": "analysis_close",
        "transitions": {
            "analysis_close_candidate": (
                "invalidate_borrowed_handles",
                "preserve_independently_detached_values",
                "release_owned_resources",
            ),
            "analysis_close_captured": (
                "invalidate_borrowed_handles",
                "preserve_independently_detached_values",
                "release_owned_resources",
            ),
        },
        "version": "1",
    },
    "compile_projection": {
        "effects": (),
        "implementation": "projection",
        "transitions": {},
        "version": "1",
    },
    "complete": {
        "effects": ("atomic_terminal_result_and_reports",),
        "implementation": "complete",
        "transitions": {"task_complete": (), "task_complete_held": ()},
        "version": "2",
    },
    "complete_unit": {
        "effects": ("persist_typed_source_and_measurement_reports",),
        "implementation": "complete_unit",
        "transitions": {},
        "version": "2",
    },
    "configure_method": {
        "effects": ("freeze_method_configuration",),
        "implementation": "method",
        "transitions": {},
        "version": "1",
    },
    "construct_project": {
        "effects": ("initialize_project_and_empty_writable_realization",),
        "implementation": "project",
        "transitions": {},
        "version": "1",
    },
    "derive": {
        "effects": ("private_finite_positive_proof",),
        "implementation": "derive",
        "transitions": {},
        "version": "1",
    },
    "end_run": {
        "effects": ("coordinated_run_and_task_terminalization", "retain_held_diagnostics"),
        "implementation": "end_run",
        "transitions": {
            "run_fail_open": (),
            "run_fail_sealed": (),
            "task_cancel": (),
            "task_cancel_held": (),
        },
        "version": "1",
    },
    "evaluate": {
        "effects": ("atomic_source_proof_result_publication", "private_compute"),
        "implementation": "evaluate",
        "transitions": {
            "realization_complete": (),
            "result_publish": (),
            "run_finish": ("publish_receipts_and_completed_result_atomically",),
        },
        "version": "1",
    },
    "execute_source": {
        "effects": ("source_execution",),
        "implementation": "source_execution",
        "transitions": {"run_start_source": ()},
        "version": "1",
    },
    "explain": {"effects": (), "implementation": "explain", "transitions": {}, "version": "1"},
    "graph_project": {
        "effects": (),
        "implementation": "graph_project",
        "transitions": {},
        "version": "1",
    },
    "graph_validate": {
        "effects": (),
        "implementation": "graph_validate",
        "transitions": {},
        "version": "1",
    },
    "hold_submission": {
        "effects": ("durable_checked_progress", "renew_deadline"),
        "implementation": "hold",
        "transitions": {"submission_hold": (), "task_hold": ()},
        "version": "2",
    },
    "make_packet": {"effects": (), "implementation": "packet", "transitions": {}, "version": "1"},
    "open_analysis": {
        "effects": ("own_engine_readers_registrations_scratch",),
        "implementation": "analysis",
        "transitions": {},
        "version": "1",
    },
    "open_read": {"effects": (), "implementation": "read", "transitions": {}, "version": "1"},
    "prepare": {"effects": (), "implementation": "prepare", "transitions": {}, "version": "1"},
    "publish": {
        "effects": ("atomic_native_publication", "monotone_revision"),
        "implementation": "publish",
        "transitions": {},
        "version": "1",
    },
    "publish_arrow": {
        "effects": ("protected_copy_same_transaction",),
        "implementation": "publish_arrow",
        "transitions": {},
        "version": "1",
    },
    "publish_inference": {
        "effects": ("protected_proof_publication",),
        "implementation": "publish_inference",
        "transitions": {},
        "version": "1",
    },
    "query": {"effects": (), "implementation": "query", "transitions": {}, "version": "1"},
    "read_original": {
        "effects": (),
        "implementation": "read_original",
        "transitions": {},
        "version": "1",
    },
    "reference_grade": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_grade",
        "transitions": {
            "reference_grade_record_commit": (
                "atomic_protected_insert",
                "preserve_exact_authored_and_context_bytes",
            )
        },
        "version": "1",
    },
    "reference_items": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_items",
        "transitions": {},
        "version": "1",
    },
    "reference_pass": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_pass",
        "transitions": {
            "reference_pass_record_commit": (
                "atomic_protected_insert",
                "preserve_exact_authored_and_context_bytes",
            )
        },
        "version": "1",
    },
    "reference_set": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_set",
        "transitions": {},
        "version": "1",
    },
    "reference_split": {
        "effects": ("protected_independent_reference_operation",),
        "implementation": "reference_split",
        "transitions": {},
        "version": "1",
    },
    "register_document": {
        "effects": ("preserve_original_bytes",),
        "implementation": "register_document",
        "transitions": {},
        "version": "1",
    },
    "release_claim": {
        "effects": ("release_current_attempt_preserving_held_progress",),
        "implementation": "release_claim",
        "transitions": {
            "task_release_claim": ("release_current_attempt_preserving_held_progress",),
            "task_release_claim_held": ("release_current_attempt_preserving_held_progress",),
        },
        "version": "1",
    },
    "reload": {"effects": (), "implementation": "reload", "transitions": {}, "version": "1"},
    "renew_claim": {
        "effects": ("renew_current_attempt_deadline",),
        "implementation": "renew_claim",
        "transitions": {
            "task_renew_claim": ("renew_current_attempt_deadline",),
            "task_renew_claim_held": ("renew_current_attempt_deadline",),
        },
        "version": "1",
    },
    "resolve_identity": {
        "effects": ("preserve_identity_exclusions",),
        "implementation": "resolve_identity",
        "transitions": {},
        "version": "2",
    },
    "schedule": {
        "effects": ("schedule_pending_or_reused_or_skipped",),
        "implementation": "schedule",
        "transitions": {},
        "version": "1",
    },
    "scientific_policy": {
        "effects": (),
        "implementation": "scientific_policy",
        "transitions": {},
        "version": "1",
    },
    "select_result": {
        "effects": ("generation_cas_select_completed_output",),
        "implementation": "select_result",
        "transitions": {},
        "version": "1",
    },
    "start_run": {
        "effects": ("construct_new_run",),
        "implementation": "start_run",
        "transitions": {},
        "version": "1",
    },
    "validate_continuation": {
        "effects": (),
        "implementation": "validate_continuation",
        "transitions": {},
        "version": "1",
    },
}

SUPPORTED_EFFECT_VERSIONS = {
    "atomic_attempt_holder_deadline_change": "1",
    "atomic_native_publication": "1",
    "atomic_parent_generation_cas": "1",
    "atomic_protected_insert": "1",
    "atomic_source_proof_result_publication": "1",
    "atomic_terminal_result_and_reports": "1",
    "attempt_every_owned_teardown": "1",
    "capture_final_cut": "1",
    "construct_new_run": "2",
    "coordinated_run_and_task_terminalization": "1",
    "durable_checked_progress": "1",
    "final_cut_seals_source_atomically": "1",
    "freeze_method_configuration": "1",
    "generation_cas_select_completed_output": "1",
    "immutable_cut": "1",
    "initialize_project_and_empty_writable_realization": "1",
    "invalidate_borrowed_handles": "1",
    "materialize_same_snapshot_before_source_close": "1",
    "monotone_revision": "1",
    "own_engine_readers_registrations_scratch": "1",
    "persist_exact_archive": "1",
    "persist_typed_source_and_measurement_reports": "1",
    "preserve_exact_authored_and_context_bytes": "1",
    "preserve_failure_and_cancellation": "1",
    "preserve_identity_exclusions": "1",
    "preserve_independently_detached_values": "1",
    "preserve_original_bytes": "1",
    "preserve_original_normalized_distinction": "1",
    "private_canonical_assembly": "1",
    "private_compute": "1",
    "private_finite_positive_proof": "1",
    "protected_copy_same_transaction": "1",
    "protected_independent_reference_operation": "1",
    "protected_proof_publication": "1",
    "publish_receipts_and_completed_result_atomically": "1",
    "release_current_attempt_preserving_held_progress": "1",
    "release_owned_resources": "1",
    "renew_current_attempt_deadline": "1",
    "renew_deadline": "1",
    "retain_held_diagnostics": "1",
    "schedule_pending_or_reused_or_skipped": "2",
    "seal_source_production": "1",
    "source_execution": "1",
}

# Companion bundles share the existing task/publication lifecycle.
SUPPORTED_EFFECTS.update(
    {
        "prepare_integrated_pdf": {
            "effects": (),
            "implementation": "prepare_integrated_pdf",
            "transitions": {},
            "version": "1",
        },
        "publish_pdf_observation": {
            "effects": ("atomic_native_publication",),
            "implementation": "publish_pdf_observation",
            "transitions": {},
            "version": "1",
        },
        "read_pdf_product": {
            "effects": (),
            "implementation": "read_pdf_product",
            "transitions": {},
            "version": "1",
        },
    }
)

# Pure PDF reconciliation consumes retained evidence and publishes no side effects.
for _operation in ("map_pdf_observation", "compare_pdf_occurrences", "select_pdf_integration"):
    SUPPORTED_EFFECTS[_operation] = {
        "effects": (),
        "implementation": _operation,
        "transitions": {},
        "version": "1",
    }

SUPPORTED_EFFECTS["recognize_pdf_observation"] = {
    "effects": ("external_model_requests", "retain_recognition_artifacts"),
    "implementation": "recognize_pdf_observation",
    "transitions": {},
    "version": "1",
}
SUPPORTED_EFFECT_VERSIONS.update(external_model_requests="1", retain_recognition_artifacts="1")

SUPPORTED_EFFECT_VERSIONS["atomic_private_pdf_stage"] = "1"

SUPPORTED_EFFECTS["stream_pdf_native"] = {
    "effects": ("owned_private_pdf_compute",),
    "implementation": "stream_pdf_native",
    "transitions": {},
    "version": "1",
}
SUPPORTED_EFFECTS["reconcile_pdf_stream"] = {
    "effects": ("owned_private_pdf_replay",),
    "implementation": "reconcile_pdf_stream",
    "transitions": {},
    "version": "1",
}
SUPPORTED_EFFECTS["stage_pdf_producer"] = {
    "effects": ("atomic_private_pdf_stage",),
    "implementation": "stage_pdf_producer",
    "transitions": {},
    "version": "1",
}
SUPPORTED_EFFECT_VERSIONS.update(owned_private_pdf_compute="1", owned_private_pdf_replay="1")

SUPPORTED_EFFECT_VERSIONS["atomic_pdf_document_publication"] = "1"

SUPPORTED_EFFECTS["freeze_pdf_build"] = {
    "effects": ("atomic_pdf_document_publication",),
    "implementation": "freeze_pdf_build",
    "transitions": {"pdf_private_freeze": ("atomic_pdf_document_publication",)},
    "version": "1",
}

SUPPORTED_EFFECTS["prepare_pdf_build"] = {
    "effects": ("atomic_pdf_document_publication",),
    "implementation": "prepare_pdf_build",
    "transitions": {},
    "version": "1",
}

SUPPORTED_EFFECTS["validate_pdf_build"] = {
    "effects": ("atomic_pdf_document_publication",),
    "implementation": "validate_pdf_build",
    "transitions": {},
    "version": "1",
}

SUPPORTED_EFFECTS["seal_pdf_build"] = {
    "effects": ("atomic_pdf_document_publication",),
    "implementation": "seal_pdf_build",
    "transitions": {"pdf_private_publish": ("atomic_pdf_document_publication",)},
    "version": "1",
}

SUPPORTED_EFFECTS["adopt_pdf_companion_batch"] = {
    "effects": ("atomic_pdf_document_publication",),
    "implementation": "adopt_pdf_companion_batch",
    "transitions": {},
    "version": "1",
}

SUPPORTED_EFFECTS["retain_pdf_stage_recipe"] = {
    "effects": ("atomic_pdf_document_publication",),
    "implementation": "retain_pdf_stage_recipe",
    "transitions": {},
    "version": "1",
}

SUPPORTED_EFFECTS["inspect_pdf_build"] = {
    "effects": (),
    "implementation": "inspect_pdf_build",
    "transitions": {},
    "version": "1",
}
