export function newAttemptId(randomUUID = crypto.randomUUID.bind(crypto)) {
  return `attempt_${randomUUID().replaceAll("-", "")}`;
}

export function buildAttemptRequest({attemptId, item, startedAt, response, confidence = null, hintEvents = [], state = "draft", submittedAt = null, outcome = null, entryKind = "voluntary_practice", dueId = null}) {
  if (!attemptId || !item || typeof response !== "string") return {status: "rejected", problem: {code: "invalid_attempt_input"}};
  const submitted = state === "submitted";
  return {status: "ready", request: {
    schema_version: "kgnote.attempt-save-request.v1",
    attempt_id: attemptId,
    review_item_id: item.item_id,
    item_revision: item.revision,
    learning_unit_id: item.learning_unit_id,
    activity_type: item.activity_type,
    state,
    started_at: startedAt,
    submitted_at: submitted ? submittedAt : null,
    raw_response: response,
    confidence: confidence || null,
    hint_events: structuredClone(hintEvents),
    support_state: hintEvents.length ? "hinted" : "unassisted",
    answer_exposure_state: submitted ? "revealed_after_submission" : "hidden",
    outcome: submitted ? outcome : null,
    correction_feedback: submitted ? "提交後依 rubric 與 Evidence 進行人工自評；系統未以逐字匹配判定理解。" : null,
    entry_context: {route: "/practice.html", from_route: entryKind === "scheduled_review" ? "/review.html" : "/learn.html", entry_kind: entryKind, due_id: dueId},
    source_refs: structuredClone(item.source_refs),
    claim_refs: [structuredClone(item.claim_ref)],
    evidence_refs: structuredClone(item.evidence_refs),
  }};
}

export function safePracticeItem(item) {
  const forbidden = ["canonical_answer", "canonical_phrase", "canonical_sentence", "evidence", "source_excerpt", "linking_phrase"];
  return forbidden.every(key => !(key in item));
}

export function groupedItems(items) {
  return {
    relation_recall: items.filter(item => item.activity_type === "relation_recall"),
    free_explanation: items.filter(item => item.activity_type === "free_explanation"),
    application_prediction: items.filter(item => item.activity_type === "application_prediction"),
    distinction: items.filter(item => item.activity_type === "distinction"),
  };
}
