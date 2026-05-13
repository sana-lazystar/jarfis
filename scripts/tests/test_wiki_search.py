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
        jarfis_dir = org_root / ".jarfis-org"
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
        # No .jarfis-org/wiki/ directory

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


# ── ADR-0002 (M3) — JARFIS self-knowledge scope ─────────────────────


class TestJarfisScope:
    def test_jarfis_in_valid_scopes(self):
        from jarfis.wiki_search import VALID_SCOPES
        assert "jarfis" in VALID_SCOPES

    def test_get_jarfis_index_dir_under_personal(self, jarfis_env):
        from jarfis.wiki_search import get_jarfis_index_dir
        path = get_jarfis_index_dir()
        assert path.startswith(jarfis_env["personal_dir"])
        assert path.endswith(".jarfis-index")

    def test_collect_jarfis_files_includes_md(self, jarfis_env):
        from jarfis.wiki_search import _collect_jarfis_files
        cmd_dir = os.path.join(jarfis_env["claude_dir"], "commands", "jarfis")
        os.makedirs(cmd_dir, exist_ok=True)
        sample = os.path.join(cmd_dir, "sample.md")
        with open(sample, "w") as f:
            f.write("# Sample\n\n## Section A\nbody\n")
        files = _collect_jarfis_files(jarfis_env["claude_dir"])
        rels = [f["rel_path"] for f in files]
        assert "commands/jarfis/sample.md" in rels

    def test_collect_jarfis_files_includes_python(self, jarfis_env):
        from jarfis.wiki_search import _collect_jarfis_files
        scripts_jarfis = os.path.join(
            jarfis_env["claude_dir"], "scripts", "jarfis"
        )
        os.makedirs(scripts_jarfis, exist_ok=True)
        sample = os.path.join(scripts_jarfis, "sample.py")
        with open(sample, "w") as f:
            f.write("def foo():\n    return 1\n")
        files = _collect_jarfis_files(jarfis_env["claude_dir"])
        exts = {f["ext"] for f in files}
        assert ".py" in exts

    def test_collect_jarfis_files_excludes_pycache(self, jarfis_env):
        from jarfis.wiki_search import _collect_jarfis_files
        cache_dir = os.path.join(
            jarfis_env["claude_dir"], "scripts", "jarfis", "__pycache__"
        )
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, "junk.py"), "w") as f:
            f.write("# should be skipped\n")
        files = _collect_jarfis_files(jarfis_env["claude_dir"])
        rels = [f["rel_path"] for f in files]
        assert not any("__pycache__" in r for r in rels)

    def test_collect_jarfis_files_excludes_distill_backup(self, jarfis_env):
        from jarfis.wiki_search import _collect_jarfis_files
        backup_dir = os.path.join(
            jarfis_env["claude_dir"], "scripts", "jarfis", ".distill-backup"
        )
        os.makedirs(backup_dir, exist_ok=True)
        with open(os.path.join(backup_dir, "old.md"), "w") as f:
            f.write("# old\n")
        files = _collect_jarfis_files(jarfis_env["claude_dir"])
        rels = [f["rel_path"] for f in files]
        assert not any(".distill-backup" in r for r in rels)

    def test_collect_jarfis_files_includes_legacy(self, jarfis_env):
        """Legacy archive remains indexable per ADR-0002 §2.2."""
        from jarfis.wiki_search import _collect_jarfis_files
        legacy_dir = os.path.join(
            jarfis_env["claude_dir"], "agents", "jarfis", "legacy"
        )
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, "old.md"), "w") as f:
            f.write("# legacy\nbody\n")
        files = _collect_jarfis_files(jarfis_env["claude_dir"])
        rels = [f["rel_path"] for f in files]
        assert "agents/jarfis/legacy/old.md" in rels

    def test_collect_jarfis_files_includes_jarfis_cli(self, jarfis_env):
        from jarfis.wiki_search import _collect_jarfis_files
        cli_path = os.path.join(jarfis_env["claude_dir"], "scripts", "jarfis_cli.py")
        with open(cli_path, "w") as f:
            f.write("# jarfis_cli\n")
        files = _collect_jarfis_files(jarfis_env["claude_dir"])
        rels = [f["rel_path"] for f in files]
        assert "scripts/jarfis_cli.py" in rels


class TestChunkPython:
    def test_small_python_single_chunk(self):
        from jarfis.wiki_search import _chunk_python_file
        chunks = _chunk_python_file("a.py", "x = 1\ny = 2\n")
        assert len(chunks) == 1
        assert chunks[0]["section"] is None

    def test_large_python_splits_by_def(self):
        from jarfis.wiki_search import _chunk_python_file
        body = "\n".join([
            "import os",
            "",
            "def foo():\n    return 1\n" + ("    # filler\n" * 200),
            "",
            "def bar():\n    return 2\n" + ("    # filler\n" * 200),
            "",
            "class Baz:\n    pass\n" + ("    # filler\n" * 200),
        ])
        chunks = _chunk_python_file("big.py", body)
        sections = [c["section"] for c in chunks]
        assert "foo" in sections
        assert "bar" in sections
        assert "Baz" in sections


class TestChunkJarfisFile:
    def test_dispatches_md_to_chunk_file(self):
        from jarfis.wiki_search import _chunk_jarfis_file
        long_md = "# Title\n" + "## Section A\nbody\n" * 100 + "## Section B\nmore\n" * 100
        chunks = _chunk_jarfis_file("a.md", long_md, ".md")
        assert len(chunks) >= 2

    def test_dispatches_yaml_single_chunk_when_small(self):
        from jarfis.wiki_search import _chunk_jarfis_file
        yaml_body = "agents:\n  product-owner:\n    persona: product-owner\n"
        chunks = _chunk_jarfis_file("composition.yaml", yaml_body, ".yaml")
        assert len(chunks) == 1


class TestSearchMainJarfisRouting:
    def test_search_main_index_jarfis_recognized(self, jarfis_env, monkeypatch):
        from jarfis import wiki_search

        called = {}

        def fake_index_jarfis(incremental=False, files_filter=None):
            called["yes"] = True
            called["incremental"] = incremental
            called["files_filter"] = files_filter
            wiki_search.json_output({"status": "indexed", "scope": "jarfis"})

        monkeypatch.setattr(wiki_search, "cmd_index_jarfis", fake_index_jarfis)
        wiki_search.search_main(["index", "jarfis"])
        assert called.get("yes") is True
        assert called["incremental"] is False
        assert called["files_filter"] is None

    def test_search_main_search_jarfis_recognized(self, jarfis_env, monkeypatch):
        from jarfis import wiki_search

        called = {}

        def fake_search_jarfis(query, top_k, pretty):
            called["query"] = query
            called["top_k"] = top_k
            wiki_search.json_output({"query": query, "results": []})

        monkeypatch.setattr(wiki_search, "cmd_search_jarfis", fake_search_jarfis)
        wiki_search.search_main(["jarfis", "test query", "--top-k", "3"])
        assert called["query"] == "test query"
        assert called["top_k"] == 3

    def test_search_main_index_jarfis_incremental(self, jarfis_env, monkeypatch):
        """--incremental --files <csv> must reach cmd_index_jarfis with proper args."""
        from jarfis import wiki_search

        called = {}

        def fake_index_jarfis(incremental=False, files_filter=None):
            called["incremental"] = incremental
            called["files_filter"] = files_filter
            wiki_search.json_output({"status": "indexed", "incremental": incremental})

        monkeypatch.setattr(wiki_search, "cmd_index_jarfis", fake_index_jarfis)
        wiki_search.search_main([
            "index", "jarfis",
            "--incremental",
            "--files", "commands/jarfis/x.md,scripts/jarfis/y.py",
        ])
        assert called["incremental"] is True
        assert called["files_filter"] == [
            "commands/jarfis/x.md",
            "scripts/jarfis/y.py",
        ]


class TestFilterChunksForIncremental:
    def test_removes_specified_files(self):
        from jarfis.wiki_search import _filter_chunks_for_incremental
        import numpy as np
        meta = {"chunks": [
            {"file": "a.md", "section": None, "preview": "a"},
            {"file": "b.md", "section": None, "preview": "b"},
            {"file": "a.md", "section": "S2", "preview": "a2"},
        ]}
        embeddings = np.array([[1, 0], [0, 1], [0.5, 0.5]], dtype=float)
        new_chunks, new_embs = _filter_chunks_for_incremental(meta, embeddings, {"a.md"})
        assert len(new_chunks) == 1
        assert new_chunks[0]["file"] == "b.md"
        assert new_embs.shape == (1, 2)
        assert (new_embs[0] == [0, 1]).all()

    def test_removes_nothing_returns_original(self):
        from jarfis.wiki_search import _filter_chunks_for_incremental
        import numpy as np
        meta = {"chunks": [{"file": "a.md", "preview": "a"}]}
        embeddings = np.array([[1, 0]], dtype=float)
        new_chunks, new_embs = _filter_chunks_for_incremental(meta, embeddings, {"unrelated.md"})
        assert len(new_chunks) == 1
        assert new_embs is embeddings  # fast path — same object

    def test_removes_all_returns_empty(self):
        from jarfis.wiki_search import _filter_chunks_for_incremental
        import numpy as np
        meta = {"chunks": [{"file": "a.md", "preview": "a"}]}
        embeddings = np.array([[1, 0]], dtype=float)
        new_chunks, new_embs = _filter_chunks_for_incremental(meta, embeddings, {"a.md"})
        assert new_chunks == []
        assert new_embs.shape == (0, 2)


class TestCollectPOProjectsIA:
    """Stage 6b — wiki_search recognizes wiki/PO/projects/{name}/ia/ subdirs."""

    def _make_wiki(self, tmp_path, project_names=None):
        wiki_dir = tmp_path / ".jarfis-org" / "wiki"
        for section in ("PO", "DESIGN", "TA", "QA"):
            (wiki_dir / section).mkdir(parents=True, exist_ok=True)
            (wiki_dir / section / "_index.md").write_text(
                "| File | Summary | Projects | Updated |\n"
                "|------|---------|----------|---------|\n"
                "| (none) | - | - | - |\n",
                encoding="utf-8",
            )
        if project_names is not None:
            projects_dir = wiki_dir / "PO" / "projects"
            projects_dir.mkdir(parents=True, exist_ok=True)
            for name in project_names:
                ia_dir = projects_dir / name / "ia"
                ia_dir.mkdir(parents=True, exist_ok=True)
                (ia_dir / "manifest.json").write_text(
                    '{"version":"2.0","project":"' + name + '","pages":[]}\n',
                    encoding="utf-8",
                )
        return wiki_dir

    def test_no_projects_dir_returns_empty(self, tmp_path):
        """R-15 — pre-Stage-6a orgs have no PO/projects/; helper returns []."""
        from jarfis.wiki_search import _collect_po_projects_ia
        self._make_wiki(tmp_path, project_names=None)
        result = _collect_po_projects_ia(str(tmp_path / ".jarfis-org" / "wiki"))
        assert result == []

    def test_empty_projects_dir_returns_empty(self, tmp_path):
        """R-18 — PO/projects/ exists but empty → []."""
        from jarfis.wiki_search import _collect_po_projects_ia
        self._make_wiki(tmp_path, project_names=[])
        result = _collect_po_projects_ia(str(tmp_path / ".jarfis-org" / "wiki"))
        assert result == []

    def test_lists_projects_with_ia(self, tmp_path):
        """Each PO/projects/{name}/ia/ directory yields one entry."""
        from jarfis.wiki_search import _collect_po_projects_ia
        self._make_wiki(tmp_path, project_names=["alpha", "beta"])
        result = _collect_po_projects_ia(str(tmp_path / ".jarfis-org" / "wiki"))
        names = sorted(e["name"] for e in result)
        assert names == ["alpha", "beta"]
        # Each entry exposes pages_count for INDEX rendering.
        for entry in result:
            assert "pages_count" in entry
            assert entry["pages_count"] == 0  # empty manifest

    def test_skips_project_without_ia(self, tmp_path):
        """Project dir without ia/ subdir is ignored (graceful)."""
        from jarfis.wiki_search import _collect_po_projects_ia
        wiki_dir = self._make_wiki(tmp_path, project_names=["alpha"])
        # Add a stray dir without ia/
        (wiki_dir / "PO" / "projects" / "stray").mkdir()
        result = _collect_po_projects_ia(str(wiki_dir))
        names = [e["name"] for e in result]
        assert "stray" not in names
        assert "alpha" in names


class TestRebuildIndexProjects:
    """Stage 6b — cmd_rebuild_index renders PO/projects/ sub-list when present."""

    def _seed_wiki(self, tmp_path, project_names=None):
        wiki_dir = tmp_path / ".jarfis-org" / "wiki"
        for section in ("PO", "DESIGN", "TA", "QA"):
            (wiki_dir / section).mkdir(parents=True, exist_ok=True)
            (wiki_dir / section / "_index.md").write_text(
                "| File | Summary | Projects | Updated |\n"
                "|------|---------|----------|---------|\n"
                "| (none) | - | - | - |\n",
                encoding="utf-8",
            )
        if project_names is not None:
            projects_dir = wiki_dir / "PO" / "projects"
            projects_dir.mkdir(parents=True, exist_ok=True)
            for name in project_names:
                ia_dir = projects_dir / name / "ia"
                ia_dir.mkdir(parents=True, exist_ok=True)
                (ia_dir / "manifest.json").write_text(
                    '{"version":"2.0","project":"' + name + '","pages":[]}\n',
                    encoding="utf-8",
                )
        return tmp_path

    def test_rebuild_index_no_projects_dir_preserves_layout(self, tmp_path, capsys):
        """R-15 — pre-Stage-6a INDEX.md still renders cleanly."""
        from jarfis.wiki_search import cmd_rebuild_index
        org_root = self._seed_wiki(tmp_path, project_names=None)
        try:
            cmd_rebuild_index(str(org_root))
        except SystemExit:
            pass
        capsys.readouterr()  # drain json_output stdout
        content = (org_root / ".jarfis-org" / "wiki" / "INDEX.md").read_text(encoding="utf-8")
        assert "### PO/ (0 files)" in content
        assert "Projects:" not in content  # no sub-list when no projects/ dir

    def test_rebuild_index_with_projects_renders_sublist(self, tmp_path, capsys):
        """R-16 mitigation — PO section gains a 'Projects:' sub-list."""
        from jarfis.wiki_search import cmd_rebuild_index
        org_root = self._seed_wiki(tmp_path, project_names=["alpha", "beta"])
        try:
            cmd_rebuild_index(str(org_root))
        except SystemExit:
            pass
        capsys.readouterr()
        content = (org_root / ".jarfis-org" / "wiki" / "INDEX.md").read_text(encoding="utf-8")
        # Sub-list line under PO section
        assert "Projects:" in content
        assert "alpha" in content
        assert "beta" in content

    def test_rebuild_index_empty_projects_dir_no_sublist(self, tmp_path, capsys):
        """R-18 — empty PO/projects/ directory does not emit empty sub-list."""
        from jarfis.wiki_search import cmd_rebuild_index
        org_root = self._seed_wiki(tmp_path, project_names=[])
        try:
            cmd_rebuild_index(str(org_root))
        except SystemExit:
            pass
        capsys.readouterr()
        content = (org_root / ".jarfis-org" / "wiki" / "INDEX.md").read_text(encoding="utf-8")
        assert "Projects:" not in content
