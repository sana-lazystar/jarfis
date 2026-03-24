"""Tests for jarfis.measure — prompt file token measurement."""

import json
import os

import pytest

from jarfis.measure import main


class TestMeasure:
    def test_measures_markdown_files(self, tmp_path, capsys, jarfis_env):
        md_dir = tmp_path / "prompts"
        md_dir.mkdir()
        (md_dir / "test1.md").write_text("# Hello\n\nThis is a test file.\n")
        (md_dir / "test2.md").write_text("# World\n\nAnother file.\n")

        main([str(md_dir)])
        output = json.loads(capsys.readouterr().out)
        assert output["total"]["files"] == 2
        assert output["total"]["lines"] > 0
        assert output["total"]["chars"] > 0
        assert output["total"]["tokens_est"] > 0

    def test_excludes_files(self, tmp_path, capsys, jarfis_env):
        md_dir = tmp_path / "prompts"
        md_dir.mkdir()
        (md_dir / "keep.md").write_text("# Keep")
        (md_dir / "skip.md").write_text("# Skip")

        main(["--exclude", "skip.md", str(md_dir)])
        output = json.loads(capsys.readouterr().out)
        assert output["total"]["files"] == 1
        names = [f["name"] for f in output["files"]]
        assert "keep.md" in names
        assert "skip.md" not in names

    def test_diagnostics_mode(self, tmp_path, capsys, jarfis_env):
        md_dir = tmp_path / "prompts"
        md_dir.mkdir()
        content = "# Title\n\n## Section 1\n\n```python\nprint('hello')\n```\n\n## Section 2\n"
        (md_dir / "test.md").write_text(content)

        main(["--diagnostics", str(md_dir)])
        output = json.loads(capsys.readouterr().out)
        assert output["files"][0]["diagnostics"]["codeblock_lines"] == 1
        assert len(output["files"][0]["diagnostics"]["headers"]) >= 2

    def test_index_mismatch_check(self, tmp_path, capsys, jarfis_env):
        md_dir = tmp_path / "prompts"
        md_dir.mkdir()
        (md_dir / "existing.md").write_text("# Existing")

        index = tmp_path / "index.md"
        index.write_text("## Files\n- existing.md\n- missing.md\n")

        main(["--index", str(index), str(md_dir)])
        output = json.loads(capsys.readouterr().out)
        assert any("missing_on_disk:missing.md" in m for m in output.get("index_mismatches", []))

    def test_empty_directory(self, tmp_path, capsys, jarfis_env):
        empty = tmp_path / "empty"
        empty.mkdir()
        main([str(empty)])
        output = json.loads(capsys.readouterr().out)
        assert output["total"]["files"] == 0

    def test_skips_distill_backup(self, tmp_path, capsys, jarfis_env):
        md_dir = tmp_path / "prompts"
        md_dir.mkdir()
        (md_dir / "keep.md").write_text("# Keep")
        backup = md_dir / ".distill-backup"
        backup.mkdir()
        (backup / "old.md").write_text("# Old backup")

        main([str(md_dir)])
        output = json.loads(capsys.readouterr().out)
        assert output["total"]["files"] == 1
