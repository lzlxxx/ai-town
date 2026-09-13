# LLM Gateway Response Compatibility

## Goal
- Fix the CyberTown backend LLM failure shown during batch NPC dialogue generation: `'str' object has no attribute 'choices'`.
- Keep the backend compatible with third-party OpenAI-compatible gateways without editing installed third-party package files.

## Scope
- Add a project-side LLM wrapper for response extraction.
- Route NPC single chat and batch dialogue generation through the wrapper.
- Limit auxiliary affinity-analysis latency so single chat does not wait through long SDK retries.
- Update the startup guide troubleshooting notes for base URL and response-format issues.

## Out of Scope
- No Godot scene changes.
- No change to NPC prompt design, memory schema, or relationship scoring rules.
- No real API key or secret is written into docs.

## Plan
1. Inspect the current `HelloAgentsLLM.invoke()` behavior and NPC call sites.
2. Add a backend wrapper that accepts normal OpenAI SDK objects, dict responses, and raw string responses.
3. Replace the two backend LLM construction sites with the wrapper.
4. Add shorter timeout/no-retry settings for affinity analysis.
5. Run syntax/import checks.
6. Restart or probe the backend and verify core endpoints.
7. Document the fix and troubleshooting path.

## Acceptance Criteria
- Backend Python files compile.
- NPC manager and batch generator import successfully.
- `/health`, `/npcs`, and `/npcs/status` stay reachable after restart.
- A slow affinity-analysis request degrades without blocking chat for several minutes.
- The guide explains that `LLM_BASE_URL` should usually include `/v1`, and identifies the screenshot error as an LLM gateway response/base URL issue.

## Verification Commands
- `.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend`
- `.venv311/bin/python -c "from llm_client import CyberTownLLM; print(CyberTownLLM)"`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/npcs`
- `curl http://127.0.0.1:8000/npcs/status`

## Risks
- A real gateway can still fail with `401`, unsupported model names, or non-OpenAI-compatible endpoints.
- Real LLM verification may consume a small amount of user gateway quota if run against the configured key.

## Verification Results
- Backend Python compilation passed.
- `CyberTownLLM`, `RelationshipManager`, `NPCAgentManager`, and `NPCBatchGenerator` imports passed.
- Local response extraction handled raw string, dict `choices`, and JSON-string `choices` shapes.
- Real gateway smoke test returned `OK` with the current `.env` values.
- Temporary backend on port `8001` started successfully with Qdrant and local embeddings.
- Batch NPC dialogue generation succeeded with the real gateway.
- `GET /health`, `GET /npcs`, and `GET /npcs/status` returned successful responses on port `8001`.
- `POST /chat` returned 200; auxiliary affinity analysis timed out once and degraded safely before the no-retry/short-timeout adjustment was added.
- Temporary port `8001` backend was stopped after verification.

## Decisions
- Use a project-side `CyberTownLLM` wrapper instead of editing installed `hello-agents` package files.
- Keep `LLM_BASE_URL` in `.env` at `https://elysiver.h-e.top/v1`.
- Set `LLM_MAX_RETRIES=0` and `LLM_AFFINITY_TIMEOUT=8` to keep game interactions responsive when auxiliary analysis is slow.
