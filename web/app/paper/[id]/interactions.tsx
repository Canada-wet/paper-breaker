"use client";

import { useState } from "react";
import { callAgent } from "@/lib/agents";

export function InteractionButtons({ paperId }: { paperId: string }) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "dismissed">(
    "idle",
  );

  async function act(kind: "saved" | "dismissed") {
    setState("saving");
    try {
      await callAgent(
        "database",
        `log_interaction for paper_id=${paperId} type=${kind}`,
      );
      setState(kind);
    } catch {
      setState("idle");
    }
  }

  return (
    <div className="actions" style={{ marginTop: 12 }}>
      <button
        className="btn"
        disabled={state === "saving" || state === "saved"}
        onClick={() => act("saved")}
      >
        {state === "saved" ? "Saved" : "Save"}
      </button>
      <button
        className="btn"
        disabled={state === "saving" || state === "dismissed"}
        onClick={() => act("dismissed")}
      >
        {state === "dismissed" ? "Dismissed" : "Dismiss"}
      </button>
    </div>
  );
}
