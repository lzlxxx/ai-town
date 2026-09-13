# Active Execution Log

## 2026-06-20 CyberTown Player Profile System
- Started design planning for NPC learning of each player's preferences and habits using the `grill-me` workflow.
- Confirmed v1 architecture: global per-player profile with NPC role-aware expression boundaries.
- Confirmed learning inputs: chat content, chat timestamps, task events, and relationship/affinity events only.
- Confirmed rule-based synchronous extraction, optional off-path LLM summarization, SQLite persistence, aggregate profile items, lightweight event logs, confidence thresholds, correction statuses, local-time habits, prompt filtering, and mention cooldowns.
- Confirmed the default profile database path as `Helloagents-AI-Town/backend/profile_data/player_profiles.db`, with `PLAYER_PROFILE_DB_PATH` override support.
- Added design documentation and an active execution plan before any feature implementation.
- Confirmed implementation scope excludes Godot UI; backend profile API uses `player_id` path params and PATCH only updates item `status`.
- Confirmed API responses should include machine-readable fields plus player-readable labels/summaries, labels use built-in mapping plus fallback, extraction uses small bilingual keyword sets, NPC source counts live in item metadata, and profile failures must not block chat.
- Started backend implementation after design convergence.
- Added focused player profile tests first; initial run failed on missing `player_profile_manager`, as expected.
- Implemented SQLite-backed `PlayerProfileManager` with topic extraction, correction handling, time habits, source counts, prompt filtering, mention cooldowns, status updates, clearing, and safe profile summaries.
- Integrated profile context and non-blocking profile updates into `NPCAgentManager`, including task-event and relationship-event signals.
- Added `player_id` to chat models, profile Pydantic models, and profile API endpoints.
- Verified player profile focused checks, backend compilation, existing emotion checks, profile API/model smoke check, and `codegraph sync .`.
- Moved the player profile execution plan to `completed/` after verification.

## 2026-06-20 CyberTown NPC Emotion System
- Started implementation of v1 long-running NPC emotion system after design grilling.
- Confirmed final storage boundary: emotion state and recent history stay in backend memory only; no memory metadata writes and no restart restoration in v1.
- Created active execution plan and design document before feature code edits.
- Planned minimal TDD path: focused backend emotion tests first, then implementation, API/Godot integration, compile and Godot headless verification.
- Added focused backend emotion checks before implementation; initial run failed on missing `get_emotion_state`, as expected.
- Implemented in-memory `joy/sadness/anger/excitement` state, dominant emotion summaries, bounded recent history, prompt modifiers, LLM JSON parsing, rule fallback, decay toward NPC baselines, and weak affinity coupling in `RelationshipManager`.
- Extended `NPCAgentManager`, Pydantic models, and FastAPI chat/NPC info responses to include emotion summaries.
- Updated Godot `APIClient` chat signal to include emotion and displayed the dominant emotion in `DialogueUI`.
- Fixed a Godot `api_client.gd` indentation parse error found during headless verification.
- Verified backend compilation, focused emotion tests, API/model smoke checks, Godot 4.7 headless project load, and codegraph sync/status.
- Remaining unrelated warnings: Godot audio path case mismatch and ObjectDB/resource cleanup warnings on headless quit.

## 2026-06-20 CyberTown NPC Task System
- Started implementation of the first-version NPC task system after user approval.
- Confirmed scope: preset task templates, backend in-memory task state, task completion event written to NPC memory, independent Godot task panel opened with `T`.
- Confirmed Godot-side task cache behavior: first panel open fetches `/tasks`; later opens use cache and refresh after chat or accept.
- Added design document and active execution plan before code edits.
- Added backend `TaskManager`, task response models, `/tasks`, and `/tasks/{task_id}/accept`.
- Integrated task context and task events into `NPCAgentManager.chat_with_events`.
- Added dialogue-based task acceptance/completion rules, +10 affinity reward, and high-importance episodic memory writes for completed tasks.
- Added Godot `APIClient` task calls and automatic task refresh after chat.
- Added independent Godot task panel scene/script, opened with `T`, with accept and dismiss actions.
- Verified Python backend compilation.
- Verified `/tasks`, affinity unlock, and task accept routes with a temporary backend on port `8001`.
- User restarted Docker Qdrant; verified `ai-town-qdrant` is running, `GET /` returns 200, and collections include `ai_town_local`.
- Verified real Qdrant-backed episodic task completion memory write using a temporary SQLite directory and test collection.
- Verified Godot 4.7 headless project load succeeds; remaining audio path case warnings and exit leak warnings are existing unrelated project warnings.
- Synced codegraph after implementation; status reports 16 files, 244 nodes, and 469 edges.

## 2026-06-20 Affinity Separate LLM Configuration
- Started implementation for separate affinity-analysis LLM gateway settings.
- User requirement: affinity analysis must support independent base URL, API key, and model ID, not only a separate model name.
- Plan: create a dedicated affinity LLM instance with fallback to the main LLM configuration.
- Added `CyberTownLLM(max_retries=...)` support for per-instance retry settings.
- Added dedicated `RelationshipManager.affinity_llm` built from `LLM_AFFINITY_API_KEY`, `LLM_AFFINITY_BASE_URL`, and `LLM_AFFINITY_MODEL_ID`, with fallback to main `LLM_*`.
- Added `LLM_AFFINITY_MAX_RETRIES` and `LLM_AFFINITY_FALLBACK_TO_MAIN`.
- Current local `.env` sets affinity model to `deepseek-v4-flash` while reusing the main base URL and API key unless separate values are filled.
- Real smoke test showed `deepseek-v4-flash` can answer a tiny `OK` prompt, but a full affinity-analysis prompt returned a gateway `500`; added main-model fallback for that case.

## 2026-06-20 Godot Dialogue History And Enter Send
- Started UI improvement for Godot dialogue history and Enter-to-send behavior.
- Found `dialogue_ui.gd` clears `DialogueText` on every `start_dialogue`, so previous visible chat is not shown after reopening.
- Found Enter handling exists in multiple paths, but will centralize button, LineEdit submit, and global Enter handling through a single submit method.
- Updated `dialogue_ui.gd` to keep per-NPC in-memory visible chat history for the current game run.
- Updated sending so Send button, LineEdit submission, and Enter/KP Enter use `_submit_message`.
- Added one-pending-chat guard because `APIClient` has one `/chat` HTTPRequest node.
- Verified Godot 4.7 headless project load succeeds; remaining audio path case warnings are unrelated.
- Ran codegraph sync after the UI change.

## 2026-06-20 Affinity Timeout Log Cleanup
- Started fix for terminal noise shown in screenshots during NPC chat.
- Identified that the NPC main response succeeds, then `RelationshipManager.analyze_and_update_affinity` times out and prints a full traceback.
- Created an active execution plan scoped to affinity-analysis fallback logging only.
- Updated affinity analysis to return concise fallback reasons and stop printing full tracebacks for expected LLM analysis failures.
- Added `LLM_AFFINITY_ENABLED` so local testing can skip the auxiliary affinity LLM call.
- Verified backend compilation, simulated timeout fallback, and disabled-affinity behavior.
- Synced codegraph after the code change; index is up to date.

## 2026-06-20 Code Indexing Setup
- Started indexing setup for `/Users/brianye/PycharmProjects/AI-town`.
- Confirmed project Harness exists under `docs/exec-plans`.
- Confirmed `codegraph` CLI exists at `/opt/homebrew/bin/codegraph`.
- Found no existing `.codegraph` path from the initial file scan.
- `codegraph status` reported the project was not initialized.
- Ran `codegraph init .`, then `codegraph index .`; indexed 15 files, 188 nodes, and 333 edges.
- Verified `.codegraph/codegraph.db` exists and `codegraph status .` reports the index is up to date.
- Verified codegraph MCP can read the index through `codegraph_status` and `codegraph_files`.
- Ran fast-context MCP semantic search; it returned 11 relevant files across backend Python and Godot `.gd` scripts.
- Noted limitation: current codegraph index includes Python/XML but not Godot `.gd`; use fast-context for Godot-side semantic lookup.

## 2026-06-20 LLM Gateway Response Compatibility
- Started debugging the screenshot error: backend starts, Qdrant connects, but batch NPC dialogue generation fails with `'str' object has no attribute 'choices'`.
- Found the failure is in the LLM invocation path, not the vector database or Godot client.
- Created an active execution plan to keep the fix scoped to third-party gateway response compatibility and documentation.
- Added project-side `CyberTownLLM` wrapper and routed NPC manager plus batch generator through it.
- Verified backend Python compilation, imports, and local response extraction without calling the real gateway.
- Updated local `.env` base URL to include `/v1` and documented the screenshot error in the startup guide.
- Real gateway smoke test returned `OK`, confirming the current key/base URL/model combination works.
- Started a temporary backend on port `8001`; batch NPC dialogue generation succeeded with the real gateway.
- Verified `/health`, `/npcs`, `/npcs/status`, and `/chat` on port `8001`; single chat returned 200, while auxiliary affinity analysis timed out and degraded safely.
- Added no-retry and short affinity-analysis timeout settings to avoid multi-minute chat delays on slow gateway responses.
- Re-ran compilation, import checks, configuration checks, and a real gateway `OK` smoke test after the timeout changes.
- Restarted a temporary backend on port `8001`; startup, real batch dialogue generation, `/health`, `/npcs`, and `/npcs/status` all passed.
- Stopped the temporary backend and confirmed port `8001` has no remaining listener.

## 2026-06-20 CyberTown Startup Verification
- Started environment/startup analysis for `/Users/brianye/PycharmProjects/AI-town`.
- Found extracted project under `Helloagents-AI-Town/`.
- Found no git repository and no existing project Harness; created minimal execution plan structure.
- Initial concern: existing `.venv` appears to use Python 3.14, while project documentation recommends Python 3.10+ and dependencies may not yet support 3.14 reliably.
- Created a separate Python 3.11 virtual environment at `.venv311` using `uv`.
- Installed backend dependencies from `backend/requirements.txt`.
- Startup initially failed because `hello-agents==0.2.9` imports `huggingface_hub` without declaring it in project requirements; installed `huggingface_hub`.
- Verified that no MySQL/Redis/Neo4j setup is required for this project startup.
- Verified local SQLite memory databases exist under `Helloagents-AI-Town/backend/memory_data/<NPC>/memory.db`; tables are initialized by `hello-agents`.
- Started local Qdrant via Docker container `ai-town-qdrant` on port `6333` for episodic vector memory.
- Installed `qdrant-client`, `socksio`, and `sentence-transformers` to satisfy vector memory and local network proxy requirements.
- Downloaded the default local embedding model `sentence-transformers/all-MiniLM-L6-v2` during startup.
- Verified FastAPI startup with local Qdrant and local embeddings using dummy LLM configuration.
- Verified `GET /health`, `GET /npcs`, `GET /npcs/status`, and `GET /npcs/张三/memories`; `/npcs` returned all three NPCs with `available=true`.
- Remaining user action: start backend with real third-party LLM gateway values for `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL_ID`.

## 2026-06-20 CyberTown Environment Audit
- Started a follow-up audit to check whether any dependency, environment variable, or middleware remains missing.
- Verified `.venv311` uses Python 3.11.15.
- Verified imports for FastAPI, Uvicorn, Pydantic, Requests, HTTPX, OpenAI, HelloAgents, HuggingFace Hub, Qdrant client, socksio, sentence-transformers, torch, transformers, scikit-learn, numpy, and python-dotenv.
- Verified Docker Qdrant container `ai-town-qdrant` is running on port `6333`.
- Verified Qdrant HTTP readiness via `GET http://127.0.0.1:6333/`.
- Verified Qdrant collections include `ai_town_local`.
- Verified Godot is installed at `/Applications/Godot.app` and CLI is available at `/opt/homebrew/bin/godot`.
- Verified backend startup with dummy LLM configuration, local embedding, and Qdrant.
- Verified `GET /health`, `GET /npcs`, and `GET /npcs/status`; all three NPCs returned `available=true`.
- Stopped dummy backend test process so port `8000` is free.
- Remaining unchecked item: real third-party LLM gateway connectivity requires the user's actual key/base URL/model.

## 2026-06-20 Final Startup Test And Runbook
- Started final verification and runbook creation.
- Confirmed port `8000` is free and Qdrant container `ai-town-qdrant` is running.
- Verified dependency imports with `.venv311/bin/python`; no missing modules found.
- Verified Qdrant readiness at `http://127.0.0.1:6333/` and collections endpoint.
- Verified Godot app and project file exist.
- Started backend with dummy LLM, local embedding, and Qdrant collection `ai_town_local`.
- Verified `GET /health`, `GET /npcs`, and `GET /npcs/status`.
- Verified `/chat` error-handling path with dummy LLM; it returned a controlled fallback message rather than crashing.
- Added `docs/cybertown-startup-guide.md` with startup, verification, Godot, shutdown, and troubleshooting steps.
- Stopped the dummy backend process after verification and confirmed port `8000` is free; Qdrant remains running for user startup.

## 2026-06-20 Third-Party LLM Gateway Configuration
- Started config hardening for third-party OpenAI-compatible gateway usage.
- Found `hello-agents` reads `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL_ID` directly from environment variables.
- Found current backend config does not auto-load `.env` and does not normalize common aliases like `LLM_MODEL`, `OPENAI_API_KEY`, or `OPENAI_BASE_URL`.
- Updated `backend/config.py` to auto-load `backend/.env`, normalize common aliases, and strip accidental `/chat/completions` suffixes from base URLs.
- Updated `backend/.env.example`, `docs/cybertown-startup-guide.md`, `backend/README.md`, and `SETUP_GUIDE.md` to document third-party gateway variables.
- Verified alias mapping with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL`.
- Verified `.env` loading with a temporary dummy `.env`, then removed the temporary file.
- Started backend using only `OPENAI_*` aliases plus local embedding/Qdrant; verified `/health` and `/npcs`.
- Stopped the test backend process and confirmed no dummy `.env` remains.

## 2026-06-20 Final Project Check And Startup Guide Update
- Started final check after third-party LLM gateway config changes.
- Verified backend Python files compile successfully.
- Verified required Python imports; no missing modules found.
- Verified third-party gateway alias mapping still works and strips `/chat/completions` suffix.
- Verified Qdrant health and `ai-town-qdrant` container state.
- Started backend with dummy OpenAI-compatible alias settings and local Qdrant/embedding.
- Verified `/health`, `/npcs`, `/npcs/status`, and `/chat` controlled fallback behavior.
- Stopped the dummy backend process and confirmed no `.env` secret file remains.
- Rewrote `docs/cybertown-startup-guide.md` as the latest startup and usage guide.
