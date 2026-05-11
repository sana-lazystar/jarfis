"""Tests for Stage 2 — IA SSOT context inject (D7 L1 defense layer).

agent-composition.yaml 의 10개 IA-relevant agent context 에 work IA SSOT
파일이 inject 되는지 검증한다:

- 모든 10개 agent 가 `discovery/ia/manifest.json` 을 context 에 가진다
- PO + tech-lead-strategist 만 `discovery/ia/.baseline/manifest.json` 도 가진다
  (D4 author 책임 — Phase 6 merge 시 baseline 비교 필요)
- 모든 IA inject 항목은 `optional: true` + `importance: recommended`
  (D10 forward-only 정책; Stage 3 에서 phase-level gate 가 enforcement 담당)
- 파일 미존재 시 silent skip (block_meta.injected=False, reason=file_not_found)
- 파일 존재 시 inject 성공 (block_meta.injected=True)

본 파일은 IA inject 전용 검증을 담당하며, N-3 missing_sections 경고는
test_compose_warnings.py 에 분리되어 있다.
"""

from __future__ import annotations

import json
import os

import pytest
import yaml


COMPOSITION_YAML = os.path.expanduser(
    "~/.claude/commands/jarfis/agent-composition.yaml"
)

IA_RELEVANT_AGENTS = [
    "product-owner",
    "technical-architect",
    "tech-lead-reviewer",
    "tech-lead-strategist",
    "qa-engineer",
    "security-engineer",
    "ux-designer",
    "devops-engineer",
    "frontend-developer",
    "backend-developer",
]

BASELINE_RECEIVERS = ["product-owner", "tech-lead-strategist"]

MANIFEST_PATH = "discovery/ia/manifest.json"
BASELINE_PATH = "discovery/ia/.baseline/manifest.json"


def _load_composition():
    with open(COMPOSITION_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── YAML structure level ─────────────────────────────────────────────


class TestYamlIAInjectStructure:
    """agent-composition.yaml 의 IA inject 정의 정합성."""

    def test_all_ia_relevant_agents_have_manifest(self):
        comp = _load_composition()
        agents = comp["agents"]
        for name in IA_RELEVANT_AGENTS:
            assert name in agents, f"missing agent: {name}"
            ctx = agents[name].get("context", [])
            paths = [c["path"] for c in ctx]
            assert MANIFEST_PATH in paths, (
                f"{name}: 누락된 IA inject `{MANIFEST_PATH}` (Stage 2 D7 L1)"
            )

    def test_only_po_and_strategist_have_baseline(self):
        comp = _load_composition()
        agents = comp["agents"]
        for name in IA_RELEVANT_AGENTS:
            ctx = agents[name].get("context", [])
            paths = [c["path"] for c in ctx]
            if name in BASELINE_RECEIVERS:
                assert BASELINE_PATH in paths, (
                    f"{name}: 누락된 baseline `{BASELINE_PATH}` (D4 author)"
                )
            else:
                assert BASELINE_PATH not in paths, (
                    f"{name}: baseline 은 PO + strategist 만 받음"
                )

    def test_manifest_entries_are_optional_recommended(self):
        comp = _load_composition()
        agents = comp["agents"]
        for name in IA_RELEVANT_AGENTS:
            ctx = agents[name].get("context", [])
            for entry in ctx:
                if entry["path"] in (MANIFEST_PATH, BASELINE_PATH):
                    assert entry.get("optional") is True, (
                        f"{name}/{entry['path']}: optional 이어야 함 (D10 forward-only)"
                    )
                    assert entry.get("importance") == "recommended", (
                        f"{name}/{entry['path']}: importance=recommended"
                    )

    def test_manifest_entries_use_docs_base(self):
        comp = _load_composition()
        agents = comp["agents"]
        for name in IA_RELEVANT_AGENTS:
            ctx = agents[name].get("context", [])
            for entry in ctx:
                if entry["path"] in (MANIFEST_PATH, BASELINE_PATH):
                    assert entry["base"] == "docs", (
                        f"{name}/{entry['path']}: base=docs (state.work.docsDir 기준)"
                    )


# ── compose --dry-run integration level ──────────────────────────────


def _write_synth_state(tmp_path, docs_dir):
    """work-wide agent (PO 등) 가 동작하는 최소 state.json 합성."""
    state = {
        "locale": "ko",
        "work": {"docsDir": str(docs_dir)},
        "workspace": {
            "scope": [
                {
                    "name": "synth",
                    "path": str(tmp_path),
                    "type": "web",
                    "domain": "web",
                    "framework": "react",
                }
            ]
        },
        "org": None,
    }
    state_path = tmp_path / ".jarfis-state.json"
    state_path.write_text(json.dumps(state, indent=2))
    return state_path


def _run_compose_json(agent, state_path):
    """compose --dry-run --format json 실행 후 SystemExit 흡수."""
    from jarfis.compose.__main__ import main
    with pytest.raises(SystemExit):
        main([
            "--dry-run",
            "--agent", agent,
            "--state", str(state_path),
            "--format", "json",
        ])


def _ctx_entry(payload, path):
    for c in payload["meta"]["context_files"]:
        if c["path"] == path:
            return c
    return None


class TestComposeIAInjectWiring:
    """compose --dry-run 통합 — IA inject 가 meta.context_files[] 에 등장."""

    def test_manifest_present_records_injected_true(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        ia_dir = docs / "discovery" / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text(
            '{"slug": "synth", "version": 1, "pages": []}'
        )
        state_path = _write_synth_state(tmp_path, docs)
        _run_compose_json("product-owner", state_path)
        payload = json.loads(capsys.readouterr().out)
        manifest = _ctx_entry(payload, MANIFEST_PATH)
        assert manifest is not None, "manifest.json 이 context_files 에 없음"
        assert manifest["injected"] is True
        assert manifest["importance"] == "recommended"

    def test_manifest_missing_optional_silent_skip(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        docs.mkdir()
        # NO discovery/ia/manifest.json — silent skip 시나리오
        state_path = _write_synth_state(tmp_path, docs)
        _run_compose_json("product-owner", state_path)
        payload = json.loads(capsys.readouterr().out)
        manifest = _ctx_entry(payload, MANIFEST_PATH)
        assert manifest is not None
        assert manifest["injected"] is False
        assert manifest["reason"] == "file_not_found"

    def test_baseline_inject_for_po(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        baseline_dir = docs / "discovery" / "ia" / ".baseline"
        baseline_dir.mkdir(parents=True)
        (docs / "discovery" / "ia" / "manifest.json").write_text('{"v": 2}')
        (baseline_dir / "manifest.json").write_text('{"v": 1}')
        state_path = _write_synth_state(tmp_path, docs)
        _run_compose_json("product-owner", state_path)
        payload = json.loads(capsys.readouterr().out)
        baseline = _ctx_entry(payload, BASELINE_PATH)
        assert baseline is not None, "PO 는 baseline 도 inject 받아야 함"
        assert baseline["injected"] is True

    def test_baseline_inject_for_strategist(self, tmp_path, capsys):
        docs = tmp_path / "docs"
        baseline_dir = docs / "discovery" / "ia" / ".baseline"
        baseline_dir.mkdir(parents=True)
        (docs / "discovery" / "ia" / "manifest.json").write_text('{"v": 2}')
        (baseline_dir / "manifest.json").write_text('{"v": 1}')
        state_path = _write_synth_state(tmp_path, docs)
        _run_compose_json("tech-lead-strategist", state_path)
        payload = json.loads(capsys.readouterr().out)
        baseline = _ctx_entry(payload, BASELINE_PATH)
        assert baseline is not None, (
            "tech-lead-strategist 도 baseline inject (critic #1 fix)"
        )
        assert baseline["injected"] is True

    # ── Stage 6a — Org IA inject (F3a: strategist, NOT PO) ──────────────

    def test_strategist_receives_org_ia_inject_with_substituted_slug(
        self, tmp_path, capsys
    ):
        """tech-lead-strategist gets `PO/projects/{slug}/ia/manifest.json` inject
        with `{project_slug}` substituted to scope[0].name (Stage 6a F3a)."""
        # Set up org_root + wiki/PO/projects/{slug}/ia/manifest.json
        org_root = tmp_path / "org"
        slug = "synth"
        ia_dir = org_root / ".jarfis-org" / "wiki" / "PO" / "projects" / slug / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text(
            '{"slug": "synth", "version": 1, "pages": []}'
        )

        docs = tmp_path / "docs"
        docs.mkdir()
        # Compose synth state — single scope so default --project-slug = scope[0].name.
        state = {
            "locale": "ko",
            "work": {"docsDir": str(docs)},
            "workspace": {
                "scope": [
                    {
                        "name": slug,
                        "path": str(tmp_path),
                        "type": "web",
                        "domain": "web",
                        "framework": "react",
                    }
                ]
            },
            "org": {"root": str(org_root)},
        }
        state_path = tmp_path / ".jarfis-state.json"
        state_path.write_text(json.dumps(state, indent=2))

        _run_compose_json("tech-lead-strategist", state_path)
        payload = json.loads(capsys.readouterr().out)

        # The rendered context_files[] entry should still carry the *literal*
        # `{project_slug}` placeholder in `path` (the yaml is verbatim).
        # The substitution happens behind the scenes in resolver before
        # filesystem read. So we assert injected=True (file was found because
        # substitution worked).
        org_ia_path = "PO/projects/{project_slug}/ia/manifest.json"
        entry = _ctx_entry(payload, org_ia_path)
        assert entry is not None, (
            "tech-lead-strategist must declare Org IA inject in its context block "
            f"(path={org_ia_path})"
        )
        assert entry["injected"] is True, (
            f"Org IA inject should resolve to disk after slug substitution; "
            f"entry={entry}"
        )

    def test_po_does_NOT_receive_org_ia_inject(self, tmp_path, capsys):
        """F3a: PO unchanged — Org IA reference goes to strategist, NOT PO.

        PO keeps its work-IA + work-IA-baseline injects (Stage 2). It must
        NOT additionally receive `PO/projects/{slug}/ia/...` (Stage 6a).
        """
        org_root = tmp_path / "org"
        slug = "synth"
        ia_dir = org_root / ".jarfis-org" / "wiki" / "PO" / "projects" / slug / "ia"
        ia_dir.mkdir(parents=True)
        (ia_dir / "manifest.json").write_text("{}")

        docs = tmp_path / "docs"
        docs.mkdir()
        state = {
            "locale": "ko",
            "work": {"docsDir": str(docs)},
            "workspace": {
                "scope": [
                    {
                        "name": slug,
                        "path": str(tmp_path),
                        "type": "web",
                        "domain": "web",
                        "framework": "react",
                    }
                ]
            },
            "org": {"root": str(org_root)},
        }
        state_path = tmp_path / ".jarfis-state.json"
        state_path.write_text(json.dumps(state, indent=2))

        _run_compose_json("product-owner", state_path)
        payload = json.loads(capsys.readouterr().out)
        paths = [c["path"] for c in payload["meta"]["context_files"]]
        assert "PO/projects/{project_slug}/ia/manifest.json" not in paths, (
            "PO must NOT receive Org IA inject (F3a — strategist is the merge author)"
        )

    def test_baseline_absent_in_non_author_agent(self, tmp_path, capsys):
        """ux-designer 같은 non-author 에는 baseline entry 자체가 없어야 함."""
        docs = tmp_path / "docs"
        baseline_dir = docs / "discovery" / "ia" / ".baseline"
        baseline_dir.mkdir(parents=True)
        (docs / "discovery" / "ia" / "manifest.json").write_text('{}')
        (baseline_dir / "manifest.json").write_text('{}')
        state_path = _write_synth_state(tmp_path, docs)
        _run_compose_json("ux-designer", state_path)
        payload = json.loads(capsys.readouterr().out)
        paths = [c["path"] for c in payload["meta"]["context_files"]]
        assert BASELINE_PATH not in paths, (
            "ux-designer 는 baseline 받지 않아야 함"
        )
        assert MANIFEST_PATH in paths, "ux-designer 는 work IA 는 받아야 함"
