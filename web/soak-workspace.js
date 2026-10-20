export function makeId(prefix, uuid = () => crypto.randomUUID()) {
  return `${prefix}_${uuid().replaceAll("-", "").toLowerCase()}`;
}

export function buildExposureRequest({eventId, sessionId, unitId, item, kind, occurredAt}) {
  const allowed = new Set(["presented", "answer_revealed", "skipped", "encountered", "recognized", "applied"]);
  if (!allowed.has(kind) || !item?.item_id || !item?.concept_id || !Array.isArray(item.source_refs) || !item.source_refs.length) return {status:"rejected"};
  return {status:"ready", request:{schema_version:"kgnote.exposure-save-request.v1", event_id:eventId, exposure_session_id:sessionId, learning_unit_id:unitId, item_id:item.item_id, concept_id:item.concept_id, kind, occurred_at:occurredAt, source_refs:[...item.source_refs]}};
}

export function soakHasAssessmentFields(value) {
  return ["outcome", "correct", "incorrect", "score", "attempt_id", "raw_response"].some(key => Object.hasOwn(value, key));
}

export function supportProgression(item) {
  const allowed = new Set(["high_similarity", "cued", "changed_context", "explanation", "application"]);
  const progression = item?.support_progression;
  if (!Array.isArray(progression) || progression.length < 2 || progression.length > 8 || new Set(progression.map(step=>step?.stage)).size !== progression.length) return {status:"rejected"};
  for (const step of progression) {
    if (!allowed.has(step?.stage) || typeof step.label !== "string" || !step.label.trim() || typeof step.content !== "string" || !step.content.trim() || typeof step.response_expected !== "boolean") return {status:"rejected"};
  }
  return {status:"ready", steps:progression.map(step=>structuredClone(step))};
}
