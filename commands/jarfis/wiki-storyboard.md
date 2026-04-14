# /jarfis:wiki-storyboard — Design Catalog Browsing

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

The user wants to open the design catalog: $ARGUMENTS

## Purpose
View the overall design status of a service in the browser, outside of a workflow context.

## Prerequisites
- Organization registration complete (`org-profile.md` exists)
- Design mockups exist in `wiki/DESIGN/pages/{project}/` (at least one workflow completed)

## Flow

1. **Check Org**
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py org info $(pwd)
   ```
   - On failure: Display "Organization is not registered. Please run `/jarfis:work` first." and exit

2. **Extract FE Project List**
   - Filter only FE/Fullstack type projects from the `projects` array in the `org info` JSON
   - If 0 projects: Display "No FE projects found." and exit

3. **Select Project** (AskUserQuestion)
   ```
   question: "Select a project to open the design catalog:"
   header: "Design"
   options:
     - label: "{project_1}"
       description: "{project_1_path}"
     - label: "{project_2}"
       description: "{project_2_path}"
   ```
   - If only 1 project, select it automatically

4. **Open Catalog**
   ```bash
   open {org_root}/.jarfis-org/wiki/DESIGN/pages/{selected_project}/_index.html
   ```
   - If `_index.html` does not exist: Display "No mockups yet. Complete Phase 3 in `/jarfis:work`."

5. **Display Result**
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   📖 Design Catalog: {project}
   📂 {path_to_index_html}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```
