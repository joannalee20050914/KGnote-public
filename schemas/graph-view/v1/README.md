# Graph view query and plan v1

This contract is a pure planning boundary over `kgnote.graph-read-model.v1`. An empty filter
array means “all available values”. A query either has no focus and a null hop depth, or names
an existing focus node and requests exactly 1, 2, or 3 hops.

Filters are applied before traversal. Space filtering keeps a Concept when it belongs to a
selected space and keeps a LearningEvent when at least one of its `concept_ids` belongs to a
selected space. A focus excluded by filters is rejected rather than silently forced visible.
Traversal treats retained links as direction-neutral for navigation; selected link records keep
their canonical source/target direction. With no focus, the whole filtered graph is selected.

The plan contains sorted IDs, not duplicated graph records. Evidence is collected from selected
nodes and links; Sources are then collected from that Evidence and selected LearningEvents.
An isolated focus or filter combination with no retained links is a successful plan with an
empty `link_ids` array. `excluded` gives one stable, precedence-ordered reason per omitted canvas
node/link. Snapshot and query digests bind the plan to exact inputs.

This version does not define layout, rendering, persistence, HTTP, search, UI state, mutation,
vault access, model access, or review scheduling.
