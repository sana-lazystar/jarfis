# JARFIS Init — Project Profile Creation

> **Locale**: All user-facing output must be presented in $LOCALE language. Internal instructions: English.

Analyze the project in the current directory and generate `./.jarfis-project/project-profile.md`.
This profile is injected into sub-agents when running `/jarfis:work`, saving codebase exploration tokens and generating code that follows project conventions.

User request: $ARGUMENTS

---

## Depth Setting

Parse the `--depth` flag from `$ARGUMENTS`:
- `--depth basic` → **basic**
- `--depth medium` → **medium**
- `--depth deep` or **no flag** → **deep** (default)

---

## Execution Flow

### Step 0: Project Detection (jarfis_cli.py detect)

Auto-detect the project type using the script:
```bash
python3 ~/.claude/scripts/jarfis_cli.py detect
```

Analyze the JSON output:
- `languages`: detected language list
- `frameworks`: detected framework list
- `package_managers`: package managers
- `project_type`: backend / frontend / fullstack / mobile / desktop / unknown
- `confidence`: high / medium / low
- `manifests_found`: files used for detection

If `confidence` is `low` or `project_type` is `unknown`, ask the user:
```
Could not auto-detect the project type.
Please describe this project's type and tech stack.
```

Display the detection results:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Init — Project Analysis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Path: (current directory)
🔍 Type: {project_type}
🛠️ Frameworks: {frameworks}
📦 Package manager: {package_managers}
🎯 Confidence: {confidence}
⚙️ Depth: basic / medium / deep
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 1: Basic Analysis (runs at all depth levels)

Analyze the following items:

**1-1. Tech Stack Identification**
- Language and version (refer to tsconfig.json, .nvmrc, .python-version, etc.)
- Framework and version
- Package manager (npm, yarn, pnpm, bun, etc.)
- Runtime (Node.js, Deno, Bun, etc.)

**1-2. Directory Structure**
- Generate a directory tree up to 3 levels deep
- One-line description of each major directory's role

**1-3. Key Dependencies**
- Core frameworks/libraries (excluding devDependencies)
- One-line description of each dependency's role

**1-4. Scripts and Commands**
- Dev server, build, test, and lint commands
- Check for environment variable files (.env.example, etc.)

**1-5. Config File Summary**
- Key settings from ESLint, Prettier, TypeScript, build tools, etc.
- Do not copy entire config files; summarize only the important options

> **basic depth ends here → proceed to Step 4**

### Step 2: Medium Analysis (runs at medium and deep)

**2-1. Coding Conventions Detection**
- File naming patterns: kebab-case, camelCase, PascalCase, etc. (sample actual filenames)
- Component/module structure patterns: barrel exports, co-location, feature-based, etc.
- Import conventions: absolute paths, path aliases (@/, ~/), ordering rules
- Type definition approach: interface vs type, file separation
- Error handling patterns: try-catch, Result types, custom error classes, etc.

**2-2. API Routes / Page List**
- BE: Explore route files and list endpoints (Method + Path + handler location)
- FE: List pages/routes (path + component location)

**2-3. Data Models / Schemas**
- Explore DB model files (Prisma schema, Mongoose models, TypeORM entities, Drizzle schema, etc.)
- Model name + key field list (summarize, do not copy entire schemas)

**2-4. Module Relationship Map**
- Dependency relationships between major modules (which module imports which)
- Identify shared modules/utilities

> **medium depth ends here → proceed to Step 4**

### Step 3: Deep Analysis (runs at deep only)

**3-1. Architecture Pattern Analysis**
- Identify layer structure: Controller-Service-Repository, MVC, Hexagonal, etc.
- Middleware chain / plugin structure
- State management patterns (FE): Redux, Zustand, Recoil, Context usage
- Authentication/authorization implementation

**3-2. Core Business Logic Summary**
- Identify main service/use-case modules and summarize each one's responsibility in 1-2 sentences
- Flag modules with complex business rules
- Do not copy code verbatim; describe only the role and logic flow

**3-3. Reusable Component Catalog**
- FE: List common UI components (name, props summary, usage locations)
- BE: List common utilities/helpers (name, function summary, usage locations)
- List shared types/interfaces

**3-4. Technical Notes and Caveats**
- Known workarounds or hack code (search TODO/FIXME/HACK comments)
- Unused code or deprecated patterns
- Performance-related notes (caching, memoization, lazy loading, etc.)

> **deep depth complete → proceed to Step 4**

### Step 4: Generate Profile Document

Save the analysis results to `./.jarfis-project/project-profile.md`.

> Use the template at `templates/project-profile.md` as the output format.

**Writing principles:**
- Token efficiency is the top priority: do not copy code verbatim; **describe** structure and patterns
- Do not include sections that were not analyzed at the current depth (no empty sections)
- All file paths should be relative to the project root
- Include the current HEAD commit hash in the header:
  ```bash
  git rev-parse --short HEAD
  ```
  Record the result as `> Last-Commit: <short-hash>`

### Step 4.5: Ensure project-rule.md Exists

Check if `./.jarfis-project/project-rule.md` exists. If not, create an empty file:
```bash
touch ./.jarfis-project/project-rule.md
```
Do not write any content, do not ask the user, do not provide guidance. Just ensure the file exists.

### Step 5: Report Results

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Init Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Project: [project name]
🔍 Type: [BE/FE/Fullstack]
📊 Depth: [basic/medium/deep]
📄 Output: ./.jarfis-project/project-profile.md

This profile is automatically referenced when running /jarfis:work.
Re-run /jarfis:project-init if the project structure changes significantly.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
