"""Tests for jarfis.state — .jarfis-state.json CRUD operations."""

import json
import os

import pytest

from jarfis.state import (
    cmd_init,
    cmd_read,
    cmd_set,
    cmd_set_nested,
    cmd_validate,
    cmd_write,
    cmd_list_workflows,
    main,
    set_design_mode,
)


class TestCmdInit:
    def test_creates_state_file(self, tmp_path):
        """v4.1 (M2.11, ADR-0002): cmd_init emits the v4 nested shape.

        v3 flat keys (project_name, work_name, work_input, docs_dir,
        branch, branches, source_meeting) are no longer emitted — work-legacy
        is gone, so the dual-emit rationale evaporates. Surviving top-level
        keys (status, started_at, current_phase, phases, etc.) belong to
        the v4 schema and stay.
        """
        sf = str(tmp_path / "work" / ".jarfis-state.json")
        cmd_init([sf, "my-project", "20260324-feature", str(tmp_path / "docs")])
        assert os.path.isfile(sf)
        with open(sf) as f:
            data = json.load(f)

        # v4 nested shape is the SSOT for project/work identity.
        assert data["work"]["name"] == "20260324-feature"
        assert data["work"]["docsDir"].endswith("docs")
        assert "sessionKey" in data and data["sessionKey"].startswith("jf-")
        assert "domain" in data
        assert "locale" in data

        # v4 lifecycle keys remain at top level (consumed by phase prompts).
        assert data["status"] == "in-progress"
        assert data["current_phase"] == 0
        assert "0" in data["phases"]
        assert data["phases"]["0"]["status"] == "in_progress"

    def test_no_v3_flat_keys_emitted(self, tmp_path):
        """ADR-0002 §3.2: v3 flat keys must no longer appear in fresh state."""
        sf = str(tmp_path / "work" / ".jarfis-state.json")
        cmd_init([sf, "my-project", "20260324-feature", str(tmp_path / "docs")])
        with open(sf) as f:
            data = json.load(f)
        for forbidden in (
            "project_name", "work_name", "work_input",
            "docs_dir", "branch", "branches", "source_meeting",
        ):
            assert forbidden not in data, \
                f"v3 flat key '{forbidden}' should not be emitted by cmd_init"

    def test_creates_parent_directories(self, tmp_path):
        sf = str(tmp_path / "deep" / "nested" / ".jarfis-state.json")
        cmd_init([sf, "proj", "work", str(tmp_path)])
        assert os.path.isfile(sf)

    def test_errors_on_missing_args(self):
        with pytest.raises(SystemExit):
            cmd_init(["state.json", "proj", ""])


class TestCmdRead:
    def test_reads_entire_state(self, state_file, capsys):
        cmd_read([state_file])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["project_name"] == "test-project"

    def test_reads_nested_key(self, state_file, capsys):
        cmd_read([state_file, "phases.0.status"])
        output = capsys.readouterr().out
        assert json.loads(output) == "in_progress"

    def test_returns_null_for_missing_key(self, state_file, capsys):
        cmd_read([state_file, "nonexistent.key"])
        output = capsys.readouterr().out
        assert json.loads(output) is None

    def test_errors_on_missing_file(self):
        with pytest.raises(SystemExit):
            cmd_read(["/nonexistent/path.json"])


class TestCmdWrite:
    def test_writes_entire_state(self, tmp_path, capsys):
        sf = str(tmp_path / "state.json")
        # Create initial file
        with open(sf, "w") as f:
            json.dump({"old": True}, f)
        new_data = {"project_name": "new", "status": "completed"}
        cmd_write([sf, json.dumps(new_data)])
        with open(sf) as f:
            result = json.load(f)
        assert result == new_data

    def test_outputs_success(self, tmp_path, capsys):
        sf = str(tmp_path / "state.json")
        cmd_write([sf, '{"a": 1}'])
        output = json.loads(capsys.readouterr().out)
        assert output["success"] is True


class TestCmdSet:
    def test_sets_top_level_key(self, state_file, capsys):
        cmd_set([state_file, "status", "completed"])
        with open(state_file) as f:
            data = json.load(f)
        assert data["status"] == "completed"

    def test_sets_json_value(self, state_file, capsys):
        cmd_set([state_file, "current_phase", "2"])
        with open(state_file) as f:
            data = json.load(f)
        assert data["current_phase"] == 2  # parsed as int

    def test_set_with_audit_path(self, state_file, tmp_path, capsys):
        audit = str(tmp_path / "audit.jsonl")
        cmd_set([state_file, "status", "completed"], audit_path=audit)
        # State changed
        with open(state_file) as f:
            data = json.load(f)
        assert data["status"] == "completed"
        # Audit event recorded
        with open(audit) as f:
            lines = f.readlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["type"] == "PhaseCompleted"
        assert event["key"] == "status"

    def test_set_without_audit_path(self, state_file, tmp_path, capsys):
        """audit_path=None (default) should not create any audit file."""
        audit = str(tmp_path / "audit.jsonl")
        cmd_set([state_file, "status", "completed"])
        assert not os.path.exists(audit)

    def test_set_audit_failure_does_not_block(self, state_file, tmp_path, capsys):
        """Audit write failure should not prevent state change."""
        # Use a directory path as audit_path to force write failure
        bad_audit = str(tmp_path / "nonexistent_dir" / "deep" / "audit.jsonl")
        cmd_set([state_file, "status", "completed"], audit_path=bad_audit)
        with open(state_file) as f:
            data = json.load(f)
        assert data["status"] == "completed"


class TestCmdSetNested:
    def test_sets_nested_key(self, state_file, capsys):
        cmd_set_nested([state_file, "phases.1.status", "in_progress"])
        with open(state_file) as f:
            data = json.load(f)
        assert data["phases"]["1"]["status"] == "in_progress"

    def test_creates_intermediate_dicts(self, state_file, capsys):
        cmd_set_nested([state_file, "new.nested.key", '"value"'])
        with open(state_file) as f:
            data = json.load(f)
        assert data["new"]["nested"]["key"] == "value"

    def test_set_nested_with_audit_path(self, state_file, tmp_path, capsys):
        audit = str(tmp_path / "audit.jsonl")
        cmd_set_nested([state_file, "phases.1.status", "in_progress"], audit_path=audit)
        with open(state_file) as f:
            data = json.load(f)
        assert data["phases"]["1"]["status"] == "in_progress"
        with open(audit) as f:
            lines = f.readlines()
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["type"] == "PhaseCompleted"
        assert event["key_path"] == "phases.1.status"


class TestCmdValidate:
    def test_valid_state(self, state_file, capsys):
        cmd_validate([state_file])
        output = json.loads(capsys.readouterr().out)
        assert output["valid"] is True
        assert output["error_count"] == 0

    def test_invalid_missing_fields(self, tmp_path, capsys):
        sf = str(tmp_path / "bad.json")
        with open(sf, "w") as f:
            json.dump({"some": "data"}, f)
        cmd_validate([sf])
        output = json.loads(capsys.readouterr().out)
        assert output["valid"] is False
        assert output["error_count"] > 0

    def test_invalid_phase_status(self, tmp_path, capsys):
        sf = str(tmp_path / "bad.json")
        state = {
            "project_name": "p",
            "work_name": "w",
            "docs_dir": "/tmp",
            "started_at": "2026-01-01",
            "current_phase": 0,
            "phases": {"0": {"status": "INVALID_STATUS"}},
        }
        with open(sf, "w") as f:
            json.dump(state, f)
        cmd_validate([sf])
        output = json.loads(capsys.readouterr().out)
        assert output["valid"] is False
        assert any("INVALID_STATUS" in e for e in output["errors"])

    def test_valid_top_level_status(self, state_file, capsys):
        # Modify to completed
        with open(state_file) as f:
            data = json.load(f)
        data["status"] = "completed"
        with open(state_file, "w") as f:
            json.dump(data, f)
        cmd_validate([state_file])
        output = json.loads(capsys.readouterr().out)
        assert output["valid"] is True


class TestCmdListWorkflows:
    def test_empty_workspace(self, tmp_path, capsys):
        ws = str(tmp_path / "workspace")
        os.makedirs(os.path.join(ws, "works"))
        cmd_list_workflows([ws])
        output = json.loads(capsys.readouterr().out)
        assert output["count"] == 0
        assert output["workflows"] == []

    def test_lists_workflows(self, tmp_path, capsys):
        ws = str(tmp_path / "workspace")
        work = os.path.join(ws, "works", "20260324-test")
        os.makedirs(work)
        state = {
            "project_name": "proj",
            "work_name": "20260324-test",
            "current_phase": 1,
            "status": "in-progress",
            "key_decisions": ["decision1"],
            "started_at": "2026-03-24T00:00:00Z",
            "docs_dir": work,
            "phases": {"6": {"status": "pending"}},
        }
        with open(os.path.join(work, ".jarfis-state.json"), "w") as f:
            json.dump(state, f)
        cmd_list_workflows([ws])
        output = json.loads(capsys.readouterr().out)
        assert output["count"] == 1
        assert output["workflows"][0]["project_name"] == "proj"

    def test_completed_only_filter(self, tmp_path, capsys):
        ws = str(tmp_path / "workspace")
        for name, status in [("work1", "in-progress"), ("work2", "completed")]:
            work = os.path.join(ws, "works", name)
            os.makedirs(work)
            with open(os.path.join(work, ".jarfis-state.json"), "w") as f:
                json.dump({
                    "project_name": "p", "work_name": name,
                    "current_phase": 6, "status": status,
                    "key_decisions": [], "started_at": "2026-01-01",
                    "docs_dir": work, "phases": {},
                }, f)
        cmd_list_workflows([ws, "--completed-only"])
        output = json.loads(capsys.readouterr().out)
        assert output["count"] == 1
        assert output["workflows"][0]["status"] == "completed"

    def test_scans_all_orgs_without_args(self, jarfis_env, capsys):
        """When no org_dir arg, scan all org workspaces."""
        # Create a workflow in standalone
        work = os.path.join(jarfis_env["standalone_works"], "20260324-test")
        os.makedirs(work)
        with open(os.path.join(work, ".jarfis-state.json"), "w") as f:
            json.dump({
                "project_name": "p", "work_name": "20260324-test",
                "current_phase": 1, "status": "in-progress",
                "key_decisions": [], "started_at": "2026-03-24",
                "docs_dir": work, "phases": {},
            }, f)
        cmd_list_workflows([])
        output = json.loads(capsys.readouterr().out)
        assert output["count"] >= 1


class TestMain:
    def test_unknown_action_exits(self):
        with pytest.raises(SystemExit):
            main(["unknown-action"])

    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            main([])


# ---------------------------------------------------------------------------
# design-supplied-mode-v1 — Step 2 additions
#
# These tests pin the SSOT-preserving invariants required by Critic blocker
# #4 (mutual exclusion) plus the new ``state.design.suppliedPath`` /
# ``state.design.brandAssetsDir`` schema fields. The invariants are enforced
# by ``state.set_design_mode`` and (separately) by ``verify._gate2_checks``
# / ``verify._phase_3_verify``.
# ---------------------------------------------------------------------------
class TestDesignSuppliedSchema:
    def test_default_design_supplied_path_null(self, tmp_path):
        """cmd_init seeds suppliedPath / brandAssetsDir = None alongside
        the existing mode/figmaPages defaults."""
        sf = str(tmp_path / "work" / ".jarfis-state.json")
        cmd_init([sf, "p", "20260507-feature", str(tmp_path / "docs")])
        with open(sf) as f:
            data = json.load(f)
        design = data["design"]
        assert design["mode"] is None
        assert design["figmaPages"] == []
        # New keys (Step 2 schema extension)
        assert "suppliedPath" in design
        assert design["suppliedPath"] is None
        assert "brandAssetsDir" in design
        assert design["brandAssetsDir"] is None


class TestSetDesignMode:
    def test_supplied_resets_figma_pages(self):
        state = {
            "design": {
                "mode": "figma",
                "figmaPages": [{"title": "Home", "url": "https://figma.com/x"}],
                "suppliedPath": None,
                "brandAssetsDir": None,
            }
        }
        out = set_design_mode(state, "supplied")
        assert out["design"]["mode"] == "supplied"
        assert out["design"]["figmaPages"] == []
        # suppliedPath is left for the caller to fill in (Phase 1a)
        assert out is state  # in-place mutation

    def test_figma_resets_supplied_path(self):
        state = {
            "design": {
                "mode": "supplied",
                "figmaPages": [],
                "suppliedPath": "/abs/path/mockup",
                "brandAssetsDir": None,
            }
        }
        set_design_mode(state, "figma")
        assert state["design"]["mode"] == "figma"
        assert state["design"]["suppliedPath"] is None

    def test_text_resets_both(self):
        state = {
            "design": {
                "mode": "supplied",
                "figmaPages": [{"title": "X", "url": "u"}],
                "suppliedPath": "/abs/m",
                "brandAssetsDir": None,
            }
        }
        set_design_mode(state, "text")
        assert state["design"]["mode"] == "text"
        assert state["design"]["figmaPages"] == []
        assert state["design"]["suppliedPath"] is None

    def test_null_resets_both(self):
        state = {
            "design": {
                "mode": "supplied",
                "figmaPages": [{"title": "X", "url": "u"}],
                "suppliedPath": "/abs/m",
                "brandAssetsDir": None,
            }
        }
        set_design_mode(state, None)
        assert state["design"]["mode"] is None
        assert state["design"]["figmaPages"] == []
        assert state["design"]["suppliedPath"] is None

    def test_seeds_design_block_when_missing(self):
        """Defensive: state without a ``design`` key still gets a
        normalized block."""
        state = {}
        set_design_mode(state, "supplied")
        assert "design" in state
        assert state["design"]["mode"] == "supplied"
        assert state["design"]["figmaPages"] == []


class TestSetNestedDesignModeIntegration:
    """``cmd_set_nested`` must trigger the same mutual-exclusion enforcement
    when the caller writes ``design.mode`` directly. This is the integration
    point used by work.md / phase3.md when persisting Phase 1a answers.
    """

    def _seed(self, tmp_path, **design):
        sf = tmp_path / ".jarfis-state.json"
        state = {
            "work": {"name": "w", "docsDir": str(tmp_path / "docs")},
            "started_at": "2026-05-07T00:00:00Z",
            "current_phase": 0,
            "phases": {},
            "design": {
                "mode": None,
                "figmaPages": [],
                "suppliedPath": None,
                "brandAssetsDir": None,
            },
        }
        state["design"].update(design)
        sf.write_text(json.dumps(state))
        return str(sf)

    def test_set_nested_design_mode_supplied_clears_figma_pages(self, tmp_path, capsys):
        sf = self._seed(
            tmp_path,
            mode="figma",
            figmaPages=[{"title": "Home", "url": "https://figma.com/x"}],
        )
        cmd_set_nested([sf, "design.mode", '"supplied"'])
        with open(sf) as f:
            data = json.load(f)
        assert data["design"]["mode"] == "supplied"
        # Mutual exclusion must be enforced even via the generic set-nested
        # path — otherwise figmaPages lingers and verify.py rejects the
        # state at Gate 2.
        assert data["design"]["figmaPages"] == []

    def test_set_nested_design_mode_figma_clears_supplied_path(self, tmp_path, capsys):
        sf = self._seed(tmp_path, mode="supplied", suppliedPath="/abs/m")
        cmd_set_nested([sf, "design.mode", '"figma"'])
        with open(sf) as f:
            data = json.load(f)
        assert data["design"]["mode"] == "figma"
        assert data["design"]["suppliedPath"] is None

    def test_set_nested_unrelated_path_unaffected(self, tmp_path, capsys):
        """Writes outside ``design.mode`` must not trigger the helper."""
        sf = self._seed(
            tmp_path,
            mode="figma",
            figmaPages=[{"title": "Home", "url": "https://figma.com/x"}],
        )
        cmd_set_nested([sf, "phases.1.status", '"in_progress"'])
        with open(sf) as f:
            data = json.load(f)
        # figmaPages preserved — only design.mode writes are intercepted
        assert data["design"]["figmaPages"] == [
            {"title": "Home", "url": "https://figma.com/x"}
        ]
