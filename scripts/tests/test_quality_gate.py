"""Tests for jarfis.quality_gate — lint/typecheck on edited files."""

import json
import os

import pytest

from jarfis.quality_gate import (
    ALL_CHECKABLE,
    find_project_root,
    has_biome,
    check_file,
    main,
)


class TestFindProjectRoot:
    def test_finds_package_json(self, project_dir):
        subdir = os.path.join(project_dir, "src", "components")
        os.makedirs(subdir)
        result = find_project_root(os.path.join(subdir, "App.tsx"))
        assert result == project_dir

    def test_returns_none_when_not_found(self, tmp_path):
        result = find_project_root(str(tmp_path / "orphan.ts"))
        assert result is None


class TestHasBiome:
    def test_detects_biome_json(self, tmp_path):
        (tmp_path / "biome.json").write_text("{}")
        assert has_biome(str(tmp_path)) is True

    def test_detects_biome_jsonc(self, tmp_path):
        (tmp_path / "biome.jsonc").write_text("{}")
        assert has_biome(str(tmp_path)) is True

    def test_no_biome(self, tmp_path):
        assert has_biome(str(tmp_path)) is False


class TestCheckFile:
    def test_skips_non_checkable_extension(self, tmp_path):
        results, skipped = check_file(str(tmp_path / "file.py"))
        assert skipped is True
        assert results == []

    def test_skips_when_no_package_json(self, tmp_path):
        results, skipped = check_file(str(tmp_path / "file.ts"))
        assert skipped is True

    def test_all_checkable_extensions(self):
        assert ".ts" in ALL_CHECKABLE
        assert ".tsx" in ALL_CHECKABLE
        assert ".js" in ALL_CHECKABLE
        assert ".json" in ALL_CHECKABLE
        assert ".css" in ALL_CHECKABLE
        assert ".py" not in ALL_CHECKABLE


class TestMain:
    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            main([])
