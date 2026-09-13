# Code Indexing Setup

## Goal
- Build local code intelligence indexes for `/Users/brianye/PycharmProjects/AI-town` using `codegraph`.
- Verify `fast-context` MCP can inspect the project with a project-level semantic query.

## Scope
- Initialize or refresh local `.codegraph` data.
- Run codegraph health/status checks.
- Run one fast-context search against the project root to verify availability.
- Record commands and results in `docs/exec-plans/activeLog.md`.

## Out of Scope
- No source code changes.
- No dependency installation unless the indexing tools require it.
- No real LLM gateway calls for the game runtime.

## Plan
1. Confirm `codegraph` CLI availability and existing index state.
2. Run `codegraph init` or equivalent for the project root.
3. Verify index health through codegraph MCP/status.
4. Run a fast-context semantic search for the CyberTown project structure.
5. Move this plan to `completed/` after verification.

## Acceptance Criteria
- `.codegraph` exists or codegraph status reports an initialized project.
- Codegraph MCP can return project status or file/symbol data.
- Fast-context MCP returns project-level results without failing.

## Verification Commands
- `codegraph --help`
- `codegraph init`
- `codegraph status`
- `mcp__codegraph.codegraph_status`
- `mcp__fast_context.fast_context_search`

## Risks
- Fast-context may require a Windsurf API key or remote service availability.
- Codegraph may skip unsupported Godot `.gd` symbols depending on parser support.

## Verification Results
- `codegraph status` initially reported the project was not initialized.
- `codegraph init .` initialized `/Users/brianye/PycharmProjects/AI-town`.
- `codegraph index .` indexed 15 files, 188 nodes, and 333 edges.
- Codegraph database was created at `.codegraph/codegraph.db`.
- `codegraph status .` reported the index is up to date.
- `mcp__codegraph.codegraph_status` returned the same 15 files, 188 nodes, and 333 edges.
- `mcp__codegraph.codegraph_files` returned backend Python files and `.idea` XML files.
- `mcp__fast_context.fast_context_search` returned 11 relevant project files, including backend Python modules and Godot `.gd` scripts.

## Notes
- Codegraph currently indexed Python and XML only in this project; it did not index Godot `.gd` scripts.
- Fast-context successfully found Godot scripts such as `scripts/api_client.gd` and `scripts/config.gd`, so use fast-context for Godot-side semantic lookup.
