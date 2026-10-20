# Ubuntu Claude reviewer role decision — 2026-10-20

Status: `APPROVED`. Authority: current explicit product-owner execution decision.

This decision supersedes only the former requirement that ChatGPT Work perform every
independent product-review round. It does not alter product requirements, budgets,
Stop Markers, merge protection, human acceptance, or release gates.

- Ubuntu Codex implements and repairs product work.
- Ubuntu Claude is the sole routine independent AI product reviewer.
- The production Runner dispatches work, verifies and publishes candidates, relays the
  unmodified Claude result to a canonical top-level GitHub PR comment, and requires the
  canonical Consumer to read it back before accepting the verdict.
- The relay must preserve Claude reviewer identity separately from the authenticated
  GitHub publisher identity and retain exact repository, PR, HEAD, fingerprint, round,
  record ID, URL, author, submitted time, original-body digest, verdict and findings.
- A local result or local record number is never canonical evidence. Write/read-back
  failure is fail-closed and must not start another Claude round.
- ChatGPT Work is notification-only. It may be triggered once for an eligible
  `SOFT_FEEDBACK_AVAILABLE` event, which is non-blocking, or for
  `FINAL_HUMAN_ACCEPTANCE_REQUIRED` after the complete Issue #21 delivery evidence is
  present, which remains blocking until a human decides. All routine reviews, retries,
  progress changes and dispatches must not trigger Work.
- Notifications are deduplicated by goal, candidate identity and experience scope.
  Unverified delivery capability remains `NOT_VERIFIED`; the pending event is retained
  without blocking ordinary product development or claiming delivery.

Historical ChatGPT Work results retain their original identity and content.
