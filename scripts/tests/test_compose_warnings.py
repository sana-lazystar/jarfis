"""Tests for compose `missing_sections` stderr warning (v4.0.4 N-3).

The compose CLI emits a per-block stderr line when a context entry's
`sections:` filter in agent-composition.yaml refers to a heading that does
not exist in the target file. The meta JSON keeps the canonical record; the
stderr warning exists only so humans running compose interactively notice
a stale yaml mapping immediately.
"""

import io
import sys

from jarfis.compose.__main__ import _emit_missing_sections_warnings


class TestMissingSectionsWarning:
    def test_emits_warning_for_each_block_with_missing_sections(self, monkeypatch):
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", buf)

        meta = [
            {
                "path": ".jarfis-project/project-profile.md",
                "injected": True,
                "missing_sections": ["Reusable Components"],
            },
            {
                "path": ".jarfis-project/project-rule.md",
                "injected": True,
            },
            {
                "path": ".wiki-cache.md",
                "injected": True,
                "missing_sections": ["Security", "Operations"],
            },
        ]
        _emit_missing_sections_warnings("backend-developer", meta)

        out = buf.getvalue().splitlines()
        assert len(out) == 2
        assert "agent=backend-developer" in out[0]
        assert "path=.jarfis-project/project-profile.md" in out[0]
        assert "Reusable Components" in out[0]
        assert "path=.wiki-cache.md" in out[1]
        assert "Security" in out[1]
        assert "Operations" in out[1]

    def test_silent_when_all_sections_found(self, monkeypatch):
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", buf)

        meta = [
            {"path": "a.md", "injected": True},
            {"path": "b.md", "injected": True, "missing_sections": []},
        ]
        _emit_missing_sections_warnings("qa-engineer", meta)

        assert buf.getvalue() == ""

    def test_silent_when_block_not_injected(self, monkeypatch):
        buf = io.StringIO()
        monkeypatch.setattr(sys, "stderr", buf)

        meta = [
            {"path": "a.md", "injected": False, "reason": "file_not_found"},
        ]
        _emit_missing_sections_warnings("qa-engineer", meta)

        assert buf.getvalue() == ""
