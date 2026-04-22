// Supabase Edge Function: daily_trigger
//
// Called once per day by pg_cron (see supabase/migrations/0002_cron.sql once you
// add it). POSTs a heartbeat to the NotificationAgent's A2A endpoint with a
// shared secret so the agent server knows the request is authorized.
//
// Deploy:
//   supabase functions deploy daily_trigger --no-verify-jwt
//   supabase secrets set AGENT_SERVER_URL=https://your-agent-host:8333 \
//                       DAILY_TRIGGER_SECRET=change-me

import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const AGENT_URL = Deno.env.get("AGENT_SERVER_URL")!;
const SECRET = Deno.env.get("DAILY_TRIGGER_SECRET")!;

Deno.serve(async (_req) => {
  if (!AGENT_URL || !SECRET) {
    return new Response("missing AGENT_SERVER_URL or DAILY_TRIGGER_SECRET", {
      status: 500,
    });
  }

  // The agent server hosts a single orchestrator endpoint that routes
  // internally to the notification flow when it sees "digest" intent.
  const resp = await fetch(`${AGENT_URL}/agents/orchestrator/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Daily-Secret": SECRET,
    },
    body: JSON.stringify({
      message: {
        role: "user",
        parts: [
          { kind: "text", text: "Run today's daily digest for the default user." },
        ],
      },
    }),
  });

  const body = await resp.text();
  return new Response(
    JSON.stringify({ status: resp.status, body: body.slice(0, 2000) }),
    { headers: { "Content-Type": "application/json" } },
  );
});
