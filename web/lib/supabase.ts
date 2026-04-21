import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!,
  {
    auth: { persistSession: false },
    realtime: { params: { eventsPerSecond: 5 } },
  },
);

export type DailyDigest = {
  id: string;
  user_id: string;
  date: string;
  paper_ids: string[];
  summary: string | null;
  created_at: string;
};

export type Paper = {
  id: string;
  arxiv_id: string | null;
  title: string;
  abstract: string | null;
  authors: string[] | null;
  url: string | null;
  pdf_url: string | null;
  published_at: string | null;
  source: string | null;
};

export type PaperAnalysis = {
  paper_id: string;
  sections: { heading: string; plain_summary: string; key_points: string[] }[];
  insights: { insight: string; novelty: string; caveats: string }[];
  henry_application: string;
  model: string;
  created_at: string;
};
