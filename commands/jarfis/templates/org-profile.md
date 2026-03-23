# Organization Profile Template

아래 구조로 `{org_root}/.jarfis/org-profile.md`를 생성한다.
프론트매터에 org, root, created를 정의하고, projects: 섹션에 하위 프로젝트를 등록한다.

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
