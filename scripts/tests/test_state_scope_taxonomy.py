"""M5.2 + M5.3 — scope.type / responsive taxonomy expansion.

ADR-0004 §2.1 + roadmap.md §4 trk(b) B5: v4.1 broadens the scope-shape
vocabulary to cover mobile/desktop/library/cli scopes and
``responsive=mobile-only`` (mobile-app workloads where desktop viewport
is N/A).

Two surfaces:

1. ``state.workspace.scope[i].type`` — must accept the new
   ``mobile | desktop | library | cli`` values in addition to the
   v4.0 ``frontend | backend`` set. ``cmd_validate`` rejects unknown
   values.

2. ``state.responsive`` — must accept ``mobile-only`` alongside the
   v4.0 ``pc-only | pc-mobile | pc-mobile-tablet`` set. ``cmd_validate``
   rejects unknown values.

The state.py module did not previously validate either field; M5
introduces explicit checks so misspellings or stale type names surface
at the validate gate (run before every Phase) instead of silently
dispatching the wrong domain.
"""

from __future__ import annotations

import json

import pytest

from jarfis.state import cmd_validate


SCOPE_TYPES_VALID = ("frontend", "backend", "mobile", "desktop", "library", "cli")
SCOPE_TYPES_INVALID = ("ml", "data", "FRONTEND", "frontend ", "")
RESPONSIVE_VALID = ("pc-only", "pc-mobile", "pc-mobile-tablet", "mobile-only")
RESPONSIVE_INVALID = ("mobile", "desktop-only", "mobile-tablet", "PC-ONLY", "")


def _base_state(scope_entries=None, responsive=None):
    state = {
        "work": {"name": "w", "docsDir": "/tmp"},
        "started_at": "2026-05-04",
        "current_phase": 0,
        "phases": {"0": {"status": "in_progress"}},
        "workspace": {"scope": scope_entries or []},
    }
    if responsive is not None:
        state["responsive"] = responsive
    return state


def _validate(tmp_path, capsys, state):
    sf = str(tmp_path / ".jarfis-state.json")
    with open(sf, "w") as f:
        json.dump(state, f)
    cmd_validate([sf])
    return json.loads(capsys.readouterr().out)


# ── M5.2 — scope.type expansion ─────────────────────────────────────


class TestScopeTypeExpansion:
    @pytest.mark.parametrize("scope_type", SCOPE_TYPES_VALID)
    def test_valid_scope_types_pass(self, tmp_path, capsys, scope_type):
        """All 6 valid types validate — frontend/backend (legacy) plus
        mobile/desktop/library/cli (M5.2)."""
        state = _base_state(scope_entries=[
            {"name": "s", "path": "/p", "type": scope_type},
        ])
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is True, (
            f"type={scope_type} should validate: {out}"
        )

    @pytest.mark.parametrize("bad_type", SCOPE_TYPES_INVALID)
    def test_invalid_scope_types_rejected(self, tmp_path, capsys, bad_type):
        """Unknown / malformed types fail validation."""
        state = _base_state(scope_entries=[
            {"name": "s", "path": "/p", "type": bad_type},
        ])
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is False, (
            f"type={bad_type!r} should fail validation: {out}"
        )
        # Error message must mention the offending value or the field
        # name so users can pinpoint the issue.
        assert any(
            "type" in e.lower() or "scope" in e.lower()
            for e in out["errors"]
        ), f"errors={out['errors']}"

    def test_missing_type_does_not_break(self, tmp_path, capsys):
        """type is optional — scope entries without type should still
        validate (e.g. when the loop hasn't asked the user yet)."""
        state = _base_state(scope_entries=[{"name": "s", "path": "/p"}])
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is True, f"missing type should be allowed: {out}"

    def test_mixed_types_in_monorepo(self, tmp_path, capsys):
        """Multi-scope state with mixed valid types — common case for
        monorepos (Tauri shell + RN app + shared library)."""
        state = _base_state(scope_entries=[
            {"name": "shell", "path": "/p/shell", "type": "desktop"},
            {"name": "app", "path": "/p/app", "type": "mobile"},
            {"name": "shared", "path": "/p/shared", "type": "library"},
            {"name": "tools", "path": "/p/tools", "type": "cli"},
        ])
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is True, f"mixed taxonomy: {out}"


# ── M5.3 — responsive expansion ─────────────────────────────────────


class TestResponsiveExpansion:
    @pytest.mark.parametrize("level", RESPONSIVE_VALID)
    def test_valid_responsive_levels_pass(self, tmp_path, capsys, level):
        state = _base_state(responsive=level)
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is True, (
            f"responsive={level} should validate: {out}"
        )

    @pytest.mark.parametrize("bad", RESPONSIVE_INVALID)
    def test_invalid_responsive_rejected(self, tmp_path, capsys, bad):
        state = _base_state(responsive=bad)
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is False, (
            f"responsive={bad!r} should fail: {out}"
        )
        assert any(
            "responsive" in e.lower() for e in out["errors"]
        ), f"errors={out['errors']}"

    def test_responsive_null_allowed(self, tmp_path, capsys):
        """state.responsive = null pre-Phase 1a should validate
        (cmd_init seeds it as None)."""
        state = _base_state(responsive=None)
        # _base_state skips responsive when None — confirm the absent
        # value is accepted.
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is True, f"null responsive: {out}"

    def test_mobile_only_unlocks_no_pc_designs(self, tmp_path, capsys):
        """``mobile-only`` is the new option — verify it persists
        through validate without requiring any PC viewport context."""
        state = _base_state(
            scope_entries=[{"name": "app", "path": "/p", "type": "mobile"}],
            responsive="mobile-only",
        )
        out = _validate(tmp_path, capsys, state)
        assert out["valid"] is True
