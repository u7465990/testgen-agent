"""Test target generation — Normal, Boundary, Exception, Path, Reflection."""

from __future__ import annotations

from typing import List, Optional

from method_extractor import MethodInfo
from target_profile import TargetProfile


class TargetGenerator:
    """
    Generates test targets (Normal/Boundary/Path/Exception/Reflection)
    for each method. Each target is a descriptive string passed to the LLM.
    """

    def __init__(
        self,
        target_types: Optional[List[str]] = None,
        max_tests_per_method: int = 10,
        profile: Optional[TargetProfile] = None,
    ):
        self.target_types = target_types or [
            "normal", "boundary", "exception", "path", "reflection"
        ]
        self.max_tests_per_method = max_tests_per_method
        # Shared, populated in place during Phase 1 — read at use time so the
        # detected version applies even though this object is built earlier.
        self.profile = profile or TargetProfile()

    @property
    def _junit(self) -> str:
        """Framework name, as it appears in the target description text."""
        return f"JUnit {self.profile.junit_version}"

    def generate_targets(self, method: MethodInfo) -> List[str]:
        """Return a list of target description strings for this method."""
        targets: List[str] = []

        for tt in self.target_types:
            tt_lower = tt.lower()
            if tt_lower == "normal":
                targets.extend(self._normal_targets(method))
            elif tt_lower == "boundary":
                targets.extend(self._boundary_targets(method))
            elif tt_lower == "exception":
                targets.extend(self._exception_targets(method))
            elif tt_lower == "path":
                targets.extend(self._path_targets(method))
            elif tt_lower == "reflection" and method.is_private:
                targets.append(self._reflection_target(method))

        # Cap the total
        return targets[: self.max_tests_per_method]

    # ── Normal targets ────────────────────────────────────────

    def _normal_targets(self, method: MethodInfo) -> List[str]:
        """One normal-case target."""
        param_hints = self._param_value_hints(method, "normal")
        return [
            f"[Normal] Write a {self._junit} test with representative valid "
            f"inputs. "
            f"Use typical values: {param_hints}. "
            f"Assert the expected return value or side effect."
        ]

    # ── Boundary targets ──────────────────────────────────────

    def _boundary_targets(self, method: MethodInfo) -> List[str]:
        """One boundary target per parameter with interesting edge values."""
        targets: List[str] = []
        for i, (pt, pn) in enumerate(
            zip(method.parameter_types, method.parameter_names)
        ):
            base_type = pt.replace("[]", "").strip()
            edges = self._boundary_values(base_type, pt.endswith("[]"))
            for edge_label, edge_value in edges:
                targets.append(
                    f"[Boundary] Test with boundary input for parameter "
                    f"{i} ({pn}: {pt}): set it to {edge_value}. "
                    f"Use reasonable defaults for other parameters. "
                    f"Assert the expected behavior."
                )
        return targets

    @staticmethod
    def _boundary_values(
        base_type: str, is_array: bool
    ) -> List[tuple[str, str]]:
        """Return (label, value) pairs for boundary testing a type."""
        if is_array:
            return [
                ("null", "null"),
                ("empty", f"new {base_type}[0]"),
                ("small", f"new {base_type}{{1, 2, 3}}"),
            ]
        type_map = {
            "String": [
                ("null", "null"),
                ("empty", '""'),
                ("non-empty", '"test"'),
            ],
            "int": [
                ("zero", "0"),
                ("positive", "1"),
                ("negative", "-1"),
            ],
            "long": [
                ("zero", "0L"),
                ("positive", "1L"),
                ("negative", "-1L"),
            ],
            "double": [
                ("zero", "0.0"),
                ("positive", "1.0"),
                ("negative", "-1.0"),
            ],
            "float": [
                ("zero", "0.0f"),
                ("positive", "1.0f"),
                ("negative", "-1.0f"),
            ],
            "boolean": [
                ("true", "true"),
                ("false", "false"),
            ],
            "char": [
                ("null char", "'\\0'"),
                ("letter", "'a'"),
            ],
            "byte": [
                ("zero", "(byte) 0"),
                ("one", "(byte) 1"),
            ],
            "short": [
                ("zero", "(short) 0"),
                ("one", "(short) 1"),
            ],
        }
        return type_map.get(base_type, [("default", f"({base_type}) 0")])

    # ── Exception targets ─────────────────────────────────────

    def _exception_targets(self, method: MethodInfo) -> List[str]:
        """One target per declared checked exception."""
        if not method.throws_exceptions:
            return []
        targets: List[str] = []
        for ex in method.throws_exceptions:
            ex_simple = ex.split(".")[-1]
            if self.profile.junit_version == 5:
                how = (
                    f"Use assertThrows({ex_simple}.class, () -> {{ ... }}) "
                    f"with a lambda. Do NOT use @Test(expected=...)."
                )
            else:
                how = (
                    f"Use try-catch with fail() if no exception is thrown, "
                    f"or @Test(expected={ex_simple}.class). "
                    f"Do NOT use assertThrows."
                )
            targets.append(
                f"[Exception] Write a {self._junit} test that triggers "
                f"{ex_simple}. {how}"
            )
        return targets

    # ── Path targets ──────────────────────────────────────────

    def _path_targets(self, method: MethodInfo) -> List[str]:
        """One target per branch condition, asking to cover each path."""
        if not method.branch_conditions:
            return [
                f"[Path] Write a {self._junit} test that achieves "
                f"statement coverage for the method."
            ]
        targets: List[str] = []
        for i, cond in enumerate(method.branch_conditions):
            # Extract the condition inside parentheses
            cond_clean = cond.strip()
            targets.append(
                f"[Path] Write a {self._junit} test that exercises the branch "
                f"where condition holds: {cond_clean}. "
                f"Provide inputs that make this condition true. "
                f"Assert the expected outcome."
            )
            targets.append(
                f"[Path] Write a {self._junit} test that exercises the branch "
                f"where condition is FALSE: {cond_clean}. "
                f"Provide inputs that make this condition false. "
                f"Assert the expected outcome."
            )
        return targets

    # ── Reflection target ─────────────────────────────────────

    def _reflection_target(self, method: MethodInfo) -> str:
        param_types = ", ".join(method.parameter_types)
        return (
            f"[Reflection] The focal method is private. "
            f"Write a {self._junit} test that invokes "
            f"{method.class_name}.{method.method_name}({param_types}) "
            f"using Java reflection: getDeclaredMethod, setAccessible(true), "
            f"invoke. Handle InvocationTargetException correctly."
        )

    # ── Value hints for normal targets ────────────────────────

    @staticmethod
    def _param_value_hints(method: MethodInfo, style: str) -> str:
        """Suggest reasonable parameter values for target descriptions."""
        hints = []
        for pt in method.parameter_types:
            base = pt.replace("[]", "").strip()
            is_arr = pt.endswith("[]")
            if is_arr:
                hints.append(f"non-null {base} array")
            elif base == "String":
                hints.append('"test" or ""')
            elif base in ("int", "long", "short", "byte"):
                hints.append("0, 1, -1")
            elif base in ("double", "float"):
                hints.append("0.0, 1.0, -1.0")
            elif base == "boolean":
                hints.append("true, false")
            elif base == "char":
                hints.append("'a'")
            else:
                hints.append(f"valid {base} instance")
        return "; ".join(hints)
