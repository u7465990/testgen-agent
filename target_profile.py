"""Target project profile — detect the Java and JUnit versions a project uses.

The agent does not impose a JUnit or Java version; it follows the project under
test. This mirrors what Surefire itself does: if `junit-jupiter` is on the test
classpath it runs the JUnit Platform, otherwise it treats the suite as JUnit 4.
Picking a global default instead would mean generating tests that cannot compile
against the project's own dependencies.

Detection is cheap and reuses machinery Phase 1 already has — the resolved
classpath (`JavaProjectAnalyzer.resolve_classpath()`) and the compiled classes
(`find_compiled_classes()`) — so it adds no Maven or JVM invocation of its own.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

# ── Constants ─────────────────────────────────────────────────

# .class file major version -> Java release. The major version lives in bytes
# 6-7 of a class file (big-endian), right after the 0xCAFEBABE magic and the
# minor version. Reading it is the most reliable signal available offline: it
# is what the compiler actually emitted, as opposed to what the pom claims.
_CLASS_MAJOR_TO_JAVA = {
    45: 1, 46: 2, 47: 3, 48: 4, 49: 5, 50: 6, 51: 7, 52: 8,
    53: 9, 54: 10, 55: 11, 56: 12, 57: 13, 58: 14, 59: 15,
    60: 16, 61: 17, 62: 18, 63: 19, 64: 20, 65: 21,
}

_JAVA_MAGIC = b"\xca\xfe\xba\xbe"

# Fallbacks when nothing can be detected. Java 8 / JUnit 4 is the most
# conservative choice: a test written for them compiles against a project on
# any newer toolchain, which is not true in the other direction.
DEFAULT_JAVA_VERSION = 8
DEFAULT_JUNIT_VERSION = 4

_SUPPORTED_JAVA = (8, 11, 17, 21)


# ── Data model ────────────────────────────────────────────────

@dataclass
class TargetProfile:
    """The Java and JUnit versions the generated tests must target.

    `*_source` records *how* each version was determined, and is surfaced in
    the report so a wrong guess can be traced to its evidence rather than
    re-derived by hand.
    """

    java_version: int = DEFAULT_JAVA_VERSION
    junit_version: int = DEFAULT_JUNIT_VERSION
    java_source: str = "default"
    junit_source: str = "default"
    warnings: List[str] = field(default_factory=list)

    @property
    def junit_label(self) -> str:
        """Human-readable framework name for prompts and reports."""
        return f"JUnit {self.junit_version}"

    @property
    def java_label(self) -> str:
        return f"Java {self.java_version}"

    @property
    def supported(self) -> bool:
        """True if the detected combinations are ones we can generate for."""
        return self.java_version in _SUPPORTED_JAVA and self.junit_version in (4, 5)

    def describe(self) -> str:
        return (
            f"{self.java_label} / {self.junit_label} "
            f"(java: {self.java_source}; junit: {self.junit_source})"
        )

    def to_dict(self) -> dict:
        return {
            "java_version": self.java_version,
            "junit_version": self.junit_version,
            "java_source": self.java_source,
            "junit_source": self.junit_source,
            "warnings": list(self.warnings),
        }


# ── Public API ────────────────────────────────────────────────

def detect(
    project_path: Path,
    classpath: str = "",
    configured_java: str = "auto",
    configured_junit: str = "auto",
    javac_path: Optional[Path] = None,
) -> TargetProfile:
    """Detect the Java and JUnit versions for `project_path`."""
    return detect_into(
        TargetProfile(), project_path, classpath,
        configured_java, configured_junit, javac_path,
    )


def detect_into(
    profile: TargetProfile,
    project_path: Path,
    classpath: str = "",
    configured_java: str = "auto",
    configured_junit: str = "auto",
    javac_path: Optional[Path] = None,
) -> TargetProfile:
    """Fill an existing TargetProfile in place and return it.

    The agent builds its sub-modules (compiler, extractor, target generator)
    before Phase 1, because detection needs the resolved classpath — which is
    only available once Phase 1 has run. Those modules therefore hold a
    reference to one profile object that gets populated in place here, rather
    than each being rebuilt after detection.

    `configured_java` / `configured_junit` are the CLI overrides ("auto" means
    detect). `classpath` should be the already-resolved test classpath; when it
    is empty, JUnit detection falls back to reading the build file.
    """
    profile.warnings = []

    profile.java_version, profile.java_source = _detect_java(
        project_path, configured_java, javac_path
    )
    profile.junit_version, profile.junit_source = _detect_junit(
        project_path, classpath, configured_junit
    )

    if not profile.supported:
        profile.warnings.append(
            f"Detected {profile.java_label} / {profile.junit_label} is outside "
            f"the supported range (Java {_SUPPORTED_JAVA} with JUnit 4 or 5). "
            f"Generated tests may not compile — override with --java / --junit."
        )
    return profile


# ── Java version ──────────────────────────────────────────────

def _detect_java(
    project_path: Path, configured: str, javac_path: Optional[Path]
) -> Tuple[int, str]:
    """Return (java_version, source_description)."""
    if configured and configured != "auto":
        parsed = _normalize_java_version(configured)
        if parsed is not None:
            return parsed, "explicit (--java)"

    for pom_text, label in _pom_candidates(project_path):
        parsed = _java_from_pom_text(pom_text)
        if parsed is not None:
            return parsed, f"{label} maven.compiler"
    for gradle_text, label in _gradle_candidates(project_path):
        parsed = _java_from_gradle_text(gradle_text)
        if parsed is not None:
            return parsed, f"{label} sourceCompatibility"

    parsed = _java_from_class_files(project_path)
    if parsed is not None:
        return parsed, "compiled .class major version"

    parsed = _java_from_javac(javac_path)
    if parsed is not None:
        return parsed, "javac -version (fallback)"

    return DEFAULT_JAVA_VERSION, "default (nothing detected)"


def _java_from_pom_text(text: str) -> Optional[int]:
    """Read the compiler level out of a pom.xml.

    Preference order is release > source > target: `release` is the strictest
    (it also pins the platform API), and `source` is what actually forbids
    newer syntax in the generated test.
    """
    text = _strip_xml_comments(text)
    for key in ("maven.compiler.release", "java.version",
                "maven.compiler.source", "maven.compiler.target"):
        m = re.search(
            rf"<{re.escape(key)}>\s*([^<]+?)\s*</{re.escape(key)}>", text
        )
        if m:
            parsed = _normalize_java_version(m.group(1))
            if parsed is not None:
                return parsed
    # maven-compiler-plugin's own <source>/<target>/<release> configuration
    for tag in ("release", "source", "target"):
        m = re.search(
            rf"<{tag}>\s*(1?\.?\d+)\s*</{tag}>", text
        )
        if m:
            parsed = _normalize_java_version(m.group(1))
            if parsed is not None:
                return parsed
    return None


def _java_from_gradle_text(text: str) -> Optional[int]:
    """Read sourceCompatibility/targetCompatibility out of a Gradle build file."""
    patterns = [
        r"sourceCompatibility\s*=?\s*JavaVersion\.VERSION_([\d_]+)",
        r"targetCompatibility\s*=?\s*JavaVersion\.VERSION_([\d_]+)",
        r"sourceCompatibility\s*=?\s*['\"]?([\d._]+)['\"]?",
        r"targetCompatibility\s*=?\s*['\"]?([\d._]+)['\"]?",
    ]
    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            parsed = _normalize_java_version(m.group(1))
            if parsed is not None:
                return parsed
    return None


def _java_from_class_files(project_path: Path) -> Optional[int]:
    """Infer the Java level from a compiled class, if the project was built.

    Only main classes are inspected — test classes are excluded so a project
    built with a newer JDK than its own target does not skew the result.
    """
    for classes_dir in _classes_dirs(project_path):
        for class_file in classes_dir.rglob("*.class"):
            try:
                header = class_file.read_bytes()[:8]
            except OSError:
                continue
            if len(header) < 8 or not header.startswith(_JAVA_MAGIC):
                continue
            major = int.from_bytes(header[6:8], "big")
            if major in _CLASS_MAJOR_TO_JAVA:
                return _CLASS_MAJOR_TO_JAVA[major]
    return None


def _java_from_javac(javac_path: Optional[Path]) -> Optional[int]:
    """Last resort: the JDK running javac (generated code must compile on it)."""
    if not javac_path:
        return None
    try:
        result = subprocess.run(
            [str(javac_path), "-version"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # JDK 8 prints to stderr ("javac 1.8.0_281"); JDK 9+ prints to stdout.
    text = (result.stdout or "") + (result.stderr or "")
    m = re.search(r"javac\s+1\.(\d+)", text)
    if m:
        return int(m.group(1))
    m = re.search(r"javac\s+(\d+)", text)
    if m:
        return int(m.group(1))
    return None


def _normalize_java_version(raw: str) -> Optional[int]:
    """Normalize "1.8", "1_8", "8", "17", "VERSION_17" to a release number."""
    raw = raw.strip().replace("_", ".").replace("VERSION.", "")
    m = re.match(r"^1\.(\d+)$", raw)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d+)$", raw)
    if m:
        return int(m.group(1))
    return None


# ── JUnit version ─────────────────────────────────────────────

def _detect_junit(
    project_path: Path, classpath: str, configured: str
) -> Tuple[int, str]:
    """Return (junit_version, source_description)."""
    if configured and configured != "auto":
        try:
            return int(configured), "explicit (--junit)"
        except ValueError:
            pass

    has_jupiter, has_junit4 = _classpath_junit_signals(classpath)
    origin = "classpath"
    if not classpath:
        has_jupiter, has_junit4 = _build_file_junit_signals(project_path)
        origin = "build file"

    if has_jupiter:
        # Both present means a migration in progress (jupiter + vintage);
        # jupiter wins because that is the direction the project is moving.
        return 5, f"{origin} (junit-jupiter)"
    if has_junit4:
        return 4, f"{origin} (junit:junit)"
    return DEFAULT_JUNIT_VERSION, f"default (no test framework found in {origin})"


def _classpath_junit_signals(classpath: str) -> Tuple[bool, bool]:
    """Return (has_jupiter, has_junit4) for a resolved classpath string."""
    # Normalize separators so Maven's repo layout matches on Windows too.
    norm = classpath.replace("\\", "/").lower()
    has_jupiter = (
        "junit-jupiter" in norm
        or "junit-platform" in norm
        or "junit/jupiter" in norm
    )
    # JUnit 4 resolves to .../junit/junit/4.13.2/junit-4.13.2.jar
    has_junit4 = (
        "/junit/junit/" in norm
        or "junit-4." in norm
        or "junit4" in norm
    )
    return has_jupiter, has_junit4


def _build_file_junit_signals(project_path: Path) -> Tuple[bool, bool]:
    """Fallback when the classpath could not be resolved: read the build file."""
    text = ""
    pom = project_path / "pom.xml"
    if pom.is_file():
        try:
            text = _strip_xml_comments(pom.read_text(encoding="utf-8"))
        except OSError:
            text = ""
    if not text:
        for name in ("build.gradle", "build.gradle.kts"):
            candidate = project_path / name
            if candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8")
                except OSError:
                    text = ""
                break
    # Match against lowercased text, so every needle must be lowercase too —
    # an XML tag written as <artifactId> would otherwise never match.
    norm = text.lower()
    return ("junit-jupiter" in norm or "junit_platform" in norm,
            "junit-4." in norm or "<artifactid>junit</artifactid>" in norm)


# ── Build-file helpers ────────────────────────────────────────

def _strip_xml_comments(text: str) -> str:
    """Drop XML comments so a commented-out version does not win detection."""
    return re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)


def _pom_candidates(project_path: Path) -> List[Tuple[str, str]]:
    """Root pom, then any sub-module poms (multi-module Maven)."""
    candidates: List[Tuple[str, str]] = []
    root = project_path / "pom.xml"
    if root.is_file():
        try:
            candidates.append((_strip_xml_comments(
                root.read_text(encoding="utf-8")), "pom.xml"))
        except OSError:
            pass
    if project_path.is_dir():
        module_dirs = sorted(p for p in project_path.iterdir() if p.is_dir())
        for module_dir in module_dirs:
            module_pom = module_dir / "pom.xml"
            if module_pom.is_file():
                try:
                    candidates.append((_strip_xml_comments(
                        module_pom.read_text(encoding="utf-8")),
                        f"{module_dir.name}/pom.xml"))
                except OSError:
                    pass
    return candidates


def _gradle_candidates(project_path: Path) -> List[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    for name in ("build.gradle", "build.gradle.kts"):
        path = project_path / name
        if path.is_file():
            try:
                candidates.append((path.read_text(encoding="utf-8"), name))
            except OSError:
                pass
    return candidates


def _classes_dirs(project_path: Path) -> List[Path]:
    candidates = [
        project_path / "target/classes",
        project_path / "build/classes",
        project_path / "bin",
    ]
    return [d for d in candidates if d.is_dir()]


def pom_declares(project_path: Path, artifact: str) -> bool:
    """True if the project's root pom mentions `artifact` at all.

    Used to decide whether mutation analysis can run: PiTest needs
    `pitest-junit5-plugin` on its own plugin classpath for JUnit 5, and that
    dependency can only be declared in the pom — there is no `-D` property for
    it. When it is missing we skip with an explanation instead of letting Maven
    fail with an opaque error.
    """
    pom = project_path / "pom.xml"
    if not pom.is_file():
        return False
    try:
        return artifact in _strip_xml_comments(pom.read_text(encoding="utf-8"))
    except OSError:
        return False
