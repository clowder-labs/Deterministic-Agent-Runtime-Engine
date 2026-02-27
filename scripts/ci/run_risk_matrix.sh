#!/usr/bin/env bash
set -euo pipefail

# Keep this suite small and stable: auth, channel concurrency/backpressure,
# execution-control, and security gate behavior are the highest-leverage
# regression sentinels.
pytest -q \
  tests/unit/test_a2a.py \
  tests/unit/test_transport_channel.py \
  tests/unit/test_execution_control.py \
  tests/unit/test_security_boundary.py \
  tests/unit/test_governed_tool_gateway.py \
  tests/unit/test_dare_agent_security_policy_gate.py \
  tests/integration/test_security_policy_gate_flow.py
