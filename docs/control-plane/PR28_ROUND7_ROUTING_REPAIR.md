# PR #28 Round 7 reviewer-routing repair

Status: `FIXED_PENDING_REVIEW`. This is control-plane repair evidence; it does not alter product behavior, approve a review verdict, or authorize another model call.

Canonical source finding: GitHub PR #28 comment `6283528124`, verdict `CHANGES_REQUIRED`, exact candidate `1725cdee06753ead8dcfb79821e8043332d04178` / `d52dcebf0e1e940e7c959d0328542f3544702125dc98583ceeb40971bbc7e108`.

| Finding | Repair | Regression evidence |
|---|---|---|
| `finding-work-per-round-routing-remains` | New review results, custody, transitions, finding lifecycle and generated handoffs use `UBUNTU_CLAUDE_REVIEWER`; Runner relay and canonical Consumer read-back are the active external path. `CHATGPT_WORK_REVIEWER` is accepted only for immutable events dated before the 2026-10-20 cutover and cannot author a new result. ChatGPT Work remains notification-only. | `test_legacy_work_role_cannot_author_a_new_candidate_result`; `test_legacy_work_history_is_read_only_across_role_cutover`; `test_generated_routine_review_handoff_names_claude_runner_and_not_work`; orchestrator external-handoff assertion; existing Work notification eligibility/deduplication tests. |

Round 7 evidence and budget are immutable: comment `6283528124` remains unchanged and Claude usage remains `7/7`. The next candidate must stop at `READY_FOR_REVIEW_BUDGET_BLOCKED` until a separate owner authorization exists.
