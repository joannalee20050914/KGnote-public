"""Versioned boundary contracts."""

from .graph_read_model import (
    GraphReadModelValidationError,
    SCHEMA_VERSION as GRAPH_READ_MODEL_SCHEMA_VERSION,
    validate_graph_read_model,
)
from .guided_map import (
    GuidedMapValidationError,
    READ_MODEL_SCHEMA_VERSION as GUIDED_MAP_READ_MODEL_SCHEMA_VERSION,
    SPEC_SCHEMA_VERSION as GUIDED_MAP_SPEC_SCHEMA_VERSION,
    validate_guided_map_read_model,
    validate_guided_map_spec,
)
from .reader import (
    APPLICATION_VERSION as READER_APPLICATION_VERSION,
    QUERY_VERSION as READER_QUERY_VERSION,
    ReaderValidationError,
    validate_reader_application_result,
    validate_reader_query,
)
from .linking_phrase import (
    CANDIDATE_SET_VERSION as LINKING_PHRASE_CANDIDATE_SET_VERSION,
    CONTEXT_VERSION as LINKING_PHRASE_CONTEXT_VERSION,
    LinkingPhraseCandidateResult,
    build_linking_phrase_candidates,
    validate_linking_phrase_context,
)
from .learning_note import (
    LEARNING_NOTE_VERSION,
    SAVE_REQUEST_VERSION as LEARNING_NOTE_SAVE_REQUEST_VERSION,
    LearningNoteValidationError,
    validate_learning_note,
    validate_learning_note_save,
)

__all__ = [
    "GRAPH_READ_MODEL_SCHEMA_VERSION",
    "GraphReadModelValidationError",
    "validate_graph_read_model",
    "GUIDED_MAP_READ_MODEL_SCHEMA_VERSION",
    "GUIDED_MAP_SPEC_SCHEMA_VERSION",
    "GuidedMapValidationError",
    "validate_guided_map_read_model",
    "validate_guided_map_spec",
    "READER_APPLICATION_VERSION",
    "READER_QUERY_VERSION",
    "ReaderValidationError",
    "validate_reader_application_result",
    "validate_reader_query",
    "LINKING_PHRASE_CANDIDATE_SET_VERSION",
    "LINKING_PHRASE_CONTEXT_VERSION",
    "LinkingPhraseCandidateResult",
    "build_linking_phrase_candidates",
    "validate_linking_phrase_context",
    "LEARNING_NOTE_VERSION",
    "LEARNING_NOTE_SAVE_REQUEST_VERSION",
    "LearningNoteValidationError",
    "validate_learning_note",
    "validate_learning_note_save",
]
