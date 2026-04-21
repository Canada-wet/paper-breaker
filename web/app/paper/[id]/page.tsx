import Link from "next/link";
import { supabase, type Paper, type PaperAnalysis } from "@/lib/supabase";
import { InteractionButtons } from "./interactions";

export const revalidate = 0;

export default async function PaperPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const { data: paper } = await supabase
    .from("papers")
    .select("*")
    .eq("id", id)
    .maybeSingle();
  const { data: analysis } = await supabase
    .from("paper_analyses")
    .select("*")
    .eq("paper_id", id)
    .maybeSingle();

  if (!paper) {
    return (
      <main className="container">
        <p>Paper not found.</p>
        <Link href="/">← back</Link>
      </main>
    );
  }

  const p = paper as Paper;
  const a = analysis as PaperAnalysis | null;

  return (
    <main className="container">
      <Link href="/" className="meta">← back to digest</Link>
      <h1 style={{ marginTop: 12 }}>{p.title}</h1>
      <div className="meta">
        {p.authors?.join(", ")}
        {p.published_at ? ` · ${p.published_at.slice(0, 10)}` : ""}
        {p.url ? (
          <>
            {" · "}
            <a href={p.url} target="_blank" rel="noreferrer">source</a>
          </>
        ) : null}
      </div>

      <InteractionButtons paperId={p.id} />

      {!a && (
        <p className="summary" style={{ marginTop: 20 }}>
          No analysis yet. Run <code>paper-breaker analyze {p.arxiv_id}</code>.
        </p>
      )}

      {a && (
        <>
          <h2 style={{ marginTop: 28 }}>How this applies to your work</h2>
          <p>{a.henry_application}</p>

          <h2 style={{ marginTop: 28 }}>Sections</h2>
          {a.sections?.map((s, i) => (
            <section key={i} style={{ marginBottom: 18 }}>
              <h3>{s.heading}</h3>
              <p>{s.plain_summary}</p>
              <ul>
                {s.key_points?.map((kp, j) => <li key={j}>{kp}</li>)}
              </ul>
            </section>
          ))}

          <h2 style={{ marginTop: 28 }}>Insights</h2>
          <ul>
            {a.insights?.map((i, k) => (
              <li key={k} style={{ marginBottom: 10 }}>
                <strong>{i.insight}</strong>
                <div className="meta">Novelty: {i.novelty}</div>
                {i.caveats ? <div className="meta">Caveats: {i.caveats}</div> : null}
              </li>
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
