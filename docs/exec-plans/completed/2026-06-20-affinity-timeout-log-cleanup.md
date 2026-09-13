# Affinity Timeout Log Cleanup

## Goal
- Stop noisy terminal tracebacks when NPC chat succeeds but auxiliary affinity analysis times out.
- Keep NPC dialogue, memory saving, and graceful affinity fallback working.

## Scope
- Update `backend/relationship_manager.py` exception handling for affinity analysis.
- Add an optional environment switch to disable affinity LLM analysis during local testing.
- Update `.env.example` and startup guide with the new switch and timeout behavior.
- Verify Python compilation/imports and focused fallback behavior.

## Out of Scope
- No Godot scene changes.
- No changes to main NPC response generation.
- No changes to memory database or Qdrant.

## Plan
1. Replace full traceback printing in affinity analysis with concise fallback messages.
2. Return clearer fallback reasons such as `分析超时` instead of generic `分析失败`.
3. Add `LLM_AFFINITY_ENABLED` for local testing.
4. Run compile/import checks and a focused unit-style fallback check.
5. Document restart instructions and residual gateway timeout behavior.

## Acceptance Criteria
- Affinity timeout no longer prints a long traceback.
- Chat can still return the NPC reply when affinity analysis fails.
- `LLM_AFFINITY_ENABLED=false` skips affinity LLM analysis and leaves affinity unchanged.

## Verification Commands
- `.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend`
- `.venv311/bin/python -c "... focused RelationshipManager fallback check ..."`

## Risks
- If the main NPC reply LLM call times out, that is still a real chat failure and should remain visible.
- Disabling affinity analysis means relationship scores will not change during that run.

## Verification Results
- Backend Python compilation passed.
- Simulated affinity timeout returned `{'changed': False, 'affinity': 50.0, 'reason': '分析超时', 'sentiment': 'neutral'}` and printed only one concise warning line.
- Simulated `LLM_AFFINITY_ENABLED=false` returned `分析已关闭` without calling the analyzer.
- Codegraph sync completed and status reports the index is up to date.

## Decision
- Keep main NPC response failures visible, but treat post-response affinity-analysis failures as graceful fallback.
- Default `LLM_AFFINITY_ENABLED=true`; users can disable it during local testing.
