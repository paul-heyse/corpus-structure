"""Prepare TC-10 source-only opportunities; never tokenize or read characterizations.

Reads the selected immutable PDF source views and native hierarchy only. The script has
no annotation/model/producer-output imports. Selection is an exposed purposive chapter
panel, not a probability sample or book-wide semantic reference denominator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from sqlalchemy import select

from corpus_structure.evaluate.record_references import source_binding, source_units
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RUN = 496
CUT = 614
PROJECT = "nce-grinstead-snell-full-book"
FACETS = (
    "source_capture", "native_fidelity", "predicates_roles", "operators_scope",
    "attachment_binding", "choice_compatibility", "provider_questions",
    "coverage_failure", "retained_consumer_fidelity",
)


def write(name, data):
    path = HERE / name
    path.write_bytes(canonical_bytes(data) + b"\n")
    return path


def block_owner(pointer, nodes):
    # Plain native containment only; inline child text belongs to its enclosing
    # original text item. There is no token/sentence/predicate nomination here.
    node = nodes[pointer]
    parent = nodes.get(node.get("parent", {}).get("$ref"), {})
    if node.get("label") == "inline":
        return node.get("parent", {}).get("$ref", pointer)
    if parent.get("label") == "inline":
        return parent.get("parent", {}).get("$ref", pointer)
    return pointer


def inventory():
    rows = []
    with open_runtime_engine(Settings(), "tc10-source-only-panel", purpose="read") as engine, engine.connect() as conn:
        release = conn.scalar(select(table("ops.run").c.release_id).where(table("ops.run").c.id == RUN))
        units = source_units(conn, RUN)
        for unit in units:
            view = load_source_view(conn, unit["source_view_id"], analysis=False)
            nodes = {item["self_ref"]: item for item in view.items}
            section = nodes.get(view.ref.section_pointer, {})
            ancestors = [{"pointer": item["self_ref"], "title": item.get("name", "")} for item in view.ancestors if item.get("label") == "section"]
            grouped = {}
            for piece in view.pieces:
                if piece["kind"] != "native_text" or piece["end"] <= piece["start"]:
                    continue
                owner = block_owner(piece["item_ref"], nodes)
                if nodes.get(owner, {}).get("label") == "table":
                    continue
                grouped.setdefault(owner, []).append(piece)
            blocks = []
            for owner, pieces in grouped.items():
                start, end = pieces[0]["start"], pieces[-1]["end"]
                text = view.text[start:end]
                if not text.strip():
                    continue
                extents = [dict(source_view_id=view.ref.id, projection=view.ref.projection_digest,
                                native_pointer=piece["item_ref"], start=piece["start"], end=piece["end"])
                           for piece in pieces]
                labels = [nodes.get(piece["item_ref"], {}).get("label") for piece in pieces]
                pages = sorted({prov["page_no"] for piece in pieces for prov in nodes.get(piece["item_ref"], {}).get("prov", []) if "page_no" in prov})
                blocks.append(dict(pointer=owner, start=start, end=end, text=text,
                                   extents=extents, labels=labels, pages=pages))
            rows.append(dict(
                view_id=view.ref.id, unit_key=unit["unit_key"], title=section.get("name", ""),
                section_pointer=view.ref.section_pointer, ancestors=ancestors,
                base_document=view.ref.native_product.values(), projection_digest=view.ref.projection_digest,
                recipe_digest=view.ref.recipe_digest, text_length=len(view.text),
                source_health=view.health, blocks=blocks,
            ))
    write("source-inventory.json", dict(run=RUN, cut=CUT, project=PROJECT, release=release,
          source_only=True, selected_views=len(rows), views=rows))
    print(json.dumps({"source_views": len(rows), "blocks": sum(len(row["blocks"]) for row in rows)}))




def select_panel():
    data = json.loads((HERE / "source-inventory.json").read_bytes())
    chapter = None
    candidates = {}
    summary = []
    for view in data["views"]:
        marker = re.fullmatch(r"Chapter ([0-9]+)", view["title"])
        if marker:
            chapter = int(marker[1])
        elif view["title"] == "Appendices":
            chapter = None
        view["chapter"] = chapter
        summary.append({key: view[key] for key in ("view_id", "unit_key", "title", "section_pointer", "ancestors", "text_length", "chapter")})
        if chapter is None or view["title"] in {"Exercises", "Historical Remarks"}:
            continue
        for block in view["blocks"]:
            if 80 <= len(block["text"]) <= 1200 and any(c.isalpha() for c in block["text"]):
                candidates.setdefault(chapter, []).append((view, block))
    write("source-inventory-summary.json", dict(
        run=RUN, cut=CUT, project=PROJECT, release=data["release"], source_only=True,
        selected_views=len(summary), original_blocks=sum(len(v["blocks"]) for v in data["views"]),
        views=summary,
    ))
    questions = []
    def add(chapter, facet, family, kind, question, pair):
        view, block = pair
        key = f"ch{chapter:02d}-{facet}-{len(questions)+1:02d}"
        questions.append(dict(
            opportunity_id=key, chapter=chapter, facet=facet, required_family=family,
            native_kind=kind, question=question, view_id=view["view_id"],
            unit_key=view["unit_key"], block=block,
        ))
    for chapter in range(1, 13):
        simple = [pair for pair in candidates[chapter] if 90 <= len(pair[1]["text"]) <= 350
                  and all(label == "text" for label in pair[1]["labels"])
                  and pair[1]["text"].isascii() and len(pair[1]["extents"]) == 1
                  and pair[1]["text"][0].isupper() and pair[1]["text"].rstrip().endswith((".", "!", "?"))]
        if not simple:
            raise ValueError(f"chapter {chapter} needs an independently reviewed whole-block native opportunity")
        # First suitable original block in source order; neither prediction success nor
        # alignment survival influences eligibility or this deterministic panel selection.
        pair = simple[0]
        kind = "spans" if chapter % 2 else "tokenization"
        facet = "native_fidelity" if kind == "spans" else "source_capture"
        family = "spacy.sentences" if kind == "spans" else "spacy.tokens"
        question = (
            "Independently delimit every sentence in this complete original block, with exact character boundaries. "
            "Supply independent atom-preserving words/spaces reconstructing its exact text; use native_reference kind spans, span_key sents, labeled false."
            if kind == "spans" else
            "Independently specify the complete original block's atom-preserving token boundaries as words/spaces reconstructing its exact text. "
            "Use native_reference kind tokenization; punctuation and repeated occurrences retain exact original positions."
        )
        add(chapter, facet, family, kind, question, pair)
    semantic = [
        (1, "predicates_roles", "construction.predication", r"\b(?:is|are|was|will|gives|toss|roll)\b", "Identify the source-supported predicate(s) and participant roles in the selected original block. Preserve grammatical versus semantic role and distinguish implicit or unresolved participants; do not label every passive subject an actor."),
        (2, "operators_scope", "construction.scope", r"\b(?:not|each|every|any|must|may|only|if)\b", "Identify overt quantification, negation, modality and their supported targets/scopes. Preserve source-supported alternatives or unresolved scope rather than forcing a unique reading."),
        (3, "attachment_binding", "context.binding", r"\b(?:let|suppose|this|these|it|they|where|if)\b", "Identify source-local binders or anaphoric mentions and supported binding/host within the supplied original block and focal source view. Do not infer an antecedent across unavailable context."),
        (4, "choice_compatibility", "construction.source_readings", r"\b(?:either|or|otherwise|not|if)\b", "Distinguish semantic disjunction from genuine interpretive uncertainty. State permitted readings/correlations and whether compatibility is unknown; independent local possibilities do not license crossed combinations."),
        (5, "provider_questions", "character_modal_force_v1", r"\b(?:may|must|can|will|should)\b", "Independently state any overt modal cue, its target and source-supported force in this block, or explicit inapplicability/insufficient source. No cue alone establishes its force or target."),
        (6, "coverage_failure", "spacy.tokens", r"\b(?:suppose|let|each|every|if|not)\b", "Specify the original ordered real source extents that a claimed complete token examination of this block must cover, including formula/reference atoms if present. Source-side expectations do not assert that a runtime operation succeeded; actual failures are assessed separately after execution."),
        (7, "retained_consumer_fidelity", "spacy.tokens", r"\b(?:is|are|if|let|this|then)\b", "Specify exact original occurrences, their ordered extents and distinct repeated spellings that retained reads/replay must preserve. This source-first question asserts no future layer or choice identity; output-first replay will bind those later."),
    ]
    occupied = {(q["view_id"], q["block"]["pointer"]) for q in questions}
    for chapter, facet, family, cue, question in semantic:
        matches = [pair for pair in candidates[chapter] if (pair[0]["view_id"],pair[1]["pointer"]) not in occupied and re.search(cue, pair[1]["text"], re.I)]
        if not matches:
            raise ValueError(f"no source-side opportunity for {facet}")
        pair = matches[0]
        occupied.add((pair[0]["view_id"], pair[1]["pointer"]))
        add(chapter, facet, family, None, question, pair)
    # Source-selected challenge questions, not pre-authored expected interpretations.
    challenges = [
        (8, "operators_scope", "construction.scope", r"\bnot\b", "Challenge case: independently determine negation and quantified scope/targets, retaining a partial or unresolved interpretation when the supplied source does not settle it."),
        (9, "choice_compatibility", "construction.source_readings", r"\bor\b", "Challenge case: determine whether the source's or expresses an object-level disjunction or admits distinct supported analytical readings, preserving correlations and unknown compatibility."),
        (10, "attachment_binding", "context.binding", r"\b(?:let|suppose|this|it|they|that)\b", "Challenge case: distinguish a source-local binder/reference occurrence from another equal-spelled mention and identify only a source-supported host or explicit unresolved binding."),
    ]
    for chapter, facet, family, cue, question in challenges:
        matches = [pair for pair in candidates[chapter] if (pair[0]["view_id"],pair[1]["pointer"]) not in occupied and re.search(cue,pair[1]["text"],re.I)]
        if not matches:
            raise ValueError(f"no source-side challenge {chapter}/{facet}")
        pair = matches[0]
        occupied.add((pair[0]["view_id"],pair[1]["pointer"]))
        add(chapter, facet, family, None, question, pair)
    # Actual original math atoms exercise early formal characterization rather than
    # relying solely on prose/native task references. No parsed reading is supplied.
    formal_targets = [
        ("\\omega_1", "formal.identifier", "Independently characterize this exact original subscripted Greek identifier and its character/atom boundaries. Preserve original spelling and subscript attachment; scientific identity is outside this question."),
        (".3\\le x<.7", "formal.interval", "Independently characterize the exact original chained inequality, endpoint inclusivity and the bound variable. Preserve source correspondence and any recognition or interpretation uncertainty; do not replace the original TeX with an unexplained normalized string."),
        ("X_1+X_2+X_3+X_4", "formal.math", "Independently specify the source-supported formal sum structure and its four indexed terms. Preserve subscript binding, operand order and original positions; declare unresolved alternatives rather than infer scientific relations."),
    ]
    for literal, family, question in formal_targets:
        found = None
        for source_view in data["views"]:
            if source_view.get("chapter") is None:
                continue
            for block in source_view["blocks"]:
                for label, extent in zip(block["labels"], block["extents"], strict=True):
                    text = block["text"][extent["start"]-block["start"]:extent["end"]-block["start"]]
                    if label == "formula" and text == literal:
                        selected_block = dict(block, pointer=extent["native_pointer"],
                            context_owner=block["pointer"],start=extent["start"],end=extent["end"],
                            text=text,extents=[extent],labels=[label])
                        found = (source_view,selected_block)
                        break
                if found: break
            if found: break
        if found is None:
            raise ValueError("selected original formal source is unavailable")
        add(found[0]["chapter"], "source_capture", family, None, question, found)
    dependency = next((view,block) for view in data["views"] for block in view["blocks"]
                      if block["text"] == "This method can be easily programmed to run on a computer.")
    add(dependency[0]["chapter"], "native_fidelity", "spacy.dependency", "dependencies",
        "Independently provide the complete original short block's grammatical dependency heads and labels in the spaCy scheme, with zero-based token heads and self-headed root. Supply independent exact words/spaces; preserve passive subject versus actor and modal/infinitival attachment. Use native_reference kind dependencies; do not substitute UD labels.",dependency)
    selected_ids = {question["view_id"] for question in questions}
    selected = []
    for view in data["views"]:
        if view["view_id"] not in selected_ids:
            continue
        asked = [question for question in questions if question["view_id"] == view["view_id"]]
        chosen = {question["block"].get("context_owner", question["block"]["pointer"]) for question in asked}
        # Neighbour source blocks provide local original context without any producer hints.
        indices = {i for i,block in enumerate(view["blocks"]) if block["pointer"] in chosen}
        context_indices = {j for i in indices for j in range(max(0,i-1),min(len(view["blocks"]),i+2))}
        packet = {key:view[key] for key in ("view_id","unit_key","title","section_pointer","ancestors","base_document","projection_digest","recipe_digest","chapter","source_health","text_length")}
        packet.update(source_only=True, questions=asked,
                      original_context_blocks=[view["blocks"][i] for i in sorted(context_indices)])
        write(f"source-view-{view['view_id']}.json",packet)
        selected.append(dict(view_id=view["view_id"],unit_key=view["unit_key"],chapter=view["chapter"],title=view["title"],opportunities=[q["opportunity_id"] for q in asked],packet=f"source-view-{view['view_id']}.json"))
    manifest = dict(
        version="tc10-source-panel-1", project=PROJECT, source_run=RUN, source_cut=CUT,
        release_id=data["release"], source_only=True, producer_outputs_inspected=False,
        selection="deterministic_source_order_chapter_facet_panel", chapters=list(range(1,13)),
        facets=sorted({q["facet"] for q in questions}), source_views=selected,
        opportunities=questions, semantic_population_claim="selected panel only; full-book coverage is separate",
        inherited_source_limits="display partial; inline/cell unknown; no source-health strengthening",
    )
    write("manifest.json",manifest)
    selected_files = {unit["packet"] for unit in selected}
    local_drafts = sorted(path.name for path in HERE.glob("source-view-*.json") if path.name not in selected_files)
    (HERE / ".gitignore").write_text(
        "# Reproducible local source-only selection cache; original source custody is retained in native storage.\nsource-inventory.json\n"
        + "".join(name + "\n" for name in local_drafts)
    )
    print(json.dumps(dict(views=len(selected),opportunities=len(questions),chapters=manifest["chapters"],facets=manifest["facets"])))




def frames():
    manifest = json.loads((HERE / "manifest.json").read_bytes())
    payloads = {}
    with open_runtime_engine(Settings(), "tc10-source-only-panel-frames", purpose="evaluate") as engine, engine.connect() as conn:
        for selected in manifest["source_views"]:
            packet = json.loads((HERE / selected["packet"]).read_bytes())
            logical = source_binding(conn, source_run_id=RUN, source_view_id=packet["view_id"], source_cut_id=CUT)
            base = packet["base_document"]
            pin = dict(source=logical, native_product_task_id=base["task_id"], product_key=base["product_key"],
                       product_digest=base["content_digest"], projection_digest=packet["projection_digest"],
                       recipe_digest=packet["recipe_digest"], source_view_id=packet["view_id"])
            opportunities, scopes = [], {}
            for question in packet["questions"]:
                extents = question["block"]["extents"]
                opportunities.append(dict(opportunity_id=question["opportunity_id"], extents=extents,
                                          facet=question["facet"], source_state="uninspected"))
                for extent in extents:
                    scope = dict(pin=pin, space="selected_projection", pointer=extent["native_pointer"],
                                 precision="exact", start=extent["start"], end=extent["end"])
                    scopes[canonical_bytes(scope)] = scope
            frozen_questions = "\n".join(
                f"{q['opportunity_id']} [facet={q['facet']}; required_family={q['required_family']}]: {q['question']}"
                for q in packet["questions"]
            )
            frame = dict(
                unit=selected["unit_key"], release_id=manifest["release_id"],
                guideline_version="characterization-reference-1", rubric_version="chapter-facet-native-and-semantic-1",
                context_policy="original-native-block-and-focal-view-source-only-1",
                operation_question=frozen_questions, operation_version="text-characterization-panel-1",
                domain="statistics", direction="source_first", pin=pin, anchor_ids=[], related_pins=[],
                anchor_scopes=list(scopes.values()), contribution_ids=[], source_group="grinstead-snell",
                partition="development", inspected_scope="Selected original whole blocks and their authenticated focal source view; ancestor titles are context, not extra focal membership.",
                opportunities=opportunities,
                exposure_history=["shared-full-book-development", "source-only-panel-selection"],
                characterization_view=None, selected_layers=[], outputs=None,
            )
            payloads[selected["unit_key"]] = dict(protocol="source-operation-frame-3", evaluation_frame=frame,
                                                captured_coordinates=[], context_dependency_digest=None)
    write("sample.json", dict(
        sampling=dict(seed=0, strata={unit["unit_key"]: f"chapter-{unit['chapter']}" for unit in manifest["source_views"]},
                      inclusion_probabilities={key:1.0 for key in payloads},
                      provenance=dict(selection="deterministic_purposive_panel", source_only=True,
                                      probability_meaning="Membership is certain within this explicitly fixed panel; not random sampling or book-wide accuracy inference.",
                                      manifest_sha256=hashlib.sha256((HERE / "manifest.json").read_bytes()).hexdigest(),
                                      producer_outputs_inspected=False),
                      cohort="tc10-chapter-and-nine-facet-panel-1"),
        frames=payloads,
    ))
    print(json.dumps(dict(frames=len(payloads), opportunities=sum(len(v["evaluation_frame"]["opportunities"]) for v in payloads.values()))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inventory", "select", "frames"])
    args = parser.parse_args()
    {"inventory": inventory, "select": select_panel, "frames": frames}[args.action]()
