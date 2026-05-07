# Organization Profile Template

Create `{org_root}/.jarfis-org/org-profile.md` with the structure below.
Define org, root, and created in the frontmatter, and register sub-projects in the projects: section.

```markdown
---
org: {org_name}
root: {org_root_path}
sync: git  # or 'manual' / 'none' — auto-detected by org-init based on whether root is in a git work tree (Critic Fix B, v4.4.0)
created: {date}
---

# Organization Profile

## Projects

| Name | Path | Type | Profile |
|------|------|------|---------|
| {project_name} | {relative_path} | {type} | .jarfis-project/project-profile.md |
```

### Frontmatter fields

- `org` — display name of the organization.
- `root` — absolute path to the physical org root (the directory containing this `.jarfis-org/`).
- `sync` — synchronization mode for the org's `.jarfis-org/` data:
  - `git` — `root` is inside a git work tree; the data flows via that repo's normal git workflow.
  - `manual` — user-managed sync (e.g. external rsync/dropbox); not auto-detected, set explicitly.
  - `none` — git-orphan org_root with no automatic sync mechanism (e.g. ad-hoc local directory).
  Auto-detection by `_create_org_files` (org-init) writes `git` when `git -C {root} rev-parse --show-toplevel` succeeds, otherwise `none`. The `migrate v4.3-to-v4.4` script applies the same auto-detect; the user may upgrade to `manual` post-migration.
- `created` — ISO date the organization was initialized.
