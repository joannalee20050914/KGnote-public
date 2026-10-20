# Import review preview v1

This is the human inspection layer between accepted extraction output and canonical apply.
It resolves stable IDs to candidate names, makes Edge direction explicit, and includes exact
numbered source lines for every Evidence-backed relationship.

`linking_phrase` is deliberately `null` with `linking_phrase_status: not_proposed` because the
current extraction contract produces canonical relation types, not reviewed learner-facing
Teaching Propositions. Renderers must not invent that missing phrase. `CONFLICT` and `REJECT`
items are copied into `blocking_items` and set `apply_blocked`.
