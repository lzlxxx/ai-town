# CyberTown Environment Audit

## Goal
- Verify whether any dependency, environment variable, or middleware is still missing for running CyberTown locally.

## Scope
- Check Python runtime and installed backend dependencies.
- Check required extra packages used by `hello-agents`.
- Check Qdrant Docker container and HTTP readiness.
- Check backend startup with local embedding/Qdrant configuration.
- Check Godot installation status and client API configuration.

## Out of Scope
- No application code changes.
- No API keys or secrets will be written to files.

## Plan
1. Inspect project config and dependency declarations.
2. Verify Python imports for required backend modules.
3. Verify Docker/Qdrant state and Qdrant HTTP readiness.
4. Verify backend can start and expose basic endpoints.
5. Verify whether Godot is installed or still missing.
6. Summarize required, optional, and missing items.

## Acceptance Criteria
- Produce a clear list of ready/missing items.
- Provide exact commands for any remaining setup.

## Verification Commands
- `.venv311/bin/python --version`
- `.venv311/bin/python -c "... imports ..."`
- `docker ps --filter name=ai-town-qdrant`
- `curl http://127.0.0.1:6333/`
- `curl http://127.0.0.1:8000/health`
- `curl http://127.0.0.1:8000/npcs`

## Risks
- Real LLM connectivity cannot be fully verified without the user's actual third-party gateway key.
- Godot may not be installed yet on this machine.
