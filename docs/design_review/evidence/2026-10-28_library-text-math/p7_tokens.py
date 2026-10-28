"""P7 (2026-10-28): token counting with tokenizers 0.23.3 and the Qwen3.5-9B tokenizer.json (results/environment.json).

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p7_tokens.py

Normalizer, pre-tokenizer and post-processor of the file; whether encode adds special tokens;
encode_batch_fast against encode_batch (same ids?) and time; whether per-sentence counts add up to the
count of the joined unit text; whether a chat template is in tokenizer.json. Uses the four spike pages'
canonical texts and sentences (S1 adapter + s1_sentences, P1 + b').
"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent / "2026-10-28_design-spikes"
sys.path.insert(0, str(SPIKE / "code"))
import tokenizers  # noqa: E402
from tokenizers import Tokenizer  # noqa: E402

env = json.loads((SPIKE / "results/environment.json").read_text())
path = env["tokenizers"]["qwen3.5-9b"]["tokenizer_json"]
tok = Tokenizer.from_file(path)
cfg = json.loads(Path(path).read_text())
snap = Path(path).parent
res = {"tokenizers": tokenizers.__version__, "revision": env["tokenizers"]["qwen3.5-9b"]["revision"],
       "normalizer": (cfg.get("normalizer") or {}).get("type"), "pre_tokenizer": (cfg.get("pre_tokenizer") or {}).get("type"),
       "post_processor": (cfg.get("post_processor") or {}).get("type"), "model": cfg["model"]["type"],
       "added_tokens": len(cfg.get("added_tokens", [])), "chat_template_in_tokenizer_json": "chat_template" in cfg,
       "tokenizer_config_has_chat_template": (snap / "tokenizer_config.json").exists() and "chat_template" in (snap / "tokenizer_config.json").read_text(),
       "chat_template_jinja_file": (snap / "chat_template.jinja").exists()}
s = "Suppose that \\(X\\) has the normal distribution with mean \\(\\mu\\)."
res["special_tokens_added_by_encode"] = len(tok.encode(s).ids) - len(tok.encode(s, add_special_tokens=False).ids)

texts = [p.read_text() for p in sorted((SPIKE / "results/s1/canonical").glob("special__*.txt"))]
paras = [x for t in texts for x in t.split("\n\n") if x.strip()]
t0 = time.perf_counter(); a = tok.encode_batch(paras, add_special_tokens=False); t_batch = time.perf_counter() - t0
t0 = time.perf_counter(); b = tok.encode_batch_fast(paras, add_special_tokens=False); t_fast = time.perf_counter() - t0
t0 = time.perf_counter(); c = [tok.encode(x, add_special_tokens=False) for x in paras]; t_loop = time.perf_counter() - t0
res.update({"paragraphs": len(paras), "tokens_total": sum(len(e.ids) for e in a),
            "fast_ids_equal": all(x.ids == y.ids for x, y in zip(a, b)), "loop_ids_equal": all(x.ids == y.ids for x, y in zip(a, c)),
            "fast_offsets_zero": all(o == (0, 0) for e in b[:20] for o in e.offsets),
            "time_ms": {"encode_batch": round(t_batch * 1000, 1), "encode_batch_fast": round(t_fast * 1000, 1), "loop": round(t_loop * 1000, 1)},
            "chars_per_token": round(sum(map(len, paras)) / sum(len(e.ids) for e in a), 2)})

# additivity: sentences of each paragraph counted separately versus the paragraph
sys.path.insert(0, str(SPIKE / "code"))
import s1_adapter as A  # noqa: E402
import s1_sentences as S  # noqa: E402
diff, n, worst = 0, 0, 0
for page in ["special/Normal.html", "special/Gamma.html"]:
    r = A.adapt(page)
    sents = S.sentences(r, "P1", "bp+c")
    by_parent = {}
    for x in sents:
        by_parent.setdefault(x["parent"], []).append(x)
    for parent, ss in by_parent.items():
        if len(ss) < 2:
            continue
        whole = r["text"][ss[0]["start"]:ss[-1]["end"]]
        parts = [r["text"][x["start"]:x["end"]] for x in ss]
        tw = len(tok.encode(whole, add_special_tokens=False).ids)
        tp = sum(len(e.ids) for e in tok.encode_batch_fast(parts, add_special_tokens=False))
        n += 1
        diff += tp != tw
        worst = max(worst, abs(tp - tw) / tw)
res["multi_sentence_blocks"] = n
res["blocks_where_sum_of_sentences_differs"] = diff
res["worst_relative_difference"] = round(worst, 4)
print(json.dumps(res, indent=1))
