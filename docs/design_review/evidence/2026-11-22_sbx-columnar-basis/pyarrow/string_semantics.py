"""Spot check: UTF-8 kernel units and regex class semantics in pyarrow 26.0.0 (synthetic).

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/pyarrow/string_semantics.py
"""

import json

import pyarrow as pa
import pyarrow.compute as pc

a = pa.array(["éa", "\U0001f600b"])
print(json.dumps({
    "pyarrow": pa.__version__,
    "utf8_length": pc.utf8_length(a).to_pylist(),
    "binary_length": pc.binary_length(a).to_pylist(),
    "utf8_slice_codeunits_0_1": pc.utf8_slice_codeunits(a, 0, 1).to_pylist(),
    "utf8_normalize_nfc_combining": pc.utf8_normalize(pa.array(["é"]), "NFC").to_pylist() == ["é"],
    "re2_backslash_w_matches_e_acute": pc.match_substring_regex(pa.array(["é"]), r"^\w$").to_pylist(),
    "utf8_is_alpha_e_acute": pc.utf8_is_alpha(pa.array(["é"])).to_pylist(),
}, ensure_ascii=False, indent=2))
