import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from claude_billing_preflight import BillingPreflightError, verify_subscription_oauth


class ClaudeBillingPreflightTest(unittest.TestCase):
    def runner(self, payload, returncode=0):
        return lambda command, **kwargs: subprocess.CompletedProcess(
            command, returncode, json.dumps(payload), "sensitive stderr must not be surfaced"
        )

    def test_accepts_only_verified_pro_subscription_oauth(self):
        result = verify_subscription_oauth(
            Path("/fixture/claude"), environ={}, runner=self.runner({
                "loggedIn": True, "authMethod": "claude.ai",
                "apiProvider": "firstParty", "subscriptionType": "pro",
                "email": "must-not-appear@example.invalid", "orgId": "must-not-appear",
            })
        )
        self.assertEqual("PASS", result["status"])
        self.assertNotIn("email", result)
        self.assertNotIn("orgId", result)

    def test_rejects_api_key_without_exposing_value(self):
        secret = "secret-value-must-not-appear"
        with self.assertRaises(BillingPreflightError) as caught:
            verify_subscription_oauth(Path("claude"), environ={"ANTHROPIC_API_KEY": secret})
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn("ANTHROPIC_API_KEY", str(caught.exception))

    def test_rejects_metered_provider_selectors(self):
        for name in ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX", "CLAUDE_CODE_USE_FOUNDRY"):
            with self.subTest(name=name), self.assertRaises(BillingPreflightError):
                verify_subscription_oauth(Path("claude"), environ={name: "1"})

    def test_rejects_unverified_or_non_pro_auth(self):
        for payload in (
            {"loggedIn": False, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "pro"},
            {"loggedIn": True, "authMethod": "apiKey", "apiProvider": "firstParty", "subscriptionType": "pro"},
            {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "bedrock", "subscriptionType": "pro"},
            {"loggedIn": True, "authMethod": "claude.ai", "apiProvider": "firstParty", "subscriptionType": "api"},
        ):
            with self.subTest(payload=payload), self.assertRaises(BillingPreflightError):
                verify_subscription_oauth(Path("claude"), environ={}, runner=self.runner(payload))

    def test_raw_auth_output_is_not_in_parse_failure(self):
        runner = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "token=secret", "")
        with self.assertRaises(BillingPreflightError) as caught:
            verify_subscription_oauth(Path("claude"), environ={}, runner=runner)
        self.assertNotIn("secret", str(caught.exception))
