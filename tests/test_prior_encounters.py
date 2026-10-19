from __future__ import annotations

import copy
import unittest

from kgnote.learning import prior_encounters


class PriorEncounterTests(unittest.TestCase):
    def test_sc10_shared_concept_requires_real_other_unit_history(self) -> None:
        assist = {"glosses": [{"id":"gloss_shared_x","concept_ref":"concept_shared_x"}]}
        events = [
            {"event_id":"exposure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":"unit_a","concept_id":"concept_shared_x","kind":"encountered","occurred_at":"2026-09-18T01:00:00Z","source_refs":["source_a"]},
            {"event_id":"exposure_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","learning_unit_id":"unit_b","concept_id":"concept_shared_x","kind":"applied","occurred_at":"2026-09-19T01:00:00Z","source_refs":["source_b"]},
        ]
        original = copy.deepcopy(events)
        result = prior_encounters(assist, events, current_unit_id="unit_b")
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["learning_unit_id"], result[0]["kind"], result[0]["source_refs"]), ("unit_a", "encountered", ["source_a"]))
        self.assertEqual(events, original)

    def test_concept_record_without_event_and_same_unit_event_do_not_claim_prior_learning(self) -> None:
        assist = {"glosses": [{"id":"gloss_shared_x","concept_ref":"concept_shared_x"}]}
        same_unit = {"event_id":"exposure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","learning_unit_id":"unit_b","concept_id":"concept_shared_x","kind":"recognized","occurred_at":"2026-09-19T01:00:00Z","source_refs":["source_b"]}
        self.assertEqual(prior_encounters(assist, [], current_unit_id="unit_b"), [])
        self.assertEqual(prior_encounters(assist, [same_unit], current_unit_id="unit_b"), [])


if __name__ == "__main__": unittest.main()
