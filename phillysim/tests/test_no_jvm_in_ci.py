"""EP-13: CI never runs the JVM.

The routing dependency group is optional and not installed in CI; importing r5py starts
a JVM (and, without the jar, downloads it), so no module under ``phillysim`` may import
r5py or JPype at module level, and only the harness child may import them at all (inside
the function that runs in the child). The scan is static (AST), so it holds whether or
not the group is installed where the suite runs; the import check confirms that
importing the CLI and every routing module leaves neither in ``sys.modules``. The
project configuration is checked too: the group is not a default group, CI installs no
group, the ignore rules cover the toolchain and the run records, and nothing under the
toolchain directories is tracked.
"""

from __future__ import annotations

import ast
import importlib
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = PROJECT_DIR.parent
PACKAGE_DIR = PROJECT_DIR / "src" / "phillysim"
JVM_PACKAGES = frozenset({"r5py", "jpype", "jpype1"})
#: The one module allowed to import r5py, and only inside a function body.
CHILD_MODULE = PACKAGE_DIR / "routing" / "harness.py"


def _imports(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Import):
        names.update(alias.name.split(".")[0] for alias in node.names)
    elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        names.add(node.module.split(".")[0])
    return names


def module_level_jvm_imports(source: str) -> set[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in tree.body:
        for child in ast.walk(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                break
        else:
            found |= _imports(node) & JVM_PACKAGES
            continue
        # A top-level statement that *contains* a function (a class body, say) still
        # counts for its own direct imports.
        found |= _imports(node) & JVM_PACKAGES
    return found


def any_jvm_imports(source: str) -> set[str]:
    return {name for node in ast.walk(ast.parse(source)) for name in _imports(node) & JVM_PACKAGES}


def test_no_module_imports_r5py_or_jpype_at_module_level() -> None:
    offenders = {
        str(path.relative_to(PACKAGE_DIR)): hits
        for path in sorted(PACKAGE_DIR.rglob("*.py"))
        if (hits := module_level_jvm_imports(path.read_text("utf-8")))
    }
    assert offenders == {}


def test_only_the_harness_child_imports_r5py_anywhere() -> None:
    offenders = {
        str(path.relative_to(PACKAGE_DIR)): hits
        for path in sorted(PACKAGE_DIR.rglob("*.py"))
        if path != CHILD_MODULE and (hits := any_jvm_imports(path.read_text("utf-8")))
    }
    assert offenders == {}
    assert any_jvm_imports(CHILD_MODULE.read_text("utf-8")) == {"r5py"}


def test_detector_fires_on_a_module_level_import() -> None:
    assert module_level_jvm_imports("import r5py\n") == {"r5py"}
    assert module_level_jvm_imports("from jpype import startJVM\n") == {"jpype"}
    assert module_level_jvm_imports("def f():\n    import r5py\n") == set()
    assert any_jvm_imports("def f():\n    import r5py\n") == {"r5py"}
    assert module_level_jvm_imports("import r5pyx\nimport psutil\n") == set()


def test_importing_the_cli_and_the_routing_modules_starts_no_jvm() -> None:
    for name in (
        "phillysim.cli",
        "phillysim.routing",
        "phillysim.routing.toolchain",
        "phillysim.routing.sampler",
        "phillysim.routing.records",
        "phillysim.routing.harness",
        "phillysim.routing.smoke",
        "phillysim.routing.plan",
        "phillysim.routing.matrix",
        "phillysim.routing.verdict",
        "phillysim.routing.handcheck",
        "phillysim.routing.concordance",
        "phillysim.routing.stage",
        "phillysim.pipeline",
    ):
        importlib.import_module(name)
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (loaded & JVM_PACKAGES), loaded & JVM_PACKAGES


def test_routing_group_is_optional_and_psutil_is_core() -> None:
    pyproject = tomllib.loads((PROJECT_DIR / "pyproject.toml").read_text("utf-8"))
    groups = pyproject["dependency-groups"]
    # EP-15 (ADR-0008): osmnx and scipy, the fallback engine and the concordance, join the
    # group; CI still installs none of it, so the OSMnx-side tests skip there.
    assert {s.split("==")[0] for s in groups["routing"]} == {
        "r5py",
        "jpype1",
        "psutil",
        "osmnx",
        "scipy",
    }
    assert "routing" not in pyproject["tool"]["uv"]["default-groups"]
    core = {s.split(">=")[0].split("==")[0] for s in pyproject["project"]["dependencies"]}
    assert "psutil" in core and "r5py" not in core and "jpype1" not in core
    assert "osmnx" not in core and "scipy" not in core
    assert groups["routing"] == [
        "r5py==1.1.7",
        "jpype1==1.7.1",
        "psutil==7.2.2",
        "osmnx==2.1.1",
        "scipy==1.18.1",
    ]


def test_ci_installs_no_routing_group_and_runs_no_routing_verb() -> None:
    workflow = (REPO_DIR / ".github" / "workflows" / "ci.yml").read_text("utf-8")
    assert "--group routing" not in workflow and "--all-groups" not in workflow
    assert "toolchain install" not in workflow and "route smoke" not in workflow
    assert "uv sync --locked" in workflow


def test_gitignore_covers_the_toolchain_and_the_run_records() -> None:
    rules = {
        line.strip()
        for line in (REPO_DIR / ".gitignore").read_text("utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }
    assert {".jdk/", ".r5/", "*.jar", "data/runs/", "phillysim/toolchain.json"} <= rules


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not on PATH")
def test_nothing_under_the_toolchain_directories_is_tracked() -> None:
    if not (REPO_DIR / ".git").exists():
        pytest.skip("not a git checkout")
    listing = subprocess.run(
        ["git", "-C", str(REPO_DIR), "ls-files", "--", "phillysim"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    tracked = [
        p
        for p in listing
        if p.startswith(("phillysim/.jdk/", "phillysim/.r5/"))
        or p.endswith(".jar")
        or p == "phillysim/toolchain.json"
    ]
    assert tracked == []
