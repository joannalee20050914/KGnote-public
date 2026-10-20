# Guided edge review v1

`request.schema.json` binds one linking-phrase response to an exact learning unit, Source, graph
snapshot, and Edge. The browser does not send a question, canonical answer, Evidence list, locator,
or comparison outcome; the server reconstructs those fields from its configured, validated Guided
Map read model.

`record.schema.json` describes the append-only Markdown front matter. It preserves the exact
Teaching Proposition, supporting Evidence IDs and locators, focus question, response, hint use, and
factual phrase comparison. `matched_reviewed_phrase` means only string agreement with the reviewed
phrase; it is not a mastery or understanding claim.
