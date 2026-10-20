# Product and architecture decision queue

This file links unresolved reviewer questions to durable human decisions. It does not replace the existing KGnote authority/decision system.

<!-- BEGIN KGNOTE DECISIONS JSON -->
```json
{
  "schema_version": "kgnote.review-decisions.v1",
  "protocol_version": "kgnote.review-protocol.v1",
  "decisions": []
}
```
<!-- END KGNOTE DECISIONS JSON -->

Each future entry must contain `decision_id`, `question`, `why_existing_authority_is_insufficient`, `affected_requirements`, `available_options`, `observable_consequences`, `blocking_scope`, `linked_findings`, `status`, `selected_option`, `decided_by`, `decided_at`, and `authority_record`. For a decided item, `authority_record` is the new canonical artifact `docs/requirements/human-decisions/<decision_id>.md`; candidate-control files and pre-existing or non-canonical documents are invalid.
