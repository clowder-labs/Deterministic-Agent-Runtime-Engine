#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

failures=0

if command -v rg >/dev/null 2>&1; then
  SEARCH_BIN="rg"
else
  SEARCH_BIN="grep"
fi

search_has_match() {
  local pattern="$1"
  shift
  if [[ "$SEARCH_BIN" == "rg" ]]; then
    rg -q -- "$pattern" "$@"
  else
    grep -Eq -- "$pattern" "$@"
  fi
}

search_list_matches() {
  local pattern="$1"
  shift
  if [[ "$SEARCH_BIN" == "rg" ]]; then
    rg -n -- "$pattern" "$@"
  else
    grep -En -- "$pattern" "$@"
  fi
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    echo "[design-doc-drift] missing required file: $path"
    failures=$((failures + 1))
  fi
}

require_pattern_in_file() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  if ! search_has_match "$pattern" "$file"; then
    echo "[design-doc-drift] missing required pattern ($label) in $file"
    failures=$((failures + 1))
  fi
}

reject_pattern_in_targets() {
  local pattern="$1"
  local label="$2"
  shift 2
  local targets=("$@")
  if search_list_matches "$pattern" "${targets[@]}" >/tmp/design-doc-drift-match.log 2>/dev/null; then
    echo "[design-doc-drift] stale claim detected ($label):"
    cat /tmp/design-doc-drift-match.log
    failures=$((failures + 1))
  fi
}

echo "[design-doc-drift] checking reconstructability governance files..."
require_file "docs/design/Design_Reconstructability_Traceability_Matrix.md"
require_file "docs/guides/Design_Reconstruction_SOP.md"

echo "[design-doc-drift] checking architecture links..."
require_pattern_in_file "Design_Reconstructability_Traceability_Matrix\\.md" "docs/design/Architecture.md" "traceability-matrix-link"
require_pattern_in_file "Design_Reconstruction_SOP\\.md" "docs/design/Architecture.md" "rebuild-sop-link"

echo "[design-doc-drift] checking module status labels..."
for file in docs/design/modules/*/README.md; do
  if ! search_has_match "## 能力状态（landed / partial / planned）" "$file"; then
    echo "[design-doc-drift] missing status labels section in $file"
    failures=$((failures + 1))
  fi
done

targets=(
  "docs/design/Architecture.md"
  "docs/design/DARE_Formal_Design.md"
  "docs/design/TODO_INDEX.md"
  "docs/design/modules/agent/README.md"
  "docs/design/modules/plan/README.md"
  "docs/design/modules/tool/README.md"
  "docs/design/modules/security/README.md"
)

echo "[design-doc-drift] checking stale claims..."
reject_pattern_in_targets "ValidatedPlan\\.steps 未驱动执行" "step-driven-stale-claim" "${targets[@]}"
reject_pattern_in_targets "SecurityBoundary 未接入" "security-not-integrated-stale-claim" "${targets[@]}"
reject_pattern_in_targets 'policy/hitl 未自动执行（`ISecurityBoundary` 未接入）' "tool-policy-stale-claim" "${targets[@]}"
reject_pattern_in_targets "仅接口定义，未接入主流程" "interface-only-stale-claim" "${targets[@]}"
reject_pattern_in_targets "接口已定义，默认实现缺失" "event-default-missing-stale-claim" "${targets[@]}"

if [[ "$failures" -gt 0 ]]; then
  echo "[design-doc-drift] failed with $failures issue(s)."
  exit 1
fi

echo "[design-doc-drift] passed."
