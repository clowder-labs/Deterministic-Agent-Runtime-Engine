#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

failures=0

log() {
  echo "[governance-evidence-truth] $*"
}

if command -v rg >/dev/null 2>&1; then
  SEARCH_BIN="rg"
else
  SEARCH_BIN="grep"
fi

search_has_match() {
  local pattern="$1"
  local file="$2"
  if [[ "$SEARCH_BIN" == "rg" ]]; then
    rg -q -- "$pattern" "$file"
  else
    grep -Eq -- "$pattern" "$file"
  fi
}

extract_frontmatter() {
  local file="$1"
  awk '
    NR == 1 && $0 == "---" {in_fm=1; next}
    in_fm && $0 == "---" {exit}
    in_fm {print}
  ' "$file"
}

frontmatter_scalar() {
  local block="$1"
  local key="$2"
  awk -v key="$key" '
    $0 ~ "^[[:space:]]*" key ":[[:space:]]*" {
      sub("^[[:space:]]*" key ":[[:space:]]*", "", $0)
      print
      exit
    }
  ' <<<"$block"
}

trim_quotes() {
  local value="$1"
  value="${value#\"}"
  value="${value%\"}"
  value="${value#\'}"
  value="${value%\'}"
  echo "$value"
}

frontmatter_has_change_ids() {
  local block="$1"
  if grep -Eq '^[[:space:]]*change_ids:[[:space:]]*\[[^]]+\][[:space:]]*$' <<<"$block"; then
    return 0
  fi

  # Support multiline YAML list form:
  # change_ids:
  #   - id-a
  #   - id-b
  awk '
    /^[[:space:]]*change_ids:[[:space:]]*$/ {in_list=1; next}
    in_list && /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*/ {in_list=0}
    in_list && /^[[:space:]]*-[[:space:]]*.+$/ {found=1}
    END {exit(found ? 0 : 1)}
  ' <<<"$block"
}

require_pattern() {
  local pattern="$1"
  local file="$2"
  local label="$3"
  if ! search_has_match "$pattern" "$file"; then
    log "missing $label in $file"
    failures=$((failures + 1))
  fi
}

extract_section() {
  local file="$1"
  local start_heading="$2"
  awk -v start="$start_heading" '
    $0 == start {in_section=1; next}
    in_section && $0 ~ /^## / {in_section=0}
    in_section {print}
  ' "$file"
}

extract_subsection() {
  local file="$1"
  local start_heading="$2"
  awk -v start="$start_heading" '
    $0 == start {in_section=1; next}
    in_section && $0 ~ /^### / {in_section=0}
    in_section && $0 ~ /^## / {in_section=0}
    in_section {print}
  ' "$file"
}

check_feature_doc() {
  local file="$1"
  local frontmatter status mode topic_slug

  frontmatter="$(extract_frontmatter "$file")"
  if [[ -z "$frontmatter" ]]; then
    log "missing frontmatter block in $file"
    failures=$((failures + 1))
    return
  fi

  status="$(trim_quotes "$(frontmatter_scalar "$frontmatter" "status")")"
  if [[ -z "$status" ]]; then
    log "missing status frontmatter in $file"
    failures=$((failures + 1))
    return
  fi

  # Evidence requirements are enforced for active feature docs only.
  if [[ "$status" != "active" ]]; then
    log "skip non-active feature doc $file (status=$status)"
    return
  fi

  log "checking $file"

  require_pattern "^## Evidence$" "$file" "Evidence section"
  require_pattern "^### Commands$" "$file" "Commands subsection"
  require_pattern "^### Results$" "$file" "Results subsection"
  require_pattern "^### Behavior Verification$" "$file" "Behavior Verification subsection"
  require_pattern "^### Risks and Rollback$" "$file" "Risks and Rollback subsection"
  require_pattern "^### Review and Merge Gate Links$" "$file" "Review and Merge Gate Links subsection"

  mode="$(trim_quotes "$(frontmatter_scalar "$frontmatter" "mode")")"
  if [[ "$mode" == "todo_fallback" ]]; then
    topic_slug="$(trim_quotes "$(frontmatter_scalar "$frontmatter" "topic_slug")")"
    if [[ -z "$topic_slug" ]]; then
      log "missing topic_slug frontmatter (fallback mode) in $file"
      failures=$((failures + 1))
    fi
  else
    if ! frontmatter_has_change_ids "$frontmatter"; then
      log "missing change_ids frontmatter (OpenSpec mode) in $file"
      failures=$((failures + 1))
    fi
  fi

  # Ensure OpenSpec artifact references are resolvable from repository root.
  while IFS= read -r path; do
    if [[ -n "$path" ]]; then
      if [[ ! -f "$path" ]]; then
        log "unresolvable artifact path in $file: $path"
        failures=$((failures + 1))
      fi
    fi
  done < <(extract_section "$file" "## OpenSpec Artifacts" | sed -n 's/.*`\([^`]*\)`.*/\1/p')

  # Require at least one GitHub PR link in review section.
  local review_section
  review_section="$(extract_subsection "$file" "### Review and Merge Gate Links")"
  if ! grep -Eq 'https://github\.com/.+/pull/[0-9]+' <<<"$review_section"; then
    log "missing GitHub PR review/merge link in $file"
    failures=$((failures + 1))
  fi
}

feature_docs=()
while IFS= read -r path; do
  feature_docs+=("$path")
done < <(find docs/features -maxdepth 1 -type f -name '*.md' ! -name 'README.md' | sort)

if [[ ${#feature_docs[@]} -eq 0 ]]; then
  log "no active feature aggregation docs found under docs/features/"
fi

for file in "${feature_docs[@]}"; do
  check_feature_doc "$file"
done

if [[ $failures -gt 0 ]]; then
  log "failed with $failures issue(s)"
  exit 1
fi

log "passed"
