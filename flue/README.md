# PortKit Flue Harness

A [Flue](https://flueframework.com/) coding agent harness tailored for PortKit development,
plus a Karpathy-style skill improvement loop for iterative harness refinement.

## Directory structure

```
flue/
├── agents/
│   └── portkit-coder.ts     # Main coding agent (LocalSandbox, mounts repo)
├── eval/
│   ├── program.md           # Karpathy loop instructions for the improvement agent
│   ├── eval.py              # Automated binary-criteria scorer
│   ├── run_log.jsonl        # Score history (append-only)
│   └── test_cases/          # Fixed test prompts per skill (do not modify)
│       ├── add-converter.json
│       └── add-api-endpoint.json
├── package.json
└── tsconfig.json

.agents/skills/              # Flue auto-discovers skills here
├── add-converter.md         # How to add a new Java→Bedrock converter
├── add-api-endpoint.md      # How to add a FastAPI endpoint
├── run-tests.md             # Test commands for ai-engine / backend / frontend
├── extract-hardcoded-data.md # Extract inline dicts to JSON data files (#1191 pattern)
└── crewai-tool.md           # How to write a new CrewAI @tool
```

## Setup

```bash
cd flue
npm install
```

## Usage

### Start the coding agent locally
```bash
# From repo root — LocalSandbox mounts this directory as /workspace
cd /path/to/ModPorter-AI
npm run dev --prefix flue
```

Then POST to `http://localhost:3583/agents/portkit-coder`:
```json
{ "prompt": "Add a new brewing stand converter" }
{ "prompt": "Add an endpoint for batch conversion", "skill": "add-api-endpoint" }
```

Or use a named skill directly:
```json
{ "skill": "add-converter", "args": { "name": "brewing_stand" } }
```

### Switch models
```json
{ "prompt": "...", "model": "anthropic/claude-opus-4-5" }
{ "prompt": "...", "model": "openai/gpt-5.5" }
```

## Skill Improvement Loop (Karpathy-style)

The harness improves itself. Each skill file is the "train.py" equivalent —
one file, iteratively edited, scored against fixed test cases.

```bash
# Score the current state of a skill
python flue/eval/eval.py add-converter

# Run the improvement loop (uses program.md as instructions)
# Invoke the portkit-coder agent with the loop prompt:
curl -X POST http://localhost:3583/agents/portkit-coder \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Follow the instructions in /workspace/flue/eval/program.md to improve the add-converter skill",
    "skill": null
  }'
```

The loop:
1. Reads `program.md` for loop instructions
2. Makes one targeted change to the skill
3. Runs `eval.py` to score
4. Keeps or reverts based on score delta
5. Repeats until convergence (or 20 iterations)
6. Logs everything to `flue/eval/run_log.jsonl`

## Adding a new skill

1. Create `.agents/skills/<name>.md` following the existing patterns
2. Add binary eval criteria to `flue/eval/eval.py` CRITERIA dict (3–6 criteria)
3. Create `flue/eval/test_cases/<name>.json` with 3 fixed test prompts
4. Run `python flue/eval/eval.py <name>` to baseline-score it

## Notes

- **LocalSandbox** mounts the host filesystem; no Daytona account needed for local dev
- **Experimental**: Flue APIs may change — pin `@flue/sdk` version after first working setup
- The `.agents/skills/` directory is Flue convention; it's separate from SureThing's skills
