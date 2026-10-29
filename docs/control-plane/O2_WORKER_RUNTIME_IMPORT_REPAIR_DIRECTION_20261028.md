# O2 Ubuntu Worker runtime import repair direction — 2026-10-28

## Authority and bounded objective

The Product Owner has directed Codex to keep the formal O2 Goal paused, preserve all three existing launch reservations, and repair only the deployed Ubuntu Worker runtime. This direction does not authorize `RESUME`, a fourth reservation, or a new O2 product-model attempt.

The repair must make the exact reviewed Ubuntu deployment self-contained before any model process can start. In particular, deployment must fail closed when a required Worker Python module or the reviewed dependency lock is missing, and formal cold-start acceptance must exercise the deployed runtime rather than a repository checkout.

## Formal production baseline

- Goal: `GOAL-KGNOTE-O2-READING-EXPERIENCE`
- Goal version: `2026-10-23.2-s0-s2-proposal`
- Deployed reviewed revision: `8fc5a7f99cf5d01afa9bb544ba3774ee7cdf11ba`
- Owner action: `PAUSE`
- Owner comment ID: `6461719798`
- Formal lifecycle: `BLOCKED`
- Authority lease: `PAUSED`
- Ledger cursor: `26`
- Work Item A launch reservations: `3`
- Goal cumulative launch reservations: `3 / 8`
- Fourth reservation, attempt, dispatch, checkpoint, or model launch: absent

The third attempt, `o2-wi-o2-a-implement-codex-33383dc5b9d42939`, failed at `2026-10-28T12:48:14+08:00` before Codex started. Its checkpoint records `codex.event_count=0`; its reservation remains part of the append-only accounting.

## Observed deployment gaps

The reviewed release contains `scripts/codex_jsonl_evidence.py`, but the deployed flat runtime originally omitted it. Both Worker entrypoints therefore exited during import. Synchronizing the exact reviewed module (SHA-256 `e6eebee348f4be6b532d234566669b3f889134b7dd7499183f2b5c4a016ca844`) made direct imports and both `--help` cold starts pass.

The subsequent full no-model development-environment admission found a second gap: the product worktree does not contain `requirements-runtime.lock`, while the reviewed release does. The current Worker looks only in the product worktree, so the deployment is not yet acceptable.

## Authorized repair

Codex may:

1. make the Worker resolve the dependency lock from the reviewed deployed runtime without modifying the sealed product checkout;
2. extend the Ubuntu runtime installer and receipt so the fixed required module set and dependency lock are hash-attested against the reviewed release;
3. require deployed import closure and both Worker entrypoint cold starts during deployment;
4. add positive, negative, tamper, and compatibility tests for those conditions;
5. create one bounded branch/PR, obtain exact-candidate independent review, merge normally, deploy the reviewed merge, and run no-model cold-start acceptance;
6. write deployment and verification evidence without changing the formal O2 state or ledger.

## Prohibitions

- Do not publish `RESUME`, `APPROVE`, or any equivalent authority action.
- Do not create, reserve, dispatch, or simulate a fourth O2 product attempt.
- Do not invoke Codex or another product-development model during cold-start acceptance.
- Do not add files to, or otherwise change the identity of, the sealed product checkout.
- Do not deploy code bytes that have not passed exact-candidate independent review.
- Do not rewrite or delete prior ledger, checkpoint, stdout, stderr, or accounting evidence.
- Do not rebuild or replace the broader O2 autonomy flow.

## Completion criteria

1. The installed runtime module manifest and dependency lock are bound to the exact reviewed source revision and SHA-256 values.
2. Removing or modifying any required runtime module or the lock causes deployment validation to fail before a model launch is possible.
3. Using the formal Ubuntu account, `/usr/bin/python3`, and deployed runtime path, direct import closure and both Worker entrypoint `--help` invocations pass.
4. The existing isolated Worker path completes full no-model admission, including exact product checkout validation, locked dependency inventory, and `pip check`, without starting Codex.
5. Formal state and ledger still show comment `6461719798`, `PAUSED`, `BLOCKED`, cursor `26`, exactly three launch reservations, and no fourth dispatch.
6. `release_verified` and all physical-device, Obsidian, learning, and human acceptance gates remain unpromoted.
