# Tests and fixtures that pin changing shapes

**Inspected · 2026-11-21 at `cc64bde7c`.** Paths below are relative to
`python/corpus-structure/tests`. This baseline identifies the existing controls to migrate with
their owning package. No test campaign was run for this inventory. New package tests retain
independent expected meaning while replacing the representation-specific expectations.

| Changing contract | Existing tests and shared fixtures | Migration owner |
| --- | --- | --- |
| Product header, native member packet and id | `semantic/test_data_product_admission_programs.py`, `semantic/test_data_operation_admission_native.py`, `semantic/test_data_operation_admission_model.py`, `semantic/test_data_operation_output_witnesses.py`, `semantic/test_data_operation_output_witness_native.py`; `semantic/data_operation_kernel_support.py` | SBX-01, SBX-02, SBX-04 |
| Generated closed completion shape and correspondence | `semantic/test_data_operation_wire.py`, `semantic/test_data_operation_wire_generation.py`; captured native protocol sources in kernel fixtures | SBX-01, SBX-05, SBX-06 |
| Token/sentence/HanLP packets, membership and coordinates | `semantic/test_sentence_products.py`, `semantic/test_hanlp_products.py`, `semantic/sentence_products_test_support.py`, `methods/test_pm2_hanlp_products.py`, `methods/test_pm2_hanlp_admission.py`, `ingest/test_sentences.py` | SBX-03, SBX-05 |
| Shared reference dictionaries and graph membership | `semantic/test_selected_contribution_inputs.py`, `semantic/test_selected_contribution_scope.py`, `semantic/selected_graph_test_support.py`, `semantic/rich_domain_native_support.py`, `semantic/test_contextual_workflow_native.py` | SBX-00 defect repair, SBX-05 |
| Whole-product support, frontier, exact cut and export pages | `semantic/test_demand_export_native.py`, `semantic/test_demand_export_manifest.py`, `semantic/test_demand_wire.py`; `semantic/declared_scenarios.py` | SBX-11, SBX-12 |
| PDF staged rows, access columns and captured reconstruction | `semantic/test_pdf_staging.py`, `semantic/test_pdf_reconciliation.py`, `semantic/test_pdf_access_correspondence_programs.py`, `semantic/test_current_pdf_integration_native.py`, `semantic/pdf_record_reader_support.py` | SBX-14 through SBX-17 |
| Spool, worker, acknowledgement and recovery | `ingest/test_pdf_build_spool.py`, `ingest/test_pdf_worker_stdio.py`, `ingest/test_pdf_stream_protocol.py`, `orchestrate/test_pdf_cancellation_native.py`, `orchestrate/test_pdf_streaming_integration.py`; `pdf_process_support.py`, `pdf_acceptance_support.py` | SBX-16, SBX-17, SBX-20 |

The defect repair specifically replaces the fake `ops.data_request.binding` fixtures in
`semantic/test_selected_contribution_inputs.py` with exact frontier-use selections. A native
export-backed regression must reach both graph and grouped finite interpretation. The new
partition controls must include corrupted digest refusal and independent canonical vectors,
since updating fixture shapes alone cannot establish semantic correctness.

For subsequent slices, search the changed symbol's current consumers before removing a helper.
This starting baseline groups the known affected contracts and is not a claim that these are
the only tests that will change across all 23 packages.
