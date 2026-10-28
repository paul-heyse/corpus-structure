"""P5 (2026-10-28): spaCy 3.8 mechanics for M03 variant b' on the four spike pages (S1 adapter).

    cd docs/design_review/evidence/2026-10-28_design-spikes
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python ../2026-10-28_library-text-math/p5_spacy.py

1. How often the tokenizer's boundaries straddle a math span (Doc.char_span strict is None), so that
   alignment_mode="expand" merges non-math characters into the math token.
2. Whether the merge attrs POS=PROPN / TAG=NNP survive the tagger and attribute_ruler.
3. A Doc built from words/spaces (math spans as single words, the prose pieces tokenized by
   nlp.tokenizer) against the retokenize route: identical sentence starts?
4. nlp.pipe over prepared Docs against the per-block loop over nlp.pipeline: identical output, time.
"""
import json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-10-28_design-spikes" / "code"))
import spacy  # noqa: E402
from spacy.tokens import Doc  # noqa: E402
import s1_adapter as A  # noqa: E402
import s1_sentences as S  # noqa: E402

nlp = spacy.load("en_core_web_sm")
pages = ["special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"]
blocks = [b for p in pages for b in S.blocks_of(A.adapt(p))]
res = {"blocks": len(blocks), "spacy": spacy.__version__, "model": nlp.meta["name"] + "-" + nlp.meta["version"],
       "pipeline": nlp.pipe_names}

straddle, examples, inline = 0, [], 0
for b in blocks:
    doc = nlp.make_doc(b["text"])
    for m in b["math"]:
        if m["display"]:
            continue
        inline += 1
        if doc.char_span(m["start"], m["end"], alignment_mode="strict") is None:
            straddle += 1
            sp = doc.char_span(m["start"], m["end"], alignment_mode="expand")
            if len(examples) < 6:
                examples.append({"math": b["text"][m["start"]:m["end"]][:50], "expanded": sp.text[:60] if sp else None})
res["inline_math"] = inline
res["strict_misaligned"] = straddle
res["misaligned_examples"] = examples

# 2. tags after the pipeline
docs = [S.merged_doc(nlp, b) for b in blocks]
tags = {}
for d in docs:
    for t in d:
        if t.text.startswith("\\(") and t.text.endswith("\\)"):
            tags[(t.tag_, t.pos_)] = tags.get((t.tag_, t.pos_), 0) + 1
res["merged_math_token_tag_pos_after_pipeline"] = {f"{k[0]}/{k[1]}": v for k, v in sorted(tags.items(), key=lambda kv: -kv[1])[:6]}


# 3. words/spaces construction
def words_doc(b):
    text, words, spaces, is_math = b["text"], [], [], []
    pos = 0
    cuts = sorted([(m["start"], m["end"]) for m in b["math"] if not m["display"]] + [(r["start"], r["end"]) for r in b.get("refs", [])])
    def prose(a, e):
        for t in nlp.tokenizer(text[a:e]):
            words.append(t.text); spaces.append(bool(t.whitespace_)); is_math.append(False)
    for a, e in cuts:
        if a < pos:
            continue
        prose(pos, a)
        words.append(text[a:e]); spaces.append(e < len(text) and text[e] == " "); is_math.append(True)
        pos = e + (1 if e < len(text) and text[e] == " " else 0)
    prose(pos, len(text))
    # a prose piece ending in a space before math: the tokenizer drops trailing whitespace into whitespace_
    doc = Doc(nlp.vocab, words=words, spaces=spaces)
    assert doc.text == text, (doc.text[:80], text[:80])
    for r in b.get("refs", []):
        sp = doc.char_span(r["start"], r["end"])
        if sp is not None:
            for t in sp:
                t.is_sent_start = False
    for m in b["math"]:
        if m["display"]:
            sp = doc.char_span(m["start"], m["end"], alignment_mode="expand")
            if sp is not None:
                for t in sp[1:]:
                    t.is_sent_start = False
    return doc

same = 0
bad = 0
for b, d in zip(blocks, docs):
    try:
        w = words_doc(b)
    except AssertionError:
        bad += 1
        continue
    for _, proc in nlp.pipeline:
        w = proc(w)
    same += [s.start_char for s in w.sents] == [s.start_char for s in d.sents]
res["words_doc_same_sentences"] = same
res["words_doc_text_mismatch"] = bad


# 4. nlp.pipe over prepared docs
def prepared(b):
    doc = nlp.make_doc(b["text"])
    with doc.retokenize() as rt:
        for m in b["math"]:
            if not m["display"]:
                sp = doc.char_span(m["start"], m["end"], alignment_mode="expand")
                if sp is not None and len(sp) > 1:
                    rt.merge(sp)
        for r in b.get("refs", []):
            sp = doc.char_span(r["start"], r["end"], alignment_mode="expand")
            if sp is not None and len(sp) > 1:
                rt.merge(sp)
    for r in b.get("refs", []):
        sp = doc.char_span(r["start"], r["end"], alignment_mode="expand")
        if sp is not None:
            for t in sp:
                t.is_sent_start = False
    for m in b["math"]:
        if m["display"]:
            sp = doc.char_span(m["start"], m["end"], alignment_mode="expand")
            if sp is not None:
                for t in sp[1:]:
                    t.is_sent_start = False
    return doc

t = time.perf_counter(); loop = [S.merged_doc(nlp, b) for b in blocks]; t_loop = time.perf_counter() - t
t = time.perf_counter(); piped = list(nlp.pipe((prepared(b) for b in blocks), batch_size=64)); t_pipe = time.perf_counter() - t
res["pipe_same_sentences"] = sum([s.start_char for s in a.sents] == [s.start_char for s in c.sents] for a, c in zip(loop, piped))
res["time_loop_s"], res["time_pipe_s"] = round(t_loop, 2), round(t_pipe, 2)
excl = ["ner", "lemmatizer"]
nlp2 = spacy.load("en_core_web_sm", exclude=excl)
t = time.perf_counter(); piped2 = list(nlp2.pipe((prepared(b) for b in blocks), batch_size=64)); res["time_pipe_exclude_ner_lemmatizer_s"] = round(time.perf_counter() - t, 2)
res["pipe_exclude_same_sentences"] = sum([s.start_char for s in a.sents] == [s.start_char for s in c.sents] for a, c in zip(loop, piped2))
print(json.dumps(res, indent=1, ensure_ascii=False))
