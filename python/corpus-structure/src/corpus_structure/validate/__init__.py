"""Batch validation, the batch -> candidate adapter, the rule views and the rule runner (P0-S-2).

Schema and rules §3.5-§3.8; D4 M19, M24 step 3; D5 §8. `validate` is the sole owner of reference
and type checking for batches (RC19). It never imports `methods.math`: the grammar's readings reach
the finalize site's views as data (D5 §8.2, P0CL-14).
"""
