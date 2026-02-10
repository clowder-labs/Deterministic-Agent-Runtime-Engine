#!/usr/bin/env bash
set -euo pipefail

DIFF_RANGE=""
if [[ -n "${GITHUB_BASE_REF:-}" ]]; then
  git fetch --no-tags --depth=1 origin "${GITHUB_BASE_REF}" >/dev/null 2>&1 || true
  if git merge-base "origin/${GITHUB_BASE_REF}" HEAD >/dev/null 2>&1; then
    DIFF_RANGE="origin/${GITHUB_BASE_REF}...HEAD"
  else
    echo "No merge base with origin/${GITHUB_BASE_REF}; fallback to previous commit diff."
  fi
fi

if [[ -z "${DIFF_RANGE}" ]]; then
  if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    DIFF_RANGE="HEAD~1...HEAD"
  else
    echo "No comparable base commit found; skipping lockfile policy check."
    exit 0
  fi
fi

CHANGED_FILES="$(git diff --name-only "${DIFF_RANGE}")"
if [[ -z "${CHANGED_FILES}" ]]; then
  echo "No changed files; lockfile policy check skipped."
  exit 0
fi

LOCK_PATTERN='(^|/)(poetry\.lock|Pipfile\.lock|uv\.lock|requirements\.lock|package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$'
if ! printf '%s\n' "${CHANGED_FILES}" | rg -q "${LOCK_PATTERN}"; then
  echo "No lockfile changes detected."
  exit 0
fi

if printf '%s\n' "${CHANGED_FILES}" | rg -q '(^|/)(requirements\.txt|pyproject\.toml|package\.json)$'; then
  echo "Lockfile and dependency manifest changed together."
  exit 0
fi

echo "Lockfile changed without manifest update (requirements.txt/pyproject.toml/package.json)."
echo "Please update dependency manifest in the same PR or split the lockfile update."
exit 1
