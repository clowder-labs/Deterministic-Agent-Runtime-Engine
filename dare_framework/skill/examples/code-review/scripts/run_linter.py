#!/usr/bin/env python3
"""Example linter script for code-review skill. Portable across platforms."""
import sys
path_arg = sys.argv[1] if len(sys.argv) > 1 else "."
print(f"Linting: {path_arg}")
print("  [OK] No issues found (example output)")
sys.exit(0)
