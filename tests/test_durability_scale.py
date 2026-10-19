from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from kgnote.learning import latest_resume_context, record_resume_context
from kgnote.review import list_attempts, list_due, list_exposures, record_exposure, save_attempt, schedule_after_feedback
from tests.test_attempt_store import request as attempt_request
from tests.test_exposure_store import event as exposure_event
from tests.test_resume_context import request as resume_request


class DurabilityScaleTests(unittest.TestCase):
    def test_large_append_only_history_round_trips_without_identity_loss(self) -> None:
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            unit_id = attempt_request()["learning_unit_id"]
            for index in range(500):
                value = attempt_request(state="submitted", response=f"response {index}", attempt_id=f"attempt_{index:032x}")
                value["review_item_id"] = f"item_{index % 50:02d}"
                self.assertEqual(save_attempt(root, value).status, "saved")
                if index < 50:
                    feedback = {"outcome": "CORRECT"}
                    self.assertEqual(schedule_after_feedback(root, value, feedback).status, "saved")
            for index in range(100):
                value = exposure_event("encountered")
                value["event_id"] = f"exposure_{index:032x}"
                value["occurred_at"] = f"2026-09-20T{index // 60:02d}:{index % 60:02d}:00Z"
                self.assertEqual(record_exposure(root, value).status, "recorded")
                context = copy.deepcopy(resume_request())
                context["event_id"] = f"resume_{index:032x}"
                context["occurred_at"] = f"2026-09-20T{index // 60:02d}:{index % 60:02d}:30Z"
                self.assertEqual(record_resume_context(root, context).status, "recorded")
            attempts = list_attempts(root, unit_id).payload["attempts"]
            exposures = list_exposures(root, exposure_event()["learning_unit_id"]).payload["events"]
            dues = list_due(root, now="2026-12-31T00:00:00Z").payload["items"]
            latest = latest_resume_context(root, resume_request()["learning_unit_id"]).payload["context"]
            self.assertEqual((len(attempts), len(exposures), len(dues)), (500, 100, 50))
            self.assertEqual(len({item["attempt_id"] for item in attempts}), 500)
            self.assertEqual(len({item["event_id"] for item in exposures}), 100)
            self.assertEqual(latest["event_id"], "resume_00000000000000000000000000000063")


if __name__ == "__main__":
    unittest.main()
