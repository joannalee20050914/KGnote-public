from __future__ import annotations
import importlib.util, json, subprocess, sys, tempfile, unittest
import hashlib
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch
from tests.control_plane.runtime_admission_fixtures import (
    activation_dependency_receipts,
    prepare_model_reservation,
    product_goal_spec,
    runtime_identity,
    write_reservation_receipt,
)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
SPEC = importlib.util.spec_from_file_location("runner", ROOT / "scripts/local_autonomy_runner.py")
RUNNER = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(RUNNER)

class RunnerTests(unittest.TestCase):
    def install_carryover_evidence(self, repo: Path, spec: dict) -> None:
        relative = Path(spec["history_carryover"]["evidence_path"])
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())

    def test_o2_first_window_runner_binds_seed_bootstraps_checkout_and_reserves_once(self):
        """Exercise the real first-dispatch boundary without launching a model."""
        from tests.control_plane.test_github_product_goal_control import comment
        import codex_control
        import goal_continuity as goal
        import linux_worker_bootstrap as bootstrap
        import product_goal_worker_identity as identity

        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/"source"; origin=root/"origin.git"
            central=root/"central"; deploy=root/"deploy"; runtime=root/"runtime"
            spec=product_goal_spec()
            source.mkdir(); runtime.mkdir()
            self.install_carryover_evidence(source, spec)
            subprocess.run(["git","init","-b",identity.PRODUCT_BRANCH],cwd=source,check=True,capture_output=True)
            subprocess.run(["git","config","user.email","test@example.invalid"],cwd=source,check=True)
            subprocess.run(["git","config","user.name","Test"],cwd=source,check=True)
            (source/".gitignore").write_text("output/\n")
            (source/"seed.txt").write_text("seed\n")
            (source/"scripts").mkdir()
            for name in ("router.py","admission.py"):
                (source/"scripts"/name).write_text("# trusted fixture\n")
            subprocess.run(["git","add","."],cwd=source,check=True)
            subprocess.run(["git","commit","-m","seed"],cwd=source,check=True,capture_output=True)
            seed=subprocess.check_output(["git","rev-parse","HEAD"],cwd=source,text=True).strip()
            subprocess.run(["git","clone","--bare",str(source),str(origin)],check=True,capture_output=True)
            subprocess.run(["git","clone",str(origin),str(central)],check=True,capture_output=True)
            subprocess.run(["git","config","user.email","test@example.invalid"],cwd=central,check=True)
            subprocess.run(["git","config","user.name","Test"],cwd=central,check=True)
            subprocess.run(["git","switch","-c","codex/hotfix-fixture"],cwd=central,check=True,capture_output=True)
            (central/"hotfix.txt").write_text("runner hotfix\n")
            subprocess.run(["git","add","hotfix.txt"],cwd=central,check=True)
            subprocess.run(["git","commit","-m","hotfix"],cwd=central,check=True,capture_output=True)
            hotfix=subprocess.check_output(["git","rev-parse","HEAD"],cwd=central,text=True).strip()
            subprocess.run(["git","worktree","add","--detach",str(deploy),hotfix],cwd=central,check=True,capture_output=True)

            spec_path=runtime/"spec.json"; state_path=runtime/"state.json"
            ledger_path=runtime/"ledger.jsonl"; comments_path=runtime/"comments.json"
            spec_path.write_text(json.dumps(spec))
            goal.atomic_write_json(
                state_path,
                goal.initial_runner_state(
                    spec,now="2026-10-29T16:00:00+08:00",
                    dependency_receipts=activation_dependency_receipts(spec),
                ),
            )
            authority_comment=comment(spec,login="joannalee20050914")
            authority_comment["html_url"]="https://github.com/joannalee20050914/KGnote-public/issues/9#issuecomment-6431195804"
            authority_comment["issue_url"]="https://api.github.com/repos/joannalee20050914/KGnote-public/issues/9"
            comments_path.write_text(json.dumps([authority_comment]))
            epoch=runtime/"epoch.json"; epoch.write_text("{}")
            router=deploy/"scripts/router.py"; admission=deploy/"scripts/admission.py"
            calls=[]
            def no_model(command,**kwargs):
                calls.append(command)
                if "--discover-runtime" in command:
                    return subprocess.CompletedProcess(
                        command,0,json.dumps(runtime_identity()),"",
                    )
                if "--admit-order" in command:
                    order=Path(command[command.index("--admit-order")+1])
                    receipt=write_reservation_receipt(
                        deploy,order,
                        observed_at=datetime(2026,10,29,17,0,tzinfo=ZoneInfo("Asia/Taipei")),
                    )
                    expected=Path(command[command.index("--admission-receipt")+1])
                    expected.parent.mkdir(parents=True,exist_ok=True)
                    expected.write_bytes(receipt.read_bytes())
                    return subprocess.CompletedProcess(command,0,expected.read_text(),"")
                return subprocess.CompletedProcess(command,0,"{}\n","")

            patches=(
                patch.object(RUNNER.goal_runner_adapter.product_goal_worker_identity,"PRODUCT_REPOSITORY_URL",str(origin)),
                patch.object(RUNNER.goal_runner_adapter.product_goal_worker_identity,"PRODUCT_SEED_COMMIT",seed),
                patch.object(bootstrap,"PRODUCT_REPOSITORY_URL",str(origin)),
            )
            with patches[0],patches[1],patches[2]:
                before=RUNNER.run_product_goal_mode(
                    deploy,spec_path=spec_path,state_path=state_path,ledger_path=ledger_path,
                    comments_path=comments_path,backlog_path=None,trial=False,router=router,
                    epoch_record=epoch,admission=admission,runner_identity={"sha256":"fixture"},
                    current=datetime(2026,10,29,16,59,tzinfo=ZoneInfo("Asia/Taipei")),command_runner=no_model,
                )
                self.assertEqual("WAIT_TRIAL_START",before["status"])
                self.assertEqual(0,len(goal.reduce_ledger(goal.read_ledger(ledger_path))["dispatch_reservations"]))
                pre_dispatch=deepcopy(goal.load_json(state_path))

                first=RUNNER.run_product_goal_mode(
                    deploy,spec_path=spec_path,state_path=state_path,ledger_path=ledger_path,
                    comments_path=comments_path,backlog_path=None,trial=False,router=router,
                    epoch_record=epoch,admission=admission,runner_identity={"sha256":"fixture"},
                    current=datetime(2026,10,29,17,0,tzinfo=ZoneInfo("Asia/Taipei")),command_runner=no_model,
                )
                self.assertEqual("DISPATCHED",first["status"])
                saved=goal.load_json(state_path)
                self.assertEqual(seed,saved["candidate_identity"]["commit"])
                self.assertIsNone(saved["candidate_identity"]["pull_request"])
                binding=saved["work_items"][0]["dispatch_binding"]
                order_path=deploy/binding["order_path"]
                self.assertEqual(binding["order_sha256"],hashlib.sha256(order_path.read_bytes()).hexdigest())
                order=json.loads(order_path.read_text())
                lane=json.loads(order["command"][order["command"].index("--command-json")+1])
                nested=json.loads(lane[lane.index("--command-json")+1])
                self.assertEqual("0",nested[nested.index("--pull-request")+1])

                guest=root/"ubuntu"
                with patch.object(bootstrap,"WORKTREE_ROOT",guest),patch.object(bootstrap,"GENERIC_ROOT",guest/"work-items"),patch.object(
                    bootstrap,"_validate_product_dev_environment",
                    return_value={"status":"DEVELOPMENT_ENVIRONMENT_READY","versions":{}},
                ):
                    guest.mkdir(mode=0o700)
                    checkout=bootstrap.prepare(
                        order["event_id"],order["stage"],guest/"work-items/goal-o2-reading-experience",
                        order["bootstrap_identity"],
                    )
                self.assertEqual("CHECKOUT_READY",checkout["checkout"]["status"])
                self.assertEqual(
                    saved["candidate_identity"]["fingerprint"],
                    codex_control.repository_fingerprint(guest/"work-items/goal-o2-reading-experience")["value"],
                )

                call_count=len(calls)
                replay=RUNNER.run_product_goal_mode(
                    deploy,spec_path=spec_path,state_path=state_path,ledger_path=ledger_path,
                    comments_path=comments_path,backlog_path=None,trial=False,router=router,
                    epoch_record=epoch,admission=admission,runner_identity={"sha256":"fixture"},
                    current=datetime(2026,11,2,9,0,tzinfo=ZoneInfo("Asia/Taipei")),command_runner=no_model,
                )
                self.assertEqual("CHECKPOINT_PENDING",replay["status"])
                self.assertEqual(call_count,len(calls))
                projection=goal.reduce_ledger(goal.read_ledger(ledger_path))
                self.assertEqual(1,len(projection["dispatch_reservations"]))
                self.assertEqual(1,len(projection["model_attempts"]))

                at_close=RUNNER.goal_runner_adapter.next_action(
                    spec,pre_dispatch,goal.read_ledger(ledger_path)[:3],
                    RUNNER.goal_runner_adapter.github_control.resolve_authority([authority_comment],spec),
                    now=datetime(2026,11,2,18,0,tzinfo=ZoneInfo("Asia/Taipei")),trial=False,
                )
                self.assertEqual("WAIT_WORK_WINDOW",at_close["status"])
                hard=RUNNER.goal_runner_adapter.trial_schedule_admission(
                    spec,datetime(2026,11,13,18,0,tzinfo=ZoneInfo("Asia/Taipei"))
                )
                self.assertEqual("GOAL_HARD_STOP",hard["status"])

    def test_product_goal_mode_never_bypasses_existing_stop_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".ai").mkdir()
            (repo / ".ai" / "ORCHESTRATOR_STOP").write_text("stop\n")
            result = RUNNER.run_product_goal_mode(
                repo,
                spec_path=repo / "missing-spec.json",
                state_path=repo / "missing-state.json",
                ledger_path=repo / "missing-ledger.jsonl",
                comments_path=None,
                backlog_path=None,
                trial=False,
                router=repo / "missing-router.py",
                epoch_record=repo / "missing-epoch.json",
                admission=repo / "missing-admission.py",
                runner_identity={"sha256": "test"},
            )
            self.assertEqual("STOPPED", result["status"])

    def test_product_goal_tick_delivers_queued_github_notice_with_readback(self):
        from tests.control_plane.test_goal_continuity import product_goal_spec
        from tests.control_plane.test_github_product_goal_control import comment
        import goal_continuity as goal

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".ai").mkdir()
            spec = product_goal_spec()
            state = goal.initial_runner_state(
                spec, now="2026-10-22T10:00:00+08:00"
            )
            spec_path, state_path = repo / "spec.json", repo / "state.json"
            ledger_path, comments_path = repo / "ledger.jsonl", repo / "comments.json"
            spec_path.write_text(json.dumps(spec))
            goal.atomic_write_json(state_path, state)
            comments_path.write_text(json.dumps([comment(spec)]))
            notice = RUNNER.goal_runner_adapter.goal_notifications.build_notification(
                goal_id=spec["goal_id"], goal_version=spec["goal_version"],
                event_kind="PRODUCT_WHAT_CONFLICT", decision_key="exact-conflict",
                summary="受影響的 Work Item 已停止，獨立工作仍可繼續。",
                decision_requested="以新的 exact Goal 版本裁決產品 WHAT。",
                github_issue=spec["github_issue"],
            )
            RUNNER.goal_runner_adapter.goal_notifications.queue_decision_notification(
                ledger_path, notice, occurred_at="2026-10-22T10:00:00+08:00"
            )
            body = RUNNER.goal_runner_adapter.goal_notifications.github_notification_body(
                notice
            )
            github_rows = []
            calls = []

            def fake(command, **kwargs):
                calls.append(command)
                if command[:2] == ["gh", "api"]:
                    if "-f" in command:
                        github_rows.append({
                            "id": 901,
                            "html_url": "https://github.com/owner/repo/issues/42#issuecomment-901",
                            "body": body,
                        })
                    return subprocess.CompletedProcess(
                        command, 0, json.dumps(github_rows), ""
                    )
                return subprocess.CompletedProcess(command, 0, "{}\n", "")

            result = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path,
                ledger_path=ledger_path, comments_path=comments_path,
                backlog_path=None, trial=False, router=repo / "router.py",
                epoch_record=repo / "epoch.json", admission=repo / "admission.py",
                runner_identity={"sha256": "test"},
                current=datetime(2026, 10, 22, 10, 1, tzinfo=ZoneInfo("Asia/Taipei")),
                command_runner=fake,
            )
            self.assertEqual("ADMISSION_UNAVAILABLE", result["status"])
            self.assertEqual(3, len([row for row in calls if row[:2] == ["gh", "api"]]))
            self.assertEqual(
                "SENT",
                RUNNER.goal_runner_adapter.goal_notifications.notification_state(
                    goal.read_ledger(ledger_path), notice["notification_id"]
                ),
            )
            sent = [
                row for row in goal.read_ledger(ledger_path)
                if row["event_type"] == "NOTIFICATION_SENT"
            ]
            self.assertEqual(901, sent[0]["payload"]["comment_id"])
            self.assertEqual("NONE", sent[0]["payload"]["authority_effect"])

    def test_pre_reservation_admission_failure_never_reserves_routes_or_mutates_formal_files(self):
        from tests.control_plane.test_github_product_goal_control import comment
        import goal_continuity as goal

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".ai").mkdir()
            spec = product_goal_spec()
            self.install_carryover_evidence(repo, spec)
            state = goal.initial_runner_state(
                spec, now="2026-11-02T10:00:00+08:00",
                dependency_receipts=activation_dependency_receipts(spec),
            )
            state["candidate_identity"] = {
                "commit": "1" * 40,
                "fingerprint": "2" * 64,
                "branch": "codex/o2-reading-experience",
                "pull_request": 33,
            }
            order_path = repo / "output" / "pre-admission-fail.json"
            order_path.parent.mkdir(parents=True)
            order = {
                "schema_version": "kgnote.linux-worker-order.v1",
                "event_id": "pre-admission-fail",
                "stage": "codex",
                "working_directory": (
                    "/home/kgnote/.local/share/kgnote/work-items/"
                    "pre-admission-fail"
                ),
                "command": ["/usr/bin/true"],
                "checkpoint_path": str(repo / "formal-checkpoint.json"),
            }
            order_path.write_text(json.dumps(order))
            state["work_items"][0]["dispatch_binding"] = {
                "order_path": "output/pre-admission-fail.json",
                "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
                "order_event_id": order["event_id"],
            }
            spec_path, state_path = repo / "spec.json", repo / "state.json"
            ledger_path, comments_path = repo / "ledger.jsonl", repo / "comments.json"
            spec_path.write_text(json.dumps(spec))
            goal.atomic_write_json(state_path, state)
            authority_comment = comment(spec, login="joannalee20050914")
            authority_comment["html_url"] = (
                "https://github.com/joannalee20050914/KGnote-public/"
                "issues/9#issuecomment-100"
            )
            authority_comment["issue_url"] = (
                "https://api.github.com/repos/joannalee20050914/"
                "KGnote-public/issues/9"
            )
            comments_path.write_text(json.dumps([authority_comment]))
            authority = RUNNER.goal_runner_adapter.github_control.resolve_authority(
                [authority_comment], spec,
            )
            RUNNER.goal_runner_adapter.reconcile_owner_authority(
                spec, state, authority, state_path=state_path,
                ledger_path=ledger_path,
                observed_at=datetime(
                    2026, 10, 29, 14, tzinfo=ZoneInfo("Asia/Taipei"),
                ),
            )
            now = datetime(2026, 11, 2, 10, tzinfo=ZoneInfo("Asia/Taipei"))
            unavailable = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path,
                ledger_path=ledger_path, comments_path=comments_path,
                backlog_path=None, trial=False, router=repo / "missing-router.py",
                epoch_record=repo / "missing-epoch.json",
                admission=repo / "missing-admission.py",
                runner_identity={"sha256": "test"}, current=now,
                command_runner=lambda command, **kwargs: subprocess.CompletedProcess(
                    command, 0, "{}\n", "",
                ),
            )
            self.assertEqual("ADMISSION_UNAVAILABLE", unavailable["status"])
            before_state = hashlib.sha256(state_path.read_bytes()).hexdigest()
            before_ledger = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
            router, epoch, admission = (
                repo / "router.py", repo / "epoch.json", repo / "admission.py"
            )
            for path in (router, epoch, admission):
                path.write_text("{}")
            calls = []

            def fail_admission(command, **kwargs):
                calls.append(command)
                if "--discover-runtime" in command:
                    return subprocess.CompletedProcess(
                        command, 0, json.dumps(runtime_identity()), "",
                    )
                if "--admit-order" in command:
                    return subprocess.CompletedProcess(
                        command, 2, "", "Landlock admission failed",
                    )
                if (
                    len(command) > 1 and command[1] == str(router)
                    and "--order" in command
                ) or command[0] == "ssh":
                    self.fail("formal route/model path was reached after admission failure")
                return subprocess.CompletedProcess(command, 0, "{}\n", "")

            rejected = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path,
                ledger_path=ledger_path, comments_path=comments_path,
                backlog_path=None, trial=False, router=router,
                epoch_record=epoch, admission=admission,
                runner_identity={"sha256": "test"}, current=now,
                command_runner=fail_admission,
            )
            self.assertEqual("PRE_RESERVATION_ADMISSION_REJECTED", rejected["status"])
            self.assertEqual(before_state, hashlib.sha256(state_path.read_bytes()).hexdigest())
            self.assertEqual(before_ledger, hashlib.sha256(ledger_path.read_bytes()).hexdigest())
            projection = goal.reduce_ledger(goal.read_ledger(ledger_path))
            self.assertEqual({}, projection["dispatch_reservations"])
            self.assertEqual({}, projection["model_attempts"])
            self.assertEqual(0, goal.load_json(state_path)["work_items"][0]["attempts"])
            self.assertFalse(Path(order["checkpoint_path"]).exists())
            self.assertEqual(3, len(calls))

    def test_product_goal_live_path_reserves_routes_and_never_blind_redispatches(self):
        from tests.control_plane.test_goal_continuity import product_goal_spec
        from tests.control_plane.test_github_product_goal_control import comment
        import goal_continuity as goal

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".ai").mkdir()
            spec = product_goal_spec()
            state = goal.initial_runner_state(spec, now="2026-10-22T10:00:00+08:00")
            order_path = repo / "output" / "sealed.json"
            order_path.parent.mkdir(parents=True)
            order = {
                "schema_version": "kgnote.linux-worker-order.v1",
                "event_id": "product-goal-order-1",
                "stage": "codex",
                "working_directory": "/home/kgnote/.local/share/kgnote/work-items/product-goal-test",
                "command": ["/usr/bin/true"],
                "checkpoint_path": str(repo / "checkpoint.json"),
            }
            order_path.write_text(json.dumps(order))
            state["work_items"][0]["dispatch_binding"] = {
                "order_path": "output/sealed.json",
                "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
                "order_event_id": order["event_id"],
            }
            spec_path, state_path = repo / "spec.json", repo / "state.json"
            ledger_path, comments_path = repo / "ledger.jsonl", repo / "comments.json"
            spec_path.write_text(json.dumps(spec)); goal.atomic_write_json(state_path, state)
            comments_path.write_text(json.dumps([comment(spec)]))
            router, epoch, admission = repo / "router.py", repo / "epoch.json", repo / "admission.py"
            for path in (router, epoch, admission): path.write_text("{}")
            calls = []
            def fake(command, **kwargs):
                calls.append(command)
                if "--discover-runtime" in command:
                    return subprocess.CompletedProcess(
                        command,0,json.dumps(runtime_identity()),"",
                    )
                if "--admit-order" in command:
                    order=Path(command[command.index("--admit-order")+1])
                    durable=goal.load_json(state_path)
                    action={
                        "work_item_id":durable["work_items"][0]["work_item_id"],
                        "action":"DISPATCH_IMPLEMENTATION","provider":"codex",
                    }
                    prepared,receipt=prepare_model_reservation(
                        repo,durable,action,observed_at=now,
                    )
                    self.assertEqual(order,prepared)
                    expected=Path(command[command.index("--admission-receipt")+1])
                    expected.parent.mkdir(parents=True,exist_ok=True)
                    expected.write_bytes(receipt.read_bytes())
                    return subprocess.CompletedProcess(command,0,expected.read_text(),"")
                return subprocess.CompletedProcess(command, 0, "{}\n", "")
            now = datetime(2026, 10, 22, 10, tzinfo=ZoneInfo("Asia/Taipei"))
            first = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path, ledger_path=ledger_path,
                comments_path=comments_path, trial=False, router=router,
                backlog_path=None,
                epoch_record=epoch, admission=admission, runner_identity={"sha256": "test"},
                current=now, command_runner=fake,
            )
            self.assertEqual("DISPATCHED", first["status"])
            self.assertEqual(5, len(calls))
            before = len(calls)
            second = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path, ledger_path=ledger_path,
                comments_path=comments_path, trial=False, router=router,
                backlog_path=None,
                epoch_record=epoch, admission=admission, runner_identity={"sha256": "test"},
                current=now, command_runner=fake,
            )
            self.assertEqual("CHECKPOINT_PENDING", second["status"])
            self.assertEqual(before, len(calls))

    def test_product_goal_runner_releases_reconciled_failure_then_retries_through_admission(self):
        from tests.control_plane.test_goal_continuity import product_goal_spec
        from tests.control_plane.test_github_product_goal_control import comment
        import goal_continuity as goal
        import linux_worker_router as router_control

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            (repo / ".ai").mkdir()
            spec = product_goal_spec()
            state = goal.initial_runner_state(spec, now="2026-10-22T10:00:00+08:00")
            order_path = repo / "output" / "recoverable.json"
            order_path.parent.mkdir(parents=True)
            checkpoint_path = repo / "checkpoint.json"
            order = {
                "schema_version": "kgnote.linux-worker-order.v1",
                "event_id": "product-goal-recoverable-1",
                "stage": "codex",
                "working_directory": "/home/kgnote/.local/share/kgnote/work-items/product-goal-recovery",
                "command": ["/usr/bin/true"],
                "checkpoint_path": str(checkpoint_path),
            }
            order_path.write_text(json.dumps(order))
            state["work_items"][0]["dispatch_binding"] = {
                "order_path": "output/recoverable.json",
                "order_sha256": hashlib.sha256(order_path.read_bytes()).hexdigest(),
                "order_event_id": order["event_id"],
            }
            spec_path, state_path = repo / "spec.json", repo / "state.json"
            ledger_path, comments_path = repo / "ledger.jsonl", repo / "comments.json"
            spec_path.write_text(json.dumps(spec)); goal.atomic_write_json(state_path, state)
            comments_path.write_text(json.dumps([comment(spec)]))
            router, epoch, admission = repo / "router.py", repo / "epoch.json", repo / "admission.py"
            for path in (router, epoch, admission): path.write_text("{}")
            calls = []
            def fake(command, **kwargs):
                calls.append(command)
                if "--discover-runtime" in command:
                    return subprocess.CompletedProcess(
                        command,0,json.dumps(runtime_identity()),"",
                    )
                if "--admit-order" in command:
                    order=Path(command[command.index("--admit-order")+1])
                    admission_index=sum(
                        "--admit-order" in row for row in calls
                    )-1
                    observed=now+RUNNER.timedelta(minutes=6*admission_index)
                    durable=goal.load_json(state_path)
                    action={
                        "work_item_id":durable["work_items"][0]["work_item_id"],
                        "action":"DISPATCH_IMPLEMENTATION","provider":"codex",
                    }
                    prepared,receipt=prepare_model_reservation(
                        repo,durable,action,observed_at=observed,
                    )
                    self.assertEqual(order,prepared)
                    expected=Path(command[command.index("--admission-receipt")+1])
                    expected.parent.mkdir(parents=True,exist_ok=True)
                    expected.write_bytes(receipt.read_bytes())
                    return subprocess.CompletedProcess(command,0,expected.read_text(),"")
                return subprocess.CompletedProcess(command, 0, "{}\n", "")
            now = datetime(2026, 10, 22, 10, tzinfo=ZoneInfo("Asia/Taipei"))
            first = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path, ledger_path=ledger_path,
                comments_path=comments_path, trial=False, router=router,
                backlog_path=None, epoch_record=epoch, admission=admission,
                runner_identity={"sha256": "test"}, current=now, command_runner=fake,
            )
            self.assertEqual("DISPATCHED", first["status"])
            routed_order=json.loads(order_path.read_text())
            checkpoint_path.write_text(json.dumps({
                "schema_version": "kgnote.linux-worker-route.v1",
                "status": "FAILED_CLOSED", "reason": "guest_worker_failed",
                "event_id": routed_order["event_id"],
                "command_digest": router_control.command_digest(
                    router_control.WorkerOrder.from_dict(routed_order)
                ),
                "execution_evidence": {"failure_class": "DETERMINISTIC_WORKER_FAILURE"},
            }))
            reconciled = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path, ledger_path=ledger_path,
                comments_path=comments_path, trial=False, router=router,
                backlog_path=None, epoch_record=epoch, admission=admission,
                runner_identity={"sha256": "test"}, current=now, command_runner=fake,
            )
            self.assertEqual("CHECKPOINT_RECONCILED", reconciled["status"])
            before_retry = len(calls)
            retried = RUNNER.run_product_goal_mode(
                repo, spec_path=spec_path, state_path=state_path, ledger_path=ledger_path,
                comments_path=comments_path, trial=False, router=router,
                backlog_path=None, epoch_record=epoch, admission=admission,
                runner_identity={"sha256": "test"},
                current=datetime(2026, 10, 22, 10, 6, tzinfo=ZoneInfo("Asia/Taipei")),
                command_runner=fake,
            )
            self.assertEqual("DISPATCHED", retried["status"], retried)
            self.assertGreater(len(calls), before_retry)
            operations = [
                row["payload"].get("operation") for row in goal.read_ledger(ledger_path)
            ]
            self.assertEqual(1, operations.count("RECOVERABLE_RUNTIME_BLOCK_RELEASED"))

    def test_admission_pending_item_is_prepared_then_dispatched_once(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); item["status"]="ADMISSION_PENDING"; item["admission"]={"sealed":True}
            pending=self.scheduler_pending([item]); pending_path=repo/"pending.json"; pending_path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True); order.write_text("{}")
            router=repo/"router.py"; router.write_text(""); epoch=repo/"epoch.json"; epoch.write_text("{}"); admission=repo/"admission.py"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"{}\n","")
            receipt={"status":"READY","order_path":item["order_path"],"pull_request":27,"head":"a"*40,"fingerprint":"b"*64,"worktree":"/tmp/w","pull_request_url":"https://example/pr/27","issue_title":"Issue"}
            with patch.object(RUNNER.cross_issue_admission,"prepare",return_value=receipt) as prepare:
                result=RUNNER.route_next_ready_work(repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake)
            self.assertEqual(0,result); prepare.assert_called_once()
            saved=json.loads(pending_path.read_text()); self.assertEqual("DISPATCHED",saved["runner_status"])
            self.assertEqual(1,saved["ready_queue"][0]["budget"]["used"])
        finally: tmp.cleanup()
    def ready_item(self, work_item_id="D2-T07", dependencies=None):
        return {
            "work_item_id":work_item_id, "status":"READY",
            "authority":{"status":"APPROVED","source":"owner-approved issue"},
            "dependencies":dependencies or [], "order_path":f"output/{work_item_id}.json",
            "budget":{"authorized":2,"used":0},
            "safety":{"isolated_worktree":True,"automatic_merge":False},
        }

    def scheduler_pending(self, items=None):
        return {
            "work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},
            "ready_queue":items or [], "work_item_states":{}, "global_constraints":[],
            "stop_marker_policy":{"scope":"WORK_ITEM","affected_work":["legacy-pr-23"],"release_condition":"legacy owner gate"},
        }

    def test_a_waiting_pr_allows_independent_authorized_ready_work(self):
        pending=self.scheduler_pending([self.ready_item()]); pending["status"]="WAITING_HUMAN_ACCEPTANCE"
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("DISPATCH_READY",decision["status"])
        self.assertEqual("D2-T07",decision["selected"]["work_item_id"])

    def test_a_selected_independent_work_routes_existing_sealed_order(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); pending=self.scheduler_pending([item]); pending["status"]="WAITING_HUMAN_ACCEPTANCE"
            pending_path=repo/"pending.json"; pending_path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True); order.write_text("{}")
            router=repo/"router.py"; router.write_text("")
            epoch=repo/"epoch.json"; epoch.write_text("{}")
            admission=repo/"admission.py"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"{}\n","")
            result=RUNNER.route_next_ready_work(
                repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),
                stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake,
            )
            self.assertEqual(0,result)
            saved=json.loads(pending_path.read_text())
            self.assertEqual("DISPATCHED",saved["runner_status"])
            self.assertEqual("DISPATCHED",saved["ready_queue"][0]["status"])
            self.assertEqual(1,saved["ready_queue"][0]["budget"]["used"])
            self.assertEqual(3,len(calls))
        finally: tmp.cleanup()

    def test_route_failure_consumes_the_single_reserved_dispatch(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); item["budget"]={"authorized":1,"used":0}
            pending=self.scheduler_pending([item]); pending_path=repo/"pending.json"; pending_path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True); order.write_text("{}")
            router=repo/"router.py"; router.write_text(""); epoch=repo/"epoch.json"; epoch.write_text("{}")
            admission=repo/"admission.py"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs):
                calls.append(command)
                code=7 if command and command[0]==sys.executable and str(router) in command else 0
                return subprocess.CompletedProcess(command,code,"{}\n","")
            result=RUNNER.route_next_ready_work(repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake)
            self.assertEqual(7,result)
            saved=json.loads(pending_path.read_text())
            self.assertEqual(1,saved["ready_queue"][0]["budget"]["used"])
            self.assertEqual("WORK_ITEM_BLOCKED",saved["ready_queue"][0]["status"])
            self.assertEqual("WORK_ITEM_BLOCKED",saved["runner_status"])
            before=len(calls)
            restarted=json.loads(pending_path.read_text())
            self.assertEqual(0,RUNNER.route_next_ready_work(repo,pending_path,restarted,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake))
            self.assertEqual(before,len(calls))
            self.assertEqual(1,json.loads(pending_path.read_text())["ready_queue"][0]["budget"]["used"])
        finally: tmp.cleanup()

    def test_quota_route_failure_blocks_without_spending_or_redispatching(self):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        try:
            item=self.ready_item(); item["budget"]={"authorized":1,"used":0}
            pending=self.scheduler_pending([item]); path=repo/"pending.json"; path.write_text(json.dumps(pending))
            order=repo/item["order_path"]; order.parent.mkdir(parents=True)
            checkpoint=repo/"route.json"; order.write_text(json.dumps({"checkpoint_path":str(checkpoint)}))
            checkpoint.write_text(json.dumps({"status":"FAILED_CLOSED","reason":"quota_exhausted","exit_code":1}))
            router=repo/"router.py"; router.write_text(""); epoch=repo/"epoch"; epoch.write_text(""); admission=repo/"admission"; admission.write_text("")
            calls=[]
            def fake(command,**kwargs):
                calls.append(command)
                code=2 if command and command[0]==sys.executable and str(router) in command else 0
                return subprocess.CompletedProcess(command,code,"","usage limit reached")
            self.assertEqual(2,RUNNER.route_next_ready_work(repo,path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake))
            saved=json.loads(path.read_text()); self.assertEqual(0,saved["ready_queue"][0]["budget"]["used"])
            self.assertEqual("QUOTA_EXHAUSTED",saved["runtime_block"]["failure_class"])
            before=len(calls)
            self.assertEqual(0,RUNNER.route_next_ready_work(repo,path,saved,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,router=router,epoch_record=epoch,admission=admission,command_runner=fake))
            self.assertEqual(before,len(calls))
        finally: tmp.cleanup()

    def checkpoint_fixture(self, status="COMPLETED", reason=None):
        tmp=tempfile.TemporaryDirectory(); repo=Path(tmp.name)
        item=self.ready_item(); item.update({
            "status":"DISPATCHED",
            "admission":{"repository":"owner/repo","issue":14},
            "admission_receipt":{"pull_request":27},
        })
        pending=self.scheduler_pending([item]); pending_path=repo/"pending.json"
        pending_path.write_text(json.dumps(pending))
        order_path=repo/item["order_path"]; order_path.parent.mkdir(parents=True)
        checkpoint=repo/"checkpoint.json"
        order={
            "schema_version":RUNNER.ORDER_SCHEMA,"event_id":"issue-14-test","stage":"codex",
            "working_directory":"/home/kgnote/.local/share/kgnote/work-items/issue-14-d2-t07",
            "command":["/usr/bin/true"],"checkpoint_path":str(checkpoint),
        }
        order_path.write_text(json.dumps(order))
        checkpoint.write_text(json.dumps({
            "status":status,"reason":reason,"event_id":order["event_id"],
            "command_digest":RUNNER.worker_command_digest(order),"exit_code":1 if status!="COMPLETED" else 0,
        }))
        return tmp,repo,pending_path,item,order,checkpoint

    def test_checkpoint_running_waits_without_router(self):
        tmp,repo,path,item,order,_=self.checkpoint_fixture("RUNNING")
        try:
            self.assertTrue(RUNNER.consume_dispatched_checkpoints(repo,path,json.loads(path.read_text()),command_runner=lambda *a,**k:self.fail("must not call router or network")))
            saved=json.loads(path.read_text()); self.assertEqual("DISPATCHED",saved["runner_status"])
            self.assertEqual(0,saved["revision"]-1)
        finally: tmp.cleanup()

    def test_checkpoint_completed_is_consumed_once_without_router_or_push_when_pr_matches(self):
        tmp,repo,path,item,order,_=self.checkpoint_fixture()
        head="a"*40; calls=[]
        def fake(command,**kwargs):
            calls.append(command)
            if command[0]=="ssh": return subprocess.CompletedProcess(command,0,head+"\n","")
            return subprocess.CompletedProcess(command,0,json.dumps({"headRefOid":head}),"")
        try:
            pending=json.loads(path.read_text())
            self.assertTrue(RUNNER.consume_dispatched_checkpoints(repo,path,pending,command_runner=fake))
            saved=json.loads(path.read_text()); self.assertEqual("WORKER_COMPLETED",saved["ready_queue"][0]["status"])
            self.assertEqual(["issue-14-test"],saved["consumed_ready_work_events"])
            before=len(calls)
            self.assertFalse(RUNNER.consume_dispatched_checkpoints(repo,path,saved,command_runner=fake))
            self.assertEqual(before,len(calls))
        finally: tmp.cleanup()

    def test_checkpoint_publisher_rejection_blocks_and_preserves_evidence(self):
        tmp,repo,path,item,order,_=self.checkpoint_fixture()
        head="a"*40
        def fake(command,**kwargs):
            if command[0]=="ssh": return subprocess.CompletedProcess(command,0,head+"\n M src/value.py\n","")
            return subprocess.CompletedProcess(command,0,json.dumps({"headRefOid":"b"*40}),"")
        def reject(*args): raise RuntimeError("forbidden path: PLAN.md")
        try:
            self.assertTrue(RUNNER.consume_dispatched_checkpoints(repo,path,json.loads(path.read_text()),command_runner=fake,publisher=reject))
            saved=json.loads(path.read_text()); self.assertEqual("WORK_ITEM_BLOCKED",saved["ready_queue"][0]["status"])
            self.assertIn("PLAN.md",saved["runtime_block"]["reason"])
        finally: tmp.cleanup()

    def test_historical_manual_publication_is_read_only_consumed_without_claiming_d3(self):
        tmp,repo,path,item,order,checkpoint=self.checkpoint_fixture()
        worktree=repo/"published"; worktree.mkdir()
        evidence=worktree/"verification.json"
        evidence.write_text(json.dumps({"result":"pass","evidence_readback":True}))
        candidate="c"*40; product="d"*40; remote="e"*40; guest="a"*40
        pending=json.loads(path.read_text()); queued=pending["ready_queue"][0]
        queued.update({
            "status":"WORK_ITEM_BLOCKED",
            "blocked_reason":"trusted Publisher rejected candidate: trusted Publisher request is missing for dirty worker result",
            "dispatch_receipt":{
                "route_status":"COMPLETED","event_id":order["event_id"],
                "route_checkpoint":str(checkpoint),"candidate_head":candidate,
                "trusted_product_commit":product,"verification_evidence":"verification.json",
            },
        })
        queued["admission_receipt"].update({"worktree":str(worktree)})
        pending["runtime_block"]={"work_item_id":queued["work_item_id"],"retry_blocked":True}
        path.write_text(json.dumps(pending))
        calls=[]
        def fake(command,**kwargs):
            calls.append(command)
            if command[0]=="ssh": return subprocess.CompletedProcess(command,0,guest+"\n M src/value.py\n","")
            if command[0]=="/opt/homebrew/bin/gh": return subprocess.CompletedProcess(command,0,json.dumps({"headRefOid":remote}),"")
            if "rev-parse" in command: return subprocess.CompletedProcess(command,0,remote+"\n","")
            if "status" in command: return subprocess.CompletedProcess(command,0,"","")
            if "merge-base" in command: return subprocess.CompletedProcess(command,0,"","")
            self.fail(f"unexpected command: {command}")
        try:
            self.assertTrue(RUNNER.consume_dispatched_checkpoints(repo,path,json.loads(path.read_text()),command_runner=fake,publisher=lambda *a:self.fail("must not publish")))
            saved=json.loads(path.read_text()); consumed=saved["ready_queue"][0]["checkpoint_consumption"]
            self.assertEqual("WORKER_COMPLETED",saved["ready_queue"][0]["status"])
            self.assertEqual("HISTORICAL_MANUAL_PUBLICATION_OBSERVED",consumed["publication_status"])
            self.assertIs(False,consumed["d3_verified"])
            self.assertNotIn("runtime_block",saved)
            self.assertEqual([order["event_id"]],saved["consumed_ready_work_events"])
        finally: tmp.cleanup()

    def test_checkpoint_publisher_and_push_success_are_consumed_once(self):
        tmp,repo,path,item,order,_=self.checkpoint_fixture()
        guest="a"*40; committed="c"*40; remote_heads=iter(["b"*40,committed]); pushed=[]
        def fake(command,**kwargs):
            if command[0]=="ssh": return subprocess.CompletedProcess(command,0,guest+"\n M src/value.py\n","")
            return subprocess.CompletedProcess(command,0,json.dumps({"headRefOid":next(remote_heads)}),"")
        def publish(*args): return {"status":"COMMITTED_LOCAL_ONLY","commit":committed}
        def push(*args): pushed.append(committed)
        try:
            self.assertTrue(RUNNER.consume_dispatched_checkpoints(repo,path,json.loads(path.read_text()),command_runner=fake,publisher=publish,pusher=push))
            saved=json.loads(path.read_text()); self.assertEqual("WORKER_COMPLETED",saved["ready_queue"][0]["status"])
            self.assertEqual([committed],pushed)
            self.assertEqual(committed,saved["ready_queue"][0]["checkpoint_consumption"]["published_head"])
        finally: tmp.cleanup()

    def test_checkpoint_failure_quota_and_identity_mismatch_block_without_router(self):
        for status,reason,mismatch,failure_class in (
            ("FAILED_CLOSED","guest_worker_failed",False,"DETERMINISTIC_WORKER_FAILURE"),
            ("BLOCKED","deterministic_worker_failure",False,"DETERMINISTIC_WORKER_FAILURE"),
            ("FAILED_CLOSED","quota_exhausted",False,"QUOTA_EXHAUSTED"),
            ("COMPLETED",None,True,"DETERMINISTIC_WORKER_FAILURE"),
        ):
            tmp,repo,path,item,order,checkpoint=self.checkpoint_fixture(status,reason)
            try:
                if mismatch:
                    value=json.loads(checkpoint.read_text()); value["command_digest"]="0"*64; checkpoint.write_text(json.dumps(value))
                self.assertTrue(RUNNER.consume_dispatched_checkpoints(repo,path,json.loads(path.read_text()),command_runner=lambda *a,**k:self.fail("must not route")))
                saved=json.loads(path.read_text()); self.assertEqual("WORK_ITEM_BLOCKED",saved["ready_queue"][0]["status"])
                self.assertEqual(failure_class,saved["runtime_block"]["failure_class"])
            finally: tmp.cleanup()

    def test_pending_compare_and_swap_rejects_stale_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"pending.json"; path.write_text(json.dumps({"revision":2,"value":"new"}))
            with self.assertRaises(RUNNER.PendingWriteConflict):
                RUNNER.write_pending(path,{"revision":1,"value":"stale"})
            self.assertEqual("new",json.loads(path.read_text())["value"])

    def test_dirty_runner_code_idles_before_dispatch(self):
        tmp,repo,router=self.fixture(); calls=[]
        try:
            result=RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:calls.append(a) or subprocess.CompletedProcess(a,0,"",""),router,runner_identity={"runner_code_head":"a"*40,"runner_code_dirty":True})
            self.assertEqual(0,result); self.assertEqual([],calls)
            events=[json.loads(line)["event"] for line in (repo/"output/control-plane/production-runner/runner.jsonl").read_text().splitlines()]
            self.assertEqual(["runner_tick_started","runner_code_dirty_idle"],events)
        finally: tmp.cleanup()

    def queue_projection_fixture(self):
        tmp=tempfile.TemporaryDirectory(); out=Path(tmp.name)/"runner"
        item=self.ready_item(); item["admission"]={"repository":"owner/repo","issue":14}
        pending=self.scheduler_pending([item])
        return tmp,out,item,pending

    def test_label_projection_adds_verified_target_before_removing_stale_label(self):
        tmp,out,item,pending=self.queue_projection_fixture(); calls=[]; labels={"queue:ready"}
        def fake(command,**kwargs):
            calls.append(command)
            if command[1:3]==["label","list"]: return subprocess.CompletedProcess(command,0,json.dumps([{"name":"queue:work-item-blocked"}]),"")
            if "view" in command: return subprocess.CompletedProcess(command,0,json.dumps({"labels":[{"name":name} for name in sorted(labels)]}),"")
            if "--add-label" in command: labels.add(command[command.index("--add-label")+1])
            if "--remove-label" in command: labels.discard(command[command.index("--remove-label")+1])
            return subprocess.CompletedProcess(command,0,"","")
        try:
            with patch.object(RUNNER,"OUT",out), patch.object(RUNNER,"LOG",out/"runner.jsonl"):
                self.assertTrue(RUNNER.apply_queue_label(pending,"WORK_ITEM_BLOCKED",item=item,command_runner=fake))
            mutations=[command for command in calls if "edit" in command]
            self.assertIn("--add-label",mutations[0]); self.assertIn("--remove-label",mutations[1])
            self.assertEqual({"queue:work-item-blocked"},labels)
        finally: tmp.cleanup()

    def test_missing_target_label_and_add_failure_preserve_original_label(self):
        for failure in ("missing_target","add_target"):
            tmp,out,item,pending=self.queue_projection_fixture(); calls=[]; labels={"queue:ready"}
            def fake(command,**kwargs):
                calls.append(command)
                if command[1:3]==["label","list"]:
                    labels_found=[] if failure=="missing_target" else [{"name":"queue:work-item-blocked"}]
                    return subprocess.CompletedProcess(command,0,json.dumps(labels_found),"")
                if "view" in command: return subprocess.CompletedProcess(command,0,json.dumps({"labels":[{"name":name} for name in labels]}),"")
                if "--add-label" in command:
                    return subprocess.CompletedProcess(command,1,"","rejected")
                self.fail(f"original label must not be removed: {command}")
            try:
                with patch.object(RUNNER,"OUT",out), patch.object(RUNNER,"LOG",out/"runner.jsonl"):
                    self.assertFalse(RUNNER.apply_queue_label(pending,"WORK_ITEM_BLOCKED",item=item,command_runner=fake,current=datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei"))))
                self.assertEqual({"queue:ready"},labels)
                self.assertFalse(any("--remove-label" in command for command in calls))
            finally: tmp.cleanup()

    def test_exact_label_has_zero_mutation_and_failure_backoff_survives_ticks(self):
        tmp,out,item,pending=self.queue_projection_fixture(); calls=[]; labels={"queue:work-item-blocked"}
        def exact(command,**kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command,0,json.dumps({"labels":[{"name":name} for name in labels]}),"")
        now=datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei"))
        try:
            with patch.object(RUNNER,"OUT",out), patch.object(RUNNER,"LOG",out/"runner.jsonl"):
                self.assertTrue(RUNNER.apply_queue_label(pending,"WORK_ITEM_BLOCKED",item=item,command_runner=exact,current=now))
                self.assertEqual(1,len(calls)); self.assertFalse(any("edit" in command for command in calls))
                labels.clear(); labels.add("queue:ready"); calls.clear()
                def failing(command,**kwargs):
                    calls.append(command)
                    if command[1:3]==["label","list"]: return subprocess.CompletedProcess(command,0,'[{"name":"queue:work-item-blocked"}]',"")
                    if "view" in command: return subprocess.CompletedProcess(command,0,'{"labels":[{"name":"queue:ready"}]}',"")
                    return subprocess.CompletedProcess(command,1,"","rejected")
                self.assertFalse(RUNNER.apply_queue_label(pending,"WORK_ITEM_BLOCKED",item=item,command_runner=failing,current=now))
                after_failure=len(calls)
                self.assertFalse(RUNNER.apply_queue_label(pending,"WORK_ITEM_BLOCKED",item=item,command_runner=failing,current=now.replace(second=30)))
                self.assertEqual(after_failure,len(calls))
                self.assertTrue((out/RUNNER.QUEUE_LABEL_RETRY).is_file())
        finally: tmp.cleanup()

    def test_work_window_never_projects_global_over_durable_work_item_block(self):
        pending=self.scheduler_pending([]); pending["status"]="WORK_ITEM_BLOCKED"
        inside=RUNNER.select_ready_work(pending,datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        outside=RUNNER.select_ready_work(pending,datetime(2026,10,20,20,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        weekend=RUNNER.select_ready_work(pending,datetime(2026,10,24,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("WORK_ITEM_BLOCKED",RUNNER.scheduler_projection_status(pending,inside))
        self.assertEqual("WORK_ITEM_BLOCKED",RUNNER.scheduler_projection_status(pending,outside))
        self.assertEqual("WORK_ITEM_BLOCKED",RUNNER.scheduler_projection_status(pending,weekend))
        self.assertEqual("WORK_ITEM_BLOCKED",pending["status"])

    def test_cross_window_ticks_keep_work_item_label_without_mutation(self):
        tmp,repo,router=self.fixture(); path=repo/"pending.json"; calls=[]
        pending=self.scheduler_pending([])
        pending.update({"status":"WORK_ITEM_BLOCKED","scope":{"repository":"owner/repo","pull_request":26}})
        path.write_text(json.dumps(pending))
        def fake(command,**kwargs):
            calls.append(command)
            if "view" in command:
                return subprocess.CompletedProcess(command,0,'{"labels":[{"name":"queue:work-item-blocked"}]}',"")
            self.fail(f"exact projection must not mutate GitHub: {command}")
        try:
            for moment in (
                datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),
                datetime(2026,10,20,20,tzinfo=ZoneInfo("Asia/Taipei")),
                datetime(2026,10,24,10,tzinfo=ZoneInfo("Asia/Taipei")),
                datetime(2026,10,26,10,tzinfo=ZoneInfo("Asia/Taipei")),
            ):
                current=json.loads(path.read_text())
                self.assertEqual(0,RUNNER.route_next_ready_work(
                    repo,path,current,moment,stop_marker_present=True,router=router,
                    epoch_record=repo/"epoch",admission=repo/"admission",command_runner=fake,
                ))
            self.assertTrue(calls)
            self.assertFalse(any("edit" in command for command in calls))
            self.assertEqual("WORK_ITEM_BLOCKED",json.loads(path.read_text())["status"])
        finally: tmp.cleanup()

    def test_ready_work_item_and_real_global_classifications_remain_distinct(self):
        ready=self.scheduler_pending([self.ready_item()])
        self.assertEqual("DISPATCH_READY",RUNNER.select_ready_work(ready,datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)["status"])
        blocked=self.scheduler_pending([{**self.ready_item(),"status":"WORK_ITEM_BLOCKED"}])
        blocked_decision=RUNNER.select_ready_work(blocked,datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("WORK_ITEM_BLOCKED",RUNNER.scheduler_projection_status(blocked,blocked_decision))
        global_blocked=self.scheduler_pending([self.ready_item()]); global_blocked["global_constraints"]=[{"active":True,"reason":"safety isolation unavailable"}]
        global_decision=RUNNER.select_ready_work(global_blocked,datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("GLOBAL_BLOCKED",RUNNER.scheduler_projection_status(global_blocked,global_decision))

    def test_completed_item_does_not_project_default_ready_label(self):
        tmp,repo,router=self.fixture(); pending_path=repo/"pending.json"
        try:
            pending=self.scheduler_pending([{**self.ready_item(),"status":"WORKER_COMPLETED"}])
            pending_path.write_text(json.dumps(pending)); calls=[]
            result=RUNNER.route_next_ready_work(
                repo,pending_path,pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),
                stop_marker_present=True,router=router,epoch_record=repo/"epoch.json",admission=repo/"admission.py",
                command_runner=lambda command,**kwargs:calls.append(command) or subprocess.CompletedProcess(command,0,"","")
            )
            self.assertEqual(0,result)
            self.assertFalse(any(command and command[0]=="/opt/homebrew/bin/gh" for command in calls))
        finally: tmp.cleanup()

    def test_route_order_records_router_stderr_tail(self):
        with tempfile.TemporaryDirectory() as directory:
            repo=Path(directory); router=repo/"router.py"; router.write_text(""); order=repo/"order.json"; order.write_text("{}")
            calls=[]
            def fake(command,**kwargs):
                return subprocess.CompletedProcess(command,0,"","") if command[0]=="ssh" else subprocess.CompletedProcess(command,2,"","missing schema_version")
            with patch.object(RUNNER,"append",side_effect=lambda event,**fields:calls.append((event,fields))):
                self.assertEqual(2,RUNNER.route_order(repo,router,order,fake))
            self.assertEqual("missing schema_version",calls[-1][1]["error_tail"])

    def test_six_of_six_claude_changes_required_cannot_dispatch_codex_repair(self):
        pending={
            "schema_version":"kgnote.pending-successor-goal.v1","status":"ACTIVE",
            "activation_not_before":"2026-10-19T09:00:00+08:00",
            "authority":{"status":"APPROVED_FOR_FUTURE_WINDOW"},"product_work_started":False,
            "legacy_inheritance":{"pull_request":23,"review_round":8,"cycle":20},
            "continuous_budget":{
                "new_prs":{"authorized":3,"used":0},
                "claude_product_reviews":{"authorized":6,"used":6},
                "codex_implementation_or_repair_cycles":{"authorized":12,"used":6},
            },
            "review_result":{"verdict":"CHANGES_REQUIRED"},
        }
        errors=RUNNER.successor_errors(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")))
        self.assertIn("claude_product_reviews budget is exhausted or invalid",errors)

    def test_b_dependency_on_waiting_pr_is_not_dispatchable(self):
        pending=self.scheduler_pending([self.ready_item("D2-T02",["PR-26"])]); pending["work_item_states"]={"PR-26":"WAITING_HUMAN_ACCEPTANCE"}
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("NO_ELIGIBLE_READY_WORK",decision["status"])
        self.assertEqual("DEPENDENCY_BLOCKED",decision["blocks"][0]["kind"])
        self.assertEqual("DEPENDENCY_SUBGRAPH",decision["blocks"][0]["scope"])

    def test_c_no_eligible_work_is_normal_idle_with_reason(self):
        decision=RUNNER.select_ready_work(self.scheduler_pending(),datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual({"status":"NO_ELIGIBLE_READY_WORK","selected":None,"blocks":[]},decision)

    def test_d_global_window_or_safety_constraint_stops_every_dispatch(self):
        pending=self.scheduler_pending([self.ready_item()])
        outside=RUNNER.select_ready_work(pending,datetime(2026,10,19,20,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("GLOBAL_BLOCKED",outside["status"])
        pending["global_constraints"]=[{"active":True,"reason":"safety isolation unavailable","release_condition":"restore isolation"}]
        safety=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("GLOBAL_BLOCKED",safety["status"])

    def test_e_same_candidate_cannot_flip_changes_required_to_pass_without_new_evidence(self):
        identity={"candidate_commit":"a"*40,"candidate_fingerprint":"b"*64}
        previous={**identity,"verdict":"CHANGES_REQUIRED","findings":[{"id":"finding-r-004","severity":"blocking"}]}
        current={**identity,"verdict":"PASS","findings":[]}
        self.assertIn("without structured new resolution evidence",RUNNER.review_progression_error(previous,current))
        current["resolution_evidence"]=[{"finding_ids":["finding-r-004"],"evidence_identity":"targeted-test:sha256:abc"}]
        self.assertIsNone(RUNNER.review_progression_error(previous,current))

    def test_component_pass_does_not_trigger_preserved_human_gates(self):
        pending=self.scheduler_pending()
        pending.update({
            "status":"ACTIVE",
            "scope":{"issue":8,"objective":"Source Library component"},
            "preserved_human_gates":["PA-HUMAN-1","NS-HUMAN-SMOKE"],
        })
        self.assertEqual("COMPONENT_REVIEW_COMPLETE",RUNNER.status_after_component_pass(pending))
        self.assertIn("not explicitly scheduled","; ".join(RUNNER.human_checkpoint_eligibility_errors(pending)))

    def final_checkpoint(self):
        return {
            "gate_id":"D2-T14-FINAL-HUMAN-ACCEPTANCE",
            "status":"READY",
            "candidate_scope":"COMPLETE_PRODUCT_DELIVERY",
            "candidate_commit":"a"*40,
            "candidate_fingerprint":"b"*64,
            "approved_required_scope_complete":True,
            "required_features_complete":True,
            "dependencies_complete":True,
            "cross_module_integration_complete":True,
            "required_scenarios_complete":True,
            "delivery_evidence_complete":True,
            "no_known_delivery_blockers":True,
            "rc_evidence_complete":True,
            "independent_review_complete":True,
            "integrated_verification_complete":True,
            "trial_entrypoint":"kgnote://final-candidate",
            "formal_human_acceptance_status":"NOT_EVALUATED",
            "authority_refs":[
                "docs/requirements/PERSONAL_ALPHA_INTEGRATED_STAGE_DIRECTION_20260927.md",
                "https://github.com/joannalee20050914/KGnote-public/issues/21",
            ],
        }

    def test_only_explicit_complete_product_candidate_enters_final_acceptance(self):
        pending=self.scheduler_pending()
        pending.update({"candidate_commit":"a"*40,"candidate_fingerprint":"b"*64})
        pending["human_checkpoint"]=self.final_checkpoint()
        self.assertEqual([],RUNNER.human_checkpoint_eligibility_errors(pending))
        self.assertEqual("FINAL_HUMAN_ACCEPTANCE_REQUIRED",RUNNER.status_after_component_pass(pending))
        pending["human_checkpoint"].update({
            "evidence":["RC-01..RC-34 exact candidate receipt","independent review PASS"],
            "acceptance_scope":["installation","daily use","backup and restore"],
        })
        notice=RUNNER.final_human_acceptance_notification(pending["human_checkpoint"])
        self.assertTrue(notice["blocking"])
        self.assertIn("不會自動通過",notice["continuation_notice"])
        for field in ("dependencies_complete","required_features_complete","cross_module_integration_complete"):
            with self.subTest(field=field):
                candidate=json.loads(json.dumps(pending)); candidate["human_checkpoint"][field]=False
                self.assertEqual("COMPONENT_REVIEW_COMPLETE",RUNNER.status_after_component_pass(candidate))

    def test_soft_feedback_is_nonblocking_deduplicated_and_late_reply_bound(self):
        pending=self.scheduler_pending([self.ready_item()])
        event={
            "goal_id":"goal-1","candidate_version":"sha256:abc","experience_scope":"source-import",
            "entrypoint":"http://127.0.0.1:8080/source/1","actually_operable":True,
            "operable_evidence":["HTTP 200 and imported source read-back"],
            "suggested_steps":["Import the fixture","Open Source detail"],
            "experience_questions":["Can you find the imported source without learning internal IDs?"],
        }
        stored,created=RUNNER.register_soft_feedback_event(pending,event)
        self.assertTrue(created); self.assertFalse(stored["blocking"])
        duplicate,created_again=RUNNER.register_soft_feedback_event(pending,event)
        self.assertFalse(created_again); self.assertEqual(stored["notification_key"],duplicate["notification_key"])
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("DISPATCH_READY",decision["status"])
        notice=RUNNER.soft_feedback_notification(stored)
        self.assertTrue(notice["optional"]); self.assertFalse(notice["blocks_development"])
        followup=RUNNER.record_late_soft_feedback(
            pending,stored["notification_key"],feedback="The source is hard to locate",impact_scope=["source-library navigation"],
        )
        self.assertEqual("sha256:abc",followup["candidate_version"])
        self.assertEqual("source-library navigation",followup["impact_scope"][0])

    def test_work_is_not_triggered_by_routine_review_retry_progress_or_dispatch(self):
        for event_type in (
            "CLAUDE_PASS", "CLAUDE_CHANGES_REQUIRED", "PRODUCT_WORK_STARTED",
            "RETRY_SCHEDULED", "PROGRESS_UPDATED", "NEXT_WORK_DISPATCHED",
            "GITHUB_STATE_SYNCHRONIZED",
        ):
            with self.subTest(event_type=event_type):
                self.assertFalse(RUNNER.work_notification_eligible(event_type))
        self.assertTrue(RUNNER.work_notification_eligible("SOFT_FEEDBACK_AVAILABLE"))
        self.assertTrue(RUNNER.work_notification_eligible("FINAL_HUMAN_ACCEPTANCE_REQUIRED"))

    def test_soft_feedback_requires_operable_result_and_specific_question(self):
        pending=self.scheduler_pending()
        event={"goal_id":"g","candidate_version":"c","experience_scope":"s","entrypoint":"/tmp/demo",
               "actually_operable":False,"operable_evidence":[],"suggested_steps":[],"experience_questions":[]}
        stored,created=RUNNER.register_soft_feedback_event(pending,event)
        self.assertIsNone(stored); self.assertFalse(created)
        self.assertNotIn("soft_feedback_events",pending)

    def test_soft_feedback_silence_survives_restart_without_becoming_pass(self):
        pending=self.scheduler_pending()
        event={
            "goal_id":"goal-1","candidate_version":"sha256:abc","experience_scope":"source-import",
            "entrypoint":"/tmp/demo","actually_operable":True,"operable_evidence":["read-back"],
            "suggested_steps":["Open demo"],"experience_questions":["Is navigation clear?"],
        }
        stored,_=RUNNER.register_soft_feedback_event(pending,event)
        restarted=json.loads(json.dumps(pending))
        self.assertEqual("OPTIONAL_PENDING",restarted["soft_feedback_events"][0]["feedback_status"])
        self.assertEqual(stored["notification_key"],restarted["soft_feedback_events"][0]["notification_key"])

    def test_component_pass_without_ready_successor_is_normal_idle(self):
        pending=self.scheduler_pending(); pending["status"]=RUNNER.status_after_component_pass(pending)
        decision=RUNNER.select_ready_work(
            pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True,
        )
        self.assertEqual("COMPONENT_REVIEW_COMPLETE",pending["status"])
        self.assertEqual("NO_ELIGIBLE_READY_WORK",decision["status"])

    def test_restart_blocks_component_pass_without_canonical_github_record(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo,status="COMPONENT_REVIEW_COMPLETE")
        (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n")
        value=json.loads(pending.read_text())
        value["review_result"]={"verdict":"PASS","round":5,"canonical_record":None}
        pending.write_text(json.dumps(value))
        try:
            with patch.object(RUNNER,"apply_queue_label",return_value={"status":"APPLIED"}):
                result=RUNNER.run_once(
                    repo,datetime(2026,10,20,11,tzinfo=ZoneInfo("Asia/Taipei")),
                    lambda *a,**k:self.fail("missing canonical evidence must not dispatch"),
                    router,pending_goal=pending,
                )
            saved=json.loads(pending.read_text())
            self.assertEqual(0,result)
            self.assertEqual("WORK_ITEM_BLOCKED",saved["status"])
            self.assertIn("not a GitHub record ID",saved["work_item_block"]["reason"])
        finally: tmp.cleanup()

    def test_restart_of_locally_blocked_item_rechecks_independent_queue_and_idles(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo,status="WORK_ITEM_BLOCKED")
        (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n")
        value=json.loads(pending.read_text())
        value.update({
            "work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},
            "review_result":{"verdict":"PASS","round":4,"consistency_audited":True},
            "ready_queue":[],"work_item_states":{},"global_constraints":[],
            "stop_marker_policy":{"scope":"WORK_ITEM","affected_work":["PR-26"]},
        })
        pending.write_text(json.dumps(value))
        try:
            result=RUNNER.run_once(
                repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),
                lambda *a,**k:self.fail("idle selection must not invoke an external command"),
                router,pending_goal=pending,
            )
            self.assertEqual(0,result)
            saved=json.loads(pending.read_text())
            self.assertEqual("WORK_ITEM_BLOCKED",saved["status"])
            self.assertEqual("NO_ELIGIBLE_READY_WORK",saved["runner_status"])
            self.assertEqual("NO_ELIGIBLE_READY_WORK",saved["scheduler"]["status"])
        finally: tmp.cleanup()

    def test_f_restart_does_not_redispatch_completed_work_or_reset_budget(self):
        item=self.ready_item(); item["status"]="DISPATCHED"; item["budget"]={"authorized":2,"used":1}
        pending=self.scheduler_pending([item])
        first=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        second=RUNNER.select_ready_work(json.loads(json.dumps(pending)),datetime(2026,10,20,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=False)
        self.assertEqual("NO_ELIGIBLE_READY_WORK",first["status"])
        self.assertEqual("NO_ELIGIBLE_READY_WORK",second["status"])
        self.assertEqual(1,pending["ready_queue"][0]["budget"]["used"])

    def test_g_work_item_human_gate_preserves_legacy_marker_and_merge_protection(self):
        independent=self.ready_item(); pending=self.scheduler_pending([independent]); pending["status"]="WAITING_HUMAN_ACCEPTANCE"
        decision=RUNNER.select_ready_work(pending,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),stop_marker_present=True)
        self.assertEqual("DISPATCH_READY",decision["status"])
        self.assertFalse(independent["safety"]["automatic_merge"])
        self.assertEqual(["legacy-pr-23"],pending["stop_marker_policy"]["affected_work"])

    def test_h_github_projection_distinguishes_all_scheduler_states(self):
        expected={
            "WORK_ITEM_BLOCKED":"queue:work-item-blocked", "DEPENDENCY_BLOCKED":"queue:dependency-blocked",
            "GLOBAL_BLOCKED":"queue:global-blocked", "WAITING_HUMAN_ACCEPTANCE":"queue:waiting-human",
            "NO_ELIGIBLE_READY_WORK":"queue:idle",
            "FINAL_HUMAN_ACCEPTANCE_REQUIRED":"queue:waiting-final-human",
            "PRODUCT_DECISION_REQUIRED":"queue:product-decision",
        }
        self.assertEqual(expected,{state:RUNNER.github_queue_label(state) for state in expected})

    def test_formal_model_contexts_are_explicit_and_deterministic_role_has_no_model(self):
        codex=RUNNER.configured_execution_context("CODEX_IMPLEMENTER",pull_request=26,cycle=7)
        claude=RUNNER.configured_execution_context("CLAUDE_PRODUCT_REVIEWER",pull_request=26,review_round=5)
        deterministic=RUNNER.configured_execution_context("DETERMINISTIC_VERIFICATION",pull_request=26)
        self.assertEqual(("gpt-5.6-terra","medium"),(codex["requested_model"],codex["requested_effort"]))
        self.assertEqual(("sonnet","medium"),(claude["requested_model"],claude["requested_effort"]))
        self.assertEqual("NOT_APPLICABLE",deterministic["model_usage_status"])
        self.assertIsNone(deterministic["requested_model"])

    def test_publisher_accepts_only_verified_repair_child_of_last_published_head(self):
        old="a"*40; candidate="b"*40; legacy="c"*40
        verified={"status":"PASS","candidate_commit":candidate,"candidate_fingerprint":"d"*64}
        self.assertIsNone(RUNNER.publish_admission_error(old,candidate,legacy,old,verified))
        self.assertEqual("remote_head_mismatch",RUNNER.publish_admission_error("e"*40,candidate,legacy,old,verified))
        self.assertEqual("candidate_not_verified",RUNNER.publish_admission_error(old,candidate,legacy,old,{**verified,"status":"FAIL"}))
        self.assertEqual("candidate_not_verified",RUNNER.publish_admission_error(old,candidate,legacy,old,{**verified,"candidate_commit":"f"*40}))

    def test_full_verification_identity_requires_exact_head_stable_fingerprint_and_readback(self):
        candidate="a"*40
        evidence={"result":"pass","evidence_readback":True,"repository":{"head":candidate},"fingerprint_stable":True,"fingerprint_after":{"value":"b"*64}}
        self.assertEqual("b"*64,RUNNER.verified_candidate_fingerprint(evidence,candidate))
        for changed in ({"result":"fail"},{"evidence_readback":False},{"repository":{"head":"c"*40}},{"fingerprint_stable":False},{"fingerprint_after":{"value":"short"}}):
            self.assertIsNone(RUNNER.verified_candidate_fingerprint({**evidence,**changed},candidate))

    def test_verification_command_creates_receipt_parent_and_uses_pinned_toolchain(self):
        command=RUNNER.verification_command("output/control-plane/runner-verification-197c094f.json")
        self.assertEqual("/bin/sh",command[0])
        self.assertIn("/usr/bin/mkdir -p output/control-plane",command[2])
        self.assertIn(f"KGNOTE_TEST_PYTHON={RUNNER.REMOTE_VERIFICATION_PYTHON}",command[2])
        self.assertNotIn(".venv/bin/python scripts/codex_control.py",command[2].replace(str(RUNNER.REMOTE_VERIFICATION_PYTHON),"PINNED"))

    def test_verification_status_sync_changes_only_excluded_identity_receipt(self):
        value={
            "updated_at":"old",
            "git":{"branch":"old","head":"a"*40,"checkpoint_commit":"a"*40},
            "working_state":{"fingerprint":"b"*64},
            "verification":{"candidate_verified":True,"control_plane_ready":True},
        }
        text=(
            "# status\n\n"+RUNNER.STATUS_BEGIN+"\n```json\n"+
            json.dumps(value,indent=2)+"\n```\n"+RUNNER.STATUS_END+"\n\nHandoff remains intact.\n"
        )
        rendered=RUNNER.render_verification_status(
            text,candidate="c"*40,fingerprint="d"*64,updated_at="now",
        )
        payload=json.loads(rendered.split("```json\n",1)[1].split("\n```",1)[0])
        self.assertEqual("c"*40,payload["git"]["head"])
        self.assertEqual("c"*40,payload["git"]["checkpoint_commit"])
        self.assertEqual("d"*64,payload["working_state"]["fingerprint"])
        self.assertFalse(payload["verification"]["candidate_verified"])
        self.assertIn("Handoff remains intact.",rendered)

    def test_verification_failure_routing_separates_infra_product_and_hard_stops(self):
        self.assertEqual(
            "INFRA_RETRY",
            RUNNER.verification_failure_disposition(
                {},route_exit=2,stderr="cannot create output/control-plane/x: Directory nonexistent",
            )[0],
        )
        base={"evidence_readback":True,"fingerprint_stable":True,"preflight":{"errors":[]}}
        product={**base,"gates":[{"name":"python_product_tests","passed":False}]}
        self.assertEqual("PRODUCT_REPAIR",RUNNER.verification_failure_disposition(product,route_exit=2,stderr="")[0])
        safety={**base,"gates":[{"name":"public_safety_scan","passed":False}]}
        self.assertEqual("HARD_STOP",RUNNER.verification_failure_disposition(safety,route_exit=2,stderr="")[0])
        tooling={**base,"preflight":{"errors":["tooling: node is unavailable"]},"gates":[]}
        self.assertEqual("INFRA_RETRY",RUNNER.verification_failure_disposition(tooling,route_exit=2,stderr="")[0])
        drift={**base,"fingerprint_stable":False,"gates":[]}
        self.assertEqual("HARD_STOP",RUNNER.verification_failure_disposition(drift,route_exit=2,stderr="")[0])
        self.assertEqual(
            "HARD_STOP",
            RUNNER.verification_failure_disposition({},route_exit=2,stderr="Permission denied")[0],
        )

    def fixture(self, state="IMPLEMENTING", approved=True):
        tmp = tempfile.TemporaryDirectory(); repo = Path(tmp.name)
        (repo / ".ai").mkdir(); (repo / "scripts").mkdir(); (repo / "scripts/codex_orchestrator.py").write_text("")
        (repo / ".ai/ORCHESTRATOR_STATE.json").write_text(json.dumps({"active_goal":"goal","work_package":"package","state":state}))
        envelope={"schema_version":"kgnote.work-package-envelope.v1","status":"APPROVED" if approved else "PENDING_OWNER_APPROVAL","goal_id":"goal","work_package_id":"package","authority_record":"approval","approval":{"source_status":"RECONCILING","receipt":".ai/reconciliation-receipt.json"},"work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:30"},"budgets":{name:{"authorized":2,"used":0} for name in ("local_repairs","internal_reviews","external_reviews")}}
        (repo / ".ai/work-package-envelope.json").write_text(json.dumps(envelope))
        router = repo / "linux_worker_router.py"; router.write_text("")
        return tmp, repo, router

    def pending(self, repo, status="PENDING_ELIGIBLE"):
        path=repo/"pending.json"
        value={"schema_version":"kgnote.pending-successor-goal.v1","goal_id":"GOAL-KGNOTE-SOURCE-LIBRARY-SUCCESSOR-20261019","status":status,"activation_not_before":"2026-10-19T09:00:00+08:00","work_window":{"timezone":"Asia/Taipei","start":"09:00","end":"18:00"},"authority":{"status":"APPROVED_FOR_FUTURE_WINDOW","source":"owner"},"scope":{"repository":"joannalee20050914/KGnote-public"},"legacy_inheritance":{"pull_request":23,"review_round":8,"cycle":20,"head":"4b6e6eebcddcbd4ef21259a3ece6d92b276473ea","candidate_fingerprint":"38eae708123a99a7abd04327ce079b05248e18646402285a6f83fb49f69a2330"},"continuous_budget":{"new_prs":{"authorized":3,"used":0},"claude_product_reviews":{"authorized":6,"used":0},"codex_implementation_or_repair_cycles":{"authorized":12,"used":0}},"cutover_epoch":"epoch","product_work_started":False,"new_product_pr_created":False}
        path.write_text(json.dumps(value)); return path

    def test_approved_package_routes_one_linux_worker_order_without_host_fallback(self):
        tmp, repo, router=self.fixture(); calls=[]
        order_path=repo/".ai/linux-worker-order.json"; order_path.write_text("{}")
        epoch=repo/"epoch.json"; epoch.write_text("{}")
        admission=repo/"epoch_scope_admission.py"; admission.write_text("")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,epoch_record=epoch,admission=admission))
            self.assertIn("--epoch",calls[0]); self.assertIn("--order",calls[0])
            self.assertEqual(["--order",str(order_path)],calls[2][-2:])
            self.assertNotIn("codex_orchestrator.py", " ".join(sum(calls, [])))
        finally: tmp.cleanup()

    def test_stop_marker_is_preserved_and_only_routes_idempotent_idle_health(self):
        tmp, repo, router=self.fixture(); calls=[]
        marker=repo/".ai/ORCHESTRATOR_STOP"; marker.write_text("stop\n")
        def fake(command, **kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,20,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=repo/"absent-pending.json"))
            self.assertTrue(marker.exists())
            self.assertEqual("production-idle-health-v2",json.loads((repo/"output/control-plane/production-runner/linux-idle-health-order.json").read_text())["event_id"])
            self.assertNotIn("codex_orchestrator.py", " ".join(sum(calls, [])))
        finally: tmp.cleanup()

    def test_guest_unavailable_fails_closed_before_router(self):
        tmp, repo, router=self.fixture(); calls=[]
        marker=repo/".ai/ORCHESTRATOR_STOP"; marker.write_text("stop\n")
        def fake(command, **kwargs):
            calls.append(command); return subprocess.CompletedProcess(command,255,"","offline")
        try:
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=repo/"absent-pending.json"))
            self.assertEqual("ssh",calls[0][0]); self.assertEqual(1,len(calls)); self.assertTrue(marker.exists())
        finally: tmp.cleanup()

    def test_stop_marker_allows_only_private_smoke_canary_order(self):
        tmp, repo, router=self.fixture(); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n")
        with tempfile.TemporaryDirectory() as integration_directory:
            integration=Path(integration_directory).resolve()
            canary=integration/"output/claude-reviewer-final/test-order.json"
            canary.parent.mkdir(parents=True)
            canary.write_text(json.dumps({"event_id":"production-canary-test","working_directory":"/home/kgnote/.local/share/kgnote/smoke-repo","checkpoint_path":str(canary.with_name("test-checkpoint.json"))}))
            calls=[]
            def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,"","")
            try:
                with patch.object(RUNNER,"INTEGRATION_REPO",integration):
                    self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,17,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,canary,pending_goal=repo/"absent-pending.json"))
                self.assertEqual(str(canary),calls[1][-1]); self.assertTrue((repo/".ai/ORCHESTRATOR_STOP").exists())
            finally: tmp.cleanup()

    def test_stop_marker_rejects_canary_outside_controlled_integration_root(self):
        cases=(
            {"event_id":"not-allowlisted","working_directory":"/home/kgnote/.local/share/kgnote/smoke-repo","checkpoint":"inside"},
            {"event_id":"production-canary-test","working_directory":"/home/kgnote/.local/share/kgnote/not-smoke","checkpoint":"inside"},
            {"event_id":"production-canary-test","working_directory":"/home/kgnote/.local/share/kgnote/smoke-repo","checkpoint":"outside"},
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root=Path(directory); integration=root/"controlled-integration"
                allowed=integration/"output/claude-reviewer-final"; allowed.mkdir(parents=True)
                order=root/"canary.json"
                checkpoint=(allowed/"checkpoint.json" if case["checkpoint"]=="inside" else root/"outside.json")
                order.write_text(json.dumps({"event_id":case["event_id"],"working_directory":case["working_directory"],"checkpoint_path":str(checkpoint)}))
                with patch.object(RUNNER,"INTEGRATION_REPO",integration):
                    with self.assertRaises(ValueError): RUNNER.validate_canary_order(order)

    def test_missing_linux_order_fails_closed_without_host_execution(self):
        tmp, repo, router=self.fixture()
        try:
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_terminal_unapproved_outside_hours_and_overspend_do_not_run(self):
        cases=[("AUTOMATION_BLOCKED",True,10,0),("IMPLEMENTING",False,10,2),("IMPLEMENTING",True,8,0),("IMPLEMENTING",True,18,0),("IMPLEMENTING",True,20,0)]
        for state, approved, hour, expected in cases:
            tmp, repo, router=self.fixture(state,approved)
            try:
                result=RUNNER.run_once(repo,datetime(2026,10,19,hour,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router)
                self.assertEqual(expected,result)
            finally: tmp.cleanup()
        tmp, repo, router=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope["budgets"]["internal_reviews"]={"authorized":1,"used":2}; (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_manually_flipped_approved_status_without_transition_receipt_does_not_run(self):
        tmp, repo, router=self.fixture()
        try:
            envelope=json.loads((repo/".ai/work-package-envelope.json").read_text()); envelope.pop("approval"); (repo/".ai/work-package-envelope.json").write_text(json.dumps(envelope))
            self.assertEqual(2,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
        finally: tmp.cleanup()

    def test_weekend_never_dispatches_product_work(self):
        for day in (17, 18):
            tmp, repo, router=self.fixture()
            try:
                self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,day,10,tzinfo=ZoneInfo("Asia/Taipei")),lambda *a,**k:self.fail("must not run"),router))
            finally: tmp.cleanup()

    def test_0859_keeps_successor_pending_and_does_not_create_pr(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n"); calls=[]
        def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,8,59,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=pending))
            self.assertEqual("PENDING_ELIGIBLE",json.loads(pending.read_text())["status"])
            self.assertFalse(any("pr" in command for command in calls))
        finally: tmp.cleanup()

    def test_0900_creates_one_successor_pr_and_dispatches_same_checkpoint(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n"); calls=[]
        head="4b6e6eebcddcbd4ef21259a3ece6d92b276473ea"
        def fake(command,**kwargs):
            calls.append(command); joined=" ".join(command)
            if "git/ref/heads" in joined and "--method" not in command:
                count=sum(1 for item in calls if "git/ref/heads" in " ".join(item) and "--method" not in item)
                return subprocess.CompletedProcess(command,1 if count==1 else 0,"" if count==1 else json.dumps({"object":{"sha":head}}),"")
            if "git/refs" in joined: return subprocess.CompletedProcess(command,0,"{}","")
            if "pr list" in joined: return subprocess.CompletedProcess(command,0,"[]","")
            if "pr create" in joined: return subprocess.CompletedProcess(command,0,"https://github.com/joannalee20050914/KGnote-public/pull/26\n","")
            if "pr view" in joined: return subprocess.CompletedProcess(command,0,json.dumps({"number":26,"state":"OPEN","isDraft":True,"headRefName":"codex/source-library-successor-20261019","baseRefName":"codex/issue-19-real-review","url":"https://github.com/joannalee20050914/KGnote-public/pull/26"}),"")
            return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,9,0,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=pending))
            value=json.loads(pending.read_text()); self.assertEqual("ACTIVE",value["status"]); self.assertEqual(26,value["successor_pull_request"])
            order=json.loads((repo/"output/control-plane/production-runner/successor-linux-worker-order.json").read_text()); self.assertEqual("2026-10-19T18:00:00+08:00",order["deadline_at"])
            self.assertTrue(order["bootstrap_working_directory"])
            self.assertEqual("gpt-5.6-terra",order["execution_context"]["requested_model"])
            self.assertEqual("medium",order["execution_context"]["requested_effort"])
            self.assertEqual("--goal-id",order["command"][1])
            self.assertEqual("26",order["command"][4])
            self.assertEqual("CODEX_DISPATCHED",json.loads((repo/"output/control-plane/production-runner/successor-handoff.json").read_text())["status"])
        finally: tmp.cleanup()

    def test_blocked_successor_keeps_launchagent_idle_without_redispatch(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo,status="BLOCKED"); (repo/".ai/ORCHESTRATOR_STOP").write_text("stop\n"); calls=[]
        value=json.loads(pending.read_text()); value["runtime_block"]={"retry_blocked":True,"failure_class":"DETERMINISTIC_WORKER_FAILURE"}; pending.write_text(json.dumps(value))
        def fake(command,**kwargs): calls.append(command); return subprocess.CompletedProcess(command,0,'{"status":"COMPLETED"}\n',"")
        try:
            self.assertEqual(0,RUNNER.run_once(repo,datetime(2026,10,19,10,tzinfo=ZoneInfo("Asia/Taipei")),fake,router,pending_goal=pending))
            self.assertEqual(2,len(calls)); self.assertIn("linux-idle-health-order.json",calls[1][-1])
            self.assertEqual("BLOCKED",json.loads(pending.read_text())["status"])
        finally: tmp.cleanup()

    def test_repeated_pending_read_reuses_existing_pr(self):
        tmp,repo,router=self.fixture(); pending=self.pending(repo); calls=[]; head="4b6e6eebcddcbd4ef21259a3ece6d92b276473ea"
        def fake(command,**kwargs):
            calls.append(command); joined=" ".join(command)
            if "git/ref/heads" in joined: return subprocess.CompletedProcess(command,0,json.dumps({"object":{"sha":head}}),"")
            if "pr list" in joined: return subprocess.CompletedProcess(command,0,json.dumps([{"number":26,"state":"OPEN","isDraft":True,"headRefName":"codex/source-library-successor-20261019","baseRefName":"codex/issue-19-real-review","url":"url"}]),"")
            return subprocess.CompletedProcess(command,0,"","")
        try:
            order,errors=RUNNER.prepare_successor_handoff(repo,pending,datetime(2026,10,19,9,tzinfo=ZoneInfo("Asia/Taipei")),fake)
            self.assertFalse(errors); self.assertIsNotNone(order); self.assertFalse(any("pr create" in " ".join(command) for command in calls))
        finally: tmp.cleanup()

if __name__ == "__main__": unittest.main()
