"""Resolver walk-up + monorepo SSOT dedupe tests (TDD-first).

Spec: /Users/sanhalee/repos/jarfis/.personal/sys-implements/monorepo-ssot-walkup-v1/step2-prompt.md

The `all-projects` branch of `resolve_path` must walk up parent
directories when a sub-package has no `.jarfis-project/` of its own,
falling back to a shared root profile. The walk-up is gated:
    * engages only for paths starting with ".jarfis-project/"
    * bounded by org.root, nearest .git ancestor, hard depth-3 limit
    * dedupes when 2+ scopes resolve to the same absolute file

Return shape:
    * non-prefix-gated path → list[str] (legacy shape)
    * .jarfis-project/ path → list[dict{path, from_scope_indices}]
"""

from __future__ import annotations

import json
import os

import pytest


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "jarfis", "tests", "fixtures",
)


def _fixture(name):
    return os.path.abspath(os.path.join(FIXTURES_DIR, name))


def _state_with_scope(scope_paths, *, names=None, org_root=None):
    """Build a minimal state with `workspace.scope` entries."""
    if names is None:
        names = [os.path.basename(p) or f"idx{i}" for i, p in enumerate(scope_paths)]
    state = {
        "workspace": {
            "scope": [
                {"path": p, "name": n}
                for p, n in zip(scope_paths, names)
            ],
        },
    }
    if org_root is not None:
        state["org"] = {"root": org_root}
    return state


# ── Fixture sanity ──────────────────────────────────────────────────


def test_fixture_tree_exists():
    """The monorepo-shared-ssot fixture must be on disk."""
    root = _fixture("monorepo-shared-ssot")
    assert os.path.isdir(os.path.join(root, ".git"))
    assert os.path.isfile(
        os.path.join(root, ".jarfis-project", "project-profile.md")
    )
    assert os.path.isdir(os.path.join(root, "packages", "daemon"))
    assert os.path.isdir(os.path.join(root, "packages", "pwa"))


# ── 9 required cases (per step2-prompt.md) ──────────────────────────


def test_walkup_finds_root_ssot():
    """Sub-package with no profile → resolves to root profile (walkup engages)."""
    from jarfis.compose.resolver import resolve_path

    root = _fixture("monorepo-shared-ssot")
    daemon = os.path.join(root, "packages", "daemon")
    state = _state_with_scope([daemon], names=["daemon"])

    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert isinstance(entry, dict)
    expected = os.path.join(root, ".jarfis-project", "project-profile.md")
    assert os.path.abspath(entry["path"]) == os.path.abspath(expected)
    assert entry["from_scope_indices"] == [0]


def test_per_package_profile_wins(tmp_path):
    """Both root + sub-package profile present → sub-package wins (no walkup)."""
    from jarfis.compose.resolver import resolve_path

    root = tmp_path / "monorepo"
    (root / ".git").mkdir(parents=True)
    (root / ".jarfis-project").mkdir(parents=True)
    (root / ".jarfis-project" / "project-profile.md").write_text(
        "# root profile\n"
    )
    pkg = root / "packages" / "daemon"
    (pkg / ".jarfis-project").mkdir(parents=True)
    (pkg / ".jarfis-project" / "project-profile.md").write_text(
        "# pkg profile\n"
    )

    state = _state_with_scope([str(pkg)], names=["daemon"])
    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert len(result) == 1
    entry = result[0]
    expected = pkg / ".jarfis-project" / "project-profile.md"
    assert os.path.abspath(entry["path"]) == os.path.abspath(str(expected))
    assert entry["from_scope_indices"] == [0]


def test_walkup_stops_at_org_root(tmp_path):
    """org.root above scope → walk-up does not cross it upward."""
    from jarfis.compose.resolver import resolve_path

    # layout: /tmp_path/super_root/org_root/sub/packages/daemon
    #   profile lives ABOVE org_root (in super_root) — walk-up must NOT find it.
    super_root = tmp_path / "super"
    org_root = super_root / "org"
    sub = org_root / "sub" / "packages" / "daemon"
    sub.mkdir(parents=True)
    (super_root / ".jarfis-project").mkdir()
    (super_root / ".jarfis-project" / "project-profile.md").write_text("x")

    state = _state_with_scope(
        [str(sub)], names=["daemon"], org_root=str(org_root)
    )
    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    # walk-up cannot find SSOT within bounds → returns probe path so reader
    # can mark file_not_found
    assert len(result) == 1
    entry = result[0]
    # The returned path should be the original probe (not the SSOT above org_root)
    forbidden = super_root / ".jarfis-project" / "project-profile.md"
    assert os.path.abspath(entry["path"]) != os.path.abspath(str(forbidden))


def test_walkup_stops_at_fs_root(tmp_path):
    """No org, no .git, no profile within depth-3 → returns original path."""
    from jarfis.compose.resolver import resolve_path

    deep = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    state = _state_with_scope([str(deep)], names=["deep"])

    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert len(result) == 1
    entry = result[0]
    # Returned path should be the original probe (will trigger file_not_found
    # downstream in reader)
    expected_probe = os.path.join(
        str(deep), ".jarfis-project", "project-profile.md"
    )
    assert os.path.abspath(entry["path"]) == os.path.abspath(expected_probe)
    assert entry["from_scope_indices"] == [0]


def test_dedupe_same_ssot_resolved_twice():
    """2 scope entries resolving to same SSOT → 1 dict with both indices."""
    from jarfis.compose.resolver import resolve_path

    root = _fixture("monorepo-shared-ssot")
    daemon = os.path.join(root, "packages", "daemon")
    pwa = os.path.join(root, "packages", "pwa")
    state = _state_with_scope([daemon, pwa], names=["daemon", "pwa"])

    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert len(result) == 1, f"expected dedupe to 1 entry, got {result!r}"
    entry = result[0]
    assert isinstance(entry, dict)
    expected = os.path.join(root, ".jarfis-project", "project-profile.md")
    assert os.path.abspath(entry["path"]) == os.path.abspath(expected)
    assert entry["from_scope_indices"] == [0, 1]


def test_walkup_only_for_jarfis_project_prefix(tmp_path):
    """path='package.json' (non-prefixed) → no walk-up, list[str] returned."""
    from jarfis.compose.resolver import resolve_path

    root = tmp_path / "mono"
    pkg = root / "packages" / "daemon"
    pkg.mkdir(parents=True)
    state = _state_with_scope([str(pkg)], names=["daemon"])

    result = resolve_path("all-projects", "package.json", state, None)
    assert isinstance(result, list)
    assert len(result) == 1
    # Legacy shape: list[str]
    assert isinstance(result[0], str), (
        f"non-prefixed paths must keep list[str] shape; got {type(result[0])}"
    )
    expected = os.path.join(str(pkg), "package.json")
    assert os.path.abspath(result[0]) == os.path.abspath(expected)


def test_walkup_bounded_by_git_ancestor(tmp_path):
    """org=null; .git 1 level above scope → walk-up stops at .git boundary."""
    from jarfis.compose.resolver import resolve_path

    # layout: outer/.jarfis-project/profile.md   <-- profile (SSOT) at outer
    #         outer/middle/.git                  <-- git boundary
    #         outer/middle/inner                 <-- scope (one level below .git)
    # Walk-up from `inner` must stop AT the .git directory (i.e. at middle),
    # so the SSOT at `outer` is NOT reachable.
    outer = tmp_path / "outer"
    middle = outer / "middle"
    inner = middle / "inner"
    inner.mkdir(parents=True)
    (middle / ".git").mkdir()
    (outer / ".jarfis-project").mkdir()
    (outer / ".jarfis-project" / "project-profile.md").write_text("x")

    state = _state_with_scope([str(inner)], names=["inner"])
    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert len(result) == 1
    entry = result[0]
    # Walk-up stopped at .git; the SSOT at `outer` must NOT be returned.
    forbidden = outer / ".jarfis-project" / "project-profile.md"
    assert os.path.abspath(entry["path"]) != os.path.abspath(str(forbidden))


def test_walkup_bounded_by_depth_3(tmp_path):
    """No org, no .git; profile at depth-4 → not found, original returned."""
    from jarfis.compose.resolver import resolve_path

    # layout: top/L1/L2/L3/L4/scope   — scope is 5 levels under top
    #         top/.jarfis-project/profile.md     — profile at top (5 walk-up steps)
    # Hard depth-3 cap means walk-up cannot reach top.
    top = tmp_path / "top"
    scope = top / "L1" / "L2" / "L3" / "L4" / "scope"
    scope.mkdir(parents=True)
    (top / ".jarfis-project").mkdir()
    (top / ".jarfis-project" / "project-profile.md").write_text("x")

    state = _state_with_scope([str(scope)], names=["scope"])
    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert len(result) == 1
    entry = result[0]
    forbidden = top / ".jarfis-project" / "project-profile.md"
    assert os.path.abspath(entry["path"]) != os.path.abspath(str(forbidden))
    # Returned path should be the original probe (file not found)
    expected_probe = os.path.join(
        str(scope), ".jarfis-project", "project-profile.md"
    )
    assert os.path.abspath(entry["path"]) == os.path.abspath(expected_probe)


def test_dedupe_uses_shared_ssot_label_in_main(tmp_path, capsys):
    """Integration: compose --dry-run emits shared-SSOT label for fixture."""
    from jarfis.compose.__main__ import main

    root = _fixture("monorepo-shared-ssot")
    # Build a minimal state file with two scope entries pointing at sub-packages.
    state = {
        "schema_version": "4.0",
        "workspace": {
            "scope": [
                {"path": os.path.join(root, "packages", "daemon"), "name": "daemon"},
                {"path": os.path.join(root, "packages", "pwa"), "name": "pwa"},
            ],
            "currentScopeIndex": 0,
        },
        "work": {"docsDir": str(tmp_path)},
    }
    state_path = tmp_path / "state.json"
    state_path.write_text(json.dumps(state))

    with pytest.raises(SystemExit) as excinfo:
        main([
            "--dry-run",
            "--agent", "technical-architect",
            "--state", str(state_path),
        ])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "monorepo SSOT shared by:" in out, (
        f"shared-SSOT label missing from compose dry-run output:\n{out[:600]}"
    )
    assert "daemon" in out and "pwa" in out
