"""Tests for jarfis.agent_admin — Skill+persona registry CRUD module.

Coverage targets (per agent-skill-system-v1 Step 2 spec):
  1. skill_list_empty
  2. skill_list_populated
  3. skill_add_dry_run
  4. skill_add_apply
  5. skill_add_invalid_name
  6. skill_add_duplicate
  7. skill_add_with_framework
  8. skill_remove_dry_run
  9. skill_remove_apply
  10. persona_list

Each test uses tmp_path-backed isolation by overriding env vars
JARFIS_SKILLS_DIR / JARFIS_TEMPLATE_PATH / JARFIS_COMPOSITION_PATH /
JARFIS_DOMAINS_DIR — agent_admin respects these for testability.
"""

import json
import os

import pytest

from jarfis import agent_admin


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def isolated_skills(tmp_path, monkeypatch):
    """Set up isolated skills/template/composition env."""
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()
    composition_path = tmp_path / "agent-composition.yaml"

    # Minimal skill template (matches templates/skill-template.md structure).
    template_path = templates_dir / "skill-template.md"
    template_path.write_text(
        """# Skill Template — Checkpoint Style

> **Skill 파일 작성 가이드.**

## 권장 5섹션 구조

~~~markdown
# {기술명} Expertise

> {1줄 요약: 어떤 작업에 쓰이는 skill인가}

## Common Pitfalls
- 함정 1 (왜 + 어떻게 회피)
- 함정 2

## Decision Heuristics
- 휴리스틱 1 (when X → do Y)
- 휴리스틱 2

## Anti-patterns
- 반패턴 1 (X 하지 마, Y 하라)
- 반패턴 2

## Version & Environment Notes
- 버전 의존성, 호환성 주의

## Related Skills
- 같이 쓰면 좋은 skill 또는 충돌 skill (선택)
~~~

## 파일 위치 + 명명
"""
    )

    # Minimal agent-composition.yaml (read-only — never written by module).
    composition_path.write_text(
        """agents:
  product-owner:
    persona: product-owner
    scope: work-wide
    skills_from_domain: false
    context:
      - {base: docs, path: .wiki-cache.md, optional: true, importance: recommended}

  technical-architect:
    persona: technical-architect
    scope: work-wide
    skills_from_domain: false
    context:
      - {base: all-projects, path: .jarfis-project/project-profile.md}

  tech-lead-reviewer:
    persona: tech-lead
    scope: per-project
    model: sonnet
    skills_from_domain: true
    context:
      - {base: project, path: .jarfis-project/project-rule.md, optional: true}
      - {base: project, path: .jarfis-project/project-profile.md}
      - {base: docs, path: .wiki-cache.md, optional: true}

  tech-lead-strategist:
    persona: tech-lead
    scope: work-wide
    skills_from_domain: true
    context:
      - {base: all-projects, path: .jarfis-project/project-profile.md, optional: true}
      - {base: docs, path: .wiki-cache.md, optional: true}

  qa-engineer:
    persona: qa-engineer
    scope: per-project
    skills_from_domain: true
    context:
      - {base: project, path: .jarfis-project/project-rule.md, optional: true}
      - {base: project, path: .jarfis-project/project-profile.md}
      - {base: docs, path: .wiki-cache.md, optional: true}

  security-engineer:
    persona: security-engineer
    scope: work-wide
    skills_from_domain: true
    context:
      - {base: all-projects, path: .jarfis-project/project-profile.md, optional: true}
      - {base: docs, path: .wiki-cache.md, optional: true}

  ux-designer:
    persona: ux-designer
    scope: work-wide
    skills_from_domain: false
    context:
      - {base: org_wiki, path: DESIGN/, optional: true}

  devops-engineer:
    persona: devops-engineer
    model: opus
    scope: work-wide
    skills_from_domain: true
    context:
      - {base: all-projects, path: .jarfis-project/project-profile.md}
      - {base: docs, path: .wiki-cache.md, optional: true}

  frontend-developer:
    persona: frontend-developer
    scope: per-project
    skills_from_domain: true
    context:
      - {base: project, path: .jarfis-project/project-rule.md, optional: true}
      - {base: project, path: .jarfis-project/project-context.md, optional: true}
      - {base: project, path: .jarfis-project/project-profile.md}

  backend-developer:
    persona: backend-developer
    scope: per-project
    skills_from_domain: true
    context:
      - {base: project, path: .jarfis-project/project-rule.md, optional: true}
      - {base: project, path: .jarfis-project/project-context.md, optional: true}
      - {base: project, path: .jarfis-project/project-profile.md}

extra_skills_by_framework:
  vue: [vue]
  react: [react, browser]
  nextjs: [react, browser]
"""
    )

    monkeypatch.setenv("JARFIS_SKILLS_DIR", str(skills_dir))
    monkeypatch.setenv("JARFIS_TEMPLATE_PATH", str(template_path))
    monkeypatch.setenv("JARFIS_COMPOSITION_PATH", str(composition_path))
    monkeypatch.setenv("JARFIS_DOMAINS_DIR", str(domains_dir))

    return {
        "skills_dir": skills_dir,
        "templates_dir": templates_dir,
        "template_path": template_path,
        "composition_path": composition_path,
        "domains_dir": domains_dir,
    }


# ─────────────────────────────────────────────────────────────────────
# skill list
# ─────────────────────────────────────────────────────────────────────


class TestSkillList:
    def test_skill_list_empty(self, isolated_skills, capsys):
        agent_admin.main(["skill", "list"])
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0
        assert out["skills"] == []

    def test_skill_list_populated(self, isolated_skills, capsys):
        skills_dir = isolated_skills["skills_dir"]
        (skills_dir / "react.md").write_text(
            "# React Expertise\n\n> SPA framework — hooks, JSX, virtual DOM\n\n## Common Pitfalls\n- foo\n"
        )
        (skills_dir / "nodejs.md").write_text(
            "# Node.js Backend Expertise\n\n> Server JS — event loop\n"
        )
        agent_admin.main(["skill", "list"])
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        names = sorted(s["name"] for s in out["skills"])
        assert names == ["nodejs", "react"]
        # Title + description extracted.
        react = next(s for s in out["skills"] if s["name"] == "react")
        assert "React" in react["title"]
        assert "SPA" in react["description"]


# ─────────────────────────────────────────────────────────────────────
# skill add
# ─────────────────────────────────────────────────────────────────────


class TestSkillAdd:
    def test_skill_add_dry_run(self, isolated_skills, capsys):
        agent_admin.main(["skill", "add", "graphql"])
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "dry_run"
        # File NOT written.
        assert not (isolated_skills["skills_dir"] / "graphql.md").exists()

    def test_skill_add_apply(self, isolated_skills, capsys):
        agent_admin.main(["skill", "add", "graphql", "--apply"])
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "created"
        path = isolated_skills["skills_dir"] / "graphql.md"
        assert path.exists()
        body = path.read_text()
        # Title Case heading derived from kebab-case.
        assert "# Graphql Expertise" in body
        # 5 sections present.
        for section in [
            "## Common Pitfalls",
            "## Decision Heuristics",
            "## Anti-patterns",
            "## Version & Environment Notes",
            "## Related Skills",
        ]:
            assert section in body
        # TODO placeholders.
        assert "TODO" in body

    def test_skill_add_apply_kebab_title_case(self, isolated_skills, capsys):
        agent_admin.main(["skill", "add", "aws-lambda", "--apply"])
        capsys.readouterr()
        body = (isolated_skills["skills_dir"] / "aws-lambda.md").read_text()
        # kebab-case → "Aws Lambda" in the heading.
        assert "# Aws Lambda Expertise" in body

    def test_skill_add_invalid_name(self, isolated_skills, capsys):
        with pytest.raises(SystemExit) as excinfo:
            agent_admin.main(["skill", "add", "Foo", "--apply"])
        assert excinfo.value.code != 0
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_skill_add_invalid_name_too_long(self, isolated_skills, capsys):
        long_name = "a" * 41
        with pytest.raises(SystemExit):
            agent_admin.main(["skill", "add", long_name, "--apply"])
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_skill_add_duplicate(self, isolated_skills, capsys):
        (isolated_skills["skills_dir"] / "react.md").write_text("# React Expertise\n")
        with pytest.raises(SystemExit) as excinfo:
            agent_admin.main(["skill", "add", "react", "--apply"])
        assert excinfo.value.code != 0
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_skill_add_with_framework(self, isolated_skills, capsys):
        agent_admin.main(
            ["skill", "add", "graphql", "--bind-framework", "react", "--apply"]
        )
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "created"
        binding = out.get("framework_binding")
        assert binding is not None
        assert binding["manual_action_required"] is True
        assert "graphql" in binding["composition_yaml_diff"]
        assert "react" in binding["composition_yaml_diff"]
        # Composition file MUST NOT have been modified.
        comp_after = isolated_skills["composition_path"].read_text()
        assert "graphql" not in comp_after

    def test_skill_add_with_library(self, isolated_skills, capsys):
        agent_admin.main(
            ["skill", "add", "graphql", "--library", "ctx7-id/123", "--apply"]
        )
        capsys.readouterr()
        body = (isolated_skills["skills_dir"] / "graphql.md").read_text()
        # Comment hint included.
        assert "Context7 ID" in body
        assert "ctx7-id/123" in body


# ─────────────────────────────────────────────────────────────────────
# skill update
# ─────────────────────────────────────────────────────────────────────


class TestSkillUpdate:
    def test_skill_update_locates_file(self, isolated_skills, capsys):
        path = isolated_skills["skills_dir"] / "react.md"
        path.write_text("# React Expertise\n")
        agent_admin.main(["skill", "update", "react"])
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "located"
        assert out["path"].endswith("react.md")
        assert out["size_bytes"] > 0
        assert "instruction" in out

    def test_skill_update_missing(self, isolated_skills, capsys):
        with pytest.raises(SystemExit):
            agent_admin.main(["skill", "update", "nonexistent"])
        err = json.loads(capsys.readouterr().err)
        assert "error" in err


# ─────────────────────────────────────────────────────────────────────
# skill remove
# ─────────────────────────────────────────────────────────────────────


class TestSkillRemove:
    def test_skill_remove_dry_run(self, isolated_skills, capsys):
        skills_dir = isolated_skills["skills_dir"]
        (skills_dir / "vue.md").write_text("# Vue Expertise\n")
        agent_admin.main(["skill", "remove", "vue"])
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "dry_run"
        # File still exists.
        assert (skills_dir / "vue.md").exists()
        # References surfaced.
        refs = out["references"]
        assert any("agent-composition.yaml" in r["file"] for r in refs)

    def test_skill_remove_apply(self, isolated_skills, capsys):
        skills_dir = isolated_skills["skills_dir"]
        (skills_dir / "vue.md").write_text("# Vue Expertise\n")
        agent_admin.main(["skill", "remove", "vue", "--apply"])
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "removed"
        assert not (skills_dir / "vue.md").exists()
        # Manual cleanup list surfaced.
        cleanup = out.get("manual_cleanup_required", [])
        assert any("agent-composition.yaml" in r["file"] for r in cleanup)
        # Composition.yaml NOT auto-edited.
        comp_after = isolated_skills["composition_path"].read_text()
        assert "vue: [vue]" in comp_after

    def test_skill_remove_missing(self, isolated_skills, capsys):
        with pytest.raises(SystemExit):
            agent_admin.main(["skill", "remove", "nonexistent"])
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_skill_remove_with_domain_refs(self, isolated_skills, capsys):
        skills_dir = isolated_skills["skills_dir"]
        domains_dir = isolated_skills["domains_dir"]
        (skills_dir / "vue.md").write_text("# Vue Expertise\n")
        (domains_dir / "frontend.yaml").write_text(
            "skills:\n  - vue\n  - react\n"
        )
        agent_admin.main(["skill", "remove", "vue"])
        out = json.loads(capsys.readouterr().out)
        refs = out["references"]
        # Both composition + domain refs surfaced.
        files = {r["file"] for r in refs}
        assert any("frontend.yaml" in f for f in files)


# ─────────────────────────────────────────────────────────────────────
# persona list
# ─────────────────────────────────────────────────────────────────────


class TestPersonaList:
    def test_persona_list(self, isolated_skills, capsys):
        agent_admin.main(["persona", "list"])
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 10
        agents = {a["name"]: a for a in out["agents"]}
        assert "tech-lead-reviewer" in agents
        tlr = agents["tech-lead-reviewer"]
        assert tlr["persona"] == "tech-lead"
        assert tlr["scope"] == "per-project"
        assert tlr["skills_from_domain"] is True
        assert tlr["context_count"] == 3
        assert tlr["model"] == "sonnet"
        # devops-engineer has model: opus override.
        assert agents["devops-engineer"]["model"] == "opus"
        # product-owner has skills_from_domain: false.
        assert agents["product-owner"]["skills_from_domain"] is False

    def test_persona_list_default_model_sonnet(self, isolated_skills, capsys):
        agent_admin.main(["persona", "list"])
        out = json.loads(capsys.readouterr().out)
        agents = {a["name"]: a for a in out["agents"]}
        # No model field → defaults to "sonnet".
        assert agents["product-owner"]["model"] == "sonnet"


# ─────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────


class TestDispatcher:
    def test_no_args(self, isolated_skills, capsys):
        with pytest.raises(SystemExit):
            agent_admin.main([])
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_unknown_subcommand(self, isolated_skills, capsys):
        with pytest.raises(SystemExit):
            agent_admin.main(["bogus"])
        err = json.loads(capsys.readouterr().err)
        assert "error" in err

    def test_skill_unknown_action(self, isolated_skills, capsys):
        with pytest.raises(SystemExit):
            agent_admin.main(["skill", "bogus"])
        err = json.loads(capsys.readouterr().err)
        assert "error" in err
