from dare_framework.hook._internal.hook_selector import (
    deduplicate_hook_specs,
    filter_hook_specs,
    sort_hook_specs,
)


def test_sort_order_is_phase_lane_priority_source_registration() -> None:
    ordered = sort_hook_specs(
        [
            {
                "phase": "before_tool",
                "lane": "observe",
                "priority": 100,
                "source": "code",
                "registration_order": 2,
            },
            {
                "phase": "before_tool",
                "lane": "control",
                "priority": 100,
                "source": "config",
                "registration_order": 1,
            },
        ]
    )
    assert ordered[0]["lane"] == "control"


def test_filter_matches_requested_phase() -> None:
    filtered = filter_hook_specs(
        [
            {"phase": "before_tool"},
            {"phase": "after_tool"},
        ],
        phase="before_tool",
    )
    assert filtered == [{"phase": "before_tool"}]


def test_deduplicate_uses_dedup_key() -> None:
    deduped = deduplicate_hook_specs(
        [
            {"dedup_key": "a", "registration_order": 1},
            {"dedup_key": "a", "registration_order": 2},
            {"dedup_key": "b", "registration_order": 3},
        ]
    )
    assert [item["dedup_key"] for item in deduped] == ["a", "b"]
