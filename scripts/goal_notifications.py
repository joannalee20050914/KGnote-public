#!/usr/bin/env python3
"""Small durable decision-notification layer for Product Goals.

ChatGPT Work remains UNVERIFIED until an operated event trigger and delivery
read-back exist. GitHub Issue comments are the default reliable notification
transport; neither transport grants Product Goal authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Callable

import goal_continuity


HUMAN_EVENT_KINDS = {
    "FINAL_PRODUCT_ACCEPTANCE_REQUIRED",
    "NEXT_GOAL_APPROVAL_REQUIRED",
    "PRODUCT_WHAT_CONFLICT",
    "NEW_EXPENSE_PERMISSION_OR_IRREVERSIBLE_RISK",
    "STRATEGY_EXHAUSTED_NEEDS_PRODUCT_OR_RESOURCE_CHANGE",
}
IGNORED_OPERATIONAL_KINDS = {
    "CHANGES_REQUIRED", "QUOTA_WAIT", "SESSION_RESUMED", "PR_UPDATED",
    "TEST_FAILURE", "PUBLISHER_RETRY", "WORK_WINDOW_CLOSED",
}
ACK_MARKER = "<!-- kgnote-product-goal-notification-ack:v1 -->"
NOTIFICATION_FIELDS = {
    "notification_id", "goal_id", "goal_version", "event_kind",
    "decision_key", "summary", "decision_requested", "github_issue",
    "transport", "chatgpt_work_status", "authority_effect",
}


class NotificationError(goal_continuity.GoalContractError):
    pass


def notification_id(goal_id: str, event_kind: str, decision_key: str) -> str:
    if event_kind not in HUMAN_EVENT_KINDS:
        raise NotificationError(f"event kind does not require human attention: {event_kind}")
    digest = hashlib.sha256(
        goal_continuity.canonical_json_bytes(
            {"goal_id": goal_id, "event_kind": event_kind, "decision_key": decision_key}
        )
    ).hexdigest()[:24]
    return f"notice-{digest}"


def build_notification(
    *, goal_id: str, goal_version: str, event_kind: str, decision_key: str,
    summary: str, decision_requested: str, github_issue: int,
    work_status: str = "UNVERIFIED",
) -> dict[str, Any]:
    if work_status not in {"UNVERIFIED", "VERIFIED"}:
        raise NotificationError("ChatGPT Work status must be UNVERIFIED or VERIFIED")
    notice_id = notification_id(goal_id, event_kind, decision_key)
    transport = "CHATGPT_WORK" if work_status == "VERIFIED" else "GITHUB_NATIVE"
    return {
        "notification_id": notice_id,
        "goal_id": goal_id,
        "goal_version": goal_version,
        "event_kind": event_kind,
        "decision_key": decision_key,
        "summary": summary,
        "decision_requested": decision_requested,
        "github_issue": github_issue,
        "transport": transport,
        "chatgpt_work_status": work_status,
        "authority_effect": "NONE",
    }


def notification_state(
    events: list[dict[str, Any]], notification_id_value: str
) -> str | None:
    projection = goal_continuity.reduce_ledger(events)
    notice = projection["notifications"].get(notification_id_value)
    if notice is None:
        return None
    return {
        "NOTIFICATION_QUEUED": "QUEUED",
        "NOTIFICATION_DELIVERY_FAILED": "QUEUED",
        "NOTIFICATION_SENT": "SENT",
        "NOTIFICATION_ACKNOWLEDGED": "ACKNOWLEDGED",
    }.get(notice["last_event"])


def acknowledgement_record_from_comment(
    comment: dict[str, Any],
    notification: dict[str, Any],
    *,
    repository: str,
    owner_logins: list[str],
) -> dict[str, Any]:
    """Validate one exact Owner ACK; acknowledgment has no authority effect."""
    body = comment.get("body")
    if not isinstance(body, str) or body.count(ACK_MARKER) != 1:
        raise NotificationError("notification ACK marker must occur exactly once")
    tail = body.split(ACK_MARKER, 1)[1]
    matches = re.findall(r"```json\s*(.*?)\s*```", tail, re.DOTALL)
    if len(matches) != 1:
        raise NotificationError("notification ACK requires exactly one fenced JSON payload")
    payload = json.loads(matches[0])
    expected = {"schema_version", "notification_id", "goal_id", "goal_version"}
    if not isinstance(payload, dict) or set(payload) != expected:
        raise NotificationError("notification ACK payload keys must be exact")
    if payload != {
        "schema_version": "kgnote.product-goal-notification-ack.v1",
        "notification_id": notification["notification_id"],
        "goal_id": notification["goal_id"],
        "goal_version": notification["goal_version"],
    }:
        raise NotificationError("notification ACK does not bind the exact notification")
    author = comment.get("user") if isinstance(comment.get("user"), dict) else {}
    login = author.get("login")
    if comment.get("author_association") != "OWNER" or login not in owner_logins:
        raise NotificationError("notification ACK is not authored by an allowed repository Owner")
    issue_url = str(comment.get("issue_url") or "")
    expected_issue_url = (
        f"https://api.github.com/repos/{repository}/issues/{notification['github_issue']}"
    )
    if issue_url != expected_issue_url:
        raise NotificationError("notification ACK belongs to the wrong repository or Issue")
    comment_id = comment.get("id")
    comment_url = comment.get("html_url")
    if not isinstance(comment_id, int) or not isinstance(comment_url, str):
        raise NotificationError("notification ACK comment identity is incomplete")
    return {
        "notification_id": notification["notification_id"],
        "owner_comment_id": comment_id,
        "owner_comment_url": comment_url,
        "owner_login": login,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "authority_effect": "NONE",
    }


def acknowledge_notification(
    path,
    notification: dict[str, Any],
    comment: dict[str, Any],
    *,
    repository: str,
    owner_logins: list[str],
    occurred_at: str,
) -> tuple[dict[str, Any], bool]:
    receipt = acknowledgement_record_from_comment(
        comment, notification, repository=repository, owner_logins=owner_logins
    )
    events = goal_continuity.read_ledger(path)
    state = notification_state(events, notification["notification_id"])
    if state == "ACKNOWLEDGED":
        event = next(
            row for row in events
            if row["event_type"] == "NOTIFICATION_ACKNOWLEDGED"
            and row["payload"].get("notification_id") == notification["notification_id"]
        )
        if event["payload"] != receipt:
            raise NotificationError("notification was acknowledged by a different Owner record")
        return event, False
    if state != "SENT":
        raise NotificationError("notification must be SENT before Owner acknowledgment")
    return goal_continuity.append_ledger_event(
        path,
        event_id=f"{notification['notification_id']}-ack",
        event_type="NOTIFICATION_ACKNOWLEDGED",
        occurred_at=occurred_at,
        goal_id=notification["goal_id"],
        goal_version=notification["goal_version"],
        logical_work_id=None,
        attempt_id=None,
        payload=receipt,
    )


def queue_decision_notification(
    path, notification: dict[str, Any], *, occurred_at: str
) -> tuple[dict[str, Any], bool]:
    events = goal_continuity.read_ledger(path)
    state = notification_state(events, notification["notification_id"])
    if state is not None:
        existing = next(
            row for row in events
            if row["event_type"] == "NOTIFICATION_QUEUED"
            and row["payload"].get("notification_id") == notification["notification_id"]
        )
        if existing["payload"] != notification:
            raise NotificationError("notification deduplication key was reused with changed content")
        return existing, False
    return goal_continuity.append_ledger_event(
        path,
        event_id=f"{notification['notification_id']}-queued",
        event_type="NOTIFICATION_QUEUED",
        occurred_at=occurred_at,
        goal_id=notification["goal_id"],
        goal_version=notification["goal_version"],
        logical_work_id=None,
        attempt_id=None,
        payload=deepcopy(notification),
    )


def github_notification_body(notification: dict[str, Any]) -> str:
    marker = f"<!-- kgnote-product-goal-notification:{notification['notification_id']} -->"
    return (
        f"{marker}\n"
        f"## KGnote Product Goal 需要決策\n\n"
        f"- Goal：`{notification['goal_id']}` / `{notification['goal_version']}`\n"
        f"- 事件：`{notification['event_kind']}`\n"
        f"- 摘要：{notification['summary']}\n"
        f"- 請決定：{notification['decision_requested']}\n"
        f"- 通知 ID：`{notification['notification_id']}`\n\n"
        "此通知不授予執行權；Product Goal transition 仍須 exact Owner authority record。\n"
    )


def publish_github_notification(
    repository: str,
    notification: dict[str, Any],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Publish once and read back exactly; caller records NOTIFICATION_SENT."""
    endpoint = f"repos/{repository}/issues/{notification['github_issue']}/comments"
    body = github_notification_body(notification)
    marker = f"<!-- kgnote-product-goal-notification:{notification['notification_id']} -->"

    def read() -> list[dict[str, Any]]:
        result = command_runner(["gh", "api", endpoint, "--paginate"], capture_output=True, text=True)
        if result.returncode:
            raise NotificationError((result.stderr or "GitHub notification read failed").strip())
        rows = json.loads(result.stdout)
        if not isinstance(rows, list):
            raise NotificationError("GitHub notification read did not return a list")
        return rows

    matches = [row for row in read() if marker in str(row.get("body") or "")]
    if not matches:
        result = command_runner(
            ["gh", "api", endpoint, "-f", f"body={body}"], capture_output=True, text=True
        )
        if result.returncode:
            raise NotificationError((result.stderr or "GitHub notification write failed").strip())
        matches = [row for row in read() if marker in str(row.get("body") or "")]
    exact = [row for row in matches if row.get("body") == body]
    if len(exact) != 1 or len(matches) != 1:
        raise NotificationError("GitHub notification did not read back exactly once")
    if not isinstance(exact[0].get("id"), int) or not isinstance(
        exact[0].get("html_url"), str
    ):
        raise NotificationError("GitHub notification read-back identity is incomplete")
    return {
        "notification_id": notification["notification_id"],
        "transport": "GITHUB_NATIVE",
        "comment_id": exact[0].get("id"),
        "comment_url": exact[0].get("html_url"),
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "authority_effect": "NONE",
    }


def _notification_from_projection(projected: dict[str, Any]) -> dict[str, Any]:
    if not NOTIFICATION_FIELDS.issubset(projected):
        raise NotificationError("projected notification is missing its queued identity")
    return {key: deepcopy(projected[key]) for key in NOTIFICATION_FIELDS}


def deliver_queued_github_notifications(
    path,
    *,
    repository: str,
    max_attempts: int,
    now: datetime,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[dict[str, Any]]:
    """Deliver queued fallback notifications with durable bounded retries."""
    if now.tzinfo is None:
        raise NotificationError("notification delivery time must be timezone-aware")
    if max_attempts < 1:
        raise NotificationError("notification delivery max_attempts must be positive")
    outcomes: list[dict[str, Any]] = []
    events = goal_continuity.read_ledger(path)
    projection = goal_continuity.reduce_ledger(events)
    for notice_id, projected in sorted(projection["notifications"].items()):
        if notification_state(events, notice_id) != "QUEUED":
            continue
        notification = _notification_from_projection(projected)
        if notification["transport"] != "GITHUB_NATIVE":
            outcomes.append({
                "notification_id": notice_id,
                "status": "WAIT_VERIFIED_CHATGPT_WORK_DELIVERY_ADAPTER",
            })
            continue
        failures = [
            row for row in events
            if row["event_type"] == "NOTIFICATION_DELIVERY_FAILED"
            and row["payload"].get("notification_id") == notice_id
        ]
        if len(failures) >= max_attempts:
            outcomes.append({
                "notification_id": notice_id,
                "status": "DELIVERY_RETRY_EXHAUSTED",
                "attempts": len(failures),
            })
            continue
        if failures:
            retry_value = failures[-1]["payload"].get("retry_at")
            if isinstance(retry_value, str) and now < datetime.fromisoformat(retry_value):
                outcomes.append({
                    "notification_id": notice_id,
                    "status": "WAIT_DELIVERY_BACKOFF",
                    "retry_at": retry_value,
                })
                continue
        try:
            receipt = publish_github_notification(
                repository, notification, command_runner=command_runner
            )
        except (NotificationError, json.JSONDecodeError) as exc:
            failure_number = len(failures) + 1
            retry_at = now + timedelta(minutes=5)
            goal_continuity.append_ledger_event(
                path,
                event_id=f"{notice_id}-delivery-failed-{failure_number}",
                event_type="NOTIFICATION_DELIVERY_FAILED",
                occurred_at=now.isoformat(),
                goal_id=notification["goal_id"],
                goal_version=notification["goal_version"],
                logical_work_id=None,
                attempt_id=None,
                payload={
                    "notification_id": notice_id,
                    "transport": "GITHUB_NATIVE",
                    "failure_number": failure_number,
                    "error_sha256": hashlib.sha256(str(exc).encode("utf-8")).hexdigest(),
                    "retry_at": retry_at.isoformat(),
                    "authority_effect": "NONE",
                },
            )
            outcomes.append({
                "notification_id": notice_id,
                "status": "DELIVERY_FAILED_RETRY_SCHEDULED",
                "attempts": failure_number,
                "retry_at": retry_at.isoformat(),
            })
        else:
            goal_continuity.append_ledger_event(
                path,
                event_id=f"{notice_id}-sent",
                event_type="NOTIFICATION_SENT",
                occurred_at=now.isoformat(),
                goal_id=notification["goal_id"],
                goal_version=notification["goal_version"],
                logical_work_id=None,
                attempt_id=None,
                payload=receipt,
            )
            outcomes.append({
                "notification_id": notice_id,
                "status": "SENT_READ_BACK_VERIFIED",
                "comment_id": receipt["comment_id"],
                "comment_url": receipt["comment_url"],
            })
        events = goal_continuity.read_ledger(path)
    return outcomes


def reconcile_owner_acknowledgements(
    path,
    comments: list[dict[str, Any]],
    *,
    repository: str,
    owner_logins: list[str],
    observed_at: str,
) -> dict[str, list[dict[str, Any]]]:
    """Consume matching Owner ACKs without granting Product Goal authority."""
    events = goal_continuity.read_ledger(path)
    projection = goal_continuity.reduce_ledger(events)
    acknowledged: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for notice_id, projected in sorted(projection["notifications"].items()):
        if notification_state(events, notice_id) != "SENT":
            continue
        notification = _notification_from_projection(projected)
        candidates = [
            row for row in comments
            if ACK_MARKER in str(row.get("body") or "")
            and notice_id in str(row.get("body") or "")
        ]
        for comment in candidates:
            try:
                event, appended = acknowledge_notification(
                    path, notification, comment,
                    repository=repository, owner_logins=owner_logins,
                    occurred_at=(
                        comment.get("created_at")
                        if isinstance(comment.get("created_at"), str)
                        else observed_at
                    ),
                )
            except (NotificationError, json.JSONDecodeError) as exc:
                rejected.append({
                    "notification_id": notice_id,
                    "comment_id": comment.get("id"),
                    "reason": str(exc),
                })
                continue
            acknowledged.append({
                "notification_id": notice_id,
                "comment_id": event["payload"]["owner_comment_id"],
                "appended": appended,
            })
            events = goal_continuity.read_ledger(path)
            break
    return {"acknowledged": acknowledged, "rejected": rejected}
