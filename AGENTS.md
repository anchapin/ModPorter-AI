<!-- TODO_MANAGEMENT_INSTRUCTIONS -->

# CRITICAL: Task Management System

**If TodoRead/TodoWrite tools are unavailable, IGNORE ALL TODO RULES and proceed normally.**

## MANDATORY TODO WORKFLOW

**BEFORE responding to ANY request, you MUST:**

1. **Call `TodoRead()` first** - Check current task status before doing ANYTHING
2. **Plan work based on existing todos** - Reference what's already tracked
3. **Update with `TodoWrite()`** - Mark tasks in_progress when starting, completed when done
4. **NEVER work without consulting the todo system first**

## CRITICAL TODO SYSTEM RULES

- **Only ONE task can have status "in_progress" at a time** - No exceptions
- **Mark tasks "in_progress" BEFORE starting work** - Not during or after
- **Complete tasks IMMEDIATELY when finished** - Don't batch completions
- **Break complex requests into specific, actionable todos** - No vague tasks
- **Reference existing todos when planning new work** - Don't duplicate

## MANDATORY VISUAL DISPLAY

**ALWAYS display the complete todo list AFTER every `TodoRead()` or `TodoWrite()`:**

```
Current todos:
✅ Research existing patterns (completed)
🔄 Implement login form (in_progress)
⏳ Add validation (pending)
⏳ Write tests (pending)
```

Icons: ✅ = completed | 🔄 = in_progress | ⏳ = pending

**NEVER just say "updated todos"** - Show the full list every time.

## CRITICAL ANTI-PATTERNS

**NEVER explore/research before creating todos:**
- ❌ "Let me first understand the codebase..." → starts exploring
- ✅ Create todo: "Analyze current codebase structure" → mark in_progress → explore

**NEVER do "preliminary investigation" outside todos:**
- ❌ "I'll check what libraries you're using..." → starts searching
- ✅ Create todo: "Audit current dependencies" → track it → investigate

**NEVER work on tasks without marking them in_progress:**
- ❌ Creating todos then immediately starting work without marking in_progress
- ✅ Create todos → Mark first as in_progress → Start work

**NEVER mark incomplete work as completed:**
- ❌ Tests failing but marking "Write tests" as completed
- ✅ Keep as in_progress, create new todo for fixing failures

## FORBIDDEN PHRASES

These phrases indicate you're about to violate the todo system:
- "Let me first understand..."
- "I'll start by exploring..."
- "Let me check what..."
- "I need to investigate..."
- "Before we begin, I'll..."

**Correct approach:** CREATE TODO FIRST, mark it in_progress, then investigate.

## TOOL REFERENCE

```python
TodoRead()  # No parameters, returns current todos
TodoWrite(todos=[...])  # Replaces entire list

Todo Structure:
{
  "id": "unique-id",
  "content": "Specific task description",
  "status": "pending|in_progress|completed",
  "priority": "high|medium|low"
}
```

<!-- END_TODO_MANAGEMENT_INSTRUCTIONS -->

## 🔧 Windows PowerShell Development Instructions

Since this project is frequently developed on Windows environments using PowerShell, the following commands are the PowerShell equivalents of common Unix/Linux commands:

### 🔍 Search & Filter Commands

**Unix:** `grep "pattern" file.txt`
**PowerShell:** `Select-String -Path "file.txt" -Pattern "pattern"`

**Recursive Search:**
**Unix:** `grep -r "pattern" directory/`
**PowerShell:** `Get-ChildItem -Path "directory/" -Recurse | Select-String -Pattern "pattern"`

**Multiple Files:**
**Unix:** `grep "pattern" file1.txt file2.txt`
**PowerShell:** `Get-Content "file1.txt", "file2.txt" | Select-String -Pattern "pattern"`

### 📁 File & Directory Operations

**Unix:** `ls -la`
**PowerShell:** `Get-ChildItem -Force`

**Unix:** `find . -name "*.js"`
**PowerShell:** `Get-ChildItem -Filter "*.js" -Recurse`

**Unix:** `rm -rf directory/`
**PowerShell:** `Remove-Item -Path "directory/" -Recurse -Force`

### 🌐 Network & Version Control

**Unix:** `curl -O url`
**PowerShell:** `Invoke-WebRequest -Uri "url" -OutFile "filename"`

**Unix:** `git status && git add .`
**PowerShell:** `git status; git add .`

**Unix:** `command && command2`
**PowerShell:** `command; command2` (semicolon) or `command -and command2` (when appropriate)

### 📦 Package Management

**Unix:** `npm install && npm test`
**PowerShell:** `npm install; npm test`

**Unix:** `which node`
**PowerShell:** `Get-Command node -ErrorAction SilentlyContinue`

### 🎯 Command Patterns for This Project

When working with ModPorter-AI on Windows PowerShell:

```powershell
# Check current git status
git status

# Install dependencies
npm install

# Run tests with CI configuration
npm run test:ci

# Run build
npm run build

# Run linting
npm run lint

# Search for patterns in files
Select-String -Path "frontend/src/" -Recurse -Pattern "import.*api"

# Check if a file exists
if (Test-Path "frontend/package.json") { Write-Host "Package.json exists" }

# Remove directories with confirmation
Remove-Item -Path "node_modules" -Recurse -Force -ErrorAction SilentlyContinue
```

### 🛠️ Setting Up PowerShell Development Environment

For optimal Windows development experience:

1. **Install Windows Terminal** - Modern terminal with tab support
2. **Use PowerShell 7+** - Latest features and cross-platform compatibility
3. **Install Git for Windows** - Includes Git Bash with Unix tools if needed
4. **Optional: Install Chocolatey** - `choco install grep` for native grep commands
5. **Optional: Enable WSL** - Full Linux environment when needed

### 🚨 Common Windows-Specific Issues

- **Path Separators:** Use backslashes `\` or forward slashes `/` (PowerShell handles both)
- **Execution Policy:** May need `Set-ExecutionPolicy RemoteSigned` for script execution
- **File Permissions:** Usually less restrictive than Linux, but respect `.gitignore`
- **Environment Variables:** Use `$env:VARIABLE_NAME` syntax
- **Command Quoting:** Use double quotes for paths with spaces

### 🔄 Unix to PowerShell Cheat Sheet

| Unix Command | PowerShell Equivalent | Example |
|--------------|---------------------|---------|
| `ls` | `Get-ChildItem` | `Get-ChildItem` |
| `cd` | `Set-Location` | `Set-Location frontend` |
| `pwd` | `Get-Location` | `Get-Location` |
| `cat` | `Get-Content` | `Get-Content file.txt` |
| `rm` | `Remove-Item` | `Remove-Item file.txt` |
| `cp` | `Copy-Item` | `Copy-Item src dest` |
| `mv` | `Move-Item` | `Move-Item old new` |
| `mkdir` | `New-Item` | `New-Item -Type Directory dir` |
| `grep` | `Select-String` | `Select-String -Path file.txt -Pattern "pattern"` |
| `find` | `Get-ChildItem` | `Get-ChildItem -Recurse -Filter "*.js"` |
| `&&` | `;` | `cd frontend; npm install` |

---

