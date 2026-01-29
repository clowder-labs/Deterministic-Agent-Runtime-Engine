#!/bin/bash
# Test script for interactive CLI

cd "$(dirname "$0")"

echo "Find all TODO comments" | PYTHONPATH=../.. python interactive_cli.py
