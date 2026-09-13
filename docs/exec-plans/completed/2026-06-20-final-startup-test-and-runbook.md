# Final Startup Test And Runbook

## Goal
- Run one final local startup verification for CyberTown.
- Add a concise Markdown runbook describing how to start and use the project.

## Scope
- Verify Python dependency imports.
- Verify Qdrant is reachable.
- Start the FastAPI backend with local embedding/Qdrant and dummy LLM values.
- Verify `/health`, `/npcs`, `/npcs/status`, and `/chat` behavior.
- Create a Markdown startup guide under `docs/`.

## Out of Scope
- No real LLM key will be written or tested.
- No business logic changes.

## Acceptance Criteria
- Backend starts locally and core endpoints respond.
- Any remaining caveat is documented clearly.
- Markdown guide contains copyable startup commands.

## Verification Commands
- `.venv311/bin/python --version`
- `.venv311/bin/python -c "... imports ..."`
- `curl http://127.0.0.1:6333/`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/npcs`
- `curl http://127.0.0.1:8000/npcs/status`
- `curl -X POST http://127.0.0.1:8000/chat ...`

## Risks
- `/chat` with dummy LLM can only verify backend error handling, not real model quality.
