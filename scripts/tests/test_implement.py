"""Tests for jarfis.implement — sys-implement deliverables workspace.

Verifies ADR-0003 (Saga + LangGraph + Command + Clean Architecture synthesis).
Workspace location: {JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/.
"""

import json
import os
import time

import pytest

from jarfis.implement import (
    cmd_archive,
    cmd_init,
    cmd_list,
    cmd_log,
    cmd_resume,
    cmd_state,
    main,
    PLAN_NAME_RE,
    DEFAULT_PLANNED_STEPS,
    InvalidPlanNameError,
    WorkspaceLockedError,
    WorkspaceNotFoundError,
    LogAppendOnlyViolation,
)


# ── §2.7 plan-name validation ──────────────────────────────────────


class TestPlanNameValidation:
    def test_valid_kebab_case(self):
        assert PLAN_NAME_RE.match("rag-integration-v1")
        assert PLAN_NAME_RE.match("a")
        assert PLAN_NAME_RE.match("dialectic-evidence-v2")

    def test_rejects_uppercase(self):
        assert not PLAN_NAME_RE.match("Test_Plan")
        assert not PLAN_NAME_RE.match("RAG-v1")

    def test_rejects_underscore(self):
        assert not PLAN_NAME_RE.match("rag_integration")

    def test_rejects_starting_digit(self):
        assert not PLAN_NAME_RE.match("1-plan")

    def test_rejects_special_chars(self):
        assert not PLAN_NAME_RE.match("plan!")
        assert not PLAN_NAME_RE.match("plan/v1")

    def test_max_length(self):
        # >40 chars rejected at higher level (cmd_init), regex itself
        # accepts long matches — length check is in init/validation
        assert PLAN_NAME_RE.match("a" * 50)


# ── §M4.1 cmd_init — workspace creation ───────────────────────────


class TestCmdInit:
    def test_creates_workspace_directories(self, jarfis_env):
        cmd_init(["rag-integration-v1", "Add RAG integration"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "rag-integration-v1"
        )
        assert os.path.isdir(plan_dir)
        assert os.path.isdir(os.path.join(plan_dir, "log"))
        assert os.path.isdir(os.path.join(plan_dir, "artifacts"))

    def test_writes_manifest_json(self, jarfis_env):
        cmd_init(["rag-integration-v1", "Add RAG integration"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "rag-integration-v1"
        )
        with open(os.path.join(plan_dir, "manifest.json")) as f:
            m = json.load(f)
        assert m["planName"] == "rag-integration-v1"
        assert m["request"] == "Add RAG integration"
        assert m["schemaVersion"] == "sys-implement-manifest-v1"
        assert m["plannedSteps"] == DEFAULT_PLANNED_STEPS
        assert m["executionMode"] is None  # set later in Step 1.7
        assert "createdAt" in m

    def test_writes_state_json(self, jarfis_env):
        cmd_init(["rag-integration-v1", "Add RAG integration"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "rag-integration-v1"
        )
        with open(os.path.join(plan_dir, "state.json")) as f:
            s = json.load(f)
        assert s["planName"] == "rag-integration-v1"
        assert s["currentState"] == "step0"
        assert s["schemaVersion"] == "sys-implement-state-v1"
        assert s["steps"]["step0"]["status"] == "in_progress"
        assert s["steps"]["step1"]["status"] == "pending"
        assert s["blockers"] == []
        assert s["user_gates_pending"] == []

    def test_writes_resume_md_and_readme(self, jarfis_env):
        cmd_init(["rag-integration-v1", "Add RAG integration"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "rag-integration-v1"
        )
        assert os.path.isfile(os.path.join(plan_dir, "RESUME.md"))
        assert os.path.isfile(os.path.join(plan_dir, "README.md"))

    def test_writes_initial_log_entry(self, jarfis_env):
        cmd_init(["rag-integration-v1", "Add RAG integration"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "rag-integration-v1"
        )
        log_files = sorted(os.listdir(os.path.join(plan_dir, "log")))
        assert len(log_files) == 1
        assert log_files[0].startswith("0000-init")
        with open(os.path.join(plan_dir, "log", log_files[0])) as f:
            entry = json.load(f)
        assert entry["event"] == "init"
        assert entry["id"] == "0000"

    def test_rejects_invalid_plan_name(self, jarfis_env):
        with pytest.raises(InvalidPlanNameError):
            cmd_init(["Test_Plan", "request"])

    def test_rejects_too_long_plan_name(self, jarfis_env):
        with pytest.raises(InvalidPlanNameError):
            cmd_init(["a" * 41, "request"])

    def test_rejects_collision_without_resume_flag(self, jarfis_env):
        cmd_init(["rag-integration-v1", "first request"])
        with pytest.raises(SystemExit):
            cmd_init(["rag-integration-v1", "second request"])


# ── §M4.1 cmd_state — read/write ────────────────────────────────


class TestCmdState:
    def test_get_returns_current_state(self, jarfis_env, capsys):
        cmd_init(["plan-v1", "request"])
        capsys.readouterr()  # discard init output
        cmd_state(["plan-v1", "--get", "currentState"])
        output = capsys.readouterr().out
        assert json.loads(output) == "step0"

    def test_set_updates_lastUpdated(self, jarfis_env):
        cmd_init(["plan-v1", "request"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        with open(os.path.join(plan_dir, "state.json")) as f:
            old_ts = json.load(f)["lastUpdated"]
        time.sleep(0.01)
        cmd_state(["plan-v1", "--set", "currentState=step1"])
        with open(os.path.join(plan_dir, "state.json")) as f:
            s = json.load(f)
        assert s["currentState"] == "step1"
        assert s["lastUpdated"] != old_ts

    def test_set_nested(self, jarfis_env):
        cmd_init(["plan-v1", "request"])
        cmd_state(
            ["plan-v1", "--set-nested", "steps.step0.status", "completed"]
        )
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        with open(os.path.join(plan_dir, "state.json")) as f:
            s = json.load(f)
        assert s["steps"]["step0"]["status"] == "completed"

    def test_set_nested_with_dotted_literal_key(self, jarfis_env):
        """`steps.step1.5.status completed` must address the literal "step1.5"
        key, not nest as steps→step1→"5"→status. Init creates step1.5,
        step3.5, step4.5 keys with dots; --set-nested must honor them.
        Regression: discovered in M7.2 E2E (scenario 1)."""
        cmd_init(["plan-v1", "request"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        for dotted_step in ("step1.5", "step3.5", "step4.5"):
            cmd_state(
                ["plan-v1", "--set-nested", f"steps.{dotted_step}.status", "skipped"]
            )
        with open(os.path.join(plan_dir, "state.json")) as f:
            s = json.load(f)
        assert s["steps"]["step1.5"]["status"] == "skipped"
        assert s["steps"]["step3.5"]["status"] == "skipped"
        assert s["steps"]["step4.5"]["status"] == "skipped"
        # Negative: must NOT have created the spurious nested "step1"."5" path
        assert "5" not in s["steps"].get("step1", {})
        assert "5" not in s["steps"].get("step3", {})
        assert "5" not in s["steps"].get("step4", {})

    def test_set_nested_creates_missing_intermediate(self, jarfis_env):
        """Greedy-match must still create new nested dicts when no literal
        key exists at the current level."""
        cmd_init(["plan-v1", "request"])
        cmd_state(
            ["plan-v1", "--set-nested", "newSection.subkey.value", "42"]
        )
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        with open(os.path.join(plan_dir, "state.json")) as f:
            s = json.load(f)
        assert s["newSection"]["subkey"]["value"] == 42

    def test_workspace_not_found(self, jarfis_env):
        with pytest.raises(WorkspaceNotFoundError):
            cmd_state(["nonexistent-plan", "--get", "currentState"])


# ── §M4.1 cmd_log — append-only ─────────────────────────────────


class TestCmdLog:
    def test_append_increments_id(self, jarfis_env):
        cmd_init(["plan-v1", "request"])
        cmd_log(["plan-v1", "append", '{"event":"test1","step":"step0"}'])
        cmd_log(["plan-v1", "append", '{"event":"test2","step":"step1"}'])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        log_files = sorted(os.listdir(os.path.join(plan_dir, "log")))
        # 0000-init.json + 0001-step0-test1.json + 0002-step1-test2.json
        assert len(log_files) == 3
        assert log_files[1].startswith("0001-")
        assert log_files[2].startswith("0002-")

    def test_appended_entry_has_correct_id_and_ts(self, jarfis_env):
        cmd_init(["plan-v1", "request"])
        cmd_log(["plan-v1", "append", '{"event":"started","step":"step0"}'])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        log_files = sorted(os.listdir(os.path.join(plan_dir, "log")))
        with open(os.path.join(plan_dir, "log", log_files[1])) as f:
            entry = json.load(f)
        assert entry["id"] == "0001"
        assert entry["event"] == "started"
        assert entry["step"] == "step0"
        assert "ts" in entry

    def test_append_only_rejects_modify(self, jarfis_env, monkeypatch):
        cmd_init(["plan-v1", "request"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        # Try to overwrite the init log entry — implementation should refuse
        existing = os.path.join(plan_dir, "log", "0000-init.json")
        from jarfis.implement import _write_log_entry
        with pytest.raises(LogAppendOnlyViolation):
            _write_log_entry(plan_dir, {"id": "0000", "event": "tampered"})


# ── §M4.1 cmd_resume ─────────────────────────────────────────────


class TestCmdResume:
    def test_returns_current_state(self, jarfis_env, capsys):
        cmd_init(["plan-v1", "request"])
        cmd_state(["plan-v1", "--set", "currentState=step1.5"])
        capsys.readouterr()  # discard init + set output
        cmd_resume(["plan-v1"])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert data["planName"] == "plan-v1"
        assert data["currentState"] == "step1.5"
        assert data["user_gates_pending"] == []
        assert "nextAction" in data


# ── §M4.1 cmd_list ────────────────────────────────────────────────


class TestCmdList:
    def test_groups_by_status(self, jarfis_env, capsys):
        cmd_init(["plan-a-v1", "first"])
        cmd_init(["plan-b-v1", "second"])
        cmd_state(
            ["plan-a-v1", "--set-nested", "currentState", "step5"]
        )
        capsys.readouterr()  # discard prior output
        cmd_list([])
        output = capsys.readouterr().out
        data = json.loads(output)
        assert "in_progress" in data
        assert any(p["planName"] == "plan-a-v1" for p in data["in_progress"])
        assert any(p["planName"] == "plan-b-v1" for p in data["in_progress"])


# ── §M4.1 cmd_archive ────────────────────────────────────────────


class TestCmdArchive:
    def test_moves_to_archive_dir(self, jarfis_env):
        cmd_init(["plan-v1", "request"])
        cmd_archive(["plan-v1"])
        impl_dir = os.path.join(jarfis_env["personal_dir"], "sys-implements")
        assert not os.path.isdir(os.path.join(impl_dir, "plan-v1"))
        archive_dir = os.path.join(impl_dir, "_archive")
        assert os.path.isdir(archive_dir)
        archived = os.listdir(archive_dir)
        assert len(archived) == 1
        assert archived[0].endswith("-plan-v1")


# ── §M4.1 lock file ──────────────────────────────────────────────


class TestLockFile:
    def test_lock_file_prevents_concurrent(self, jarfis_env):
        cmd_init(["plan-v1", "request"])
        from jarfis.implement import _acquire_lock, _release_lock, get_plan_dir
        plan_dir = get_plan_dir("plan-v1")
        fd = _acquire_lock(plan_dir)
        try:
            with pytest.raises(WorkspaceLockedError):
                _acquire_lock(plan_dir)
        finally:
            _release_lock(fd, plan_dir)


# ── §M4.1 main entry point ───────────────────────────────────────


class TestMain:
    def test_routes_init(self, jarfis_env):
        main(["init", "plan-v1", "test request"])
        plan_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", "plan-v1"
        )
        assert os.path.isdir(plan_dir)

    def test_unknown_subcommand_exits(self):
        with pytest.raises(SystemExit):
            main(["unknown-subcommand"])

    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            main([])


# ── ADR-0005 — Dialectic evidence policy (M5) ───────────────────────


class TestValidateCitations:
    def test_valid_path_line(self, tmp_path):
        from jarfis.implement import validate_citations
        p = tmp_path / "sample.md"
        p.write_text("line1\nline2 hello\nline3\n")
        text = f"As shown in `{p}:2`, hello appears."
        cites = validate_citations(text)
        assert len(cites) == 1
        assert cites[0].path == str(p)
        assert cites[0].line_start == 2
        assert cites[0].line_end == 2
        assert cites[0].status == "valid"
        assert "hello" in cites[0].text

    def test_invalid_path(self):
        from jarfis.implement import validate_citations
        text = "Reference `~/nonexistent-jarfis-test-12345.md:42`."
        cites = validate_citations(text)
        assert len(cites) == 1
        assert cites[0].status == "invalid_path"

    def test_invalid_line_range(self, tmp_path):
        from jarfis.implement import validate_citations
        p = tmp_path / "tiny.md"
        p.write_text("only one line\n")
        text = f"See `{p}:99`."
        cites = validate_citations(text)
        assert len(cites) == 1
        assert cites[0].status == "invalid_line"

    def test_tilde_expansion(self, tmp_path, monkeypatch):
        from jarfis.implement import validate_citations
        # Use HOME monkeypatch so ~/foo expands into tmp_path
        monkeypatch.setenv("HOME", str(tmp_path))
        p = tmp_path / "x.md"
        p.write_text("hello world\n")
        text = "Cited at `~/x.md:1`."
        cites = validate_citations(text)
        assert len(cites) == 1
        assert cites[0].status == "valid"

    def test_range_format(self, tmp_path):
        from jarfis.implement import validate_citations
        p = tmp_path / "ranges.md"
        p.write_text("a\nb\nc\nd\ne\n")
        text = f"See `{p}:2-4`."
        cites = validate_citations(text)
        assert len(cites) == 1
        assert cites[0].line_start == 2
        assert cites[0].line_end == 4
        assert cites[0].status == "valid"
        # text should include 3 lines (b, c, d)
        assert "b" in cites[0].text and "c" in cites[0].text and "d" in cites[0].text

    def test_no_citations_returns_empty(self):
        from jarfis.implement import validate_citations
        cites = validate_citations("plain prose with no backticks")
        assert cites == []

    def test_multiple_citations(self, tmp_path):
        from jarfis.implement import validate_citations
        p = tmp_path / "multi.md"
        p.write_text("a\nb\nc\n")
        text = f"see `{p}:1` and also `{p}:3`."
        cites = validate_citations(text)
        assert len(cites) == 2


class TestClassifyVerdict:
    def test_critic_only_valid_advocate_invalid_path(self, tmp_path):
        """Advocate cites bad path → critic wins (advocate concedes)."""
        from jarfis.implement import classify_verdict
        p = tmp_path / "real.md"
        p.write_text("here\n")
        adv = "I claim it works `~/missing-fake-path-99999.md:1`."
        crit = f"Blocked at `{p}:1` — see 'here'."
        verdict = classify_verdict(adv, crit, "")
        assert verdict.status == "ACKNOWLEDGED-critic-wins"

    def test_advocate_only_valid_critic_no_citation(self, tmp_path):
        """Critic without any file:line citation → automatic loss for critic."""
        from jarfis.implement import classify_verdict
        p = tmp_path / "real.md"
        p.write_text("here\n")
        adv = f"My case rests on `{p}:1`."
        crit = "I disagree but I have no citation to back it."
        verdict = classify_verdict(adv, crit, "")
        assert verdict.status == "ACKNOWLEDGED-advocate-wins"

    def test_both_valid_unresolved(self, tmp_path):
        """Both sides cite valid file:line → orchestrator must defer to user."""
        from jarfis.implement import classify_verdict
        p = tmp_path / "real.md"
        p.write_text("a\nb\n")
        adv = f"From `{p}:1`."
        crit = f"But `{p}:2`."
        verdict = classify_verdict(adv, crit, "")
        assert verdict.status == "UNRESOLVED"

    def test_neither_valid_critic_loses_first(self):
        """Neither has valid citations → critic's lack-of-citation wins first
        (formal violation by critic — advocate-wins)."""
        from jarfis.implement import classify_verdict
        adv = "Trust me bro."
        crit = "No, trust ME bro."
        verdict = classify_verdict(adv, crit, "")
        assert verdict.status == "ACKNOWLEDGED-advocate-wins"

    def test_advocate_rebuttal_counted(self, tmp_path):
        """Advocate's first turn lacks citation but rebuttal supplies one — should still count."""
        from jarfis.implement import classify_verdict
        p = tmp_path / "real.md"
        p.write_text("a\nb\n")
        adv_first = "Initial claim, no citation yet."
        crit = f"Blocked at `{p}:1`."
        adv_rebuttal = f"Rebut with `{p}:2`."
        verdict = classify_verdict(adv_first, crit, adv_rebuttal)
        # critic valid + advocate (rebuttal) valid → UNRESOLVED
        assert verdict.status == "UNRESOLVED"


# ── ADR-0004 — execution mode dispatch (M5) ─────────────────────────


class TestRecommendExecutionMode:
    def test_single_one_file_content(self):
        from jarfis.implement import recommend_execution_mode
        impact = {"files_affected": ["commands/jarfis/aws-lambda.md"], "change_type": "content"}
        mode, reason = recommend_execution_mode(impact)
        assert mode == "single"

    def test_single_two_file_content(self):
        from jarfis.implement import recommend_execution_mode
        impact = {
            "files_affected": [
                "commands/jarfis/aws-lambda.md",
                "commands/jarfis/jarfis-index.md",
            ],
            "change_type": "content",
        }
        mode, reason = recommend_execution_mode(impact)
        assert mode == "single"

    def test_tmux_python_modification(self):
        from jarfis.implement import recommend_execution_mode
        impact = {
            "files_affected": [
                "scripts/jarfis/foo.py",
                "scripts/tests/test_foo.py",
            ],
            "change_type": "content",
        }
        mode, reason = recommend_execution_mode(impact)
        assert mode == "tmux"
        assert "python" in reason.lower() or "scripts/jarfis" in reason

    def test_tmux_four_files(self):
        from jarfis.implement import recommend_execution_mode
        impact = {
            "files_affected": [f"commands/jarfis/skill-{i}.md" for i in range(4)],
            "change_type": "content",
        }
        mode, reason = recommend_execution_mode(impact)
        assert mode == "tmux"

    def test_tmux_force_six_files(self):
        from jarfis.implement import recommend_execution_mode
        impact = {
            "files_affected": [f"f{i}.md" for i in range(6)],
            "change_type": "content",
        }
        mode, reason = recommend_execution_mode(impact)
        assert mode == "tmux"
        # force tmux when file_count >= 6
        assert "6" in reason or "강제" in reason or "force" in reason.lower()

    def test_tmux_structural(self):
        from jarfis.implement import recommend_execution_mode
        impact = {"files_affected": ["a.md", "b.md"], "change_type": "structural"}
        mode, reason = recommend_execution_mode(impact)
        assert mode == "tmux"

    def test_tmux_new_command(self):
        from jarfis.implement import recommend_execution_mode
        impact = {"files_affected": ["a.md", "b.md"], "change_type": "new-command"}
        mode, reason = recommend_execution_mode(impact)
        assert mode == "tmux"

    def test_returns_tuple(self):
        from jarfis.implement import recommend_execution_mode
        impact = {"files_affected": ["a.md"], "change_type": "content"}
        result = recommend_execution_mode(impact)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] in ("single", "tmux")
        assert isinstance(result[1], str)


# ── ADR-0002 §2.4 — RAG auto-update hook (M6) ───────────────────────


class TestExtractChangedFiles:
    def _setup_plan(self, jarfis_env, plan_name="rag-update-test-v1"):
        cmd_init([plan_name, "extract changed files test"])
        impl_dir = os.path.join(
            jarfis_env["personal_dir"], "sys-implements", plan_name
        )
        step2_dir = os.path.join(impl_dir, "artifacts", "step2")
        os.makedirs(step2_dir, exist_ok=True)
        return impl_dir, step2_dir

    def test_parses_git_style_diff(self, jarfis_env):
        from jarfis.implement import extract_changed_files
        plan_dir, step2 = self._setup_plan(jarfis_env)
        diff = (
            "diff --git a/commands/jarfis/aws-lambda.md b/commands/jarfis/aws-lambda.md\n"
            "--- a/commands/jarfis/aws-lambda.md\n"
            "+++ b/commands/jarfis/aws-lambda.md\n"
            "@@ -1 +1,2 @@\n"
            " line\n"
            "+added\n"
        )
        with open(os.path.join(step2, "diff.patch"), "w") as f:
            f.write(diff)
        files = extract_changed_files(plan_dir)
        assert files == ["commands/jarfis/aws-lambda.md"]

    def test_parses_multiple_files(self, jarfis_env):
        from jarfis.implement import extract_changed_files
        plan_dir, step2 = self._setup_plan(jarfis_env)
        diff = (
            "diff --git a/agents/jarfis/x.md b/agents/jarfis/x.md\n"
            "--- a/agents/jarfis/x.md\n"
            "+++ b/agents/jarfis/x.md\n"
            "@@ -1 +1 @@\n"
            "-old\n+new\n"
            "diff --git a/scripts/jarfis/y.py b/scripts/jarfis/y.py\n"
            "--- a/scripts/jarfis/y.py\n"
            "+++ b/scripts/jarfis/y.py\n"
            "@@ -1 +1 @@\n"
            "-pass\n+return 1\n"
        )
        with open(os.path.join(step2, "diff.patch"), "w") as f:
            f.write(diff)
        files = extract_changed_files(plan_dir)
        assert sorted(files) == sorted([
            "agents/jarfis/x.md",
            "scripts/jarfis/y.py",
        ])

    def test_handles_renames(self, jarfis_env):
        """git rename emits two paths: a/old → b/new. Both should be returned."""
        from jarfis.implement import extract_changed_files
        plan_dir, step2 = self._setup_plan(jarfis_env)
        diff = (
            "diff --git a/agents/jarfis/old-name.md b/agents/jarfis/new-name.md\n"
            "rename from agents/jarfis/old-name.md\n"
            "rename to agents/jarfis/new-name.md\n"
        )
        with open(os.path.join(step2, "diff.patch"), "w") as f:
            f.write(diff)
        files = extract_changed_files(plan_dir)
        assert "agents/jarfis/old-name.md" in files
        assert "agents/jarfis/new-name.md" in files

    def test_strips_a_b_prefix(self, jarfis_env):
        """git diff prefixes paths with a/ and b/ — these must be stripped."""
        from jarfis.implement import extract_changed_files
        plan_dir, step2 = self._setup_plan(jarfis_env)
        diff = (
            "--- a/commands/jarfis/x.md\n"
            "+++ b/commands/jarfis/x.md\n"
            "@@ -1 +1 @@\n"
            "-a\n+b\n"
        )
        with open(os.path.join(step2, "diff.patch"), "w") as f:
            f.write(diff)
        files = extract_changed_files(plan_dir)
        assert files == ["commands/jarfis/x.md"]

    def test_returns_empty_when_no_diff(self, jarfis_env):
        from jarfis.implement import extract_changed_files
        plan_dir, _ = self._setup_plan(jarfis_env)
        files = extract_changed_files(plan_dir)
        assert files == []

    def test_skips_dev_null(self, jarfis_env):
        """`+++ /dev/null` (file deletion) should NOT appear in output."""
        from jarfis.implement import extract_changed_files
        plan_dir, step2 = self._setup_plan(jarfis_env)
        diff = (
            "diff --git a/agents/jarfis/old.md b/agents/jarfis/old.md\n"
            "deleted file mode 100644\n"
            "--- a/agents/jarfis/old.md\n"
            "+++ /dev/null\n"
        )
        with open(os.path.join(step2, "diff.patch"), "w") as f:
            f.write(diff)
        files = extract_changed_files(plan_dir)
        # Deleted file path (a/...) should still be recorded — RAG removal needs it.
        assert "agents/jarfis/old.md" in files
        # /dev/null should NOT be in the result
        assert not any("/dev/null" in f for f in files)

    def test_deduplicates(self, jarfis_env):
        """Same file appearing in multiple hunks → one entry."""
        from jarfis.implement import extract_changed_files
        plan_dir, step2 = self._setup_plan(jarfis_env)
        diff = (
            "--- a/commands/jarfis/x.md\n"
            "+++ b/commands/jarfis/x.md\n"
            "@@ -1 +1 @@\n"
            "-a\n+b\n"
            "--- a/commands/jarfis/x.md\n"
            "+++ b/commands/jarfis/x.md\n"
            "@@ -10 +10 @@\n"
            "-c\n+d\n"
        )
        with open(os.path.join(step2, "diff.patch"), "w") as f:
            f.write(diff)
        files = extract_changed_files(plan_dir)
        assert files == ["commands/jarfis/x.md"]
