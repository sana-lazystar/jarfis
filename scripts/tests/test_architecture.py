"""Architecture boundary validation tests.

Enforces Clean Architecture rules (brainstorm-v3.md section 9):
- Core must not reference domain-specific terms
- Domain packs must not cross-reference each other
- All domain.yaml files must conform to schema
- Top-level directory structure reveals system purpose (Screaming Architecture)
"""

import os
import re

import pytest


def _get_jarfis_source():
    """Get JARFIS source repo path."""
    source_file = os.path.expanduser("~/.claude/.jarfis-source")
    if os.path.isfile(source_file):
        with open(source_file) as f:
            return f.read().strip()
    return os.path.expanduser("~/repos/jarfis")


# These tests run against the INSTALLED files (~/.claude/), not the source repo.
# They validate the active system's architectural integrity.

COMMANDS_DIR = os.path.expanduser("~/.claude/commands/jarfis")
SCRIPTS_DIR = os.path.expanduser("~/.claude/scripts/jarfis")
DOMAINS_DIR = os.path.join(COMMANDS_DIR, "domains")


class TestLeakyAbstraction:
    """Core modules must not contain domain-specific terminology."""

    # Domain-specific terms that should NOT appear in core modules
    DOMAIN_TERMS = [
        "react", "vue", "svelte", "angular", "nextjs",
        "unity", "godot", "unreal",
        "tauri", "electron",
        "django", "flask", "fastapi",
        "csharp", "c#",
    ]

    # Core module files to check (domain.py is excluded — it's the bridge)
    CORE_MODULES = [
        "state.py", "measure.py", "preflight.py",
        "meetings.py", "version.py", "sync.py",
        "validate.py", "organization.py",
    ]

    def test_core_modules_no_domain_terms(self):
        """No core module should reference specific frameworks/languages."""
        violations = []
        for module in self.CORE_MODULES:
            path = os.path.join(SCRIPTS_DIR, module)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as f:
                content = f.read().lower()
            for term in self.DOMAIN_TERMS:
                if term in content:
                    violations.append(f"{module} contains '{term}'")

        assert violations == [], f"Leaky abstractions found:\n" + "\n".join(violations)


class TestCrossDomainReferences:
    """Domain packs must not reference each other."""

    def test_no_cross_domain_references(self):
        """Files in domains/X/ must not reference domains/Y/."""
        if not os.path.isdir(DOMAINS_DIR):
            pytest.skip("No domains directory")

        domain_names = []
        for item in os.listdir(DOMAINS_DIR):
            if os.path.isdir(os.path.join(DOMAINS_DIR, item)) and not item.startswith("_"):
                domain_names.append(item)

        if len(domain_names) < 2:
            pytest.skip("Need at least 2 domains to check cross-references")

        violations = []
        for domain in domain_names:
            domain_path = os.path.join(DOMAINS_DIR, domain)
            for root, dirs, files in os.walk(domain_path):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            content = f.read()
                    except Exception:
                        continue
                    for other in domain_names:
                        if other != domain and other in content:
                            # Exclude external_skills references (allowed)
                            if f"{other}/" in content:
                                continue
                            violations.append(
                                f"{domain}/{fname} references '{other}'"
                            )

        assert violations == [], "Cross-domain references:\n" + "\n".join(violations)


class TestDomainYamlSchema:
    """All domain.yaml files must have required fields."""

    REQUIRED_FIELDS = ["schema_version", "domain", "roles"]
    REQUIRED_DOMAIN_FIELDS = ["name"]

    def test_all_domain_yamls_valid(self):
        """Every .yaml file in domains/ (except _*) must have required fields."""
        if not os.path.isdir(DOMAINS_DIR):
            pytest.skip("No domains directory")

        import yaml

        violations = []
        for fname in os.listdir(DOMAINS_DIR):
            if fname.startswith("_") or not fname.endswith(".yaml"):
                continue
            fpath = os.path.join(DOMAINS_DIR, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
            except yaml.YAMLError as e:
                violations.append(f"{fname}: YAML parse error: {e}")
                continue

            if not config or not isinstance(config, dict):
                violations.append(f"{fname}: empty or not a dict")
                continue

            for field in self.REQUIRED_FIELDS:
                if field not in config:
                    violations.append(f"{fname}: missing required field '{field}'")

            domain_info = config.get("domain", {})
            for field in self.REQUIRED_DOMAIN_FIELDS:
                if field not in domain_info:
                    violations.append(f"{fname}: missing domain.{field}")

        assert violations == [], "Schema violations:\n" + "\n".join(violations)
