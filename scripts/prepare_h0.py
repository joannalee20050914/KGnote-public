#!/usr/bin/env python3
"""Prepare one ignored, source-only H0 run directory without starting the test."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kgnote.experiments import load_formative_manifest, validate_formative_run_record  # noqa: E402
from kgnote.reader import load_reader  # noqa: E402
from kgnote.storage import read_canonical_store  # noqa: E402
from kgnote.visualization import load_graph_view  # noqa: E402


CANONICAL_DIRECTORIES = ("concepts", "edges", "evidence", "learning-events", "sources")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _copy_exact(source: Path, destination: Path) -> None:
    content = source.read_bytes()
    if destination.exists():
        if not destination.is_file() or destination.is_symlink() or destination.read_bytes() != content:
            raise RuntimeError(f"existing output differs: {destination.name}")
        return
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination.write_bytes(content)


def _verify_upstream(manifest: dict, upstream_root: Path) -> None:
    upstream = manifest["source"]["upstream"]
    result = subprocess.run(
        ["git", "show", f"{upstream['commit']}:{upstream['path']}"],
        cwd=upstream_root, check=False, capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("upstream revision unavailable")
    if _sha256(result.stdout) != upstream["content_sha256"]:
        raise RuntimeError("upstream content digest mismatch")


def prepare(manifest_path: Path, template_path: Path, output_root: Path, upstream_root: Path) -> dict:
    manifest = load_formative_manifest(manifest_path)
    try:
        output_root.resolve().relative_to((ROOT / "output").resolve())
    except ValueError:
        raise RuntimeError("output must stay under repository output/") from None
    _verify_upstream(manifest, upstream_root)

    record = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    validate_formative_run_record(record, manifest)
    run_root = output_root / record["run_id"]
    source_store = run_root / "source-store"
    notebook_root = run_root / "notebook"
    for directory in CANONICAL_DIRECTORIES:
        (source_store / directory).mkdir(mode=0o700, parents=True, exist_ok=True)
    (source_store / "raw").mkdir(mode=0o700, parents=True, exist_ok=True)
    notebook_root.mkdir(mode=0o700, parents=True, exist_ok=True)

    fixture_raw = ROOT / manifest["source"]["fixture_path"]
    fixture_store = fixture_raw.parents[1]
    source_record = fixture_store / "sources" / f"{manifest['source']['source_id']}.md"
    _copy_exact(fixture_raw, source_store / "raw" / fixture_raw.name)
    _copy_exact(source_record, source_store / "sources" / source_record.name)
    _copy_exact(manifest_path, run_root / "manifest.yaml")
    _copy_exact(template_path, run_root / "run-record.yaml")

    snapshot = read_canonical_store(source_store)
    if snapshot.status != "loaded":
        raise RuntimeError(f"prepared source store rejected: {snapshot.problem.code if snapshot.problem else 'unknown'}")
    graph = load_graph_view(source_store)
    if graph.status != "ready" or graph.response["view"]["nodes"] or graph.response["view"]["links"]:
        raise RuntimeError("prepared H0 store must contain zero graph nodes and links")
    reader = load_reader(source_store, {
        "schema_version": "kgnote.reader-query.v1",
        "snapshot_sha256": graph.response["view"]["snapshot_sha256"],
        "source_id": manifest["source"]["source_id"],
        "locator": {"kind": "line_range", "value": manifest["source"]["selected_range"]},
    })
    if reader.status != "ready":
        raise RuntimeError("prepared source failed Reader read-back")

    port = 4175
    server_command = (
        f".venv/bin/python scripts/serve_graph_view.py --store {source_store} "
        f"--notes-root {notebook_root} --enable-note-writes --port {port}"
    )
    note_query = {
        "note_id": "note_h0_bitepacer_p4_backup",
        "notebook_id": "notebook_h0_bitepacer",
        "learning_unit_id": "unit_p4_backup_verification",
        "title": "BitePacer P4 backup verification",
        "source_id": manifest["source"]["source_id"],
        "locator": "L24-L46",
        "source_label": "P4 backup micro-source · manifest 與 restore",
    }
    from urllib.parse import urlencode
    return {
        "status": "prepared",
        "run_root": str(run_root),
        "manifest_id": manifest["id"],
        "source_sha256": manifest["source"]["content_sha256"],
        "source_line_count": reader.response["document"]["line_count"],
        "graph_node_count": 0,
        "graph_link_count": 0,
        "server_command": server_command,
        "learning_note_url": f"http://127.0.0.1:{port}/learning-note.html?{urlencode(note_query)}",
        "pretest_required": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="experiments/manifests/h0-bitepacer-p4-backup-v1.yaml")
    parser.add_argument("--template", default="experiments/templates/h0-bitepacer-run-record-v1.yaml")
    parser.add_argument("--output", default="output/h0-bitepacer-p4-backup-v1")
    parser.add_argument("--upstream-root", required=True)
    args = parser.parse_args()
    try:
        payload = prepare(
            (ROOT / args.manifest).resolve(), (ROOT / args.template).resolve(),
            (ROOT / args.output).resolve(), Path(args.upstream_root).resolve(),
        )
    except Exception as error:
        payload = {"status": "rejected", "problem": {"code": str(error)}}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        raise SystemExit(1) from None
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
