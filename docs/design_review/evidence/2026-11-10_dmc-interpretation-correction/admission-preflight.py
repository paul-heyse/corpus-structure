"""Read-only current statistics-pack admission preflight; no database or deployment effects."""

import json
from pathlib import Path

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.publication import admit_release, native_constraints, _admit_inference
from corpus_structure.semantic.record_contracts import record_product_classes
from corpus_structure.semantic.regeneration import prepare_packs

folder = Path(__file__).parent / "raw"
folder.mkdir(exist_ok=True)
prepared = prepare_packs((DOMAINS / "statistics",))[-1]
report = dict(
    scope="current_statistics_pack_static_admission_only",
    release_id=prepared.release_id,
    diagnostics=[dict(code=d.code, location=d.location, message=d.message, outcome=d.outcome)
                 for d in prepared.diagnostics],
    effects="none",
)
constraints = native_constraints(prepared)
_admit_inference(prepared)
products = record_product_classes(prepared.definitions)
patterns = [(d.name,p.name) for d in prepared.definitions if d.name not in products
            for p in d.properties if p.pattern or p.patterns]
scopes = [(d.name,p.name,p.constraint_scope) for d in prepared.definitions if d.name not in products
          for p in d.properties if p.constraint_scope not in {"shape","accepted_value"}]
unpermitted = [d for d in prepared.diagnostics if d.outcome in {"unsupported","unresolved"}
              or (d.outcome=="unchecked" and not (d.code=="unchecked_term" and d.message=="not4curation:unchecked"))]
report.update(native_constraints="passed", native_constraint_count=len(constraints),
              inference_lowering="passed", patterned_fields=patterns, unsupported_scopes=scopes,
              unpermitted_diagnostic_count=len(unpermitted))
assert not patterns and not scopes and not unpermitted
try:
    admit_release(prepared)
except Exception as error:
    report.update(outcome="partial", full_admission="blocked", error_type=type(error).__name__,
                  reason=str(error), conclusion="Static native lowering, scopes, patterns and diagnostic checks pass; full admission requires verified deployment and archived binding.")
else:
    report.update(outcome="passed", full_admission="passed")
(folder / "admission-preflight-partial.json").write_text(json.dumps(report, sort_keys=True))
print(json.dumps(report, sort_keys=True))
