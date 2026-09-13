# CyberTown NPC Task System

## Goal

Add a first-version NPC task loop for resume/demo use:

- Tasks unlock when NPC affinity reaches 60.
- Each NPC owns one preset task.
- Players can accept tasks from dialogue keywords or the task panel.
- Task completion is judged from NPC dialogue, not from a separate form.
- Completion grants affinity reward and writes an important event into the NPC memory system.

## Scope

Version 1 uses deterministic preset task templates and rule-based completion checks. LLM-generated tasks are a future extension, not part of this implementation.

Backend is the source of truth. Task state is kept in backend memory for the current server run. Godot caches task data after the first `/tasks` fetch, then refreshes after chat or task acceptance.

## Task Templates

| NPC | Task | Completion Rule |
| --- | --- | --- |
| 张三 | 帮张三调试代码 | Player discusses debugging/code analysis keywords with 张三. |
| 李四 | 帮李四收集用户反馈 | Player must talk to 王五 first, then report feedback keywords to 李四. |
| 王五 | 帮王五评价设计方案 | Player discusses visual/design/usability keywords with 王五. |

## States

- `locked`: affinity is below unlock threshold.
- `available`: affinity reached threshold and task can be accepted.
- `active`: task has been accepted.
- `completed`: task has been completed and rewarded once.

There is no persistent `rejected` state. "暂不接受" only closes or ignores the panel action.

## API

- `GET /tasks`: returns all NPC tasks for the player.
- `POST /tasks/{task_id}/accept`: accepts one available task.
- `POST /chat`: can return `task_events` in addition to the NPC reply.

## Godot UX

- Press `T` to open or close the task panel.
- First open fetches `/tasks`; later opens render cached tasks and refresh in the background.
- Available tasks show `接受` and `暂不接受`.
- Active/completed/locked tasks show status and hints.
- After chat succeeds, Godot refreshes `/tasks`.

## Future Extension

LLM-generated task creation can be added later behind the same `TaskManager` boundary by replacing preset templates with generated templates and keeping the current API contract.
