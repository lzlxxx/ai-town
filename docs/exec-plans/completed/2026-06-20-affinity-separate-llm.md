# Affinity Separate LLM Configuration

## Goal
- Let affinity analysis use its own OpenAI-compatible gateway configuration.
- Support separate `base_url`, `api_key`, and `model_id` for future faster/cheaper affinity-analysis providers.

## Scope
- Add `LLM_AFFINITY_API_KEY`, `LLM_AFFINITY_BASE_URL`, and `LLM_AFFINITY_MODEL_ID`.
- Add optional `LLM_AFFINITY_MAX_RETRIES`.
- Keep existing fallback behavior: if affinity-specific values are omitted, use the main `LLM_*` configuration.
- Update `.env.example`, local `.env`, and startup guide.
- Verify with compile/import checks and a focused configuration test.

## Out of Scope
- No Godot client changes.
- No prompt or scoring-rule changes.
- No real secret values in documentation.

## Plan
1. Extend `CyberTownLLM` so each instance can set its own retry count.
2. Create a dedicated affinity-analysis `CyberTownLLM` in `RelationshipManager`.
3. Normalize affinity base URLs and fall back to main LLM config when not set.
4. Document the new `.env` variables.
5. Run compile/import checks, config fallback checks, and codegraph sync.

## Acceptance Criteria
- Affinity analysis can use a different model/base URL/key from NPC chat.
- Missing affinity-specific config falls back to the main LLM config.
- Existing `LLM_AFFINITY_ENABLED` and `LLM_AFFINITY_TIMEOUT` still work.
- Backend code compiles.

## Verification Commands
- `.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend`
- `.venv311/bin/python -c "... RelationshipManager affinity config check ..."`
- `codegraph sync .`

## Risks
- A separate affinity gateway can still fail due to wrong key, unsupported model name, rate limit, or timeout.
- If affinity analysis uses a weaker model, JSON formatting may be less stable.

## Verification Results
- Backend Python compilation passed.
- Focused config test verified affinity analysis can use an independent model/base URL/key.
- Focused fallback test verified omitted affinity-specific values reuse the main LLM config.
- Focused failure test verified independent affinity model failure can fall back to the main analyzer when `LLM_AFFINITY_FALLBACK_TO_MAIN=true`.
- Local `.env` now sets `LLM_AFFINITY_MODEL_ID=deepseek-v4-flash` while leaving affinity base URL and API key blank, so it reuses the main gateway credentials.
- Real tiny prompt against `deepseek-v4-flash` returned `OK`.

## Notes
- A full affinity-analysis prompt returned gateway `500` on the current channel for both the independent model and fallback main model during testing. The new configuration mechanism works, but this specific provider/model path may still be unreliable for that prompt shape.
- The code degrades safely to unchanged affinity if both analyzers fail.

## Decisions
- Keep separate affinity LLM configuration as optional. Missing values fall back to main `LLM_*`.
- Keep `LLM_AFFINITY_FALLBACK_TO_MAIN=true` by default.
