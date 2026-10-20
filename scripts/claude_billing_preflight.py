#!/usr/bin/env python3
"""Fail-closed Claude Pro OAuth admission check without credential disclosure."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Callable


FORBIDDEN_ENVIRONMENT = {
    "ANTHROPIC_API_KEY",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "AWS_BEARER_TOKEN_BEDROCK",
    "ANTHROPIC_VERTEX_PROJECT_ID",
    "ANTHROPIC_VERTEX_REGION",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_API_KEY",
}


class BillingPreflightError(RuntimeError):
    pass


def verify_subscription_oauth(
    claude_cmd: Path,
    *,
    environ: dict[str, str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, object]:
    environment = os.environ if environ is None else environ
    forbidden_present = sorted(name for name in FORBIDDEN_ENVIRONMENT if environment.get(name))
    if forbidden_present:
        raise BillingPreflightError(
            "forbidden metered-provider environment is present: " + ", ".join(forbidden_present)
        )
    result = runner(
        [str(claude_cmd), "auth", "status", "--json"],
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        raise BillingPreflightError("Claude authentication status is unavailable")
    try:
        status = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BillingPreflightError("Claude authentication status is not valid JSON") from exc
    expected = {
        "loggedIn": True,
        "authMethod": "claude.ai",
        "apiProvider": "firstParty",
        "subscriptionType": "pro",
    }
    mismatches = [name for name, value in expected.items() if status.get(name) != value]
    if mismatches:
        raise BillingPreflightError(
            "Claude Pro OAuth subscription could not be verified: " + ", ".join(mismatches)
        )
    return {
        "status": "PASS",
        "logged_in": True,
        "auth_method": "claude.ai",
        "api_provider": "firstParty",
        "subscription_type": "pro",
        "forbidden_metered_environment_present": False,
        "credential_values_logged": False,
        "total_cost_usd_interpretation": "usage_reference_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify_subscription_oauth(args.claude)
    except BillingPreflightError as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": str(exc)}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
