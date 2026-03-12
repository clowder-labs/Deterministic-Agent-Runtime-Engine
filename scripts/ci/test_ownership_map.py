"""Test file -> responsible module ownership mapping.

Canonical source for test failure attribution. Used by:
- tests/conftest.py (pytest marker injection)
- scripts/ci/check_test_failure_ownership.py (failure attribution report)
"""

from __future__ import annotations

from pathlib import Path, PurePath


def is_pytest_discovery_file(path: str | Path | PurePath) -> bool:
    """Match pytest's default module filename patterns used by this repo."""
    name = PurePath(path).name
    return name.startswith("test_") or name.endswith("_test.py")

# Each entry: test_path (relative to repo root) -> { module, owner, tier }
# owner: responsible individual or team handle
OWNERSHIP_MAP: dict[str, dict[str, str]] = {
    # --- integration tests ---
    "tests/integration/test_client_cli_flow.py": {
        "module": "client",
        "owner": "lang",
        "tier": "integration",
    },
    "tests/integration/test_config_provider_reload.py": {
        "module": "dare_framework/config",
        "owner": "lang",
        "tier": "integration",
    },
    "tests/integration/test_example_agent_flow.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "integration",
    },
    "tests/integration/test_hook_governance_flow.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "integration",
    },
    "tests/integration/test_p0_conformance_gate.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "integration",
    },
    "tests/integration/test_security_policy_gate_flow.py": {
        "module": "dare_framework/security",
        "owner": "lang",
        "tier": "integration",
    },
    # --- smoke tests ---
    "tests/smoke/test_ci_smoke.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "smoke",
    },
    "tests/smoke/test_client_cli_smoke.py": {
        "module": "client",
        "owner": "lang",
        "tier": "smoke",
    },
    "tests/smoke/test_client_entrypoint_smoke.py": {
        "module": "client",
        "owner": "lang",
        "tier": "smoke",
    },
    # --- unit tests: a2a ---
    "tests/unit/test_a2a.py": {
        "module": "dare_framework/a2a",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: agent domain ---
    "tests/unit/test_agent_construction_contract.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_agent_event_transport_hook.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_agent_input_normalizer.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_agent_output_envelope.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_base_agent_transport_contract.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_component_managers.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_config_filtering.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_hook_ordering.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_manager_resolution.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_security_boundary.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_skill_tool_mode.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builder_tool_gateway.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_component_managers.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_hook_governance.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_hook_transport_boundary.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_mcp_management.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_orchestration_split.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_security_boundary.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_security_policy_gate.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_dare_agent_step_driven_mode.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_five_layer_agent.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_kernel_flow.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_output_normalizer.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_react_agent_gateway_injection.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_runtime_state.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_session_orchestrator_message_input.py": {
        "module": "dare_framework/agent",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: checkpoint ---
    "tests/unit/test_checkpoint_message_schema.py": {
        "module": "dare_framework/checkpoint",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: client ---
    "tests/unit/test_client_cli.py": {
        "module": "client",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_client_runtime_bootstrap.py": {
        "module": "client",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: config ---
    "tests/unit/test_config_action_handler.py": {
        "module": "dare_framework/config",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_config_model.py": {
        "module": "dare_framework/config",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_config_nonnull_guards.py": {
        "module": "dare_framework/config",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_config_provider.py": {
        "module": "dare_framework/config",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_layered_config_provider.py": {
        "module": "dare_framework/config",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: context ---
    "tests/unit/test_context_implementation.py": {
        "module": "dare_framework/context",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_context_message_types.py": {
        "module": "dare_framework/context",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: event ---
    "tests/unit/test_event_log.py": {
        "module": "dare_framework/event",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_event_sqlite_event_log.py": {
        "module": "dare_framework/event",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: examples ---
    "tests/unit/test_example_10_agentscope_compat.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_example_hook_governance.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_examples_04_cli.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_examples_cli.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_examples_cli_mcp.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_examples_with_tools.py": {
        "module": "examples",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: hook ---
    "tests/unit/test_hook_config_model.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_contract_types.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_decision_arbiter.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_extension_point_governance.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_legacy_adapter.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_metrics.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_patch_validator.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_phase_schema.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_runner.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_hook_selector.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_stdout_hook.py": {
        "module": "dare_framework/hook",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: governance / CI scripts ---
    "tests/unit/test_governance_evidence_truth_gate.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_governance_intent_gate.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_governance_traceability_gate.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_check_test_failure_ownership.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_conftest_ownership_markers.py": {
        "module": "tests",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_main_guard.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_manual_merge_guard.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_p0_gate_ci.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: interaction / transport ---
    "tests/unit/test_interaction_controls.py": {
        "module": "dare_framework/transport",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_interaction_dispatcher.py": {
        "module": "dare_framework/transport",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_transport_adapters.py": {
        "module": "dare_framework/transport",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_transport_channel.py": {
        "module": "dare_framework/transport",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_transport_typed_payloads.py": {
        "module": "dare_framework/transport",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_transport_types.py": {
        "module": "dare_framework/transport",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: mcp ---
    "tests/unit/test_mcp_action_handler.py": {
        "module": "dare_framework/mcp",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_mcp_client.py": {
        "module": "dare_framework/mcp",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_mcp_manager.py": {
        "module": "dare_framework/mcp",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_mcp_tool_provider.py": {
        "module": "dare_framework/mcp",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: memory ---
    "tests/unit/test_memory_knowledge_direct.py": {
        "module": "dare_framework/memory",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_embedding_openai_adapter.py": {
        "module": "dare_framework/memory",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: model ---
    "tests/unit/test_anthropic_model_adapter.py": {
        "module": "dare_framework/model",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_builtin_prompt_loader.py": {
        "module": "dare_framework/model",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_default_model_adapter_manager.py": {
        "module": "dare_framework/model",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_openai_model_adapter.py": {
        "module": "dare_framework/model",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_openrouter_adapter.py": {
        "module": "dare_framework/model",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_prompt_store.py": {
        "module": "dare_framework/model",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: observability ---
    "tests/unit/test_llm_io_capture_hook.py": {
        "module": "dare_framework/observability",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_observability.py": {
        "module": "dare_framework/observability",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: plan ---
    "tests/unit/test_composite_validator.py": {
        "module": "dare_framework/plan",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_default_planner.py": {
        "module": "dare_framework/plan",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_default_remediator.py": {
        "module": "dare_framework/plan",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_plan_v2_tools.py": {
        "module": "dare_framework/plan",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_registry_plan_validator.py": {
        "module": "dare_framework/plan",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: security ---
    "tests/unit/test_security_boundary.py": {
        "module": "dare_framework/security",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: skill ---
    "tests/unit/test_search_skill_tool.py": {
        "module": "dare_framework/skill",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_skill_store_builder.py": {
        "module": "dare_framework/skill",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: tool ---
    "tests/unit/test_execution_control.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_governed_tool_gateway.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_native_tool_provider.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_tool_approval_action_handler.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_tool_approval_manager.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_tool_gateway.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_tool_manager.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_tool_signature_contract.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_tool_types.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_v4_file_tools.py": {
        "module": "dare_framework/tool",
        "owner": "lang",
        "tier": "unit",
    },
    # --- unit tests: cross-cutting ---
    "tests/unit/test_llm_io_summary_script.py": {
        "module": "scripts",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_local_backend.py": {
        "module": "_local_backend",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_package_initializers_facade_pattern.py": {
        "module": "dare_framework",
        "owner": "lang",
        "tier": "unit",
    },
    "tests/unit/test_ownership_map_coverage.py": {
        "module": "scripts/ci",
        "owner": "lang",
        "tier": "unit",
    },
}


def get_entry(test_path: str) -> dict[str, str] | None:
    """Return the ownership entry for *test_path* (relative to repo root)."""
    return OWNERSHIP_MAP.get(test_path)


def modules_for_failures(failed_paths: list[str]) -> dict[str, list[str]]:
    """Group *failed_paths* by their responsible module.

    Returns ``{module: [test_path, ...]}``.  Unmapped paths are grouped
    under the key ``"UNMAPPED"``.
    """
    grouped: dict[str, list[str]] = {}
    for path in failed_paths:
        entry = OWNERSHIP_MAP.get(path)
        key = entry["module"] if entry else "UNMAPPED"
        grouped.setdefault(key, []).append(path)
    return grouped
