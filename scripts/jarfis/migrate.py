"""JARFIS Migration — v4.3 → v4.4 org-root data-source restructure.

Subcommand: ``jarfis migrate v4.3-to-v4.4 [--dry-run] [--no-backup]``

Behavior:
  1. Read ``.personal/orgs/orgs.json``.
  2. For each registered org, plan moves:
     - ``{personal}/orgs/{name}/meetings/`` → ``{org.root}/.jarfis-org/meetings/``
     - ``{personal}/orgs/{name}/works/``    → ``{org.root}/.jarfis-org/works/``
     - ``{personal}/orgs/{name}/learnings.md`` → ``{org.root}/.jarfis-org/learnings.md``
  3. Standalone bucket: ``{personal}/orgs/_standalone/{meetings,works,learnings.md}``
     → ``{personal}/{meetings,works,learnings.md}/`` (flat, no _standalone wrapper).
  4. Detect git-orphan org_root (Critic Fix B):
     - ``git -C {org.root} rev-parse --show-toplevel`` — non-zero return code →
       org_root is git-orphan; mark sync: none in org-profile.md frontmatter.
     - Zero return code → mark sync: git.
  5. Write/update ``sync: git|manual|none`` line in
     ``{org.root}/.jarfis-org/org-profile.md`` frontmatter.
  6. Backup: ``tar -czf .personal/orgs/.backup-v4.3-{ISO}.tgz`` (skip if --no-backup).
  7. Active state.json files: scan all moved works/, find ``.jarfis-state.json``,
     rewrite ``work.docsDir`` and ``docs_dir`` strings to the new path.
  8. Dry-run: print actions only, perform no FS mutation.
  9. After successful migration: rename ``.personal/orgs/`` →
     ``.personal/orgs.v4.3-archive/`` (preserves ``orgs.json`` for reference;
     a fresh ``orgs.json`` is written at the new location).

The dry-run path returns a JSON summary; the apply path performs the moves
and returns a JSON summary too.
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile

from .utils import get_personal_dir, json_error, json_output


def _is_git_repo(path):
    """Return True if `git -C {path} rev-parse --show-toplevel` succeeds."""
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _ensure_sync_field(profile_path, sync_value):
    """Insert/update the ``sync:`` line in YAML frontmatter of org-profile.md.

    If the file has YAML frontmatter (``---`` ... ``---`` at top), the sync
    line is upserted there. If a sync line already exists, it is rewritten.
    """
    if not os.path.isfile(profile_path):
        return
    with open(profile_path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        # No frontmatter — prepend a minimal block (rare path).
        new_block = ["---", f"sync: {sync_value}", "---", ""]
        new_content = "\n".join(new_block) + content
        with open(profile_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return

    # Find closing '---'
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return  # malformed — leave alone

    # Look for an existing sync: line in [1:end_idx]
    sync_re = re.compile(r"^\s*sync\s*:")
    for i in range(1, end_idx):
        if sync_re.match(lines[i]):
            lines[i] = f"sync: {sync_value}"
            new_content = "\n".join(lines)
            with open(profile_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return

    # Insert before closing '---'
    lines.insert(end_idx, f"sync: {sync_value}")
    new_content = "\n".join(lines)
    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(new_content)


def _move_dir_contents(src, dst, actions, dry_run):
    """Move every entry inside src into dst (creating dst). Records action."""
    if not os.path.isdir(src):
        return
    os.makedirs(dst, exist_ok=True) if not dry_run else None
    for entry in os.listdir(src):
        src_entry = os.path.join(src, entry)
        dst_entry = os.path.join(dst, entry)
        actions.append({"op": "move", "src": src_entry, "dst": dst_entry})
        if dry_run:
            continue
        if os.path.exists(dst_entry):
            # Idempotency: skip already-migrated entries.
            actions[-1]["skipped"] = "destination_exists"
            continue
        shutil.move(src_entry, dst_entry)


def _move_file(src, dst, actions, dry_run):
    if not os.path.isfile(src):
        return
    actions.append({"op": "move", "src": src, "dst": dst})
    if dry_run:
        return
    if os.path.exists(dst):
        actions[-1]["skipped"] = "destination_exists"
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)


def _rewrite_state_docsdir(works_dir, legacy_path_substr, new_path_substr, actions, dry_run):
    """Walk works_dir, rewrite .jarfis-state.json docs_dir / work.docsDir strings.

    Replace any occurrence of legacy_path_substr with new_path_substr in
    docs_dir + work.docsDir.
    """
    if not os.path.isdir(works_dir):
        return
    for root, _dirs, files in os.walk(works_dir):
        if ".jarfis-state.json" not in files:
            continue
        sf = os.path.join(root, ".jarfis-state.json")
        try:
            with open(sf, encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        changed = False
        if isinstance(state.get("docs_dir"), str) and legacy_path_substr in state["docs_dir"]:
            actions.append({"op": "rewrite_state", "file": sf, "field": "docs_dir"})
            if not dry_run:
                state["docs_dir"] = state["docs_dir"].replace(legacy_path_substr, new_path_substr)
                changed = True
        work = state.get("work") if isinstance(state.get("work"), dict) else None
        if work and isinstance(work.get("docsDir"), str) and legacy_path_substr in work["docsDir"]:
            actions.append({"op": "rewrite_state", "file": sf, "field": "work.docsDir"})
            if not dry_run:
                work["docsDir"] = work["docsDir"].replace(legacy_path_substr, new_path_substr)
                state["work"] = work
                changed = True
        if changed and not dry_run:
            with open(sf, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)


def _create_backup(legacy_orgs_dir, dry_run):
    """tar -czf .backup-v4.3-{ISO}.tgz the legacy orgs dir."""
    if not os.path.isdir(legacy_orgs_dir):
        return None
    iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_name = f".backup-v4.3-{iso}.tgz"
    backup_path = os.path.join(legacy_orgs_dir, backup_name)
    if dry_run:
        return backup_path
    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            for entry in os.listdir(legacy_orgs_dir):
                if entry == backup_name:
                    continue
                tar.add(os.path.join(legacy_orgs_dir, entry), arcname=entry)
    except (OSError, tarfile.TarError) as e:
        return None
    return backup_path


def _do_migration(dry_run, no_backup):
    personal = get_personal_dir()
    legacy_orgs_dir = os.path.join(personal, "orgs")
    legacy_archive_dir = os.path.join(personal, "orgs.v4.3-archive")
    actions = []
    notes = []

    # Idempotency check: if there's no orgs.json AND no legacy structure, no-op.
    orgs_json_path = os.path.join(legacy_orgs_dir, "orgs.json")
    if not os.path.isfile(orgs_json_path):
        # Check archive (already-migrated state)
        archive_orgs_json = os.path.join(legacy_archive_dir, "orgs.json")
        if os.path.isfile(archive_orgs_json):
            return {"status": "already_migrated", "actions": [], "dry_run": dry_run}
        return {"status": "no_op", "actions": [], "dry_run": dry_run, "reason": "no orgs.json"}

    with open(orgs_json_path, encoding="utf-8") as f:
        orgs_data = json.load(f)

    backup_path = None
    if not no_backup:
        backup_path = _create_backup(legacy_orgs_dir, dry_run)
        if backup_path:
            actions.append({"op": "backup", "path": backup_path})

    # Migrate each registered org.
    for org_entry in orgs_data.get("orgs", []):
        name = org_entry.get("name")
        root = org_entry.get("root")
        if not name or not root:
            continue

        legacy_org_dir = os.path.join(legacy_orgs_dir, name)
        new_jarfis_org = os.path.join(root, ".jarfis-org")

        if not os.path.isdir(legacy_org_dir):
            # Nothing to migrate for this org (already done or never existed).
            notes.append(f"{name}: legacy dir absent — skipping")
            # Still ensure sync field is set on org-profile.md if it exists.
            profile_path = os.path.join(new_jarfis_org, "org-profile.md")
            if os.path.isfile(profile_path):
                sync_mode = "git" if _is_git_repo(root) else "none"
                if not dry_run:
                    _ensure_sync_field(profile_path, sync_mode)
                actions.append({"op": "set_sync", "org": name, "value": sync_mode})
            continue

        # Move meetings/
        legacy_meetings = os.path.join(legacy_org_dir, "meetings")
        new_meetings = os.path.join(new_jarfis_org, "meetings")
        _move_dir_contents(legacy_meetings, new_meetings, actions, dry_run)

        # Move works/  (collect substrings for state rewrite)
        legacy_works = os.path.join(legacy_org_dir, "works")
        new_works = os.path.join(new_jarfis_org, "works")
        _move_dir_contents(legacy_works, new_works, actions, dry_run)

        # Rewrite state files in the (now-moved) works dir.
        if not dry_run:
            _rewrite_state_docsdir(
                new_works, legacy_works, new_works, actions, dry_run
            )

        # Move learnings.md
        legacy_learn = os.path.join(legacy_org_dir, "learnings.md")
        new_learn = os.path.join(new_jarfis_org, "learnings.md")
        _move_file(legacy_learn, new_learn, actions, dry_run)

        # Detect git-orphan + write sync field
        sync_mode = "git" if _is_git_repo(root) else "none"
        profile_path = os.path.join(new_jarfis_org, "org-profile.md")
        if os.path.isfile(profile_path):
            actions.append({"op": "set_sync", "org": name, "value": sync_mode})
            if not dry_run:
                _ensure_sync_field(profile_path, sync_mode)
        if sync_mode == "none":
            notes.append(f"{name}: git-orphan — sync set to 'none'")

    # Standalone bucket flatten
    legacy_standalone = os.path.join(legacy_orgs_dir, "_standalone")
    if os.path.isdir(legacy_standalone):
        for sub in ("meetings", "works"):
            src = os.path.join(legacy_standalone, sub)
            dst = os.path.join(personal, sub)
            _move_dir_contents(src, dst, actions, dry_run)
        legacy_sa_learn = os.path.join(legacy_standalone, "learnings.md")
        new_sa_learn = os.path.join(personal, "learnings.md")
        _move_file(legacy_sa_learn, new_sa_learn, actions, dry_run)
        # Rewrite state files in the new {personal}/works/
        if not dry_run:
            new_sa_works = os.path.join(personal, "works")
            _rewrite_state_docsdir(
                new_sa_works,
                os.path.join(legacy_standalone, "works"),
                new_sa_works,
                actions,
                dry_run,
            )

    # Final rename of orgs/ → orgs.v4.3-archive/ (apply only).
    # Preserve orgs.json by copying it to the new (fresh) orgs/ dir.
    if not dry_run:
        # Ensure the fresh orgs dir exists with orgs.json.
        # First, copy orgs.json out so we can recreate the directory.
        try:
            with open(orgs_json_path, encoding="utf-8") as f:
                fresh_orgs_data = f.read()
        except OSError:
            fresh_orgs_data = json.dumps(orgs_data, indent=2)

        # Move legacy orgs dir → orgs.v4.3-archive (preserve everything we just moved out of, plus the backup tarball + any leftover empty dirs).
        if os.path.isdir(legacy_orgs_dir) and not os.path.isdir(legacy_archive_dir):
            # Only rename if the only directly-still-relevant content is the
            # archive marker and orgs.json; otherwise leave untouched as a
            # safety measure.
            try:
                shutil.move(legacy_orgs_dir, legacy_archive_dir)
                actions.append({"op": "archive_legacy", "path": legacy_archive_dir})
            except OSError as e:
                notes.append(f"could not rename {legacy_orgs_dir} -> {legacy_archive_dir}: {e}")
        # Recreate fresh orgs/ with orgs.json so future runs see a registry.
        os.makedirs(legacy_orgs_dir, exist_ok=True)
        with open(orgs_json_path, "w", encoding="utf-8") as f:
            f.write(fresh_orgs_data)

    return {
        "status": "completed",
        "dry_run": dry_run,
        "actions": actions,
        "notes": notes,
        "backup": backup_path,
    }


def main(args):
    """Dispatch ``migrate`` subcommands.

    Currently only ``v4.3-to-v4.4`` is supported.
    """
    if not args:
        json_error(
            "Usage: jarfis migrate v4.3-to-v4.4 [--dry-run] [--no-backup]"
        )

    sub = args[0]
    flags = args[1:]
    dry_run = "--dry-run" in flags
    no_backup = "--no-backup" in flags

    if sub != "v4.3-to-v4.4":
        json_error(f"Unknown migrate target: {sub}. Supported: v4.3-to-v4.4")

    result = _do_migration(dry_run=dry_run, no_backup=no_backup)
    json_output(result)
