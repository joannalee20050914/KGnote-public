#!/usr/bin/env python3
"""Guest-side lease guard for one systemd-confined KGnote worker command."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import threading
import time
from pathlib import Path


def run_guarded(command: list[str], lease: Path, lease_timeout: float) -> int:
    if not command or not command[0].startswith(("/bin/", "/usr/bin/", "/home/kgnote/.local/")):
        raise ValueError("worker command must use an approved absolute guest executable")
    if not lease.is_file():
        raise ValueError("worker lease is absent")
    process = subprocess.Popen(command, start_new_session=True)
    stopped = threading.Event()

    def watchdog() -> None:
        while not stopped.wait(0.5):
            try:
                stale = time.time() - lease.stat().st_mtime > lease_timeout
            except OSError:
                stale = True
            if not stale:
                continue
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            if not stopped.wait(2):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            return

    watcher = threading.Thread(target=watchdog, name="kgnote-worker-lease", daemon=True)
    watcher.start()
    try:
        return process.wait()
    finally:
        stopped.set()
        watcher.join(timeout=3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lease", type=Path, required=True)
    parser.add_argument("--lease-timeout", type=float, default=8.0)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not 3 <= args.lease_timeout <= 60:
        parser.error("lease timeout must be between 3 and 60 seconds")
    try:
        return run_guarded(command, args.lease, args.lease_timeout)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
