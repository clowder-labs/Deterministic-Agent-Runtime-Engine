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
    echo "No comparable base commit found; skipping skip-marker check."
    exit 0
  fi
fi

PATTERN='^\+[^+].*(pytest\.mark\.(skip|skipif|xfail)|\.skip\(|\.only\()'
if git diff -U0 "${DIFF_RANGE}" -- '*.py' | rg -n "${PATTERN}"; then
  echo
  echo "Detected newly added skip/only/xfail markers in changed Python lines."
  echo "Please justify in PR risk section and get explicit reviewer approval."
  exit 1
fi

echo "No newly added skip/only/xfail markers detected."
