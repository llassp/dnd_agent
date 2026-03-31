# CLAUDE.md — DnD RAG Campaign Agent

> **Reading order for Claude Code**: Read this file fully before writing any code. When uncertain about a decision, re-read the relevant section rather than inferring. This document is the source of truth.

---

## 1. Mission

Build a production-oriented DnD GM assistant platform powered by RAG, supporting:

- Multi-campaign isolation (no cross-contamination)
- Pluggable, versioned campaign modules
- Rule-grounded answers with mandatory citations
- Stateful narrative progression across sessions
- Extensible agent/tool architecture

**Core invariant**: Never fabricate rule citations. If evidence confidence is low, say so and ask a clarifying question.

---

## 2. Goals & Non-Goals

### MVP Goals
1. Answer DnD rules/lore questions with citations to source chunks.
2. Support multiple campaigns with hard data isolation.
3. Ingest modules (official/homebrew) with versioning and ingestion reports.
4. Persist world state and session events across queries.
5. Expose a stable JSON API suitable for future Discord/VTT integration.

### Non-Goals (MVP)
- Full tactical battle simulator
- Real-time voice pipeline
- 3D map rendering
- Redistribution of copyrighted SRD content verbatim

---

## 3. Tech Stack

Use this stack unless the repository already defines one — if it does, follow existing conventions.

| Layer | Choice |
|---|---|
| Runtime | Python 3.11 |
| Web framework | FastAPI |
| Database | PostgreSQL 15+ with `pgvector` extension |
| Vector search | `pgvector` (IVFFlat index) |
| Lexical search | PostgreSQL FTS (`tsvector` / `GIN`) |
| Reranker | Cross-encoder, provider-configurable (stub-ready at MVP) |
| Job queue | Celery + Redis |
| Observability | OpenTelemetry + structured JSON logs |
| Workflow orchestration | LangGraph or custom deterministic pipeline |
| Package manager | `uv` (preferred) or `poetry` |
| Testing | `pytest` |
| Lint/format | `ruff` + `black` |

---

## 4. Architecture

```
┌─────────────────────────────────────────┐
│              API Layer (FastAPI)         │
│  /campaigns  /modules  /query  /state   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│          Orchestration Layer             │
│  Router → intent classification          │
│  Dispatches to: Rules / Narrative /      │
│               State / Encounter agent    │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│              RAG Layer                   │
│  Query rewrite → Hybrid retrieval        │
│  → Merge/dedup → Rerank → Evidence bundle│
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│              Data Layer (PostgreSQL)     │
│  Chunks + embeddings | Entities          │
│  Session events | World state snapshots  │
└─────────────────────────────────────────┘
```

**Retrieval must always filter by**: active `campaign_id` + enabled modules for that campaign + global sources where `campaign_id IS NULL`.

---

## 5. Data Model

### 5.1 Tables and Columns

```sql
-- Campaign container
campaigns (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  edition     TEXT NOT NULL,           -- e.g. '5e', '3.5e'
  status      TEXT NOT NULL DEFAULT 'active',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
)

-- Module definition (version-tracked)
modules (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  version       TEXT NOT NULL,         -- semver
  edition       TEXT NOT NULL,
  manifest_json JSONB NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (name, version)
)

-- Many-to-many with priority
campaign_modules (
  campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  module_id   UUID NOT NULL REFERENCES modules(id),
  enabled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  priority    INT NOT NULL DEFAULT 50, -- higher = takes precedence on conflict
  PRIMARY KEY (campaign_id, module_id)
)

-- Source document registry
source_docs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id     UUID NOT NULL REFERENCES modules(id),
  title         TEXT NOT NULL,
  source_type   TEXT NOT NULL,         -- 'adventure' | 'rule' | 'homebrew'
  uri           TEXT,
  checksum      TEXT NOT NULL,         -- SHA-256 of source content
  version       TEXT NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
)

-- Text chunks with embeddings
chunks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_doc_id UUID NOT NULL REFERENCES source_docs(id) ON DELETE CASCADE,
  chunk_text    TEXT NOT NULL,
  token_count   INT NOT NULL,
  embedding     vector(1536),          -- match your embedding model dimension
  metadata_json JSONB NOT NULL,        -- see required keys below
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
)
-- Required metadata_json keys:
--   campaign_id   UUID | null   (null = globally available rule)
--   module_id     UUID
--   source_type   TEXT
--   canon_level   TEXT          ('official' | 'homebrew' | 'custom')
--   entity_refs   UUID[]        (IDs of referenced rule/lore entities)
--   version       TEXT

-- Structured rules (e.g. spells, conditions, class features)
rule_entities (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  module_id       UUID NOT NULL REFERENCES modules(id),
  entity_type     TEXT NOT NULL,       -- 'spell' | 'condition' | 'feat' | ...
  name            TEXT NOT NULL,
  normalized_name TEXT NOT NULL,       -- lowercase, stripped
  data_json       JSONB NOT NULL,
  UNIQUE (module_id, entity_type, normalized_name)
)

-- Campaign-specific lore (NPCs, locations, factions)
lore_entities (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  module_id   UUID REFERENCES modules(id),
  entity_type TEXT NOT NULL,
  name        TEXT NOT NULL,
  aliases     TEXT[] NOT NULL DEFAULT '{}',
  data_json   JSONB NOT NULL
)

-- Append-only event log per session
session_events (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id),
  session_id  UUID NOT NULL,
  event_type  TEXT NOT NULL,
  event_time  TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload_json JSONB NOT NULL
)

-- Key-value world state per campaign (last-write-wins per key)
world_state (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id),
  key         TEXT NOT NULL,          -- dotted path, e.g. 'quests.main.status'
  value_json  JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (campaign_id, key)
)

-- Full conversation history per session
chat_turns (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID NOT NULL REFERENCES campaigns(id),
  session_id  UUID NOT NULL,
  role        TEXT NOT NULL,          -- 'user' | 'assistant'
  content     TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  trace_json  JSONB                   -- retrieval trace, agent used, confidence
)
```

### 5.2 Required Indexes

```sql
-- Vector similarity search
CREATE INDEX idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- JSONB filtering (campaign, module, canon_level)
CREATE INDEX idx_chunks_metadata ON chunks USING GIN (metadata_json);

-- Full-text search
CREATE INDEX idx_chunks_fts ON chunks USING GIN (to_tsvector('english', chunk_text));

-- Session timeline queries
CREATE INDEX idx_session_events_campaign_session ON session_events (campaign_id, session_id, event_time);

-- World state lookups
CREATE INDEX idx_world_state_campaign_key ON world_state (campaign_id, key);
```

---

## 6. Module System

### 6.1 Manifest Format

```yaml
# module.yaml — required in every module package root
name: "Curse of Strahd"
version: "1.0.0"          # semver
edition: "5e"
priority: 50               # 1–100; higher wins on rule conflicts within a campaign
sources:
  - type: "adventure"
    path: "docs/adventure.md"
  - type: "rule"
    path: "docs/rules.md"
entities:
  - type: "npc"
    path: "data/npcs.json"
  - type: "monster"
    path: "data/monsters.json"
hooks:
  on_session_start: []     # list of callable identifiers (reserved for post-MVP)
  on_long_rest: []
compatibility:
  min_platform_version: "0.1.0"
```

### 6.2 Ingestion Pipeline (ordered steps)

1. **Validate manifest** — schema check; reject unknown fields; verify semver; abort on error.
2. **Check for existing version** — if `(name, version)` already exists, skip unless `--force` flag set.
3. **Parse sources** — supported at MVP: `.md`, `.txt`, `.json`; emit warning for unsupported types.
4. **Chunk and embed** — configurable `chunk_size` / `chunk_overlap`; store `token_count`; embed with configured provider.
5. **Extract entities** — parse `entities` paths; upsert into `rule_entities` / `lore_entities`.
6. **Build retrieval indexes** — update FTS vectors; trigger IVFFlat index rebuild if needed.
7. **Register module version** — write `modules` row and commit.
8. **Return ingestion report** — counts of chunks/entities, warnings, errors; never silently succeed.

### 6.3 Priority Conflict Resolution

When two enabled modules define the same rule entity:

- The module with **higher `priority`** wins.
- The lower-priority chunk is still stored but tagged `canon_level = 'overridden'`.
- The `/query` response must include a `DM Adjudication Note` when conflict is detected.

---

## 7. Retrieval & Answer Policy

### 7.1 Retrieval Pipeline

```
user_input
    │
    ▼
query_rewrite()        # lightweight; no semantic drift; only expand abbreviations
    │
    ├──► vector_search(topK=20, filters)
    └──► lexical_search(topK=20, filters)
         │
         ▼
    merge_deduplicate()
         │
         ▼
    rerank(topN=5)     # cross-encoder; stub-able at MVP
         │
         ▼
    evidence_bundle    # topN chunks with source metadata
```

**Mandatory filters on every retrieval call**:
```python
filters = {
    "campaign_id": [campaign_id, None],   # None = global rules
    "module_id": enabled_module_ids,
}
```

### 7.2 Answer Structure (mandatory for all factual/rules responses)

Every answer MUST contain all three parts:

```
**Conclusion**: [direct answer]

**Evidence**: [citations from retrieved chunks; chunk IDs included]

**DM Adjudication Note**: [present only if ambiguity, rule conflict, or low confidence]
```

If no evidence found with sufficient confidence: state this explicitly, do not hallucinate, ask a clarifying question.

---

## 8. Agent Architecture

### 8.1 Router (deterministic first, no LLM planner at MVP)

```python
def route(user_input: str, context: SessionContext) -> AgentType:
    # Rule-based intent classification
    # Fallback: RulesAgent
```

Classification order:
1. **StateAgent** — if input references explicit world state mutation ("mark quest complete", "player died")
2. **EncounterAgent** — if input references combat, monsters, initiative
3. **NarrativeAgent** — if input references scene, NPC, dialogue, description
4. **RulesAgent** — default

### 8.2 Agent Responsibilities

| Agent | Responsibility |
|---|---|
| `RulesAgent` | Rule lookup, constraint checking, action legality |
| `NarrativeAgent` | Scene narration, NPC dialogue grounded in lore + world state |
| `StateAgent` | Read/write world state, quest progression, consequence application |
| `EncounterAgent` | Encounter scaling suggestions, monster tactics from available data |

Each agent receives the full `evidence_bundle` from RAG. Agents must not retrieve independently — always go through the RAG layer.

---

## 9. API Contract

### Endpoints

#### `POST /modules/ingest`
```json
// Request
{ "package_path": "string" }

// Response
{
  "module_id": "uuid",
  "version": "1.0.0",
  "ingestion_report": {
    "chunks_created": 0,
    "entities_created": 0,
    "warnings": [],
    "errors": []
  }
}
```

#### `POST /campaigns`
```json
// Request
{ "name": "string", "edition": "5e" }
// Response: campaign object
```

#### `POST /campaigns/{campaign_id}/enable-module`
```json
// Request
{ "module_id": "uuid", "priority": 50 }
```

#### `POST /query`
```json
// Request
{
  "campaign_id": "uuid",
  "session_id": "uuid",
  "user_input": "string",
  "mode": "rules | narrative | state | encounter | auto"
}
// Response: see §10
```

#### `POST /sessions/{session_id}/events`
```json
// Request
{
  "campaign_id": "uuid",
  "event_type": "string",
  "payload_json": {}
}
```

#### `POST /state/apply`
```json
// Request
{
  "campaign_id": "uuid",
  "patches": [{ "op": "set|inc|append", "path": "string", "value": {} }]
}
```

#### `GET /campaigns/{campaign_id}/timeline`
Returns paginated list of `session_events` ordered by `event_time`.

---

## 10. `/query` Response Schema

```json
{
  "answer": "string",
  "used_agent": "rules | narrative | state | encounter",
  "confidence": 0.0,
  "citations": [
    {
      "chunk_id": "uuid",
      "source_doc_id": "uuid",
      "title": "string",
      "uri": "string | null",
      "snippet": "string"
    }
  ],
  "state_updates": [
    {
      "op": "set | inc | append",
      "path": "quests.main.status",
      "value": "in_progress",
      "reason": "string"
    }
  ],
  "needs_clarification": false,
  "clarification_question": "string | null"
}
```

`state_updates` are **proposed** — apply them via `POST /state/apply` to commit.

---

## 11. Safety & Compliance Rules

These are hard constraints — never relax them:

1. **No fabricated citations.** If a rule has no supporting chunk, say so.
2. **Excerpt, not reproduction.** Return `snippet` (≤ 200 chars) not full source text.
3. **Campaign scoping is mandatory.** Retrieval must never return chunks from a different campaign's private modules.
4. **Trace every query.** Write `trace_json` to `chat_turns` for every request: chunk IDs retrieved, agent used, rerank scores.
5. **Conflict transparency.** When module priority resolves a conflict, include the conflict details in `DM Adjudication Note`.

---

## 12. Testing Strategy

### Unit Tests
- `test_chunking.py` — chunk size/overlap correctness; metadata completeness
- `test_filters.py` — retrieval filter logic; campaign isolation enforced at query level
- `test_router.py` — intent classification for 20 representative inputs
- `test_state_patch.py` — valid and invalid patch operations

### Integration Tests (require live DB)
- Ingest sample module → query → verify citation chunk IDs exist in DB
- Create two campaigns with same module → query both → assert zero result cross-contamination
- Enable two modules with conflicting rule → verify higher-priority module wins + adjudication note present
- Apply state patches → query timeline → verify event ordering

### Evaluation Fixtures

Create `tests/fixtures/eval_set.json` with:
- 50 rule questions + expected citations (chunk IDs or source doc titles)
- 30 lore continuity questions + expected entity references
- 20 state progression scenarios + expected `state_updates`

Track these metrics in CI:
| Metric | Target |
|---|---|
| Retrieval hit@5 | ≥ 0.85 |
| Citation precision | ≥ 0.90 |
| Rule accuracy | ≥ 0.90 |
| State consistency | 1.0 |
| P95 query latency | < 2s |

---

## 13. Build Order

Work in this sequence. Each step should be independently mergeable:

```
Step 1  DB schema + Alembic migrations
Step 2  Module manifest validator + ingestion pipeline (parse → chunk → embed → store)
Step 3  Hybrid retrieval (vector + lexical) — reranker stubbed behind interface
Step 4  Router + 4 agent handlers (minimal viable, no LLM orchestration)
Step 5  POST /query with full citation-rich response schema
Step 6  State/event persistence (POST /state/apply, POST /sessions/.../events)
Step 7  Remaining API endpoints (/campaigns, /modules/ingest, /timeline)
Step 8  Integration tests + eval fixtures
Step 9  Docs + example module package
```

**First PR scope** (Steps 1–3 + minimal /query):
- DB schema + migrations
- `/campaigns`, `/modules/ingest`, `/query` (rules mode only)
- Basic hybrid retrieval without reranker
- Citation output contract enforced
- ≥ 10 integration tests with sample module

---

## 14. Repository Structure

```
app/
├── api/            # FastAPI routers
├── agents/         # RulesAgent, NarrativeAgent, StateAgent, EncounterAgent
├── rag/            # retrieval pipeline, reranker interface
├── ingestion/      # manifest validator, chunker, embedder
├── state/          # world state patch validator and applier
├── db/             # SQLAlchemy models, Alembic migrations
├── schemas/        # Pydantic request/response schemas
└── core/           # config, logging, tracing

tests/
├── unit/
├── integration/
└── fixtures/
    ├── eval_set.json
    └── modules/
        └── sample_forgotten_forest/
            ├── module.yaml
            ├── docs/
            └── data/

examples/
└── modules/
    └── sample_forgotten_forest/   # same as fixtures copy, for docs
```

---

## 15. Definition of Done (MVP)

All must pass before MVP is complete:

- [ ] A module can be ingested end-to-end with a structured report.
- [ ] A campaign can enable multiple modules with different priorities.
- [ ] `/query` returns grounded answer + chunk-level citations.
- [ ] Two campaigns querying the same question do not leak each other's private module chunks.
- [ ] Session events update timeline; world state is consistent after patch.
- [ ] All integration tests pass in CI with a clean DB.
- [ ] P95 `/query` latency < 2s on evaluation fixture set.

---

## 16. Coding Standards & Claude Code Behavior

### Code Standards
- Type hints everywhere; no untyped public functions.
- Functions ≤ 30 lines; single responsibility.
- No hidden global mutable state.
- All critical code paths emit structured logs with `trace_id`.
- Docstrings on all public interfaces.
- Explicit errors over silent fallback — raise, don't swallow.

### For Claude Code Specifically
- **Before changing architecture**: check existing repo conventions first. If conflict, flag it and ask.
- **Before adding a dependency**: choose the simplest stable option; note the choice in PR description.
- **When changing API contracts**: update Pydantic schemas, tests, and docs in the same change.
- **Migrations**: prefer backward-compatible (add column with default; don't rename/drop in same migration as feature).
- **On ambiguous requirements**: document your assumption as a `# ASSUMPTION:` comment, and note it in the PR.
- **On test failures you can't explain**: do not skip or mock around them — surface the root cause.
