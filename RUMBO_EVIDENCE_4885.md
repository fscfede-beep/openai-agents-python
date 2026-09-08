# Issue #4885 — maintainer evidence packet

This file preserves the evidence needed to reconsider the AnyLLM/LiteLLM `finish_reason="length"` follow-up without changing upstream state.

## Upstream context

- Issue #4510 established the defect family: a length-truncated empty Chat Completions turn can collapse to zero output items and become indistinguishable from a genuine empty turn.
- PR #4514 attempted the AnyLLM/LiteLLM sibling fix. When closing it, maintainer `seratch` explicitly asked for a **redacted real-provider response** showing `finish_reason="length"`, no content or tool calls, and the resulting **user-visible failure** before revisiting the extension follow-up.
- Issue #4885 later re-opened that sibling-adapter gap with the desired error semantics (`ModelBehaviorError`) rather than routing token-budget exhaustion through refusal handling.

## Real-provider evidence

Provider/model:
- Ollama 0.32.14 on isolated loopback server
- `rumbo-qwen3-4b-q4km:latest`
- temperature 0

### Truly empty truncation

With `max_tokens=1`, a real OpenAI-compatible `/v1/chat/completions` response produced:

```text
finish_reason="length"
content_len=0
reasoning_len=0
refusal_present=false
tool_calls_present=false
message keys=["role", "content"]
```

Pinned base `1d471a4775bf2f40179f411824da383deb4c3fca`:
- AnyLLM direct -> `ModelResponse(output=[])`
- AnyLLM + `Runner.run` -> successful `final_output=""`, `new_items=[]`
- LiteLLM direct -> `ModelResponse(output=[])`
- LiteLLM + `Runner.run` -> successful `final_output=""`, `new_items=[]`

Reasoning-aware fix:
- AnyLLM direct / Runner -> `ModelBehaviorError`
- LiteLLM direct / Runner -> `ModelBehaviorError`

This demonstrates the user-visible failure requested in the #4514 closure criterion: a real provider-side truncation is silently accepted as a successful empty final answer.

### Reasoning-only compatibility case

With `max_tokens=8`, the same real provider/model produced:

```text
finish_reason="length"
content_len=0
reasoning_len=18
```

Pinned comparison:
- base `1d471a4775bf2f40179f411824da383deb4c3fca` -> one `ResponseReasoningItem`
- incompatible #4886 head `7a437cea5bf7a2e10194ee7239a25d87f59f31ad` -> `ModelBehaviorError`
- reasoning-aware fix -> one `ResponseReasoningItem`

This shows why the guard must exclude provider reasoning from the definition of an empty truncation.

## Canonical implementation

Ready-to-resubmit branch:
- `fix/empty-length-chat-completions-4885-v2`
- head: `dc009c822dfa557342fed5867039bf7931cf1db6`
- base: upstream `main` at `544b8b03b8cf95e62c7f5ebb89adfc4bd66c9d1f`
- exactly one commit ahead, zero behind at the audited point
- changed files only:
  - `src/agents/extensions/models/any_llm_model.py`
  - `src/agents/extensions/models/litellm_model.py`
  - `tests/models/test_any_llm_model.py`
  - `tests/models/test_litellm_content_filter.py`

Behavior:
- raise only when `finish_reason == "length"` and there is no text, refusal, tool call, or provider reasoning;
- preserve partial text, refusals, tool calls, and reasoning-only output.

Verification recorded before the final rebase:
- affected suite: 96 passed
- Ruff: PASS
- Pyright: PASS
- mypy: PASS
- `git diff --check`: PASS

## Current external gate

The upstream repository currently rejects new interactions from this account with:

```text
422: Interactions on this repository have been restricted to prior contributors only.
```

No bypass is attempted. The legitimate next action is to resubmit the preserved one-commit branch only after one of these changes:

1. maintainer response or explicit invitation to resubmit;
2. issue reopen by upstream;
3. repository interaction eligibility changes.

This packet is evidence storage only. It does not claim upstream acceptance, review approval, merge, or production inclusion.
