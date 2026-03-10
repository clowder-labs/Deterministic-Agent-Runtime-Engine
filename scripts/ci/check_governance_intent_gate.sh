#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="${GOVERNANCE_INTENT_GATE_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT_DIR"

failures=0
RESOLVED_PR_STATE=""

log() {
  echo "[governance-intent-gate] $*"
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

normalize_status() {
  local status="$1"
  tr '[:upper:]' '[:lower:]' <<<"$status" | tr '-' '_' | tr -d '[:space:]'
}

is_governance_only_path() {
  local path="$1"
  case "$path" in
  docs/* | openspec/* | .codex/*)
    return 0
    ;;
  .github/workflows/*)
    return 0
    ;;
  scripts/ci/check_governance_*.sh)
    return 0
    ;;
  tests/unit/test_governance_*.py)
    return 0
    ;;
  AGENTS.md | README.md)
    return 0
    ;;
  esac
  return 1
}

resolve_diff_range() {
  local diff_range=""

  if [[ -n "${GOVERNANCE_INTENT_GATE_DIFF_RANGE:-}" ]]; then
    echo "${GOVERNANCE_INTENT_GATE_DIFF_RANGE}"
    return
  fi

  if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
    git fetch --no-tags --depth=1 origin "${GITHUB_BASE_REF}" >/dev/null 2>&1 || true
    if git merge-base "origin/${GITHUB_BASE_REF}" HEAD >/dev/null 2>&1; then
      diff_range="origin/${GITHUB_BASE_REF}...HEAD"
    else
      log "No merge base with origin/${GITHUB_BASE_REF}; fallback to previous commit diff."
    fi
  fi

  if [[ -z "$diff_range" ]]; then
    if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
      diff_range="HEAD~1...HEAD"
    fi
  fi

  echo "$diff_range"
}

resolve_changed_files() {
  # Test harness can inject deterministic changed-file sets without a git history.
  if [[ -n "${GOVERNANCE_INTENT_GATE_CHANGED_FILES:-}" ]]; then
    printf '%s\n' "${GOVERNANCE_INTENT_GATE_CHANGED_FILES}" | sed '/^[[:space:]]*$/d'
    return
  fi

  local diff_range
  diff_range="$(resolve_diff_range)"
  if [[ -z "$diff_range" ]]; then
    echo ""
    return
  fi

  git diff --name-only "$diff_range" | sed '/^[[:space:]]*$/d'
}

extract_intent_pr_url() {
  local file="$1"
  local review_links_section
  review_links_section="$(awk '
    $0 ~ /^```/ {
      in_fence = !in_fence
      if (in_section) {
        print
      }
      next
    }
    !in_section && !in_fence && $0 ~ /^###[[:space:]]+(Review and Merge Gate Links?|Review[[:space:]]*\/[[:space:]]*Merge Gate Links?)[[:space:]]*$/ {in_section=1; next}
    in_section && !in_fence && $0 ~ /^###[[:space:]]+/ {exit}
    in_section && !in_fence && $0 ~ /^##[[:space:]]+/ {exit}
    in_section {print}
  ' "$file")"

  grep -Ei '^[[:space:]]*-[[:space:]]*Intent[[:space:]_-]+PR[[:space:]]*:' <<<"$review_links_section" \
    | grep -Eo 'https://github\.com/[^/[:space:]]+/[^/[:space:]]+/pull/[0-9]+' \
    | head -n 1 || true
}

parse_pr_components() {
  local pr_url="$1"
  if [[ "$pr_url" =~ ^https://github\.com/([^/]+)/([^/]+)/pull/([0-9]+)$ ]]; then
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
    return 0
  fi
  return 1
}

lookup_pr_state_fixture() {
  local owner="$1"
  local repo="$2"
  local pr_number="$3"
  local key="$owner/$repo#$pr_number"
  local fixture="${GOVERNANCE_INTENT_GATE_PR_STATE_FIXTURE:-}"
  local entry clean k v

  [[ -z "$fixture" ]] && return 1

  while IFS= read -r entry; do
    clean="$(tr -d '[:space:]' <<<"$entry")"
    [[ -z "$clean" ]] && continue
    if [[ "$clean" != *=* ]]; then
      continue
    fi
    k="${clean%%=*}"
    v="${clean#*=}"
    if [[ "$k" == "$key" ]]; then
      echo "$v"
      return 0
    fi
  done < <(tr ',;' '\n\n' <<<"$fixture")

  return 1
}

resolve_pr_state() {
  local owner="$1"
  local repo="$2"
  local pr_number="$3"
  local fixture_state payload api_url

  RESOLVED_PR_STATE=""

  # Unit tests can short-circuit remote calls with explicit fixture states.
  if fixture_state="$(lookup_pr_state_fixture "$owner" "$repo" "$pr_number")"; then
    RESOLVED_PR_STATE="$fixture_state"
    return 0
  fi

  if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    log "missing GITHUB_TOKEN for PR state lookup: $owner/$repo#$pr_number"
    return 2
  fi

  api_url="https://api.github.com/repos/$owner/$repo/pulls/$pr_number"
  if ! payload="$(curl -fsSL \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    "$api_url" 2>/dev/null)"; then
    log "failed to query PR state from GitHub API: $owner/$repo#$pr_number"
    return 2
  fi

  if grep -Eq '"merged":[[:space:]]*true' <<<"$payload"; then
    RESOLVED_PR_STATE="merged"
    return 0
  fi

  if grep -Eq '"merged":[[:space:]]*false' <<<"$payload"; then
    RESOLVED_PR_STATE="open"
    return 0
  fi

  log "unable to parse merged state from GitHub API for $owner/$repo#$pr_number"
  return 2
}

main() {
  local changed_files
  changed_files="$(resolve_changed_files)"
  if [[ -z "$changed_files" ]]; then
    log "No changed files detected; skip intent gate."
    exit 0
  fi

  local implementation_changed="false"
  local -a changed_feature_docs=()
  local path
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    if [[ "$path" =~ ^docs/features/[^/]+\.md$ ]] && [[ "$path" != "docs/features/README.md" ]]; then
      changed_feature_docs+=("$path")
    fi
    if ! is_governance_only_path "$path"; then
      implementation_changed="true"
    fi
  done <<<"$changed_files"

  if [[ "$implementation_changed" != "true" ]]; then
    log "No implementation-path changes detected; intent gate skipped."
    exit 0
  fi

  local -a governed_feature_docs=()
  local doc frontmatter status normalized_status
  if [[ ${#changed_feature_docs[@]} -eq 0 ]]; then
    log "implementation changes detected but PR must update at least one governed feature doc under docs/features/*.md"
    failures=$((failures + 1))
  else
    for doc in "${changed_feature_docs[@]}"; do
      if [[ ! -f "$doc" ]]; then
        log "changed governed feature doc is missing in workspace: $doc"
        failures=$((failures + 1))
        continue
      fi

      frontmatter="$(extract_frontmatter "$doc")"
      status="$(trim_quotes "$(frontmatter_scalar "$frontmatter" "status")")"
      normalized_status="$(normalize_status "$status")"
      if [[ "$normalized_status" == "active" || "$normalized_status" == "in_review" ]]; then
        governed_feature_docs+=("$doc")
      fi
    done

    if [[ ${#governed_feature_docs[@]} -eq 0 ]]; then
      log "implementation changes detected but PR must update at least one governed feature doc (status active/in_review)"
      failures=$((failures + 1))
    else
      local intent_pr_url components owner repo pr_number pr_state
      for doc in "${governed_feature_docs[@]}"; do
        intent_pr_url="$(extract_intent_pr_url "$doc")"
        if [[ -z "$intent_pr_url" ]]; then
          log "missing Intent PR link in $doc"
          failures=$((failures + 1))
          continue
        fi

        if ! components="$(parse_pr_components "$intent_pr_url")"; then
          log "invalid Intent PR link format in $doc: $intent_pr_url"
          failures=$((failures + 1))
          continue
        fi

        read -r owner repo pr_number <<<"$components"
        if ! resolve_pr_state "$owner" "$repo" "$pr_number"; then
          failures=$((failures + 1))
          continue
        fi
        pr_state="$RESOLVED_PR_STATE"

        if [[ "$pr_state" != "merged" ]]; then
          log "Intent PR $intent_pr_url is not merged (state=$pr_state)"
          failures=$((failures + 1))
          continue
        fi

        log "validated merged Intent PR for $doc: $intent_pr_url"
      done
    fi
  fi

  if [[ $failures -gt 0 ]]; then
    log "failed with $failures issue(s)"
    exit 1
  fi

  log "passed"
}

main "$@"
