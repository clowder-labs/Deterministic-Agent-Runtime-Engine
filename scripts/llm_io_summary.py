#!/usr/bin/env python3
"""Summarize local LLM I/O JSONL traces captured by DARE hooks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make the repository importable when running the script directly.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dare_framework.observability._internal.llm_io_capture_hook import summarize_llm_io_trace


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-path",
        default="",
        help="Explicit JSONL trace file path.",
    )
    parser.add_argument(
        "--trace-dir",
        default=".dare/observability/llm_io",
        help="Directory containing *.llm_io.jsonl files.",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="Resolve trace file as <trace-dir>/<run-id>.llm_io.jsonl.",
    )
    parser.add_argument(
        "--show-calls",
        action="store_true",
        help="Print each model call with input/output preview.",
    )
    parser.add_argument(
        "--show-history",
        action="store_true",
        help="When used with --show-calls, include all user messages in each request.",
    )
    return parser


def _resolve_trace_paths(args: argparse.Namespace) -> list[Path]:
    if args.trace_path:
        return [Path(args.trace_path).expanduser()]

    trace_dir = Path(args.trace_dir).expanduser()
    if args.run_id:
        return [trace_dir / f"{args.run_id}.llm_io.jsonl"]

    candidates = sorted(
        trace_dir.glob("*.llm_io.jsonl"),
        key=lambda path: path.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(f"no trace files found in {trace_dir}")
    return candidates


def _load_records(trace_path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_line in trace_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def _latest_user_message(messages: Any) -> str:
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


def _all_user_messages(messages: Any) -> list[str]:
    if not isinstance(messages, list):
        return []
    result: list[str] = []
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            result.append(str(msg.get("content", "")))
    return result


def _preview(text: Any, *, max_chars: int = 140) -> str:
    value = str(text or "")
    compact = " ".join(value.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        trace_paths = _resolve_trace_paths(args)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    missing_paths = [path for path in trace_paths if not path.exists()]
    if missing_paths:
        print(f"Error: trace file not found: {missing_paths[0]}", file=sys.stderr)
        return 1

    aggregate = {
        "model_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "duration_ms": 0.0,
    }
    for trace_path in trace_paths:
        summary = summarize_llm_io_trace(trace_path)
        aggregate["model_calls"] += int(summary.get("model_calls", 0))
        aggregate["prompt_tokens"] += int(summary.get("prompt_tokens", 0))
        aggregate["completion_tokens"] += int(summary.get("completion_tokens", 0))
        aggregate["total_tokens"] += int(summary.get("total_tokens", 0))
        aggregate["duration_ms"] += float(summary.get("duration_ms", 0.0))

    if len(trace_paths) == 1:
        print(f"Trace: {trace_paths[0]}")
    else:
        print(f"Trace dir: {Path(args.trace_dir).expanduser()}")
        print(f"Trace files: {len(trace_paths)}")
    print(f"Model calls: {aggregate['model_calls']}")
    print(f"Prompt tokens: {aggregate['prompt_tokens']}")
    print(f"Completion tokens: {aggregate['completion_tokens']}")
    print(f"Total tokens: {aggregate['total_tokens']}")
    print(f"Total duration (ms): {aggregate['duration_ms']:.2f}")

    if args.show_calls:
        records: list[dict[str, Any]] = []
        for trace_path in trace_paths:
            records.extend(_load_records(trace_path))
        print("\nCalls:")
        for index, record in enumerate(records, start=1):
            iteration = record.get("iteration", index)
            request = record.get("request", {})
            response = record.get("response", {})
            messages = request.get("messages", []) if isinstance(request, dict) else []
            latest_user = _latest_user_message(messages)
            user_history = _all_user_messages(messages)
            output = response.get("content", "") if isinstance(response, dict) else ""
            usage = record.get("usage", {})
            total_tokens = usage.get("total_tokens", 0) if isinstance(usage, dict) else 0
            history_suffix = ""
            if args.show_history and user_history:
                history_suffix = f" history='{_preview(' || '.join(user_history))}'"
            print(
                f"- iter={iteration} tokens={total_tokens} "
                f"input='{_preview(latest_user)}' output='{_preview(output)}'{history_suffix}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
