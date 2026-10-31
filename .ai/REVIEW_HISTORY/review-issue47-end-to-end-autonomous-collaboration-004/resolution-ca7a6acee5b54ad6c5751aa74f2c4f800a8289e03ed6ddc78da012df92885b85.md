# Current review result

Writer after reviewer custody: independent Ubuntu Claude reviewer only.

<!-- BEGIN KGNOTE REVIEW RESULT JSON -->
```json
{
  "schema_version": "kgnote.review-result.v1",
  "protocol_version": "kgnote.review-protocol.v1",
  "artifact_state": "SUBMITTED",
  "review_id": "review-issue47-end-to-end-autonomous-collaboration-004",
  "author_role": "UBUNTU_CLAUDE_REVIEWER",
  "reviewer_identity": "claude-code:ubuntu-review-only/session:7f445564-dff8-4e45-85e6-04304377dfc3/github-record:6538538869",
  "reviewed_revision": "e9955c778d0aa1ae0d2cc839345dbcbca0e4cc5d+worktree:428be2cd0b089c0a13d35c632543677405ef1eaddb8f0ea5330e51ebd748c716",
  "reviewed_fingerprint": "428be2cd0b089c0a13d35c632543677405ef1eaddb8f0ea5330e51ebd748c716",
  "verdict": "CHANGES_REQUIRED",
  "findings": [
    {
      "finding_id": "R-001",
      "severity": "MAJOR",
      "authority_source": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json#WI-4-TRUSTED-DEPLOYMENT.acceptance; docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json#hard_stop_conditions; review-request acceptance_criteria[2]",
      "expected_behavior": "Before enablement the candidate must implement and test rejection of duplicate or already-loaded service, unexpected model process or competing writer, latched stop, and rollback resurrection.",
      "observed_behavior": "Review 002 found the required negative paths missing. The Review 004 candidate added those paths and tests; the Review 004 reviewer was explicitly asked to revalidate R-001 and did not report a recurrence.",
      "evidence": [
        "Review 002 external finding: finding-unexpected-process-and-duplicate-service-negative-tests-missing",
        "output/control-plane/verification-20261031T113511+0800.json#control_plane_negative_tests",
        "Canonical Review 004 record: https://github.com/joannalee20050914/KGnote-public/pull/49#issuecomment-6538538869"
      ],
      "affected_files_or_behavior": [
        "scripts/install_collaboration_goal_entrypoint.py",
        "scripts/collaboration_goal_entrypoint.py",
        "tests/control_plane/test_collaboration_goal_entrypoint.py"
      ],
      "required_resolution": "Retain the reviewed negative paths and tests in all later candidates.",
      "verification_method": "Review 004 exact-candidate revalidation plus deterministic negative tests.",
      "status": "VERIFIED"
    },
    {
      "finding_id": "R-002",
      "severity": "MAJOR",
      "authority_source": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json#WI-4-TRUSTED-DEPLOYMENT.acceptance[0]; review-request acceptance_criteria[0]",
      "expected_behavior": "Status read-back and enabled execution must fail closed unless deployment identity and installed bytes match the reviewed receipt and exact activation record.",
      "observed_behavior": "Review 002 found deployed bytes were not reverified. The Review 004 candidate added receipt-bound read-back and enabled-path checks; the Review 004 reviewer was explicitly asked to revalidate R-002 and did not report a recurrence.",
      "evidence": [
        "Review 002 external finding: finding-deployed-bytes-not-reverified-at-status-or-run",
        "output/control-plane/verification-20261031T113511+0800.json#control_plane_negative_tests",
        "Canonical Review 004 record: https://github.com/joannalee20050914/KGnote-public/pull/49#issuecomment-6538538869"
      ],
      "affected_files_or_behavior": [
        "scripts/install_collaboration_goal_entrypoint.py",
        "scripts/collaboration_goal_entrypoint.py",
        "enabled status and run path"
      ],
      "required_resolution": "Retain exact receipt-bound deployment and activation checks in all later candidates.",
      "verification_method": "Review 004 exact-candidate revalidation plus deployment drift tests.",
      "status": "VERIFIED"
    },
    {
      "finding_id": "R-003",
      "severity": "MINOR",
      "authority_source": "docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json#WI-3-ZERO-MODEL-E2E.acceptance; docs/control-plane/ISSUE47_END_TO_END_ENGINEERING_GOAL_SPEC_v2026-10-31.2.json#review_policy.changes_required",
      "expected_behavior": "Exercise CHANGES_REQUIRED to DISPATCH_REPAIR with live no-model admission, cumulative accounting and restart suppression.",
      "observed_behavior": "Review 002 found the dispatch-boundary repair test missing. The Review 004 candidate added the test and related routing evidence; the Review 004 reviewer was explicitly asked to revalidate R-003 and did not report a recurrence.",
      "evidence": [
        "Review 002 external finding: finding-changes-required-repair-not-covered-at-dispatch-boundary",
        "output/control-plane/verification-20261031T113511+0800.json#control_plane_negative_tests",
        "Canonical Review 004 record: https://github.com/joannalee20050914/KGnote-public/pull/49#issuecomment-6538538869"
      ],
      "affected_files_or_behavior": [
        "scripts/collaboration_goal_dispatch.py",
        "scripts/goal_runner_adapter.py",
        "tests/control_plane/test_collaboration_goal_dispatch.py"
      ],
      "required_resolution": "Retain dispatch-boundary repair and restart coverage in all later candidates.",
      "verification_method": "Review 004 exact-candidate revalidation plus dispatcher-level repair tests.",
      "status": "VERIFIED"
    },
    {
      "finding_id": "R-004",
      "severity": "BLOCKER",
      "authority_source": "Review request acceptance criterion 5 and reviewer_focus on cumulative usage; negative requirement forbidding launch/accounting reset; Engineering Goal spec v2026-10-31.4 resource_policy",
      "expected_behavior": "Each reservation or launch must durably and atomically increase cumulative provider and workday usage, tied to the dispatch key, before a model command can run.",
      "observed_behavior": "The gate reads usage from CODEX_STATUS.md, but reservation and entrypoint transitions only update the wakeup state. No path advances the counters enforced by the gate.",
      "evidence": [
        "External reviewer finding: finding-usage-counters-never-advance",
        "scripts/issue47_engineering_wakeup.py:243-255 and 382",
        "scripts/collaboration_goal_entrypoint.py:399-422",
        "Canonical GitHub record: https://github.com/joannalee20050914/KGnote-public/pull/49#issuecomment-6538538869"
      ],
      "affected_files_or_behavior": [
        "scripts/issue47_engineering_wakeup.py",
        "scripts/collaboration_goal_entrypoint.py",
        "durable provider usage accounting"
      ],
      "required_resolution": "Charge exact dispatch usage atomically before launch, preserve it across restart, and enforce total and workday ceilings from the same durable history.",
      "verification_method": "Non-model tests must prove pre-launch charge, idempotency by dispatch key, preserved accounting after restart, and quota rejection.",
      "status": "FIXED_PENDING_REVIEW",
      "resolution_evidence": [
        "output/control-plane/verification-20261031T114907+0800.json#control_plane_negative_tests; scripts/issue47_engineering_wakeup.py; tests/control_plane/test_issue47_engineering_wakeup.py"
      ]
    },
    {
      "finding_id": "R-005",
      "severity": "BLOCKER",
      "authority_source": "Review request acceptance criterion 5; negative requirement forbidding launch history reset on restart",
      "expected_behavior": "A launched dispatch in RUNNING, COMPLETED or FAILED must not be silently re-reserved under the same key; unknown states must fail closed.",
      "observed_behavior": "Same-key suppression covers RESERVED, RUNNING and COMPLETED but not FAILED. A non-zero continuation can therefore be re-reserved, and the single state record is overwritten. Unknown statuses also fall through.",
      "evidence": [
        "External reviewer finding: finding-failed-same-key-redispatch",
        "scripts/issue47_engineering_wakeup.py:409-429 and 461",
        "scripts/collaboration_goal_entrypoint.py:407-411",
        "Canonical GitHub record: https://github.com/joannalee20050914/KGnote-public/pull/49#issuecomment-6538538869"
      ],
      "affected_files_or_behavior": [
        "scripts/issue47_engineering_wakeup.py",
        "scripts/collaboration_goal_entrypoint.py",
        "tests/control_plane/test_issue47_engineering_wakeup.py"
      ],
      "required_resolution": "Suppress every already-launched same key including FAILED, fail closed on unknown state, and preserve append-only dispatch history. Any retry must be explicit, bounded, charged and backoff-aware.",
      "verification_method": "Non-model restart tests must cover FAILED, unknown status, exact retry authority, append-only history, backoff and quota preservation.",
      "status": "FIXED_PENDING_REVIEW",
      "resolution_evidence": [
        "output/control-plane/verification-20261031T114907+0800.json#control_plane_negative_tests; scripts/issue47_engineering_wakeup.py; tests/control_plane/test_issue47_engineering_wakeup.py"
      ]
    },
    {
      "finding_id": "R-006",
      "severity": "MAJOR",
      "authority_source": "Review scope requiring deployed-byte and exact candidate identity binding; review request acceptance criterion 1",
      "expected_behavior": "The model-launching code must be the reviewed and attested bytes, the runtime candidate must match admission, and continuation must be bound to the reserved key, action and provider.",
      "observed_behavior": "The verified gate runs from the deployment repository, but continuation executes runtime/scripts/codex_orchestrator.py without hash or candidate identity verification. Generic resume --max-steps 1 is not constrained to the reserved key, action or provider.",
      "evidence": [
        "External reviewer finding: finding-continuation-bytes-and-action-unbound",
        "scripts/collaboration_goal_entrypoint.py:392-406",
        "scripts/issue47_engineering_wakeup.py:364-370",
        "Canonical GitHub record: https://github.com/joannalee20050914/KGnote-public/pull/49#issuecomment-6538538869"
      ],
      "affected_files_or_behavior": [
        "scripts/collaboration_goal_entrypoint.py",
        "scripts/issue47_engineering_wakeup.py",
        "scripts/codex_orchestrator.py",
        "runtime candidate and continuation identity"
      ],
      "required_resolution": "Verify runtime commit, fingerprint and continuation bytes against the reviewed receipt and make continuation prove the exact reserved dispatch key, action and provider before any model launch.",
      "verification_method": "Non-model tests must reject runtime HEAD/fingerprint/hash drift and any mismatch of dispatch key, action, provider or continuation bytes.",
      "status": "FIXED_PENDING_REVIEW",
      "resolution_evidence": [
        "output/control-plane/verification-20261031T114907+0800.json#control_plane_negative_tests; scripts/collaboration_goal_entrypoint.py; scripts/codex_orchestrator.py; tests/control_plane/test_codex_orchestrator.py"
      ]
    }
  ],
  "verified_requirements": [
    "Review 002 findings R-001, R-002 and R-003"
  ],
  "unverified_requirements": [
    "v2026-10-31.4 resource_policy cumulative accounting",
    "same-key restart suppression after FAILED",
    "exact reviewed continuation byte/action/provider binding"
  ],
  "human_decisions_required": [],
  "human_gates_preserved": [
    "ISSUE47-ENGINEERING-GOAL-OWNER-APPROVAL",
    "ISSUE47-EXACT-PRODUCT-GOAL-CANARY-APPROVAL",
    "ISSUE47-FINAL-OWNER-ACCEPTANCE-AND-GO-LIVE",
    "ISSUE47-CLAUDE-PRIMARY-CODEX-REVIEW-PROOF",
    "O2-V4-FORMAL-RUNTIME-PROTECTION",
    "D2-T14-FINAL-HUMAN-ACCEPTANCE",
    "PA-HUMAN-1",
    "NS-HUMAN-SMOKE"
  ],
  "reviewed_at": "2026-10-31T11:40:27.336709+08:00"
}
```
<!-- END KGNOTE REVIEW RESULT JSON -->
