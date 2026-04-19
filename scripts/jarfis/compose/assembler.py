"""Assemble the final prompt delivered to jarfis-foreman sub-agents.

Output layout (system-spec §5.5):
    ## Output Language
    {locale}

    ## Persona
    {persona_text}

    ## Active Skills          (omitted if skills_text is empty)
    {skills_text}

    ## Context                (omitted if no context_blocks)

    ### {label}
    {content}
    ...

    ## Task
    {task_instruction}

`## Task` default: a short directive telling the sub-agent to follow the
Phase prompt provided in the parent process. Callers pass a full override
when they have bespoke instructions.
"""

from .errors import ConfigError


_DEFAULT_TASK = (
    "Read the Phase prompt provided in the parent process and execute the "
    "instructions."
)

_DEFAULT_LOCALE = "ko"


def assemble_prompt(locale, persona_text, skills_text, context_blocks,
                    task_instruction=None):
    """Build the final prompt string.

    Args:
        locale: state.locale (may be None → default `ko`, meta flagged).
        persona_text: non-empty markdown body of persona file.
        skills_text: already-joined skills markdown (no `## Active Skills`
            heading). Empty string → section omitted.
        context_blocks: list[(label, content)] — label becomes `### label`,
            content placed verbatim below. Empty → section omitted.
        task_instruction: override for the `## Task` body. None → default.

    Returns:
        (prompt_str, meta_dict)
        meta_dict keys:
            locale_fallback — True when locale was None/empty.

    Raises:
        ConfigError: persona_text empty.
    """
    if not persona_text or not persona_text.strip():
        raise ConfigError("assemble_prompt: persona_text is required")

    meta = {}
    if not locale:
        locale = _DEFAULT_LOCALE
        meta["locale_fallback"] = True

    parts = [
        f"## Output Language\n{locale}",
        f"## Persona\n{persona_text.strip()}",
    ]

    if skills_text and skills_text.strip():
        parts.append(f"## Active Skills\n{skills_text.strip()}")

    if context_blocks:
        ctx_lines = ["## Context"]
        for label, content in context_blocks:
            if content is None or not str(content).strip():
                continue
            ctx_lines.append(f"\n### {label}\n{str(content).strip()}")
        # only emit the section if at least one block had real content
        if len(ctx_lines) > 1:
            parts.append("\n".join(ctx_lines))

    parts.append(f"## Task\n{task_instruction or _DEFAULT_TASK}")

    return "\n\n".join(parts) + "\n", meta
