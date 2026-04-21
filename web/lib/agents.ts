// Thin wrapper around Agent Stack HTTP endpoints. Called from server actions
// and client components when the user asks a question / saves / dismisses.

const BASE = process.env.NEXT_PUBLIC_AGENT_SERVER_URL ?? "http://127.0.0.1:8333";

export async function callAgent(
  agent: "orchestrator" | "search" | "analysis" | "notification" | "database",
  text: string,
): Promise<string> {
  const resp = await fetch(`${BASE}/agents/${agent}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: { role: "user", parts: [{ kind: "text", text }] },
    }),
  });
  if (!resp.ok) throw new Error(`agent ${agent} returned ${resp.status}`);
  const data = await resp.json();
  // Agent Stack response shape: { message: { parts: [{ kind: "text", text }] } }
  return (
    data?.message?.parts?.map((p: { text?: string }) => p.text ?? "").join("") ??
    JSON.stringify(data)
  );
}
