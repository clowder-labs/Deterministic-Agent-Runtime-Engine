#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="${GOVERNANCE_TRACEABILITY_ROOT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT_DIR"

failures=0

log() {
  echo "[governance-traceability] $*"
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

frontmatter_list_items() {
  local block="$1"
  local key="$2"
  awk -v key="$key" '
    function emit_inline(value) {
      gsub(/^[[:space:]]*\[/, "", value)
      gsub(/\][[:space:]]*$/, "", value)
      n = split(value, parts, ",")
      for (i = 1; i <= n; i++) {
        item = parts[i]
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", item)
        gsub(/^"/, "", item)
        gsub(/"$/, "", item)
        gsub(/^'\''/, "", item)
        gsub(/'\''$/, "", item)
        if (item != "") {
          print item
        }
      }
    }

    $0 ~ "^[[:space:]]*" key ":[[:space:]]*\\[[^]]*\\][[:space:]]*$" {
      sub("^[[:space:]]*" key ":[[:space:]]*", "", $0)
      emit_inline($0)
      exit
    }

    $0 ~ "^[[:space:]]*" key ":[[:space:]]*$" {in_list=1; next}
    in_list && $0 ~ /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*:[[:space:]]*/ {exit}
    in_list && $0 ~ /^[[:space:]]*-[[:space:]]*/ {
      sub(/^[[:space:]]*-[[:space:]]*/, "", $0)
      gsub(/^"/, "", $0)
      gsub(/"$/, "", $0)
      gsub(/^'\''/, "", $0)
      gsub(/'\''$/, "", $0)
      print
    }
  ' <<<"$block"
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    log "missing $label: $path"
    failures=$((failures + 1))
  fi
}

require_line() {
  local needle="$1"
  local file="$2"
  local label="$3"
  if ! grep -Fq -- "$needle" "$file"; then
    log "missing $label in $file"
    failures=$((failures + 1))
  fi
}

require_section_line() {
  local needle="$1"
  local file="$2"
  local heading="$3"
  local label="$4"
  if ! grep -Fq -- "$needle" < <(extract_markdown_section "$file" "$heading"); then
    log "missing $label in $file"
    failures=$((failures + 1))
  fi
}

require_checkpoint_skill_pair() {
  local checkpoint="$1"
  local file="$2"
  local heading="$3"
  local skills_raw
  shift 3
  local IFS=$'\034'
  skills_raw="$*"

  if ! awk -v checkpoint="$checkpoint" -v skills="$skills_raw" -v heading="$heading" '
    function line_has_all_skills(line, skills_raw,    n, i, arr) {
      n = split(skills_raw, arr, "\034")
      for (i = 1; i <= n; i++) {
        if (arr[i] != "" && index(line, arr[i]) == 0) {
          return 0
        }
      }
      return 1
    }

    $0 == heading {in_section=1; next}
    in_section && /^##[[:space:]]+/ {exit}
    in_section && index($0, "- " checkpoint " ->") == 1 {
      if (line_has_all_skills($0, skills)) {
        found=1
        exit
      }
    }
    END {exit found ? 0 : 1}
  ' "$file"; then
    log "missing checkpoint-to-skill pair in $file"
    failures=$((failures + 1))
  fi
}

extract_markdown_section() {
  local file="$1"
  local heading="$2"
  awk -v heading="$heading" '
    $0 == heading {in_section=1; next}
    in_section && /^##[[:space:]]+/ {exit}
    in_section {print}
  ' "$file"
}

extract_markdown_section_matching() {
  local file="$1"
  local pattern="$2"
  awk -v pattern="$pattern" '
    $0 ~ /^##[[:space:]]+/ && $0 ~ pattern {in_section=1; next}
    in_section && /^##[[:space:]]+/ {exit}
    in_section {print}
  ' "$file"
}

escape_extended_regex() {
  printf '%s' "$1" | sed -E 's/[][(){}.^$*+?|\\/]/\\&/g'
}

file_has_discrete_token() {
  local file="$1"
  local token="$2"
  local escaped
  escaped="$(escape_extended_regex "$token")"
  grep -Eq "(^|[^A-Za-z0-9_-])${escaped}([^A-Za-z0-9_-]|$)" "$file"
}

text_has_discrete_token() {
  local text="$1"
  local token="$2"
  local escaped
  escaped="$(escape_extended_regex "$token")"
  grep -Eq "(^|[^A-Za-z0-9_-])${escaped}([^A-Za-z0-9_-]|$)" <<<"$text"
}

trim_whitespace() {
  sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//' <<<"$1"
}

normalize_scope_segment() {
  local segment="$1"
  segment="$(trim_whitespace "$segment")"
  sed -E 's/[[:space:]]*[（(].*$//' <<<"$segment"
}

todo_id_within_range() {
  local todo_id="$1"
  local range_start="$2"
  local range_end="$3"
  local todo_prefix todo_number start_prefix start_number end_prefix end_number

  if [[ ! "$todo_id" =~ ^([A-Za-z0-9]+)-([0-9]+)$ ]]; then
    return 1
  fi
  todo_prefix="${BASH_REMATCH[1]}"
  todo_number="${BASH_REMATCH[2]}"

  if [[ ! "$range_start" =~ ^([A-Za-z0-9]+)-([0-9]+)$ ]]; then
    return 1
  fi
  start_prefix="${BASH_REMATCH[1]}"
  start_number="${BASH_REMATCH[2]}"

  if [[ ! "$range_end" =~ ^([A-Za-z0-9]+)-([0-9]+)$ ]]; then
    return 1
  fi
  end_prefix="${BASH_REMATCH[1]}"
  end_number="${BASH_REMATCH[2]}"

  if [[ "$todo_prefix" != "$start_prefix" || "$start_prefix" != "$end_prefix" ]]; then
    return 1
  fi

  (( 10#$todo_number >= 10#$start_number && 10#$todo_number <= 10#$end_number ))
}

scope_contains_todo_id() {
  local scope="$1"
  local todo_id="$2"
  local segment range_start range_end

  while IFS= read -r segment; do
    segment="$(normalize_scope_segment "$segment")"
    [[ -z "$segment" ]] && continue
    if [[ "$segment" == "$todo_id" ]]; then
      return 0
    fi
    if [[ "$segment" == *"~"* ]]; then
      range_start="$(trim_whitespace "${segment%%~*}")"
      range_end="$(trim_whitespace "${segment##*~}")"
      if todo_id_within_range "$todo_id" "$range_start" "$range_end"; then
        return 0
      fi
    fi
  done < <(tr ',' '\n' <<<"$scope")

  return 1
}

section_has_index_entry() {
  local index_file="$1"
  local section_heading="$2"
  local path="$3"
  grep -Fq -- "\`$path\`" < <(extract_markdown_section "$index_file" "$section_heading")
}

claim_ledger_has_tokens_in_same_record() {
  local file="$1"
  local first_token="$2"
  local second_token="$3"
  local line scope_field

  while IFS= read -r line; do
    [[ "$line" == \|* ]] || continue
    if ! text_has_discrete_token "$line" "$second_token"; then
      continue
    fi
    if text_has_discrete_token "$line" "$first_token"; then
      return 0
    fi
    scope_field="$(awk -F'|' 'NF >= 4 {field=$3; gsub(/^[[:space:]]+|[[:space:]]+$/, "", field); print field}' <<<"$line")"
    if [[ -n "$scope_field" ]] && scope_contains_todo_id "$scope_field" "$first_token"; then
      return 0
    fi
  done < <(extract_markdown_section_matching "$file" "Claim Ledger")

  return 1
}

check_index_entry_targets() {
  local index_file="$1"
  local section_heading="$2"
  local stale_label="$3"
  local valid_regex="$4"
  local invalid_regex="$5"
  local path basename

  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    if [[ ! -f "$path" ]]; then
      log "stale $stale_label index entry in $index_file: $path"
      failures=$((failures + 1))
      continue
    fi
    if [[ -n "$invalid_regex" && "$path" =~ $invalid_regex ]]; then
      log "invalid $stale_label index entry path in $index_file: $path"
      failures=$((failures + 1))
      continue
    fi
    basename="${path##*/}"
    if [[ "$basename" == "README.md" ]]; then
      log "invalid $stale_label index entry path in $index_file: $path"
      failures=$((failures + 1))
      continue
    fi
    if [[ ! "$path" =~ $valid_regex ]]; then
      log "invalid $stale_label index entry path in $index_file: $path"
      failures=$((failures + 1))
    fi
  done < <(
    extract_markdown_section "$index_file" "$section_heading" \
      | sed -n 's/.*`\([^`]*\)`.*/\1/p'
  )
}

check_feature_indexes() {
  local active_index="docs/features/README.md"
  local archive_index="docs/features/archive/README.md"
  local template="docs/features/templates/feature_aggregation_template.md"
  local file

  require_file "$active_index" "active feature index"
  require_file "$archive_index" "feature archive index"
  require_file "$template" "feature aggregation template"

  if [[ -f "$active_index" ]]; then
    require_line "docs/features/templates/feature_aggregation_template.md" "$active_index" "template link"
    require_line "docs/features/archive/README.md" "$active_index" "archive index link"
    require_line "## Active Entries" "$active_index" "Active Entries section"
    require_line "## Migration Rules" "$active_index" "Migration Rules section"
  fi

  if [[ -f "$archive_index" ]]; then
    require_line "## Archived Entries" "$archive_index" "Archived Entries section"
    require_line "## Archive Migration Rules" "$archive_index" "Archive Migration Rules section"
  fi

  while IFS= read -r file; do
    if ! section_has_index_entry "$active_index" "## Active Entries" "$file"; then
      log "missing active feature index entry for $file"
      failures=$((failures + 1))
    fi
  done < <(find docs/features -maxdepth 1 -type f -name '*.md' ! -name 'README.md' | sort)

  while IFS= read -r file; do
    if ! section_has_index_entry "$archive_index" "## Archived Entries" "$file"; then
      log "missing archived feature index entry for $file"
      failures=$((failures + 1))
    fi
  done < <(find docs/features/archive -maxdepth 1 -type f -name '*.md' ! -name 'README.md' | sort)

  check_index_entry_targets "$active_index" "## Active Entries" "active feature" '^docs/features/[^/]+\.md$' '^docs/features/archive/'
  check_index_entry_targets "$archive_index" "## Archived Entries" "archived feature" '^docs/features/archive/[^/]+\.md$' ""
}

check_checkpoint_skill_mapping() {
  local model="docs/governance/Documentation_Management_Model.md"

  require_file "$model" "documentation management model"
  require_file ".codex/skills/documentation-management/SKILL.md" "documentation-management skill"
  require_file ".codex/skills/development-workflow/SKILL.md" "development-workflow skill"

  if [[ -f "$model" ]]; then
    require_line "## 7. Checkpoint-to-Skill Mapping" "$model" "checkpoint-to-skill mapping"
    require_line "documentation-management" "$model" "documentation-management mapping"
    require_line "development-workflow" "$model" "development-workflow mapping"
    require_line "kickoff" "$model" "kickoff checkpoint"
    require_line "execution-sync" "$model" "execution-sync checkpoint"
    require_line "verification" "$model" "verification checkpoint"
    require_line "review-merge-gate" "$model" "review-merge-gate checkpoint"
    require_line "completion-archive" "$model" "completion-archive checkpoint"
    require_checkpoint_skill_pair "kickoff" "$model" "## 7. Checkpoint-to-Skill Mapping" '`development-workflow`' '`documentation-management`'
    require_checkpoint_skill_pair "execution-sync" "$model" "## 7. Checkpoint-to-Skill Mapping" '`development-workflow`' '`documentation-management`'
    require_checkpoint_skill_pair "verification" "$model" "## 7. Checkpoint-to-Skill Mapping" '`development-workflow`'
    require_checkpoint_skill_pair "review-merge-gate" "$model" "## 7. Checkpoint-to-Skill Mapping" '`development-workflow`' '`documentation-management`'
    require_checkpoint_skill_pair "completion-archive" "$model" "## 7. Checkpoint-to-Skill Mapping" '`development-workflow`' '`documentation-management`'
  fi
}

check_feature_doc() {
  local file="$1"
  local frontmatter mode doc_kind key change_id todo_id matched candidate
  local change_ids_raw todo_ids_raw

  frontmatter="$(extract_frontmatter "$file")"
  if [[ -z "$frontmatter" ]]; then
    log "missing frontmatter in $file"
    failures=$((failures + 1))
    return
  fi

  for key in doc_kind topics created updated status mode; do
    if [[ -z "$(frontmatter_scalar "$frontmatter" "$key")" ]]; then
      log "missing required frontmatter field '$key' in $file"
      failures=$((failures + 1))
    fi
  done

  doc_kind="$(trim_quotes "$(frontmatter_scalar "$frontmatter" "doc_kind")")"
  if [[ "$doc_kind" != "feature" ]]; then
    log "feature aggregation doc must declare doc_kind: feature in $file"
    failures=$((failures + 1))
  fi

  mode="$(trim_quotes "$(frontmatter_scalar "$frontmatter" "mode")")"
  if [[ "$mode" == "todo_fallback" ]]; then
    if [[ -z "$(frontmatter_scalar "$frontmatter" "topic_slug")" ]]; then
      log "missing required frontmatter field 'topic_slug' in $file"
      failures=$((failures + 1))
    fi
    return
  fi

  change_ids_raw="$(frontmatter_list_items "$frontmatter" "change_ids")"
  if [[ -z "$change_ids_raw" ]]; then
    log "missing required frontmatter field 'change_ids' in $file"
    failures=$((failures + 1))
    return
  fi

  while IFS= read -r change_id; do
    [[ -z "$change_id" ]] && continue
    if [[ ! -f "openspec/changes/$change_id/tasks.md" ]] && \
      ! find openspec/changes/archive -type f \( -path "*/$change_id/tasks.md" -o -path "*/????-??-??-$change_id/tasks.md" \) | grep -q .; then
      log "missing OpenSpec tasks artifact for change_id '$change_id' declared in $file"
      failures=$((failures + 1))
    fi
  done <<<"$change_ids_raw"

  todo_ids_raw="$(frontmatter_list_items "$frontmatter" "todo_ids")"
  if [[ -z "$todo_ids_raw" ]]; then
    return
  fi

  while IFS= read -r todo_id; do
    [[ -z "$todo_id" ]] && continue
    matched=0
    while IFS= read -r candidate; do
      [[ -z "$candidate" ]] && continue
      while IFS= read -r change_id; do
        [[ -z "$change_id" ]] && continue
        if claim_ledger_has_tokens_in_same_record "$candidate" "$todo_id" "$change_id"; then
          matched=1
          break
        fi
      done <<<"$change_ids_raw"
      if [[ "$matched" -eq 1 ]]; then
        break
      fi
    done < <(find docs/todos -type f -name '*.md' | sort)

    if [[ "$matched" -eq 0 ]]; then
      log "missing TODO mapping for feature doc $file: $todo_id"
      failures=$((failures + 1))
    fi
  done <<<"$todo_ids_raw"
}

check_feature_indexes
check_checkpoint_skill_mapping

while IFS= read -r file; do
  check_feature_doc "$file"
done < <(find docs/features -maxdepth 1 -type f -name '*.md' ! -name 'README.md' | sort)

if [[ $failures -gt 0 ]]; then
  log "failed with $failures issue(s)"
  exit 1
fi

log "passed"
