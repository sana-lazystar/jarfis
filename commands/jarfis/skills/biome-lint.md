# Biome Linting & Formatting Expertise

## Overview
Biome is a unified tool combining Prettier + ESLint. Written in Rust, making it extremely fast.

## Configuration (biome.json)
- `formatter`: Indentation, line width, quote style
- `linter`: Enable/disable rules, adjust severity
- `organizeImports`: Automatic import sorting

## Key Rules
- **Complexity**: noExcessiveCognitiveComplexity — Limit function complexity
- **Correctness**: noUnusedVariables, noConstAssign — Prevent mistakes
- **Suspicious**: noDoubleEquals — Prevent implicit type coercion
- **Style**: useConst — Prefer const over let

## Integration Patterns
- **Pre-commit hook**: lint-staged + biome check
- **CI**: `biome check --write` (auto-fix) vs `biome check` (validation only)
- **IDE**: VSCode Biome extension — Auto-format on save

## Migration from ESLint/Prettier
- `biome migrate eslint` — Automatically convert ESLint configuration
- Note: Some ESLint plugin rules may not exist in Biome
- Prettier compatibility: Mostly identical, but minor differences in trailing commas, etc.
