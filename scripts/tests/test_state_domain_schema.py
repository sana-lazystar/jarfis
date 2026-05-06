"""M4.2 + M4.5 — ``state.workspace.scope[i].domain`` schema + v4.0.x
forward-compat migration (ADR-0003 §2.1).

These tests cover the schema-side guarantees:

1. **cmd_init** must initialize ``state.workspace`` with an empty
   ``scope: []`` array (so set-nested at ``workspace.scope.0.domain``
   has somewhere to land), AND include ``state.domain = None`` for
   legacy compat readers.
2. **migrate_v40_to_v41(state)** is the public migration helper used
   by readers (validate, list-workflows, compose) when they encounter
   a v4.0.x state file. It populates ``scope[i].domain`` from the
   single ``state.domain`` field whenever the per-scope field is
   absent. v4.1 state files (where ``scope[i].domain`` is already
   set) are left untouched.
3. **cmd_validate** accepts both shapes: legacy (``state.domain`` only)
   AND v4.1 (``scope[i].domain`` set). It must NOT reject either.

The migration MUST be idempotent — applying it twice is a no-op.
"""

import json
import os

import pytest

from jarfis.state import (
    cmd_init,
    cmd_validate,
    migrate_v40_to_v41,
)


# ── M4.2 — cmd_init scope schema ────────────────────────────────────


class TestCmdInitScopeSchema:
    def test_workspace_has_scope_array(self, tmp_path):
        sf = str(tmp_path / "work" / ".jarfis-state.json")
        cmd_init([sf, "proj", "20260504-feat", str(tmp_path / "docs")])
        with open(sf) as f:
            data = json.load(f)
        assert "workspace" in data
        # M4.2: scope[] is the per-project array; v4.0 left workspace={}.
        # Must be a list (possibly empty after init — populated in step 5).
        assert "scope" in data["workspace"], (
            "cmd_init must seed workspace.scope = [] for v4.1 schema"
        )
        assert isinstance(data["workspace"]["scope"], list)

    def test_legacy_state_domain_remains(self, tmp_path):
        """state.domain (legacy) is still emitted as None so readers
        can still fall back when scope[i].domain is missing."""
        sf = str(tmp_path / "work" / ".jarfis-state.json")
        cmd_init([sf, "proj", "20260504-feat", str(tmp_path / "docs")])
        with open(sf) as f:
            data = json.load(f)
        assert "domain" in data
        assert data["domain"] is None


# ── M4.5 — migrate_v40_to_v41 ────────────────────────────────────────


class TestMigrateV40ToV41:
    def test_legacy_state_domain_populates_scopes(self):
        """v4.0.x: state.domain="web" + 3 scopes without domain →
        all scopes get domain="web" after migration."""
        state = {
            "domain": "web",
            "workspace": {
                "scope": [
                    {"name": "shell", "path": "/p/shell", "type": "frontend"},
                    {"name": "api", "path": "/p/api", "type": "backend"},
                    {"name": "admin", "path": "/p/admin", "type": "frontend"},
                ]
            },
        }
        migrated = migrate_v40_to_v41(state)
        for s in migrated["workspace"]["scope"]:
            assert s["domain"] == "web", (
                f"scope[{s['name']}] should inherit state.domain='web'"
            )

    def test_v41_state_unchanged(self):
        """When scope[i].domain is already set, migration must NOT
        overwrite — the v4.1 schema is the source of truth."""
        state = {
            "domain": "web",
            "workspace": {
                "scope": [
                    {"name": "shell", "domain": "desktop"},
                    {"name": "app", "domain": "mobile"},
                ]
            },
        }
        migrated = migrate_v40_to_v41(state)
        assert migrated["workspace"]["scope"][0]["domain"] == "desktop"
        assert migrated["workspace"]["scope"][1]["domain"] == "mobile"

    def test_partial_migration(self):
        """Some scopes have domain, some don't. Only fill in the gaps
        without touching the explicit ones."""
        state = {
            "domain": "web",
            "workspace": {
                "scope": [
                    {"name": "shell", "domain": "desktop"},  # explicit
                    {"name": "api"},                          # gets web
                    {"name": "app", "domain": "mobile"},     # explicit
                ]
            },
        }
        migrated = migrate_v40_to_v41(state)
        assert migrated["workspace"]["scope"][0]["domain"] == "desktop"
        assert migrated["workspace"]["scope"][1]["domain"] == "web"
        assert migrated["workspace"]["scope"][2]["domain"] == "mobile"

    def test_no_state_domain_no_migration(self):
        """Without state.domain we cannot infer; leave scopes untouched."""
        state = {
            "workspace": {
                "scope": [
                    {"name": "shell"},
                    {"name": "api"},
                ]
            },
        }
        migrated = migrate_v40_to_v41(state)
        for s in migrated["workspace"]["scope"]:
            assert "domain" not in s

    def test_state_domain_preserved_after_migration(self):
        """ADR-0003 §2.1 last paragraph: state.domain stays for legacy
        compat after migration; only the per-scope field is added."""
        state = {
            "domain": "desktop",
            "workspace": {"scope": [{"name": "shell"}]},
        }
        migrated = migrate_v40_to_v41(state)
        assert migrated["domain"] == "desktop"

    def test_idempotent(self):
        """Applying twice = same as once."""
        state = {
            "domain": "web",
            "workspace": {"scope": [{"name": "x"}]},
        }
        once = migrate_v40_to_v41(state)
        twice = migrate_v40_to_v41(once)
        assert once == twice

    def test_empty_scope_array(self):
        """Empty scope array is valid (Phase 0 step 5 may not have run yet)."""
        state = {"domain": "web", "workspace": {"scope": []}}
        migrated = migrate_v40_to_v41(state)
        assert migrated["workspace"]["scope"] == []

    def test_missing_workspace(self):
        """No workspace key → migration is a no-op."""
        state = {"domain": "web"}
        migrated = migrate_v40_to_v41(state)
        # Should not raise; state returned unchanged or with workspace
        # left absent.
        assert migrated.get("domain") == "web"


# ── M4.2 — cmd_validate accepts both shapes ─────────────────────────


class TestCmdValidateAcceptsBothShapes:
    def test_validates_v41_with_per_scope_domain(self, tmp_path, capsys):
        sf = str(tmp_path / ".jarfis-state.json")
        state = {
            "work": {"name": "w", "docsDir": "/tmp"},
            "started_at": "2026-05-04",
            "current_phase": 0,
            "phases": {"0": {"status": "in_progress"}},
            "workspace": {
                "scope": [
                    {"name": "s", "path": "/p", "type": "frontend",
                     "domain": "mobile"},
                ]
            },
        }
        with open(sf, "w") as f:
            json.dump(state, f)
        cmd_validate([sf])
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True, f"v4.1 state failed validate: {out}"

    def test_validates_v40_legacy_state_domain(self, tmp_path, capsys):
        sf = str(tmp_path / ".jarfis-state.json")
        state = {
            "work": {"name": "w", "docsDir": "/tmp"},
            "started_at": "2026-05-04",
            "domain": "web",  # legacy single domain
            "current_phase": 0,
            "phases": {"0": {"status": "in_progress"}},
            "workspace": {"scope": [{"name": "s"}]},
        }
        with open(sf, "w") as f:
            json.dump(state, f)
        cmd_validate([sf])
        out = json.loads(capsys.readouterr().out)
        assert out["valid"] is True, f"v4.0.x legacy state failed: {out}"
