#!/usr/bin/env python3
"""Run candidate control-plane tests while deferring only legacy remote-PR checks.

The O2 product checkout declares PLAN/STATUS non-authoritative before publication.
Two repository-integrity tests in the sealed successor therefore belong to the
downstream trusted GitHub read-back gate, not the local pre-publication gate.  This
runner requires both exact test identities to exist and runs every other discovered
control-plane test.  Any missing identity or attempted expansion fails closed.
"""
from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


DEFERRED_REMOTE_PUBLICATION_TESTS = (
    "test_codex_control.RepositoryIntegrityTests."
    "test_current_orchestrator_state_matches_plan_and_review_bus",
    "test_codex_control.RepositoryIntegrityTests."
    "test_fresh_agent_can_reconstruct_resume_state_from_repository_only",
)


def _flatten(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    tests: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            tests.extend(_flatten(item))
        else:
            tests.append(item)
    return tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    start = repo / "tests/control_plane"
    if not start.is_dir():
        print("O2 pre-publication control tests are unavailable", file=sys.stderr)
        return 2
    # Match the repository's established `unittest discover -s
    # tests/control_plane` semantics.  That directory is intentionally not a
    # package in the sealed product successor.
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(start))
    suite = unittest.defaultTestLoader.discover(str(start), pattern="test_*.py")
    tests = _flatten(suite)
    by_id = {test.id(): test for test in tests}
    missing = sorted(set(DEFERRED_REMOTE_PUBLICATION_TESTS) - set(by_id))
    if missing:
        print(
            "Expected legacy remote-publication tests are missing: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 2
    selected = unittest.TestSuite(
        test for test in tests if test.id() not in DEFERRED_REMOTE_PUBLICATION_TESTS
    )
    print(
        "DEFERRED_TO_TRUSTED_REMOTE_PUBLICATION_IDENTITY="
        + ",".join(DEFERRED_REMOTE_PUBLICATION_TESTS)
    )
    result = unittest.TextTestRunner(verbosity=2).run(selected)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
