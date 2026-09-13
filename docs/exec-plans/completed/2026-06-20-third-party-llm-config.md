# Third-Party LLM Gateway Configuration

## Goal
- Make backend configuration easier to use with third-party OpenAI-compatible LLM gateways.

## Scope
- Load `backend/.env` automatically.
- Normalize common environment variable aliases to the names required by `hello-agents`.
- Update documentation/examples without writing real secrets.
- Verify backend still starts with dummy gateway settings.

## Out of Scope
- No real API key testing.
- No change to NPC business logic or Godot scene files.

## Plan
1. Inspect how `hello-agents` reads LLM configuration.
2. Patch backend config to load `.env` and normalize aliases.
3. Update `.env.example` and startup guide to document third-party gateway usage.
4. Run backend startup verification with dummy LLM values, local embedding, and Qdrant.

## Acceptance Criteria
- `LLM_MODEL`, `OPENAI_API_KEY`, and `OPENAI_BASE_URL` aliases can map to `LLM_MODEL_ID`, `LLM_API_KEY`, and `LLM_BASE_URL`.
- Backend starts successfully with `.env`-style dummy settings.
- No real secrets are committed.

## Verification Commands
- `python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/npcs`

## Risks
- Real gateway compatibility still depends on provider-specific model names and API behavior.
