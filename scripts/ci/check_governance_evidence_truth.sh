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
    $0 ~ /^```/ {
      in_fence = !in_fence
      if (in_section) {
        print
      }
      next
    }
    !in_section && !in_fence && $0 == start {in_section=1; next}
    in_section && !in_fence && $0 ~ /^#[[:space:]]+/ {in_section=0}
    in_section && !in_fence && $0 ~ /^##[[:space:]]+/ {in_section=0}
    in_section {print}
  ' "$file"
}

extract_subsection() {
  local file="$1"
  local start_heading="$2"
  awk -v start="$start_heading" '
    $0 ~ /^```/ {
      in_fence = !in_fence
      if (in_section) {
        print
      }
      next
    }
    !in_section && !in_fence && $0 == start {in_section=1; next}
    in_section && !in_fence && $0 ~ /^###[[:space:]]+/ {in_section=0}
    in_section && !in_fence && $0 ~ /^##[[:space:]]+/ {in_section=0}
    in_section {print}
  ' "$file"
}

extract_subsection_from_section() {
  local section="$1"
  local start_heading="$2"
  awk -v start="$start_heading" '
    $0 ~ /^```/ {
      in_fence = !in_fence
      if (in_section) {
        print
      }
      next
    }
    !in_section && !in_fence && $0 == start {in_section=1; next}
    in_section && !in_fence && $0 ~ /^###[[:space:]]+/ {in_section=0}
    in_section {print}
  ' <<<"$section"
}

normalize_status() {
  local status="$1"
  tr '[:upper:]' '[:lower:]' <<<"$status" | tr '-' '_' | tr -d '[:space:]'
}

resolve_heading_line() {
  local file="$1"
  local pattern="$2"
  local heading
  heading="$(awk -v pattern="$pattern" '
    BEGIN { IGNORECASE = 1 }
    /^```/ { in_fence = !in_fence; next }
    !in_fence && $0 ~ pattern { print; exit }
  ' "$file" || true)"
  echo "$heading"
}

resolve_heading_in_section() {
  local section="$1"
  local pattern="$2"
  local heading
  heading="$(awk -v pattern="$pattern" '
    BEGIN { IGNORECASE = 1 }
    /^```/ { in_fence = !in_fence; next }
    !in_fence && $0 ~ pattern { print; exit }
  ' <<<"$section" || true)"
  echo "$heading"
}

require_heading_found() {
  local heading="$1"
  local label="$2"
  local context="$3"
  if [[ -z "$heading" ]]; then
    log "missing $label in $context"
    failures=$((failures + 1))
  fi
}

has_observability_na_fallback() {
  local section="$1"
  grep -Eiq '(^|[[:space:][:punct:]])(none|n/a|n\.a)([[:space:][:punct:]]|$)' <<<"$section" &&
    grep -Eiq '(reason|because|rationale)' <<<"$section" &&
    grep -Eiq '(fallback|evidence|commands|regression|verification)' <<<"$section"
}

is_placeholder_token() {
  local token="$1"
  local normalized
  normalized="$(tr '[:upper:]' '[:lower:]' <<<"$token" | tr -d '[:space:]')"
  [[ "$normalized" == "none" || "$normalized" == "n/a" || "$normalized" == "n.a" || "$normalized" == "na" || "$normalized" == "tbd" || "$normalized" == "todo" || "$normalized" == "placeholder" ]]
}

count_non_placeholder_backticked_tokens() {
  local section="$1"
  local count=0
  local token
  while IFS= read -r token; do
    if [[ -z "$token" ]]; then
      continue
    fi
    if ! is_placeholder_token "$token"; then
      count=$((count + 1))
    fi
  done < <(grep -Eo '`[^`]+`' <<<"$section" | sed -E 's/^`(.*)`$/\1/' || true)
  echo "$count"
}

is_file_like_token() {
  local token="$1"
  [[ "$token" =~ ^[A-Za-z0-9._/-]+$ ]] && [[ "$token" != */ ]] && [[ "$token" != -* ]]
}

is_known_single_command() {
  local token="$1"
  local normalized
  normalized="$(tr '[:upper:]' '[:lower:]' <<<"$token" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
  case "$normalized" in
  pytest | tox | nox | make | just | uv | uvx | poetry | pip | pipx | python | python3 | bash | sh | zsh | npm | pnpm | yarn | node | npx | go | cargo | ruff | mypy | coverage)
    return 0
    ;;
  esac
  return 1
}

count_file_like_backticked_tokens() {
  local section="$1"
  local count=0
  local token
  while IFS= read -r token; do
    if [[ -z "$token" ]]; then
      continue
    fi
    if is_placeholder_token "$token"; then
      continue
    fi
    if is_file_like_token "$token"; then
      count=$((count + 1))
    fi
  done < <(grep -Eo '`[^`]+`' <<<"$section" | sed -E 's/^`(.*)`$/\1/' || true)
  echo "$count"
}

is_command_like_token() {
  local token="$1"
  local normalized
  local words=()
  local idx cmd remainder
  local first_stage first_words=() first_idx first_cmd
  normalized="$(sed -E 's/^[[:space:]]+|[[:space:]]+$//g' <<<"$token")"
  if [[ -z "$normalized" ]]; then
    return 1
  fi
  if is_placeholder_token "$normalized"; then
    return 1
  fi

  if is_known_single_command "$normalized"; then
    return 0
  fi
  if grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=.*$' <<<"$normalized" && ! grep -Eq '[[:space:]]' <<<"$normalized"; then
    return 1
  fi

  if [[ "$normalized" == ./* || "$normalized" == /* ]]; then
    return 0
  fi

  # Parse shell-like tokens; skip env-assignment prefixes and require a plausible command shape.
  read -r -a words <<<"$normalized"
  idx=0
  while ((idx < ${#words[@]})); do
    if grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=.*$' <<<"${words[$idx]}"; then
      idx=$((idx + 1))
      continue
    fi
    break
  done

  if ((idx >= ${#words[@]})); then
    return 1
  fi

  cmd="${words[$idx]}"
  remainder="${normalized#*${cmd}}"
  remainder="$(sed -E 's/^[[:space:]]+//g' <<<"$remainder")"

  if is_known_single_command "$cmd" || [[ "$cmd" == ./* || "$cmd" == /* ]]; then
    return 0
  fi

  if grep -Eq '(^|[[:space:]])-[A-Za-z0-9-]+' <<<"$remainder"; then
    return 0
  fi
  if grep -Eq '[|&;]' <<<"$normalized"; then
    # For separator-based commands, require a concrete executable-like first command.
    first_stage="$(sed -E 's/[|&;].*$//' <<<"$normalized" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')"
    read -r -a first_words <<<"$first_stage"
    first_idx=0
    while ((first_idx < ${#first_words[@]})); do
      if grep -Eq '^[A-Za-z_][A-Za-z0-9_]*=.*$' <<<"${first_words[$first_idx]}"; then
        first_idx=$((first_idx + 1))
        continue
      fi
      break
    done

    if ((first_idx >= ${#first_words[@]})); then
      return 1
    fi
    first_cmd="${first_words[$first_idx]}"
    if is_known_single_command "$first_cmd" || [[ "$first_cmd" == ./* || "$first_cmd" == /* ]]; then
      return 0
    fi
    return 1
  fi

  return 1
}

is_candidate_regression_command_line() {
  local line="$1"
  if grep -Eiq '(runner|command)' <<<"$line"; then
    return 0
  fi
  # Accept unlabeled bullet commands like: - `pytest -q tests/...`
  if grep -Eq '^[[:space:]]*[-*]?[[:space:]]*`[^`]+`[[:space:]]*$' <<<"$line"; then
    return 0
  fi
  return 1
}

count_command_like_backticked_tokens() {
  local section="$1"
  local count=0
  local line token

  while IFS= read -r line; do
    if [[ -z "$line" ]]; then
      continue
    fi
    if ! is_candidate_regression_command_line "$line"; then
      continue
    fi
    while IFS= read -r token; do
      if [[ -z "$token" ]]; then
        continue
      fi
      if is_command_like_token "$token"; then
        count=$((count + 1))
      fi
    done < <(grep -Eo '`[^`]+`' <<<"$line" | sed -E 's/^`(.*)`$/\1/' || true)
  done <<<"$section"

  echo "$count"
}

dimension_uses_placeholder_value() {
  local section="$1"
  local dimension_pattern="$2"
  local line
  while IFS= read -r line; do
    if [[ -z "$line" ]]; then
      continue
    fi
    if grep -Eiq '(^|[[:space:][:punct:]])(tbd|todo|placeholder|unknown)([[:space:][:punct:]]|$)' <<<"$line"; then
      return 0
    fi
  done < <(grep -Ei -- "$dimension_pattern" <<<"$section" || true)
  return 1
}

dimension_none_without_reason() {
  local section="$1"
  local dimension_pattern="$2"
  local line
  while IFS= read -r line; do
    if [[ -z "$line" ]]; then
      continue
    fi
    if grep -Eiq '(^|[[:space:][:punct:]])(none|n/a|n\.a)([[:space:][:punct:]]|$)' <<<"$line" &&
      ! grep -Eiq '(reason|because|rationale)' <<<"$line"; then
      return 0
    fi
  done < <(grep -Ei -- "$dimension_pattern" <<<"$section" || true)
  return 1
}

extract_pr_number_for_marker() {
  local section="$1"
  local marker_pattern="$2"
  local pr_url
  pr_url="$(
    grep -Ei -- "$marker_pattern" <<<"$section" \
      | grep -Eo 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+' \
      | head -n 1 || true
  )"
  if [[ -z "$pr_url" ]]; then
    echo ""
    return
  fi
  sed -E 's#.*/pull/([0-9]+)#\1#' <<<"$pr_url"
}

check_feature_doc() {
  local file="$1"
  local frontmatter status mode topic_slug
  local strict_acceptance_pack
  local evidence_section
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

  strict_acceptance_pack="false"
  if [[ "$normalized_status" == "in_review" ]]; then
    strict_acceptance_pack="true"
  fi

  governed_docs_count=$((governed_docs_count + 1))
  log "checking $file (strict_acceptance_pack=$strict_acceptance_pack)"

  evidence_heading="$(resolve_heading_line "$file" '^##[[:space:]]+Evidence([[:space:]]+Truth)?[[:space:]]*$')"
  require_heading_found "$evidence_heading" "Evidence section" "$file"
  if [[ -n "$evidence_heading" ]]; then
    evidence_section="$(extract_section "$file" "$evidence_heading")"
  else
    evidence_section=""
  fi
  commands_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Commands|Command Log)[[:space:]]*$')"
  require_heading_found "$commands_heading" "Commands subsection" "Evidence section"
  results_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Results|Result Summary)[[:space:]]*$')"
  require_heading_found "$results_heading" "Results subsection" "Evidence section"
  behavior_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Behavior Verification|Behavior Checks?)[[:space:]]*$')"
  require_heading_found "$behavior_heading" "Behavior Verification subsection" "Evidence section"
  risks_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Risks? and Rollback|Risk and Rollback)[[:space:]]*$')"
  require_heading_found "$risks_heading" "Risks and Rollback subsection" "Evidence section"
  review_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Review and Merge Gate Links?|Review[[:space:]]*/[[:space:]]*Merge Gate Links?)[[:space:]]*$')"
  require_heading_found "$review_heading" "Review and Merge Gate Links subsection" "Evidence section"

  if [[ "$strict_acceptance_pack" == "true" ]]; then
    contract_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Contract Delta|Contract Changes?)[[:space:]]*$')"
    require_heading_found "$contract_heading" "Contract Delta subsection" "Evidence section"
    golden_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Golden Cases?|Golden Files?)[[:space:]]*$')"
    require_heading_found "$golden_heading" "Golden Cases subsection" "Evidence section"
    regression_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Regression Summary|Regression Results?)[[:space:]]*$')"
    require_heading_found "$regression_heading" "Regression Summary subsection" "Evidence section"
    observability_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Observability( and Failure Localization)?|Failure Localization)[[:space:]]*$')"
    require_heading_found "$observability_heading" "Observability and Failure Localization subsection" "Evidence section"
    structured_review_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Structured Review Report|Structured Review)[[:space:]]*$')"
    require_heading_found "$structured_review_heading" "Structured Review Report subsection" "Evidence section"
  else
    contract_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Contract Delta|Contract Changes?)[[:space:]]*$')"
    golden_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Golden Cases?|Golden Files?)[[:space:]]*$')"
    regression_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Regression Summary|Regression Results?)[[:space:]]*$')"
    observability_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Observability( and Failure Localization)?|Failure Localization)[[:space:]]*$')"
    structured_review_heading="$(resolve_heading_in_section "$evidence_section" '^###[[:space:]]+(Structured Review Report|Structured Review)[[:space:]]*$')"
  fi

  if [[ -n "$contract_heading" ]]; then
    contract_section="$(extract_subsection_from_section "$evidence_section" "$contract_heading")"
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
    if dimension_none_without_reason "$contract_section" 'schema'; then
      log "Contract Delta schema uses none/n.a without rationale in $file"
      failures=$((failures + 1))
    fi
    if dimension_uses_placeholder_value "$contract_section" 'schema'; then
      log "Contract Delta schema uses placeholder value in $file"
      failures=$((failures + 1))
    fi
    if dimension_none_without_reason "$contract_section" '(error[[:space:]_-]?semantics|error[_[:space:]-]?code|error[_[:space:]-]?type|exception[_[:space:]-]?class|toolresult\.error)'; then
      log "Contract Delta error semantics use none/n.a without rationale in $file"
      failures=$((failures + 1))
    fi
    if dimension_uses_placeholder_value "$contract_section" '(error[[:space:]_-]?semantics|error[_[:space:]-]?code|error[_[:space:]-]?type|exception[_[:space:]-]?class|toolresult\.error)'; then
      log "Contract Delta error semantics use placeholder value in $file"
      failures=$((failures + 1))
    fi
    if dimension_none_without_reason "$contract_section" 'retry'; then
      log "Contract Delta retry semantics use none/n.a without rationale in $file"
      failures=$((failures + 1))
    fi
    if dimension_uses_placeholder_value "$contract_section" 'retry'; then
      log "Contract Delta retry semantics use placeholder value in $file"
      failures=$((failures + 1))
    fi
  fi

  if [[ -n "$golden_heading" ]]; then
    golden_section="$(extract_subsection_from_section "$evidence_section" "$golden_heading")"
    local golden_tokens
    if [[ "$strict_acceptance_pack" == "true" ]]; then
      golden_tokens="$(count_file_like_backticked_tokens "$golden_section")"
    else
      golden_tokens="$(count_non_placeholder_backticked_tokens "$golden_section")"
    fi
    if [[ "$golden_tokens" -lt 1 ]] && ! grep -Eiq '(none|n/a).*(reason|because|rationale)' <<<"$golden_section"; then
      log "Golden Cases must list file names (extension optional) or explicit none-with-reason in $file"
      failures=$((failures + 1))
    fi
  fi

  if [[ -n "$regression_heading" ]]; then
    regression_section="$(extract_subsection_from_section "$evidence_section" "$regression_heading")"
    local regression_tokens
    local regression_summary_surface
    if [[ "$strict_acceptance_pack" == "true" ]]; then
      regression_tokens="$(count_command_like_backticked_tokens "$regression_section")"
    else
      regression_tokens="$(count_non_placeholder_backticked_tokens "$regression_section")"
    fi
    if [[ "$regression_tokens" -lt 1 ]]; then
      log "Regression Summary missing runner commands in $file"
      failures=$((failures + 1))
    fi
    # Summary tokens must come from prose summary, not from command snippets in backticks.
    regression_summary_surface="$(sed -E 's/`[^`]+`//g' <<<"$regression_section")"
    for summary_token in pass fail skip; do
      if ! grep -Eiq "\\b${summary_token}\\b" <<<"$regression_summary_surface"; then
        log "Regression Summary missing '${summary_token}' summary token in $file"
        failures=$((failures + 1))
      fi
    done
  fi

  if [[ -n "$observability_heading" ]]; then
    observability_section="$(extract_subsection_from_section "$evidence_section" "$observability_heading")"
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
      if ! grep -Eiq '(error[_[:space:]-]?code|error[_[:space:]-]?type|exception[_[:space:]-]?class|toolresult\.error)' <<<"$observability_section"; then
        log "Observability section missing error locator semantics (error_code/error_type/exception_class/ToolResult.error) in $file"
        failures=$((failures + 1))
      fi
    fi
  fi

  if [[ -n "$structured_review_heading" ]]; then
    structured_review_section="$(extract_subsection_from_section "$evidence_section" "$structured_review_heading")"
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
    review_section="$(extract_subsection_from_section "$evidence_section" "$review_heading")"
    local pr_link_count
    pr_link_count="$(grep -Eo 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+' <<<"$review_section" | wc -l | tr -d '[:space:]' || true)"
    if [[ "$pr_link_count" -lt 2 ]]; then
      log "missing required PR links (need >=2, got $pr_link_count) in $file"
      failures=$((failures + 1))
    fi
    if ! grep -Eq 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+#(pullrequestreview-[0-9]+|issuecomment-[0-9]+|discussion_r[0-9]+)' <<<"$review_section"; then
      log "missing GitHub PR review/merge link in $file"
      failures=$((failures + 1))
    fi

    if [[ "$strict_acceptance_pack" == "true" ]]; then
      if ! grep -Eiq 'intent[[:space:]_-]+pr' <<<"$review_section"; then
        log "missing Intent PR marker in $file"
        failures=$((failures + 1))
      fi
      if ! grep -Eiq 'implementation[[:space:]_-]+pr' <<<"$review_section"; then
        log "missing Implementation PR marker in $file"
        failures=$((failures + 1))
      fi

      intent_pr_number="$(extract_pr_number_for_marker "$review_section" 'intent[[:space:]_-]+pr')"
      implementation_pr_number="$(extract_pr_number_for_marker "$review_section" 'implementation[[:space:]_-]+pr')"
      if [[ -z "$intent_pr_number" ]]; then
        log "Intent PR marker must include a valid GitHub PR link in $file"
        failures=$((failures + 1))
      fi
      if [[ -z "$implementation_pr_number" ]]; then
        log "Implementation PR marker must include a valid GitHub PR link in $file"
        failures=$((failures + 1))
      fi
      if [[ -n "$intent_pr_number" && -n "$implementation_pr_number" && "$intent_pr_number" == "$implementation_pr_number" ]]; then
        log "Intent PR and Implementation PR must reference different pull requests in $file"
        failures=$((failures + 1))
      fi
      if [[ -n "$intent_pr_number" && -n "$implementation_pr_number" && "$intent_pr_number" -ge "$implementation_pr_number" ]]; then
        log "warning: intent PR number ($intent_pr_number) is not lower than implementation PR number ($implementation_pr_number) in $file; verify intent-merged-before-implementation manually"
      fi
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
