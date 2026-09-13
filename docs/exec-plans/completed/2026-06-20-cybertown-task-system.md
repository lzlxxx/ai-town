# CyberTown NPC Task System

## Objective

Implement the first-version NPC task system for CyberTown: preset NPC tasks, affinity-based unlocks, accept/reject UI actions, dialogue-based completion, affinity rewards, and task completion memory persistence.

## Scope

In scope:

- Backend in-memory task manager.
- FastAPI task list and accept endpoints.
- Optional task events in chat response.
- NPCAgentManager integration for task prompt context, acceptance, completion, reward, and memory write.
- Godot task API calls and an independent task panel toggled by `T`.
- Startup guide update for the new task feature.

Out of scope:

- Persistent task database.
- LLM-generated tasks.
- Complex inventory/reward economy.
- Separate task completion input form.

## Plan

1. Add task design documentation and execution tracking.
2. Add backend task models and `TaskManager`.
3. Wire `TaskManager` into `NPCAgentManager` and FastAPI routes.
4. Add Godot task endpoints to `APIClient`.
5. Add task panel scene/script and instantiate it from `main.gd`.
6. Verify Python compilation, backend routes, and Godot project load.
7. Move this plan to `completed/` if verification passes.

## Acceptance Criteria

- `GET /tasks` returns all three NPC tasks with status, hints, and unlock data.
- Tasks become `available` when the related NPC affinity is at least 60.
- `POST /tasks/{task_id}/accept` changes an available task to `active`.
- Dialogue can accept an available task with natural accept phrases.
- Dialogue can complete an active task with the configured completion rules.
- Completed tasks grant +10 affinity once and write an episodic memory event for the task owner.
- Godot task panel opens with `T`, shows all task states, and can accept or dismiss available tasks.
- Godot refreshes task cache after successful chat.

## Verification Commands

- `.venv311/bin/python -m compileall -q Helloagents-AI-Town/backend`
- Backend route smoke tests with dummy/offline-friendly configuration.
- `/opt/homebrew/bin/godot --headless --path Helloagents-AI-Town/helloagents-ai-town --quit`

## Verification Results

- Backend Python compilation passed.
- Task accept keyword regression check passed: `运行` no longer triggers task acceptance, while `好的,我来帮忙` does.
- Temporary backend on port `8001` verified `/tasks`, affinity unlock through `PUT /npcs/张三/affinity`, and `POST /tasks/zhang_debug_code/accept`.
- Qdrant Docker container `ai-town-qdrant` is running and `GET http://127.0.0.1:6333/` returns 200.
- Real Qdrant-backed episodic task completion memory write passed using a temporary SQLite directory and the `ai_town_local_test` collection.
- Godot 4.7 headless project load passed with the new task panel scene and script.
- codegraph status reports the index is up to date with 16 files, 244 nodes, and 469 edges.

## Residual Notes

- Godot still prints existing audio path case mismatch warnings for `assets/Audio` vs `assets/audio`.
- Godot still prints existing ObjectDB/resource leak warnings on headless quit.
- Task state is in-memory by design; restart resets task states.

## Risks

- Existing LLM gateway instability can affect real dialogue, so task completion must be rule-first and not require another model call.
- Task state is intentionally in-memory; restarting the backend resets accepted/completed state.
- Godot headless load may show existing audio path or resource leak warnings unrelated to this task system.

## Decision Log

- Use preset templates for version 1.
- Keep "暂不接受" as a UI-only dismiss action.
- Keep task completion through NPC dialogue only.
- Use backend as source of truth and Godot as a cache.
