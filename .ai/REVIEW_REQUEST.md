# Current review request

Writer: Codex implementation agent. The JSON block is canonical; prose outside it is explanatory only.

<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->
```json
{"schema_version":"kgnote.review-request.v1","protocol_version":"kgnote.review-protocol.v1","review_id":"review-mainline-integration-20261020-001","goal_id":"GOAL-KGNOTE-MAINLINE-INTEGRATION-20261020","milestone_id":"MAINLINE-INTEGRATION-CANDIDATE","status":"IMPLEMENTING","author_role":"CODEX_IMPLEMENTER","base_revision":"827e4aa863fefea6f7d4a9e6120d5845bec3b9fd","candidate_revision":null,"candidate_fingerprint":null,"authoritative_specs":["docs/control-plane/AUTHORITY.md","docs/control-plane/AUTONOMOUS_EXTERNAL_REVIEW_CONTRACT.md",".ai/REVIEW_PROTOCOL.md","docs/PRODUCT_CONTRACT.md","docs/requirements/requirements.json","docs/requirements/scenarios.json","PLAN.md"],"changed_areas":["Main-based integration of the product foundation and Source Library","Current Ubuntu Claude review, Runner publication, Consumer and notification-only Work control plane"],"acceptance_criteria":["One non-stacked Draft integration PR is based directly on main","Product and Source Library deterministic verification passes","Old active PLAN, STATUS, review result and orchestrator snapshots are not imported","A new exact candidate receives Ubuntu Claude review before merge","main remains protected and requires GitHub approval"],"negative_requirements":["Do not merge or force-push main","Do not reuse PR #26 Round 5 PASS for this candidate","Do not restore ChatGPT Work per-round review","Do not clear Stop Marker or increase model budgets"],"validation_performed":[],"validation_results":[],"known_deviations":[],"known_uncertainties":["The exact integration candidate has not yet consumed the one remaining authorized Ubuntu Claude review round."],"reviewer_focus":["Product completeness versus PR #1 and PR #26","Removal of obsolete PR #22 Work-per-round behavior","Fail-closed GitHub writeback and Consumer identity checks"],"preserved_human_gates":["PA-HUMAN-1","NS-HUMAN-SMOKE","release_verified=false","GitHub required approval before main merge"],"requested_at":null,"authorized_human_decision_identities":["product owner"],"candidate_manifest":null}
```
<!-- END KGNOTE REVIEW REQUEST JSON -->

## Human-readable status

Review `review-mainline-integration-20261020-001` is `IMPLEMENTING`.
It has no active candidate binding and cannot be interpreted as a review request or PASS.
Codex must complete deterministic verification before issuing this request.
