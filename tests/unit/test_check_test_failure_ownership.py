import io
import subprocess

from scripts.ci import check_test_failure_ownership as module


def test_main_propagates_pytest_process_errors_without_failed_nodeids(
    monkeypatch, capsys
) -> None:
    def _fake_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["pytest"],
            returncode=4,
            stdout="",
            stderr="ERROR: usage: pytest [options] [file_or_dir] ...",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main([])

    captured = capsys.readouterr()
    assert exit_code == 4
    assert "ERROR: usage: pytest" in captured.err
    assert "No test failures detected." not in captured.out


def test_main_propagates_pytest_collection_errors_without_fake_failed_nodeid(
    monkeypatch, capsys
) -> None:
    def _fake_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["pytest"],
            returncode=2,
            stdout="ERROR collecting tests/unit/test_demo.py",
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main([])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ERROR collecting tests/unit/test_demo.py" in captured.err
    assert "FAILED collecting" not in captured.out


def test_main_propagates_pytest_file_level_errors_without_pseudo_nodeid(
    monkeypatch, capsys
) -> None:
    def _fake_run(*_args, **_kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["pytest"],
            returncode=2,
            stdout="ERROR tests/unit/test_tmp_collection_error.py",
            stderr="",
        )

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    exit_code = module.main([])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ERROR tests/unit/test_tmp_collection_error.py" in captured.err
    assert "FAILED tests/unit/test_tmp_collection_error.py" not in captured.out


def test_main_stdin_mode_returns_nonzero_for_collection_errors_without_failed_nodeids(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        module.sys,
        "stdin",
        io.StringIO("ERROR collecting tests/unit/test_demo.py"),
    )

    exit_code = module.main(["--stdin"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR collecting tests/unit/test_demo.py" in captured.err
    assert "No test failures detected." not in captured.out


def test_main_report_mode_returns_nonzero_for_usage_errors_without_failed_nodeids(
    tmp_path, capsys
) -> None:
    report_path = tmp_path / "pytest-output.txt"
    report_path.write_text(
        "ERROR: usage: pytest [options] [file_or_dir] ...",
        encoding="utf-8",
    )

    exit_code = module.main(["--report", str(report_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR: usage: pytest" in captured.err
    assert "No test failures detected." not in captured.out


def test_main_stdin_mode_returns_nonzero_for_keyboard_interrupt(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        module.sys,
        "stdin",
        io.StringIO("KeyboardInterrupt"),
    )

    exit_code = module.main(["--stdin"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "KeyboardInterrupt" in captured.err
    assert "No test failures detected." not in captured.out


def test_main_report_mode_returns_nonzero_when_no_tests_are_collected(
    tmp_path, capsys
) -> None:
    report_path = tmp_path / "pytest-output.txt"
    report_path.write_text(
        "no tests ran in 0.01s",
        encoding="utf-8",
    )

    exit_code = module.main(["--report", str(report_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "no tests ran in 0.01s" in captured.err
    assert "No test failures detected." not in captured.out


def test_parse_failed_lines_preserves_parametrized_nodeids_with_spaces() -> None:
    raw = "\n".join(
        [
            "FAILED tests/unit/test_demo.py::test_case[hello world] - AssertionError: boom",
            "ERROR tests/unit/test_demo.py::test_setup[hello world] - RuntimeError: boom",
        ]
    )

    assert module._parse_failed_lines(raw) == [
        "tests/unit/test_demo.py::test_case[hello world]",
        "tests/unit/test_demo.py::test_setup[hello world]",
    ]
