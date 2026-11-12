# Historical receipt summary (orientation only)

Source: retained managed receipt `docs/design_review/evidence/2026-11-06_wce-completion-repair/qualification/test-receipts/ordinary-001`,
run 2026-11-07, source head `2b11a881` (dirty), full ordinary lane, `-n auto` = 16 workers, 5,070 tests.
It predates about 100 test files and the BEP work. Phase durations are differences between consecutive
`phase_start`/`logfinish` event timestamps per worker. Nothing here is a current measurement.

- Wall time first to last event: 1255 s. Sum of phase time over workers: 19043 worker-seconds.
- By phase: call 10637 s (56%), setup 6299 s (33%), teardown 2106 s (11%)
- Session start to collection finish per worker: 7.1–7.8 s on each of 16 workers.
- Per-worker busy span (first test start to last event): min 1170 s, max 1246 s.
- Setup phase per test: median 0.001 s, mean 1.24 s, p90 0.40 s, p99 33.87 s; tests with setup > 1 s: 351; > 5 s: 274.
- Teardown phase per test: median 0.001 s, mean 0.42 s, p90 0.85 s; tests with teardown > 0.2 s: 781.

## Worker-seconds by directory

| Directory | Worker-seconds | Share |
|---|---|---|
| semantic | 14715 | 77.3% |
| evaluate | 1208 | 6.3% |
| math | 938 | 4.9% |
| tests | 587 | 3.1% |
| db | 533 | 2.8% |
| orchestrate | 259 | 1.4% |
| acceptance | 255 | 1.3% |
| schema | 245 | 1.3% |
| core | 182 | 1.0% |
| (top-level) | 57 | 0.3% |
| methods | 37 | 0.2% |
| ingest | 23 | 0.1% |
| llm | 4 | 0.0% |
| intervene | 0 | 0.0% |
| fixtures | 0 | 0.0% |
| agent | 0 | 0.0% |

## Top 45 modules by total worker-seconds

| Module | Tests | Setup s | Call s | Teardown s | Total s |
|---|---|---|---|---|---|
| semantic/test_domain_operations.py | 35 | 13 | 1109 | 71 | 1193 |
| semantic/test_local_semantic_admission_native.py | 22 | 922 | 173 | 29 | 1124 |
| semantic/test_identity_exclusions_native.py | 23 | 9 | 587 | 21 | 617 |
| semantic/test_native_attributed_evidence.py | 19 | 324 | 48 | 94 | 465 |
| semantic/test_occurrence_context.py | 13 | 8 | 331 | 108 | 446 |
| semantic/test_private_records.py | 33 | 315 | 17 | 101 | 432 |
| semantic/test_contributions_native.py | 19 | 368 | 3 | 51 | 422 |
| math/test_coverage.py | 1 | 0 | 418 | 0 | 418 |
| semantic/test_contextual_enrichment_native.py | 18 | 338 | 5 | 13 | 356 |
| evaluate/test_record_references_native.py | 11 | 168 | 125 | 63 | 356 |
| semantic/test_imported_declaration_membership.py | 7 | 3 | 306 | 18 | 326 |
| semantic/test_serving.py | 7 | 127 | 164 | 12 | 303 |
| semantic/test_pdf_integrated.py | 36 | 111 | 159 | 30 | 300 |
| semantic/test_record_publication_native.py | 17 | 195 | 82 | 11 | 287 |
| evaluate/test_operation_assessment_native.py | 6 | 170 | 20 | 81 | 271 |
| semantic/test_local_admission_native.py | 8 | 206 | 46 | 13 | 265 |
| acceptance/test_regeneration.py | 7 | 38 | 199 | 17 | 255 |
| semantic/test_runtime_entrypoints.py | 11 | 3 | 235 | 15 | 254 |
| semantic/test_retained_source_reuse_native.py | 11 | 195 | 28 | 19 | 242 |
| semantic/test_operations.py | 18 | 13 | 138 | 76 | 227 |
| orchestrate/test_policy.py | 25 | 210 | 0 | 0 | 210 |
| evaluate/test_record_policy_authority_native.py | 3 | 98 | 81 | 24 | 203 |
| tests/test_native_math_methods.py | 14 | 0 | 203 | 0 | 203 |
| semantic/test_record_consumers.py | 22 | 198 | 1 | 0 | 199 |
| semantic/test_reference_evaluation.py | 7 | 2 | 186 | 10 | 198 |
| semantic/test_witnessed_applicability_native.py | 7 | 186 | 5 | 3 | 195 |
| db/test_cli_db.py | 6 | 0 | 169 | 26 | 195 |
| semantic/test_execution_projection.py | 20 | 3 | 144 | 47 | 193 |
| semantic/test_audit_closure_native.py | 7 | 3 | 183 | 7 | 192 |
| tests/test_native_run_scope.py | 14 | 181 | 7 | 0 | 188 |
| math/test_workers.py | 12 | 0 | 181 | 0 | 181 |
| semantic/test_contextual_workflow_native.py | 4 | 75 | 80 | 16 | 170 |
| db/test_lifetime_native.py | 7 | 167 | 1 | 0 | 168 |
| semantic/test_record_assertions.py | 15 | 0 | 168 | 0 | 168 |
| semantic/test_execution_release.py | 36 | 16 | 37 | 112 | 164 |
| math/test_property.py | 23 | 59 | 103 | 0 | 162 |
| semantic/test_publication.py | 25 | 13 | 67 | 76 | 157 |
| semantic/test_audit_closure_semantics.py | 32 | 0 | 156 | 0 | 156 |
| evaluate/test_record_alignment.py | 27 | 0 | 153 | 0 | 154 |
| semantic/test_evaluation_boundaries.py | 5 | 1 | 121 | 24 | 147 |
| semantic/test_trace_counterparts.py | 4 | 1 | 143 | 1 | 145 |
| math/test_scope.py | 9 | 137 | 2 | 0 | 139 |
| semantic/test_split_decisions_native.py | 8 | 2 | 127 | 9 | 138 |
| semantic/test_identity_exclusions.py | 3 | 2 | 129 | 6 | 137 |
| semantic/test_reference_counterparts.py | 3 | 1 | 125 | 6 | 131 |

## Top 30 modules by setup worker-seconds

| Module | Tests | Setup s | Setup s per test |
|---|---|---|---|
| semantic/test_local_semantic_admission_native.py | 22 | 922 | 41.9 |
| semantic/test_contributions_native.py | 19 | 368 | 19.3 |
| semantic/test_contextual_enrichment_native.py | 18 | 338 | 18.8 |
| semantic/test_native_attributed_evidence.py | 19 | 324 | 17.0 |
| semantic/test_private_records.py | 33 | 315 | 9.5 |
| orchestrate/test_policy.py | 25 | 210 | 8.4 |
| semantic/test_local_admission_native.py | 8 | 206 | 25.7 |
| semantic/test_record_consumers.py | 22 | 198 | 9.0 |
| semantic/test_retained_source_reuse_native.py | 11 | 195 | 17.8 |
| semantic/test_record_publication_native.py | 17 | 195 | 11.4 |
| semantic/test_witnessed_applicability_native.py | 7 | 186 | 26.6 |
| tests/test_native_run_scope.py | 14 | 181 | 12.9 |
| evaluate/test_operation_assessment_native.py | 6 | 170 | 28.3 |
| evaluate/test_record_references_native.py | 11 | 168 | 15.3 |
| db/test_lifetime_native.py | 7 | 167 | 23.9 |
| math/test_scope.py | 9 | 137 | 15.3 |
| semantic/test_serving.py | 7 | 127 | 18.1 |
| core/test_method.py | 14 | 113 | 8.1 |
| semantic/test_pdf_integrated.py | 36 | 111 | 3.1 |
| evaluate/test_record_policy_authority_native.py | 3 | 98 | 32.8 |
| db/test_store.py | 4 | 86 | 21.5 |
| db/test_adbc_lifetime.py | 7 | 84 | 12.0 |
| semantic/test_contextual_workflow_native.py | 4 | 75 | 18.7 |
| schema/test_rules.py | 41 | 66 | 1.6 |
| semantic/test_reference_split_authority.py | 6 | 61 | 10.2 |
| evaluate/test_operation_fitting_native.py | 1 | 61 | 60.5 |
| math/test_property.py | 23 | 59 | 2.6 |
| semantic/test_rule_literal_bindings.py | 5 | 56 | 11.2 |
| semantic/test_pdf_staging.py | 14 | 54 | 3.9 |
| semantic/test_pdf_json_publication.py | 4 | 43 | 10.8 |

## 40 longest single phases

| Seconds | Phase | Test |
|---|---|---|
| 418.0 | call | math/test_coverage.py::test_coverage_beside_s5 |
| 115.6 | call | acceptance/test_regeneration.py::test_retained_integrated_cli_lifecycle[toy-transfer] |
| 99.3 | call | schema/test_packs.py::test_hashes_are_equal_across_processes_hash_seeds_and_load_paths |
| 93.3 | call | math/test_property.py::test_generated_layer |
| 93.1 | call | db/test_cli_db.py::test_cli_subprocess_acknowledges_creation_before_failed_migration |
| 86.8 | setup | math/test_scope.py::test_held_out_and_example_standing_contexts@math_preparation |
| 83.4 | call | acceptance/test_regeneration.py::test_retained_integrated_cli_lifecycle[statistics-acceptance-native] |
| 73.1 | call | semantic/test_operation_reporting_native.py::test_alias_only_released_change_reaches_actual_cli_mcp_and_advice |
| 68.9 | call | semantic/test_runtime_entrypoints.py::test_current_cli_stdio_journey_and_settlement[tool_failure] |
| 64.0 | call | math/test_workers.py::test_real_spawn_transports_each_stage_without_preparation_or_reparsing |
| 63.9 | call | evaluate/test_record_policy_authority_native.py::test_heldout_calibration_binding_and_native_whole_reading_admission |
| 63.3 | call | semantic/test_local_semantic_admission_native.py::test_native_rejects_forged_judged_semantic_rows[unit-judged_source0-private_source0] |
| 62.5 | setup | semantic/test_local_semantic_admission_native.py::test_native_rejects_forged_judged_semantic_rows[source-judged_source0-private_source0] |
| 61.1 | setup | evaluate/test_operation_assessment_native.py::test_native_conditional_proposal_endpoint_cases_preserve_kind_and_source_scope |
| 61.0 | setup | semantic/test_local_semantic_admission_native.py::test_nonqualifying_case_preserves_private_outputs[judged_source1-private_source0] |
| 60.5 | setup | evaluate/test_operation_fitting_native.py::test_native_operation_event_fit_retains_exact_frame_and_blocks_forgery |
| 59.4 | setup | math/test_property.py::test_corpus_layer_on_the_spike_pages@math_preparation |
| 57.7 | call | semantic/test_native_documents.py::test_pdf_original_and_native_product_need_no_rendition[True] |
| 56.7 | call | semantic/test_identity_exclusion_reads.py::test_identity_exclusion_snapshot_reader_and_columnar_closure[False] |
| 53.0 | setup | semantic/test_local_semantic_admission_native.py::test_common_v3_facets_select_exact_products_and_public_assessment_only[private_source0] |
| 51.9 | call | semantic/test_domain_operations.py::test_known_input_reference_and_declared_key_converge_with_lineage[False] |
| 50.5 | setup | math/test_scope.py::test_core_standing_contexts@math_preparation |
| 50.1 | call | semantic/test_source_search.py::test_source_search_requires_no_completed_knowledge_and_mcp_returns_exact_handles |
| 49.6 | call | math/test_workers.py::test_staged_corpus_relations_preserve_direct_page_semantics@math_preparation |
| 49.6 | setup | semantic/test_local_semantic_admission_native.py::test_native_rejects_forged_judged_semantic_rows[pass-judged_source0-private_source0] |
| 48.6 | setup | semantic/test_serving.py::test_full_projection_exports_and_cancel_cleanup |
| 48.3 | call | semantic/test_serving.py::test_real_cli_query_implementation_edit_and_bound_followups |
| 48.1 | call | semantic/test_pdf_json_publication.py::test_retained_book_witness_descriptor_and_content_fit_without_relation_jsonb |
| 47.8 | call | semantic/test_domain_operations.py::test_native_scientific_comparison_preserves_facts_and_uncertainty[formulas1-different-0] |
| 47.7 | call | semantic/test_identity_exclusion_reads.py::test_identity_exclusion_snapshot_reader_and_columnar_closure[True] |
| 47.7 | call | semantic/test_imported_declaration_membership.py::test_native_imported_membership_requires_exact_bound_lineage[class] |
| 47.6 | call | semantic/test_trace_counterparts.py::test_trace_t4_keeps_log_normal_parameters_distinct_from_normal_mean |
| 47.6 | call | semantic/test_imported_declaration_membership.py::test_native_imported_membership_requires_exact_bound_lineage[establishment] |
| 47.2 | call | semantic/test_identity_exclusions.py::test_known_input_exclusions_follow_participating_endpoints |
| 47.0 | call | math/test_workers.py::test_spawned_vendored_page_returns_real_span_rows |
| 46.8 | call | semantic/test_runtime_entrypoints.py::test_current_cli_stdio_journey_and_settlement[complete] |
| 46.7 | call | semantic/test_pdf_integrated.py::test_integrated_preparation_and_native_task_fences_are_explicit |
| 46.6 | setup | semantic/test_local_semantic_admission_native.py::test_writer_cannot_obtain_heldout_admission_contents[judged_source1-private_source0] |
| 46.6 | call | semantic/test_trace_counterparts.py::test_trace_t1_current_construction_is_not_a_distribution_family |
| 46.4 | setup | semantic/test_local_semantic_admission_native.py::test_writer_cannot_read_raw_adjudication_helper[private_source0] |
