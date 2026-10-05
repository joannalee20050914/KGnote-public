# One-answer assessment response v1

The reviewer receives one caller-supplied question, one user answer, the boolean fact that a hint
was or was not used, and one `kgnote.reviewer-context.v1` payload. It may return only `outcome` and
`correction`. Outcome is one of `CORRECT`, `PARTIAL`, `INCORRECT`, or
`INSUFFICIENT_EVIDENCE`. The adapter additionally enforces at most two sentences and 500 characters
for correction.

This is an evidence-grounded assessment of one answer, not a mastery claim. Question generation,
provider transport, consent, persistence, scheduling, and hint fading are separate boundaries.
