from __future__ import annotations

import importlib
import tarfile
import zipfile
from pathlib import Path


def test_local_backend_build_editable_contains_pth_and_entry_points(tmp_path: Path) -> None:
    backend = importlib.import_module("_local_backend")
    wheel_name = backend.build_editable(str(tmp_path))
    wheel_path = tmp_path / wheel_name
    assert wheel_path.exists()

    with zipfile.ZipFile(wheel_path, "r") as archive:
        names = set(archive.namelist())
        assert any(name.endswith(".dist-info/METADATA") for name in names)
        assert any(name.endswith(".dist-info/entry_points.txt") for name in names)
        pth_names = [name for name in names if name.endswith(".pth")]
        assert len(pth_names) == 1
        pth_content = archive.read(pth_names[0]).decode("utf-8").strip()
        assert pth_content == str(backend._project_root())


def test_local_backend_build_wheel_includes_cli_sources(tmp_path: Path) -> None:
    backend = importlib.import_module("_local_backend")
    wheel_name = backend.build_wheel(str(tmp_path))
    wheel_path = tmp_path / wheel_name
    assert wheel_path.exists()

    with zipfile.ZipFile(wheel_path, "r") as archive:
        names = set(archive.namelist())
        assert "client/main.py" in names
        assert "dare_framework/__init__.py" in names
        assert any(name.endswith(".dist-info/RECORD") for name in names)


def test_local_backend_wheel_metadata_includes_markdown_readme(tmp_path: Path) -> None:
    backend = importlib.import_module("_local_backend")
    wheel_name = backend.build_wheel(str(tmp_path))
    wheel_path = tmp_path / wheel_name

    with zipfile.ZipFile(wheel_path, "r") as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        metadata = archive.read(metadata_name).decode("utf-8")

    assert "Description-Content-Type: text/markdown" in metadata
    assert "## 本地安装" in metadata


def test_local_backend_build_sdist_includes_core_sources(tmp_path: Path) -> None:
    backend = importlib.import_module("_local_backend")
    sdist_name = backend.build_sdist(str(tmp_path))
    sdist_path = tmp_path / sdist_name
    assert sdist_path.exists()
    assert sdist_path.suffixes[-2:] == [".tar", ".gz"]

    with tarfile.open(sdist_path, "r:gz") as archive:
        names = set(archive.getnames())
        assert any(name.endswith("/pyproject.toml") for name in names)
        assert any(name.endswith("/_local_backend.py") for name in names)
        assert any(name.endswith("/client/main.py") for name in names)
        assert any(name.endswith("/dare_framework/__init__.py") for name in names)
        assert any(name.endswith("/PKG-INFO") for name in names)


def test_local_backend_reports_no_extra_requirements_for_build_sdist() -> None:
    backend = importlib.import_module("_local_backend")
    assert backend.get_requires_for_build_sdist() == []
