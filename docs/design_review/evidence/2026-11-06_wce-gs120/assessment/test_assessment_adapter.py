"""Independent literal controls for the evidence adapter; no product qualification claim."""
import unittest

from normalize_sources import native_segments
from characterize_outputs import anchored_footprints, lower_task, overlap, raw_report_counts, source_indices


def source_fixture():
    return {
        "passage": {"passage_id": "p", "source_ref": "ref", "start": 0,
                    "end": 9, "text": "same\nsame"},
        "source": {"source_view_id": 1, "native_product_key": "organized",
                   "native_content_digest": "d"*64, "native_task_id": 7},
        "packet": {"page_map": [{"excerpt_physical_page": 1, "parent_physical_page": 191},
                                 {"excerpt_physical_page": 2, "parent_physical_page": 192}]},
        "native_context": {"items": [
            {"self_ref": "#/texts/0", "text": "same", "prov": [{"page_no": 1, "charspan": [0,4]}]},
            {"self_ref": "#/texts/1", "text": "same", "prov": [{"page_no": 2, "charspan": [0,4]}]}],
            "pieces": [{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": 4},
                       {"kind": "synthetic_separator", "start": 4, "end": 5},
                       {"kind": "native_text", "item_ref": "#/texts/1", "source_field": "text", "start": 5, "end": 9}]},
    }


class AdapterControls(unittest.TestCase):
    def test_repeated_strings_keep_distinct_physical_occurrences_and_pages(self):
        view=source_fixture()
        first,_=native_segments(view,0,4,"same")
        second,_=native_segments(view,5,9,"same")
        self.assertEqual(first[0]["source_pointer"],"#/texts/0")
        self.assertEqual(first[0]["parent_physical_pages"],[191])
        self.assertEqual(second[0]["source_pointer"],"#/texts/1")
        self.assertEqual(second[0]["parent_physical_pages"],[192])
        self.assertFalse(overlap(first[0],second[0]))

    def test_wrong_quote_is_rejected_without_searching_for_replacement(self):
        with self.assertRaisesRegex(ValueError,"differs"):
            native_segments(source_fixture(),1,4,"same")

    def test_cross_piece_quote_retains_separator_without_inventing_native_text(self):
        segments,separators=native_segments(source_fixture(),0,9,"same\nsame")
        self.assertEqual([s["text"] for s in segments],["same","same"])
        self.assertEqual(separators,[{"start":4,"end":5,"text":"\n"}])
        self.assertEqual([s["native_start"] for s in segments],[0,0])

    def test_native_source_anchor_requires_exact_piece_text(self):
        index,_=source_indices({1:source_fixture()})
        anchor={"pin":{"product_key":"organized","product_digest":"d"*64},
                "space":"native","pointer":"#/texts/0","start":1,"end":3,"source_piece":"am"}
        observed,state=anchored_footprints(anchor,index)
        self.assertEqual(state,"exact_native_text_verified")
        self.assertEqual(observed[0]["text"],"am")
        observed,state=anchored_footprints({**anchor,"source_piece":"wrong"},index)
        self.assertEqual(observed,[])
        self.assertEqual(state,"exact_native_text_not_verified")

    def test_raw_json_and_definition_reports_are_counted_without_missing_values_becoming_locations(self):
        detail={"reports":[{"report":{"raw_json":'{"definition":[{"term":{"text":"x","start":0,"end":1},"defining_text":null,"confidence":0.9}]}'}}],
                "raw_reports":[{"raw_json":'{"entities":{"term":[{"text":"y","start":2,"end":3}]},"relation_extraction":{"defined_by":[]}}'}],
                "local_reports":[{"report":{"raw":{"role":[]}}}]}
        counts=raw_report_counts(detail)
        self.assertEqual(counts["raw_provider_report_count"],3)
        self.assertEqual(counts["raw_payload_encoding_counts"],{"raw_json":2,"raw_object":1})
        self.assertEqual(counts["raw_returned_group_field_state_counts"],
                         {"definition.term.located_shape":1,"definition.defining_text.null":1})
        self.assertEqual(counts["raw_entity_label_container_counts"],{"term":1})
        self.assertEqual(counts["raw_relation_label_container_counts"],{"defined_by":0})

    def test_native_group_without_projected_text_is_an_item_scope_not_foreign_source(self):
        view=source_fixture()
        view["native_context"]["items"].append({"self_ref":"#/groups/0","label":"section"})
        index,_=source_indices({1:view})
        anchor={"pin":{"product_key":"organized","product_digest":"d"*64},
                "space":"native","pointer":"#/groups/0","precision":"item"}
        observed,state=anchored_footprints(anchor,index)
        self.assertEqual(observed,[])
        self.assertEqual(state,"item_location_only_no_exact_text_extent")

    def test_verified_location_does_not_gain_semantic_support(self):
        index,by_ref=source_indices({1:source_fixture()})
        task={"selected_task_id":17,"origin_task_id":17,"method":"test-producer",
              "operation_version":"1","raw_file":"task17.json"}
        body={"outcome":"produced","records":[],"contribution_operations":[],
              "contributions":[{"contribution_id":"c1","kind":"occurrence",
                "semantic_type":"definition.term","standing":"retained_private",
                "anchors":[{"pin":{"product_key":"organized","product_digest":"d"*64},
                  "space":"native","pointer":"#/texts/0","start":0,"end":4,"source_piece":"same"}]}]}
        outputs,_,_=lower_task(task,body,index,by_ref)
        self.assertEqual(outputs[0]["direct_anchor_location_states"],["exact_native_text_verified"])
        self.assertEqual(outputs[0]["semantic_correctness"],"unassessed")


if __name__ == "__main__":
    unittest.main()
