# KGnote Product Goal v1 schemas

These schemas describe the dormant B-scheme Product Goal contract. They do not
create Product Goal authority. Authority exists only after the Mac Runner reads
back an exact Owner-authored GitHub Issue transition for the goal/version/spec
digest tuple.

- `goal-spec.schema.json`: immutable scope, permissions, dependencies,
  resources, completion rules, obligations and planned Work Items.
- `github-authority-record.schema.json`: one exact GitHub Owner lifecycle
  transition (`APPROVE`, `PAUSE`, `RESUME`, `REVOKE`, `ACCEPT`, or `CLOSE`).
- `runner-state.schema.json`: Mac Runner lifecycle projection. Compatibility
  fields are aliases, never a second authority source.
- `ledger-event.schema.json`: append-only hash-chained accounting event. Model
  attempts, usage, review verdicts, publication and product progress use
  different event types.

The Codex App Goal/thread identity may be retained as non-authoritative
provenance. It must never populate `authority_record` or drive a Product Goal
lifecycle transition.
