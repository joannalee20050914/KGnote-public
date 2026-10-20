# KGnote Claude Reviewer permanent billing policy

Status: active execution authority. Approved by the product owner on 2026-10-18.
This policy applies to every future KGnote Claude Reviewer task on macOS, Linux,
CI, disposable repositories, and production cutover work.

## Required authentication and billing boundary

- Claude Code may use only Claude Pro OAuth subscription entitlement.
- Non-interactive commands such as `claude -p` are allowed only after the local
  CLI reports `loggedIn=true`, `authMethod=claude.ai`, `apiProvider=firstParty`,
  and `subscriptionType=pro`.
- Anthropic Console API keys, Amazon Bedrock, Google Vertex AI, Microsoft
  Foundry/Azure, and every other metered backend are forbidden.
- Before every Claude model launch, inspect only whether relevant credential or
  backend-selection environment variables are present. Never print, serialize,
  hash, checkpoint, or log their values.
- `total_cost_usd` is usage-reference metadata only. It must never be presented
  as proof of an actual charge or as authorization for metered billing.
- A quota, usage-limit, or rate-limit exhaustion stops Claude work immediately.
  Preserve the checkpoint and cumulative round count, launch no fallback
  provider, and wait for subscription entitlement to recover.
- Buying Usage Credits, enabling API billing, auto-recharge, changing to a paid
  API backend, or upgrading a plan is forbidden without a new explicit human
  decision. Automation may never perform those actions.
- If subscription-backed Pro OAuth cannot be positively verified, model launch
  fails closed. A remembered login, another host's login, or the absence of an
  API key is not sufficient evidence.
- Ubuntu must complete the official Claude Pro login flow in the guest. The Mac
  login state and credentials must not be copied, mounted, or assumed to carry
  over.

## Safe preflight evidence

`scripts/claude_billing_preflight.py` is the canonical local admission check. Its
output contains only booleans and normalized auth labels; it deliberately omits
email, organization IDs, tokens, keys, credential paths, and raw CLI output.
The Claude Reviewer adapter must pass this check before starting agent-loop or a
Claude subprocess.
