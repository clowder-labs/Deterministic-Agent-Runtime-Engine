#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="${GOVERNANCE_EVIDENCE_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT_DIR"

failures=0
governed_docs_count=0

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
    in_section && $0 ~ /^##[[:space:]]+/ {in_section=0}
    in_section {print}
  ' "$file"
}

extract_subsection() {
  local file="$1"
  local start_heading="$2"
  awk -v start="$start_heading" '
    $0 == start {in_section=1; next}
    in_section && $0 ~ /^###[[:space:]]+/ {in_section=0}
    in_section && $0 ~ /^##[[:space:]]+/ {in_section=0}
    in_section {print}
  ' "$file"
}

normalize_status() {
  local status="$1"
  tr '[:upper:]' '[:lower:]' <<<"$status" | tr '-' '_' | tr -d '[:space:]'
}

resolve_heading_line() {
  local file="$1"
  local pattern="$2"
  local label="$3"
  local heading
  heading="$(grep -Ei -- "$pattern" "$file" | head -n 1 || true)"
  if [[ -z "$heading" ]]; then
    log "missing $label in $file"
    failures=$((failures + 1))
  fi
  echo "$heading"
}

has_observability_na_fallback() {
  local section="$1"
  grep -Eiq '(none|n/a|n\.a)' <<<"$section" &&
    grep -Eiq '(reason|because|rationale)' <<<"$section" &&
    grep -Eiq '(fallback|evidence|commands|regression|verification)' <<<"$section"
}

extract_pr_number_for_marker() {
  local section="$1"
  local marker_pattern="$2"
  local marker_line pr_url
  marker_line="$(grep -Ei -- "$marker_pattern" <<<"$section" | head -n 1 || true)"
  pr_url="$(grep -Eo 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+' <<<"$marker_line" | head -n 1 || true)"
  if [[ -z "$pr_url" ]]; then
    echo ""
    return
  fi
  sed -E 's#.*/pull/([0-9]+)#\1#' <<<"$pr_url"
}

check_feature_doc() {
  local file="$1"
  local frontmatter status mode topic_slug
  local contract_section golden_section regression_section observability_section structured_review_section review_section
  local evidence_heading commands_heading results_heading contract_heading golden_heading regression_heading
  local observability_heading structured_review_heading behavior_heading risks_heading review_heading
  local openspec_heading intent_pr_number implementation_pr_number

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

  # Evidence requirements are enforced for active/in_review feature docs.
  local normalized_status
  normalized_status="$(normalize_status "$status")"
  if [[ "$normalized_status" != "active" && "$normalized_status" != "in_review" ]]; then
    log "skip non-governed feature doc $file (status=$status)"
    return
  fi

  governed_docs_count=$((governed_docs_count + 1))
  log "checking $file"

  evidence_heading="$(resolve_heading_line "$file" '^##[[:space:]]+Evidence([[:space:]]+Truth)?[[:space:]]*$' "Evidence section")"
  commands_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Commands|Command Log)[[:space:]]*$' "Commands subsection")"
  results_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Results|Result Summary)[[:space:]]*$' "Results subsection")"
  contract_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Contract Delta|Contract Changes?)[[:space:]]*$' "Contract Delta subsection")"
  golden_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Golden Cases?|Golden Files?)[[:space:]]*$' "Golden Cases subsection")"
  regression_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Regression Summary|Regression Results?)[[:space:]]*$' "Regression Summary subsection")"
  observability_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Observability( and Failure Localization)?|Failure Localization)[[:space:]]*$' "Observability and Failure Localization subsection")"
  structured_review_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Structured Review Report|Structured Review)[[:space:]]*$' "Structured Review Report subsection")"
  behavior_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Behavior Verification|Behavior Checks?)[[:space:]]*$' "Behavior Verification subsection")"
  risks_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Risks? and Rollback|Risk and Rollback)[[:space:]]*$' "Risks and Rollback subsection")"
  review_heading="$(resolve_heading_line "$file" '^###[[:space:]]+(Review and Merge Gate Links?|Review[[:space:]]*/[[:space:]]*Merge Gate Links?)[[:space:]]*$' "Review and Merge Gate Links subsection")"

  if [[ -n "$contract_heading" ]]; then
    contract_section="$(extract_subsection "$file" "$contract_heading")"
    if ! grep -Eiq 'schema' <<<"$contract_section"; then
      log "Contract Delta missing schema semantics in $file"
      failures=$((failures + 1))
    fi
    if ! grep -Eiq '(error[_[:space:]-]?code|error[_[:space:]-]?type|exception[_[:space:]-]?class|toolresult\.error|error semantics)' <<<"$contract_section"; then
      log "Contract Delta missing error semantics (error_code/error_type/exception_class/ToolResult.error) in $file"
      failures=$((failures + 1))
    fi
    if ! grep -Eiq 'retry' <<<"$contract_section"; then
      log "Contract Delta missing retry semantics in $file"
      failures=$((failures + 1))
    fi
  fi

  if [[ -n "$golden_heading" ]]; then
    golden_section="$(extract_subsection "$file" "$golden_heading")"
    if ! grep -Eq '`[^`]+`' <<<"$golden_section" && \
      ! grep -Eiq '(none|n/a).*(reason|because)' <<<"$golden_section"; then
      log "Golden Cases must list file names (extension optional) or explicit none-with-reason in $file"
      failures=$((failures + 1))
    fi
  fi

  if [[ -n "$regression_heading" ]]; then
    regression_section="$(extract_subsection "$file" "$regression_heading")"
    if ! grep -Eq '`[^`]+`' <<<"$regression_section"; then
      log "Regression Summary missing runner commands in $file"
      failures=$((failures + 1))
    fi
    if ! grep -Eiq '(pass|fail|skip)' <<<"$regression_section"; then
      log "Regression Summary missing pass/fail/skip summary in $file"
      failures=$((failures + 1))
    fi
  fi

  if [[ -n "$observability_heading" ]]; then
    observability_section="$(extract_subsection "$file" "$observability_heading")"
    if has_observability_na_fallback "$observability_section"; then
      log "Observability N/A accepted with reason + fallback evidence in $file"
    else
      for marker in start tool_call end fail; do
        if ! grep -Eiq "\\b${marker}\\b" <<<"$observability_section"; then
          log "Observability section missing '${marker}' marker in $file"
          failures=$((failures + 1))
        fi
      done
      for field in run_id tool_call_id capability_id attempt trace_id; do
        if ! grep -Eiq "\\b${field}\\b" <<<"$observability_section"; then
          log "Observability section missing locator field '${field}' in $file"
          failures=$((failures + 1))
        fi
      done
      if ! grep -Eiq '(error[_[:space:]-]?code|error[_[:space:]-]?type|exception[_[:space:]-]?class|toolresult\.error|error[[:space:]_-]?message)' <<<"$observability_section"; then
        log "Observability section missing error locator semantics (error_code/error_type/exception_class/ToolResult.error) in $file"
        failures=$((failures + 1))
      fi
    fi
  fi

  if [[ -n "$structured_review_heading" ]]; then
    structured_review_section="$(extract_subsection "$file" "$structured_review_heading")"
    for topic in \
      "Changed Module Boundaries / Public API" \
      "New State" \
      "Concurrency / Timeout / Retry" \
      "Side Effects and Idempotency" \
      "Coverage and Residual Risk"; do
      if ! grep -Eiq "$topic" <<<"$structured_review_section"; then
        log "Structured Review Report missing '${topic}' in $file"
        failures=$((failures + 1))
      fi
    done
  fi

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
  openspec_heading="$(grep -Ei '^##[[:space:]]+OpenSpec Artifacts[[:space:]]*$' "$file" | head -n 1 || true)"
  if [[ -n "$openspec_heading" ]]; then
    while IFS= read -r path; do
      if [[ -n "$path" ]]; then
        if [[ ! -f "$path" ]]; then
          log "unresolvable artifact path in $file: $path"
          failures=$((failures + 1))
        fi
      fi
    done < <(extract_section "$file" "$openspec_heading" | sed -n 's/.*`\([^`]*\)`.*/\1/p')
  fi

  # Require both intent/implementation links and at least one review link.
  if [[ -n "$review_heading" ]]; then
    review_section="$(extract_subsection "$file" "$review_heading")"
    if ! grep -Eiq 'intent[[:space:]_-]+pr' <<<"$review_section"; then
      log "missing Intent PR marker in $file"
      failures=$((failures + 1))
    fi
    if ! grep -Eiq 'implementation[[:space:]_-]+pr' <<<"$review_section"; then
      log "missing Implementation PR marker in $file"
      failures=$((failures + 1))
    fi

    local pr_link_count
    pr_link_count="$(grep -Eo 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+' <<<"$review_section" | wc -l | tr -d '[:space:]' || true)"
    if [[ "$pr_link_count" -lt 2 ]]; then
      log "missing required PR links (need >=2, got $pr_link_count) in $file"
      failures=$((failures + 1))
    fi
    if ! grep -Eq 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+#(pullrequestreview|issuecomment|discussion_r)' <<<"$review_section"; then
      log "missing GitHub PR review/merge link in $file"
      failures=$((failures + 1))
    fi

    intent_pr_number="$(extract_pr_number_for_marker "$review_section" 'intent[[:space:]_-]+pr')"
    implementation_pr_number="$(extract_pr_number_for_marker "$review_section" 'implementation[[:space:]_-]+pr')"
    if [[ -n "$intent_pr_number" && -n "$implementation_pr_number" && "$intent_pr_number" == "$implementation_pr_number" ]]; then
      log "Intent PR and Implementation PR must reference different pull requests in $file"
      failures=$((failures + 1))
    fi
    if [[ -n "$intent_pr_number" && -n "$implementation_pr_number" && "$intent_pr_number" -ge "$implementation_pr_number" ]]; then
      log "warning: intent PR number ($intent_pr_number) is not lower than implementation PR number ($implementation_pr_number) in $file; verify intent-merged-before-implementation manually"
    fi
  fi
}

feature_docs=()
while IFS= read -r path; do
  feature_docs+=("$path")
done < <(find docs/features -maxdepth 1 -type f -name '*.md' ! -name 'README.md' | sort)

if [[ ${#feature_docs[@]} -eq 0 ]]; then
  log "no feature aggregation docs found under docs/features/"
  failures=$((failures + 1))
fi

for file in "${feature_docs[@]}"; do
  check_feature_doc "$file"
done

if [[ $governed_docs_count -eq 0 ]]; then
  log "no governed docs in status active/in_review (supports in-review variant) under docs/features/"
  failures=$((failures + 1))
fi

if [[ $failures -gt 0 ]]; then
  log "failed with $failures issue(s)"
  exit 1
fi

log "passed"
