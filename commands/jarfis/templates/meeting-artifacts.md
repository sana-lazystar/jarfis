# Meeting Artifacts Templates

## 1. summary.md — Meeting Summary

```yaml
---
type: meeting-summary
idea: "$ARGUMENTS original text"
meeting_name: "$MEETING_NAME"
date: "YYYY-MM-DD"
participants: [PO, TL, list of summoned experts]
status: completed
---
```

```markdown
# $MEETING_NAME Meeting Summary

## One-Line Summary
(Core summary in 3-5 lines)

## Key Decisions
- (1-3 major decision bullets)

## Next Steps
- (Key points to reference when proceeding with work)
```

## 2. meeting-notes.md — Topic-Organized Meeting Notes

```markdown
# $MEETING_NAME Meeting Notes

**Date**: YYYY-MM-DD
**Participants**: PO, TL [, summoned experts]

## Topic 1: [Topic Name]
### Discussion
- (Key discussion points)

### Agreements
- (Agreed-upon items)

### Open Items
- (Unresolved items)

## Topic 2: [Topic Name]
...

## Other Discussion
- (Miscellaneous discussion items that are hard to categorize)
```

## 3. decisions.md — Decision Tracking Table

```markdown
# $MEETING_NAME Decisions

| # | Decision | Rationale | Alternatives Considered | Decided By | Status |
|---|----------|-----------|------------------------|------------|--------|
| 1 | (Decision content) | (Why this was decided) | (Other options reviewed) | PO/TL/Consensus | Confirmed/Tentative |
| 2 | ... | ... | ... | ... | ... |

## Tentative Decision Details
(Additional explanation for tentative decisions, if needed)

## Open Items
- [ ] (Undecided item 1)
- [ ] (Undecided item 2)
```

## 4. tech-research.md — Expert Research Results (Conditional)

This file is only generated when an expert was summoned during the meeting.

```markdown
# $MEETING_NAME Technical Research

## Research 1: [Expert Type] — [Topic]
**Question**: ...
**Analysis Results**: ...
**Recommendations**: ...

## Research 2: [Expert Type] — [Topic]
...
```
