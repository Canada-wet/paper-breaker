import Link from "next/link";
import { supabase, type DailyDigest, type Paper } from "@/lib/supabase";
import { DigestLive } from "./digest-live";

export const revalidate = 0;

export default async function Home() {
  const today = new Date().toISOString().slice(0, 10);
  const { data: digest } = await supabase
    .from("daily_digests")
    .select("*")
    .eq("date", today)
    .maybeSingle();

  let papers: Paper[] = [];
  if (digest && digest.paper_ids?.length) {
    const { data } = await supabase
      .from("papers")
      .select("*")
      .in("id", digest.paper_ids);
    papers = data ?? [];
  }

  return (
    <main className="container">
      <div className="header">
        <h1>Paper Breaker</h1>
        <span className="meta">{today}</span>
      </div>

      <DigestLive initial={digest as DailyDigest | null} />

      {digest?.summary && <p className="summary">{digest.summary}</p>}

      {papers.length === 0 && (
        <p className="summary">
          No digest yet for today. Run{" "}
          <code>paper-breaker digest</code> or wait for the 07:00 cron.
        </p>
      )}

      <div className="grid">
        {papers.map((p) => (
          <Link key={p.id} href={`/paper/${p.id}`} className="card">
            <h3>{p.title}</h3>
            <div className="meta">
              {p.authors?.slice(0, 3).join(", ")}
              {p.authors && p.authors.length > 3 ? " +more" : ""}
              {p.published_at ? ` · ${p.published_at.slice(0, 10)}` : ""}
              {p.source ? ` · ${p.source}` : ""}
            </div>
            <div className="abstract">{p.abstract}</div>
          </Link>
        ))}
      </div>
    </main>
  );
}
