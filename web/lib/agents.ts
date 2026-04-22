// Thin wrapper around the single A2A orchestrator endpoint. The orchestrator
// is a LangGraph state machine that routes each message to the right
// specialist (search / analysis / notification / database / chat) internally.

const BASE = process.env.NEXT_PUBLIC_AGENT_SERVER_URL ?? "http://127.0.0.1:8333";

export async function callAgent(text: string): Promise<string> {
  const resp = await fetch(`${BASE}/agents/orchestrator/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: { role: "user", parts: [{ kind: "text", text }] },
    }),
  });
  if (!resp.ok) throw new Error(`orchestrator returned ${resp.status}`);
  const data = await resp.json();
  // Agent Stack response shape: { message: { parts: [{ kind: "text", text }] } }
  return (
    data?.message?.parts?.map((p: { text?: string }) => p.text ?? "").join("") ??
    JSON.stringify(data)
  );
}
