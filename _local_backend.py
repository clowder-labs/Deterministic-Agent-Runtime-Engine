"""Minimal PEP 517 backend for this repository.

This backend intentionally uses only the Python standard library so that
`pip install -e .` works in constrained environments where setuptools is
not available.
"""

from __future__ import annotations

import base64
import hashlib
import io
import re
import tarfile
import tomllib
import zipfile
from pathlib import Path
from typing import Iterable


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _load_project_metadata() -> dict:
    pyproject = _project_root() / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("missing [project] table in pyproject.toml")
    return project


def _normalize_dist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "_", name).lower()


def _dist_info_dir(project: dict) -> str:
    name = str(project["name"])
    version = str(project["version"])
    return f"{_normalize_dist_name(name)}-{version}.dist-info"


def _wheel_filename(project: dict) -> str:
    name = _normalize_dist_name(str(project["name"]))
    version = str(project["version"])
    return f"{name}-{version}-py3-none-any.whl"


def _normalize_sdist_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _sdist_root_dir(project: dict) -> str:
    name = _normalize_sdist_name(str(project["name"]))
    version = str(project["version"])
    return f"{name}-{version}"


def _sdist_filename(project: dict) -> str:
    return f"{_sdist_root_dir(project)}.tar.gz"


def _infer_readme_content_type(path: Path) -> str:
    if path.suffix.lower() == ".md":
        return "text/markdown"
    if path.suffix.lower() == ".rst":
        return "text/x-rst"
    return "text/plain"


def _readme_payload(project: dict) -> tuple[str, str] | None:
    readme = project.get("readme")
    if isinstance(readme, str):
        path = _project_root() / readme
        return path.read_text(encoding="utf-8"), _infer_readme_content_type(path)
    if isinstance(readme, dict):
        content_type = str(readme.get("content-type") or "text/plain")
        if "file" in readme:
            path = _project_root() / str(readme["file"])
            if "content-type" not in readme:
                content_type = _infer_readme_content_type(path)
            return path.read_text(encoding="utf-8"), content_type
        if "text" in readme:
            return str(readme["text"]), content_type
    return None


def _readme_file(project: dict) -> Path | None:
    readme = project.get("readme")
    if isinstance(readme, str):
        return _project_root() / readme
    if isinstance(readme, dict) and "file" in readme:
        return _project_root() / str(readme["file"])
    return None


def _metadata_text(project: dict) -> str:
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {project['name']}",
        f"Version: {project['version']}",
    ]
    description = project.get("description")
    if description:
        lines.append(f"Summary: {description}")
    requires_python = project.get("requires-python")
    if requires_python:
        lines.append(f"Requires-Python: {requires_python}")
    for dep in project.get("dependencies", []):
        lines.append(f"Requires-Dist: {dep}")
    readme_payload = _readme_payload(project)
    if readme_payload is None:
        return "\n".join(lines) + "\n"
    readme_text, content_type = readme_payload
    lines.append(f"Description-Content-Type: {content_type}")
    return "\n".join(lines) + "\n\n" + readme_text.rstrip() + "\n"


def _wheel_text() -> str:
    return (
        "Wheel-Version: 1.0\n"
        "Generator: dare-local-backend\n"
        "Root-Is-Purelib: true\n"
        "Tag: py3-none-any\n"
    )


def _entry_points_text(project: dict) -> str:
    scripts = project.get("scripts") or {}
    if not scripts:
        return ""
    lines = ["[console_scripts]"]
    for name, target in scripts.items():
        lines.append(f"{name} = {target}")
    return "\n".join(lines) + "\n"


def _package_files() -> Iterable[Path]:
    root = _project_root()
    for package_dir in ("client", "dare_framework"):
        base = root / package_dir
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix == ".py":
                yield path


def _sdist_files() -> Iterable[Path]:
    root = _project_root()
    seen: set[Path] = set()

    def _yield(path: Path) -> Iterable[Path]:
        if not path.exists() or not path.is_file():
            return ()
        if path in seen:
            return ()
        seen.add(path)
        return (path,)

    for candidate in (
        root / "pyproject.toml",
        root / "_local_backend.py",
        root / "requirements.txt",
        root / "pytest.ini",
        root / "client" / "README.md",
    ):
        yield from _yield(candidate)

    readme_file = _readme_file(_load_project_metadata())
    if readme_file is not None:
        yield from _yield(readme_file)

    for file_path in _package_files():
        if file_path not in seen:
            seen.add(file_path)
            yield file_path


def _hash_and_size(payload: bytes) -> tuple[str, int]:
    digest = hashlib.sha256(payload).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return f"sha256={encoded}", len(payload)


def _build_wheel_artifact(*, wheel_directory: str, editable: bool) -> str:
    wheel_dir = Path(wheel_directory)
    wheel_dir.mkdir(parents=True, exist_ok=True)

    project = _load_project_metadata()
    filename = _wheel_filename(project)
    dist_info = _dist_info_dir(project)
    wheel_path = wheel_dir / filename

    records: list[str] = []
    with zipfile.ZipFile(wheel_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        def add(name: str, payload: bytes) -> None:
            archive.writestr(name, payload)
            digest, size = _hash_and_size(payload)
            records.append(f"{name},{digest},{size}")

        add(f"{dist_info}/METADATA", _metadata_text(project).encode("utf-8"))
        add(f"{dist_info}/WHEEL", _wheel_text().encode("utf-8"))
        entry_points = _entry_points_text(project)
        if entry_points:
            add(f"{dist_info}/entry_points.txt", entry_points.encode("utf-8"))

        if editable:
            # Editable mode uses .pth to expose the repository root as import path.
            pth_name = f"{_normalize_dist_name(str(project['name']))}.pth"
            add(pth_name, f"{_project_root()}\n".encode("utf-8"))
        else:
            root = _project_root()
            for file_path in _package_files():
                relpath = file_path.relative_to(root).as_posix()
                add(relpath, file_path.read_bytes())

        record_path = f"{dist_info}/RECORD"
        records.append(f"{record_path},,")
        archive.writestr(record_path, ("\n".join(records) + "\n").encode("utf-8"))

    return filename


def _write_metadata_directory(metadata_directory: str) -> str:
    target_root = Path(metadata_directory)
    project = _load_project_metadata()
    dist_info = _dist_info_dir(project)
    output_dir = target_root / dist_info
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "METADATA").write_text(_metadata_text(project), encoding="utf-8")
    (output_dir / "WHEEL").write_text(_wheel_text(), encoding="utf-8")
    entry_points = _entry_points_text(project)
    if entry_points:
        (output_dir / "entry_points.txt").write_text(entry_points, encoding="utf-8")
    return dist_info


def build_sdist(
    sdist_directory: str,
    config_settings: dict | None = None,
) -> str:
    _ = config_settings
    sdist_dir = Path(sdist_directory)
    sdist_dir.mkdir(parents=True, exist_ok=True)

    project = _load_project_metadata()
    filename = _sdist_filename(project)
    root_dir = _sdist_root_dir(project)
    artifact_path = sdist_dir / filename
    project_root = _project_root()

    with tarfile.open(artifact_path, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
        for file_path in _sdist_files():
            relpath = file_path.relative_to(project_root).as_posix()
            archive.add(file_path, arcname=f"{root_dir}/{relpath}", recursive=False)

        metadata_payload = _metadata_text(project).encode("utf-8")
        pkg_info = tarfile.TarInfo(name=f"{root_dir}/PKG-INFO")
        pkg_info.size = len(metadata_payload)
        archive.addfile(pkg_info, io.BytesIO(metadata_payload))

    return filename


def build_wheel(
    wheel_directory: str,
    config_settings: dict | None = None,
    metadata_directory: str | None = None,
) -> str:
    _ = (config_settings, metadata_directory)
    return _build_wheel_artifact(wheel_directory=wheel_directory, editable=False)


def build_editable(
    wheel_directory: str,
    config_settings: dict | None = None,
    metadata_directory: str | None = None,
) -> str:
    _ = (config_settings, metadata_directory)
    return _build_wheel_artifact(wheel_directory=wheel_directory, editable=True)


def get_requires_for_build_wheel(config_settings: dict | None = None) -> list[str]:
    _ = config_settings
    return []


def get_requires_for_build_editable(config_settings: dict | None = None) -> list[str]:
    _ = config_settings
    return []


def get_requires_for_build_sdist(config_settings: dict | None = None) -> list[str]:
    _ = config_settings
    return []


def prepare_metadata_for_build_wheel(
    metadata_directory: str,
    config_settings: dict | None = None,
) -> str:
    _ = config_settings
    return _write_metadata_directory(metadata_directory)


def prepare_metadata_for_build_editable(
    metadata_directory: str,
    config_settings: dict | None = None,
) -> str:
    _ = config_settings
    return _write_metadata_directory(metadata_directory)
