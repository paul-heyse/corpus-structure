"""CPU preparation and native inference retain different admission responsibilities."""

from types import SimpleNamespace

from corpus_structure.methods import pm2_hanlp


def test_cpu_bulk_preparation_can_exceed_inference_sentence_cap(tmp_path, monkeypatch):
    parameter = SimpleNamespace(device=SimpleNamespace(type="cpu"), dtype="float32")
    tasks = {
        name: SimpleNamespace(config=SimpleNamespace(max_arg_width=20)) for name in pm2_hanlp._TASKS
    }
    model = SimpleNamespace(
        resolve_tasks=lambda tasks, skip: [list(pm2_hanlp._TASKS)],
        model_=SimpleNamespace(
            parameters=lambda: iter([parameter]),
            encoder=SimpleNamespace(
                transformer=SimpleNamespace(config=SimpleNamespace(_attn_implementation="eager"))
            ),
        ),
        tasks=tasks,
        config=SimpleNamespace(
            transform=lambda sample: sample,
            encoder=SimpleNamespace(transform=lambda: SimpleNamespace(max_seq_length=512)),
        ),
        _savable_config={},
    )
    modules = {
        "torch": SimpleNamespace(device=lambda value: value, float32="float32"),
        "hanlp_common.constant": SimpleNamespace(EOS="<eos>"),
    }
    monkeypatch.setattr(pm2_hanlp, "importlib", SimpleNamespace(import_module=modules.__getitem__))
    monkeypatch.setattr(pm2_hanlp, "_load_archive", lambda *args: (model, []))
    calls = []

    def prepare(actual, resolved, sentences):
        assert actual is model
        calls.append(sentences)
        return [dict(input_ids=list(range(index + 3))) for index, _ in enumerate(sentences)], 512

    monkeypatch.setattr(pm2_hanlp, "_prepare", prepare)
    startup, infer = pm2_hanlp._load_hanlp(tmp_path, "cpu", tmp_path, "backbone")
    sentences = [[str(index)] for index in range(startup["max_sentences"] + 2)]
    admitted = infer(dict(sentences=sentences, prepare_bulk=True))
    assert admitted["outcome"] == "prepared_batch"
    assert [(row["ordinal"], row["row_tokens"]) for row in admitted["members"]] == list(
        enumerate(range(3, 3 + len(sentences)))
    )
    assert calls == [sentences]
    assert infer(dict(sentences=sentences)) == dict(
        outcome="limited", reason="sentences", limit=startup["max_sentences"]
    )
    assert calls == [sentences]
