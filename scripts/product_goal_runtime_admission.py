#!/usr/bin/env python3
"""Shared no-model Ubuntu runtime admission identity and receipt checks.

This module never launches Codex, Claude, or a successor agent.  It is used by
the existing Router and Worker lane to attest one immutable Ubuntu runtime
generation, then by the Mac Runner adapter to reject a model reservation unless
the exact live receipt is fresh and identity-bound.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from product_goal_worker_identity import (
        PRODUCT_GOAL_ID,
        PRODUCT_GOAL_VERSION,
        PRODUCT_IDENTITY_SCHEMA,
        ProductGoalIdentityError,
        validate_product_goal_identity,
        validate_product_goal_runtime_context,
    )
except ModuleNotFoundError:  # Repository package import in unit tests.
    from scripts.product_goal_worker_identity import (
        PRODUCT_GOAL_ID,
        PRODUCT_GOAL_VERSION,
        PRODUCT_IDENTITY_SCHEMA,
        ProductGoalIdentityError,
        validate_product_goal_identity,
        validate_product_goal_runtime_context,
    )


RUNTIME_ROOT = Path("/home/kgnote/.local/share/kgnote/runtime")
RUNTIME_RELEASES = ".worker-runtime-releases"
RUNTIME_CURRENT = ".worker-runtime-current"
DEPLOYMENT_RECEIPT = "ubuntu-worker-runtime-receipt.json"
DEPLOYMENT_RECEIPT_SCHEMA = "kgnote.ubuntu-worker-runtime-receipt.v2"
RUNTIME_DISCOVERY_SCHEMA = "kgnote.runtime-generation-identity.v1"
ADMISSION_IDENTITY_SCHEMA = "kgnote.runtime-admission-identity.v1"
ADMISSION_CONTEXT_SCHEMA = "kgnote.runtime-admission-context.v1"
WORKER_RECEIPT_SCHEMA = "kgnote.runtime-admission-worker-receipt.v1"
ADMISSION_RECEIPT_SCHEMA = "kgnote.runtime-admission-receipt.v1"
DEPLOYMENT_REQUEST_SCHEMA = "kgnote.runtime-admission-request.v1"
MODEL_PRE_RESERVATION = "MODEL_PRE_RESERVATION"
DEPLOYMENT_ACCEPTANCE = "DEPLOYMENT_ACCEPTANCE"
EXECUTION_DIRECTION_ID = "kgnote-o2-runtime-receipt-pre-reservation-2026-10-29"
PRODUCT_WORKING_DIRECTORY = Path(
    "/home/kgnote/.local/share/kgnote/work-items/goal-o2-reading-experience"
)
REQUIRED_GENERATION_FILES = {
    "requirements-runtime.lock",
    "product_goal_runtime_admission.py",
    "product_goal_worker_identity.py",
    "product_goal_worker_lane.py",
    "product_goal_worker_result.py",
    "linux_worker_bootstrap.py",
    "linux_worker_guard.py",
    "linux_landlock_exec.py",
}
SHA1_RE = re.compile(r"[0-9a-f]{40}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
CHALLENGE_RE = re.compile(r"[0-9a-f]{64}")


class RuntimeAdmissionError(ValueError):
    pass


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()


def admission_event_id(challenge: str, binding: object) -> str:
    """Return the Router's canonical identity for one no-model admission."""
    suffix = hashlib.sha256(
        challenge.encode() + canonical_json_bytes(binding)
    ).hexdigest()[:16]
    return f"o2-admission-{suffix}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, *, description: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise RuntimeAdmissionError(f"{description} is absent or not a regular file")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeAdmissionError(f"{description} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeAdmissionError(f"{description} is not an object")
    return value


def _generation_from_current(runtime_root: Path) -> Path:
    releases = (runtime_root / RUNTIME_RELEASES).resolve()
    current = runtime_root / RUNTIME_CURRENT
    if not current.is_symlink():
        raise RuntimeAdmissionError("runtime current pointer is absent or not a symlink")
    generation = (runtime_root / os.readlink(current)).resolve()
    try:
        generation.relative_to(releases)
    except ValueError as exc:
        raise RuntimeAdmissionError("runtime current pointer leaves immutable releases") from exc
    if generation.parent != releases or not generation.is_dir() or generation.is_symlink():
        raise RuntimeAdmissionError("runtime current generation is invalid")
    return generation


def discover_runtime(runtime_root: Path = RUNTIME_ROOT) -> dict[str, Any]:
    """Read back the current immutable generation and deployment receipt."""
    generation = _generation_from_current(runtime_root)
    receipt_path = runtime_root / DEPLOYMENT_RECEIPT
    receipt = _load_json(receipt_path, description="Ubuntu runtime deployment receipt")
    if (
        receipt.get("schema_version") != DEPLOYMENT_RECEIPT_SCHEMA
        or receipt.get("status") != "PASS"
        or receipt.get("model_launches") != 0
    ):
        raise RuntimeAdmissionError("Ubuntu runtime deployment receipt is not a zero-model PASS")
    worker = receipt.get("worker_runtime")
    if not isinstance(worker, dict):
        raise RuntimeAdmissionError("Ubuntu runtime deployment receipt lacks worker identity")
    reviewed_revision = worker.get("reviewed_revision")
    source = worker.get("reviewed_source")
    files = worker.get("files")
    if (
        not isinstance(reviewed_revision, str)
        or SHA1_RE.fullmatch(reviewed_revision) is None
        or generation.name != reviewed_revision
        or not isinstance(source, dict)
        or SHA1_RE.fullmatch(str(source.get("head") or "")) is None
        or source.get("head") != reviewed_revision
        or SHA1_RE.fullmatch(str(source.get("tree") or "")) is None
        or SHA256_RE.fullmatch(str(worker.get("manifest_sha256") or "")) is None
        or not isinstance(files, dict)
        or not REQUIRED_GENERATION_FILES.issubset(files)
    ):
        raise RuntimeAdmissionError("Ubuntu runtime deployment identity is incomplete or inconsistent")
    if any(
        not isinstance(name, str)
        or not isinstance(digest, str)
        or SHA256_RE.fullmatch(digest) is None
        for name, digest in files.items()
    ):
        raise RuntimeAdmissionError("Ubuntu runtime deployment file map is malformed")
    observed: dict[str, str] = {}
    for name, expected in sorted(files.items()):
        path = generation / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeAdmissionError(f"runtime generation file is absent: {name}")
        digest = sha256_file(path)
        if digest != expected:
            raise RuntimeAdmissionError(f"runtime generation file hash drifted: {name}")
        observed[name] = digest
    lock_digest = observed.get("requirements-runtime.lock")
    if SHA256_RE.fullmatch(str(lock_digest or "")) is None:
        raise RuntimeAdmissionError("runtime generation dependency lock is absent")
    return {
        "schema_version": RUNTIME_DISCOVERY_SCHEMA,
        "runtime_root": str(runtime_root),
        "generation": str(generation),
        "generation_id": generation.name,
        "reviewed_revision": reviewed_revision,
        "reviewed_tree": source["tree"],
        "manifest_sha256": worker["manifest_sha256"],
        "deployment_receipt_path": str(receipt_path),
        "deployment_receipt_sha256": sha256_file(receipt_path),
        "requirements_lock_sha256": lock_digest,
        "files": observed,
        "deployment_model_launches": 0,
    }


def validate_runtime_identity(value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema_version") != RUNTIME_DISCOVERY_SCHEMA:
        raise RuntimeAdmissionError("runtime generation identity is missing or unsupported")
    required = {
        "runtime_root", "generation", "generation_id", "reviewed_revision",
        "reviewed_tree", "manifest_sha256", "deployment_receipt_path",
        "deployment_receipt_sha256", "requirements_lock_sha256", "files",
        "deployment_model_launches",
    }
    if required - set(value):
        raise RuntimeAdmissionError("runtime generation identity is incomplete")
    generation = Path(str(value["generation"]))
    if (
        generation.parent.name != RUNTIME_RELEASES
        or generation.name != value.get("generation_id")
        or value.get("reviewed_revision") != value.get("generation_id")
        or SHA1_RE.fullmatch(str(value.get("reviewed_revision") or "")) is None
        or SHA1_RE.fullmatch(str(value.get("reviewed_tree") or "")) is None
        or any(
            SHA256_RE.fullmatch(str(value.get(key) or "")) is None
            for key in (
                "manifest_sha256", "deployment_receipt_sha256",
                "requirements_lock_sha256",
            )
        )
        or value.get("deployment_model_launches") != 0
    ):
        raise RuntimeAdmissionError("runtime generation identity fields are invalid")
    files = value.get("files")
    if (
        not isinstance(files, dict)
        or not REQUIRED_GENERATION_FILES.issubset(files)
        or any(SHA256_RE.fullmatch(str(item or "")) is None for item in files.values())
        or files.get("requirements-runtime.lock") != value.get("requirements_lock_sha256")
    ):
        raise RuntimeAdmissionError("runtime generation file identity is invalid")
    return value


def require_live_runtime_identity(
    expected: object, *, runtime_root: Path = RUNTIME_ROOT,
) -> dict[str, Any]:
    expected = validate_runtime_identity(expected)
    observed = discover_runtime(runtime_root)
    if canonical_json_bytes(observed) != canonical_json_bytes(expected):
        raise RuntimeAdmissionError("live Ubuntu runtime generation differs from the admitted identity")
    return observed


def _candidate_fields(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeAdmissionError("admission candidate identity is absent")
    if (
        SHA1_RE.fullmatch(str(value.get("commit") or "")) is None
        or SHA256_RE.fullmatch(str(value.get("fingerprint") or "")) is None
        or not isinstance(value.get("branch"), str)
        or not value["branch"].startswith("codex/")
    ):
        raise RuntimeAdmissionError("admission candidate identity is invalid")
    tree = value.get("tree")
    if tree is not None and SHA1_RE.fullmatch(str(tree)) is None:
        raise RuntimeAdmissionError("admission candidate tree is invalid")
    return value


def validate_admission_identity(
    identity: object, *, event_id: str, stage: str, working_directory: Path,
    worktree_root: Path,
) -> dict[str, Any]:
    if not isinstance(identity, dict) or identity.get("schema_version") != ADMISSION_IDENTITY_SCHEMA:
        raise RuntimeAdmissionError("runtime admission identity is missing or unsupported")
    if stage != "admission" or identity.get("stage") != "admission":
        raise RuntimeAdmissionError("runtime admission identity must use the admission stage")
    if identity.get("event_id") != event_id or not event_id.startswith("o2-admission-"):
        raise RuntimeAdmissionError("runtime admission event identity differs")
    challenge = identity.get("challenge")
    if not isinstance(challenge, str) or CHALLENGE_RE.fullmatch(challenge) is None:
        raise RuntimeAdmissionError("runtime admission challenge is invalid")
    if working_directory != PRODUCT_WORKING_DIRECTORY or (
        working_directory != worktree_root / "work-items" / "goal-o2-reading-experience"
    ):
        raise RuntimeAdmissionError("runtime admission checkout path differs")
    validate_runtime_identity(identity.get("runtime_identity"))
    candidate = _candidate_fields(identity.get("candidate"))
    kind = identity.get("admission_kind")
    if kind == MODEL_PRE_RESERVATION:
        product_identity = identity.get("product_goal_identity")
        context = identity.get("product_goal_context")
        if not isinstance(product_identity, dict) or product_identity.get("schema_version") != PRODUCT_IDENTITY_SCHEMA:
            raise RuntimeAdmissionError("model admission lacks the original Product Goal identity")
        try:
            validate_product_goal_identity(
                product_identity,
                event_id=str(product_identity.get("order_event_id") or ""),
                stage=str(product_identity.get("stage") or ""),
                working_directory=working_directory,
                worktree_root=worktree_root,
            )
            context = validate_product_goal_runtime_context(context, identity=product_identity)
        except ProductGoalIdentityError as exc:
            raise RuntimeAdmissionError(str(exc)) from exc
        if (
            identity.get("authority_lease") != "ACTIVE"
            or identity.get("go_live_authorized") is not True
            or identity.get("formal_dispatch_authorized") is not True
            or SHA256_RE.fullmatch(str(identity.get("work_order_sha256") or "")) is None
            or any(
                candidate.get(left) != context.get(right)
                for left, right in {
                    "commit": "candidate_commit",
                    "fingerprint": "candidate_fingerprint",
                    "branch": "branch",
                    "pull_request": "pull_request",
                }.items()
            )
        ):
            raise RuntimeAdmissionError("model admission identity is not exact and active")
    elif kind == DEPLOYMENT_ACCEPTANCE:
        if (
            identity.get("execution_direction_id") != EXECUTION_DIRECTION_ID
            or identity.get("product_goal_id") != PRODUCT_GOAL_ID
            or identity.get("product_goal_version") != PRODUCT_GOAL_VERSION
            or identity.get("authority_lease") != "PAUSED"
            or identity.get("go_live_authorized") is not False
            or identity.get("formal_dispatch_authorized") is not False
            or identity.get("product_goal_identity") is not None
            or identity.get("product_goal_context") is not None
            or identity.get("work_order_sha256") is not None
        ):
            raise RuntimeAdmissionError("deployment admission identity may not impersonate active Product Goal authority")
    else:
        raise RuntimeAdmissionError("runtime admission kind is unsupported")
    return identity


def validate_admission_context(context: object) -> dict[str, Any]:
    if not isinstance(context, dict) or context.get("schema_version") != ADMISSION_CONTEXT_SCHEMA:
        raise RuntimeAdmissionError("runtime admission context is missing or unsupported")
    required = {
        "admission_kind", "challenge", "event_id", "candidate",
        "runtime_identity", "admission_identity", "work_order_sha256",
    }
    if required - set(context):
        raise RuntimeAdmissionError("runtime admission context is incomplete")
    identity = context.get("admission_identity")
    if not isinstance(identity, dict):
        raise RuntimeAdmissionError("runtime admission context lacks its identity")
    if any(
        context.get(key) != identity.get(key)
        for key in (
            "admission_kind", "challenge", "event_id", "candidate",
            "runtime_identity", "work_order_sha256",
        )
    ):
        raise RuntimeAdmissionError("runtime admission context differs from its bootstrap identity")
    return context


def validate_deployment_request(request: object) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("schema_version") != DEPLOYMENT_REQUEST_SCHEMA:
        raise RuntimeAdmissionError("deployment admission request is missing or unsupported")
    if (
        request.get("admission_kind") != DEPLOYMENT_ACCEPTANCE
        or request.get("execution_direction_id") != EXECUTION_DIRECTION_ID
        or request.get("product_goal_id") != PRODUCT_GOAL_ID
        or request.get("product_goal_version") != PRODUCT_GOAL_VERSION
        or request.get("authority_lease") != "PAUSED"
        or request.get("go_live_authorized") is not False
        or request.get("formal_dispatch_authorized") is not False
        or request.get("working_directory") != str(PRODUCT_WORKING_DIRECTORY)
        or CHALLENGE_RE.fullmatch(str(request.get("challenge") or "")) is None
    ):
        raise RuntimeAdmissionError("deployment admission request crosses the PAUSE boundary")
    _candidate_fields(request.get("candidate"))
    validate_runtime_identity(request.get("runtime_identity"))
    return request


def build_deployment_request(
    *, runtime_identity: dict[str, Any], challenge: str,
    candidate_commit: str, candidate_fingerprint: str,
    candidate_branch: str, candidate_tree: str | None = None,
) -> dict[str, Any]:
    candidate = {
        "commit": candidate_commit,
        "fingerprint": candidate_fingerprint,
        "branch": candidate_branch,
        "tree": candidate_tree,
    }
    if candidate_tree is None:
        candidate.pop("tree")
    request = {
        "schema_version": DEPLOYMENT_REQUEST_SCHEMA,
        "admission_kind": DEPLOYMENT_ACCEPTANCE,
        "execution_direction_id": EXECUTION_DIRECTION_ID,
        "product_goal_id": PRODUCT_GOAL_ID,
        "product_goal_version": PRODUCT_GOAL_VERSION,
        "authority_lease": "PAUSED",
        "go_live_authorized": False,
        "formal_dispatch_authorized": False,
        "working_directory": str(PRODUCT_WORKING_DIRECTORY),
        "challenge": challenge,
        "candidate": candidate,
        "runtime_identity": runtime_identity,
    }
    return validate_deployment_request(request)


def model_processes(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    if not proc_root.is_dir():
        raise RuntimeAdmissionError("Linux process table is unavailable")
    for process in proc_root.iterdir():
        if not process.name.isdigit():
            continue
        try:
            argv = [
                item.decode("utf-8", errors="replace")
                for item in (process / "cmdline").read_bytes().split(b"\0")
                if item
            ]
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if not argv:
            continue
        executable = Path(argv[0]).name
        model = (
            executable in {"codex", "claude"}
            or (executable.startswith("node") and any(Path(item).name == "codex.js" for item in argv[1:]))
        )
        if model:
            observed.append({"pid": int(process.name), "argv_sha256": hashlib.sha256(canonical_json_bytes(argv)).hexdigest()})
    return observed


def validate_reservation_receipt(
    receipt: object, *, order_sha256: str, context: dict[str, Any],
    occurred_at: datetime, evidence_root: Path,
) -> dict[str, Any]:
    """Validate the final Mac-side live receipt before any ledger append."""
    if not isinstance(receipt, dict) or receipt.get("schema_version") != ADMISSION_RECEIPT_SCHEMA:
        raise RuntimeAdmissionError("pre-reservation admission receipt is missing or unsupported")
    if receipt.get("status") != "PASS" or receipt.get("admission_kind") != MODEL_PRE_RESERVATION:
        raise RuntimeAdmissionError("pre-reservation admission receipt is not a model-bound PASS")
    if receipt.get("work_order_sha256") != order_sha256:
        raise RuntimeAdmissionError("pre-reservation admission receipt binds a different WorkOrder")
    try:
        issued_at = datetime.fromisoformat(str(receipt["issued_at"]))
        expires_at = datetime.fromisoformat(str(receipt["expires_at"]))
    except (KeyError, ValueError) as exc:
        raise RuntimeAdmissionError("pre-reservation admission receipt time is invalid") from exc
    if (
        issued_at.tzinfo is None
        or expires_at.tzinfo is None
        or occurred_at.tzinfo is None
        or not issued_at <= occurred_at <= expires_at
        or (expires_at - issued_at).total_seconds() > 180
    ):
        raise RuntimeAdmissionError("pre-reservation admission receipt is stale or outside its bounded lifetime")
    candidate = _candidate_fields(receipt.get("candidate"))
    exact = {
        "goal_id": context.get("goal_id"),
        "goal_version": context.get("goal_version"),
        "work_item_id": context.get("work_item_id"),
        "order_event_id": context.get("order_event_id"),
        "attempt_id": context.get("attempt_id"),
        "action": context.get("action"),
        "provider": context.get("provider"),
    }
    if any(receipt.get(key) != value for key, value in exact.items()):
        raise RuntimeAdmissionError("pre-reservation admission receipt identity differs from the WorkOrder")
    if any(
        candidate.get(left) != context.get(right)
        for left, right in {
            "commit": "candidate_commit",
            "fingerprint": "candidate_fingerprint",
            "branch": "branch",
            "pull_request": "pull_request",
        }.items()
    ):
        raise RuntimeAdmissionError("pre-reservation admission candidate differs from the WorkOrder")
    runner = context.get("runner_context")
    authority = receipt.get("authority")
    if not isinstance(runner, dict) or not isinstance(authority, dict) or any(
        authority.get(key) != expected for key, expected in {
            "state_projection_sha256": runner.get("state_projection_sha256"),
            "authority_record_sha256": runner.get("authority_record_sha256"),
            "authority_lease": "ACTIVE",
            "lifecycle": "ACTIVE",
            "go_live_authorized": True,
        }.items()
    ):
        raise RuntimeAdmissionError("pre-reservation admission authority differs from the live order")
    runtime = validate_runtime_identity(receipt.get("runtime_identity"))
    if canonical_json_bytes(runtime) != canonical_json_bytes(context.get("runtime_identity")):
        raise RuntimeAdmissionError("pre-reservation admission runtime differs from the pinned WorkOrder")
    challenge = receipt.get("challenge")
    if not isinstance(challenge, str) or CHALLENGE_RE.fullmatch(challenge) is None:
        raise RuntimeAdmissionError("pre-reservation admission challenge is invalid")
    expected_admission_event_id = admission_event_id(challenge, {
        "work_order_sha256": order_sha256,
        "runtime_identity": runtime,
    })
    isolation = receipt.get("isolation")
    if not isinstance(isolation, dict) or any(
        isolation.get(key) != "PASS"
        for key in ("ssh", "bootstrap", "systemd", "guard", "landlock")
    ):
        raise RuntimeAdmissionError("pre-reservation admission did not prove the full isolated route")
    if (
        receipt.get("model_process_started") is not False
        or receipt.get("model_launches") != 0
        or receipt.get("model_processes") != []
    ):
        raise RuntimeAdmissionError("pre-reservation admission observed a model process")
    if SHA256_RE.fullmatch(str(receipt.get("worker_receipt_sha256") or "")) is None:
        raise RuntimeAdmissionError("pre-reservation admission lacks exact Worker evidence")
    checkpoint_value = receipt.get("router_checkpoint_path")
    if not isinstance(checkpoint_value, str) or not checkpoint_value:
        raise RuntimeAdmissionError("pre-reservation admission lacks a Router checkpoint path")
    root = evidence_root.resolve()
    checkpoint_path = Path(checkpoint_value)
    if not checkpoint_path.is_absolute():
        checkpoint_path = evidence_root / checkpoint_path
    try:
        checkpoint_resolved = checkpoint_path.resolve(strict=True)
        checkpoint_resolved.relative_to(root)
    except (FileNotFoundError, OSError, ValueError) as exc:
        raise RuntimeAdmissionError(
            "pre-reservation admission Router checkpoint leaves the evidence root or is absent"
        ) from exc
    if checkpoint_path.is_symlink() or not checkpoint_resolved.is_file():
        raise RuntimeAdmissionError(
            "pre-reservation admission Router checkpoint is not a regular file"
        )
    checkpoint_bytes = checkpoint_resolved.read_bytes()
    checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
    if (
        receipt.get("router_checkpoint_sha256") != checkpoint_sha256
        or SHA256_RE.fullmatch(checkpoint_sha256) is None
    ):
        raise RuntimeAdmissionError(
            "pre-reservation admission Router checkpoint hash differs from the receipt"
        )
    try:
        checkpoint = json.loads(checkpoint_bytes)
    except json.JSONDecodeError as exc:
        raise RuntimeAdmissionError(
            "pre-reservation admission Router checkpoint is malformed"
        ) from exc
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("schema_version") != "kgnote.linux-worker-route.v1"
        or checkpoint.get("status") not in {"COMPLETED", "ALREADY_COMPLETED"}
        or checkpoint.get("event_id") != expected_admission_event_id
        or checkpoint.get("host_fallback_used") is not False
        or SHA256_RE.fullmatch(str(checkpoint.get("command_digest") or "")) is None
    ):
        raise RuntimeAdmissionError(
            "pre-reservation admission Router checkpoint is incomplete or mismatched"
        )
    bootstrap_sha256 = receipt.get("bootstrap_receipt_sha256")
    if (
        SHA256_RE.fullmatch(str(bootstrap_sha256 or "")) is None
        or checkpoint.get("bootstrap_receipt_sha256") != bootstrap_sha256
    ):
        raise RuntimeAdmissionError(
            "pre-reservation admission Bootstrap evidence differs from the Router checkpoint"
        )
    worker = checkpoint.get("execution_evidence")
    if (
        not isinstance(worker, dict)
        or worker.get("schema_version") != WORKER_RECEIPT_SCHEMA
        or worker.get("status") != "PASS"
        or hashlib.sha256(canonical_json_bytes(worker)).hexdigest()
        != receipt.get("worker_receipt_sha256")
    ):
        raise RuntimeAdmissionError(
            "pre-reservation admission Worker evidence differs from the Router checkpoint"
        )
    worker_exact = {
        "admission_kind": MODEL_PRE_RESERVATION,
        "challenge": challenge,
        "event_id": expected_admission_event_id,
        "work_order_sha256": order_sha256,
        **exact,
        "candidate": candidate,
        "authority": authority,
        "runtime_identity": runtime,
        "model_process_started": False,
        "model_launches": 0,
        "model_processes": [],
        "landlock_denial_probe": "PASS",
    }
    if any(
        canonical_json_bytes(worker.get(key)) != canonical_json_bytes(expected)
        for key, expected in worker_exact.items()
    ):
        raise RuntimeAdmissionError(
            "pre-reservation admission Worker evidence identity differs from the receipt"
        )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--discover-runtime", action="store_true")
    operation.add_argument("--make-deployment-request", action="store_true")
    parser.add_argument("--runtime-root", type=Path, default=RUNTIME_ROOT)
    parser.add_argument("--runtime-identity", type=Path)
    parser.add_argument("--challenge")
    parser.add_argument("--candidate-commit")
    parser.add_argument("--candidate-fingerprint")
    parser.add_argument("--candidate-branch")
    parser.add_argument("--candidate-tree")
    args = parser.parse_args()
    try:
        if args.discover_runtime:
            result = discover_runtime(args.runtime_root)
        else:
            required = {
                "runtime identity": args.runtime_identity,
                "challenge": args.challenge,
                "candidate commit": args.candidate_commit,
                "candidate fingerprint": args.candidate_fingerprint,
                "candidate branch": args.candidate_branch,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                raise RuntimeAdmissionError(
                    "deployment request lacks " + ", ".join(missing)
                )
            result = build_deployment_request(
                runtime_identity=_load_json(
                    args.runtime_identity,
                    description="runtime identity",
                ),
                challenge=args.challenge,
                candidate_commit=args.candidate_commit,
                candidate_fingerprint=args.candidate_fingerprint,
                candidate_branch=args.candidate_branch,
                candidate_tree=args.candidate_tree,
            )
    except (OSError, RuntimeAdmissionError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
