"""Domain dispatch + greenfield + override integration tests (M3).

ADR-0003 dispatch matrix coverage for the four single-domain cases that
M3 owns (multi-domain + tie are deferred to M4):

    (1) high-confidence single  → tauri-sample fixture → desktop ≥ 0.85
    (2) low-confidence single   → lowconf-sample → confidence < 0.85
    (3) greenfield              → empty fixture → preflight greenfield True
    (4) user override           → ``--domain desktop`` parsed off $ARGUMENTS

Companion tests cover ``compose --persona rust_engineer --scope <fixture>``
(skill loading from desktop.yaml) and the new
``scripts/jarfis/work_args.py`` parser.
"""

import json
import os

import pytest

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "jarfis", "tests", "fixtures",
)


def _fixture(name):
    return os.path.abspath(os.path.join(FIXTURES_DIR, name))


# ── M3.1 — A0 desktop dispatch (Tauri fixture) ───────────────────────


class TestTauriFixturePresent:
    def test_fixture_dir_exists(self):
        assert os.path.isdir(_fixture("tauri-sample")), (
            "Tauri fixture dir missing — see scripts/jarfis/tests/fixtures/"
        )

    def test_tauri_conf_present(self):
        assert os.path.isfile(
            os.path.join(_fixture("tauri-sample"), "src-tauri", "tauri.conf.json")
        )

    def test_cargo_toml_present(self):
        assert os.path.isfile(os.path.join(_fixture("tauri-sample"), "Cargo.toml"))

    def test_package_json_has_tauri(self):
        path = os.path.join(_fixture("tauri-sample"), "package.json")
        with open(path) as f:
            data = json.load(f)
        all_deps = {}
        for section in ("dependencies", "devDependencies"):
            all_deps.update(data.get(section, {}))
        assert any("tauri" in dep for dep in all_deps), (
            "Tauri fixture package.json must contain a tauri dependency"
        )


class TestHighConfidenceTauriDispatch:
    """Case (1) — Tauri fixture must dispatch to desktop with ≥ 0.85
    confidence and 1 winning candidate."""

    def test_detect_returns_desktop(self):
        from jarfis.domain import detect
        result = detect(_fixture("tauri-sample"))
        matches = result["matches"]
        assert matches, "Expected at least one matched domain"
        # desktop must rank #1
        assert matches[0]["domain"] == "desktop", (
            f"Expected desktop top-ranked, got {[m['domain'] for m in matches]}"
        )

    def test_detect_high_confidence(self):
        from jarfis.domain import detect
        result = detect(_fixture("tauri-sample"))
        top = result["matches"][0]
        assert top["confidence"] >= 0.85, (
            f"Tauri fixture should hit ≥0.85 confidence, got {top['confidence']}"
        )

    def test_detect_no_tie(self):
        from jarfis.domain import detect
        result = detect(_fixture("tauri-sample"))
        # We don't enforce single-candidate (tauri-npm matches package.json
        # which web also reads), but desktop must beat web by margin.
        assert result["tie"] is False, (
            "Tauri fixture must not produce a tie between web and desktop"
        )

    def test_compose_loads_rust_engineer_skills(self):
        """desktop.yaml roles.implement[rust_engineer].skills =
        ['rust', 'tauri-backend']. compose() must load both."""
        from jarfis.domain import compose
        result = compose("desktop", "rust_engineer", "implement login flow")
        assert result["fallback"] is False, (
            f"compose returned fallback: {result.get('error')}"
        )
        loaded = set(result["loaded_skills"])
        # Both skills should resolve since flat skills/ has rust.md + tauri-backend.md
        assert "rust" in loaded, f"rust skill not loaded: {loaded}"
        assert "tauri-backend" in loaded, f"tauri-backend not loaded: {loaded}"


# ── M3.5 — A3.1 preflight greenfield signal ─────────────────────────


class TestPreflightGreenfield:
    """preflight.py must emit a ``greenfield`` boolean so work.md Phase 0
    can trigger the AskUserQuestion described in ADR-0003 §2.4."""

    def test_empty_dir_is_greenfield(self, tmp_path, capsys, jarfis_env):
        """Brand new empty directory → greenfield True."""
        from jarfis.preflight import main
        main([str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        assert "greenfield" in out, (
            "preflight output must include a `greenfield` field (ADR-0003 §2.4)"
        )
        assert out["greenfield"] is True

    def test_existing_project_not_greenfield(self, tmp_path, capsys, jarfis_env):
        """Directory with project profile → not greenfield."""
        from jarfis.preflight import main
        jarfis_dir = tmp_path / ".jarfis-project"
        jarfis_dir.mkdir()
        (jarfis_dir / "project-profile.md").write_text("# Profile")
        main([str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        assert out["greenfield"] is False

    def test_dir_with_manifest_not_greenfield(self, tmp_path, capsys, jarfis_env):
        """Directory with package.json (a project) → not greenfield, even
        without profile (preflight still warns about profile but does NOT
        flag greenfield)."""
        from jarfis.preflight import main
        (tmp_path / "package.json").write_text('{"name": "x"}')
        main([str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        assert out["greenfield"] is False, (
            "Existing codebase (manifest present) must not be flagged greenfield"
        )

    def test_greenfield_dir_emits_user_question_warning(self, tmp_path, capsys, jarfis_env):
        """Greenfield directory should add a soft warning string that
        work.md Phase 0 can use to trigger AskUserQuestion."""
        from jarfis.preflight import main
        main([str(tmp_path)])
        out = json.loads(capsys.readouterr().out)
        assert any("greenfield" in w.lower() or "no codebase" in w.lower()
                   for w in out["warnings"]), (
            f"Expected greenfield warning, got: {out['warnings']}"
        )


# ── M3.6 — A3.2 /jarfis:work --domain argument parsing ──────────────


class TestParseWorkArgs:
    """parse_work_args(arg_string) extracts ``--domain`` and
    ``--scope-domain <name>=<domain>`` overrides off $ARGUMENTS so
    work.md Phase 0 step 7 can bypass detect."""

    def test_no_args_returns_empty(self):
        from jarfis.work_args import parse_work_args
        assert parse_work_args("") == {}
        assert parse_work_args(None) == {}

    def test_domain_override(self):
        from jarfis.work_args import parse_work_args
        args = parse_work_args("--domain desktop")
        assert args.get("domain") == "desktop"

    def test_domain_override_web(self):
        from jarfis.work_args import parse_work_args
        args = parse_work_args("--domain web")
        assert args["domain"] == "web"

    def test_domain_override_mobile(self):
        from jarfis.work_args import parse_work_args
        args = parse_work_args("--domain mobile")
        assert args["domain"] == "mobile"

    def test_domain_invalid_raises(self):
        """Invalid domain values must raise so the user gets a clear error
        instead of a silent fallback to detect."""
        from jarfis.work_args import parse_work_args, WorkArgsError
        with pytest.raises(WorkArgsError):
            parse_work_args("--domain windows")

    def test_scope_domain_per_scope(self):
        from jarfis.work_args import parse_work_args
        args = parse_work_args(
            "--scope-domain shell=desktop --scope-domain app=mobile"
        )
        assert args["scope_domains"] == {"shell": "desktop", "app": "mobile"}

    def test_combined_domain_and_scope_domain(self):
        from jarfis.work_args import parse_work_args
        args = parse_work_args(
            "--domain mobile --scope-domain shell=desktop"
        )
        assert args["domain"] == "mobile"
        assert args["scope_domains"] == {"shell": "desktop"}

    def test_scope_domain_invalid_format(self):
        """``--scope-domain shell`` (no `=`) must raise."""
        from jarfis.work_args import parse_work_args, WorkArgsError
        with pytest.raises(WorkArgsError):
            parse_work_args("--scope-domain shell")

    def test_scope_domain_invalid_domain_value(self):
        from jarfis.work_args import parse_work_args, WorkArgsError
        with pytest.raises(WorkArgsError):
            parse_work_args("--scope-domain shell=windows")

    def test_user_text_passes_through(self):
        """Free-text input (work description) is preserved as ``input``."""
        from jarfis.work_args import parse_work_args
        args = parse_work_args(
            "build login flow --domain desktop"
        )
        assert args["domain"] == "desktop"
        assert args["input"].strip() == "build login flow"

    def test_input_only_no_overrides(self):
        from jarfis.work_args import parse_work_args
        args = parse_work_args("just refactor the auth module")
        assert "domain" not in args
        assert args.get("input", "").startswith("just refactor")


# ── M3.7 — single-domain dispatch case matrix ───────────────────────


class TestDispatchCases:
    """ADR-0003 §2.2 dispatch matrix — single-domain subset (4/6).

    Multi-domain monorepo (case 5) and tie (case 6) are M4 territory.
    """

    def test_case_1_high_confidence_tauri(self):
        """Case 1: Tauri fixture → desktop, confidence ≥ 0.85."""
        from jarfis.domain import detect
        result = detect(_fixture("tauri-sample"))
        assert result["matches"]
        top = result["matches"][0]
        assert top["domain"] == "desktop"
        assert top["confidence"] >= 0.85

    def test_case_2_low_confidence(self):
        """Case 2: package.json without framework keys → either zero
        matches or a single match with confidence < 0.85 (forces
        AskUserQuestion in work.md)."""
        from jarfis.domain import detect
        result = detect(_fixture("lowconf-sample"))
        if result["matches"]:
            top = result["matches"][0]
            assert top["confidence"] < 0.85, (
                f"lowconf fixture matched too strongly ({top['confidence']}), "
                "expected sub-0.85 forcing AskUserQuestion"
            )

    def test_case_3_greenfield_empty_dir(self, capsys, jarfis_env):
        """Case 3: empty fixture → preflight `greenfield: True`."""
        from jarfis.preflight import main
        main([_fixture("greenfield-empty")])
        out = json.loads(capsys.readouterr().out)
        assert out["greenfield"] is True

    def test_case_3_greenfield_detect_returns_no_matches(self):
        """detect on the empty fixture returns no matches (caller treats
        empty matches as greenfield signal alongside preflight)."""
        from jarfis.domain import detect
        result = detect(_fixture("greenfield-empty"))
        assert result["matches"] == []
        assert result["tie"] is False

    def test_case_4_user_override_bypasses_detect(self):
        """Case 4: ``--domain desktop`` short-circuits detect output.

        This is a contract test — the parser yields the override; work.md
        Phase 0 step 7 is responsible for honoring it before calling
        domain detect.
        """
        from jarfis.work_args import parse_work_args
        args = parse_work_args("--domain desktop")
        assert args["domain"] == "desktop"
        # The contract: when args["domain"] is set, the orchestrator
        # MUST skip detect. We assert the parser surfaces the field so
        # work.md can branch on it.
        assert "domain" in args

    def test_case_4_override_scope_domain(self):
        """Case 4 (per-scope variant): --scope-domain shell=desktop."""
        from jarfis.work_args import parse_work_args
        args = parse_work_args("--scope-domain shell=desktop")
        assert args["scope_domains"] == {"shell": "desktop"}


# ── M6.1/M6.2 — multi-domain monorepo dispatch (ADR-0003 §2.2 case 5) ─


class TestMultiDomainFixturePresent:
    """The multi-domain fixture simulates a single repo with three
    workspaces — Tauri shell (desktop), RN app (mobile), React admin
    (web) — exercised via separate ``domain detect`` calls plus the
    per-scope state seed integration test below.
    """

    def test_fixture_dir_exists(self):
        assert os.path.isdir(_fixture("multi-domain")), (
            "multi-domain fixture missing — see scripts/jarfis/tests/fixtures/"
        )

    def test_root_workspaces_manifest(self):
        path = os.path.join(_fixture("multi-domain"), "package.json")
        with open(path) as f:
            data = json.load(f)
        assert "workspaces" in data, (
            "multi-domain root package.json must declare workspaces"
        )
        assert set(data["workspaces"]) == {"shell", "app", "admin"}

    def test_shell_has_tauri_markers(self):
        shell = os.path.join(_fixture("multi-domain"), "shell")
        assert os.path.isfile(os.path.join(shell, "tauri.conf.json"))
        assert os.path.isfile(os.path.join(shell, "Cargo.toml"))
        assert os.path.isfile(os.path.join(shell, "src-tauri", "tauri.conf.json"))

    def test_app_has_react_native_markers(self):
        app = os.path.join(_fixture("multi-domain"), "app")
        with open(os.path.join(app, "package.json")) as f:
            data = json.load(f)
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        assert "react-native" in deps
        assert os.path.isfile(os.path.join(app, "metro.config.js"))
        assert os.path.isfile(os.path.join(app, "ios", "Podfile"))
        assert os.path.isfile(os.path.join(app, "android", "build.gradle"))

    def test_admin_has_react_web_markers(self):
        admin = os.path.join(_fixture("multi-domain"), "admin")
        with open(os.path.join(admin, "package.json")) as f:
            data = json.load(f)
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        assert "react" in deps
        # admin must NOT contain RN or Tauri markers
        assert "react-native" not in deps
        assert not os.path.isfile(os.path.join(admin, "tauri.conf.json"))


class TestMultiDomainPerScopeDispatch:
    """ADR-0003 §2.2 case (5): each workspace inside a monorepo must
    dispatch to its own domain when detected independently."""

    def test_shell_detects_desktop(self):
        from jarfis.domain import detect
        result = detect(_fixture("multi-domain/shell"))
        assert result["matches"], "shell should produce at least one match"
        top = result["matches"][0]
        assert top["domain"] == "desktop", (
            f"shell expected desktop, got {[m['domain'] for m in result['matches']]}"
        )
        assert top["confidence"] >= 0.85
        assert result["tie"] is False

    def test_app_detects_mobile(self):
        from jarfis.domain import detect
        result = detect(_fixture("multi-domain/app"))
        assert result["matches"], "app should produce at least one match"
        top = result["matches"][0]
        assert top["domain"] == "mobile", (
            f"app expected mobile, got {[m['domain'] for m in result['matches']]}"
        )
        assert top["confidence"] >= 0.85
        assert result["tie"] is False, (
            "RN markers (4 indicators) must beat web (2 indicators) on "
            "matched_count tiebreak"
        )

    def test_admin_detects_web(self):
        from jarfis.domain import detect
        result = detect(_fixture("multi-domain/admin"))
        assert result["matches"], "admin should produce at least one match"
        top = result["matches"][0]
        assert top["domain"] == "web", (
            f"admin expected web, got {[m['domain'] for m in result['matches']]}"
        )
        assert result["tie"] is False

    def test_three_distinct_domains_across_workspaces(self):
        """End-to-end: detection across all three workspaces yields
        exactly three distinct domains (desktop, mobile, web)."""
        from jarfis.domain import detect
        domains = set()
        for sub in ("shell", "app", "admin"):
            r = detect(_fixture(f"multi-domain/{sub}"))
            assert r["matches"]
            domains.add(r["matches"][0]["domain"])
        assert domains == {"desktop", "mobile", "web"}


class TestMultiDomainScopeStateSeed:
    """B1.1 + ADR-0003 §2.2 (5): when work.md Phase 0 builds
    state.workspace.scope[] for a multi-domain repo, each scope[i]
    must carry its own ``domain`` field. We verify two paths:

    (a) ``--scope-domain`` overrides parsed off $ARGUMENTS so users can
        force the layout without relying on detect.
    (b) automatic per-scope detect — calling detect() per scope dir
        produces the matching domain assignment used as the state seed.
    """

    def test_scope_domain_args_seed_multi_domain_state(self):
        """Parsing ``--scope-domain shell=desktop --scope-domain app=mobile
        --scope-domain admin=web`` yields the per-scope assignment that
        work.md Phase 0 will write into state.workspace.scope[i].domain.
        """
        from jarfis.work_args import parse_work_args
        args = parse_work_args(
            "--scope-domain shell=desktop "
            "--scope-domain app=mobile "
            "--scope-domain admin=web"
        )
        assert args["scope_domains"] == {
            "shell": "desktop",
            "app": "mobile",
            "admin": "web",
        }

    def test_per_scope_detection_yields_state_seed(self):
        """Composing the state seed from per-scope detect() reproduces
        the ``--scope-domain`` override above, demonstrating that the
        fixture is a faithful end-to-end test for ADR-0003 §2.2 case 5.
        """
        from jarfis.domain import detect
        seed = []
        for name in ("shell", "app", "admin"):
            r = detect(_fixture(f"multi-domain/{name}"))
            seed.append({"name": name, "domain": r["matches"][0]["domain"]})
        # Build a state-shaped scope[] and assert per-scope domain.
        state = {"workspace": {"scope": seed}}
        scopes = {s["name"]: s["domain"] for s in state["workspace"]["scope"]}
        assert scopes == {
            "shell": "desktop",
            "app": "mobile",
            "admin": "web",
        }

    def test_scope_domain_override_matches_auto_detection(self):
        """Override should agree with auto-detection — guards against
        future fixture or detector drift."""
        from jarfis.domain import detect
        from jarfis.work_args import parse_work_args
        args = parse_work_args(
            "--scope-domain shell=desktop "
            "--scope-domain app=mobile "
            "--scope-domain admin=web"
        )
        for name, expected in args["scope_domains"].items():
            r = detect(_fixture(f"multi-domain/{name}"))
            assert r["matches"][0]["domain"] == expected, (
                f"scope-domain override `{name}={expected}` disagrees with "
                f"auto-detect ({r['matches'][0]['domain']})"
            )
