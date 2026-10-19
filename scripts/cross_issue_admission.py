#!/usr/bin/env python3
"""Trusted one-time preparation for an already authorized Ready Issue.

This module does not discover or invent product work.  It accepts a fully
sealed ready-queue record, verifies the live GitHub Issue, creates one local
worktree and Draft PR, and emits one epoch-admitted Ubuntu work order.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


class AdmissionError(RuntimeError):
    pass


def _run(command: list[str], *, cwd: Path, runner: Callable[..., subprocess.CompletedProcess[str]]) -> str:
    result = runner(command, cwd=cwd, text=True, capture_output=True, timeout=120, check=False)
    if result.returncode:
        raise AdmissionError(result.stderr.strip() or result.stdout.strip() or f"command failed: {command[0]}")
    return result.stdout.strip()


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _authorized_local_worktree(value: object) -> Path:
    """Expand only the explicitly supported public-safe home placeholder."""
    raw = str(value)
    if not raw.startswith("${HOME}/") or raw.count("${HOME}") != 1:
        raise AdmissionError("local worktree must use the exact ${HOME}/... identity")
    home = Path(os.environ.get("HOME", "")).resolve()
    if not str(home) or str(home) == "/":
        raise AdmissionError("HOME is unavailable for local worktree resolution")
    return (home / raw.removeprefix("${HOME}/")).resolve()


def validate_item(item: object, current: datetime) -> dict[str, Any]:
    if not isinstance(item, dict) or item.get("status") != "ADMISSION_PENDING":
        raise AdmissionError("ready item is not pending formal admission")
    authority = item.get("authority")
    budget = item.get("budget")
    safety = item.get("safety")
    admission = item.get("admission")
    if not isinstance(authority, dict) or authority.get("status") != "APPROVED":
        raise AdmissionError("explicit product/execution authority is missing")
    if not isinstance(budget, dict) or budget.get("authorized") != 1 or budget.get("used") != 0:
        raise AdmissionError("cross-Issue implementation budget must be exactly one unused dispatch")
    if not isinstance(safety, dict) or safety.get("isolated_worktree") is not True or safety.get("automatic_merge") is not False:
        raise AdmissionError("isolated worktree and automatic_merge=false are required")
    if not isinstance(admission, dict):
        raise AdmissionError("sealed admission metadata is missing")
    required = {
        "repository", "issue", "goal_id", "work_item_id", "branch", "worktree_slug",
        "authority_record", "authority_sha256", "source_commit", "local_worktree",
    }
    if required - set(admission):
        raise AdmissionError(f"sealed admission fields are missing: {sorted(required - set(admission))}")
    repository, issue = admission["repository"], admission["issue"]
    if repository != "joannalee20050914/KGnote-public" or not isinstance(issue, int) or issue < 1:
        raise AdmissionError("repository or Issue identity is invalid")
    if admission["authority_record"] != f"https://github.com/{repository}/issues/{issue}":
        raise AdmissionError("authority record does not match the exact Issue")
    if not re.fullmatch(r"[0-9a-f]{64}", str(admission["authority_sha256"])):
        raise AdmissionError("authority digest is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(admission["source_commit"])):
        raise AdmissionError("source commit is invalid")
    if not re.fullmatch(r"GOAL-KGNOTE-[A-Z0-9-]+", str(admission["goal_id"])):
        raise AdmissionError("goal identity is invalid")
    if not re.fullmatch(r"D2-T[0-9]{2}", str(admission["work_item_id"])):
        raise AdmissionError("work item identity is invalid")
    if admission["worktree_slug"] != f"issue-{issue}-{str(admission['work_item_id']).lower()}":
        raise AdmissionError("worktree slug is not derived from Issue/work-item identity")
    if not re.fullmatch(r"codex/[a-z0-9][a-z0-9-]{2,80}", str(admission["branch"])):
        raise AdmissionError("branch is not a bounded codex/* branch")
    if current.weekday() >= 5 or not (9 <= current.hour < 18):
        raise AdmissionError("outside the authorized Asia/Taipei work window")
    return admission


def _live_issue(repo: Path, admission: dict[str, Any], runner: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, Any]:
    raw = _run([
        "/opt/homebrew/bin/gh", "issue", "view", str(admission["issue"]),
        "--repo", admission["repository"], "--json", "number,state,labels,body,title,url",
    ], cwd=repo, runner=runner)
    try:
        issue = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AdmissionError("GitHub Issue read-back is invalid") from exc
    labels = {entry.get("name") for entry in issue.get("labels", []) if isinstance(entry, dict)}
    body = issue.get("body")
    if issue.get("number") != admission["issue"] or issue.get("state") != "OPEN" or "queue:ready" not in labels:
        raise AdmissionError("GitHub Issue is not the exact open queue:ready authority")
    if not isinstance(body, str) or hashlib.sha256(body.encode()).hexdigest() != admission["authority_sha256"]:
        raise AdmissionError("GitHub Issue authority bytes changed after sealing")
    if issue.get("url") != admission["authority_record"]:
        raise AdmissionError("GitHub Issue authority URL mismatch")
    return issue


def _plan_markdown(admission: dict[str, Any]) -> str:
    plan = {
        "schema_version":"kgnote.codex-plan.v1", "goal_id":admission["goal_id"],
        "objective":"Issue #14/D2-T07：有限確認外部 AI 導師的受支援授權能力，保留 copy-safe manual handoff/import 與 delta de-duplication；不啟用 cookie automation、live data、付費或自動 merge。",
        "status":"active", "active_milestone_id":"D2-T07-BOUNDED-FEASIBILITY",
        "product_direction_id":"kgnote-obsidian-first-2026-09-22",
        "requirements_baseline_id":"kgnote-stage2b-feature-disposition-ledger-2026-10-16",
        "explicit_direction":{"date":"2026-10-19","speaker":"product owner","source_path":admission["authority_record"],"durable_goal_record":"PLAN.md"},
        "requirement_context":{"github_issue":admission["authority_record"],"feature_dispositions":["FD-11"],"acceptance_criteria":["RC-20","RC-21","RC-28","RC-31"],"requirements":["KG-MEM-08","KG-PLAT-03"],"scenarios":["SC-03","SC-32"],"forbidden_substitutes":["browser-cookie automation","未授權資料外送","自動付費","把手動 fallback 當成自動 connector 已驗證"]},
        "auto_advance":{"enabled":True,"requires_dependencies_complete":True,"automatic_merge":False,"implementation_dispatch_budget":1,"claude_review_budget_added":0},
        "milestones":[{"id":"D2-T07-BOUNDED-FEASIBILITY","title":"合法授權與手動備援有限驗證","status":"active","dependencies":[],"human_gate":"none","owned_paths":["PLAN.md","CODEX_STATUS.md",".ai/CROSS_ISSUE_ADMISSION.json",".ai/work-package-envelope.json",".ai/DECISIONS.md",".ai/ORCHESTRATOR_STATE.json",".ai/REVIEW_REQUEST.md",".ai/REVIEW_RESULT.md",f".ai/WORK_ITEM_REVIEW_HISTORY/{admission['worktree_slug']}/","docs/control-plane/","scripts/codex_control.py","scripts/cross_issue_admission.py","src/kgnote/","tests/"],"acceptance":["官方授權能力有來源證據或明確 unsupported 結論","manual handoff/import fallback 可操作","round-trip delta 不重複 evidence","不啟用 live provider、cookie automation、資料外送或付費"],"stop_conditions":["需要 live data、付費、cookie 擷取、資料外送或新增 reviewer 額度","超出一次 Codex implementation dispatch"]}],
    }
    return "# KGnote active execution plan\n\n<!-- BEGIN CODEX PLAN JSON -->\n```json\n" + json.dumps(plan,ensure_ascii=False,indent=2) + "\n```\n<!-- END CODEX PLAN JSON -->\n\n## Current recovery note\n\n由正式 cross-Issue admission 建立；先執行 preflight，僅處理 Issue #14 有界範圍。\n"


def _status_markdown(admission: dict[str, Any], branch: str, source_commit: str) -> str:
    status = {
        "schema_version":"kgnote.codex-status.v1","updated_at":"2026-10-19T15:30:00+08:00",
        "goal_id":admission["goal_id"],"goal_status":"active","active_milestone_id":"D2-T07-BOUNDED-FEASIBILITY","milestone_status":"active",
        "product_direction_id":"kgnote-obsidian-first-2026-09-22","requirements_baseline_id":"kgnote-stage2b-feature-disposition-ledger-2026-10-16",
        "git":{"branch":branch,"head":source_commit,"base_commit":source_commit,"checkpoint_commit":source_commit},
        "working_state":{"fingerprint_algorithm":"sha256-canonical-json-v3-branch-independent-review-bus-exclusions","fingerprint":None,"starting_fingerprint":None,"expected_dirty_policy":"Only Issue #14 admission, bounded feasibility implementation, tests and evidence may change.","preserved_preexisting_dirty_paths":[],"unexpected_dirty_paths":[]},
        "implementation_state":"IMPLEMENTING","review":{"state":"IMPLEMENTING","current_review_id":None,"candidate_revision":None,"candidate_fingerprint":None,"unresolved_findings":[],"human_decision_blockers":[]},
        "verification":{"candidate_verified":False,"release_verified":False,"control_plane_ready":True,"last_candidate_evidence":None,"last_verified_fingerprint":None,"last_result":"Cross-Issue admission initialized; product verification not yet run."},
        "next_action":"Run preflight, then execute the single bounded Issue #14 feasibility implementation without live provider, paid service or data egress.",
        "external_or_human_gates":[],"forbidden_during_goal":["automatic merge","live provider","browser-cookie automation","unapproved data egress","paid API","new Claude review budget"],
    }
    return "# KGnote Codex status\n\n<!-- BEGIN CODEX STATUS JSON -->\n```json\n" + json.dumps(status,ensure_ascii=False,indent=2) + "\n```\n<!-- END CODEX STATUS JSON -->\n\n## Human-readable handoff\n\nIssue #14 admitted for exactly one bounded Codex implementation dispatch.\n"


def _initialize_review_scope(worktree: Path, admission: dict[str, Any]) -> list[str]:
    """Start the existing review bus in a work-item scope without rewriting prior Issue history."""
    history_relative = f".ai/WORK_ITEM_REVIEW_HISTORY/{admission['worktree_slug']}"
    history = worktree / history_relative
    _atomic_text(history / "events.jsonl", "")
    _atomic_json(history / "index.json", {
        "schema_version":"kgnote.review-history-index.v1", "protocol_version":"kgnote.review-protocol.v1",
        "event_count":0, "last_event_id":None, "reviews":{}, "findings":{},
    })
    review_id = "review-issue-14-tutor-handoff-001"
    request = {
        "schema_version":"kgnote.review-request.v1", "protocol_version":"kgnote.review-protocol.v1",
        "review_id":review_id, "goal_id":admission["goal_id"], "milestone_id":"D2-T07-BOUNDED-FEASIBILITY",
        "status":"IMPLEMENTING", "author_role":"CODEX_IMPLEMENTER", "base_revision":admission["source_commit"],
        "candidate_revision":None, "candidate_fingerprint":None, "candidate_manifest":None,
        "authorized_human_decision_identities":["product owner"],
        "authoritative_specs":["docs/control-plane/AUTHORITY.md","docs/requirements/FEATURE_DISPOSITION_LEDGER.md","PLAN.md"],
        "changed_areas":["Issue #14 bounded manual tutor handoff and pasted-delta import"],
        "acceptance_criteria":["official authorization proof or explicit unsupported conclusion","manual fallback round trip does not duplicate evidence"],
        "negative_requirements":["no live provider","no cookies","no data egress","no paid API","no automatic merge"],
        "validation_performed":[], "validation_results":[], "known_deviations":[], "known_uncertainties":[],
        "reviewer_focus":[], "preserved_human_gates":["PA-HUMAN-1","NS-HUMAN-SMOKE","release_verified=false"],
        "requested_at":None,
    }
    request_text = (
        "# Current review request\n\nWriter: Codex implementation agent. The JSON block is canonical; prose outside it is explanatory only.\n\n"
        "<!-- BEGIN KGNOTE REVIEW REQUEST JSON -->\n```json\n" + json.dumps(request,ensure_ascii=False,indent=2) +
        "\n```\n<!-- END KGNOTE REVIEW REQUEST JSON -->\n\n## Human-readable status\n\n"
        f"Review `{review_id}` is `IMPLEMENTING`.\n"
        "It has no active candidate binding and cannot be interpreted as a review request or PASS.\n"
        "Codex must complete deterministic verification before issuing this request.\n"
    )
    _atomic_text(worktree/".ai/REVIEW_REQUEST.md",request_text)
    result = {
        "schema_version":"kgnote.review-result.v1", "protocol_version":"kgnote.review-protocol.v1",
        "artifact_state":"EMPTY", "review_id":None, "author_role":None, "reviewer_identity":None,
        "reviewed_revision":None, "reviewed_fingerprint":None, "verdict":None, "findings":[],
        "verified_requirements":[], "unverified_requirements":[], "human_decisions_required":[],
        "human_gates_preserved":[], "reviewed_at":None,
    }
    _atomic_text(worktree/".ai/REVIEW_RESULT.md","# Current review result\n\nWriter after reviewer custody: independent reviewer only.\n\n<!-- BEGIN KGNOTE REVIEW RESULT JSON -->\n```json\n"+json.dumps(result,ensure_ascii=False,indent=2)+"\n```\n<!-- END KGNOTE REVIEW RESULT JSON -->\n")
    decisions={"schema_version":"kgnote.review-decisions.v1","protocol_version":"kgnote.review-protocol.v1","decisions":[]}
    _atomic_text(worktree/".ai/DECISIONS.md","# Product and architecture decision queue\n\n<!-- BEGIN KGNOTE DECISIONS JSON -->\n```json\n"+json.dumps(decisions,ensure_ascii=False,indent=2)+"\n```\n<!-- END KGNOTE DECISIONS JSON -->\n")
    orchestrator={
        "schema_version":"kgnote.orchestrator-state.v1", "run_id":"cross-issue-admission-14",
        "active_goal":admission["goal_id"], "work_package":"D2-T07-BOUNDED-FEASIBILITY", "state":"IMPLEMENTING",
        "current_agent":None, "candidate_fingerprint":None, "review_id":None, "review_cycle":0,
        "max_review_cycles":1, "agent_failures":0, "max_agent_failures":1, "empty_reviewer_results":0,
        "blockers":[], "next_action":"Execute the one authorized bounded implementation dispatch.",
        "human_action_required":False, "candidate_custody":{"status":"NONE","owner":None,"review_id":None,"fingerprint":None},
        "next_human_checkpoint":{"id":"D2-T14-FINAL-HUMAN-ACCEPTANCE","status":"not_eligible_incomplete_product_scope"},
        "last_agent_run":None, "created_at":"2026-10-19T15:30:00+08:00", "updated_at":"2026-10-19T15:30:00+08:00",
    }
    _atomic_json(worktree/".ai/ORCHESTRATOR_STATE.json",orchestrator)
    return [history_relative+"/events.jsonl",history_relative+"/index.json",".ai/REVIEW_REQUEST.md",".ai/REVIEW_RESULT.md",".ai/DECISIONS.md",".ai/ORCHESTRATOR_STATE.json"]


def _initialize_worktree(repo: Path, admission: dict[str, Any], runner: Callable[..., subprocess.CompletedProcess[str]]) -> tuple[Path, str]:
    worktree = _authorized_local_worktree(admission["local_worktree"])
    if worktree.parent != repo.parent.resolve() or worktree.name != "KGnote-public-issue14-tutor-handoff":
        raise AdmissionError("local worktree is outside the one authorized sibling path")
    branch, source = admission["branch"], admission["source_commit"]
    _run(["/usr/bin/git", "cat-file", "-e", f"{source}^{{commit}}"], cwd=repo, runner=runner)
    if not worktree.exists():
        existing = runner(
            ["/usr/bin/git","show-ref","--verify","--quiet",f"refs/heads/{branch}"],
            cwd=repo, text=True, capture_output=True, timeout=120, check=False,
        )
        command = ["/usr/bin/git","worktree","add"]
        command += [str(worktree),branch] if existing.returncode == 0 else ["-b",branch,str(worktree),source]
        _run(command,cwd=repo,runner=runner)
    observed_branch = _run(["/usr/bin/git","branch","--show-current"],cwd=worktree,runner=runner)
    if observed_branch != branch:
        raise AdmissionError("local worktree branch identity mismatch")
    marker_path = worktree / ".ai/CROSS_ISSUE_ADMISSION.json"
    if not marker_path.exists():
        _atomic_text(worktree/"PLAN.md",_plan_markdown(admission))
        _atomic_text(worktree/"CODEX_STATUS.md",_status_markdown(admission,branch,source))
        marker={"schema_version":"kgnote.cross-issue-admission.v1","status":"SEALED","admission":admission,"implementation_dispatch_budget":{"authorized":1,"used":0},"claude_review_budget_added":0,"automatic_merge":False,"review_history_root":f".ai/WORK_ITEM_REVIEW_HISTORY/{admission['worktree_slug']}"}
        _atomic_json(marker_path,marker)
        envelope={"schema_version":"kgnote.work-package-envelope.v1","status":"APPROVED","goal_id":admission["goal_id"],"work_package_id":"D2-T07-BOUNDED-FEASIBILITY","authority_record":admission["authority_record"],"approval":{"source_status":"RECONCILING","receipt":".ai/CROSS_ISSUE_ADMISSION.json"},"work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},"budgets":{"local_repairs":{"authorized":1,"used":0},"internal_reviews":{"authorized":0,"used":0},"external_reviews":{"authorized":0,"used":0}}}
        _atomic_json(worktree/".ai/work-package-envelope.json",envelope)
        scoped_review_paths=_initialize_review_scope(worktree,admission)
        shared_venv=repo/".venv"; worktree_venv=worktree/".venv"
        if shared_venv.is_dir() and not worktree_venv.exists():
            worktree_venv.symlink_to(shared_venv,target_is_directory=True)
        _run(["/usr/bin/git","add","--","PLAN.md","CODEX_STATUS.md",".ai/CROSS_ISSUE_ADMISSION.json",".ai/work-package-envelope.json",*scoped_review_paths],cwd=worktree,runner=runner)
        _run(["/usr/bin/git","commit","-m","初始化 Issue #14 有界自動入場"],cwd=worktree,runner=runner)
    head=_run(["/usr/bin/git","rev-parse","HEAD"],cwd=worktree,runner=runner)
    return worktree,head


def prepare(
    repo: Path, item: dict[str, Any], current: datetime,
    *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    admission=validate_item(item,current)
    issue=_live_issue(repo,admission,runner)
    worktree,head=_initialize_worktree(repo,admission,runner)
    _run(["/usr/bin/git","push","origin",f"HEAD:refs/heads/{admission['branch']}"],cwd=worktree,runner=runner)
    remote=json.loads(_run(["/opt/homebrew/bin/gh","api",f"repos/{admission['repository']}/git/ref/heads/{admission['branch']}"],cwd=repo,runner=runner))
    if ((remote.get("object") or {}).get("sha")) != head:
        raise AdmissionError("remote branch exact HEAD read-back mismatch")
    listed=json.loads(_run(["/opt/homebrew/bin/gh","pr","list","--repo",admission["repository"],"--head",admission["branch"],"--state","all","--json","number,state,isDraft,headRefName,baseRefName,url"],cwd=repo,runner=runner))
    if listed:
        pr=listed[0]
    else:
        made=_run(["/opt/homebrew/bin/gh","pr","create","--repo",admission["repository"],"--base","main","--head",admission["branch"],"--draft","--title","[D2-T07] 外部 AI 導師合法授權與手動備援","--body",f"本 Draft PR 由既有 Runner 依 Issue #{admission['issue']} 與 2026-10-19 產品擁有人授權建立。只允許一次 Codex implementation dispatch；不自動 merge、不新增 Claude review 額度、不啟用 live provider、cookie automation、資料外送或付費。\n\nCloses #{admission['issue']}"],cwd=repo,runner=runner)
        number=int(made.rstrip("/").split("/")[-1])
        pr=json.loads(_run(["/opt/homebrew/bin/gh","pr","view",str(number),"--repo",admission["repository"],"--json","number,state,isDraft,headRefName,baseRefName,url,headRefOid"],cwd=repo,runner=runner))
    if pr.get("state")!="OPEN" or pr.get("isDraft") is not True or pr.get("headRefName")!=admission["branch"] or pr.get("baseRefName")!="main":
        raise AdmissionError("Draft PR exact identity read-back mismatch")
    fingerprint=json.loads(_run([sys.executable,str(worktree/"scripts/codex_control.py"),"--repo",str(worktree),"fingerprint"],cwd=worktree,runner=runner))["value"]
    identity={"schema_version":"kgnote.authorized-work-identity.v1",**{k:admission[k] for k in ("repository","issue","goal_id","work_item_id","branch","worktree_slug","authority_record","authority_sha256")}}
    deadline=current.replace(hour=18,minute=0,second=0,microsecond=0)
    out=repo/"output/control-plane/production-runner"; order_path=out/"issue-14-d2-t07-linux-worker-order.json"
    prompt=("Implement only the owner-authorized Issue #14/D2-T07 bounded feasibility spike. Read AGENTS.md, PLAN.md, CODEX_STATUS.md and authority first. Preserve PR #26 and every existing budget. Verify supported official authorization documentation, implement the copy-safe manual handoff/import fallback and a delta de-dup round-trip fixture where missing. Do not use browser cookies, live user data, paid services, data egress, Claude review, automatic merge, or main. Run targeted deterministic tests and leave a durable checkpoint before exit.")
    order={"event_id":"issue-14-d2-t07-codex-20261019","stage":"codex","working_directory":"/home/kgnote/.local/share/kgnote/work-items/issue-14-d2-t07","command":["/home/kgnote/.local/bin/kgnote-successor-codex","--goal-id",admission["goal_id"],"--pull-request",str(pr["number"]),"--cycle","1",admission["repository"],admission["branch"],head,prompt],"checkpoint_path":str(out/"issue-14-d2-t07-codex-route.json"),"memory_max":"4G","tasks_max":192,"timeout_seconds":max(1,min(3600,int((deadline-current).total_seconds()))),"lease_timeout_seconds":8,"deadline_at":deadline.isoformat(),"bootstrap_working_directory":True,"bootstrap_identity":identity,"execution_context":{"schema_version":"kgnote.model-execution-evidence.v1","role":"CODEX_IMPLEMENTER","goal_id":admission["goal_id"],"pull_request":pr["number"],"cycle":1,"provider":"OpenAI","authentication":"ChatGPT OAuth","requested_model":"gpt-5.6-terra","requested_effort":"medium","configuration_status":"CONFIGURED","effective_status":"EFFECTIVE_UNKNOWN","token_usage":None},"review_admission":{"admission_kind":"IMPLEMENTATION","repository":admission["repository"],"pull_request":pr["number"],"head_sha":head,"candidate_fingerprint":fingerprint,"authority":{"status":"APPROVED","goal_id":admission["goal_id"],"authority_record":admission["authority_record"]},"implementation_budget":{"authorized":1,"used":0},"work_window_allowed":True,"stop_marker_clear":True,"existing_exact_candidate_result":False}}
    _atomic_json(order_path,order)
    return {"status":"READY","worktree":str(worktree),"head":head,"fingerprint":fingerprint,"pull_request":pr["number"],"pull_request_url":pr["url"],"order_path":str(order_path.relative_to(repo)),"issue_title":issue["title"]}
