<!-- TODO_MANAGEMENT_INSTRUCTIONS -->

# CRITICAL: Task Management System

**Using markdown file in .factory directory for task tracking instead of MCP task-manager tools.**

## MANDATORY TODO WORKFLOW

**BEFORE responding to ANY request, you MUST:**

1. **Read `.factory/tasks.md` first** - Check current task status before doing ANYTHING
2. **Plan work based on existing tasks** - Reference what's already tracked
3. **Update `.factory/tasks.md`** - Mark tasks in_progress when starting, completed when done
4. **NEVER work without consulting the task file first**

## CRITICAL TODO SYSTEM RULES

- **Only ONE task can have status "In Progress" at a time** - No exceptions
- **Mark tasks "In Progress" BEFORE starting work** - Not during or after
- **Complete tasks IMMEDIATELY when finished** - Don't batch completions
- **Break complex requests into specific, actionable tasks** - No vague tasks
- **Reference existing tasks when planning new work** - Don't duplicate

## MANDATORY VISUAL DISPLAY

**ALWAYS display the complete task list from `.factory/tasks.md` AFTER reading or updating:**

```
# Current Tasks

## In Progress
- 🔄 Implement login form

## Pending
- ⏳ Add validation
- ⏳ Write tests

## Completed
- ✅ Research existing patterns
```

Icons: ✅ = completed | 🔄 = in progress | ⏳ = pending

**NEVER just say "updated tasks"** - Show the full list every time.

## CRITICAL ANTI-PATTERNS

**NEVER explore/research before creating tasks:**
- ❌ "Let me first understand the codebase..." → starts exploring
- ✅ Create task: "Analyze current codebase structure" → mark in_progress → explore

**NEVER do "preliminary investigation" outside tasks:**
- ❌ "I'll check what libraries you're using..." → starts searching
- ✅ Create task: "Audit current dependencies" → track it → investigate

**NEVER work on tasks without marking them in_progress:**
- ❌ Creating tasks then immediately starting work without marking in_progress
- ✅ Create tasks → Mark first as in_progress → Start work

**NEVER mark incomplete work as completed:**
- ❌ Tests failing but marking "Write tests" as completed
- ✅ Keep as in_progress, create new task for fixing failures

## FORBIDDEN PHRASES

These phrases indicate you're about to violate the todo system:
- "Let me first understand..."
- "I'll start by exploring..."
- "Let me check what..."
- "I need to investigate..."
- "Before we begin, I'll..."

**Correct approach:** CREATE TASK FIRST, mark it in_progress, then investigate.

## TASK FILE REFERENCE

```markdown
# Current Tasks

## In Progress
- 🔄 Task name

## Pending  
- ⏳ Task name
- ⏳ Another task

## Completed
- ✅ Completed task
```

<!-- END_TODO_MANAGEMENT_INSTRUCTIONS -->

---

# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any shell command containing `curl` or `wget` will be intercepted and blocked by the context-mode plugin. Do NOT retry.
Instead use:
- `context-mode_ctx_fetch_and_index(url, source)` to fetch and index web pages
- `context-mode_ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any shell command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` will be intercepted and blocked. Do NOT retry with shell.
Instead use:
- `context-mode_ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### Direct web fetching — BLOCKED
Do NOT use any direct URL fetching tool. Use the sandbox equivalent.
Instead use:
- `context-mode_ctx_fetch_and_index(url, source)` then `context-mode_ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Shell (>20 lines output)
Shell is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `context-mode_ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `context-mode_ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### File reading (for analysis)
If you are reading a file to **edit** it → reading is correct (edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `context-mode_ctx_execute_file(path, language, code)` instead. Only your printed summary enters context.

### grep / search (large results)
Search results can flood context. Use `context-mode_ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `context-mode_ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `context-mode_ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `context-mode_ctx_execute(language, code)` | `context-mode_ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `context-mode_ctx_fetch_and_index(url, source)` then `context-mode_ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `context-mode_ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `upgrade` MCP tool, run the returned shell command, display as checklist |
