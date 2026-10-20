"""Deterministic, local-only building blocks for the Obsidian Personal Alpha."""

from .preview import (
    PERSONAL_ALPHA_PREVIEW_VERSION,
    PersonalAlphaPreview,
    PersonalAlphaPreviewError,
    build_learning_workspace_preview,
)
from .learner_projection import (
    LEARNER_PROJECTION_VERSION,
    LearnerProjection,
    project_learner_workspace,
)
from .workspace import (
    PERSONAL_ALPHA_WORKSPACE_VERSION,
    PersonalAlphaMaterializationError,
    PersonalAlphaMaterializationResult,
    materialize_learning_workspace,
    read_back_manual_continuation,
    read_back_learning_workspace,
)

__all__ = [
    "PERSONAL_ALPHA_PREVIEW_VERSION",
    "PersonalAlphaPreview",
    "PersonalAlphaPreviewError",
    "build_learning_workspace_preview",
    "LEARNER_PROJECTION_VERSION",
    "LearnerProjection",
    "project_learner_workspace",
    "PERSONAL_ALPHA_WORKSPACE_VERSION",
    "PersonalAlphaMaterializationError",
    "PersonalAlphaMaterializationResult",
    "materialize_learning_workspace",
    "read_back_manual_continuation",
    "read_back_learning_workspace",
]
