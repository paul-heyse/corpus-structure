"""Shared controlled inputs and builders for pdf inline reports support."""


def example():
    return dict(
        document={"pages": {"1": {"size": {"width": 200, "height": 300}}}},
        parent_task_id=2,
        parent_product_key="native",
        parent_digest="a" * 64,
        health={},
        inline_candidate_pages=[
            dict(
                page_no=1,
                has_words=True,
                has_chars=True,
                has_vectors=True,
                candidates=[
                    dict(
                        page_no=1,
                        text="",
                        left=27,
                        top=42,
                        right=30,
                        bottom=47,
                        origin="TOPLEFT",
                        basis="native-vector-gap-v1",
                    )
                ],
            )
        ],
        items=[
            dict(pointer="#/groups/0", label="section", content_layer="body"),
            dict(
                pointer="#/texts/0",
                label="text",
                content_layer="body",
                parent_pointer="#/groups/0",
                section_pointer="#/groups/0",
            ),
        ],
        regions=[
            dict(
                pointer="#/texts/0",
                page_no=1,
                left=26,
                top=40,
                right=66,
                bottom=60,
                origin="top_left",
            )
        ],
        recognition_coverage=[
            dict(
                section_pointer="#/groups/0",
                membership="direct",
                universe="inline",
                outcome="partial",
                policy="native-font-token-vector-ocr-word-v3",
            )
        ],
        inline_alignment_reports=[
            dict(
                page_no=1,
                candidate_index=0,
                item_pointers=["#/texts/0"],
                outcome="unresolved",
                basis="unmatched-native-text",
                detail="Native punctuation leaves correspondence unresolved.",
            )
        ],
    )
