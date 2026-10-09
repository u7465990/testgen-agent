"""Prompt template management — loading, substitution, rendering."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from method_extractor import MethodInfo
from target_profile import TargetProfile


class PromptManager:
    """Loads prompt templates and renders them with method-specific data."""

    def __init__(self, prompt_dir: Path):
        self.prompt_dir = prompt_dir
        self.generate_system = self._load("generate_system.txt")
        self.generate_user = self._load("generate_user.txt")
        self.repair_system = self._load("repair_system.txt")
        self.repair_user = self._load("repair_user.txt")

    def _load(self, name: str) -> str:
        path = self.prompt_dir / name
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"  [WARN] Prompt template not found: {path}")
            return ""

    # ── Generation prompt ─────────────────────────────────────

    def render_generate_prompt(
        self,
        method: MethodInfo,
        target: str,
        profile: Optional[TargetProfile] = None,
    ) -> Tuple[str, str]:
        """Return (system_prompt, user_prompt) for test generation."""
        user = self.generate_user
        replacements = {
            "#{FQN}#": method.fqn,
            "#{Signature}#": method.signature,
            "#{SourceCode}#": method.source_code,
            "#{BranchConditions}#": self._format_branch_conditions(
                method.branch_conditions
            ),
            "#{JimpleCode}#": method.jimple_code if method.jimple_code
                              else "// No Jimple IR available",
            "#{ClassContext}#": method.class_context,
            "#{AllowedImports}#": "\n".join(
                f"import {i};" for i in method.allowed_imports
            ),
            "#{ThrowsExceptions}#": (
                ", ".join(method.throws_exceptions)
                if method.throws_exceptions
                else "none"
            ),
            "#{Modifiers}#": " ".join(method.modifiers),
            "#{GenerationTarget}#": target,
        }
        for placeholder, value in replacements.items():
            user = user.replace(placeholder, value)
        return self._fill_framework(self.generate_system, profile), user

    # ── Framework-specific prompt text ────────────────────────

    def _fill_framework(
        self, template: str, profile: Optional[TargetProfile]
    ) -> str:
        """Substitute the JUnit/Java version placeholders in a system prompt.

        `str.replace` is deliberate — it is the mechanism the templates already
        use, and prompt text is full of characters a regex or `.format()` would
        reinterpret. The system templates carry these placeholders too, so this
        runs on the system prompt as well as the user prompt.
        """
        for placeholder, value in self._framework_replacements(profile).items():
            template = template.replace(placeholder, value)
        return template

    @staticmethod
    def _framework_replacements(
        profile: Optional[TargetProfile],
    ) -> Dict[str, str]:
        """The rule text that differs between JUnit 4 and JUnit 5.

        JUnit 5 is not a syntax refresh of JUnit 4 — `@Test(expected=...)` was
        removed and `assertThrows` takes an `Executable`, so its exception rule
        *requires* a lambda. That is why the banned-syntax rule has to flip
        with the version rather than being softened.
        """
        p = profile or TargetProfile()
        java = p.java_version
        if p.junit_version == 5:
            exception_rule = (
                "@rule5: For exception testing, use "
                "assertThrows(ExpectedException.class, () -> { ... }) and pass "
                "a LAMBDA. Do NOT write an anonymous inner class such as "
                "`new Executable() { ... }` — that is JUnit 4-era style and "
                "needs no import, whereas a lambda does not need one either. "
                "Do NOT use @Test(expected=...) (removed in JUnit 5), and do "
                "NOT use try-catch with fail()."
            )
            syntax_rule = (
                f"@rule7: Use JUnit 5 and Java {java}. Lambdas, method "
                f"references and Streams ARE allowed AND PREFERRED — when an "
                f"API takes a functional interface (assertThrows, "
                f"assertAll, assertTimeout), pass a lambda, not an anonymous "
                f"inner class. Do not use APIs newer than Java {java}. Use "
                f"org.junit.jupiter.api.Assertions.* for assertions, NOT "
                f"org.junit.Assert, which is JUnit 4."
            )
            syntax_rule_repair = (
                f"@rule7: JUNIT 5 & JAVA {java}: lambdas ARE allowed and are "
                f"required for assertThrows. Use "
                f"org.junit.jupiter.api.Assertions.* (NOT org.junit.Assert). "
                f"Do NOT use @Test(expected=...)."
            )
        else:
            exception_rule = (
                "@rule5: For exception testing, use try-catch and fail() if the "
                "exception is not thrown, or @Test(expected=Exception.class). "
                "Do NOT use assertThrows() (not available in JUnit 4)."
            )
            syntax_rule = (
                f"@rule7: Use JUnit 4 and Java {java}. No lambdas, no method "
                f"references, no Streams, no var. Use org.junit.Assert.* for "
                f"assertions. Do not use APIs newer than Java {java}."
            )
            syntax_rule_repair = (
                f"@rule7: STRICT JUNIT 4 & JAVA {java}: NO modern syntax. Do "
                f"NOT use lambdas (->), method references (::), Streams, or "
                f"var. Use org.junit.Assert.*, not JUnit 5 assertions."
            )
        return {
            "#{JUnitVersionLabel}#": p.junit_label,
            "#{JUnitExceptionRule}#": exception_rule,
            "#{JUnitSyntaxRule}#": syntax_rule,
            "#{JUnitSyntaxRuleRepair}#": syntax_rule_repair,
        }

    def _format_branch_conditions(self, conditions: List[str]) -> str:
        """Format branch conditions as a readable list for the prompt."""
        if not conditions:
            return "// No conditional branches detected"
        lines = ["// Control flow conditions:"]
        for i, cond in enumerate(conditions):
            lines.append(f"//   branch {i}: {cond}")
        return "\n".join(lines)

    # ── Repair prompt ─────────────────────────────────────────

    def render_repair_prompt(
        self,
        broken_code: str,
        error_message: str,
        allowed_imports: str,
        profile: Optional[TargetProfile] = None,
    ) -> Tuple[str, str]:
        """Return (system_prompt, user_prompt) for repairing broken tests."""
        user = self.repair_user
        user = user.replace("#{Java_Code}#", broken_code)
        user = user.replace("#{Error_Message}#", error_message)
        user = user.replace("#{Allowed_Imports}#", allowed_imports)
        return self._fill_framework(self.repair_system, profile), user
