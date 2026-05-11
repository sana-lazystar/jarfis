"""Resolver walk-up + monorepo SSOT dedupe tests (TDD-first).

Spec: /Users/sanhalee/repos/jarfis/.personal/sys-implements/monorepo-ssot-walkup-v1/step2-prompt.md
Extended (v4.2.x): /Users/sanhalee/repos/jarfis/.personal/sys-implements/monorepo-ssot-walkup-fix-v1/step2-prompt.md

The `all-projects` branch of `resolve_path` must walk up parent
directories when a sub-package has no `.jarfis-project/` of its own,
falling back to a shared root profile. The walk-up is gated:
    * engages for paths starting with ".jarfis-project/" OR ".jarfis-org/"
    * bounded by org.root, nearest .git ancestor, hard depth-5 limit
    * dedupes when 2+ scopes resolve to the same absolute file

Return shape:
    * non-prefix-gated path → list[str] (legacy shape)
    * .jarfis-project/ or .jarfis-org/ path → list[dict{path, from_scope_indices}]
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


def test_walkup_bounded_by_depth_5(tmp_path):
    """No org, no .git; profile beyond depth-5 → not found, original returned.

    Layout: top/L1/L2/L3/L4/L5/L6/scope (7 levels under top).
    Profile at top requires 7 walk-up steps; new hard cap is 5 — so the
    walk-up still cannot reach top, the original probe is returned. This
    asserts the boundary still functions at the new depth=5 ceiling.
    """
    from jarfis.compose.resolver import resolve_path

    top = tmp_path / "top"
    scope = top / "L1" / "L2" / "L3" / "L4" / "L5" / "L6" / "scope"
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


# ── New tests for monorepo-ssot-walkup-fix-v1 ────────────────────────


def test_walkup_engages_for_jarfis_org_prefix(tmp_path):
    """`.jarfis-org/learnings.md` from sub-package → walk-up engages, finds ancestor."""
    from jarfis.compose.resolver import resolve_path

    # Layout: root/.git, root/.jarfis-org/learnings.md, root/packages/daemon
    root = tmp_path / "monorepo"
    (root / ".git").mkdir(parents=True)
    (root / ".jarfis-org").mkdir(parents=True)
    (root / ".jarfis-org" / "learnings.md").write_text("# org learnings\n")
    pkg = root / "packages" / "daemon"
    pkg.mkdir(parents=True)

    state = _state_with_scope([str(pkg)], names=["daemon"])
    result = resolve_path(
        "all-projects", ".jarfis-org/learnings.md", state, None
    )
    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert isinstance(entry, dict), (
        f".jarfis-org/ paths must return list[dict]; got {type(entry)}"
    )
    expected = root / ".jarfis-org" / "learnings.md"
    assert os.path.abspath(entry["path"]) == os.path.abspath(str(expected))
    assert entry["from_scope_indices"] == [0]


def test_jarfis_org_prefix_returns_dict_shape(tmp_path):
    """`.jarfis-org/` resolution shape contract: list[dict{path, from_scope_indices}]."""
    from jarfis.compose.resolver import resolve_path

    root = tmp_path / "monorepo"
    (root / ".git").mkdir(parents=True)
    (root / ".jarfis-org").mkdir(parents=True)
    (root / ".jarfis-org" / "learnings.md").write_text("x")
    pkg = root / "packages" / "daemon"
    pkg.mkdir(parents=True)

    state = _state_with_scope([str(pkg)], names=["daemon"])
    result = resolve_path(
        "all-projects", ".jarfis-org/learnings.md", state, None
    )
    assert isinstance(result, list)
    assert len(result) == 1
    entry = result[0]
    assert isinstance(entry, dict)
    # Required keys per the .jarfis-project/ shape contract
    assert set(entry.keys()) >= {"path", "from_scope_indices"}
    assert isinstance(entry["path"], str)
    assert isinstance(entry["from_scope_indices"], list)
    assert all(isinstance(i, int) for i in entry["from_scope_indices"])


def test_jarfis_org_per_package_wins(tmp_path):
    """Both root + sub-package `.jarfis-org/` exist → sub-package wins, no walk-up."""
    from jarfis.compose.resolver import resolve_path

    root = tmp_path / "monorepo"
    (root / ".git").mkdir(parents=True)
    (root / ".jarfis-org").mkdir(parents=True)
    (root / ".jarfis-org" / "learnings.md").write_text("# root org\n")
    pkg = root / "packages" / "daemon"
    (pkg / ".jarfis-org").mkdir(parents=True)
    (pkg / ".jarfis-org" / "learnings.md").write_text("# pkg org\n")

    state = _state_with_scope([str(pkg)], names=["daemon"])
    result = resolve_path(
        "all-projects", ".jarfis-org/learnings.md", state, None
    )
    assert len(result) == 1
    entry = result[0]
    expected = pkg / ".jarfis-org" / "learnings.md"
    assert os.path.abspath(entry["path"]) == os.path.abspath(str(expected))
    assert entry["from_scope_indices"] == [0]


def test_walkup_depth_5_finds_at_depth_5(tmp_path):
    """Profile reachable at exactly 5 walk-up steps → new depth-5 cap finds it.

    Layout: top/L1/L2/L3/L4/scope (scope is 5 dirs under top).
    Profile at top/.jarfis-project/project-profile.md requires exactly 5
    parent moves. Under the previous depth-3 cap this would NOT be found;
    under the new depth-5 cap it MUST be found.
    """
    from jarfis.compose.resolver import resolve_path

    top = tmp_path / "top"
    scope = top / "L1" / "L2" / "L3" / "L4" / "scope"
    scope.mkdir(parents=True)
    (top / ".jarfis-project").mkdir()
    profile = top / ".jarfis-project" / "project-profile.md"
    profile.write_text("# top profile\n")

    state = _state_with_scope([str(scope)], names=["scope"])
    result = resolve_path(
        "all-projects", ".jarfis-project/project-profile.md", state, None
    )
    assert len(result) == 1
    entry = result[0]
    assert os.path.abspath(entry["path"]) == os.path.abspath(str(profile)), (
        f"depth-5 walk-up failed to find profile at {profile}; got {entry['path']}"
    )
    assert entry["from_scope_indices"] == [0]


# ── Stage 6a — `{project_slug}` substitution in resolver ─────────────


def test_substitutes_project_slug_in_path(tmp_path):
    """`{project_slug}` in path is substituted before os.path.join (Stage 6a)."""
    from jarfis.compose.resolver import resolve_path

    org_root = tmp_path / "org"
    (org_root / ".jarfis-org" / "wiki" / "PO" / "projects" / "myproj" / "ia").mkdir(
        parents=True
    )
    state = {"org": {"root": str(org_root)}}

    resolved = resolve_path(
        "org_wiki",
        "PO/projects/{project_slug}/ia/manifest.json",
        state,
        None,
        slug_context={"project_slug": "myproj"},
    )
    expected = os.path.join(
        str(org_root), ".jarfis-org", "wiki", "PO", "projects",
        "myproj", "ia", "manifest.json",
    )
    assert resolved == expected, (
        f"`{{project_slug}}` substitution failed: got {resolved!r}, want {expected!r}"
    )


def test_leaves_unknown_placeholder_literal(tmp_path):
    """Unknown placeholder key → leave literal (caller's choice, no exception)."""
    from jarfis.compose.resolver import resolve_path

    org_root = tmp_path / "org"
    (org_root / ".jarfis-org" / "wiki").mkdir(parents=True)
    state = {"org": {"root": str(org_root)}}

    # `{unknown_key}` is not in ctx → leave literal so reader marks file_not_found
    resolved = resolve_path(
        "org_wiki",
        "PO/projects/{unknown_key}/ia/manifest.json",
        state,
        None,
        slug_context={"project_slug": "myproj"},
    )
    assert "{unknown_key}" in resolved, (
        f"unknown placeholder should remain literal; got {resolved!r}"
    )


def test_no_substitution_when_ctx_none(tmp_path):
    """slug_context=None → path passes through untouched (back-compat)."""
    from jarfis.compose.resolver import resolve_path

    org_root = tmp_path / "org"
    (org_root / ".jarfis-org" / "wiki").mkdir(parents=True)
    state = {"org": {"root": str(org_root)}}

    resolved = resolve_path(
        "org_wiki",
        "PO/projects/{project_slug}/ia/manifest.json",
        state,
        None,
        slug_context=None,
    )
    # Literal `{project_slug}` survives — no substitution attempted.
    assert "{project_slug}" in resolved


def test_substitution_works_with_org_wiki_base(tmp_path):
    """Stage 6a end-to-end: org_wiki + {project_slug} + slug_context."""
    from jarfis.compose.resolver import resolve_path

    org_root = tmp_path / "org"
    target_dir = org_root / ".jarfis-org" / "wiki" / "PO" / "projects" / "acme" / "ia"
    target_dir.mkdir(parents=True)
    (target_dir / "manifest.json").write_text('{"slug": "acme"}')
    state = {"org": {"root": str(org_root)}}

    resolved = resolve_path(
        "org_wiki",
        "PO/projects/{project_slug}/ia/manifest.json",
        state,
        None,
        slug_context={"project_slug": "acme"},
    )
    assert os.path.isfile(resolved), (
        f"resolved Org IA manifest path should exist on disk: {resolved}"
    )


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
