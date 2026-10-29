from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scripts import product_goal_runtime_admission as ADMISSION


ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SPEC_PATH = (
    ROOT / "docs/control-plane/O2_BOUNDED_TRIAL_GOAL_SPEC_v2026-10-29.3.json"
)


def product_goal_spec() -> dict[str, Any]:
    return json.loads(PRODUCT_SPEC_PATH.read_text(encoding="utf-8"))


def activation_dependency_receipts(
    spec: dict[str, Any], *, verified_at: str = "2026-10-29T14:00:00+08:00",
) -> list[dict[str, Any]]:
    carryover = spec["history_carryover"]
    source = carryover["source_goal"]
    rows = [{
        "dependency_id": carryover["dependency_id"],
        "status": "CLOSED",
        "source_kind": "EXTERNAL_DECISION_RESOLVED",
        "goal_version": source["goal_version"],
        "goal_spec_sha256": source["goal_spec_sha256"],
        "evidence_sha256": carryover["evidence_sha256"],
        "verified_at": verified_at,
    }]
    for index, dependency_id in enumerate(
        spec["trial_schedule"]["activation_dependency_ids"], start=1,
    ):
        if dependency_id == carryover["dependency_id"]:
            continue
        rows.append({
            "dependency_id": dependency_id,
            "status": "CLOSED",
            "source_kind": "EXTERNAL_DECISION_RESOLVED",
            "goal_version": None,
            "goal_spec_sha256": None,
            "evidence_sha256": f"{index}" * 64,
            "verified_at": verified_at,
        })
    return rows


def runtime_identity() -> dict[str, Any]:
    revision = "9" * 40
    files = {
        name: hashlib.sha256(f"fixture:{name}".encode()).hexdigest()
        for name in ADMISSION.REQUIRED_GENERATION_FILES
    }
    return {
        "schema_version": ADMISSION.RUNTIME_DISCOVERY_SCHEMA,
        "runtime_root": str(ADMISSION.RUNTIME_ROOT),
        "generation": str(
            ADMISSION.RUNTIME_ROOT / ADMISSION.RUNTIME_RELEASES / revision
        ),
        "generation_id": revision,
        "reviewed_revision": revision,
        "reviewed_tree": "8" * 40,
        "manifest_sha256": "7" * 64,
        "deployment_receipt_path": str(
            ADMISSION.RUNTIME_ROOT / ADMISSION.DEPLOYMENT_RECEIPT
        ),
        "deployment_receipt_sha256": "6" * 64,
        "requirements_lock_sha256": files["requirements-runtime.lock"],
        "files": files,
        "deployment_model_launches": 0,
    }


def reservation_receipt(
    context: dict[str, Any], *, order_sha256: str, observed_at: datetime,
    router_checkpoint_path: Path,
) -> dict[str, Any]:
    candidate = {
        "commit": context["candidate_commit"],
        "fingerprint": context["candidate_fingerprint"],
        "branch": context["branch"],
        "pull_request": context.get("pull_request"),
    }
    runner = context["runner_context"]
    authority = {
        "state_projection_sha256": runner["state_projection_sha256"],
        "authority_record_sha256": runner["authority_record_sha256"],
        "authority_lease": "ACTIVE",
        "lifecycle": "ACTIVE",
        "go_live_authorized": True,
    }
    worker = {
        "schema_version": ADMISSION.WORKER_RECEIPT_SCHEMA,
        "status": "PASS",
        "challenge": "5" * 64,
        "work_order_sha256": order_sha256,
        "goal_id": context["goal_id"],
        "goal_version": context["goal_version"],
        "work_item_id": context["work_item_id"],
        "order_event_id": context["order_event_id"],
        "attempt_id": context["attempt_id"],
        "action": context["action"],
        "provider": context["provider"],
        "candidate": candidate,
        "authority": authority,
        "runtime_identity": context["runtime_identity"],
        "environment": {"status": "DEVELOPMENT_ENVIRONMENT_READY"},
        "entrypoints": {},
        "model_process_started": False,
        "model_launches": 0,
        "model_processes": [],
        "landlock_denial_probe": "PASS",
    }
    bootstrap_sha256 = "3" * 64
    router_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    router_checkpoint = {
        "schema_version": "kgnote.linux-worker-route.v1",
        "status": "COMPLETED",
        "event_id": context["order_event_id"],
        "command_digest": "4" * 64,
        "bootstrap_receipt_sha256": bootstrap_sha256,
        "host_fallback_used": False,
        "execution_evidence": worker,
    }
    router_checkpoint_path.write_text(json.dumps(router_checkpoint), encoding="utf-8")
    return {
        "schema_version": ADMISSION.ADMISSION_RECEIPT_SCHEMA,
        "status": "PASS",
        "admission_kind": ADMISSION.MODEL_PRE_RESERVATION,
        "challenge": "5" * 64,
        "issued_at": observed_at.isoformat(timespec="seconds"),
        "expires_at": (observed_at + timedelta(seconds=120)).isoformat(
            timespec="seconds"
        ),
        "work_order_sha256": order_sha256,
        "goal_id": context["goal_id"],
        "goal_version": context["goal_version"],
        "work_item_id": context["work_item_id"],
        "order_event_id": context["order_event_id"],
        "attempt_id": context["attempt_id"],
        "action": context["action"],
        "provider": context["provider"],
        "candidate": candidate,
        "authority": authority,
        "runtime_identity": context["runtime_identity"],
        "environment": {"status": "DEVELOPMENT_ENVIRONMENT_READY"},
        "entrypoints": {},
        "isolation": {
            "ssh": "PASS",
            "bootstrap": "PASS",
            "systemd": "PASS",
            "guard": "PASS",
            "landlock": "PASS",
        },
        "router_checkpoint_path": str(router_checkpoint_path),
        "router_checkpoint_sha256": hashlib.sha256(
            router_checkpoint_path.read_bytes()
        ).hexdigest(),
        "bootstrap_receipt_sha256": bootstrap_sha256,
        "worker_receipt_sha256": hashlib.sha256(
            ADMISSION.canonical_json_bytes(worker)
        ).hexdigest(),
        "model_process_started": False,
        "model_launches": 0,
        "model_processes": [],
    }


def prepare_model_reservation(
    repo: Path, state: dict[str, Any], action: dict[str, Any], *,
    observed_at: datetime,
) -> tuple[Path, Path]:
    work = next(
        row for row in state["work_items"]
        if row["work_item_id"] == action["work_item_id"]
    )
    binding = work["dispatch_binding"]
    order_path = repo / binding["order_path"]
    order = json.loads(order_path.read_text(encoding="utf-8"))
    candidate = state.get("candidate_identity") or {
        "commit": "a" * 40,
        "fingerprint": "b" * 64,
        "branch": "codex/runtime-admission-fixture",
        "pull_request": None,
    }
    attempt_id = (
        f"attempt-{state['goal_version']}-{action['work_item_id']}-"
        f"{int(work.get('attempts', 0)) + 1}"
    )
    runtime = runtime_identity()
    context = {
        "schema_version": "kgnote.product-goal-runtime-context.v1",
        "goal_id": state["goal_id"],
        "goal_version": state["goal_version"],
        "work_item_id": action["work_item_id"],
        "order_event_id": order["event_id"],
        "attempt_id": attempt_id,
        "action": action["action"],
        "provider": action["provider"],
        "candidate_commit": candidate["commit"],
        "candidate_fingerprint": candidate["fingerprint"],
        "branch": candidate["branch"],
        "pull_request": candidate.get("pull_request"),
        "runtime_identity": runtime,
        "runner_context": {
            "state_projection_sha256": hashlib.sha256(
                ADMISSION.canonical_json_bytes(state)
            ).hexdigest(),
            "event_cursor": state["event_cursor"],
            "lifecycle": state["lifecycle"],
            "authority_lease": state["authority_lease"],
            "go_live_authorized": state["go_live_authorized"],
            "authority_record": state["authority_record"],
            "authority_record_sha256": hashlib.sha256(
                ADMISSION.canonical_json_bytes(state["authority_record"])
            ).hexdigest(),
            "work_item": {
                "work_item_id": work["work_item_id"],
                "status": work["status"],
                "attempts_before": int(work.get("attempts", 0)),
                "active_attempt_id": work.get("active_attempt_id"),
                "dispatch_attempt_id": attempt_id,
                "dependencies": work["dependencies"],
                "obligation_ids": work["obligation_ids"],
            },
        },
    }
    order["execution_context"] = context
    order["runtime_generation"] = runtime["generation"]
    order_path.write_text(json.dumps(order), encoding="utf-8")
    receipt = reservation_receipt(
        context,
        order_sha256=hashlib.sha256(order_path.read_bytes()).hexdigest(),
        observed_at=observed_at,
        router_checkpoint_path=(
            repo / "output" / f"{order['event_id']}-router-checkpoint.json"
        ),
    )
    receipt_path = repo / "output" / f"{order['event_id']}-admission.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return order_path, receipt_path


def write_reservation_receipt(
    repo: Path, order_path: Path, *, observed_at: datetime,
) -> Path:
    order = json.loads(order_path.read_text(encoding="utf-8"))
    receipt = reservation_receipt(
        order["execution_context"],
        order_sha256=hashlib.sha256(order_path.read_bytes()).hexdigest(),
        observed_at=observed_at,
        router_checkpoint_path=(
            repo / "output" / f"{order['event_id']}-router-checkpoint.json"
        ),
    )
    receipt_path = repo / "output" / f"{order['event_id']}-admission.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return receipt_path
