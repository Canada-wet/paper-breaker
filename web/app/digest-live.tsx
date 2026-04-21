"use client";

import { useEffect, useState } from "react";
import { supabase, type DailyDigest } from "@/lib/supabase";

export function DigestLive({ initial }: { initial: DailyDigest | null }) {
  const [digest, setDigest] = useState<DailyDigest | null>(initial);

  useEffect(() => {
    const channel = supabase
      .channel("digests")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "daily_digests" },
        (payload) => {
          const row = payload.new as DailyDigest;
          const today = new Date().toISOString().slice(0, 10);
          if (row.date === today) setDigest(row);
        },
      )
      .subscribe();
    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  if (!digest) return null;
  return null; // The parent re-renders on next navigation; this exists to bind the subscription.
}
