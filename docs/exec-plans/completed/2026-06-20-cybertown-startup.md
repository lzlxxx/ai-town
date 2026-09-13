# CyberTown Startup Verification

## Goal
- Bring the extracted CyberTown project to a runnable local state.
- Identify the minimum required runtime, environment variables, and external services.

## Scope
- Inspect backend and Godot startup requirements.
- Set up Python dependencies in an isolated environment if needed.
- Start the FastAPI backend and verify basic API endpoints.
- Provide Godot launch steps.

## Out of Scope
- No business-code changes unless startup is blocked by a confirmed code defect.
- No secrets will be written into repository files.

## Plan
1. Read project startup docs and backend configuration.
2. Determine whether Qdrant, Neo4j, or other middleware is strictly required for first launch.
3. Prepare Python environment and dependencies.
4. Start backend with third-party LLM gateway environment variables.
5. Verify `/health`, `/npcs`, and `/npcs/status`.
6. Summarize remaining risks and Godot startup steps.

## Acceptance Criteria
- Backend can start locally on `http://localhost:8000`, or the exact blocker is documented.
- Required environment variables and optional middleware are clearly separated.
- User receives reproducible startup commands.

## Verification Commands
- `python --version`
- `pip install -r requirements.txt`
- `python main.py`
- `curl http://localhost:8000/health`
- `curl http://localhost:8000/npcs`
- `curl http://localhost:8000/npcs/status`

## Risks
- Current `.env` is not auto-loaded by the code.
- Python 3.14 may be too new for some dependencies; Python 3.10 or 3.11 is safer.
- LLM gateway model names and base URLs vary by provider.
- Memory dependencies may require embeddings/vector storage depending on `hello-agents` behavior.

## Decision Log
- Do not write API keys into `.env`; use shell exports for this run.
