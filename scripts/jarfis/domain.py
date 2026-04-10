"""JARFIS Domain — Domain Pack registry, composition, and management.

Usage: jarfis domain <subcommand> [args...]

Subcommands:
    list                         List installed domain packs
    detect <project_dir>         Auto-detect project domain
    agents <domain> <phase>      Get agents for a phase
    compose <domain> <role> <task> [learnings] [context]
                                 Compose Persona + Skills + Rules
    validate <domain>            Validate domain pack integrity
    scaffold <domain>            Generate skeleton domain pack
    install                      Install domain packs to ~/.claude/
"""

import json
import os
import re
import sys

import yaml

from .utils import get_claude_dir, json_output

# ── Constants ──

DOMAINS_DIR_NAME = "domains"
SKILLS_DIR_NAME = "skills"
HOOKS_DIR_NAME = "hooks"

# Validation patterns
DOMAIN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# Max file size for skill files (256 KB)
MAX_SKILL_FILE_SIZE = 256 * 1024


# ── Path Resolution ──

def _get_domains_dir():
    """Return the domains directory path (~/.claude/commands/jarfis/domains/)."""
    return os.path.join(get_claude_dir(), "commands", "jarfis", DOMAINS_DIR_NAME)


def _resolve_skill_path(domain_name, skill_name, domains_dir=None):
    """Resolve a skill file path with security validation.

    W1-11: Validates against path traversal.
    S4/S5: Validates name patterns.

    Returns:
        Absolute path to the skill .md file.

    Raises:
        ValueError: If domain or skill name is invalid.
        SecurityError: If resolved path is outside domains directory.
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    if not DOMAIN_NAME_RE.match(domain_name):
        raise ValueError(f"Invalid domain name: {domain_name}")
    if not SKILL_NAME_RE.match(skill_name):
        raise ValueError(f"Invalid skill name: {skill_name}")

    base = os.path.realpath(domains_dir)
    resolved = os.path.realpath(
        os.path.join(domains_dir, domain_name, SKILLS_DIR_NAME, f"{skill_name}.md")
    )

    if not resolved.startswith(base):
        raise ValueError(f"Path traversal detected: {skill_name}")

    return resolved


def _load_domain_yaml(domain_name, domains_dir=None):
    """Load and parse a domain.yaml file.

    Args:
        domain_name: Domain identifier (e.g., "web", "desktop").
        domains_dir: Override domains directory for testing.

    Returns:
        Parsed YAML as dict.

    Raises:
        FileNotFoundError: If domain.yaml does not exist.
        yaml.YAMLError: If YAML is malformed.
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    yaml_path = os.path.join(domains_dir, f"{domain_name}.yaml")
    if not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"Domain pack not found: {yaml_path}")

    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or not isinstance(data, dict):
        raise ValueError(f"Empty or invalid domain.yaml: {yaml_path}")

    return data


def _find_role(config, role_name):
    """Find a role by name in domain config's implement section."""
    for role in config.get("roles", {}).get("implement", []):
        if role.get("name") == role_name:
            return role
    raise KeyError(f"Role not found: {role_name}")


# ── Token Estimation ──

def estimate_tokens(text):
    """Estimate token count for text.

    W1-2: CJK characters have higher token density (~2 char/token)
    vs ASCII (~4 char/token). Adjusts dynamically based on CJK ratio.

    Accuracy: ±20% for ASCII, ±30% for mixed content.
    Budget (2500) is set conservatively to absorb this variance.
    """
    if not text:
        return 0

    cjk_count = sum(
        1 for c in text
        if ('\u4e00' <= c <= '\u9fff')       # CJK Unified
        or ('\uac00' <= c <= '\ud7af')       # Korean Hangul
        or ('\u3040' <= c <= '\u30ff')       # Japanese
    )
    cjk_ratio = cjk_count / len(text)
    chars_per_token = 4 - (2 * cjk_ratio)  # 4 (ASCII) ~ 2 (CJK)
    return max(1, int(len(text) / chars_per_token))


# ── Core Functions ──

def list_domains(domains_dir=None):
    """List all installed domain packs.

    Returns:
        List of dicts with name, display_name, schema_version.
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    result = []
    if not os.path.isdir(domains_dir):
        return result

    for fname in sorted(os.listdir(domains_dir)):
        if fname.startswith("_") or not fname.endswith(".yaml"):
            continue
        try:
            config = _load_domain_yaml(fname[:-5], domains_dir)
            domain_info = config.get("domain", {})
            result.append({
                "name": domain_info.get("name", fname[:-5]),
                "display_name": domain_info.get("display_name", ""),
                "schema_version": config.get("schema_version", 1),
            })
        except Exception:
            continue

    return result


def detect(project_dir, domains_dir=None):
    """Auto-detect project domain by scanning indicators.

    Wraps existing detect.py for framework detection, then matches
    against domain pack indicators for domain classification.

    W1-5: Results sorted by (-confidence, name) for deterministic output.
    S2: Returns tie flag when top-2 confidences are equal.

    Returns:
        Dict with 'matches' (list) and 'tie' (bool).
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    if not os.path.isdir(project_dir):
        return {"matches": [], "tie": False}

    matches = []

    for domain_info in list_domains(domains_dir):
        domain_name = domain_info["name"]
        try:
            config = _load_domain_yaml(domain_name, domains_dir)
        except Exception:
            continue

        indicators = config.get("detect", {}).get("indicators", [])
        total_score = 0.0
        matched_count = 0

        for indicator in indicators:
            score = _evaluate_indicator(indicator, project_dir)
            if score > 0:
                total_score += score
                matched_count += 1

        if matched_count > 0:
            avg_confidence = total_score / matched_count
            matches.append({
                "domain": domain_name,
                "confidence": round(avg_confidence, 3),
                "matched_indicators": matched_count,
            })

    # W1-5: Deterministic sort — confidence desc, then name asc
    matches.sort(key=lambda m: (-m["confidence"], m["domain"]))

    # S2: Detect tie between top-2
    tie = (len(matches) >= 2
           and matches[0]["confidence"] == matches[1]["confidence"])

    return {"matches": matches, "tie": tie}


def _evaluate_indicator(indicator, project_dir):
    """Evaluate a single detection indicator against a project.

    Returns:
        confidence score (0.0 if not matched).
    """
    confidence = indicator.get("confidence", 0.5)

    # File existence check
    file_path = indicator.get("file")
    if file_path:
        full_path = os.path.join(project_dir, file_path)
        if not os.path.exists(full_path):
            return 0.0

        # Optional key check within the file
        key = indicator.get("key")
        if key:
            try:
                with open(full_path, encoding="utf-8") as f:
                    content = f.read()
                if key not in content:
                    return 0.0
            except Exception:
                return 0.0

        return confidence

    # Manifest + key check
    manifest = indicator.get("manifest")
    if manifest:
        manifest_path = os.path.join(project_dir, manifest)
        if not os.path.isfile(manifest_path):
            return 0.0
        key = indicator.get("key")
        if key:
            try:
                with open(manifest_path, encoding="utf-8") as f:
                    if key not in f.read():
                        return 0.0
            except Exception:
                return 0.0
        return confidence

    return 0.0


def agents(domain_name, phase, domains_dir=None):
    """Get agent definitions for a specific phase.

    Args:
        domain_name: Domain identifier.
        phase: Phase name (plan, design, implement, review).

    Returns:
        List of role dicts.
    """
    config = _load_domain_yaml(domain_name, domains_dir)
    roles = config.get("roles", {}).get(phase, [])
    return roles


def compose(domain_name, role_name, task,
            learnings_path=None, project_context_path=None,
            domains_dir=None):
    """Compose Persona + Skills + Rules into an agent prompt.

    F1/F2: Graceful degradation on errors.
    R4: Token budget enforcement with first-skill guarantee (W1-1).
    R3: Tag-based rule filtering.
    W1-2: CJK-aware token estimation.
    W1-3/S1: Null/missing/string skills handling.

    Returns:
        Dict with agent_type, prompt_content, token_count,
        loaded_skills, truncated_skills, fallback.
    """
    try:
        config = _load_domain_yaml(domain_name, domains_dir)
        role = _find_role(config, role_name)
    except (FileNotFoundError, yaml.YAMLError, KeyError, ValueError) as e:
        # Fallback: persona-only execution
        error_msg = f"{type(e).__name__}: domain config load failed"
        return {
            "agent_type": role_name.split("_")[0] + "-developer",
            "prompt_content": f"## Task\n{task}",
            "token_count": estimate_tokens(task),
            "loaded_skills": [],
            "truncated_skills": [],
            "fallback": True,
            "error": error_msg,
        }

    # 1. Skills loading with token budget
    skills_content = ""
    loaded_skills = []
    truncated_skills = []
    token_budget = config.get("max_skill_tokens", 2500)
    token_used = 0

    # W1-3/S1: Null/missing/string handling
    skill_list = role.get("skills", []) or []
    if isinstance(skill_list, str):
        skill_list = [skill_list]

    for i, skill_name in enumerate(skill_list):
        try:
            skill_path = _resolve_skill_path(domain_name, skill_name, domains_dir)

            # Check file size (DoS prevention)
            if os.path.isfile(skill_path):
                size = os.path.getsize(skill_path)
                if size > MAX_SKILL_FILE_SIZE:
                    truncated_skills.append({
                        "name": skill_name,
                        "reason": "file_too_large",
                    })
                    continue

            with open(skill_path, encoding="utf-8") as f:
                skill_text = f.read()
        except (FileNotFoundError, ValueError) as e:
            truncated_skills.append({
                "name": skill_name,
                "reason": "file_not_found",
            })
            continue

        skill_tokens = estimate_tokens(skill_text)

        if token_used + skill_tokens > token_budget:
            # W1-1: First skill is ALWAYS loaded (minimum 1 skill guarantee)
            if i == 0 and not loaded_skills:
                pass  # Load first skill even if over budget
            else:
                truncated_skills.append({
                    "name": skill_name,
                    "reason": "token_budget_exceeded",
                })
                continue

        skills_content += f"\n{skill_text}\n"
        loaded_skills.append(skill_name)
        token_used += skill_tokens

    # 2. External skills (optional, same budget)
    for ext_skill in (role.get("external_skills") or []):
        try:
            parts = ext_skill.split("/")
            if len(parts) != 2:
                raise ValueError(f"Invalid external_skills format: {ext_skill}")
            ext_domain, ext_skill_name = parts

            ext_path = _resolve_skill_path(ext_domain, ext_skill_name, domains_dir)
            with open(ext_path, encoding="utf-8") as f:
                ext_text = f.read()

            ext_tokens = estimate_tokens(ext_text)
            if token_used + ext_tokens <= token_budget:
                skills_content += f"\n{ext_text}\n"
                loaded_skills.append(ext_skill)
                token_used += ext_tokens
            else:
                truncated_skills.append({
                    "name": ext_skill,
                    "reason": "token_budget_exceeded",
                })
        except (FileNotFoundError, ValueError):
            truncated_skills.append({
                "name": ext_skill,
                "reason": "external_not_found",
            })

    # 3. Rules loading (tag filtering)
    rules_content = ""
    if learnings_path or project_context_path:
        rules_content = load_filtered_rules(
            learnings_path, project_context_path,
            domain=domain_name,
            framework_tags=_extract_framework_tags(skill_list),
            always_include_untagged=config.get("rules", {}).get(
                "always_include_untagged", True
            ),
        )

    # 4. Compose prompt
    sections = []
    if skills_content.strip():
        sections.append(f"## Active Skills\n{skills_content}")
    if rules_content.strip():
        sections.append(f"## Team Rules\n{rules_content}")
    sections.append(f"## Task\n{task}")

    prompt = "\n\n".join(sections)

    return {
        "agent_type": role.get("persona", ""),
        "prompt_content": prompt,
        "token_count": estimate_tokens(prompt),
        "loaded_skills": loaded_skills,
        "truncated_skills": truncated_skills,
        "fallback": False,
    }


def _extract_framework_tags(skills):
    """Extract framework tags from skill names for rule filtering."""
    # Skill names themselves serve as tags
    return [s for s in skills if isinstance(s, str)]


def load_filtered_rules(learnings_path, project_context_path,
                        domain="", framework_tags=None,
                        always_include_untagged=True):
    """Load and filter rules from learnings.md and project-context.md.

    R3: Tag-based filtering to prevent attention dilution.
    F9: Handles missing sections gracefully (empty list).

    Rule sections in learnings.md:
    - ## Universal → always loaded
    - ## {domain} → loaded when domain matches
    - ## Agent Hints → legacy format, loaded as-is

    Returns:
        Formatted rules string.
    """
    rules_lines = []

    # 1. learnings.md
    if learnings_path and os.path.isfile(learnings_path):
        content = _read_file_safe(learnings_path)
        if content:
            # Parse ## Universal section
            universal = _extract_section(content, "Universal")
            if universal:
                rules_lines.append("### Universal Rules")
                rules_lines.append(universal)

            # Parse ## {domain} section
            if domain:
                domain_section = _extract_section(content, domain)
                if domain_section:
                    rules_lines.append(f"### {domain} Rules")
                    rules_lines.append(domain_section)

            # Legacy: ## Agent Hints (v2.5 compat)
            agent_hints = _extract_section(content, "Agent Hints")
            if agent_hints:
                rules_lines.append("### Agent Hints (legacy)")
                rules_lines.append(agent_hints)

    # 2. project-context.md (always loaded — project-level overrides)
    if project_context_path and os.path.isfile(project_context_path):
        context_content = _read_file_safe(project_context_path)
        if context_content:
            rules_lines.append("### Project Rules")
            rules_lines.append(context_content)

    return "\n\n".join(rules_lines)


def _extract_section(content, heading):
    """Extract content under a ## heading until the next ## heading."""
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _read_file_safe(path):
    """Read a file with size limit."""
    try:
        size = os.path.getsize(path)
        if size > MAX_SKILL_FILE_SIZE * 4:  # 1MB limit for rule files
            return ""
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def validate(domain_name, domains_dir=None):
    """Validate a domain pack's integrity.

    Checks:
    - YAML syntax and schema conformance
    - Referenced persona files exist
    - Referenced skill files exist (warning if missing — Phase B)
    - Test runner command format

    Returns:
        Dict with valid (bool), errors (list), warnings (list).
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    errors = []
    warnings = []

    # 1. Load YAML
    try:
        config = _load_domain_yaml(domain_name, domains_dir)
    except FileNotFoundError as e:
        return {"valid": False, "errors": [str(e)], "warnings": []}
    except yaml.YAMLError as e:
        return {"valid": False, "errors": [f"YAML syntax error: {e}"], "warnings": []}

    # 2. Required fields
    domain_info = config.get("domain", {})
    if not domain_info.get("name"):
        errors.append("Missing: domain.name")
    elif not DOMAIN_NAME_RE.match(domain_info["name"]):
        errors.append(f"Invalid domain.name: {domain_info['name']} (must match {DOMAIN_NAME_RE.pattern})")

    if not config.get("roles"):
        errors.append("Missing: roles section")

    # 3. Check personas exist (in agents/jarfis/)
    agents_dir = os.path.join(get_claude_dir(), "agents", "jarfis")
    all_personas = set()
    for phase in ("plan", "design", "implement", "review"):
        for role in config.get("roles", {}).get(phase, []):
            persona = role.get("persona", "")
            if persona:
                all_personas.add(persona)

    for persona in sorted(all_personas):
        # Search recursively in agents/jarfis/
        found = _find_agent_file(agents_dir, persona)
        if not found:
            errors.append(f"Persona not found: {persona} (expected in {agents_dir})")

    # 4. Check skills exist (warning only — Phase B may not have created them yet)
    total_skill_tokens = 0
    for phase in ("plan", "design", "implement", "review"):
        for role in config.get("roles", {}).get(phase, []):
            skill_list = role.get("skills", []) or []
            if isinstance(skill_list, str):
                skill_list = [skill_list]
            for skill_name in skill_list:
                try:
                    skill_path = _resolve_skill_path(domain_name, skill_name, domains_dir)
                    if not os.path.isfile(skill_path):
                        warnings.append(
                            f"Skill file not found: {skill_name}.md "
                            f"(will be created in Phase B)"
                        )
                    else:
                        with open(skill_path, encoding="utf-8") as f:
                            total_skill_tokens += estimate_tokens(f.read())
                except ValueError as e:
                    errors.append(f"Invalid skill name: {skill_name} — {e}")

    # 5. Token budget check
    budget = config.get("max_skill_tokens", 2500)
    if total_skill_tokens > budget:
        warnings.append(
            f"Total skill tokens ({total_skill_tokens}) exceed budget ({budget}). "
            f"Some skills will be truncated at compose time."
        )

    # 6. Individual skill > budget check (W1-1)
    for phase in ("implement",):
        for role in config.get("roles", {}).get(phase, []):
            for skill_name in (role.get("skills", []) or []):
                try:
                    skill_path = _resolve_skill_path(domain_name, skill_name, domains_dir)
                    if os.path.isfile(skill_path):
                        with open(skill_path, encoding="utf-8") as f:
                            single_tokens = estimate_tokens(f.read())
                        if single_tokens > budget:
                            warnings.append(
                                f"Single skill '{skill_name}' ({single_tokens} tokens) "
                                f"exceeds budget ({budget}). First skill is always loaded, "
                                f"but consider splitting."
                            )
                except (ValueError, FileNotFoundError):
                    pass

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }


def _find_agent_file(agents_dir, name):
    """Recursively find an agent .md file by frontmatter name."""
    if not os.path.isdir(agents_dir):
        return None

    for root, dirs, files in os.walk(agents_dir):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    # Quick frontmatter parse
                    first_line = f.readline().strip()
                    if first_line != "---":
                        continue
                    for line in f:
                        line = line.strip()
                        if line == "---":
                            break
                        if line.startswith("name:"):
                            agent_name = line.split(":", 1)[1].strip().strip('"').strip("'")
                            if agent_name == name:
                                return fpath
            except Exception:
                continue

    return None


def scaffold(domain_name, domains_dir=None):
    """Generate a skeleton domain pack.

    Creates:
    - domains/{name}.yaml (minimal valid config)
    - domains/{name}/skills/ (empty directory)
    - domains/{name}/hooks/ (empty directory)
    - domains/{name}/templates/ (empty directory)

    Returns:
        Dict with created_files list.
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    if not DOMAIN_NAME_RE.match(domain_name):
        return {"error": f"Invalid domain name: {domain_name}"}

    created = []

    # Create directories
    for subdir in (SKILLS_DIR_NAME, HOOKS_DIR_NAME, "templates"):
        dir_path = os.path.join(domains_dir, domain_name, subdir)
        os.makedirs(dir_path, exist_ok=True)
        created.append(dir_path)

    # Create domain.yaml
    yaml_path = os.path.join(domains_dir, f"{domain_name}.yaml")
    if not os.path.exists(yaml_path):
        template = f"""# JARFIS {domain_name} Domain Pack
schema_version: 2
min_core_version: "3.0.0"

domain:
  name: {domain_name}
  display_name: "{domain_name.title()} Development"

roles:
  plan:
    - persona: senior-product-owner
      skills: []
      model: opus
  design:
    - persona: technical-architect
      skills: []
      model: opus
  implement:
    - name: engineer
      persona: senior-backend-engineer
      skills: []
      model: sonnet
      commit_prefix: "ENG"
      required: true
  review:
    - persona: tech-lead
      skills: []
      model: opus

max_skill_tokens: 2500

rules:
  filter_by_tags: true
  always_include_untagged: true

detect:
  indicators:
    - file: "TODO_CHANGE_ME"
      framework: "{domain_name}"
      confidence: 0.9

quality:
  linters: []

commit:
  implementation: "jarfis({{ROLE}}-{{N}}):"
  fix: "jarfis(fix/{{ROLE}}):"

pipeline:
  test:
    runner: "echo 'no test configured'"
  build:
    check: "echo 'no build configured'"

lifecycle: {{}}

hooks:
  phase2: {{ before: null, after: null }}
  phase3: {{ before: null, after: null }}
  phase4: {{ before: null, after: null }}
  phase5: {{ before: null, after: null }}

fallback:
  on_compose_error: "persona-only"
  on_skip: "ask-user"
"""
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(template)
        created.append(yaml_path)

    return {"created_files": created}


# ── CLI Entry Point ──

def main(args):
    """CLI entry point for jarfis domain subcommand."""
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    subcmd = args[0]
    subargs = args[1:]

    if subcmd == "list":
        result = list_domains()
        json_output(result)

    elif subcmd == "detect":
        if not subargs:
            json_output({"error": "Usage: jarfis domain detect <project_dir>"})
            sys.exit(1)
        result = detect(subargs[0])
        json_output(result)

    elif subcmd == "agents":
        if len(subargs) < 2:
            json_output({"error": "Usage: jarfis domain agents <domain> <phase>"})
            sys.exit(1)
        result = agents(subargs[0], subargs[1])
        json_output(result)

    elif subcmd == "compose":
        if len(subargs) < 3:
            json_output({
                "error": "Usage: jarfis domain compose <domain> <role> <task> [learnings] [context]"
            })
            sys.exit(1)
        learnings = subargs[3] if len(subargs) > 3 else None
        context = subargs[4] if len(subargs) > 4 else None
        result = compose(subargs[0], subargs[1], subargs[2], learnings, context)
        json_output(result)

    elif subcmd == "validate":
        if not subargs:
            json_output({"error": "Usage: jarfis domain validate <domain>"})
            sys.exit(1)
        result = validate(subargs[0])
        json_output(result)

    elif subcmd == "scaffold":
        if not subargs:
            json_output({"error": "Usage: jarfis domain scaffold <domain>"})
            sys.exit(1)
        result = scaffold(subargs[0])
        json_output(result)

    elif subcmd == "install":
        # TODO: Phase B — implement install logic
        json_output({"status": "not_implemented", "message": "Install will be implemented in Phase B"})

    else:
        json_output({"error": f"Unknown subcommand: {subcmd}"})
        sys.exit(1)
