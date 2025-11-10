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

