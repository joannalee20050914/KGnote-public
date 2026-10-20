#!/usr/bin/env python3
"""Execute one command under an irreversible Linux Landlock filesystem allow-list."""

from __future__ import annotations

import argparse
import ctypes
import os
import platform
import sys
from pathlib import Path


SYS_LANDLOCK_CREATE_RULESET = 444
SYS_LANDLOCK_ADD_RULE = 445
SYS_LANDLOCK_RESTRICT_SELF = 446
LANDLOCK_CREATE_RULESET_VERSION = 1
LANDLOCK_RULE_PATH_BENEATH = 1
PR_SET_NO_NEW_PRIVS = 38

ACCESS_EXECUTE = 1 << 0
ACCESS_WRITE_FILE = 1 << 1
ACCESS_READ_FILE = 1 << 2
ACCESS_READ_DIR = 1 << 3
ACCESS_REMOVE_DIR = 1 << 4
ACCESS_REMOVE_FILE = 1 << 5
ACCESS_MAKE_CHAR = 1 << 6
ACCESS_MAKE_DIR = 1 << 7
ACCESS_MAKE_REG = 1 << 8
ACCESS_MAKE_SOCK = 1 << 9
ACCESS_MAKE_FIFO = 1 << 10
ACCESS_MAKE_BLOCK = 1 << 11
ACCESS_MAKE_SYM = 1 << 12
ACCESS_REFER = 1 << 13
ACCESS_TRUNCATE = 1 << 14

READ_ACCESS = ACCESS_EXECUTE | ACCESS_READ_FILE | ACCESS_READ_DIR
WRITE_ACCESS = (
    ACCESS_WRITE_FILE
    | ACCESS_REMOVE_DIR
    | ACCESS_REMOVE_FILE
    | ACCESS_MAKE_CHAR
    | ACCESS_MAKE_DIR
    | ACCESS_MAKE_REG
    | ACCESS_MAKE_SOCK
    | ACCESS_MAKE_FIFO
    | ACCESS_MAKE_BLOCK
    | ACCESS_MAKE_SYM
    | ACCESS_REFER
    | ACCESS_TRUNCATE
)
HANDLED_ACCESS = READ_ACCESS | WRITE_ACCESS


class RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathBeneathAttr(ctypes.Structure):
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


class LandlockError(RuntimeError):
    pass


def _syscall(libc: ctypes.CDLL, number: int, *args: object) -> int:
    result = int(libc.syscall(number, *args))
    if result < 0:
        error = ctypes.get_errno()
        raise LandlockError(f"landlock syscall {number} failed: errno={error}")
    return result


def restrict_filesystem(read_only: list[Path], read_write: list[Path]) -> None:
    if platform.system() != "Linux":
        raise LandlockError("Landlock is available only on Linux")
    libc = ctypes.CDLL(None, use_errno=True)
    abi = _syscall(libc, SYS_LANDLOCK_CREATE_RULESET, 0, 0, LANDLOCK_CREATE_RULESET_VERSION)
    if abi < 3:
        raise LandlockError("Landlock ABI 3 or newer is required for truncate protection")
    ruleset_attr = RulesetAttr(HANDLED_ACCESS)
    ruleset_fd = _syscall(
        libc,
        SYS_LANDLOCK_CREATE_RULESET,
        ctypes.byref(ruleset_attr),
        ctypes.sizeof(ruleset_attr),
        0,
    )
    opened: list[int] = []
    try:
        for path, access in [
            *((item, READ_ACCESS) for item in read_only),
            *((item, HANDLED_ACCESS) for item in read_write),
        ]:
            resolved = path.resolve(strict=True)
            descriptor = os.open(resolved, os.O_PATH | os.O_CLOEXEC)
            opened.append(descriptor)
            rule = PathBeneathAttr(access, descriptor)
            _syscall(
                libc,
                SYS_LANDLOCK_ADD_RULE,
                ruleset_fd,
                LANDLOCK_RULE_PATH_BENEATH,
                ctypes.byref(rule),
                0,
            )
        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise LandlockError(f"PR_SET_NO_NEW_PRIVS failed: errno={ctypes.get_errno()}")
        _syscall(libc, SYS_LANDLOCK_RESTRICT_SELF, ruleset_fd, 0)
    finally:
        for descriptor in opened:
            os.close(descriptor)
        os.close(ruleset_fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ro", action="append", default=[], type=Path)
    parser.add_argument("--rw", action="append", default=[], type=Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not os.path.isabs(command[0]):
        parser.error("command must start with an absolute executable path")
    try:
        restrict_filesystem(args.ro, args.rw)
        os.execvpe(command[0], command, os.environ)
    except (LandlockError, OSError) as exc:
        print(f"filesystem sandbox failed closed: {exc}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
