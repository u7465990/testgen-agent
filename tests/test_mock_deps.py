"""Tests for mock_deps.py — the one path that writes into someone else's project.

Everywhere else the agent is read-only. `--add-mock-deps` is the explicit
opt-in that edits a target `pom.xml`, which makes this the highest-stakes
module in the repo, and until now it had no tests at all.

The invariants worth pinning are exactly the ones its docstring claims:
idempotent, backed up once and only once, inserted as text rather than
round-tripped through a DOM, and validated before the write is kept. Each of
those is a promise about *not* damaging a file the user did not hand us to
modify, so each gets a test rather than a comment.
"""

from __future__ import annotations

from pathlib import Path
from xml.dom import minidom

import pytest

from mock_deps import (
    BACKUP_SUFFIX,
    inject_mockito_dependency,
    mockito_coordinates,
    pom_has_mockito,
    strip_xml_comments,
)

POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.demo</groupId>
  <artifactId>demo</artifactId>
  <version>1.0</version>
  <dependencies>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
</project>
"""


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _pom(tmp_path: Path, text: str = POM) -> Path:
    return _write(tmp_path / "pom.xml", text)


class TestMockitoCoordinates:
    def test_junit4_gets_mockito_core_alone(self):
        # mockito-junit-jupiter pulls junit-jupiter-api transitively, and that is
        # one of the signals target_profile uses to detect JUnit 5. Declaring it
        # on a JUnit 4 project would make the *next* run misdetect the framework.
        artifacts = [artifact for _, artifact, _ in mockito_coordinates(4, 8)]
        assert artifacts == ["mockito-core"]

    def test_junit5_also_gets_the_jupiter_bridge(self):
        artifacts = [artifact for _, artifact, _ in mockito_coordinates(5, 17)]
        assert artifacts == ["mockito-core", "mockito-junit-jupiter"]

    @pytest.mark.parametrize("java_version", [11, 17, 21])
    def test_modern_java_gets_mockito_5(self, java_version):
        assert mockito_coordinates(4, java_version)[0][2].startswith("5.")

    @pytest.mark.parametrize("java_version", [7, 8])
    def test_java_8_and_below_pin_mockito_4(self, java_version):
        # Mockito 5 requires Java 11+, so picking the coordinate off the detected
        # Java level is what keeps an older project compiling.
        assert mockito_coordinates(4, java_version)[0][2].startswith("4.")

    def test_the_boundary_sits_at_java_8(self):
        # Pinned deliberately: 8 still gets Mockito 4. If this ever moves, the
        # Java 8 demo stops compiling, so the boundary is worth a test.
        assert mockito_coordinates(4, 8)[0][2].startswith("4.")
        assert mockito_coordinates(4, 9)[0][2].startswith("5.")


class TestStripXmlComments:
    def test_removes_a_commented_out_dependency(self):
        text = "<a><!-- <artifactId>mockito-core</artifactId> --></a>"
        assert "mockito-core" not in strip_xml_comments(text)

    def test_removes_multiline_comments(self):
        text = "<a><!--\n  <artifactId>mockito-core</artifactId>\n--></a>"
        assert "mockito-core" not in strip_xml_comments(text)

    def test_leaves_real_content_alone(self):
        text = "<a><artifactId>junit</artifactId></a>"
        assert "junit" in strip_xml_comments(text)


class TestPomHasMockito:
    def test_missing_file_is_not_a_declaration(self, tmp_path):
        assert pom_has_mockito(tmp_path / "nope.xml") is False

    @pytest.mark.parametrize(
        "artifact", ["mockito-core", "mockito-junit-jupiter"]
    )
    def test_either_artifact_counts(self, tmp_path, artifact):
        pom = _pom(tmp_path, POM.replace("</dependencies>",
                                         f"<x>{artifact}</x></dependencies>"))
        assert pom_has_mockito(pom) is True

    def test_a_commented_out_dependency_does_not_count(self, tmp_path):
        # The reason strip_xml_comments exists: a pom with Mockito commented out
        # must still receive the real dependency, not be told it already has it.
        pom = _pom(tmp_path, POM.replace(
            "</dependencies>",
            "<!-- <artifactId>mockito-core</artifactId> --></dependencies>",
        ))
        assert pom_has_mockito(pom) is False

    def test_an_unrelated_pom_is_false(self, tmp_path):
        assert pom_has_mockito(_pom(tmp_path)) is False


class TestInjectMockitoDependency:
    def test_inserts_before_the_closing_dependencies_tag(self, tmp_path):
        pom = _pom(tmp_path)
        changed, message = inject_mockito_dependency(pom, 4, 8)
        assert changed is True and "mockito-core" in message
        text = pom.read_text(encoding="utf-8")
        assert text.count("<artifactId>mockito-core</artifactId>") == 1
        # Inside <dependencies>, before the close.
        assert text.index("mockito-core") < text.index("</dependencies>")

    def test_the_inserted_dependency_is_test_scoped(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        block = pom.read_text(encoding="utf-8")
        start = block.index("<artifactId>mockito-core</artifactId>")
        assert "<scope>test</scope>" in block[start:start + 300]

    def test_result_is_well_formed_xml(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        minidom.parseString(pom.read_text(encoding="utf-8"))  # must not raise

    def test_the_xml_declaration_survives(self, tmp_path):
        # The reason it is text insertion, not a DOM round-trip: re-serialising
        # through a parser drops the declaration and reformats the whole file.
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        assert pom.read_text(encoding="utf-8").startswith(
            '<?xml version="1.0" encoding="UTF-8"?>'
        )

    def test_the_rest_of_the_file_is_untouched(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        text = pom.read_text(encoding="utf-8")
        for line in POM.splitlines():
            assert line in text, line      # every original line still present

    def test_falls_back_to_a_new_dependencies_block_before_build(self, tmp_path):
        pom = _pom(tmp_path, """<?xml version="1.0"?>
<project>
  <build><plugins/></build>
</project>
""")
        changed, _ = inject_mockito_dependency(pom, 4, 8)
        assert changed is True
        text = pom.read_text(encoding="utf-8")
        assert "<dependencies>" in text
        assert text.index("<dependencies>") < text.index("<build>")
        minidom.parseString(text)

    def test_falls_back_before_the_closing_project_tag(self, tmp_path):
        pom = _pom(tmp_path, '<?xml version="1.0"?>\n<project></project>\n')
        changed, _ = inject_mockito_dependency(pom, 4, 8)
        assert changed is True
        text = pom.read_text(encoding="utf-8")
        assert text.index("<dependencies>") < text.index("</project>")
        minidom.parseString(text)

    def test_junit5_pulls_in_both_artifacts(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 5, 17)
        text = pom.read_text(encoding="utf-8")
        assert "mockito-core" in text and "mockito-junit-jupiter" in text

    def test_reports_what_it_added(self, tmp_path):
        pom = _pom(tmp_path)
        _, message = inject_mockito_dependency(pom, 4, 8)
        assert "mockito-core" in message
        assert BACKUP_SUFFIX in message          # names the backup it made


class TestInjectRefuses:
    """Every refusal is a promise that a build file was left byte-identical."""

    def test_missing_pom(self, tmp_path):
        changed, message = inject_mockito_dependency(
            tmp_path / "pom.xml", 4, 8
        )
        assert changed is False and "no pom.xml" in message

    def test_already_declared(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        changed, message = inject_mockito_dependency(pom, 4, 8)
        assert changed is False and "already declared" in message

    def test_a_pom_it_cannot_anchor_into_is_left_alone(self, tmp_path):
        pom = _pom(tmp_path, "<project>\n")
        before = pom.read_text(encoding="utf-8")
        changed, message = inject_mockito_dependency(pom, 4, 8)
        assert changed is False
        assert "</dependencies>" in message      # says what it looked for
        assert pom.read_text(encoding="utf-8") == before

    def test_refuses_when_the_result_would_not_parse(self, tmp_path, monkeypatch):
        # Validation exists so a bad insertion never reaches disk. An unclosed
        # tag is injected rather than hoping a real pom happens to produce one.
        import mock_deps

        pom = _pom(tmp_path)
        before = pom.read_text(encoding="utf-8")
        monkeypatch.setattr(
            mock_deps, "_dependency_block", lambda coords: "<unclosed>"
        )

        changed, message = inject_mockito_dependency(pom, 4, 8)

        assert changed is False
        assert "refusing to write a malformed pom.xml" in message
        assert pom.read_text(encoding="utf-8") == before

    def test_an_unreadable_pom_is_reported_not_raised(self, tmp_path, monkeypatch):
        pom = _pom(tmp_path)
        real = Path.read_text

        def refuse(self, *args, **kwargs):
            if self == pom:
                raise OSError("permission denied")
            return real(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", refuse)
        changed, message = inject_mockito_dependency(pom, 4, 8)
        assert changed is False and "cannot read" in message

    def test_an_unwritable_pom_is_reported_not_raised(self, tmp_path, monkeypatch):
        # The backup is created first, so this exercises the write failing after
        # a successful backup — the file on disk must be left as it was.
        pom = _pom(tmp_path)
        real = Path.write_text

        def refuse(self, *args, **kwargs):
            if self == pom:
                raise OSError("read-only filesystem")
            return real(self, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", refuse)
        changed, message = inject_mockito_dependency(pom, 4, 8)
        assert changed is False and "cannot write" in message

    def test_an_unreadable_pom_is_not_a_declaration(self, tmp_path, monkeypatch):
        pom = _pom(tmp_path)
        monkeypatch.setattr(
            Path, "read_text",
            lambda self, *a, **k: (_ for _ in ()).throw(OSError("nope")),
        )
        assert pom_has_mockito(pom) is False

    def test_a_readonly_backup_location_is_reported_not_raised(
        self, tmp_path, monkeypatch
    ):
        import shutil

        import mock_deps

        pom = _pom(tmp_path)
        before = pom.read_text(encoding="utf-8")

        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(shutil, "copy2", boom)
        changed, message = inject_mockito_dependency(pom, 4, 8)
        assert changed is False and "cannot create backup" in message
        assert pom.read_text(encoding="utf-8") == before


class TestBackupBehaviour:
    def test_a_backup_holds_the_pristine_original(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        backup = pom.with_name(pom.name + BACKUP_SUFFIX)
        assert backup.is_file()
        assert backup.read_text(encoding="utf-8") == POM

    def test_the_backup_is_never_overwritten_by_a_later_run(self, tmp_path):
        # The guard that matters: re-running must not replace the pristine
        # original with an already-modified file. Reached by removing Mockito
        # again (as a user reverting would) and changing something else.
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        backup = pom.with_name(pom.name + BACKUP_SUFFIX)
        assert backup.read_text(encoding="utf-8") == POM

        edited = POM.replace("<version>1.0</version>", "<version>2.0</version>")
        _write(pom, edited)
        inject_mockito_dependency(pom, 4, 8)

        assert backup.read_text(encoding="utf-8") == POM      # still pristine
        assert "2.0" in pom.read_text(encoding="utf-8")

    def test_repeated_runs_do_not_duplicate_the_dependency(self, tmp_path):
        pom = _pom(tmp_path)
        inject_mockito_dependency(pom, 4, 8)
        inject_mockito_dependency(pom, 4, 8)
        inject_mockito_dependency(pom, 4, 8)
        text = pom.read_text(encoding="utf-8")
        assert text.count("<artifactId>mockito-core</artifactId>") == 1
