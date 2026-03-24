"""Tests for jarfis.validate — workflow state and artifact validation."""

import json
import os

import pytest

from jarfis.validate import PHASE_ARTIFACTS, _check_artifacts, _check_state, main


class TestCheckState:
    def test_valid_state(self, state_file):
        valid, errors = _check_state(state_file)
        assert valid is True
        assert errors == []

    def test_missing_file(self):
        valid, errors = _check_state("/nonexistent/state.json")
        assert valid is False

    def test_invalid_json(self, tmp_path):
        sf = tmp_path / "bad.json"
        sf.write_text("not json")
        # _check_state calls state_validate which calls json_error → sys.exit(1)
        # on invalid JSON, so the function never returns (valid, errors)
        with pytest.raises(SystemExit):
            _check_state(str(sf))


class TestCheckArtifacts:
    def test_no_errors_when_pending(self, state_file):
        errors, warnings = _check_artifacts(state_file)
        assert errors == []
        assert warnings == []

    def test_warns_on_missing_artifact(self, state_file):
        # Mark phase 1 as completed
        with open(state_file) as f:
            data = json.load(f)
        data["phases"]["1"]["status"] = "completed"
        with open(state_file, "w") as f:
            json.dump(data, f)

        errors, warnings = _check_artifacts(state_file)
        # Should warn about missing press-release.md and prd.md
        assert len(warnings) >= 2
        assert any("press-release.md" in w for w in warnings)
        assert any("prd.md" in w for w in warnings)

    def test_no_warn_when_artifacts_exist(self, state_file):
        with open(state_file) as f:
            data = json.load(f)
        docs_dir = data["docs_dir"]
        data["phases"]["1"]["status"] = "completed"
        with open(state_file, "w") as f:
            json.dump(data, f)

        # Create expected artifacts
        for artifact in PHASE_ARTIFACTS["1"]:
            with open(os.path.join(docs_dir, artifact), "w") as f:
                f.write(f"# {artifact}")

        errors, warnings = _check_artifacts(state_file)
        phase1_warnings = [w for w in warnings if "Phase 1" in w]
        assert len(phase1_warnings) == 0


class TestMain:
    def test_no_state_file_found(self, jarfis_env, capsys):
        main([])
        output = json.loads(capsys.readouterr().out)
        assert output["valid"] is False

    def test_validates_with_explicit_state_file(self, state_file, jarfis_env, capsys):
        main(["--state-file", state_file])
        output = json.loads(capsys.readouterr().out)
        assert output["valid"] is True
        assert output["state_file"] == state_file

    def test_conditional_ux_direction_check(self, state_file, jarfis_env, capsys):
        with open(state_file) as f:
            data = json.load(f)
        data["phases"]["1"]["status"] = "completed"
        data["required_roles"] = {"ux_designer": True}
        with open(state_file, "w") as f:
            json.dump(data, f)

        main(["--state-file", state_file])
        output = json.loads(capsys.readouterr().out)
        assert any("ux-direction.md" in w for w in output["warnings"])


class TestPhaseArtifacts:
    def test_phase_artifacts_keys(self):
        assert "1" in PHASE_ARTIFACTS
        assert "2" in PHASE_ARTIFACTS
        assert "4" in PHASE_ARTIFACTS
        assert "4.5" in PHASE_ARTIFACTS
        assert "5" in PHASE_ARTIFACTS
        assert "6" in PHASE_ARTIFACTS

    def test_phase_4_has_no_artifacts(self):
        assert PHASE_ARTIFACTS["4"] == []
