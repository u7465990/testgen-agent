"""Keep the packaging metadata honest.

The tool's modules sit flat at the repo root, so setuptools cannot discover them
— ``find_packages()`` only sees directories containing an ``__init__.py`` — and
``setup.py`` lists them by hand in ``MODULES``. That list is the one place a new
module can be forgotten, and the failure is quiet: running from the checkout
works, the wheel is simply missing a file, and the console script dies with an
ImportError only when that particular code path is reached.

These checks are pure filesystem reads, so they belong in the offline suite
rather than in the CI job that builds the wheel. (The wheel itself is built and
installed in the ``package`` job; that is the end-to-end version of this.)

Nothing here imports the modules — ``testgen-agent`` is not installed in the
offline environment, and importing from the repo root would test the checkout
rather than the package.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETUP_PY = REPO_ROOT / "setup.py"

# `setup.py` is the build script and `__init__.py` is the repo-root marker;
# neither is a module the package ships.
_NOT_MODULES = {"setup", "__init__"}


def _setup_tree() -> ast.Module:
    return ast.parse(SETUP_PY.read_text(encoding="utf-8"))


def _declared_modules() -> list:
    """Read the MODULES literal out of setup.py without executing setup()."""
    for node in _setup_tree().body:
        if isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) == "MODULES" for target in node.targets
        ):
            return [element.value for element in node.value.elts]
    raise AssertionError("no MODULES assignment found in setup.py")


def _root_modules_on_disk() -> set:
    return {path.stem for path in REPO_ROOT.glob("*.py")} - _NOT_MODULES


def _console_script_target() -> str:
    """`main:main` -> `main`, read out of the setup() call."""
    for node in ast.walk(_setup_tree()):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node.func, "id", "") != "setup":
            continue
        for keyword in node.keywords:
            if keyword.arg == "entry_points":
                spec = keyword.value.values[0].elts[0].value
                return spec.split("=")[1].split(":")[0].strip()
    raise AssertionError("no console_scripts entry point found in setup.py")


class TestDeclaredModules:
    def test_every_flat_module_is_declared(self):
        # The bug this guards: a module added at the repo root but not to
        # MODULES installs fine for anyone running from the checkout, and is
        # simply absent from the wheel.
        undeclared = _root_modules_on_disk() - set(_declared_modules())
        assert not undeclared, (
            f"modules at the repo root but missing from setup.py's MODULES: "
            f"{sorted(undeclared)}"
        )

    def test_no_stale_entries(self):
        stale = set(_declared_modules()) - _root_modules_on_disk()
        assert not stale, (
            f"setup.py declares modules that do not exist on disk: "
            f"{sorted(stale)}"
        )

    def test_no_duplicates(self):
        declared = _declared_modules()
        assert len(declared) == len(set(declared)), declared

    def test_the_console_script_target_is_one_of_them(self):
        # `testgen-agent = main:main` must point at a module that is shipped,
        # or the entry point dangles and the command fails on import.
        assert _console_script_target() in _declared_modules()


class TestPromptTemplates:
    def test_the_templates_the_tool_loads_are_present(self):
        # PromptManager loads exactly these four by name. package_data ships
        # `prompts/*.txt`, so a *new* template rides along automatically, but a
        # rename would ship a package whose templates silently fail to load and
        # come back as empty strings.
        expected = {
            "generate_system.txt",
            "generate_user.txt",
            "repair_system.txt",
            "repair_user.txt",
        }
        present = {path.name for path in (REPO_ROOT / "prompts").glob("*.txt")}
        assert expected <= present, sorted(expected - present)

    def test_prompts_is_a_package(self):
        # It has to be one for `package_data={"prompts": ["*.txt"]}` to ship
        # anything at all — an __init__.py is what makes it a package.
        assert (REPO_ROOT / "prompts" / "__init__.py").is_file()
