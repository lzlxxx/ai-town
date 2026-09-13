# CyberTown Player Profile System

## Goal

Add a v1 player profile layer so NPCs can learn each player's preferences and habits over time. The system should remember durable signals such as programming interest, favorite topics, and active play windows, then let NPC replies reflect those signals without making every NPC feel omniscient.

## Core Boundary

Version 1 uses a hybrid model:

- A global profile is stored per `player_id`.
- NPC expression remains role-aware and bounded by what is natural for the current NPC.
- Existing per-NPC memory stays responsible for dialogue recall.
- The player profile store becomes the source of truth for long-running preference and habit inference.

This keeps durable player learning separate from `memory_data/{npc}` while still letting NPCs speak with their own context and domain.

## Learning Signals

Version 1 learns from:

- Chat message content and timestamps from `POST /chat`.
- Task acceptance and completion events.
- Relationship and affinity events that already happen in the chat flow.

Version 1 does not learn from movement traces, map location dwell time, click telemetry, or raw online duration. Those require additional Godot instrumentation and should be designed separately.

## Topic Model

Profile topics use stable top-level categories plus extensible tags.

Top-level categories:

- `programming`
- `product`
- `design`
- `gameplay`
- `social`
- `career`
- `other`

Example tags:

- `programming/python`
- `programming/debugging`
- `design/color`
- `product/user_feedback`
- `career/job_search`

Top-level categories support predictable API output and prompt filtering. Tags preserve specific player interests without hard-coding every possible topic into the model.

Version 1 extraction uses a small bilingual keyword set so Chinese dialogue and common English technical terms both work. Core labels use a built-in mapping, such as `programming/python` -> `Python` and `design/color` -> `颜色`; unknown tags fall back to their final path segment.

## Storage Model

Version 1 should use a dedicated `PlayerProfileManager` with SQLite-backed storage.
The default database path is `Helloagents-AI-Town/backend/profile_data/player_profiles.db`.
`PLAYER_PROFILE_DB_PATH` can override this path for tests, local experiments, and deployment-specific storage.

The store should include:

- Aggregated profile items for fast prompt/API reads.
- Lightweight profile events for debugging, explanation, and future recomputation.

Profile items should store:

- `player_id`
- `category`
- `tag`
- `confidence`
- `evidence_count`
- `source_npcs`
- `status`
- `evidence_summary`
- `last_seen_at`
- `last_mentioned_at`
- `last_mentioned_by_npc`
- `mention_count`
- `updated_at`

Profile events should store structured signals, not full raw dialogue:

- `player_id`
- `event_type`
- `npc_name`
- `category`
- `tag`
- `weight`
- `occurred_at`
- `evidence_summary`

The complete dialogue remains in the existing NPC memory system. The profile database stores durable conclusions and short evidence summaries only.

NPC source information is stored as item metadata through `source_npcs` and `source_counts`. Version 1 does not use a separate player-topic-NPC table.

## Confidence

Version 1 uses explainable weighted scoring:

- Normal keyword/topic hit: `+0.15`
- Explicit "like", "often", "interested in", or similar expression: `+0.30`
- Task completion or strong interaction evidence: `+0.20`
- Same category appears across multiple NPCs: `+0.15`
- Evidence appeared within the recent window, such as 7 days: `+0.10`
- Explicit player denial or correction overrides statistical inference.
- Items decay slowly when no fresh evidence appears, such as `-0.05` per week.

Thresholds:

- `< 0.4`: weak signal, store evidence only.
- `0.4-0.59`: candidate preference, do not inject into prompts.
- `0.6-0.79`: stable preference, eligible for prompt injection.
- `>= 0.8`: strong preference, eligible for more natural proactive mention, still subject to cooldown.

Explicit player statements carry more weight than keyword inference. A single message can be used in the current reply context, but it must still pass confidence thresholds before becoming a long-term prompt signal.

## Profile Status

Profile items support these states:

- `active`: eligible for prompt injection when confidence and filtering rules allow it.
- `suppressed`: still stored but not mentioned by NPCs.
- `stale`: retained at low priority after long inactivity.
- `rejected`: explicitly denied by the player and not automatically restored without strong future evidence.

Player correction must outrank statistical inference. For example, "I actually do not like Python" should suppress or reject `programming/python` even if earlier evidence existed.

## Time Habits

Version 1 learns active-time habits from real local server time because the project currently uses `datetime.now()` for status text and memory timestamps and does not expose a separate game-clock system.

Recommended buckets:

- `morning`: 06:00-11:59
- `afternoon`: 12:00-17:59
- `evening`: 18:00-22:59
- `late_night`: 23:00-05:59

A time habit should require repeated evidence, such as at least 5 interactions and more than 45% of recent interactions in the same bucket. Time habits should affect NPC reply tone and content only in v1. They should not increase NPC refresh frequency, movement frequency, task probability, or LLM call volume.

## Update Flow

1. The player sends a chat message.
2. The chat path extracts lightweight current-turn topic signals before generating the NPC reply.
3. The prompt may include current-turn signals as immediate context.
4. The prompt also receives stable profile context from `PlayerProfileManager`, filtered by NPC role, confidence, status, and cooldown.
5. The NPC reply is generated.
6. Chat, task, and relationship events are written as lightweight profile events.
7. Aggregated profile items are updated synchronously with rule-based scoring.
8. Optional LLM profile summarization may run later through a maintenance endpoint or background job.

LLM profile summarization must not run on the main chat path in v1. Profile learning should still work if all LLM summarization fails.

## Prompt Injection

Profile context should be compact and role-aware.

Rules:

- Inject at most 3 interest items and 1 time-habit item.
- Prefer topics related to the current NPC role.
- Allow high-confidence general signals when they are naturally useful.
- Never inject `suppressed`, `rejected`, or low-confidence candidate items.
- Use short conclusions, not raw evidence.
- Respect per-item and per-NPC mention cooldowns.

Example mapping:

- 张三 receives `programming/python`, `programming/debugging`, and relevant time habits.
- 李四 receives `product/user_feedback`, `career/job_search`, and relevant time habits.
- 王五 receives `design/color`, `design/ui_feedback`, and relevant time habits.

Cooldown rules:

- The same NPC should not proactively mention the same profile item again until at least 3 more conversations have passed.
- Each reply should mention at most 1 long-term preference.
- If the player is already discussing the topic, natural continuation is allowed and does not count as proactive mention.
- Time-habit mentions should be extra conservative, such as once per day.

## API

Version 1 should expose backend profile controls before Godot UI integration:

- `GET /players/{player_id}/profile`
- `DELETE /players/{player_id}/profile`
- `PATCH /players/{player_id}/profile/items/{item_id}`
- Optional later endpoint: `POST /players/{player_id}/profile/summarize`

The API should support viewing profile summaries, clearing all profile data for a player, and changing item status between active, suppressed, stale, and rejected where appropriate.

API responses include machine-readable fields and player-readable labels/summaries. `player_id` is part of the URL path for profile resources. `PATCH /players/{player_id}/profile/items/{item_id}` only updates `status`; confidence, tags, and evidence remain system-managed.

Godot profile-management UI is not part of v1. NPCs can still use profile context in chat once the backend feature is enabled.

## Failure Handling

Player profile learning is auxiliary. If profile extraction, storage, or prompt-context generation fails, the chat flow should continue and only emit a concise warning. A profile failure must not block NPC replies, task processing, affinity, or emotion updates.

## Privacy And Logging

The feature stores inferred personal preferences, so it needs explicit control surfaces.

Rules:

- Do not log full player profiles in normal logs.
- Log counts, item ids, and high-level status changes only.
- Do not copy full raw chat messages into profile events.
- Allow player profile deletion.
- Only active items that pass threshold and filters may influence prompts.

## Out Of Scope For V1

- Godot UI for viewing or editing the profile.
- Background NPC interruption or autonomous approach behavior.
- Movement, task probability, or NPC status refresh changes based on profile data.
- Location-based habits or online-duration analytics.
- LLM summarization inside the synchronous chat path.
- Replacing the existing NPC memory system.
