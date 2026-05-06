"""JARFIS Domain — Domain Pack registry, composition, and management.

Usage: jarfis domain <subcommand> [args...]

Subcommands:
    list                         List installed domain packs
    detect <project_dir>         Auto-detect project domain
    agents <domain> <phase>      Get agents for a phase
    compose <domain> <role> <task>
                                 Compose Persona + Skills
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

    Lookup order (v4 flat-first, M2 옵션 E):
        1. ~/.claude/commands/jarfis/skills/{skill_name}.md  (flat — v4 preferred)
        2. {domains_dir}/{domain_name}/skills/{skill_name}.md (domain — v3 fallback)

    If the flat file exists, its path is returned directly (flat wins).
    Otherwise the domain-scoped path is returned even if the file is absent
    so the caller's existing FileNotFoundError / open() path stays unchanged.

    W1-11: Validates against path traversal on BOTH roots.
    S4/S5: Validates name patterns.

    Returns:
        Absolute path to the skill .md file.

    Raises:
        ValueError: If domain or skill name is invalid.
                    If resolved path escapes its root directory.
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    if not DOMAIN_NAME_RE.match(domain_name):
        raise ValueError(f"Invalid domain name: {domain_name}")
    if not SKILL_NAME_RE.match(skill_name):
        raise ValueError(f"Invalid skill name: {skill_name}")

    # (1) flat lookup — sibling of domains_dir
    flat_root = os.path.join(os.path.dirname(domains_dir), "skills")
    if os.path.isdir(flat_root):
        flat_base = os.path.realpath(flat_root)
        flat_resolved = os.path.realpath(
            os.path.join(flat_root, f"{skill_name}.md")
        )
        if not (flat_resolved == flat_base
                or flat_resolved.startswith(flat_base + os.sep)):
            raise ValueError(f"Path traversal detected (flat): {skill_name}")
        if os.path.isfile(flat_resolved):
            return flat_resolved

    # (2) v3 fallback — domain-scoped
    base = os.path.realpath(domains_dir)
    resolved = os.path.realpath(
        os.path.join(domains_dir, domain_name, SKILLS_DIR_NAME, f"{skill_name}.md")
    )

    if not (resolved == base or resolved.startswith(base + os.sep)):
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

    W1-5: Results sorted by ``(-confidence, -matched_count, name)`` for
    deterministic output with quantity tiebreaking.
    S2: Returns ``tie`` flag when top-2 share BOTH confidence AND
    matched_count (a true ambiguity that work.md must resolve via
    AskUserQuestion).

    M4.7 — ADR-0003 §2.6 scoring update:
        * ``confidence = max(matched_indicators)`` (was: mean).
        * ``matched_count`` becomes the secondary sort key.
        * Tauri-as-desktop tiebreaker: when ``tauri.conf.json`` or
          ``src-tauri/`` is present in ``project_dir``, every desktop
          indicator score is multiplied by 1.5 before the max is taken.

    Returns:
        Dict with 'matches' (list) and 'tie' (bool).
    """
    if domains_dir is None:
        domains_dir = _get_domains_dir()

    if not os.path.isdir(project_dir):
        return {"matches": [], "tie": False}

    # M4.7 — desktop weighting marker check (cheap, fixed-name lookups).
    desktop_boost = _has_desktop_tauri_marker(project_dir)

    matches = []

    for domain_info in list_domains(domains_dir):
        domain_name = domain_info["name"]
        try:
            config = _load_domain_yaml(domain_name, domains_dir)
        except Exception:
            continue

        indicators = config.get("detect", {}).get("indicators", [])
        scores = []  # M4.7: collect raw scores for max-based aggregation.

        for indicator in indicators:
            score = _evaluate_indicator(indicator, project_dir)
            if score > 0:
                # ADR-0003 §2.6 last paragraph: bump desktop scores when
                # a Tauri marker is present so Tauri-as-web (react match
                # on package.json) cannot outrank Tauri-as-desktop.
                if desktop_boost and domain_name == "desktop":
                    score = min(1.0, score * 1.5)
                scores.append(score)

        if scores:
            confidence = max(scores)
            matches.append({
                "domain": domain_name,
                "confidence": round(confidence, 3),
                "matched_indicators": len(scores),
            })

    # W1-5: Deterministic sort — confidence desc, matched_count desc, name asc.
    matches.sort(
        key=lambda m: (-m["confidence"], -m["matched_indicators"], m["domain"])
    )

    # S2: True tie iff both confidence AND matched_count match between top-2.
    tie = (
        len(matches) >= 2
        and matches[0]["confidence"] == matches[1]["confidence"]
        and matches[0]["matched_indicators"] == matches[1]["matched_indicators"]
    )

    return {"matches": matches, "tie": tie}


def _has_desktop_tauri_marker(project_dir):
    """Return True iff a recognizable Tauri-desktop marker exists under
    ``project_dir``. Used by M4.7 to apply a 1.5x weight to desktop
    indicator scores so Tauri-as-web (react in package.json) cannot
    outrank Tauri-as-desktop on max-confidence ties.

    Markers (any one suffices):
        * ``<project>/tauri.conf.json``
        * ``<project>/src-tauri/`` directory
        * ``<project>/src-tauri/tauri.conf.json``
    """
    candidates = (
        os.path.join(project_dir, "tauri.conf.json"),
        os.path.join(project_dir, "src-tauri"),
        os.path.join(project_dir, "src-tauri", "tauri.conf.json"),
    )
    for path in candidates:
        if os.path.exists(path):
            return True
    return False


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


# Fallback persona mapping: role_name → known agent_type (module-level so
# v4 callers can introspect without invoking compose()).
_FALLBACK_PERSONAS = {
    "backend_engineer": "backend-developer",
    "frontend_engineer": "frontend-developer",
    "devops_engineer": "devops-engineer",
    "rust_engineer": "backend-developer",
    "webview_engineer": "frontend-developer",
    "security_engineer": "security-engineer",
    "qa_engineer": "qa-engineer",
}


def load_skills_for_role(domain_name, role_name, domains_dir=None,
                         max_skill_tokens=None):
    """Load skills for a domain role with token budget applied.

    Extracted from compose() so v4 jarfis_cli.py compose can reuse the exact
    same loading/budget logic (옵션 D, system-spec §5.5). compose() now
    delegates to this function — behavior is identical for existing callers.

    R4 / W1-1: Token budget enforcement with first-skill guarantee.
    W1-2: CJK-aware token estimation (via estimate_tokens).
    W1-3 / S1: Null / missing / string skills handling.

    Args:
        domain_name: Domain identifier (e.g., "web", "desktop").
        role_name: Role name within the domain (e.g., "frontend_engineer").
        domains_dir: Override domains directory (for tests).
        max_skill_tokens: Budget override; falls back to domain.yaml
            `max_skill_tokens` (default 2500) when None.

    Returns:
        (loaded_skills, truncated_skills, skills_text)
        - loaded_skills: list[str] of skill identifiers loaded
        - truncated_skills: list[dict{name, reason}] of skills omitted
        - skills_text: concatenated markdown body (no `## Active Skills`
          heading). Caller wraps or embeds.

    Raises:
        FileNotFoundError, yaml.YAMLError, KeyError, ValueError:
            propagated from domain config load / role lookup. Callers that
            want graceful fallback (like compose()) should catch these.
    """
    config = _load_domain_yaml(domain_name, domains_dir)
    role = _find_role(config, role_name)

    token_budget = (
        max_skill_tokens
        if max_skill_tokens is not None
        else config.get("max_skill_tokens", 2500)
    )

    skills_content = ""
    loaded_skills = []
    truncated_skills = []
    token_used = 0

    # W1-3 / S1: Null / missing / string handling
    skill_list = role.get("skills", []) or []
    if isinstance(skill_list, str):
        skill_list = [skill_list]

    for i, skill_name in enumerate(skill_list):
        try:
            skill_path = _resolve_skill_path(domain_name, skill_name, domains_dir)

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
        except (FileNotFoundError, ValueError):
            truncated_skills.append({
                "name": skill_name,
                "reason": "file_not_found",
            })
            continue

        skill_tokens = estimate_tokens(skill_text)

        if token_used + skill_tokens > token_budget:
            # W1-1: First skill always loads (minimum 1 skill guarantee)
            if i == 0 and not loaded_skills:
                pass
            else:
                truncated_skills.append({
                    "name": skill_name,
                    "reason": "token_budget_exceeded",
                })
                continue

        skills_content += f"\n{skill_text}\n"
        loaded_skills.append(skill_name)
        token_used += skill_tokens

    # External skills (optional, same budget)
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

    return loaded_skills, truncated_skills, skills_content


def compose(domain_name, role_name, task,
            domains_dir=None):
    """Compose Persona + Skills into an agent prompt.

    Project-level files (rule, context, profile) are injected by the
    orchestrator separately, not by compose().

    F1/F2: Graceful degradation on errors.
    Skill loading delegates to `load_skills_for_role` (옵션 D) — behavior
    identical to pre-extraction releases.

    Returns:
        Dict with agent_type, prompt_content, token_count,
        loaded_skills, truncated_skills, fallback.
    """
    try:
        loaded_skills, truncated_skills, skills_content = load_skills_for_role(
            domain_name, role_name, domains_dir
        )
        # Persona lookup uses domain.yaml role config, so run role discovery
        # separately to avoid fragile re-parsing.
        config = _load_domain_yaml(domain_name, domains_dir)
        role = _find_role(config, role_name)
    except (FileNotFoundError, yaml.YAMLError, KeyError, ValueError) as e:
        error_msg = f"{type(e).__name__}: domain config load failed"
        fallback_type = _FALLBACK_PERSONAS.get(
            role_name, role_name.replace("_", "-")
        )
        return {
            "agent_type": fallback_type,
            "prompt_content": f"## Task\n{task}",
            "token_count": estimate_tokens(task),
            "loaded_skills": [],
            "truncated_skills": [],
            "fallback": True,
            "error": error_msg,
        }

    sections = []
    if skills_content.strip():
        sections.append(f"## Active Skills\n{skills_content}")
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
    - persona: product-owner
      skills: []
      model: opus
  design:
    - persona: technical-architect
      skills: []
      model: opus
  implement:
    - name: engineer
      persona: backend-developer
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


def install(source_dir, target_dir=None):
    """Install domain packs and personas from source to target.

    Phase 0 confirmed: recursive discovery works, so directory copy is sufficient.
    No flattening needed.

    Args:
        source_dir: Repository root (e.g., ~/repos/jarfis).
        target_dir: Installation root (e.g., ~/.claude). Defaults to get_claude_dir().

    Returns:
        Dict with copied_count and copied_files list.
    """
    if target_dir is None:
        target_dir = get_claude_dir()

    if not os.path.isdir(source_dir):
        return {"error": f"Source directory not found: {source_dir}"}

    import shutil

    copied_files = []

    # 1. Copy domains/ (schema, yamls, skills, hooks, templates)
    src_domains = os.path.join(source_dir, "commands", "jarfis", DOMAINS_DIR_NAME)
    tgt_domains = os.path.join(target_dir, "commands", "jarfis", DOMAINS_DIR_NAME)

    if os.path.isdir(src_domains):
        for root, dirs, files in os.walk(src_domains):
            rel = os.path.relpath(root, src_domains)
            tgt_root = os.path.join(tgt_domains, rel) if rel != "." else tgt_domains
            os.makedirs(tgt_root, exist_ok=True)
            for fname in files:
                src_file = os.path.join(root, fname)
                tgt_file = os.path.join(tgt_root, fname)
                shutil.copy2(src_file, tgt_file)
                copied_files.append(os.path.relpath(tgt_file, target_dir))

    # 2. Copy agents/jarfis/personas/ (recursive)
    src_personas = os.path.join(source_dir, "agents", "jarfis", "personas")
    tgt_personas = os.path.join(target_dir, "agents", "jarfis", "personas")

    if os.path.isdir(src_personas):
        os.makedirs(tgt_personas, exist_ok=True)
        for fname in os.listdir(src_personas):
            src_file = os.path.join(src_personas, fname)
            tgt_file = os.path.join(tgt_personas, fname)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, tgt_file)
                copied_files.append(os.path.relpath(tgt_file, target_dir))

    return {
        "copied_count": len(copied_files),
        "copied_files": copied_files,
    }


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
                "error": "Usage: jarfis domain compose <domain> <role> <task>"
            })
            sys.exit(1)
        result = compose(subargs[0], subargs[1], subargs[2])
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
        source = subargs[0] if subargs else None
        if not source:
            # Default: read from .jarfis-source
            source_file = os.path.join(get_claude_dir(), ".jarfis-source")
            if os.path.isfile(source_file):
                with open(source_file) as f:
                    source = f.read().strip()
            else:
                json_output({"error": "No source directory. Usage: jarfis domain install [source_dir]"})
                sys.exit(1)
        result = install(source)
        json_output(result)

    else:
        json_output({"error": f"Unknown subcommand: {subcmd}"})
        sys.exit(1)
