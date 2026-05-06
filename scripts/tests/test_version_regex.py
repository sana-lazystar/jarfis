"""Tests for jarfis.version — Last updated/Version line regex (B2, v4.1.1).

Background (v4.1.1 backlog B2):
    The version-bump command rewrites the `Last updated: ... | Version: ...`
    line in `jarfis-index.md`. Its regex assumes a strict
        Last updated: YYYY-MM-DD | Version: X.Y.Z[<noise>]
    shape and fails to match when an annotation parenthetical sits between
    the date and the pipe (e.g. M7 release shipped with
        Last updated: 2026-05-06 (M7 release) | Version: 4.0.7
    forcing manual edit of the index after `jarfis version minor` ran).

These tests document the expected contract for v4.1.1:
  * Plain format: still rewritten cleanly (regression guard).
  * Parenthetical after date: matched, rewritten without the note.
  * Parenthetical after version: matched, rewritten without the note.
  * Both parentheticals: matched, rewritten without notes.
  * Trailing text on the same line is dropped (canonical, idempotent line).

Replacement target shape (canonical):
    > Last updated: <today-iso> | Version: <new-semver>
"""

import json
import os

from jarfis.version import main


INDEX_REL = ("commands", "jarfis", "jarfis-index.md")


def _write_index(claude_dir, content):
    """Overwrite the test fixture jarfis-index.md with a B2-shape line."""
    index_path = os.path.join(claude_dir, *INDEX_REL)
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w") as f:
        f.write(content)
    return index_path


def _read_index(claude_dir):
    index_path = os.path.join(claude_dir, *INDEX_REL)
    with open(index_path) as f:
        return f.read()


class TestVersionLineRegex:
    """B2 — `Last updated: ... | Version: ...` line must update across formats."""

    def test_plain_format_still_updated(self, jarfis_env, capsys):
        """Regression: plain `Last updated: <date> | Version: <semver>` keeps working."""
        claude = jarfis_env["claude_dir"]
        _write_index(claude, "> Last updated: 2026-03-24 | Version: 2.2.2\n")

        main(["patch", "plain regression"])
        capsys.readouterr()

        content = _read_index(claude)
        assert "Version: 2.2.3" in content
        assert "2.2.2" not in content

    def test_parenthetical_after_date(self, jarfis_env, capsys):
        """B2 primary case: `Last updated: <date> (note) | Version: <semver>`."""
        claude = jarfis_env["claude_dir"]
        _write_index(
            claude,
            "> Last updated: 2026-05-06 (M7 release) | Version: 2.2.2\n"
        )

        main(["patch", "B2 case A"])
        capsys.readouterr()

        content = _read_index(claude)
        assert "Version: 2.2.3" in content, (
            "version bump did not update the line containing parenthetical "
            "after date — B2 root cause"
        )
        # Old version must be gone — the line was actually rewritten, not just appended.
        assert "Version: 2.2.2" not in content

    def test_parenthetical_after_version(self, jarfis_env, capsys):
        """B2 secondary case: `Last updated: <date> | Version: <semver> (note)`."""
        claude = jarfis_env["claude_dir"]
        _write_index(
            claude,
            "> Last updated: 2026-05-06 | Version: 2.2.2 (M7 -> 2.2.3)\n"
        )

        main(["patch", "B2 case B"])
        capsys.readouterr()

        content = _read_index(claude)
        assert "Version: 2.2.3" in content
        assert "Version: 2.2.2" not in content

    def test_both_parentheticals(self, jarfis_env, capsys):
        """B2 combined: parentheticals on both date and version."""
        claude = jarfis_env["claude_dir"]
        _write_index(
            claude,
            "> Last updated: 2026-05-06 (M7) | Version: 2.2.2 (M7 -> 2.2.3)\n"
        )

        main(["patch", "B2 case C"])
        capsys.readouterr()

        content = _read_index(claude)
        assert "Version: 2.2.3" in content
        assert "Version: 2.2.2" not in content

    def test_extra_whitespace_tolerated(self, jarfis_env, capsys):
        """Tolerance: extra spaces around `|` should still match."""
        claude = jarfis_env["claude_dir"]
        _write_index(
            claude,
            "> Last updated: 2026-05-06   |   Version: 2.2.2\n"
        )

        main(["patch", "whitespace case"])
        capsys.readouterr()

        content = _read_index(claude)
        assert "Version: 2.2.3" in content

    def test_canonical_output_drops_notes(self, jarfis_env, capsys):
        """Canonicalization: result line should have no parenthetical notes.

        Decision (D2-derived): version bump produces a clean, idempotent line.
        Annotations are release-time noise; they get dropped on canonical
        rewrite. Users wanting notes can re-add post-bump.
        """
        claude = jarfis_env["claude_dir"]
        _write_index(
            claude,
            "> Last updated: 2026-05-06 (M7 release) | Version: 2.2.2 (note)\n"
        )

        main(["patch", "canonical drop"])
        capsys.readouterr()

        content = _read_index(claude)
        # Find the rewritten line.
        line = next(
            ln for ln in content.splitlines() if "Version:" in ln and "Last updated" in ln
        )
        assert "(M7 release)" not in line
        assert "(note)" not in line
        # Canonical shape: exactly one `|` and the new semver.
        assert line.count("|") == 1
        assert "Version: 2.2.3" in line


class TestVersionLineRegexRegression:
    """Guard rails: B2 fix must not break unrelated lines."""

    def test_does_not_match_unrelated_lines(self, jarfis_env, capsys):
        """A bullet mentioning Version somewhere else must NOT be rewritten."""
        claude = jarfis_env["claude_dir"]
        index = _write_index(
            claude,
            (
                "> Last updated: 2026-05-06 (M7) | Version: 2.2.2\n"
                "\n"
                "Some prose mentioning Version: 1.0.0 of an unrelated tool.\n"
                "- Version management: bump via jarfis version <patch|minor|major>.\n"
            ),
        )

        main(["patch", "regression guard"])
        capsys.readouterr()

        with open(index) as f:
            content = f.read()
        # Header rewritten:
        assert "Last updated:" in content
        assert "Version: 2.2.3" in content
        # Unrelated mentions preserved verbatim:
        assert "Version: 1.0.0 of an unrelated tool" in content
        assert "bump via jarfis version <patch|minor|major>" in content

    def test_files_updated_payload_intact(self, jarfis_env, capsys):
        """JSON payload's files_updated list shape must stay stable."""
        claude = jarfis_env["claude_dir"]
        _write_index(
            claude,
            "> Last updated: 2026-05-06 (M7) | Version: 2.2.2\n"
        )

        main(["patch", "payload stable"])
        out = json.loads(capsys.readouterr().out)
        assert out["previous"] == "2.2.2"
        assert out["new"] == "2.2.3"
        assert "files_updated" in out
        assert any("jarfis-index.md" in p for p in out["files_updated"])
