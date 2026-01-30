#!/usr/bin/env sh
# Example script for code-review skill. Echoes linter-style output.
# Usage: run_linter.sh [path]
# Args: path (optional) - directory or file to "lint"

PATH_ARG="${1:-.}"
echo "Linting: $PATH_ARG"
echo "  [OK] No issues found (example output)"
exit 0
