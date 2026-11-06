"""Literal custody/coverage validator for the frozen independent A assessment.

No production validator or semantic acceptance predicate is imported. A pass means
that the authored judgments are traceable and complete for the fixed 35 IDs.
It does not mean the method's semantic output passed this assessment.
"""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import runpy
import sys

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[7]
EXPECTED_IDS = ['fe09701184cd4d61d96caf05661d38e9c13f83afeb4c56ab189c9bb630b225f4', '312f1acf0514ee313c0cfb83613311410058a0314c48ab4f1d1d8aec802ddf42', 'cd2d326f82123a38804b0c53455cb00304c004b2a0946620bfb9ac98ecaebf40', '1260f6b3c5b66b10b7d058303de67975cf8e98c4fa748d69c8d788f258aa5989', '7252b07bf071a51f51ad8ba09c89341bf0b7ed03701e64b757c6c16ecbe0236b', 'c1d43f4d05f01e0e4d1315c4ba31fe45226b64fde984951f58436a5fdfdd8677', 'a0d1814a020583873cf0e3e465435c4b49fbfa94841ffa9110130950c9febef3', '63e188e0068f2a625302d6892b081cd051ae1abffbfc0ac0999076af0ede1fe8', '6182276c0987cde81c1d679738fc5f31ea8b049d264f245556e3eba3b1d3bd0d', '7150bdfe222cbe12ddb7b7ab237610026302be0745ae93a3ddfdfdd547b1348d', '025fc81d5c6e00965971609ee7d2d3a50253880387eda2be51ea82b67cecb86f', 'dd40f6c3f4447b2a25797110af22a04d16d1b35b1ed08f88f9c1922332d515d5', '10701a2dec9c4a68f38de709185a24ed667b282bc215f1f506ea94415bcb2846', 'b16b87cce059aa5d5539a4c86d1180d8f3d8c7b7666af4f720ee8e16e656e0c7', 'db4f75fbaef72154a8ff79053f6e2870f9799cfeacb91b2234983b72c9ac9e16', '8e6f3bb99a19a24d2f44c2dcf2bd446fe15501d36fa10ae61c2b08c77324b71d', '4429f8d8e484999cb8d9b846de9dc368348afa41a82ee643a1d3dd95d2b873fb', '711c96b5721f1a00268fd019a90f22a136ca92482280e809568c5e22fa0a7ae3', 'fcab116281339ef067bf07b66e213c719f317ddd63fecf19509e0fcf37e6089a', '789223b6033f9c6b1edffdead451bca2826662b663fe03fdc3c9515953251b1a', '08937a61a75694990c9030c0239cba3a0c2ce159a82d9725a89bf534291670cf', 'd5715568638f1b1644d6a105bfb3c152946b02ec01d31f601f9ba5797c9b2fe9', '33bf7dfe9874d675504993ba140c2177f6bf89ff4735020ca072a2049d143549', '0716ddb12192f28293642afea4b7ea659a8c5264582c4216d6126656528cb944', '2fc1a58d72f8fcb6396bddb0fd92fdc80a857d772e1edac04e310300ce5707c3', '923901a01d037aa85b0b0aaeb5fd61399f27f05fb7f622bb3d66d40055c7d8ce', 'bb9530518ccf0a67af6d91366240ec2fa9d9f805deceb9131019df9672f439f9', 'f3864be58e744a5cafeb200cf5971c2388c4b913de663414a2d5903be3ef081c', '66139740c4caed684e27db6a3707eb56f068bdc6c60106d4518d309ffcbfdf2e', 'c0778b4324c687a23ea8b1ced67defe7317e175a398af5ae39b8690c3f9c6aa5', 'c1a80f65900264a4066155ac4775e8829f4a6228db3cba042ab6be02ffde3b2c', '822bb6359ada0a728f424b525b3f030af958a66907511155283f216f21de7613', 'e5b4f05374633154c2c542bdebafc05b5f2b83395907a7d090ec6cd78287dbee', 'd0a47350100c9b89484ec35256a177bc7c6409cbb3575f36c42d58fce4151efd', 'e5f55c3bb94b87b9c44d36a941668535311c0d045252f7f5b30c57e5c6513546']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    assessment_path = OUT / "assessment.json"
    data = json.loads(assessment_path.read_text())
    rows = data["components"]
    check([r["component_id"] for r in rows] == EXPECTED_IDS, "exact ordered 35 component IDs")
    check(len(set(EXPECTED_IDS)) == 35, "unique fixed IDs")
    check(data["baseline"]["run_id"] == 152 and data["baseline"]["cut_id"] == 204, "baseline")
    for pin in data["source_pins"]:
        path = ROOT / pin["path"]
        check(path.stat().st_size == pin["bytes"], f"byte length {path}")
        check(sha(path) == pin["sha256"], f"raw SHA256 {path}")
    base = OUT.parents[2]
    original = base / "current-extraction/named001/structural-inspection.json"
    task = json.loads((base / "assessment/run152-current-named001/task-605.json").read_text())
    check((OUT / "original-structural-inspection.json").read_bytes() == original.read_bytes(), "raw inspection preservation")
    check(json.loads((OUT / "original-task-605-structural-product.json").read_text()) == task["body"]["structural_product"], "original task structural payload preservation")
    inspection = json.loads(original.read_text())
    source_components = [c for r in inspection["reports"] if r.get("definition_components") for c in r["definition_components"]["components"]]
    task_components = task["body"]["structural_product"]["definition_components"]["components"]
    check([c["component_id"] for c in source_components] == EXPECTED_IDS, "inspection coverage")
    check([c["component_id"] for c in task_components] == EXPECTED_IDS, "raw task coverage")
    expectations = runpy.run_path(str(OUT / "author_expectations.py"))["ROWS"]
    source_views = {}
    pages = set()
    for packet_path in sorted((base / "source-recovery/attempt001/source-packets").glob("grinstead*.json")):
        packet = json.loads(packet_path.read_text())
        pages.update(packet["parent_physical_pages"])
        for view in packet["views"]:
            source_views[view["passage"]["passage_id"]] = (packet, view)
    check(len(source_views) == 48 and pages == set(range(191,311)), "48-view / 120-page source inventory")
    span_count = quote_count = 0
    for index, (row, expectation) in enumerate(zip(rows, expectations, strict=True)):
        check(row["observed_component"] == source_components[index], f"unaltered observed component {index+1}")
        check(row["original_task_component"] == task_components[index], f"unaltered task component {index+1}")
        expected_fields = {k:v for k,v in expectation.items() if k not in ("number","native_pointers")}
        check(row["independently_authored_expectation"] == expected_fields, f"independent authored judgments {index+1}")
        packet, view = source_views[row["source"]["passage_id"]]
        check(row["source"]["source_ref"] == view["passage"]["source_ref"], f"source ref {index+1}")
        check(row["source"]["native_content_digest"] == view["source"]["native_content_digest"], f"native digest {index+1}")
        check(row["source"]["parent_pdf_sha256"] == data["baseline"]["parent_pdf_sha256"], f"parent pin {index+1}")
        for role in ("term", "content"):
            span = row["observed_component"][role]
            check(span["passage_id"] == row["source"]["passage_id"], f"passage {index+1}/{role}")
            text = view["passage"]["text"][span["start"]:span["end"]]
            check(text == span["text"], f"literal source slice {index+1}/{role}")
            check(row["exact_location_checks"][role]["exact_source_slice"] == text, f"recorded slice {index+1}/{role}")
            check(row["exact_location_checks"][role]["outcome"] == "passed", f"recorded slice outcome {index+1}/{role}")
            span_count += 1
        native = {x.get("self_ref"):x for x in view["native_context"]["items"]}
        check([e["native_pointer"] for e in row["native_evidence"]] == ["#/texts/"+n for n in expectation["native_pointers"]], f"native pointer selection {index+1}")
        for evidence in row["native_evidence"]:
            item = native[evidence["native_pointer"]]
            check(evidence["native_orig_quote"] == item.get("orig"), f"literal native.orig {index+1}")
            check(evidence["converted_quote"] == item.get("text"), f"literal converted text {index+1}")
            check(evidence["provenance"] == item.get("prov",[]), f"native provenance {index+1}")
            selected = json.loads((ROOT / row["source"]["packet"]).read_text())
            for part in evidence["packet_json_pointer"].strip("/").split("/"):
                selected = selected[int(part)] if isinstance(selected,list) else selected[part]
            check(selected == item, f"packet JSON pointer {index+1}")
            page_map = {p["excerpt_physical_page"]:p for p in packet["page_map"]}
            expected_pages = sorted({page_map[p["page_no"]]["parent_physical_page"] for p in item.get("prov",[])})
            check(evidence["physical_pages"] == expected_pages, f"physical pages {index+1}")
            check(evidence["page_pixel_pins"] == [page_map[n] for n in sorted({p["page_no"] for p in item.get("prov",[])})], f"page pixel pins {index+1}")
            quote_count += 1
        native_quotes = "\n".join(e["native_orig_quote"] or "" for e in row["native_evidence"])
        check(expectation["expected_source_quote"] in native_quotes, f"independent expected literal source quote {index+1}")
        for field in ("expected_subject", "expected_semantic_content", "expected_speech_act", "term_content_roles", "attachment_direction", "output_interpretation", "local_scope_and_conditions", "recognition_fidelity", "useful_narrower_relationship", "missing_or_unassessed_facets"):
            check(bool(expectation[field].strip()), f"granular assessment field {index+1}/{field}")
    independence = data["independence"]
    check(all(independence[k] is False for k in ("read_other_current_assessments","read_implementation_replay_verdicts","production_validator_used","output_used_as_semantic_gold")), "independence declaration")
    result = dict(outcome="passed", scope="literal custody, exact-ID coverage, source locations and independently authored record completeness only",
                  semantic_method_pass_claim=False, checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  command="uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/current-named-review/a/validate_assessment.py",
                  python_version=sys.version, executable=sys.executable, platform=platform.platform(),
                  components_checked=len(rows), exact_role_spans_checked=span_count,
                  native_items_checked=quote_count, source_views_in_inventory=len(source_views),
                  source_physical_pages=len(pages), source_pins_checked=len(data["source_pins"]),
                  assessment_sha256=sha(assessment_path),
                  artifact_hashes={p.name:sha(p) for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in ("receipt.json","validation.log")},
                  not_run=["PDF image inspection", "production runtime or database mutation", "production validator", "full corpus recall gold annotation", "test-all", "hygiene", "turn-end (root owned)"])
    print(json.dumps(result,indent=2))
    (OUT / "receipt.json").write_text(json.dumps(result,indent=2)+"\n")


if __name__ == "__main__":
    main()
