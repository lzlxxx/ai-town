# CyberTown Player Profile System

## Objective

Implement a v1 player profile system for CyberTown so NPCs can learn durable per-player preferences and habits, then use those signals in NPC replies through compact, role-aware prompt context.

## Scope

In scope:

- Add a dedicated `PlayerProfileManager`.
- Persist aggregated player profiles and lightweight profile events in SQLite at `Helloagents-AI-Town/backend/profile_data/player_profiles.db` by default, with `PLAYER_PROFILE_DB_PATH` override support.
- Learn from chat content, chat timestamps, task events, and relationship/affinity events.
- Use rule-based topic extraction and explainable confidence scoring on the main chat path.
- Track top-level categories and extensible tags.
- Track real-local-time activity buckets.
- Inject stable, active, role-relevant profile context into NPC prompts.
- Respect profile status, confidence thresholds, and mention cooldowns.
- Add backend APIs to view, clear, and update profile item status.
- Add focused backend tests for storage, extraction, scoring, time habits, API controls, and prompt context.

Out of scope:

- Godot profile-management UI.
- NPC background interruption, autonomous approach, movement changes, or refresh-rate changes.
- Location and dwell-time analytics.
- LLM summarization in the synchronous chat path.
- Replacing existing per-NPC dialogue memory.
- Persisting or redesigning the existing emotion/task systems.

## Plan

1. Add the player profile design documentation and active execution tracking.
2. Add focused backend tests for profile storage, event recording, topic scoring, time bucket inference, correction status handling, and prompt context filtering.
3. Implement `PlayerProfileManager` with SQLite schema initialization, aggregate item updates, event writes, status updates, and deletion.
4. Add rule-based topic and correction extraction for current chat messages and task/relationship events.
5. Integrate profile update and prompt-context retrieval into `NPCAgentManager.chat_with_events`.
6. Add FastAPI response/request models and profile endpoints.
7. Add mention cooldown handling and compact prompt context formatting.
8. Run backend compile/tests and API smoke checks.
9. Update docs with verification results and move this plan to `completed/` only after implementation and verification pass.

## Acceptance Criteria

- Profiles persist across backend restarts in a dedicated SQLite store.
- Chat topic signals create lightweight profile events and update aggregate profile items.
- Stable profile items require confidence `>= 0.6` before prompt injection.
- Strong profile items use confidence `>= 0.8` but still respect cooldowns.
- Explicit player correction can suppress or reject a profile item and prevents prompt injection.
- Active-time habits use real local time buckets and require repeated evidence before prompt injection.
- NPC prompt context is role-aware, limited to at most 3 interest items and 1 time habit.
- Same NPC/profile-item proactive mentions respect a cooldown of at least 3 conversations.
- `GET /players/{player_id}/profile` returns a readable profile summary.
- `DELETE /players/{player_id}/profile` clears that player's profile data.
- `PATCH /players/{player_id}/profile/items/{item_id}` can update item status.
- Normal logs avoid printing full profile content or raw player messages from profile events.
- Existing chat, emotion, affinity, and task behavior remains compatible.

## Test Data

Use deterministic backend tests with sample messages:

- 张三: "我最近一直在学 Python, 还在调试 Flask 报错。"
- 张三: "这个 Python bug 又卡住了, 能聊聊日志和断点吗?"
- 王五: "我想看看这个界面的颜色和按钮层级。"
- 李四: "我最近在找工作, 也想了解产品经理怎么收集用户反馈。"
- Correction: "我其实不喜欢 Python, 以后别老提这个。"
- Time habit: multiple interactions with injected timestamps in `evening`.

Expected classifications:

- `programming/python`
- `programming/debugging`
- `design/color`
- `design/ui_feedback`
- `career/job_search`
- `product/user_feedback`
- `time/evening`

## Verification Commands

- `.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend`
- `.venv311/bin/python Helloagents-AI-Town/backend/tests/test_player_profile_system.py`
- `.venv311/bin/python -c "... profile API/model smoke check ..."`
- Optional after endpoint integration: run a temporary backend and check `/players/player/profile`.
- `codegraph sync .`

## Risks

- Topic keyword rules can overfit English or Chinese phrasing if the first taxonomy is too small.
- Profile prompt context can feel repetitive without strict cooldowns.
- Persisted profiles need deletion and suppression controls to avoid privacy and product trust issues.
- Chat latency can grow if LLM summarization is accidentally put on the main path.
- Existing per-NPC memory retrieval is not player-filtered in the retrieved code path, so profile design must not assume memory is already a clean global source.

## Decision Log

- Use a hybrid model: global per-player profile plus NPC role-aware expression.
- Learn only from chat content, timestamps, task events, and relationship/affinity events in v1.
- Use rule-based extraction on the main path and keep LLM summarization optional/off-path.
- Persist profiles in a dedicated SQLite store through `PlayerProfileManager`.
- Use `Helloagents-AI-Town/backend/profile_data/player_profiles.db` as the default SQLite path and support `PLAYER_PROFILE_DB_PATH` for overrides.
- Store aggregate profile items plus lightweight structured profile events.
- Use fixed top-level categories with extensible tags.
- Require repeated evidence and confidence thresholds before long-term prompt injection.
- Treat explicit player corrections as higher priority than statistical inference.
- Use real local server time for v1 activity buckets.
- Let time habits affect reply tone/content only, not movement or refresh behavior.
- Inject only compact, active, role-relevant profile items with cooldowns.
- Expose backend profile view, deletion, and item status controls before Godot UI.
- Exclude Godot profile-management UI from this implementation round.
- Use URL path `player_id` for profile APIs.
- Let profile item `PATCH` update only `status`.
- Return machine-readable profile structures plus player-readable labels and summaries.
- Generate labels from a built-in mapping with fallback.
- Use a small bilingual keyword set for v1 extraction.
- Store NPC source counts as profile item metadata.
- Treat profile update/context failures as non-blocking chat warnings.

## Implementation Summary

- Added `Helloagents-AI-Town/backend/player_profile_manager.py`.
- Added `Helloagents-AI-Town/backend/tests/test_player_profile_system.py`.
- Extended `NPCAgentManager` with player profile prompt context, safe chat-side profile updates, task-event profile updates, and profile API helper methods.
- Extended `ChatRequest` and `ChatResponse` with `player_id`.
- Added profile response/request models.
- Added `GET /players/{player_id}/profile`, `DELETE /players/{player_id}/profile`, and `PATCH /players/{player_id}/profile/items/{item_id}`.

## Verification Results

- Initial TDD run failed on missing `player_profile_manager`, as expected.
- Player profile focused checks passed: storage persistence, topic scoring, correction rejection, role-aware prompt filtering, time habits, status update, deletion, and non-blocking simulated chat failure.
- Backend Python compilation passed.
- Existing emotion system checks passed.
- Profile API/model smoke check passed without starting a server.
- `codegraph sync .` passed and reported the index was already up to date.
