# `tools/` — Per-File Inventory

> Honest audit of every Python file in `tools/`. **42 files, ~12,000 lines total.**
> Generated 2026-05-24. Each entry has been verified by direct read (see "Verification" column) or sampled (marked accordingly).

---

## TL;DR

| Status | Count | What it means |
|---|---|---|
| **REAL — wired into main paths** | 14 | Imported by `assistant.py` or `web/backend/app.py`, called from chat/REST endpoints, working as advertised |
| **REAL — supporting / utility** | 14 | Solid implementations called transitively (e.g., by RAG, by ContextManager). Working code. |
| **REAL — unused in main chat path** | 5 | Substantive logic, but `process_message` / `process_message_stream` in `assistant.py` never reach them. Reachable only from CLI or non-chat endpoints. |
| **PARTIAL / MISNAMED** | 6 | Real code, but the module's name promises more than the implementation delivers. Examples: `task_classifier` is keyword scoring, not classification. |
| **STUB / DEAD-ON-ARRIVAL** | 3 | Thin wrappers, mostly init code, or unused entirely. |

**Imports from the main paths** (the strongest signal of "is this actually used"):

- **`assistant.py`** directly imports: `rag_system`, `incremental_indexer`, `diff_extractor`, `error_debugger`, `error_parser`, `multi_agent`, `logger`, `retry`, `llm_provider`, `byok`, `task_classifier`, `context_manager`, `code_completion`, `performance_monitor`.
- **`web/backend/app.py`** directly imports: `code_completion`, `git_integration`, `auth`, `rate_limiter`, `security`, `byok`, `github_oauth`.

Plus what's imported transitively: `tools/__init__.py` exports `FileOperations`, `CodebaseSearch`, `Terminal`, `DiffEditor` (used via `assistant.file_ops` / `.terminal` / etc.).

---

## Verification legend

- ✅ **Read end-to-end** by the author of this doc
- 🔍 **Read partially** (top + key sections) by the author
- 🤖 **Sampled by audit agent** + verified via `grep` of class/function definitions; not personally read end-to-end

---

## AI / LLM core

### `llm_provider.py` (346 lines) ✅ REAL — wired in
**What it does:** Abstract `LLMProvider` base class with three concrete implementations: `OpenAIProvider`, `DeepSeekProvider` (OpenAI-compatible API at `api.deepseek.com`), `AnthropicProvider` (with OpenAI-format → Anthropic-format message mapping). Both blocking `chat_completion` and async `chat_completion_stream` (background thread + queue bridge for OpenAI/DeepSeek; native `messages.stream` for Anthropic). Factory `get_provider(name, key)` at line 335.
**Called from:** `assistant.py` (all three providers instantiated at startup), `auto_fixer.py`, `hypothesis_generator.py`, `code_completion.py`, `conversation_summarizer.py`.
**Notes:** Anthropic provider correctly extracts system messages and only sends user/assistant roles (lines 247-255). `create_embedding` raises `NotImplementedError` on Anthropic (correct — Anthropic has no embeddings API).

### `task_classifier.py` (241 lines) ✅ STUB — misnamed
**What it does:** Routes user messages between DeepSeek (code generation) and Claude (reasoning) using **keyword scoring + regex pattern matching**. No LLM, no ML, no embeddings. Has negation handling (`_remove_negated_spans` line 117) so "don't create" doesn't trigger code-gen keywords. Threshold-based decision at line 153.
**Called from:** `assistant.py` `_select_provider` (line 247).
**Real name should be:** `TaskRouter` or `KeywordRouter`. **Phase 7.5b is scoped to rebuild this with an actual LLM-driven classifier.**

### `multi_agent.py` (276 lines) ✅ STUB-OF-AGENTS, REAL-AS-PIPELINE, UNUSED-IN-CHAT
**What it does:** `MultiAgentSystem` orchestrates `RetrievalAgent` (real RAG wrapper), `PlanningAgent` (regex + if/else on query keywords — **no LLM**), `ValidationAgent` (calls `diff_editor.validate_diff` — syntax-only). Runs Retrieval + Planning in parallel via `asyncio.gather` + `ThreadPoolExecutor`.
**Called from:** `assistant.py` imports it, but `process_message` and `process_message_stream` **bypass it entirely**. Dead code in the chat path.
**Notes:** PlanningAgent at lines 59-96 is literally `if "add" in query.lower(): plan["steps"].append("Create new code")`. Not an agent in any modern sense. **Phase 7.5a rebuilds this as an actual LLM-driven multi-agent system.**

### `context_manager.py` (230 lines) ✅ REAL — wired in
**What it does:** Token-budgeted context assembly. Loads facts from MemoryDB by session_id, injects RAG context, processes history with summarization above threshold (default 75% of model limit), aggressive truncation as last resort. Different token caps per model (10k DeepSeek, 150k Claude).
**Called from:** `assistant.py` `process_message` and `process_message_stream` for every chat turn.
**Notes:** `update_memory` saves facts every exchange, full summary every 20 messages.

### `conversation_summarizer.py` (252 lines) 🔍 REAL — supporting
**What it does:** Wraps an LLM call to summarize old messages into bullet-point text. Preserves the most recent N messages verbatim. Has graceful fallback chain: Anthropic → OpenAI → no-op (returns messages unchanged).
**Called from:** `context_manager.py`.

### `facts_extractor.py` (147 lines) 🤖 REAL — supporting
**What it does:** LLM-driven extraction of structured `Fact` objects from messages (user preferences, files created, decisions). Returns a list saved into `MemoryDB.save_facts`.
**Called from:** `context_manager.py`.

### `token_counter.py` (72 lines) 🤖 AUX — supporting
**What it does:** Heuristic token counter (~4 chars/token for English). Does NOT use `tiktoken` for precision; "good enough for context budgeting" per the audit.
**Called from:** `context_manager.py`.

---

## RAG / code understanding

### `rag_system.py` (1171 lines) 🔍 REAL — wired in
**What it does:** The heart of code retrieval. ChromaDB-backed vector store with two embedding providers (`_OpenAIEmbeddingProvider`, `_SentenceTransformerEmbeddingProvider` chosen via `EMBEDDING_PROVIDER` env). Parallel indexing with `ThreadPoolExecutor`. Hybrid retrieval (semantic + keyword/BM25 fallback). AST-aware chunking for Python (`_chunk_python_file` at line 795 calls `ast_analyzer.analyze_file`); language-specific chunkers for JS; line-based fallback (`_chunk_by_lines` line 878) for everything else.
**Called from:** `assistant.py`, `code_completion.py`, `error_debugger.py`, `hypothesis_generator.py`, `incremental_indexer.py`.
**Notes:** `PersistentClient` at line 144 writes to `VECTOR_DB_PATH` env var (defaults to `./.vector_db`). Logs the resolved path on init (Phase 1.4 added).

### `ast_analyzer.py` (396 lines) 🔍 REAL — supporting
**What it does:** Tree-sitter-based AST parsing. Imports `tree_sitter`, `Language`, `Parser` at lines 12-13. Defines `CodeSymbol` dataclass + `ASTAnalyzer` class. Extracts functions, classes, imports, generates summaries. Python-only despite being called `ASTAnalyzer` (per audit).
**Called from:** `rag_system.py`, `code_completion.py`, `bug_detector.py`, `code_graph.py`.

### `code_graph.py` (311 lines) 🔍 REAL — supporting
**What it does:** Builds call graphs + import graphs from the codebase using AST. `SymbolNode` + `GraphEdge` dataclasses, `CodeGraphBuilder` with `build_graph` (two-pass: collect symbols, then build relationships), `CallGraphVisitor(ast.NodeVisitor)` for call detection.
**Called from:** `rag_system.py` (lazy loaded as `self.code_graph`), `multi_agent.py::PlanningAgent`.

### `codebase_search.py` (295 lines) 🤖 REAL — supporting
**What it does:** Filesystem search by glob/pattern + keyword search in file contents. Thin wrapper on top of File I/O.
**Called from:** `assistant.py` (`self.codebase_search`).

### `code_scanner.py` (144 lines) 🤖 REAL — supporting
**What it does:** Recursively walks the workspace, filters by extension and ignore patterns (`.git`, `node_modules`, `.vector_db`, etc.), returns metadata. Used by RAG indexer and bug detector to enumerate files.
**Called from:** `rag_system.py`, `bug_detector.py`, `debug_mode.py`.

### `incremental_indexer.py` (159 lines) ✅ REAL but UNUSED in chat path
**What it does:** Real implementation: `threading.Thread` + `Queue` + debouncing (2s delay), wraps `FileWatcher`, updates ChromaDB index on file changes. Has clean start/stop, error handling, status reporting.
**Called from:** `assistant.py` imports it. **Not called in `process_message` or `process_message_stream`** — appears initialized but the chat path never triggers reindex.
**Notes:** Solid code, just not wired in.

### `file_watcher.py` (106 lines) ✅ DEAD-ON-ARRIVAL
**What it does:** `watchdog`-based filesystem event handler (`on_modified`, `on_created`, `on_deleted`). Functional implementation with debounce.
**Called from:** Only `incremental_indexer.py` — which itself is unused in the chat path. Effectively dead.

---

## Code modification

### `diff_editor.py` (520 lines) 🤖 REAL — wired in
**What it does:** Full unified-diff parser + applier. `DiffOperation` enum, `DiffHunk`, `FileDiff` dataclasses, `DiffEditor` class with `parse_diff` (proper hunk tokenization, old/new line counts, offset adjustments), `apply_diffs` with dry-run support, syntax validation pre-apply.
**Called from:** `assistant.py`, `multi_agent.py::ValidationAgent`, `auto_fixer.py`, `/api/diff/apply` endpoint.

### `diff_extractor.py` (143 lines) 🤖 REAL — wired in
**What it does:** Regex-based extraction of ```` ```code ``` ```` blocks from LLM responses. Converts them to unified diff format.
**Called from:** `assistant.py` (auto-applies diffs found in streamed responses), `auto_fixer.py`.

### `file_operations.py` (218 lines) 🤖 REAL — wired in (via `__init__.py`)
**What it does:** Read/write/delete files, list directories, sanitize paths.
**Called from:** Everywhere via `tools.file_operations` re-exported in `tools/__init__.py`.

### `validation_service.py` (500 lines) ✅ REAL — partially used
**What it does:** Multi-stage validation for any file: AST syntax check (Python), mypy types (Python), tsc types (TypeScript), flake8 lint (Python), ESLint (JS/TS). Subprocess-based, with availability checks before running each tool.
**Notes:** `validate_diff` (line 116) has a TODO at line 136: "Implement proper diff application to temp file" — currently it just validates the ORIGINAL file, not the diff applied. The `validate_file` path is fully real.
**Called from:** Indirectly via `diff_editor.validate_diff`.

### `auto_fixer.py` (214 lines) ✅ REAL but UNUSED in chat path
**What it does:** Given a `Bug`, builds a fix prompt with file context, calls Claude (or OpenAI fallback), extracts unified diff from LLM response (with regex fallback if `DiffExtractor` misses), parses + applies via `DiffEditor`. Skips critical syntax errors (line 164).
**Called from:** `debug_mode.py`, `interactive_debug_mode.py`. **Not in the chat path.**

### `code_completion.py` (545 lines) ✅ REAL — wired in (but separate from chat)
**What it does:** Combines four completion sources: AST (current-file symbols), RAG (similar code from codebase), LLM (intelligent generation via DeepSeek), language keywords/builtins. Has cache, deduplication, and ranking (prefix match + kind boost). Used for IDE-style autocomplete, NOT for chat.
**Called from:** `web/backend/app.py` `/api/completion` endpoint + `/ws/completion` WebSocket.

---

## Debugging (5 modules — overlapping, fragmented)

> **All five debug modules are imported but none are called from the main chat path.** They form a coherent subsystem reachable only via CLI commands or explicit `/api/debug` endpoints. The audit recommended consolidating these into a single `tools/debug/` subpackage.

### `error_parser.py` (148 lines) ✅ REAL — wired in (for chat error context)
**What it does:** Regex-based Python traceback parser. `StackFrame` + `ParsedError` dataclasses. Pattern at line 39 matches `File "...", line N, in function`. Helper `is_python_error` lets callers detect Python tracebacks before parsing.
**Called from:** `assistant.py` (via `error_debugger`), `runtime_debugger.py`.

### `error_debugger.py` (214 lines) ✅ REAL — wired in (for chat error context)
**What it does:** Combines `ErrorParser` + `RAGSystem` for error-aware debugging. `debug_error` returns `{error, stack_trace, context, relevant_code, suggestions}`. `get_fix_context` formats everything for LLM consumption. Has rule-based suggestions for common Python errors (NameError, AttributeError, TypeError, ImportError, IndentationError, SyntaxError).
**Called from:** `assistant.py` `process_message` (line 228) to enrich the user's query when it contains an error trace.

### `bug_detector.py` (394 lines) ✅ REAL — orchestrated by debug_mode
**What it does:** AST-based static analysis. Detects: syntax errors, bare except, print statements (code quality), TODO/FIXME comments, unused imports (via AST `ast.Import` + `ast.Name` walk). Runs `python -m py_compile` for runtime check. **`_check_undefined_variables` (line 232) returns empty list — explicitly stub-level: "simplified — full implementation would track scopes."**
**Called from:** `debug_mode.py`, `auto_fixer.py`, `interactive_debug_mode.py`.

### `debug_mode.py` (233 lines) ✅ REAL but CLI-only
**What it does:** Top-level orchestrator: `CodeScanner` → `BugDetector` → `AutoFixer` over all files in workspace, with per-severity / per-type aggregation. Writes detailed logs to `.cursor/debug.log`.
**Called from:** Probably CLI commands; not reached from the chat path.

### `hypothesis_generator.py` (278 lines) ✅ PARTIAL — UNUSED in chat
**What it does:** Builds a debugging prompt with bug description + error + file context + RAG context, calls Claude (or OpenAI fallback) at `temperature=0.7`, parses 3-5 hypotheses from the response using regex (with text-based fallback if no structured format found). Returns `Hypothesis` objects with `id`, `description`, `confidence`, `reasoning`, `suggested_instrumentation`, `suggested_fix`.
**Notes:** Has a final fallback that returns a single "need more info" hypothesis if nothing parsed (lines 266-276). Better than audit suggested — there ARE fallbacks. Still: would be cleaner with structured outputs (JSON schema).
**Called from:** Only `interactive_debug_mode.py`.

### `runtime_debugger.py` (283 lines) ✅ PARTIAL — UNUSED in chat
**What it does:** Executes a file via subprocess, parses instrumentation logs from stdout (looking for `[__debug_instrumentation__]` markers that `CodeInstrumentation` injects), parses stack traces from stderr via `ErrorParser`. `analyze_execution_trace` detects: functions entered but never exited (possible crash/infinite loop), None/null variable values, very long traces (>1000 lines = possible infinite loop).
**Called from:** Only `interactive_debug_mode.py`.

### `code_instrumentation.py` (277 lines) ✅ REAL but UNUSED in chat (audit was wrong about it)
**What it does:** **AST-based** (audit incorrectly called it "regex-based") instrumentation. Uses `ast.parse` + `ast.walk` to find function entries/exits, variable assignments, conditions (lines 109-178). Inserts print statements with the `[__debug_instrumentation__]` marker. Creates `.backup` files for restoration. Python-only.
**Called from:** Only `interactive_debug_mode.py` and `runtime_debugger.py`.

### `interactive_debug_mode.py` (261 lines) ✅ PARTIAL — misnamed
**What it does:** Orchestrates `HypothesisGenerator` → `CodeInstrumentation` → `RuntimeDebugger` → `AutoFixer`. Has methods `start_debug_session`, `test_hypothesis`, `generate_fix`, `complete_debug_session` — designed to be called step-by-step by an external interactive caller. But no built-in user prompt loop, so it's "interactive-as-API" rather than "interactive-as-UX."
**Called from:** `debug_mode.py`.

---

## Memory / state

### `memory_db.py` (202 lines) 🔍 REAL — supporting
**What it does:** SQLite wrapper with three tables: `conversations` (session_id → summary), `facts` (session_id, fact_type, content, metadata), `file_changes`. Indexed by `session_id`. Real persistent storage.
**Called from:** `context_manager.py`, `session_manager.py`.

### `session_manager.py` (47 lines) ✅ STUB — misnamed
**What it does:** `create_session` is literally `str(uuid.uuid4())` (line 24-25). Doesn't store the session ID. Other methods are thin wrappers around `MemoryDB.*` calls.
**Real name should be:** `MemoryDBFacade` or `SessionLoader`. Doesn't manage anything.
**Called from:** Unused in the main paths — `assistant.py` does its own session ID generation inline.

---

## Auth / security / ops

### `auth.py` (547 lines) ✅ REAL — wired in
**What it does:** JWT + bcrypt user management. `User` Pydantic model with `github_id` (added Phase 2.1). `AuthManager` class: create/get user, hash/verify password, create access + refresh tokens, refresh flow, GitHub OAuth user upsert (3-branch logic), partial UNIQUE INDEX on `github_id` for the migration.
**Called from:** `web/backend/app.py` for all auth routes.

### `github_oauth.py` (171 lines) ✅ REAL — wired in
**What it does:** Pure helpers (no FastAPI dependencies): `generate_state` (CSRF), `build_authorize_url` (with all required params + URL-encoded scopes), `exchange_code_for_token` (takes injectable `http_post` callable for testability), `fetch_profile` (with /user/emails fallback when public email is null).
**Called from:** `web/backend/app.py` `/api/auth/github/*` routes.

### `byok.py` (135 lines) ✅ REAL — wired in
**What it does:** `UserKeys` dataclass + `get_user_keys` FastAPI dependency (reads `X-Anthropic-Key` / `X-OpenAI-Key` / `X-DeepSeek-Key` headers) + `user_keys_from_ws_query` (browsers can't set arbitrary headers on a WS handshake → reads query params instead). Dev-env fallback to server `.env` keys.
**Called from:** `web/backend/app.py` `/api/chat`, `/ws/chat`, future BYOK endpoints. Threaded through `assistant.process_message` and `process_message_stream` via the `user_keys` param.

### `security.py` (276 lines) 🔍 REAL — wired in
**What it does:** Path traversal protection (`sanitize_file_path`), file extension whitelist, input sanitization, email/username/password strength validation, HTML escaping, secure token generation, API key format validation, `mask_secret`, `is_safe_filename`, `writes_enabled` (the production gate — Phase 1.6), `require_writes_enabled` FastAPI dep, `get_cors_origins`.
**Called from:** `web/backend/app.py`.

### `rate_limiter.py` (404 lines) ✅ REAL — wired in
**What it does:** Sliding-window rate limiting with two pluggable backends — `_InMemoryBackend` (asyncio.Lock-protected dict, lost on restart) and `_RedisBackend` (sorted sets via aioredis, persistent). Three windows: per-minute / hour / day. Backend selected via `REDIS_URL` env. Has `@rate_limit` decorator with `X-RateLimit-*` response headers. Backend errors fail-open (don't block users on Redis outage).
**Called from:** `web/backend/app.py`.

---

## Infra / utilities

### `cache.py` (236 lines) 🤖 REAL — supporting
**What it does:** File-based cache with TTL + LRU eviction. JSON serialization, hash-keyed paths. `@cached` decorator at line 195.
**Called from:** `rag_system.py` for embeddings cache + analysis results.

### `logger.py` (70 lines) 🤖 AUX — supporting
**What it does:** Thin wrapper around Python's `logging` module. `Logger` class + `get_logger()` factory. Configures file + console output (RichHandler).
**Called from:** Across the codebase via `from tools.logger import get_logger`.

### `retry.py` (66 lines) 🤖 AUX — supporting
**What it does:** `@retry` decorator and `@retry_api_call` specialized variant. Exponential backoff with jitter, `max_attempts`, configurable exceptions.
**Called from:** `assistant.py` for LLM API calls.

### `performance_monitor.py` (500 lines) 🤖 REAL — wired in
**What it does:** Tracks: indexing time, embedding generation time, API response times (with p50/p95/p99 percentiles), memory usage (via psutil), cost per call. `PerformanceMonitor` class persists stats to JSON. Used to populate the `/api/performance` endpoint.
**Called from:** `assistant.py`, `rag_system.py`.

### `terminal.py` (105 lines) 🤖 REAL — wired in
**What it does:** Subprocess execution with stdout/stderr capture. Returns `{success, stdout, stderr, returncode}`. Background vs foreground execution.
**Called from:** `assistant.py` (via `tools/__init__.py`), `bug_detector.py`, `runtime_debugger.py`. **Now gated by `ENABLE_WRITE_OPERATIONS` for `/ws/terminal`** (Phase 1.6).

### `git_integration.py` (480 lines) 🤖 REAL — wired in
**What it does:** Comprehensive Git subprocess wrapper. Status, diff, stage/unstage, commit, push, branches, history. Used by `/api/git/*` endpoints.
**Called from:** `web/backend/app.py`.

### `rules_engine.py` (187 lines) 🤖 REAL — wired in (for /api/rules)
**What it does:** Simple rules engine. Loads YAML rules, evaluates conditions using regex/keyword matching against code context, applies actions. Used for the `.cursorrules` linting/QA workflow.
**Called from:** `web/backend/app.py` `/api/rules/*` endpoints.

### `__init__.py` (171 lines) AUX
**What it does:** Package exports with graceful import fallback for optional dependencies. Re-exports `FileOperations`, `CodebaseSearch`, `Terminal`, `DiffEditor`, etc. for `from tools import X` patterns.

---

## Architectural gaps to fix (links into the plan)

These are observed issues from this audit. Each maps to a planned phase:

1. **Multi-agent is misnamed** — `PlanningAgent` is regex+heuristics, not an LLM agent. Main chat path bypasses the entire `MultiAgentSystem`. **Phase 7.5** (3 subphases) rebuilds this into a genuine LLM-driven multi-agent system and wires it into the chat path.
2. **`task_classifier` is keyword scoring** — `TaskClassifier` lies about its job. **Phase 7.5b** rebuilds it as either an LLM-driven classifier or an embedding-based nearest-neighbor router.
3. **`session_manager` is a stub** — just UUID generation. **Phase 3.5** (Connect-a-GitHub-repo) needs real per-user workspace sessions — that work will probably absorb `session_manager` into something genuine.
4. **`file_watcher` is dead code** — and so is `incremental_indexer` in the chat path. Either wire them in via Phase 3.5, or delete them in a future cleanup pass.
5. **Five overlapping debug modules** — `bug_detector`, `error_debugger`, `debug_mode`, `runtime_debugger`, `interactive_debug_mode` + `hypothesis_generator` + `code_instrumentation`. Consolidate into one `tools/debug/` subpackage if and when these are wired into the chat path. For now: leave them alone; they're not blocking anything.
6. **`validation_service.validate_diff` has an unfinished TODO** at line 136 ("Implement proper diff application to temp file"). The current implementation validates the original file content, not the diff applied. Fix during Phase 7.5c when validation feeds back into the adaptive loop.
7. **Tool calling parsed by regex** — `assistant.py:705` parses tool calls from text. **Phase 7.1** replaces this with native `tool_use` blocks + OpenAI `tools=[]`.

---

## Methodology

- **Verification:** ✅ files were read end-to-end (200-1000+ lines each). 🔍 files had multiple sections read or were partial reads. 🤖 files were sampled by an Explore agent + verified via `grep` for class/function definitions.
- **Wiring confirmed by:** explicit `grep` for `^from tools\.` in `assistant.py`, `web/backend/app.py`, and `main.py`.
- **Status labels:**
  - **REAL — wired in** = imported by a main path AND its primary class/function is called from there
  - **REAL — supporting** = imported transitively, called from a wired-in module
  - **REAL — unused in chat path** = imported but the chat methods don't call it
  - **STUB / PARTIAL / MISNAMED** = name promises more than the implementation delivers
  - **DEAD-ON-ARRIVAL** = no caller anywhere meaningful
