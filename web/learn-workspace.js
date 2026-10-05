function rejected(code) { return {status: "rejected", problem: {code}}; }

export function buildLearnWorkspace(mapModel, overlay, sourceText, structure = null, readingAssist = null) {
  if (mapModel?.schema_version !== "kgnote.guided-map-read-model.v1") return rejected("invalid_map");
  if (overlay?.schema_version !== "kgnote.claim-review-overlay.v1") return rejected("invalid_overlay");
  if (overlay.learning_unit_id !== mapModel.learning_unit.id || overlay.graph_snapshot_sha256 !== mapModel.graph_snapshot_sha256) return rejected("stale_overlay");
  if (typeof sourceText !== "string" || !sourceText) return rejected("invalid_source");
  const concepts = new Map(mapModel.concepts.map(item => [item.id, structuredClone(item)]));
  const evidence = new Map(mapModel.evidence.map(item => [item.id, structuredClone(item)]));
  const reviews = new Map(overlay.reviews.map(item => [item.claim_id, structuredClone(item)]));
  if (reviews.size !== overlay.reviews.length) return rejected("duplicate_claim_review");
  const propositions = mapModel.propositions.map(item => ({
    ...structuredClone(item),
    sentence: `${item.subject_label} ${item.linking_phrase} ${item.object_label}`,
    evidence: item.evidence_ids.map(id => evidence.get(id)).filter(Boolean),
    review: reviews.get(item.edge_id) ?? null,
  }));
  const groups = [...mapModel.groups].sort((a, b) => a.order - b.order).map(group => ({
    ...structuredClone(group), concepts: group.concept_ids.map(id => concepts.get(id)).filter(Boolean),
  }));
  if (structure !== null) {
    if (structure?.schema_version !== "kgnote.learning-structure.v1" || structure.learning_unit_id !== mapModel.learning_unit.id) return rejected("invalid_structure");
    const nodeIds = new Set(structure.nodes?.map(item => item.id));
    if (!Array.isArray(structure.nodes) || nodeIds.size !== structure.nodes.length || structure.nodes.filter(item => item.parent_id === null).length !== 1 || structure.nodes.some(item => item.parent_id !== null && !nodeIds.has(item.parent_id))) return rejected("invalid_structure");
  }
  if (readingAssist !== null && (readingAssist?.schema_version !== "kgnote.reading-assist.v1" || readingAssist.learning_unit_id !== mapModel.learning_unit.id)) return rejected("invalid_reading_assist");
  return {
    status: "ready", source: structuredClone(mapModel.source), source_text: sourceText,
    learning_unit: structuredClone(mapModel.learning_unit), groups, concepts: [...concepts.values()],
    propositions, evidence: [...evidence.values()], structure: structure ? structuredClone(structure) : null,
    reading_assist: readingAssist ? structuredClone(readingAssist) : {glosses: [], prior_knowledge: [], prior_encounters: []},
  };
}

export function structureChildren(workspace, parentId = null) {
  if (!workspace.structure) return [];
  return workspace.structure.nodes.filter(item => item.parent_id === parentId).sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
}

export function glossesForScope(workspace, node) {
  if (!node?.source_anchors || !workspace?.reading_assist?.glosses) return [];
  return workspace.reading_assist.glosses.filter(gloss => node.source_anchors.some(anchor => {
    const range = /^L(\d+)-L(\d+)$/.exec(anchor.locator?.value ?? "");
    const location = /^L(\d+)-L\d+$/.exec(gloss.locator?.value ?? "");
    return range && location && Number(location[1]) >= Number(range[1]) && Number(location[1]) <= Number(range[2]);
  }));
}

export function claimsForEvidence(workspace, evidenceId) {
  if (!workspace.evidence.some(item => item.id === evidenceId)) return rejected("unknown_evidence");
  const claims = workspace.propositions
    .filter(item => item.evidence_ids.includes(evidenceId))
    .map(item => ({claim_id: item.edge_id, sentence: item.sentence, teaching_answer_status: item.review?.teaching_answer_status ?? "blocked"}))
    .sort((left, right) => left.claim_id.localeCompare(right.claim_id));
  return {status: "ready", evidence_id: evidenceId, claims};
}

export function conceptDetail(workspace, conceptId) {
  const concept = workspace.concepts.find(item => item.id === conceptId);
  if (!concept) return rejected("unknown_concept");
  const claims = workspace.propositions.filter(item => item.subject_concept_id === conceptId || item.object_concept_id === conceptId);
  const evidenceIds = new Set([...concept.evidence_ids, ...claims.flatMap(item => item.evidence_ids)]);
  return {
    status: "ready", concept, claims,
    evidence: workspace.evidence.filter(item => evidenceIds.has(item.id)),
  };
}

export function sourceLines(sourceText, locator) {
  const match = /^L(\d+)-L(\d+)$/.exec(locator?.value ?? "");
  if (!match) return [];
  const lines = sourceText.split("\n");
  return lines.slice(Number(match[1]) - 1, Number(match[2])).map((text, offset) => ({number: Number(match[1]) + offset, text}));
}
