# KGnote Ubuntu Agent model policy

Status: active execution policy for the existing Mac Runner → Linux Router → Ubuntu Worker chain. This file does not change product authority, OAuth, budgets, review standards, merge authority, or human gates.

## Active production bindings

| Role | Requested model | Requested effort | Provider/auth | Effective evidence rule |
|---|---|---|---|---|
| Codex Implementer | `gpt-5.6-terra` | `medium` | OpenAI / existing ChatGPT OAuth | The invocation is `CONFIGURED`; until a reliable runtime model field is returned it remains `EFFECTIVE_UNKNOWN`. The configured value must not be presented as actual-model proof. |
| Claude independent product reviewer | `sonnet` | `medium` | Anthropic / existing Claude Pro OAuth | `modelUsage[*].canonicalModel` must identify the Sonnet family. A different family is `MODEL_MISMATCH` and fails closed before product-result consumption. |
| Deterministic verification | none | none | none | `model_usage_status=NOT_APPLICABLE`; Python tests, Git checks, and Runner validation must not invoke a model. |

Codex receives `--model gpt-5.6-terra` and `--config model_reasoning_effort="medium"` on the KGnote Ubuntu command line. These invocation-local values have higher precedence than project and user `config.toml` layers. Claude receives `--model sonnet --effort medium` on the KGnote Ubuntu command line. Neither binding writes `~/.codex/config.toml`, Claude settings, or Mac personal defaults.

## Recorded execution evidence

Every formal work order and resulting checkpoint records the goal, PR, cycle or review round, provider, requested model and effort, CLI version, configuration status, actual model only when reliably reported, and available token usage. Claude evidence is derived from the result envelope's `modelUsage`, `canonicalModel`, and `usage`. Codex terminal token totals are retained when the CLI prints a `tokens used` footer; the actual model remains unknown unless a future supported result field supplies it.

The existing review contract and PASS threshold are unchanged. Sonnet may not omit findings or lower acceptance criteria. If comparative evidence shows inadequate contract coverage, preserve that evidence and change the model only through a later explicit configuration decision.

## Inactive role recommendations

These are compatibility targets, not active automatic routes:

| Work class | Candidate | Effort | Activation state |
|---|---|---|---|
| Routine implementation | GPT-5.6 Terra | Medium | active formal Codex binding |
| Simple repetitive work | GPT-5.6 Luna | Low or Medium | inactive; requires explicit router policy and approval |
| Difficult repair | GPT-5.6 Sol | Medium or High | inactive; requires explicit escalation policy and approval |
| Independent product review | Claude Sonnet | Medium | active formal Claude binding |
| Deterministic tests and verification | no model | none | active |

No automatic model escalation or fallback is enabled by this policy.
