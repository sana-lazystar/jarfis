"""JARFIS Detect Project — framework/language auto-detection.

Usage: jarfis detect [project_dir]

Output: JSON with project_dir, languages, frameworks, package_managers,
        project_type, runtime, manifests_found, confidence, details.
"""

import json
import os
import sys

from .utils import json_output


def _add_unique(lst, value):
    if value not in lst:
        lst.append(value)


def _grep_file(path, pattern):
    """Check if pattern exists in file content (simple substring match)."""
    try:
        with open(path) as f:
            return pattern in f.read()
    except Exception:
        return False


def _load_package_json(project_dir):
    """Load and parse package.json, return (deps_keys_set, raw_text)."""
    pkg_path = os.path.join(project_dir, "package.json")
    if not os.path.isfile(pkg_path):
        return None, ""
    try:
        with open(pkg_path) as f:
            data = json.load(f)
        # Collect all dependency keys for framework detection
        all_deps = set()
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            if isinstance(data.get(section), dict):
                all_deps.update(data[section].keys())
        return all_deps, data
    except Exception:
        return None, ""


def detect(project_dir):
    project_dir = os.path.abspath(project_dir)
    languages = []
    frameworks = []
    package_managers = []
    manifests = []
    project_type = ""
    runtime = ""
    confidence = "high"
    details = {}

    # ── Node.js ecosystem ──
    deps, pkg_data = _load_package_json(project_dir)
    if deps is not None:
        manifests.append("package.json")
        _add_unique(languages, "javascript")

        # Package manager
        if os.path.isfile(os.path.join(project_dir, "pnpm-lock.yaml")):
            _add_unique(package_managers, "pnpm")
        elif os.path.isfile(os.path.join(project_dir, "yarn.lock")):
            _add_unique(package_managers, "yarn")
        elif os.path.isfile(os.path.join(project_dir, "bun.lockb")) or \
             os.path.isfile(os.path.join(project_dir, "bun.lock")):
            _add_unique(package_managers, "bun")
            runtime = "bun"
        elif os.path.isfile(os.path.join(project_dir, "package-lock.json")):
            _add_unique(package_managers, "npm")
        else:
            _add_unique(package_managers, "npm")

        # TypeScript
        if os.path.isfile(os.path.join(project_dir, "tsconfig.json")):
            _add_unique(languages, "typescript")
            manifests.append("tsconfig.json")

        # FE frameworks
        if "next" in deps:
            _add_unique(frameworks, "next.js")
            if os.path.isdir(os.path.join(project_dir, "app")) or \
               os.path.isdir(os.path.join(project_dir, "src", "app")):
                details["next_router"] = "app"
            elif os.path.isdir(os.path.join(project_dir, "pages")) or \
                 os.path.isdir(os.path.join(project_dir, "src", "pages")):
                details["next_router"] = "pages"
            if os.path.isdir(os.path.join(project_dir, "pages", "api")) or \
               os.path.isdir(os.path.join(project_dir, "app", "api")) or \
               os.path.isdir(os.path.join(project_dir, "src", "app", "api")):
                project_type = "fullstack"
            else:
                project_type = "frontend"
        elif "nuxt" in deps:
            _add_unique(frameworks, "nuxt")
            project_type = "fullstack" if os.path.isdir(os.path.join(project_dir, "server")) else "frontend"
        elif "react" in deps:
            _add_unique(frameworks, "react")
            project_type = "frontend"
        elif "vue" in deps:
            _add_unique(frameworks, "vue")
            project_type = "frontend"
        elif "svelte" in deps:
            _add_unique(frameworks, "svelte")
            project_type = "frontend"
        elif "@angular/core" in deps:
            _add_unique(frameworks, "angular")
            project_type = "frontend"
        elif "solid-js" in deps:
            _add_unique(frameworks, "solid")
            project_type = "frontend"
        elif "astro" in deps:
            _add_unique(frameworks, "astro")
            project_type = "frontend"

        # Remix / SvelteKit
        if any(d.startswith("@remix-run") for d in deps):
            _add_unique(frameworks, "remix")
            project_type = "fullstack"
        if "@sveltejs/kit" in deps:
            _add_unique(frameworks, "sveltekit")
            project_type = "fullstack"

        # BE frameworks (Node.js)
        for dep, fw in [("express", "express"), ("fastify", "fastify"),
                        ("@nestjs/core", "nestjs"), ("koa", "koa"), ("hono", "hono")]:
            if dep in deps:
                _add_unique(frameworks, fw)
                if not project_type:
                    project_type = "backend"

        # React Native
        if "react-native" in deps:
            _add_unique(frameworks, "react-native")
            project_type = "mobile"

        # Electron
        if "electron" in deps:
            _add_unique(frameworks, "electron")
            project_type = "desktop"

        if not runtime:
            runtime = "node"

    # ── Java/Kotlin ──
    pom = os.path.join(project_dir, "pom.xml")
    if os.path.isfile(pom):
        manifests.append("pom.xml")
        _add_unique(languages, "java")
        _add_unique(package_managers, "maven")
        project_type = "backend"
        runtime = "jvm"
        if _grep_file(pom, "spring-boot"):
            _add_unique(frameworks, "spring-boot")

    gradle = os.path.join(project_dir, "build.gradle")
    gradle_kts = os.path.join(project_dir, "build.gradle.kts")
    if os.path.isfile(gradle) or os.path.isfile(gradle_kts):
        manifests.append("build.gradle")
        _add_unique(package_managers, "gradle")
        runtime = "jvm"
        if not project_type:
            project_type = "backend"
        if os.path.isfile(gradle_kts):
            _add_unique(languages, "kotlin")
        else:
            _add_unique(languages, "java")
        gfile = gradle_kts if os.path.isfile(gradle_kts) else gradle
        if _grep_file(gfile, "spring"):
            _add_unique(frameworks, "spring-boot")

    # ── Python ──
    py_manifests = [
        ("requirements.txt", "pip"),
        ("pyproject.toml", None),  # special handling
        ("Pipfile", "pipenv"),
    ]
    for manifest, pm in py_manifests:
        mpath = os.path.join(project_dir, manifest)
        if os.path.isfile(mpath):
            _add_unique(languages, "python")
            runtime = "python"
            if not project_type:
                project_type = "backend"
            manifests.append(manifest)
            if pm:
                _add_unique(package_managers, pm)
            elif manifest == "pyproject.toml":
                if _grep_file(mpath, "poetry"):
                    _add_unique(package_managers, "poetry")
                elif _grep_file(mpath, "uv"):
                    _add_unique(package_managers, "uv")
                else:
                    _add_unique(package_managers, "pip")

    # Python framework detection
    for reqfile in ["requirements.txt", "pyproject.toml"]:
        rpath = os.path.join(project_dir, reqfile)
        if os.path.isfile(rpath):
            try:
                content = open(rpath).read().lower()
                if "django" in content:
                    _add_unique(frameworks, "django")
                if "flask" in content:
                    _add_unique(frameworks, "flask")
                if "fastapi" in content:
                    _add_unique(frameworks, "fastapi")
            except Exception:
                pass

    # ── Go ──
    gomod = os.path.join(project_dir, "go.mod")
    if os.path.isfile(gomod):
        manifests.append("go.mod")
        _add_unique(languages, "go")
        _add_unique(package_managers, "go-modules")
        runtime = "go"
        if not project_type:
            project_type = "backend"
        if _grep_file(gomod, "gin-gonic"):
            _add_unique(frameworks, "gin")
        if _grep_file(gomod, "labstack/echo"):
            _add_unique(frameworks, "echo")
        if _grep_file(gomod, "gofiber"):
            _add_unique(frameworks, "fiber")

    # ── Rust ──
    if os.path.isfile(os.path.join(project_dir, "Cargo.toml")):
        manifests.append("Cargo.toml")
        _add_unique(languages, "rust")
        _add_unique(package_managers, "cargo")
        runtime = "rust"
        if not project_type:
            project_type = "backend"

    # ── Flutter/Dart ──
    pubspec = os.path.join(project_dir, "pubspec.yaml")
    if os.path.isfile(pubspec):
        manifests.append("pubspec.yaml")
        _add_unique(languages, "dart")
        _add_unique(package_managers, "pub")
        runtime = "dart"
        if _grep_file(pubspec, "flutter"):
            _add_unique(frameworks, "flutter")
            project_type = "mobile"

    # ── Ruby ──
    gemfile = os.path.join(project_dir, "Gemfile")
    if os.path.isfile(gemfile):
        manifests.append("Gemfile")
        _add_unique(languages, "ruby")
        _add_unique(package_managers, "bundler")
        runtime = "ruby"
        if not project_type:
            project_type = "backend"
        if _grep_file(gemfile, "rails"):
            _add_unique(frameworks, "rails")

    # ── Confidence ──
    if not manifests:
        confidence = "low"
        project_type = "unknown"
    elif not frameworks:
        confidence = "medium"

    result = {
        "project_dir": project_dir,
        "languages": languages,
        "frameworks": frameworks,
        "package_managers": package_managers,
        "project_type": project_type or "unknown",
        "runtime": runtime or "unknown",
        "manifests_found": manifests,
        "confidence": confidence,
    }
    if details:
        result["details"] = details

    json_output(result)


def main(args):
    project_dir = args[0] if args else os.getcwd()
    detect(project_dir)
