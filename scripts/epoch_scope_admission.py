#!/usr/bin/env python3
"""Fail-closed admission for epoch-scoped Claude Reviewer dispatch."""
from __future__ import annotations
import argparse, json, subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

class AdmissionError(RuntimeError): pass

def parse_utc(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AdmissionError(f"{label} must be trusted UTC Z time")
    try: result = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc: raise AdmissionError(f"{label} is invalid") from exc
    if result.tzinfo != timezone.utc: raise AdmissionError(f"{label} is not UTC")
    return result

def validate(epoch: dict[str, Any], order: dict[str, Any], pr: dict[str, Any]) -> dict[str, Any]:
    if epoch.get("schema_version") != "kgnote.claude-reviewer-cutover-epoch.v1": raise AdmissionError("unsupported epoch record")
    if epoch.get("activation_scope") != "EPOCH_NEW_AUTHORIZED_PRS_ONLY": raise AdmissionError("epoch scope is inactive")
    admission = order.get("review_admission")
    if not isinstance(admission, dict): raise AdmissionError("review_admission is missing")
    repository, number = admission.get("repository"), admission.get("pull_request")
    if repository not in epoch.get("allowed_repositories", []): raise AdmissionError("repository is outside epoch scope")
    if not isinstance(number, int) or number < 1: raise AdmissionError("pull_request is invalid")
    if any(item.get("repository") == repository and item.get("pull_request") == number for item in epoch.get("legacy_pr_inventory", [])):
        raise AdmissionError("legacy PR is permanently excluded")
    created = parse_utc(pr.get("created_at"), "GitHub PR created_at")
    if created <= parse_utc(epoch.get("epoch_started_at_utc"), "epoch_started_at_utc"):
        raise AdmissionError("PR predates or equals cutover epoch")
    if pr.get("number") != number: raise AdmissionError("GitHub PR identity mismatch")
    head = ((pr.get("head") or {}).get("sha") if isinstance(pr.get("head"), dict) else None)
    if head != admission.get("head_sha"): raise AdmissionError("stale or mismatched HEAD")
    fingerprint = admission.get("candidate_fingerprint")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64: raise AdmissionError("candidate fingerprint is invalid")
    admission_kind = admission.get("admission_kind", "REVIEW")
    if admission_kind not in {"REVIEW", "IMPLEMENTATION"}: raise AdmissionError("admission kind is invalid")
    if admission_kind == "REVIEW" and (not isinstance(admission.get("review_round"), int) or admission["review_round"] < 1): raise AdmissionError("review round is invalid")
    authority = admission.get("authority")
    if not isinstance(authority, dict) or authority.get("status") != "APPROVED" or not authority.get("goal_id") or not authority.get("authority_record"):
        raise AdmissionError("legal goal/review authority is missing")
    budget = admission.get("budget") if admission_kind == "REVIEW" else admission.get("implementation_budget")
    if not isinstance(budget, dict) or not isinstance(budget.get("authorized"), int) or not isinstance(budget.get("used"), int) or budget["used"] >= budget["authorized"]:
        raise AdmissionError(f"{admission_kind.lower()} budget is stopped or exhausted")
    if admission.get("work_window_allowed") is not True: raise AdmissionError("work window is closed")
    if admission.get("stop_marker_clear") is not True: raise AdmissionError("Stop Marker does not authorize dispatch")
    if admission.get("existing_exact_candidate_result") is not False: raise AdmissionError("candidate is already reviewed or result state is unknown")
    return {"status":"ADMITTED","admission_kind":admission_kind,"epoch_id":epoch["epoch_id"],"repository":repository,"pull_request":number,"head_sha":head,"activation_scope":epoch["activation_scope"]}

def fetch_pr(repository: str, number: int, runner: Callable[..., subprocess.CompletedProcess[str]]=subprocess.run) -> dict[str, Any]:
    result=runner(["/opt/homebrew/bin/gh","api",f"repos/{repository}/pulls/{number}"],capture_output=True,text=True,timeout=20)
    if result.returncode: raise AdmissionError("trusted GitHub PR read-back failed")
    try: value=json.loads(result.stdout)
    except json.JSONDecodeError as exc: raise AdmissionError("GitHub PR metadata is invalid") from exc
    if not isinstance(value,dict): raise AdmissionError("GitHub PR metadata is not an object")
    return value

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--epoch",type=Path,required=True); parser.add_argument("--order",type=Path,required=True); args=parser.parse_args()
    try:
        epoch=json.loads(args.epoch.read_text()); order=json.loads(args.order.read_text()); admission=order.get("review_admission") or {}
        result=validate(epoch,order,fetch_pr(str(admission.get("repository")),int(admission.get("pull_request",0))))
    except (OSError,ValueError,json.JSONDecodeError,AdmissionError) as exc:
        print(json.dumps({"status":"REJECTED","reason":str(exc)})); return 2
    print(json.dumps(result,sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
