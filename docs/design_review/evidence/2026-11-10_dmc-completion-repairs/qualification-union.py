"""Reconcile retained full coverage and affected replacements by actual identity."""
import json
import subprocess
import sys

ORIGINAL = "5505058f634a4f0ba32aadc474bb8c50"
EXCLUDED = {
    "python/corpus-structure/tests/methods/test_gliner.py::test_native_boundary_diagnostic_observes_and_rescores_exact_occurrence",
    "python/corpus-structure/tests/semantic/test_pm2_parser_stage_native.py::test_alternate_domain_parser_run_retains_siblings_after_profile_refusal",
}


def answer(*args):
    return json.loads(subprocess.run(["uv", "run", "ci", *args, "--json"],
                                    capture_output=True, text=True, check=True).stdout)


def coverage(*results, bounded=False):
    args = ["test", "coverage", *results]
    if bounded:
        args.extend(("--view", "unresolved", "--limit", "10"))
    return answer(*args)


ordinary, *replacements = sys.argv[1:]
assert replacements
original = coverage(ORIGINAL)
base = coverage(ordinary)
original_required = set(original["node_coverage"]["required"])
base_required = set(base["node_coverage"]["required"])
assert EXCLUDED <= original_required
assert EXCLUDED.intersection(base_required) == {next(n for n in EXCLUDED if "parser_stage" in n)}
replacement_reports = [coverage(item) for item in replacements]
replacement_required = set()
for report in replacement_reports:
    assert report["node_coverage"]["unresolved"] == []
    assert not report["missing_lanes"]
    assert all(outcome == "passed" for outcome in report["attempt_outcomes"].values())
    replacement_required.update(report["node_coverage"]["required"])
failures = answer("test", "failures", ordinary, "--lane", "ordinary", "--limit", "100")
assert failures["selected"] == failures["available"]
assert {item["nodeid"] for item in failures["items"]} <= replacement_required
normal = coverage(ordinary, *replacements)
assert set(normal["node_coverage"]["unresolved"]) == EXCLUDED.intersection(base_required)
assert not normal["missing_lanes"]
# The original full manifest differs from the complete ordinary selection only by
# the GLiNER opt-in, the disjoint fault controls, and later added regression nodes.
fault = (original_required - base_required) - EXCLUDED
manifest = answer("results", "show", ORIGINAL)
fault_counts = manifest["details"]["lane_counts"]["fault"]
assert len(fault) == fault_counts["selected"] == fault_counts["passed"] == 8
assert all(node.startswith("tests/scripts/test_native_auth.py::") for node in fault)
assert not fault.intersection(original["node_coverage"]["unresolved"])
union = ((base_required | replacement_required) - EXCLUDED) | fault
assert (original_required - EXCLUDED) <= union
reconciled = coverage(ORIGINAL, ordinary, *replacements, bounded=True)
assert {item["nodeid"] for item in reconciled["items"]} == EXCLUDED
assert reconciled["node_coverage"]["unresolved"] == len(EXCLUDED)
assert not reconciled["missing_lanes"] and not reconciled["context_unknowns"]
print(json.dumps(dict(
    outcome="passed", original=ORIGINAL, ordinary=ordinary, replacements=replacements,
    original_required=len(original_required), applicable_original=len(original_required - EXCLUDED),
    current_required_union=len(union), fault_identities=sorted(fault),
    new_identities=sorted(union - original_required), excluded=sorted(EXCLUDED),
    original_attempt_outcomes=reconciled["attempt_outcomes"],
    source_differences=reconciled["sources_differ"],
    context_differences=reconciled["context_differences"],
    native_observations=reconciled["native_observations"],
    source_applicability="Retained full run at f98aadae9 plus affected replacements at a262e476f; unchanged native-auth/SQL/toolchain context supports original eight fault controls. Later edits are publication only.",
    rust="Original empty discovery: no applicable functional identities; Clippy passed separately.",
), sort_keys=True))
