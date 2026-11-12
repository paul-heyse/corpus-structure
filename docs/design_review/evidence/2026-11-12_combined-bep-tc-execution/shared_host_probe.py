"""Small D1/HanLP adapter check through the selected common host; no database/book."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.methods.native_host import NativeHostGroup
from corpus_structure.methods.native_profiles import pm2_selection, preflight_native_runtime
from corpus_structure.settings import Settings


def main():
    assets = Path(__file__).resolve().parents[4] / "build/models/pm2"
    selections = {}
    for provider in ("d1", "hanlp"):
        checked = preflight_native_runtime(provider, assets)
        selections[provider] = pm2_selection(provider, assets, checked["runtime_identity"], checked["assets"])
    requests = {
        "d1": {"state": {"source": "12"}, "questions": {"value": {"type": "text", "instructions": "Copy the numeral as written."}}},
        "hanlp": {"sentences": [["Let", "X", "be", "a", "value", "."]]},
    }
    with NativeHostGroup(CharacterizationExecutionPolicy(), Settings().nemotron.endpoint) as group:
        group.declare(tuple(selections.values()))
        def infer(provider):
            result = group.infer(selections[provider], requests[provider], lambda: None)
            startup = group.startup(selections[provider], lambda: None)
            return {"provider": provider, "device": startup["device"], "dtype": startup["dtype"],
                    "result": result}
        with ThreadPoolExecutor(max_workers=2) as pool:
            for result in pool.map(infer, selections):
                print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
