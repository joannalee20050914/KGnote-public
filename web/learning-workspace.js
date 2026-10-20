import {buildExpertSkeleton} from "./guided-map.js";

function rejected(code) {
  return {status: "rejected", problem: {code}};
}

function sameValues(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
}

export function projectGraphFromGuidedMap(mapModel, space = "guided-review") {
  return {
    schema_version: "kgnote.graph-read-model.v1",
    snapshot_sha256: mapModel.graph_snapshot_sha256,
    nodes: mapModel.concepts.map((concept) => ({
      id: concept.id,
      kind: "concept",
      label: concept.label,
      aliases: structuredClone(concept.aliases),
      spaces: [space],
      summary: concept.summary,
      status: concept.status,
      evidence_ids: structuredClone(concept.evidence_ids),
    })),
    links: mapModel.propositions.map((proposition) => ({
      id: proposition.edge_id,
      source_id: proposition.subject_concept_id,
      target_id: proposition.object_concept_id,
      relation: proposition.canonical_relation,
      edge_class: "canonical",
      confidence: "high",
      evidence_ids: structuredClone(proposition.evidence_ids),
    })),
    evidence: structuredClone(mapModel.evidence),
    sources: [structuredClone(mapModel.source)],
    filter_facets: {
      node_kinds: ["concept"],
      edge_classes: ["canonical"],
      relations: [...new Set(mapModel.propositions.map(({canonical_relation}) => canonical_relation))].sort(),
      spaces: [space],
    },
  };
}

export function buildLearningWorkspace(mapModel, graphModel, sourceText) {
  const skeleton = buildExpertSkeleton(mapModel, sourceText);
  if (skeleton.status !== "ready") return skeleton;
  if (graphModel?.schema_version !== "kgnote.graph-read-model.v1") return rejected("invalid_graph_version");
  if (graphModel.snapshot_sha256 !== mapModel.graph_snapshot_sha256) return rejected("cross_view_snapshot_drift");

  const graphConcepts = new Map((graphModel.nodes ?? []).filter(({kind}) => kind === "concept").map((node) => [node.id, node]));
  const graphLinks = new Map((graphModel.links ?? []).map((link) => [link.id, link]));
  const graphEvidence = new Map((graphModel.evidence ?? []).map((item) => [item.id, item]));
  const graphSources = new Map((graphModel.sources ?? []).map((item) => [item.id, item]));
  if (graphConcepts.size !== mapModel.concepts.length || graphLinks.size !== mapModel.propositions.length) return rejected("cross_view_collection_drift");

  for (const concept of mapModel.concepts) {
    const graphConcept = graphConcepts.get(concept.id);
    if (!graphConcept || graphConcept.label !== concept.label || graphConcept.summary !== concept.summary || !sameValues(graphConcept.evidence_ids, concept.evidence_ids)) {
      return rejected("cross_view_concept_drift");
    }
  }
  for (const proposition of mapModel.propositions) {
    const link = graphLinks.get(proposition.edge_id);
    if (!link || link.source_id !== proposition.subject_concept_id || link.target_id !== proposition.object_concept_id || link.relation !== proposition.canonical_relation || !sameValues(link.evidence_ids, proposition.evidence_ids)) {
      return rejected("cross_view_edge_drift");
    }
  }
  for (const item of mapModel.evidence) {
    const graphItem = graphEvidence.get(item.id);
    if (!graphItem || graphItem.source_id !== item.source_id || graphItem.proposition !== item.proposition || !sameValues(graphItem.locator, item.locator)) return rejected("cross_view_evidence_drift");
  }
  const graphSource = graphSources.get(mapModel.source.id);
  if (!graphSource || graphSource.label !== mapModel.source.label || graphSource.content_sha256 !== mapModel.source.content_sha256) return rejected("cross_view_source_drift");

  return {
    status: "ready",
    graph_snapshot_sha256: mapModel.graph_snapshot_sha256,
    learning_unit: skeleton.learning_unit,
    source: skeleton.source,
    source_text: sourceText,
    groups: skeleton.groups,
    concepts: structuredClone(mapModel.concepts),
    propositions: skeleton.propositions,
    evidence: structuredClone(mapModel.evidence),
    graph: {nodes: structuredClone(graphModel.nodes), links: structuredClone(graphModel.links)},
  };
}

function baseSelection(workspace) {
  return {source_id: workspace.source.id, focus_question: workspace.learning_unit.focus_question, concept_id: null, edge_id: null, evidence_ids: []};
}

export function selectConcept(workspace, conceptId) {
  const concept = workspace.concepts.find(({id}) => id === conceptId);
  if (!concept) return rejected("unknown_selection_concept");
  return {status: "ready", selection: {...baseSelection(workspace), concept_id: concept.id, evidence_ids: [...concept.evidence_ids]}};
}

export function selectEdge(workspace, edgeId) {
  const proposition = workspace.propositions.find((item) => item.edge_id === edgeId);
  if (!proposition) return rejected("unknown_selection_edge");
  return {status: "ready", selection: {...baseSelection(workspace), concept_id: proposition.subject_concept_id, edge_id: proposition.edge_id, evidence_ids: [...proposition.evidence_ids]}};
}

export function selectEvidence(workspace, evidenceId) {
  if (!workspace.evidence.some(({id}) => id === evidenceId)) return rejected("unknown_selection_evidence");
  const candidateEdgeIds = workspace.propositions
    .filter(({evidence_ids}) => evidence_ids.includes(evidenceId))
    .map(({edge_id}) => edge_id)
    .sort();
  return {
    status: "ready",
    selection: {...baseSelection(workspace), evidence_ids: [evidenceId], candidate_edge_ids: candidateEdgeIds},
  };
}

export function evidenceLineNumbers(workspace, selection) {
  const selected = new Set(selection.evidence_ids);
  const numbers = new Set();
  for (const item of workspace.evidence.filter(({id}) => selected.has(id))) {
    const match = /^L(\d+)-L(\d+)$/.exec(item.locator.value);
    if (!match) continue;
    for (let line = Number(match[1]); line <= Number(match[2]); line += 1) numbers.add(line);
  }
  return [...numbers].sort((a, b) => a - b);
}

export function buildLinkingPhraseExercise(workspace, edgeId) {
  const proposition = workspace.propositions.find((item) => item.edge_id === edgeId);
  if (!proposition) return rejected("unknown_exercise_edge");
  return {
    status: "ready",
    exercise: {
      edge_id: proposition.edge_id,
      subject_label: proposition.subject_label,
      object_label: proposition.object_label,
      prompt: `${proposition.subject_label}＿＿＿＿${proposition.object_label}`,
      hint: `關係詞的第一個字是「${[...proposition.linking_phrase][0]}」，共 ${[...proposition.linking_phrase].length} 個字。`,
      canonical_phrase: proposition.linking_phrase,
      canonical_sentence: proposition.sentence,
      evidence: structuredClone(proposition.evidence),
    },
  };
}

export function compareLinkingPhrase(exercise, answer) {
  if (!exercise || typeof answer !== "string" || !answer.trim() || answer.length > 80) return rejected("invalid_exercise_answer");
  const normalize = (value) => value.trim().replace(/\s+/g, " ");
  return {
    status: "ready",
    comparison: {
      edge_id: exercise.edge_id,
      matches_reviewed_phrase: normalize(answer) === normalize(exercise.canonical_phrase),
      response: answer.trim(),
      canonical_phrase: exercise.canonical_phrase,
      canonical_sentence: exercise.canonical_sentence,
      evidence: structuredClone(exercise.evidence),
    },
  };
}

export function buildGuidedReviewRequest(workspace, comparison, hintUsed) {
  if (!workspace || !comparison || typeof hintUsed !== "boolean") return rejected("invalid_guided_review_context");
  if (!workspace.propositions.some(({edge_id}) => edge_id === comparison.edge_id)) return rejected("stale_guided_review_edge");
  if (typeof comparison.response !== "string" || !comparison.response.trim()) return rejected("invalid_guided_review_response");
  return {
    status: "ready",
    request: {
      schema_version: "kgnote.guided-review-request.v1",
      learning_unit_id: workspace.learning_unit.id,
      source_id: workspace.source.id,
      graph_snapshot_sha256: workspace.graph_snapshot_sha256,
      edge_id: comparison.edge_id,
      response: comparison.response,
      hint_used: hintUsed,
    },
  };
}
