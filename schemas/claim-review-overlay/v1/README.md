# Claim review overlay v1

This snapshot-bound overlay reviews learner-facing claims without modifying the
immutable Source or the legacy Guided Map fixture. A practice item is eligible
only when its exact proposition digest matches an overlay review whose
`factual_status` is `verified` or `corrected` and whose
`teaching_answer_status` is `ready`.

`needs_revision`, stale, missing, or malformed entries remain readable in Learn
but fail closed for Practice.
