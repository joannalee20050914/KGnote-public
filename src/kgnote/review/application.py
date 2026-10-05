"""Explicit canonical-store boundary for one evidence-grounded reviewer context."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Literal

from kgnote.visualization import load_graph_view

from .context import build_reviewer_context


REVIEWER_CONTEXT_APPLICATION_VERSION = "kgnote.reviewer-context-application.v1"


@dataclass(frozen=True)
class ReviewerContextApplicationProblem:
    component: Literal["graph", "context"]
    code: str
    path: tuple[object, ...] = ()


@dataclass(frozen=True, repr=False)
class ReviewerContextApplicationResult:
    status: Literal["ready", "rejected"]
    _response_json: str = field(default="{}", repr=False)
    problem: ReviewerContextApplicationProblem | None = None

    @property
    def response(self) -> dict[str, Any]:
        return json.loads(self._response_json)

    def __repr__(self) -> str:
        return f"ReviewerContextApplicationResult(status={self.status!r}, problem={self.problem!r})"


def _result(payload, problem=None):
    return ReviewerContextApplicationResult(
        payload["status"],
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        problem,
    )


def _reject(component, code, path=()):
    problem = ReviewerContextApplicationProblem(component, code, tuple(path))
    return _result({
        "schema_version": REVIEWER_CONTEXT_APPLICATION_VERSION,
        "status": "rejected",
        "problem": {"component": component, "code": code, "path": list(path)},
    }, problem)


def load_reviewer_context(
    root: str | os.PathLike[str], concept_id: str,
) -> ReviewerContextApplicationResult:
    """Read one explicit store and materialize context for one caller-selected Concept."""

    if not isinstance(concept_id, str) or not concept_id:
        return _reject("context", "invalid_concept_id")
    graph = load_graph_view(root)
    if graph.status != "ready":
        problem = graph.problem
        return _reject("graph", problem.code if problem else "graph_rejected", problem.path if problem else ())
    projected = build_reviewer_context(graph.response["view"], concept_id)
    if projected.status != "ready":
        problem = projected.problem
        return _reject("context", problem.code if problem else "context_rejected", problem.path if problem else ())
    return _result({
        "schema_version": REVIEWER_CONTEXT_APPLICATION_VERSION,
        "status": "ready",
        "context": projected.context,
    })
