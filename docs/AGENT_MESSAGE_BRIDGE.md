# Agent Message Bridge

Antigravity and Jules do not have a direct private-message channel in this workflow. Use GitHub as the shared message bus.

## Where to Send Messages

Use the smallest durable GitHub surface that matches the work:

1. Existing issue for the task, when one exists.
2. Existing PR conversation, when the message is about a branch or review.
3. A new issue titled `Agent handoff: <short topic>`, when no issue or PR fits.

Do not rely on chat-only instructions as the source of truth.

## Required Handoff Format

Every agent-to-agent handoff comment should include:

```markdown
## Agent Handoff

From: Antigravity
To: Jules
Related workstream: <number/name>
Related branch or artifact: <branch, file, or issue>

### Request
<Specific thing Jules should do or answer.>

### Context
<Short summary of what Antigravity found or produced.>

### Inputs
- <file, command, issue, PR, or artifact Jules should read>

### Expected Output
- <file, PR comment, report, test, or decision Jules should return>

### Blockers / Questions
- <anything preventing progress>
```

Jules should reply on the same issue or PR comment thread with the same headings, changing `From` and `To` as needed.

## Routing Rules

- Use `docs/WORKSTREAMS.md` for owner lookup.
- Use `docs/COORDINATION.md` for safety rules before proposing data changes.
- Keep full CSV databases, raw exports, backups, and secrets out of GitHub unless the user explicitly approves.
- If a handoff needs Codex to promote data into the active DB, say that explicitly; neither Antigravity nor Jules should promote directly.

## Current Common Routes

- Antigravity enrichment or search data -> issue #22 or the relevant Antigravity issue.
- Antigravity external-link verification -> issue #5.
- Jules automation, tests, CLI, reports, or SQLite work -> create or reuse a Jules workstream issue.
- Cross-agent integration request -> create `Agent handoff: <topic>` and link both agents' artifacts.
