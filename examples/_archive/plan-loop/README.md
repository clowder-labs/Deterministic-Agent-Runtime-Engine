# Example: Plan Loop (Five-Layer)

This example demonstrates the canonical plan loop with a deterministic planner
and a registry-backed validator. It runs fully offline while exercising the
Plan -> Execute -> Tool flow using the built-in `EchoTool`.

## What It Shows

- **Plan Loop**: `EchoPlanner` emits a `ProposedPlan` with a tool step.
- **Plan Validation**: `RegistryPlanValidator` derives trusted metadata from
  the tool registry.
- **Execute + Tool Loop**: a deterministic model adapter emits one tool call
  then a final response to end the loop.

## Run

```bash
python examples/plan-loop/plan_loop.py
```

You should see the generated plan, followed by the final run result.

## Real Model Variant

This mirrors the model configuration conventions used in
`examples/base_tool/tool_chat3.4.py` and `examples/basic-chat/*`.

```bash
python examples/plan-loop/real_model_plan_loop.py
```

Environment variables:
- `CHAT_MODEL` (default: `gpt-4o-mini`)
- `CHAT_API_KEY`
- `CHAT_ENDPOINT` (default: `https://api.openai.com/v1`)
- `CHAT_LOG_LEVEL` (default: `INFO`)
- `TOOL_WORKSPACE_ROOT` (default: `.`)
- `PLAN_TASK` (default: `Read README.md and summarize the main purpose.`)
- `PLAN_DEFAULT_READ_PATH` (default: `README.md`)
- `PLAN_MAX_STEPS` (default: `3`)
