-- Paper-Breaker initial schema.
-- Apply via: supabase db push   (or paste into the SQL editor)

create extension if not exists vector;
create extension if not exists pg_cron;

-- -----------------------------------------------------------------------
-- user_profile: single-user today, multi-user ready.
-- -----------------------------------------------------------------------
create table if not exists user_profile (
  id            uuid primary key default gen_random_uuid(),
  email         text unique,
  role          text,
  work_context  text,
  interests     jsonb default '[]'::jsonb,
  tech_stack    jsonb default '[]'::jsonb,
  goals         text,
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

-- -----------------------------------------------------------------------
-- topics: per-user standing queries the NotificationAgent re-runs daily.
-- -----------------------------------------------------------------------
create table if not exists topics (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references user_profile(id) on delete cascade,
  query       text not null,
  cadence     text default 'daily',
  last_run_at timestamptz,
  active      boolean default true,
  created_at  timestamptz default now()
);
create index if not exists topics_user_active_idx on topics(user_id) where active;

-- -----------------------------------------------------------------------
-- papers: source-of-truth catalog. arxiv_id is unique; s2_id optional.
-- -----------------------------------------------------------------------
create table if not exists papers (
  id           uuid primary key default gen_random_uuid(),
  arxiv_id     text unique,
  s2_id        text,
  title        text not null,
  abstract     text,
  authors      jsonb,
  url          text,
  pdf_url      text,
  published_at timestamptz,
  source       text,
  raw          jsonb,
  created_at   timestamptz default now()
);
create index if not exists papers_published_idx on papers(published_at desc);

-- -----------------------------------------------------------------------
-- paper_analyses: AnalysisAgent output, one row per paper.
-- -----------------------------------------------------------------------
create table if not exists paper_analyses (
  paper_id           uuid primary key references papers(id) on delete cascade,
  sections           jsonb,
  insights           jsonb,
  henry_application  text,
  model              text,
  created_at         timestamptz default now()
);

-- -----------------------------------------------------------------------
-- paper_vectors: pgvector embedding for dedupe + "more like this".
-- Dimension matches EMBEDDING_DIMENSIONS in .env (default 384 for MiniLM).
-- If you switch to OpenAI text-embedding-3-small, alter to vector(1536).
-- -----------------------------------------------------------------------
create table if not exists paper_vectors (
  paper_id  uuid primary key references papers(id) on delete cascade,
  embedding vector(384)
);
create index if not exists paper_vectors_cos_idx
  on paper_vectors using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

-- -----------------------------------------------------------------------
-- interactions: feedback loop — viewed | saved | dismissed | rated | asked.
-- -----------------------------------------------------------------------
create table if not exists interactions (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references user_profile(id) on delete cascade,
  paper_id   uuid references papers(id) on delete cascade,
  type       text not null,
  value      jsonb,
  created_at timestamptz default now()
);
create index if not exists interactions_user_created_idx
  on interactions(user_id, created_at desc);

-- -----------------------------------------------------------------------
-- daily_digests: one row per user per day. Powers the landing page.
-- -----------------------------------------------------------------------
create table if not exists daily_digests (
  id         uuid primary key default gen_random_uuid(),
  user_id    uuid references user_profile(id) on delete cascade,
  date       date not null,
  paper_ids  uuid[] default '{}'::uuid[],
  summary    text,
  created_at timestamptz default now(),
  unique(user_id, date)
);

-- -----------------------------------------------------------------------
-- Similarity helper for dedupe (called from the Python supabase_tool).
-- -----------------------------------------------------------------------
create or replace function match_paper_by_embedding(
  query_embedding vector(384),
  match_threshold float default 0.85,
  match_count int default 5
)
returns table(paper_id uuid, similarity float)
language sql stable
as $$
  select
    pv.paper_id,
    1 - (pv.embedding <=> query_embedding) as similarity
  from paper_vectors pv
  where 1 - (pv.embedding <=> query_embedding) > match_threshold
  order by pv.embedding <=> query_embedding
  limit match_count;
$$;

-- -----------------------------------------------------------------------
-- Row Level Security.
-- Reads: publishable (anon) key can SELECT.
-- Writes: only the service_role key can INSERT/UPDATE/DELETE.
-- -----------------------------------------------------------------------
alter table user_profile   enable row level security;
alter table topics         enable row level security;
alter table papers         enable row level security;
alter table paper_analyses enable row level security;
alter table paper_vectors  enable row level security;
alter table interactions   enable row level security;
alter table daily_digests  enable row level security;

-- Anon read policies (idempotent via drop-if-exists)
drop policy if exists "anon read" on user_profile;
create policy "anon read" on user_profile for select using (true);
drop policy if exists "anon read" on topics;
create policy "anon read" on topics for select using (true);
drop policy if exists "anon read" on papers;
create policy "anon read" on papers for select using (true);
drop policy if exists "anon read" on paper_analyses;
create policy "anon read" on paper_analyses for select using (true);
drop policy if exists "anon read" on daily_digests;
create policy "anon read" on daily_digests for select using (true);
-- paper_vectors + interactions intentionally have NO anon policy — server-only.
