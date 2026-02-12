from dare_framework.hook._internal.patch_validator import merge_patches


def test_patch_rejects_out_of_allowlist() -> None:
    result = merge_patches([{"tool_name": "bash"}], allowlist=("model_input",))
    assert result.error_code == "HOOK_CONTRACT_ERROR"


def test_patch_rejects_conflicting_mutations() -> None:
    result = merge_patches(
        [{"model_input": "a"}, {"model_input": "b"}],
        allowlist=("model_input",),
    )
    assert result.error_code == "HOOK_CONTRACT_ERROR"


def test_patch_merges_when_non_conflicting_and_allowlisted() -> None:
    result = merge_patches(
        [{"model_input": "a"}, {"context_patch": {"k": "v"}}],
        allowlist=("model_input", "context_patch"),
    )
    assert result.error_code is None
    assert result.patch == {"model_input": "a", "context_patch": {"k": "v"}}
