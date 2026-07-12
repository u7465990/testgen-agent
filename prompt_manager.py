"""Prompt template management — loading, substitution, rendering."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from method_extractor import MethodInfo


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
        self, method: MethodInfo, target: str
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
        return self.generate_system, user

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
        self, broken_code: str, error_message: str, allowed_imports: str
    ) -> Tuple[str, str]:
        """Return (system_prompt, user_prompt) for repairing broken tests."""
        user = self.repair_user
        user = user.replace("#{Java_Code}#", broken_code)
        user = user.replace("#{Error_Message}#", error_message)
        user = user.replace("#{Allowed_Imports}#", allowed_imports)
        return self.repair_system, user
