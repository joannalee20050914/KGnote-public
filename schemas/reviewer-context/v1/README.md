# Reviewer context v1

This contract is the bounded read-only input to the Phase 4 reviewer. The caller selects exactly
one Concept. The projector includes its canonical summary/status/spaces, direct and incident-link
Evidence, direction-preserving one-hop nodes and links, supporting Source metadata, and only prior
confusion represented by an explicit `confusion` LearningEvent or `confused_with` learning link.

Question, exposure, explanation, encountered, and unresolved soft association records are not
promoted to confusion or understanding. Raw Markdown, absolute paths, provider credentials,
proficiency scores, question generation, model calls, scheduling, and canonical writes are outside
this contract.
