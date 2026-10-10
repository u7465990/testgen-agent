"""Add the Mockito dependency to a target project's pom, on request only.

The agent is read-only by default — it never edits a project it was pointed at.
`--add-mock-deps` is the explicit opt-in that makes an exception, because
without the dependency on the *test* classpath nothing Mockito-related can
compile, and `mvn test` (the check that matters) reads the pom rather than our
javac invocation.

Everything here is written to be safe to run repeatedly on someone else's
build file: idempotent, backed up once, inserted as text rather than
round-tripped through a DOM (which would reformat the whole file and can drop
the XML declaration), and validated before the write is kept.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple
from xml.dom import minidom

BACKUP_SUFFIX = ".testgen-backup"

# Mockito 5 requires Java 11+. Picking the coordinate from the detected Java
# level is what keeps a Java 8 project working.
_MOCKITO_VERSION_JAVA8 = "4.11.0"
_MOCKITO_VERSION_MODERN = "5.12.0"


def _mockito_version(java_version: int) -> str:
    return _MOCKITO_VERSION_JAVA8 if java_version <= 8 else _MOCKITO_VERSION_MODERN


def mockito_coordinates(
    junit_version: int, java_version: int
) -> List[Tuple[str, str, str]]:
    """(groupId, artifactId, version) triples to declare, test scope.

    `mockito-junit-jupiter` is only for JUnit 5, and deliberately so: it pulls
    `junit-jupiter-api` transitively, which is one of the signals
    `target_profile._classpath_junit_signals` uses to detect JUnit 5. Adding it
    to a JUnit 4 project would make the next run misdetect the framework.
    """
    version = _mockito_version(java_version)
    coords = [("org.mockito", "mockito-core", version)]
    if junit_version == 5:
        coords.append(("org.mockito", "mockito-junit-jupiter", version))
    return coords


def strip_xml_comments(text: str) -> str:
    """Drop XML comments so a commented-out dependency is not mistaken for one."""
    import re
    return re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)


def pom_has_mockito(pom_path: Path) -> bool:
    """True if the pom already declares any Mockito artifact."""
    if not pom_path.is_file():
        return False
    try:
        text = strip_xml_comments(pom_path.read_text(encoding="utf-8"))
    except OSError:
        return False
    return "mockito-core" in text or "mockito-junit-jupiter" in text


def _dependency_block(coords: List[Tuple[str, str, str]]) -> str:
    lines: List[str] = []
    for group, artifact, version in coords:
        lines.append("    <dependency>")
        lines.append(f"      <groupId>{group}</groupId>")
        lines.append(f"      <artifactId>{artifact}</artifactId>")
        lines.append(f"      <version>{version}</version>")
        lines.append("      <scope>test</scope>")
        lines.append("    </dependency>")
    return "\n".join(lines)


def inject_mockito_dependency(
    pom_path: Path, junit_version: int, java_version: int
) -> Tuple[bool, str]:
    """Declare Mockito in the pom. Returns (changed, message). Never raises.

    Text-insertion, not a DOM rewrite: re-serialising via a parser reformats
    the entire file (indentation, attribute quoting, the XML declaration) and
    makes the diff unreadable in a project we do not own.
    """
    if not pom_path.is_file():
        return False, f"no pom.xml at {pom_path}"

    if pom_has_mockito(pom_path):
        # Checked first, so a second run is a no-op rather than a duplicate.
        return False, "already declared"

    try:
        original = pom_path.read_text(encoding="utf-8")
    except OSError as e:
        return False, f"cannot read {pom_path}: {e}"

    block = _dependency_block(
        mockito_coordinates(junit_version, java_version)
    )

    def insert_at_line_start(text: str, marker: str, payload: str) -> str:
        """Insert `payload` on its own line, just before `marker`'s line.

        Anchoring to the line start rather than the marker's column keeps the
        block's own indentation intact — inserting at the marker's index would
        prepend the closing tag's indent to the first line and skew it.
        """
        idx = text.index(marker)
        line_start = text.rfind("\n", 0, idx) + 1
        return text[:line_start] + payload + "\n" + text[line_start:]

    if "</dependencies>" in original:
        new_text = insert_at_line_start(original, "</dependencies>", block)
    elif "<build>" in original:
        new_text = insert_at_line_start(
            original, "<build>",
            "  <dependencies>\n" + block + "\n  </dependencies>\n",
        )
    elif "</project>" in original:
        new_text = insert_at_line_start(
            original, "</project>",
            "  <dependencies>\n" + block + "\n  </dependencies>\n",
        )
    else:
        return False, "pom.xml has no </dependencies>, <build> or </project>"

    # Validate before keeping the write. minidom is stdlib; lxml happens to be
    # installed in this environment but is not a declared dependency.
    try:
        minidom.parseString(new_text)
    except Exception as e:
        return False, f"refusing to write a malformed pom.xml: {e}"

    backup = pom_path.with_name(pom_path.name + BACKUP_SUFFIX)
    if not backup.exists():
        # Written once: re-running must never overwrite the pristine original
        # with an already-modified file.
        try:
            shutil.copy2(pom_path, backup)
        except OSError as e:
            return False, f"cannot create backup {backup}: {e}"

    try:
        pom_path.write_text(new_text, encoding="utf-8")
    except OSError as e:
        return False, f"cannot write {pom_path}: {e}"

    artifacts = ", ".join(a for _, a, _ in mockito_coordinates(
        junit_version, java_version))
    return True, f"added {artifacts} (backup: {backup.name})"
