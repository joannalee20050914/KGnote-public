# KGnote Autonomous Development Go-Live — First Production Canary

Status: `APPROVED` by the product owner on 2026-10-17.

This authority permits only Issue #8 `finding-r-004`: Markdown speaker attribution repairs for HTML comments, quoted contexts, and necessary regression coverage. It authorizes at most three local repair attempts, internal cycles 18–20, and external Work rounds 5–6 during Asia/Taipei 09:00–18:30. Two consecutive rounds without material progress stop the canary.

Historical internal cycles 1–17 and external rounds 1–4 remain immutable. This authority does not permit cycle 21, external round 7, another product issue, paid API usage, force push, branch-protection bypass, modification or merge of PR #1, PR #22, or `main`, or promotion of PA-HUMAN-1, NS-HUMAN-SMOKE, or `release_verified`.

The production worktree is `/Users/joanna/KGnote-public-rewrite-20261005`, branch `codex/issue-8-source-library`, repository `joannalee20050914/KGnote-public`, PR #23 stacked on PR #22. The existing LaunchAgent, Runner, Orchestrator, Consumer, durable checkpoint, review history, and writer lock must be reused.

Stop with:

```bash
launchctl bootout gui/501 /Users/joanna/Library/LaunchAgents/com.kgnote.local-autonomy-runner.plist
```

Stopping preserves commits, checkpoints, review history, GitHub artifacts, and execution evidence. Ordinary resume or scheduled wake must never clear a terminal state outside this exact authorization.
