"""Abstract base class for method extractor backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from method_extractor import MethodInfo
from java_analyzer import SourceFile


class ExtractorBackend(ABC):
    """Interface that all extraction backends must implement."""

    @abstractmethod
    def extract(self, source_file: SourceFile) -> List[MethodInfo]:
        """Extract MethodInfo list from a single Java source file."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable backend name."""
        ...

    @property
    @abstractmethod
    def provides_jimple(self) -> bool:
        """Whether this backend produces Jimple IR."""
        ...
