# Organization Profile Template

Create `{org_root}/.jarfis/org-profile.md` with the structure below.
Define org, root, and created in the frontmatter, and register sub-projects in the projects: section.

```markdown
---
org: {org_name}
root: {org_root_path}
created: {date}
---

# Organization Profile

## Projects

| Name | Path | Type | Profile |
|------|------|------|---------|
| {project_name} | {relative_path} | {type} | .jarfis/project-profile.md |
```
