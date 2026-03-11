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
