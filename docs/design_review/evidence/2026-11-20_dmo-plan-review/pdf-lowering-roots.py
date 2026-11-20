"""Test whether removing the Integrated roots closes the existing lowering analysis."""

import json
from pathlib import Path
from subprocess import check_output

from corpus_structure.semantic import pdf_lowering
from corpus_structure.semantic.code_identity import capture_code_identity

INTEGRATED = "corpus_structure.semantic.pdf_integrated"
package_root = Path(pdf_lowering.__file__).resolve().parents[1]
loads = {
    "shared": (pdf_lowering.LOWERING_ENTRY_MODULES, pdf_lowering.LOWERING_ENTRY_CALLABLES),
    "without_integrated_root": (
        tuple(name for name in pdf_lowering.LOWERING_ENTRY_MODULES if name != INTEGRATED),
        tuple(name for name in pdf_lowering.LOWERING_ENTRY_CALLABLES
              if name.rsplit(".", 1)[0] != INTEGRATED),
    ),
}
result = {
    "source_commit": check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    "purpose": "A root-removal experiment on the existing analyzer. It does not prove the resulting workload is sufficient for Standard capture.",
    "observations": {},
}
for name, (entries, callables) in loads.items():
    code = capture_code_identity(package_root, entries, callables=callables)
    result["observations"][name] = {
        "entries": entries,
        "callables": callables,
        "module_count": len(code.modules),
        "complete": code.complete,
        "unknown_count": len(code.unknowns),
        "integrated_still_discovered": any(m.module == INTEGRATED for m in code.modules),
        "observed_digest": code.observed_digest,
    }
print(json.dumps(result, indent=2))
