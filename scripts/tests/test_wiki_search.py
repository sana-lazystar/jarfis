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
    SCORE_THRESHOLD,
    _chunk_file,
    _collect_wiki_files,
    _estimate_tokens,
    _strip_frontmatter,
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


class TestCollectWikiFiles:
    def test_collects_md_files(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        (wiki / "file1.md").write_text("# File 1")
        (wiki / "file2.md").write_text("# File 2")
        (wiki / "ignore.txt").write_text("not markdown")
        sub = wiki / "PO"
        sub.mkdir()
        (sub / "decisions.md").write_text("# Decisions")

        files = _collect_wiki_files(str(wiki))
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

        files = _collect_wiki_files(str(wiki))
        assert len(files) == 1

    def test_empty_directory(self, tmp_path):
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        files = _collect_wiki_files(str(wiki))
        assert files == []

    def test_nonexistent_directory(self, tmp_path):
        files = _collect_wiki_files(str(tmp_path / "nonexistent"))
        assert files == []


class TestConstants:
    def test_chunk_threshold_reasonable(self):
        assert CHUNK_TOKEN_THRESHOLD == 500

    def test_score_threshold_reasonable(self):
        assert 0.0 < SCORE_THRESHOLD < 1.0
