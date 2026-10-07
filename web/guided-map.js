const MODEL_VERSION = "kgnote.guided-map-read-model.v1";
const LINE_RANGE = /^L([1-9]\d*)-L([1-9]\d*)$/;

function rejected(code) {
  return {status: "rejected", problem: {code}};
}

function unique(values) {
  return new Set(values).size === values.length;
}

function lineRange(locator) {
  if (locator?.kind !== "line_range") return null;
  const match = LINE_RANGE.exec(locator.value ?? "");
  if (!match) return null;
  const start = Number(match[1]);
  const end = Number(match[2]);
  return end >= start ? {start, end} : null;
}

export function teachingSentence(proposition) {
  return `${proposition.subject_label} ${proposition.linking_phrase} ${proposition.object_label}`;
}

export function excerptForLocator(sourceText, locator) {
  const range = lineRange(locator);
  if (typeof sourceText !== "string" || range === null) return rejected("invalid_source_locator");
  const {start, end} = range;
  const lines = sourceText.split("\n");
  if (end < start || end > lines.length) return rejected("invalid_source_locator");
  return {
    status: "ready",
    excerpt: lines.slice(start - 1, end).map((text, offset) => ({number: start + offset, text})),
  };
}

export function validateGuidedMap(model) {
  if (!model || model.schema_version !== MODEL_VERSION) return rejected("invalid_guided_map_version");
  const collections = ["groups", "concepts", "propositions", "evidence"];
  if (collections.some((key) => !Array.isArray(model[key]) || model[key].length === 0)) return rejected("invalid_guided_map_shape");
  if (!model.learning_unit?.focus_question || !model.source?.id || !model.graph_snapshot_sha256) return rejected("invalid_guided_map_identity");

  for (const key of collections) {
    if (model[key].some(({id, edge_id}) => typeof (id ?? edge_id) !== "string")) return rejected("invalid_guided_map_id");
    const ids = model[key].map(({id, edge_id}) => id ?? edge_id);
    if (!unique(ids)) return rejected("duplicate_guided_map_id");
  }

  const concepts = new Map(model.concepts.map((concept) => [concept.id, concept]));
  const evidence = new Map(model.evidence.map((item) => [item.id, item]));
  const groupIds = new Set(model.groups.map(({id}) => id));
  if (model.groups.some(({order}, index) => order !== index + 1)) return rejected("invalid_group_order");
  if (model.groups.some(({concept_ids}) => !Array.isArray(concept_ids) || concept_ids.some((id) => !concepts.has(id)))) return rejected("invalid_group_reference");
  if (model.concepts.some(({id, group_id}) => groupIds.has(id) || !groupIds.has(group_id))) return rejected("invalid_concept_group");

  for (const proposition of model.propositions) {
    const subject = concepts.get(proposition.subject_concept_id);
    const object = concepts.get(proposition.object_concept_id);
    if (!subject || !object) return rejected("invalid_proposition_concept");
    if (subject.label !== proposition.subject_label || object.label !== proposition.object_label) return rejected("proposition_label_drift");
    if (!proposition.linking_phrase?.trim() || proposition.review_status !== "accepted") return rejected("invalid_teaching_proposition");
    if (!Array.isArray(proposition.evidence_ids) || !proposition.evidence_ids.length || proposition.evidence_ids.some((id) => !evidence.has(id))) return rejected("invalid_proposition_evidence");
  }
  if (model.evidence.some((item) => item.review_status !== "accepted" || item.source_id !== model.source.id || lineRange(item.locator) === null)) {
    return rejected("invalid_evidence");
  }
  return {status: "ready"};
}

export function buildExpertSkeleton(model, sourceText) {
  const validation = validateGuidedMap(model);
  if (validation.status !== "ready") return validation;
  const concepts = new Map(model.concepts.map((concept) => [concept.id, concept]));
  const evidence = new Map(model.evidence.map((item) => [item.id, item]));
  const groups = model.groups.map((group) => ({
    ...structuredClone(group),
    concepts: group.concept_ids.map((id) => structuredClone(concepts.get(id))),
  }));
  const propositions = [];
  for (const proposition of model.propositions) {
    const items = proposition.evidence_ids.map((id) => {
      const item = evidence.get(id);
      const excerpt = excerptForLocator(sourceText, item.locator);
      if (excerpt.status !== "ready") return null;
      return {...structuredClone(item), source_excerpt: excerpt.excerpt};
    });
    if (items.some((item) => item === null)) return rejected("source_locator_out_of_bounds");
    propositions.push({...structuredClone(proposition), sentence: teachingSentence(proposition), evidence: items});
  }
  return {status: "ready", learning_unit: structuredClone(model.learning_unit), source: structuredClone(model.source), groups, propositions};
}
