# Continue Extend — Agent Prompts

> **Locale**: Present ALL user-facing output in $LOCALE language. Internal reasoning: English.

## PO Prompt (PRD Augmentation)

```
Task prompt:
"Refer to the existing PRD and add the extended requirements.

## Existing PRD
{$DOCS_DIR/prd.md content}

## Extension Request
{$ARGUMENTS}

$PROJECT_CONTEXT

## Instructions
1. Preserve the structure and style of the existing PRD.
2. Append the new requirements as an '## Extension #{iteration}' section after the existing PRD.
3. Analyze dependencies and conflicts with existing features.
4. Determine whether additional roles are needed (current: {required_roles summary}).
5. Skip Working Backwards (refer to the existing press-release.md).
6. If anything is unclear, ask the user a clarifying question."
```

## Architect Prompt (Architecture Augmentation)

```
Task prompt:
"Build on the existing architecture and add the extension design.

## Existing Architecture
{$DOCS_DIR/architecture.md content}

## Extension PRD
{Extension section of prd.md}

$PROJECT_CONTEXT
$BE_PROJECT_PROFILE
$FE_PROJECT_PROFILE

## Instructions
1. Analyze the impact on the existing architecture.
2. Identify components to be changed or added.
3. Append an '## Extension #{iteration}' section to architecture.md.
4. If any decisions conflict with existing ADRs, add a new ADR."
```

## Tech Lead Prompt (Task Breakdown)

```
Task prompt:
"Break down the extension requirements into tasks.

## Existing Tasks
{$DOCS_DIR/tasks.md content}

## Extension Design
{Extension section of architecture.md}

## Extension PRD
{Extension section of prd.md}

$BE_PROJECT_PROFILE
$FE_PROJECT_PROFILE

## Instructions
1. Add an '## Extension Tasks (#N)' section to tasks.md.
2. Specify dependencies with existing tasks.
3. Follow the same format as existing tasks (BE/FE/DevOps categorization, checkboxes).
4. If a project profile exists, reference the directory structure and conventions to specify target files concretely."
```

## QA Prompt (Test Strategy Augmentation) — runs only when test-strategy.md exists

```
Task prompt:
"Refer to the existing test strategy and add the test strategy for the extended features.

## Existing Test Strategy
{$DOCS_DIR/test-strategy.md content}

## Extension Tasks
{Extension Tasks section of tasks.md}

## Extension PRD
{Extension section of prd.md}

## Instructions
1. Add an '## Extension Test Strategy (#N)' section to test-strategy.md.
2. Write Unit/Integration/E2E test scenarios for the extended features in the same format as existing tests.
3. Analyze the impact on existing tests (whether existing tests might break).
4. List edge cases for the extended features.
5. If performance test criteria change, specify them."
```
