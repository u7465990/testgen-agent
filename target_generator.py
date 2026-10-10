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
        mock_targets: List[str] = []

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
            elif tt_lower == "mock":
                mock_targets.extend(self._mock_targets(method))

        # Mock targets are prepended and exempt from the cap. Two reasons: a
        # class with collaborators is exactly the case the cap would starve
        # (boundary/path targets fill it first), and a stable low index keeps
        # the counter-derived class names — and therefore the resume
        # checkpoint — deterministic across runs. On a project with no
        # collaborators `mock_targets` is empty, so this is byte-identical to
        # the old `targets[:cap]`.
        return mock_targets + targets[: self.max_tests_per_method]

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

    # ── Mock targets ──────────────────────────────────────────

    def _mock_targets(self, method: MethodInfo) -> List[str]:
        """One Mockito target for a class whose dependencies can be mocked.

        Returns [] unless the class has resolvable, mockable collaborators —
        which requires project source (see collaborator_resolver.py). Mocking a
        dependency the test cannot instantiate produces code that does not
        compile, which is worse than not trying.
        """
        if not self.profile.mockito_available or not method.collaborators:
            return []

        lines = [
            f"[Mock] Write a {self._junit} test for "
            f"{method.class_name}.{method.method_name} that mocks this class's "
            f"injected dependencies with Mockito.",
            "Collaborators to mock:",
        ]
        for c in method.collaborators:
            lines.append(f"  - {c.type_name} ({c.fqn}) [{c.kind}], injected "
                         f"via {c.injection}.")
            if c.method_signatures:
                lines.append("    Public API available to stub:")
                for sig in c.method_signatures:
                    lines.append(f"      {sig}")
            else:
                lines.append("    (no public methods to stub)")

        lines.extend(self._mock_ctor_line(method))
        lines.append("Rules:")
        lines.append(f"  - Mock ONLY the collaborators listed above. A "
                     f"{self._junit} test that mocks nothing when it should is "
                     f"worse than no test.")
        lines.append("  - Do NOT mock java.* types (String, List, ...) or the "
                     "class under test itself.")
        lines.append("  - Write real stubs, not bare mocks: use "
                     "when(...).thenReturn(...) so the branches that depend on "
                     "a collaborator's result are actually reached.")
        lines.append("  - Use argument matchers (any(), anyString(), eq(...)) "
                     "where the exact value is not what is being asserted.")
        lines.append(f"  - Assert on the outcome of {method.class_name} "
                     f"(return value, thrown exception, or a verify(...) on "
                     f"the collaborator), not on what the mock returned.")
        lines.extend(self._mock_idiom_lines())
        return ["\n".join(lines)]

    def _mock_ctor_line(self, method: MethodInfo) -> List[str]:
        ctor_params = ""
        for c in method.constructors:
            params = ", ".join(
                f"{t} {n}" for t, n in zip(c.parameter_types, c.parameter_names)
            )
            ctor_params = f"{c.name}({params})"
            break
        if not ctor_params:
            return ["Construct the class under test with its default "
                    "constructor, injecting the mocks into its fields."]
        return [f"Constructor under test: {ctor_params}"]

    def _mock_idiom_lines(self) -> List[str]:
        """The Mockito idiom to use, in the target text rather than the prompt.

        Two deliberate choices, both from observed failures:

        Explicit `mock(...)` over `@Mock`/`@InjectMocks` annotations. A missing
        `@RunWith`/`@ExtendWith` is not a compile error — the annotated fields
        simply stay null and every test fails at runtime with an NPE. The
        repair loop only recompiles, so it cannot recover from that. The
        explicit form has no annotation to forget, and needs nothing beyond
        `mockito-core`: no runner, no extension, and no strictness setting
        (strict stubs throw `UnnecessaryStubbingException` on the over-stubbing
        LLM-written tests do routinely, and one red test stops PiTest from
        running at all, costing the whole mutation phase).

        The idiom lives in the target text because TargetGenerator reads the
        shared, correctly-detected profile; the system-prompt path has been the
        source of a framework mix-up before (see CLAUDE.md).
        """
        lines = [
            "Use this exact idiom:",
            "  - Create each collaborator with "
            "Mockito.mock(CollaboratorType.class).",
            "  - Pass them to the constructor under test (or assign them to "
            "the class's fields) yourself.",
            "  - Do NOT use @Mock / @InjectMocks, and do NOT rely on a Mockito "
            "runner or extension — the annotation form fails silently if the "
            "runner is missing.",
        ]
        if self.profile.junit_version == 5:
            lines.append(
                "  - Import Mockito statically or qualify calls as "
                "Mockito.when(...) / Mockito.verify(...); use "
                "org.mockito.ArgumentMatchers for any() / eq()."
            )
        else:
            lines.append(
                "  - Import org.mockito.Mockito and call "
                "Mockito.when(...) / Mockito.verify(...); use "
                "org.mockito.ArgumentMatchers for any() / eq()."
            )
        return lines

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
