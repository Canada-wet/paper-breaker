# paper-breaker

An A2A multi-agent system (BeeAI Framework + Agent Stack) that surfaces, breaks down,
and contextualizes AI research papers against your day-to-day work. Storage is
Supabase (Postgres + pgvector + Realtime); the landing page is a small Next.js app.

## Agents

- **Orchestrator** — routes messages to specialists; handles first-run onboarding.
- **SearchAgent** — pulls papers from arXiv + Semantic Scholar, embeds + dedupes.
- **AnalysisAgent** — breaks one paper into sections + a tailored "how this applies to you".
- **NotificationAgent** — daily cron target that writes today's `daily_digests` row.
- **DatabaseAgent** — thin BeeAI wrapper over the Supabase service-role client.

All five are exposed over HTTP as A2A services by `agentstack-sdk` in `src/paper_breaker/server.py`.

## One-time setup

1. **Secrets**
   ```bash
   cp .env.example .env
   # Fill in:
   #   ANTHROPIC_API_KEY       — console.anthropic.com
   #   SUPABASE_SERVICE_KEY    — Supabase dashboard → Project Settings → API → service_role
   # (SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY come pre-filled.)
   ```

2. **Database schema**
   ```bash
   # Option A: Supabase SQL editor — paste supabase/migrations/0001_init.sql and run.
   # Option B: Supabase CLI
   supabase link --project-ref xqrfmanrfppfxsozdmht
   supabase db push
   ```

3. **Python env**
   ```bash
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -e '.[dev]'
   ```

4. **Seed your profile** (or let the onboarding chat do it on first server run)
   ```bash
   paper-breaker profile \
     --role "Senior ML Engineer" \
     --work-context "Building agentic systems on top of LLMs" \
     --interests "LLM agents, RL, eval, multimodal" \
     --tech-stack "Python, PyTorch, FastAPI, Supabase" \
     --goals "Ship an A2A paper-analysis system; learn faster from papers."
   ```

## Phase-by-phase verification

### Phase 1 — Skateboard (SearchAgent + DatabaseAgent)
```bash
paper-breaker search "diffusion transformers" --days 7
# → check Supabase: SELECT count(*), source FROM papers GROUP BY source;
```

### Phase 2 — Scooter (AnalysisAgent)
```bash
paper-breaker analyze 2401.12345
# → check Supabase: SELECT paper_id, henry_application IS NOT NULL FROM paper_analyses;
```

### Phase 3 — Bike (A2A server)
```bash
paper-breaker-server
# Open Agent Stack's auto-UI (default http://127.0.0.1:8333) and chat with /orchestrator.
```

### Phase 4 — Motorbike (daily digest)
```bash
paper-breaker digest
# → check Supabase: SELECT * FROM daily_digests ORDER BY date DESC LIMIT 1;

# To enable the 07:00 UTC pg_cron:
#   supabase functions deploy daily_trigger --no-verify-jwt
#   supabase secrets set AGENT_SERVER_URL=... DAILY_TRIGGER_SECRET=...
#   run supabase/migrations/0002_cron.sql
```

### Phase 5 — Car (landing page)
```bash
cd web
cp .env.local.example .env.local
pnpm install
pnpm dev
# open http://localhost:3000
```

## Repo layout

```
paper-breaker/
├── pyproject.toml
├── .env.example
├── Dockerfile            docker-compose.yml
├── supabase/
│   ├── migrations/       0001_init.sql  0002_cron.sql
│   └── functions/daily_trigger/index.ts
├── src/paper_breaker/
│   ├── config.py
│   ├── server.py         orchestrator.py  cli.py
│   ├── agents/           search.py  analysis.py  notification.py  database.py
│   ├── tools/            arxiv_tool.py  semantic_scholar_tool.py  pdf_fetch_tool.py
│   │                     embedding_tool.py  supabase_tool.py
│   ├── memory/profile_loader.py
│   └── prompts/          analysis_system.md  onboarding.md
└── web/                  Next.js app (app router)
    ├── app/              page.tsx  paper/[id]/page.tsx  digest-live.tsx
    └── lib/              supabase.ts  agents.ts
```

## Key design choices (why, not what)

- **Service role key lives in the agent server only.** The publishable key is safe for the browser because RLS gates everything; agent writes go through the service-role client. Never ship the service key to `web/`.
- **Every agent hydrates from Supabase and writes back.** BeeAI's in-process Memory is a scratchpad — Supabase is the brain. This is what lets "all agents have memory about history and the user" without a central memory service.
- **pg_cron, not system cron.** Your laptop won't always be on. The Supabase Edge Function + pg_cron trigger the notification agent regardless.
- **Local embeddings (MiniLM, 384 dims).** Dedupe doesn't need SOTA embeddings; staying local avoids a second API key. Swap `EMBEDDING_PROVIDER=openai` later if you want higher fidelity.

## Known limitations (v1)

- BeeAI Python SDK is alpha; pin exact versions in `pyproject.toml` before you care about reproducibility.
- IEEE and X/Twitter paper sources are out of scope (paywalled / gated).
- "Insightful" ranking uses citation count + recency. A learned preference model becomes possible once `interactions` has enough data.
