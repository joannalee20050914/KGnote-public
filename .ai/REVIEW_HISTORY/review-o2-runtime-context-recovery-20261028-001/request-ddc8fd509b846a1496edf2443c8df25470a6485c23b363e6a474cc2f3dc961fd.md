# Current review request

Writer: Codex implementation agent. The JSON block is canonical; prose outside it is explanatory only.

<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->
```json
{
  "schema_version": "kgnote.review-request.v1",
  "protocol_version": "kgnote.review-protocol.v1",
  "review_id": "review-o2-runtime-context-recovery-20261028-001",
  "goal_id": "CODEX-APP-GOAL-O2-RUNTIME-CONTEXT-RECOVERY-20261028",
  "milestone_id": "R3-INDEPENDENT-REVIEW",
  "status": "IMPLEMENTING",
  "author_role": "CODEX_IMPLEMENTER",
  "base_revision": "9271bf8645858eed49effa8eca3df8ea491bfc17",
  "candidate_revision": null,
  "candidate_fingerprint": null,
  "authoritative_specs": [
    "docs/control-plane/AUTHORITY.md",
    "docs/control-plane/O2_RUNTIME_CONTEXT_RECOVERY_DIRECTION_20261028.md",
    "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-23.2.json",
    "docs/control-plane/O2_BOUNDED_TRIAL_AUTHORIZATION_PACKAGE_20261023.md",
    "docs/control-plane/B_SCHEME_OPERATIONS.md",
    "docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",
    ".ai/REVIEW_PROTOCOL.md",
    "docs/requirements/requirements.json",
    "docs/requirements/scenarios.json",
    "DEVELOPMENT_PLAIN.md",
    "AGENTS.md"
  ],
  "changed_areas": [
    "PLAN.md", "CODEX_STATUS.md", ".ai/", "docs/control-plane/", "requirements-runtime.lock",
    "scripts/codex_jsonl_evidence.py", "scripts/goal_continuity.py", "scripts/goal_runner_adapter.py",
    "scripts/product_goal_worker_result.py", "scripts/product_goal_worker_lane.py",
    "scripts/product_goal_worker_identity.py", "scripts/linux_worker_bootstrap.py", "scripts/linux_worker_router.py",
    "scripts/local_autonomy_runner.py", "scripts/successor_codex_entrypoint.py",
    "scripts/install_ubuntu_worker_runtime.py", "scripts/reconcile_o2_attempt_classification.py",
    "schemas/", "tests/control_plane/"
  ],
  "acceptance_criteria": [
    "Ubuntu Codex receives sealed Runner-verified Goal, Owner-authority, lifecycle, work, candidate and ledger context without deriving execution authority from stale PLAN/STATUS",
    "Exact checkout, Python, Node/npm, gh and repository tooling are admitted before provider/model invocation while conservative reservation accounting remains unchanged",
    "RATE_LIMITED requires structured provider/error evidence and is not triggered by incidental quota/429/rate-limit prose",
    "Two historical corrections are append-only and integrity-bound to original raw logs/checkpoints without resetting attempt or launch accounting",
    "Exact candidate passes deterministic verification and the existing independent Ubuntu Claude review before deployment",
    "Formal deployment read-back remains BLOCKED/PAUSED/go_live_authorized=false with exactly two attempts and no RESUME"
  ],
  "negative_requirements": [
    "Publish or synthesize RESUME, reissue APPROVE, or start a third O2 model dispatch",
    "Overwrite the formal ledger, checkpoint or raw logs, or reset resource/launch/attempt accounting",
    "Trust stale repository PLAN/STATUS as runtime Owner authority",
    "Treat arbitrary transcript prose containing quota, 429 or rate limit as provider evidence",
    "Force push, bypass GitHub rules, write main directly, reuse stale PASS or deploy unreviewed bytes",
    "Promote product, learning, physical-device, human-acceptance or release gates"
  ],
  "validation_performed": [],
  "validation_results": [],
  "known_deviations": [],
  "known_uncertainties": [],
  "reviewer_focus": [],
  "preserved_human_gates": [
    "O2-AUTHORITY-LEASE",
    "D2-T14-FINAL-HUMAN-ACCEPTANCE",
    "PA-HUMAN-1",
    "NS-HUMAN-SMOKE"
  ],
  "requested_at": null,
  "authorized_human_decision_identities": ["product owner"],
  "candidate_manifest": null,
  "completion_evidence": {
    "schema_version": "kgnote.review-completion-summary.v1",
    "applicable": false,
    "passed": true,
    "evidence_path": null,
    "evidence_sha256": null,
    "claims": [],
    "test_receipts": []
  }
}
```
<!-- END KGNOTE REVIEW REQUEST JSON -->

## Human-readable status

Review `review-o2-runtime-context-recovery-20261028-001` is `IMPLEMENTING`.
It has no active candidate binding and cannot be interpreted as a review request or PASS.
Codex must complete deterministic verification before issuing this request.
