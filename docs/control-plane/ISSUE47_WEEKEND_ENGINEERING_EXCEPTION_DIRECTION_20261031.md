# Issue #47 — 2026-10-31 / 2026-11-01 limited engineering-time exception

Owner's explicit request (2026-10-31): “現在就開始吧 自治架設 特例”.

This exception is limited to the infrastructure engineering of existing Issue #47, not to any KGnote Product Goal, live product canary or standing go-live. It is a successor **immutable Goal version**, not an edit to the previous approved spec or a reset of usage history.

1. **Identity**: retain Goal ID `CODEX-APP-GOAL-ISSUE47-END-TO-END-AUTONOMOUS-COLLABORATION`; new version `2026-10-31.2-weekend-engineering-exception`, digest `8f3036ec6429e2f8f1e546aea3a8b3bf1c0cb1459e742991a4228612836958cd`. The original 2026-10-30.1 spec, Owner approval and historical receipts remain intact.
2. **Time**: allow engineering only on 2026-10-31 from 09:15 to 18:00 and 2026-11-01 from 09:00 to 18:00, Asia/Taipei; continue normal weekdays Nov 2–20 from 09:00–18:00. No permission on Nov 7–8 or Nov 14–15.
3. **Accounting**: retain at least Codex 7/18 with a ceiling of 18 (11 remaining at most), Claude 0/12, per-workday ceilings 3/2, single writer, subscription only, no paid API. Confirm live ledger and count any further known launches; never reset.
4. **Migration**: do not rewrite the old Goal spec. Read back the exact new GitHub Owner approval, import the new spec/schema into the existing #47 protected worktree, reconcile Git identity and existing work, and update PLAN/STATUS with fresh checkpoint; do not override unexpected dirty state. Existing `AUTOMATION_BLOCKED` because of future-only work start remains in audit; release only that exact blocker after authorized window and no-model guards pass.
5. **Positive/negative tests**: no-model check on permitted and forbidden dates, no duplicate model starts, old O2 read-only and unloaded, no canary, no standing scheduler, no effect from duplicate approvals, rollback safety.
6. **Human boundaries**: independently authorized Product Goal canary and final standing B-scheme go-live remain separate. No permission to cross these gates.
7. **Workflow**: do not create a new engineering Goal/session/repository; continue original #47 checkpoint, independent review and repair under the same total budget. This branch is an immutable amendment carrier; do not run a second writer against the active Codex branch.

Source Issue: https://github.com/joannalee20050914/KGnote-public/issues/47
