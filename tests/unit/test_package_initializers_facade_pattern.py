from __future__ import annotations

import ast
import re
from pathlib import Path


def _is_internal_module_path(module: str) -> bool:
    return module == "_internal" or module.startswith("_internal.") or "._internal" in module


def _find_direct_internal_import(node: ast.stmt) -> str | None:
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module and _is_internal_module_path(module):
            return f"{'.' * node.level}{module}"

        # `from . import _internal` uses `module is None` and stores names in aliases.
        for alias in node.names:
            if _is_internal_module_path(alias.name):
                return f"{'.' * node.level}{alias.name}"
        return None

    if isinstance(node, ast.Import):
        for alias in node.names:
            if _is_internal_module_path(alias.name):
                return alias.name
    return None


def test_internal_import_detection_covers_relative_syntax() -> None:
    cases = {
        "from ._internal.foo import Bar": "._internal.foo",
        "from .._internal import Foo": ".._internal",
        "from . import _internal": "._internal",
        "from dare_framework.tool._internal.tools import EchoTool": "dare_framework.tool._internal.tools",
        "from dare_framework.tool.defaults import EchoTool": None,
    }
    for source, expected in cases.items():
        node = ast.parse(source).body[0]
        assert _find_direct_internal_import(node) == expected


def test_package_initializers_follow_facade_pattern() -> None:
    """Asserts that all dare_framework initializers use the facade pattern.

    Rules:
    1. Must have a docstring.
    2. No class or function definitions.
    3. Assignments allowed only for metadata (e.g., __all__, __version__).
    4. Imports allowed for re-exporting.
    5. Star imports are prohibited.
    6. Public facades must not import from `._internal` directly.
    """
    repo_root = Path(__file__).resolve().parents[2]
    package_root = repo_root / "dare_framework"
    init_files = sorted(package_root.rglob("__init__.py"))
    assert init_files, "Expected to find dare_framework package initializers"

    violations: list[str] = []
    for path in init_files:
        source = path.read_text(encoding="utf-8")
        is_public_facade = "_internal" not in path.parts
        if not source.strip():
            # Empty files are okay if they are just placeholders,
            # but the user wanted docstrings.
            violations.append(f"{path.relative_to(repo_root)}: Missing docstring")
            continue

        module = ast.parse(source, filename=str(path))
        body = module.body

        # Rule 1: Must have a docstring
        if not (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            violations.append(f"{path.relative_to(repo_root)}: Missing docstring at top of file")
            continue

        body = body[1:]  # Skip docstring

        for node in body:
            # Rule 2: No class or function definitions
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                violations.append(
                    f"{path.relative_to(repo_root)}: "
                    f"Prohibited definition ({type(node).__name__})"
                )
                continue

            # Rule 3: Assignments allowed only for metadata
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = []
                if isinstance(node, ast.Assign):
                    targets = node.targets
                else:
                    targets = [node.target]

                valid_assignment = True
                for target in targets:
                    if isinstance(target, ast.Name):
                        if not (target.id.startswith("__") and target.id.endswith("__")):
                            valid_assignment = False
                    else:
                        valid_assignment = False

                if not valid_assignment:
                    violations.append(
                        f"{path.relative_to(repo_root)}: "
                        "Prohibited assignment (only __all__/__version__ etc allowed)"
                    )

            # Rule 4: Imports are allowed (for re-exporting)
            if isinstance(node, ast.ImportFrom) and any(alias.name == "*" for alias in node.names):
                violations.append(f"{path.relative_to(repo_root)}: Prohibited star import in package initializer")
                continue

            # Rule 6: Public facades must not directly import internal modules.
            if is_public_facade:
                direct_internal_import = _find_direct_internal_import(node)
                if direct_internal_import is not None:
                    violations.append(
                        f"{path.relative_to(repo_root)}: Prohibited direct _internal import ({direct_internal_import})"
                    )
                    continue

            if isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            # Allow metadata assignments and imports, but flag anything else
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.Import, ast.ImportFrom)):
                violations.append(
                    f"{path.relative_to(repo_root)}: "
                    f"Prohibited node type ({type(node).__name__})"
                )

    assert not violations, (
        "Package initializers violated facade pattern rules:\n" + "\n".join(violations)
    )


def test_all_internal_dirs_have_init() -> None:
    """Every ``_internal/`` directory under dare_framework MUST contain ``__init__.py``."""
    repo_root = Path(__file__).resolve().parents[2]
    package_root = repo_root / "dare_framework"

    internal_dirs = sorted(package_root.rglob("_internal"))
    internal_dirs = [d for d in internal_dirs if d.is_dir()]
    assert internal_dirs, "Expected to find _internal directories"

    missing: list[str] = []
    for d in internal_dirs:
        init_path = d / "__init__.py"
        if not init_path.exists():
            missing.append(str(d.relative_to(repo_root)))

    assert not missing, (
        "_internal directories missing __init__.py:\n" + "\n".join(missing)
    )


def test_domain_init_does_not_import_internal_leaf_modules() -> None:
    """Domain ``__init__.py`` MUST import from ``_internal`` package, not leaf modules.

    Allowed:
        from dare_framework.plan._internal import DefaultPlanner
    Forbidden:
        from dare_framework.plan._internal.default_planner import DefaultPlanner

    The ``tool`` domain is excluded because it uses a ``_exports`` module pattern
    rather than ``_internal`` for lazy loading.
    """
    repo_root = Path(__file__).resolve().parents[2]
    package_root = repo_root / "dare_framework"

    # Pattern matches imports like ``from dare_framework.X._internal.Y import ...``
    # where Y is a leaf submodule file (i.e. there is a dot after _internal).
    leaf_import_re = re.compile(r"from\s+\S+\._internal\.\S+\s+import")

    violations: list[str] = []

    # Only check domain-level __init__.py (direct children of dare_framework/)
    for domain_dir in sorted(package_root.iterdir()):
        if not domain_dir.is_dir():
            continue
        init_path = domain_dir / "__init__.py"
        if not init_path.exists():
            continue

        source = init_path.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), start=1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if leaf_import_re.search(line):
                rel = init_path.relative_to(repo_root)
                violations.append(f"{rel}:{lineno}: {stripped}")

    assert not violations, (
        "Domain __init__.py files import directly from _internal leaf modules "
        "(must import through _internal/__init__.py):\n" + "\n".join(violations)
    )


def test_domain_init_defines_all() -> None:
    """Every domain-level ``__init__.py`` MUST define ``__all__``.

    The top-level ``dare_framework/__init__.py`` is excluded from this check
    because it is an acceptable empty-``__all__`` placeholder.
    """
    repo_root = Path(__file__).resolve().parents[2]
    package_root = repo_root / "dare_framework"

    missing: list[str] = []

    for domain_dir in sorted(package_root.iterdir()):
        if not domain_dir.is_dir():
            continue
        # Skip __pycache__ and similar
        if domain_dir.name.startswith("__"):
            continue
        init_path = domain_dir / "__init__.py"
        if not init_path.exists():
            continue

        source = init_path.read_text(encoding="utf-8")
        if not source.strip():
            # Empty placeholder -- already flagged by the docstring test
            continue

        tree = ast.parse(source, filename=str(init_path))
        has_all = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        has_all = True
                        break
            if has_all:
                break

        if not has_all:
            missing.append(str(init_path.relative_to(repo_root)))

    assert not missing, (
        "Domain __init__.py files missing __all__:\n" + "\n".join(missing)
    )
