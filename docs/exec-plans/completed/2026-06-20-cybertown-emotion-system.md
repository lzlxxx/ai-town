# CyberTown NPC Emotion System

## Goal

Implement v1 of a long-running NPC emotion system. Each NPC maintains multi-dimensional emotion state toward the player, and the state influences reply style, information sharing, API output, and Godot UI display.

## Scope

In scope:

- Add in-memory emotion state and recent emotion history per `npc_name + player_id`.
- Track `joy`, `sadness`, `anger`, and `excitement`.
- Compute `dominant` emotion, label, intensity, and prompt modifier.
- Update emotion through the existing relationship analysis path: LLM analysis first, rule fallback on parser/model failure.
- Weakly couple emotion deltas back into affinity changes with single-turn limits.
- Decay emotion toward NPC-specific baselines after each dialogue update.
- Return emotion data from `POST /chat`, `GET /npcs`, and `GET /npcs/{npc_name}`.
- Show dominant emotion in the Godot dialogue UI.
- Add focused backend checks for core emotion behavior.

Out of scope:

- No persistent emotion storage.
- No memory metadata writes for emotion state/history in v1.
- No cross-backend-restart restoration.
- No real-time decay.
- No movement behavior, proactive dialogue, or task-probability changes.

## Plan

1. Document the v1 design.
2. Add focused backend tests for baseline state, emotion update, dominant emotion, decay, and fallback parsing.
3. Extend `RelationshipManager` with emotion state/history helpers and relationship-analysis output.
4. Inject emotion prompt context in `NPCAgentManager.chat_with_events`.
5. Extend response models and API routes with emotion summaries.
6. Update Godot API parsing and dialogue UI display.
7. Run backend compile/tests and Godot headless load.
8. Move this plan to `completed/` when verification passes.

## Acceptance Criteria

- Each NPC/player pair has in-memory emotion values for `joy`, `sadness`, `anger`, and `excitement`.
- Emotion defaults to NPC baseline and resets on backend restart.
- Current emotion summary is injected into NPC prompts before generating replies.
- Dialogue analysis updates both affinity and emotion; analysis failures do not block chat.
- Emotion deltas weakly influence affinity with a single-turn clamp.
- `POST /chat` returns emotion summary and values after the update.
- `GET /npcs` and `GET /npcs/{npc_name}` return current emotion summaries.
- Godot dialogue UI displays the current dominant emotion label/intensity after chat.
- Emotion state/history is not written to memory metadata in v1.
- Backend compilation and focused tests pass.
- Godot headless project load succeeds, except for known unrelated warnings.

## Verification Commands

- `.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend`
- `.venv311/bin/python Helloagents-AI-Town/backend/tests/test_emotion_system.py`
- `.venv311/bin/python -c "... import/API model smoke check ..."`
- `/opt/homebrew/bin/godot --headless --path Helloagents-AI-Town/helloagents-ai-town --quit`
- `codegraph sync .`

## Risks

- LLM JSON output can be malformed; fallback parsing and rule defaults must be safe.
- Emotion-to-affinity coupling can make relationship changes noisy if not clamped.
- Godot UI must remain readable without redesigning the dialogue panel.

## Decision Log

- Use multi-dimensional emotion values plus dynamic dominant emotion.
- Keep all emotion state/history in memory for v1.
- Do not write emotion metadata into memory records in v1.
- Merge emotion responsibilities into `RelationshipManager` for v1.
- Apply updated emotion to the next NPC reply, not the same reply.

## Verification Results

- Backend Python compilation passed.
- Focused emotion system checks passed: baseline state, JSON parsing, emotion update, affinity coupling, rule fallback, and bounded history.
- API/model smoke check passed for `ChatResponse`, `NPCInfo`, and `NPCAgentManager.get_npc_info` emotion output.
- Godot 4.7 headless project load passed with the new dialogue emotion label and expanded chat signal.
- Existing Godot warnings remain for audio path case mismatch and ObjectDB/resource cleanup on quit; unrelated to this change.
- codegraph sync/status passed; index is up to date with 17 files, 273 nodes, and 541 edges.
