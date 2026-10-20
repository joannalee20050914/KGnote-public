# Attempt v1

`kgnote.attempt.v1` is the machine-managed record for one learner-started
activity. A due item or merely opening Practice does not create it. A draft is
not an incorrect answer. Retry uses a new client-generated `attempt_id`.

The local adapter writes one JSON file per attempt with same-directory atomic
replace. A submitted attempt is immutable: the exact same client payload is an
idempotent read-back, while a changed submitted payload is a conflict. Server
timestamps are audit fields, never identity.

Legacy `kgnote.guided-review-interaction.v1` records remain readable in their
existing store and are not relabeled as closed-book Attempt v1 records.
