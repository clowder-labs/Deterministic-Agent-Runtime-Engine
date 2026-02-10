#!/usr/bin/env bash
set -euo pipefail

# Keep this suite small and stable: auth, channel concurrency/backpressure,
# and execution-control behavior are the highest-leverage regression sentinels.
pytest -q \
  tests/unit/test_a2a.py \
  tests/unit/test_transport_channel.py \
  tests/unit/test_execution_control.py
