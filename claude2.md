# claude2.md — Gap-Closing Plan After Core Backend Completion

## Current Status Validation

Yes — the assessment is correct.

Completed:
- Database schema and migrations
- Module ingestion pipeline
- RAG retrieval (vector + full-text)
- Agent router and handler framework
- REST API endpoints
- Example module package

Remaining critical work:
1. LLM integration for natural language generation
2. Real runtime environment with PostgreSQL (+ pgvector)
3. Frontend interface for DM/player interaction

This document defines how to implement the remaining parts in a production-ready, incremental way.

---

## 1) Priority Order (strict)

1. **LLM Integration** (must-have for usable agent responses)
2. **Runtime Environment** (must-have for stable deployment/testing)
3. **Frontend MVP** (must-have for real user operation)

---

## 2) LLM Integration Plan

## 2.1 Objectives
- Let existing agents produce grounded natural-language outputs.
- Support at least two providers (OpenAI + Anthropic) behind one interface.
- Preserve citations and enforce anti-hallucination response policy.

## 2.2 Provider Abstraction (required)

Create a provider-agnostic interface:

- `LLMProvider` interface:
  - `generate(messages, system_prompt, tools?, response_format?) -> LLMResult`
- Implementations:
  - `OpenAIProvider`
  - `AnthropicProvider`
- Factory:
  - `LLMProviderFactory.from_env()`

Environment variables:
- `LLM_PROVIDER=openai|anthropic`
- `OPENAI_API_KEY=...`
- `ANTHROPIC_API_KEY=...`
- `LLM_MODEL=...`
- `LLM_TEMPERATURE=0.2`
- `LLM_MAX_TOKENS=1200`

## 2.3 Prompt Contract (required)

Use a structured system prompt with hard constraints:

1. Must answer using retrieved evidence.
2. Must include uncertainty if evidence is weak/conflicting.
3. Must not fabricate rule text.
4. Must separate:
   - Conclusion
   - Evidence summary
   - DM adjudication note

## 2.4 Query Pipeline Integration

Update `/query` flow:

1. Intent routing (existing)
2. Retrieval (existing)
3. Build `context_bundle` from top evidence
4. Call selected agent handler to create task prompt
5. Invoke `LLMProvider.generate(...)`
6. Post-process output into stable response schema
7. Persist turn + trace

## 2.5 Output Schema Enforcement

Always return:

```json
{
  "answer": "string",
  "used_agent": "rules|narrative|state|encounter",
  "confidence": 0.0,
  "citations": [],
  "state_updates": [],
  "needs_clarification": false,
  "clarification_question": ""
}
```

If the model response is malformed:
- fallback to safe template output
- include a warning in logs
- never drop citations

## 2.6 Acceptance Criteria

- `/query` returns coherent natural language answer.
- Citations are always present when retrieval returns evidence.
- Provider can switch via env var only (no code change).
- At least 20 integration tests pass for provider-agnostic behavior.

---

## 3) Runtime Environment Plan

## 3.1 Docker Compose Baseline

Add `docker-compose.yml` with services:
- `api`
- `postgres` (with pgvector extension)
- `redis` (if queue/cache used)
- optional `worker` for async ingestion

Postgres requirements:
- Enable `vector` extension on startup
- Health checks
- Persistent volume

## 3.2 Config & Startup

- `.env.example` with all required keys
- startup script:
  1. wait for db
  2. run migrations
  3. start API server
- optional:
  - seed script for sample module/campaign

## 3.3 Operational Baseline

Implement:
- `/health/live`
- `/health/ready`
- structured logs with trace IDs
- graceful shutdown hooks

## 3.4 Acceptance Criteria

- `docker compose up` boots full stack successfully.
- Migrations auto-apply.
- Ingestion + query works end-to-end in local runtime.
- Restart preserves DB data and indexes.

---

## 4) Frontend MVP Plan

## 4.1 Scope (MVP only)

Build lightweight web UI for DM + players:

1. Campaign selector
2. Session chat panel
3. Citation side panel
4. Basic world state panel
5. Module management page (list enabled modules)

Suggested stack:
- Next.js + TypeScript
- Tailwind (optional)
- SSE/WebSocket optional; start with standard request/response

## 4.2 Core Screens

1. **Campaign Dashboard**
   - campaign list
   - create campaign
   - enable module

2. **Session View**
   - message history
   - input box
   - agent tag (rules/narrative/state/encounter)
   - citation cards

3. **State View**
   - key-value world state
   - recent session events timeline

## 4.3 API Integration Rules

- Use existing REST endpoints first; do not redesign backend contract unless required.
- Show citations exactly as returned.
- If backend returns `needs_clarification=true`, render clarification prompt UI.

## 4.4 Acceptance Criteria

- DM can create/select campaign and send messages.
- Users can see answer + citations per turn.
- Session reload restores history.
- Basic errors are user-visible and actionable.

---

## 5) Suggested 3-Week Execution Plan

## Week 1 — LLM integration
- Implement provider abstraction + OpenAI/Anthropic adapters
- Integrate into `/query`
- Add prompt templates and output guards
- Add integration tests

## Week 2 — Runtime hardening
- Add docker-compose stack
- Health checks + migrations + seed flow
- End-to-end local verification scripts

## Week 3 — Frontend MVP
- Build campaign/session/state pages
- Wire citations and clarification flow
- UX polish + basic auth stub (if needed)

---

## 6) Risks & Mitigations

1. **Hallucinated rule text**
   - Mitigation: strict prompt contract + citation-required policy + low temperature

2. **Provider output format drift**
   - Mitigation: schema validator + fallback formatter

3. **Retrieval mismatch in multi-campaign**
   - Mitigation: enforce campaign/module filter at query layer; add isolation tests

4. **Local env instability**
   - Mitigation: compose health checks + startup ordering + retry logic

---

## 7) Definition of Done (Updated)

Done when all are true:

1. Agents generate natural language via configurable LLM provider.
2. Full local runtime works via docker compose with PostgreSQL+pgvector.
3. Frontend MVP supports DM/player interaction with citations visible.
4. Multi-campaign isolation remains correct after LLM/front-end integration.
5. CI includes integration tests for retrieval + generation + API response schema.

---

## 8) Immediate Next PR (recommended)

Create one focused PR titled:

**"Integrate provider-agnostic LLM generation into /query with citation-safe output"**

Include:
- LLM provider interface + 2 implementations
- env-driven provider factory
- `/query` generation integration
- schema validator + fallback formatter
- tests for success/failure/provider switch

Keep frontend and runtime compose changes in separate PRs for review clarity.