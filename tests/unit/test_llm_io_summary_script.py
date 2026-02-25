from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType


def _load_script_module() -> ModuleType:
    root = Path(__file__).resolve().parents[2]
    script_path = root / "scripts" / "llm_io_summary.py"
    module_name = "scripts_llm_io_summary_test"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _write_trace(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")


def test_summary_defaults_to_aggregating_all_trace_files(tmp_path: Path, capsys) -> None:
    module = _load_script_module()
    trace_dir = tmp_path / "llm_io"
    _write_trace(
        trace_dir / "run-1.llm_io.jsonl",
        {
            "iteration": 1,
            "request": {"messages": [{"role": "user", "content": "hello"}]},
            "response": {"content": "hi"},
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            "duration_ms": 10.0,
        },
    )
    _write_trace(
        trace_dir / "run-2.llm_io.jsonl",
        {
            "iteration": 1,
            "request": {"messages": [{"role": "user", "content": "who are you"}]},
            "response": {"content": "i am an assistant"},
            "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
            "duration_ms": 12.0,
        },
    )

    exit_code = module.main(["--trace-dir", str(trace_dir)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Model calls: 2" in output
    assert "Prompt tokens: 7" in output
    assert "Completion tokens: 5" in output
    assert "Total tokens: 12" in output


def test_show_calls_uses_latest_user_message(tmp_path: Path, capsys) -> None:
    module = _load_script_module()
    trace_dir = tmp_path / "llm_io"
    _write_trace(
        trace_dir / "run-1.llm_io.jsonl",
        {
            "iteration": 1,
            "request": {
                "messages": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi"},
                    {"role": "user", "content": "who are you"},
                ]
            },
            "response": {"content": "i am an assistant"},
            "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
            "duration_ms": 12.0,
        },
    )

    exit_code = module.main(["--trace-dir", str(trace_dir), "--show-calls"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "input='who are you'" in output


def test_show_calls_can_include_user_history(tmp_path: Path, capsys) -> None:
    module = _load_script_module()
    trace_dir = tmp_path / "llm_io"
    _write_trace(
        trace_dir / "run-1.llm_io.jsonl",
        {
            "iteration": 1,
            "request": {
                "messages": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "hi"},
                    {"role": "user", "content": "who are you"},
                ]
            },
            "response": {"content": "i am an assistant"},
            "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
            "duration_ms": 12.0,
        },
    )

    exit_code = module.main(["--trace-dir", str(trace_dir), "--show-calls", "--show-history"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "history='hello || who are you'" in output
