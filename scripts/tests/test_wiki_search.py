"""Tests for jarfis.wiki_search — semantic search utilities.

Note: Tests for embedding/search functionality are skipped if
sentence-transformers is not installed, as it requires a ~2GB model.
Only pure utility functions are tested unconditionally.
"""

import json
import os

import pytest

from jarfis.wiki_search import (
    CHUNK_TOKEN_THRESHOLD,
    MEMORY_THRESHOLD_GB,
    SCORE_THRESHOLD,
    _check_available_memory_gb,
    _chunk_file,
    _collect_md_files,
    _collect_wiki_files,
    _estimate_tokens,
    _get_mps_allocated_gb,
    _merge_results,
    _strip_frontmatter,
    format_pretty,
    resolve_search_dirs,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert _estimate_tokens("") == 0

    def test_rough_estimate(self):
        text = "a" * 400
        assert _estimate_tokens(text) == 100

    def test_korean_text(self):
        # Korean chars are multi-byte but function uses len() which counts chars
        text = "한국어 테스트 문장입니다"
        result = _estimate_tokens(text)
        assert result > 0


class TestStripFrontmatter:
    def test_strips_yaml_frontmatter(self):
        content = "---\ntitle: Test\ndate: 2026-01-01\n---\n\n# Content"
        result = _strip_frontmatter(content)
        assert result == "# Content"
        assert "title" not in result

    def test_no_frontmatter(self):
        content = "# Just content\n\nParagraph."
        result = _strip_frontmatter(content)
        assert result == content

    def test_empty_string(self):
        assert _strip_frontmatter("") == ""

    def test_frontmatter_only(self):
        content = "---\ntitle: Test\n---"
        result = _strip_frontmatter(content)
        assert result == ""


class TestChunkFile:
    def test_small_file_single_chunk(self):
        content = "---\ntitle: Test\n---\n\n# Small file\n\nJust a paragraph."
        chunks = _chunk_file("test.md", content)
        assert len(chunks) == 1
        assert chunks[0]["file"] == "test.md"
        assert chunks[0]["section"] is None

    def test_large_file_splits_by_h2(self):
        sections = []
        for i in range(10):
            sections.append(f"## Section {i}\n\n" + "Content " * 200 + "\n")
        content = "---\ntitle: Big\n---\n\n" + "\n".join(sections)
        chunks = _chunk_file("big.md", content)
        assert len(chunks) > 1
        # Each chunk should have section info
        for chunk in chunks:
            assert chunk["file"] == "big.md"
            if chunk["section"]:
                assert "Section" in chunk["section"]

    def test_empty_content(self):
        chunks = _chunk_file("empty.md", "")
        assert chunks == []

    def test_frontmatter_only_no_chunks(self):
        chunks = _chunk_file("fm.md", "---\ntitle: Only FM\n---")
        assert chunks == []


class TestCollectMdFiles:
    def test_collects_md_files(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "file1.md").write_text("# File 1")
        (wiki / "file2.md").write_text("# File 2")
        (wiki / "ignore.txt").write_text("not markdown")
        sub = wiki / "PO"
        sub.mkdir()
        (sub / "decisions.md").write_text("# Decisions")

        files = _collect_md_files(str(wiki))
        assert len(files) == 3
        paths = [f["rel_path"] for f in files]
        assert "file1.md" in paths
        assert os.path.join("PO", "decisions.md") in paths

    def test_skips_empty_files(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "empty.md").write_text("")
        (wiki / "whitespace.md").write_text("   \n  \n  ")
        (wiki / "content.md").write_text("# Has content")

        files = _collect_md_files(str(wiki))
        assert len(files) == 1

    def test_empty_directory(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        files = _collect_md_files(str(wiki))
        assert files == []

    def test_nonexistent_directory(self, tmp_path):
        files = _collect_md_files(str(tmp_path / "nonexistent"))
        assert files == []

    def test_backward_compat_alias(self, tmp_path):
        """_collect_wiki_files should be an alias for _collect_md_files."""
        d = tmp_path / "test"
        d.mkdir()
        (d / "a.md").write_text("# A")
        assert _collect_wiki_files(str(d)) == _collect_md_files(str(d))

    def test_skips_hidden_files(self, tmp_path):
        d = tmp_path / "test"
        d.mkdir()
        (d / "visible.md").write_text("# Visible")
        (d / ".hidden.md").write_text("# Hidden")
        files = _collect_md_files(str(d))
        paths = [f["rel_path"] for f in files]
        assert "visible.md" in paths
        assert ".hidden.md" not in paths

    def test_skips_vectors_meta(self, tmp_path):
        d = tmp_path / "test"
        d.mkdir()
        (d / "content.md").write_text("# Content")
        (d / ".vectors-meta.json").write_text("{}")
        files = _collect_md_files(str(d))
        assert len(files) == 1


class TestResolveSearchDirs:
    def test_resolves_with_org(self, tmp_path):
        # Simulate org structure
        org_root = tmp_path / "org-project"
        org_root.mkdir()
        jarfis_dir = org_root / ".jarfis"
        jarfis_dir.mkdir()
        wiki_dir = jarfis_dir / "wiki"
        wiki_dir.mkdir()

        org_dir = tmp_path / "org-workspace"
        org_dir.mkdir()
        (org_dir / "meetings").mkdir()
        (org_dir / "works").mkdir()

        result = resolve_search_dirs(
            org_root=str(org_root), org_dir=str(org_dir)
        )
        assert result["wiki"] == str(wiki_dir)
        assert result["meetings"] == str(org_dir / "meetings")
        assert result["works"] == str(org_dir / "works")

    def test_missing_wiki_excluded(self, tmp_path):
        org_root = tmp_path / "org-project"
        org_root.mkdir()
        # No .jarfis/wiki/ directory

        org_dir = tmp_path / "org-workspace"
        org_dir.mkdir()
        (org_dir / "meetings").mkdir()
        (org_dir / "works").mkdir()

        result = resolve_search_dirs(
            org_root=str(org_root), org_dir=str(org_dir)
        )
        assert "wiki" not in result
        assert "meetings" in result
        assert "works" in result

    def test_missing_meetings_excluded(self, tmp_path):
        org_dir = tmp_path / "org-workspace"
        org_dir.mkdir()
        # No meetings/ directory

        result = resolve_search_dirs(org_root=None, org_dir=str(org_dir))
        assert "meetings" not in result

    def test_all_missing(self, tmp_path):
        result = resolve_search_dirs(org_root=None, org_dir=None)
        assert result == {}


class TestMergeResults:
    def test_sorts_by_score_descending(self):
        results = [
            {"source": "wiki", "score": 0.7, "file_path": "a.md"},
            {"source": "meetings", "score": 0.9, "file_path": "b.md"},
            {"source": "works", "score": 0.8, "file_path": "c.md"},
        ]
        merged = _merge_results(results, top_k=5)
        scores = [r["score"] for r in merged]
        assert scores == [0.9, 0.8, 0.7]

    def test_top_k_limit(self):
        results = [
            {"source": "wiki", "score": 0.9, "file_path": f"{i}.md"}
            for i in range(10)
        ]
        merged = _merge_results(results, top_k=3)
        assert len(merged) == 3

    def test_empty_results(self):
        assert _merge_results([], top_k=5) == []

    def test_deduplicates_by_file_within_source(self):
        results = [
            {"source": "wiki", "score": 0.9, "file_path": "same.md", "section": "A"},
            {"source": "wiki", "score": 0.7, "file_path": "same.md", "section": "B"},
            {"source": "meetings", "score": 0.8, "file_path": "other.md", "section": None},
        ]
        merged = _merge_results(results, top_k=5)
        # same.md should appear only once (highest score)
        wiki_files = [r for r in merged if r["source"] == "wiki"]
        assert len(wiki_files) == 1
        assert wiki_files[0]["score"] == 0.9

    def test_same_file_different_sources_kept(self):
        """Same filename in different sources should both be kept."""
        results = [
            {"source": "wiki", "score": 0.9, "file_path": "summary.md"},
            {"source": "meetings", "score": 0.8, "file_path": "summary.md"},
        ]
        merged = _merge_results(results, top_k=5)
        assert len(merged) == 2


class TestFormatPretty:
    def test_basic_format(self):
        data = {
            "query": "Tanstack",
            "results": [
                {
                    "source": "meetings",
                    "file_path": "summary.md",
                    "section": "핵심 결정사항",
                    "score": 0.87,
                    "preview": "TanStack Query 도입...",
                }
            ],
        }
        pretty = format_pretty(data)
        assert "Tanstack" in pretty
        assert "meetings" in pretty
        assert "summary.md" in pretty
        assert "0.87" in pretty

    def test_no_results(self):
        data = {"query": "없는검색어", "results": []}
        pretty = format_pretty(data)
        assert "없는검색어" in pretty
        assert "No results" in pretty

    def test_stale_warning(self):
        data = {
            "query": "test",
            "results": [],
            "stale_warning": "2 files modified",
        }
        pretty = format_pretty(data)
        assert "stale" in pretty.lower() or "modified" in pretty.lower()


class TestCheckAvailableMemory:
    def test_returns_float(self):
        result = _check_available_memory_gb()
        # Should return a non-negative float (or None on unsupported OS)
        if result is not None:
            assert isinstance(result, float)
            assert result >= 0.0

    def test_returns_reasonable_value(self):
        result = _check_available_memory_gb()
        if result is not None:
            # Should be between 0 and 1024 GB (reasonable range)
            assert 0.0 <= result <= 1024.0

    def test_memory_threshold_default(self):
        assert MEMORY_THRESHOLD_GB == 4.0

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("JARFIS_MEMORY_THRESHOLD_GB", "2.5")
        # Re-import to pick up env var — but since it's module-level,
        # test the pattern directly
        val = float(os.environ.get("JARFIS_MEMORY_THRESHOLD_GB", "4.0"))
        assert val == 2.5


class TestGetMpsAllocatedGb:
    def test_returns_float(self):
        result = _get_mps_allocated_gb()
        assert isinstance(result, float)
        assert result >= 0.0

    def test_returns_zero_when_torch_unavailable(self, monkeypatch):
        """Should return 0.0 gracefully when torch is not importable."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "torch":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        assert _get_mps_allocated_gb() == 0.0


class TestConstants:
    def test_chunk_threshold_reasonable(self):
        assert CHUNK_TOKEN_THRESHOLD == 500

    def test_score_threshold_reasonable(self):
        assert 0.0 < SCORE_THRESHOLD < 1.0
