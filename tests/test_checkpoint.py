"""Tests for checkpoint.py — the JSONL resume log.

A resumed run has to rebuild a report identical to a full run, which is why a
record stores the whole MethodInfo rather than just its name. The tolerance for
a malformed line is deliberate too: an interrupted run leaves a half-written
line, and that must not make the checkpoint unloadable.
"""

from __future__ import annotations

from checkpoint import append_checkpoint, load_checkpoint, make_record
from method_extractor import MethodInfo


class TestLoadCheckpoint:
    def test_missing_file_is_empty(self, tmp_path):
        assert load_checkpoint(tmp_path / "nope.jsonl") == {}

    def test_round_trip(self, tmp_path, make_method):
        path = tmp_path / "checkpoint.jsonl"
        record = make_record(
            make_method(),
            "Calculator_add_int_int_Test_Normal_0",
            tmp_path / "Foo.java",
            "[Normal] t",
        )
        append_checkpoint(path, record)

        done = load_checkpoint(path)
        key = "Calculator_add_int_int_Test_Normal_0"
        assert key in done
        assert done[key]["target"] == "[Normal] t"

    def test_method_info_survives_the_round_trip(self, tmp_path, make_method):
        # agent.py rebuilds resumed methods with MethodInfo(**record["method"]),
        # so every field has to survive asdict -> json.dumps -> json.loads.
        path = tmp_path / "checkpoint.jsonl"
        method = make_method(branch_conditions=["a > 0"])
        append_checkpoint(
            path, make_record(method, "C_0", tmp_path / "F.java", "t")
        )
        rebuilt = MethodInfo(**load_checkpoint(path)["C_0"]["method"])
        assert rebuilt == method

    def test_malformed_line_is_skipped(self, tmp_path):
        path = tmp_path / "checkpoint.jsonl"
        path.write_text(
            '{"class_name": "Good_0"}\n'
            "not json at all\n"
            "\n"
            '{"class_name": "AlsoGood_0"}\n',
            encoding="utf-8",
        )
        assert set(load_checkpoint(path)) == {"Good_0", "AlsoGood_0"}

    def test_record_without_class_name_is_ignored(self, tmp_path):
        path = tmp_path / "checkpoint.jsonl"
        path.write_text('{"target": "t"}\n', encoding="utf-8")
        assert load_checkpoint(path) == {}

    def test_appends_accumulate(self, tmp_path, make_method):
        path = tmp_path / "checkpoint.jsonl"
        for i in range(3):
            append_checkpoint(
                path, make_record(make_method(), f"C_{i}", tmp_path / "F.java", "t")
            )
        assert len(load_checkpoint(path)) == 3

    def test_creates_the_parent_directory(self, tmp_path, make_method):
        path = tmp_path / "nested" / "deep" / "checkpoint.jsonl"
        append_checkpoint(
            path, make_record(make_method(), "C_0", tmp_path / "F.java", "t")
        )
        assert path.is_file()
