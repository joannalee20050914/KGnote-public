const CONFUSION_RELATION = "confused_with";

function rejected(code) {
  return {status: "rejected", problem: {code}};
}

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b));
}

function eventOrder(left, right) {
  if (left.occurred_at !== right.occurred_at) {
    if (left.occurred_at === null) return 1;
    if (right.occurred_at === null) return -1;
    return right.occurred_at.localeCompare(left.occurred_at);
  }
  return left.id.localeCompare(right.id);
}

function copy(value) {
  return structuredClone(value);
}

export function buildNodeDetails(view, nodeId) {
  if (!view || view.schema_version !== "kgnote.graph-read-model.v1" || typeof nodeId !== "string") {
    return rejected("invalid_detail_request");
  }
  if (![view.nodes, view.links, view.evidence, view.sources].every(Array.isArray)) {
    return rejected("invalid_detail_view");
  }

  const nodes = new Map();
  const evidence = new Map();
  const sources = new Map();
  for (const node of view.nodes) {
    if (!node?.id || nodes.has(node.id)) return rejected("invalid_detail_node");
    nodes.set(node.id, node);
  }
  for (const item of view.evidence) {
    if (!item?.id || evidence.has(item.id)) return rejected("invalid_detail_evidence");
    evidence.set(item.id, item);
  }
  for (const source of view.sources) {
    if (!source?.id || sources.has(source.id)) return rejected("invalid_detail_source");
    sources.set(source.id, source);
  }

  for (const candidate of view.nodes) {
    if (!Array.isArray(candidate.evidence_ids) || candidate.evidence_ids.some((id) => !evidence.has(id))) {
      return rejected("missing_detail_evidence");
    }
    if (candidate.kind === "learning_event" && (
      !Array.isArray(candidate.concept_ids) || candidate.concept_ids.some((id) => !nodes.has(id))
    )) return rejected("invalid_detail_event_reference");
    if (candidate.kind === "learning_event" && (
      !Array.isArray(candidate.source_ids) || candidate.source_ids.some((id) => !sources.has(id))
    )) return rejected("missing_detail_source");
  }
  if ([...evidence.values()].some((item) => !sources.has(item.source_id))) return rejected("missing_detail_source");

  const node = nodes.get(nodeId);
  if (!node) return rejected("unknown_detail_node");
  const incidentLinks = view.links.filter((link) => link?.source_id === nodeId || link?.target_id === nodeId);
  if (view.links.some((link) => !link || !nodes.has(link.source_id) || !nodes.has(link.target_id) ||
      !Array.isArray(link.evidence_ids) || link.evidence_ids.some((id) => !evidence.has(id)))) {
    return rejected("invalid_detail_link");
  }

  const directEvidenceIds = Array.isArray(node.evidence_ids) ? node.evidence_ids : [];
  const incidentEvidenceIds = incidentLinks.flatMap((link) => link.evidence_ids);
  const evidenceIds = uniqueSorted([...directEvidenceIds, ...incidentEvidenceIds]);
  if (evidenceIds.some((id) => !evidence.has(id))) return rejected("missing_detail_evidence");
  const evidenceItems = evidenceIds.map((id) => evidence.get(id));
  const sourceIds = uniqueSorted([
    ...(Array.isArray(node.source_ids) ? node.source_ids : []),
    ...evidenceItems.map((item) => item.source_id),
  ]);
  if (sourceIds.some((id) => !sources.has(id))) return rejected("missing_detail_source");

  const relatedEvents = (node.kind === "concept"
    ? view.nodes.filter((candidate) => candidate.kind === "learning_event" && (
      candidate.concept_ids?.includes(nodeId) || incidentLinks.some((link) => link.edge_class === "learning" && link.source_id === candidate.id)
    ))
    : [node]
  ).slice().sort(eventOrder);

  const confusionEvents = relatedEvents.filter((event) => event.event_type === "confusion");
  const confusionLinks = incidentLinks.filter((link) => link.edge_class === "learning" && link.relation === CONFUSION_RELATION);
  const confusionEvidenceIds = uniqueSorted([
    ...confusionEvents.flatMap((event) => event.evidence_ids ?? []),
    ...confusionLinks.flatMap((link) => link.evidence_ids),
  ]);
  if (confusionEvidenceIds.some((id) => !evidence.has(id))) return rejected("missing_confusion_evidence");

  const detail = {
    id: node.id,
    kind: node.kind,
    label: node.label,
    evidence: evidenceItems.map(copy),
    sources: sourceIds.map((id) => copy(sources.get(id))),
    history: relatedEvents.map(copy),
    known_confusion: {
      events: confusionEvents.map(copy),
      links: confusionLinks.slice().sort((a, b) => a.id.localeCompare(b.id)).map(copy),
      evidence: confusionEvidenceIds.map((id) => copy(evidence.get(id))),
    },
  };
  if (node.kind === "concept") {
    Object.assign(detail, {summary: node.summary, status: node.status, spaces: [...node.spaces]});
  } else if (node.kind === "learning_event") {
    Object.assign(detail, {
      event_type: node.event_type,
      context: node.context,
      occurred_at: node.occurred_at,
      concepts: node.concept_ids.map((id) => nodes.get(id)).filter(Boolean).map(({id, label}) => ({id, label})),
    });
  } else {
    return rejected("invalid_detail_node_kind");
  }
  return {status: "ready", detail};
}
