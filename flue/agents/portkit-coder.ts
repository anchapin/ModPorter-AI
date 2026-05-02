import type { FlueContext } from '@flue/sdk/client';

// Run locally: npx @flue/cli dev flue/agents/portkit-coder.ts
// Or via webhook: POST /agents/portkit-coder/:id { prompt, skill?, args?, model? }
export const triggers = { webhook: true };

export default async function ({ init, payload }: FlueContext) {
  const agent = await init({
    // LocalSandbox: mounts host filesystem; run `flue dev` from the PortKit repo root
    // so your live checkout is accessible at /workspace
    sandbox: 'local',
    model: (payload.model as string) ?? 'anthropic/claude-opus-4-5',
  });

  const session = await agent.session({
    system: `You are a senior developer working on PortKit — a tool that converts
Minecraft Java Edition mods to Bedrock Edition addons.

## Read First (always before making changes)
- /workspace/CLAUDE.md           — AI coding directives and conventions
- /workspace/ARCHITECTURE.md     — full system architecture
- /workspace/.cursorrules        — code style rules
- /workspace/ai-engine/SKELETON.md        — ai-engine module map (index)
- /workspace/ai-engine/SKELETON-agents.md — CrewAI agent definitions
- /workspace/ai-engine/SKELETON-converters.md — converter implementations
- /workspace/ai-engine/SKELETON-pipeline.md   — conversion pipeline
- /workspace/backend/SKELETON.md  — backend module map
- /workspace/frontend/SKELETON.md — frontend module map

## Stack
- ai-engine : Python · CrewAI · Celery · tree-sitter (Java parsing) · FastAPI
- backend   : Python · FastAPI · PostgreSQL · Redis
- frontend  : TypeScript · React

## Hard Rules
1. Read CLAUDE.md before touching any file.
2. Never modify: rag_pipeline.py · knowledge/patterns/mappings.py · orchestrator strategy selector.
3. All new converters → ai-engine/converters/ using @tool decorator from crewai.tools.
4. Register new converters in the enclosing __init__.py.
5. Add a pytest test file alongside every new converter.
6. New backend endpoints → backend/routes/ using FastAPI APIRouter + Pydantic models.
7. Large data dicts (>10 entries) belong in ai-engine/data/*.json, not inline code.`,
  });

  // If a named skill is requested, invoke it; otherwise free-form prompt
  if (payload.skill) {
    return await session.skill(payload.skill as string, {
      args: (payload.args as Record<string, unknown>) ?? {},
    });
  }

  return await session.prompt(payload.prompt as string);
}
