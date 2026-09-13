# Godot Dialogue History And Enter Send

## Goal
- Keep visible per-NPC chat history when the player closes and reopens a dialogue in the same game session.
- Make Enter/KP Enter reliably trigger the same send path as the Send button.

## Scope
- Modify `Helloagents-AI-Town/helloagents-ai-town/scripts/dialogue_ui.gd`.
- Preserve UI chat history in memory per NPC for the current Godot run.
- Keep backend memory behavior unchanged.
- Verify GDScript syntax with the installed Godot CLI if available.

## Out of Scope
- No backend API changes.
- No persistent chat UI history across game restarts.
- No UI redesign of the dialogue panel.

## Plan
1. Inspect current Godot dialogue UI script and input handling.
2. Add an in-memory per-NPC dialogue history store.
3. Centralize send behavior so button, LineEdit submit, and Enter key use one method.
4. Ensure late NPC replies are stored under the correct NPC even if the panel is closed.
5. Run syntax/project checks where possible.

## Acceptance Criteria
- Reopening the same NPC during one game run shows previous visible messages.
- Enter sends messages when the dialogue is visible and input text is non-empty.
- Send button behavior remains unchanged.
- Backend long-term NPC memory remains independent from UI transcript history.

## Verification Commands
- `godot --headless --path Helloagents-AI-Town/helloagents-ai-town --quit`
- `codegraph sync .`

## Risks
- Godot CLI may require display/graphics resources even in headless mode.
- This change stores UI history only in memory; restarting the game clears it.

## Verification Results
- Godot headless project load succeeded with Godot `4.7.stable`.
- `dialogue_ui.gd` initialized successfully during the headless run.
- Existing warnings remain for audio resource path case mismatch: `assets/Audio` vs `assets/audio`; unrelated to this change.
- Codegraph sync ran after the change; no Python index changes were needed because `.gd` scripts are not indexed by current codegraph.

## Decisions
- Keep UI chat history in memory by NPC for the current game run.
- Do not persist visible UI transcript across Godot restarts yet; backend memory remains the persistent NPC memory layer.
- Keep a single pending chat request because `APIClient` uses one `HTTPRequest` node for `/chat`.
