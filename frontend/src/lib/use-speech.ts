"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";
import { friendlyError } from "@/lib/errors";

/** Press to talk, press again to stop: the recording becomes words (the same service the proposals use). */
export function useSpeech(onText: (t: string) => void, endpoint = "/api/files/proposals/transcribe") {
  const rec = useRef<MediaRecorder | null>(null);
  const [state, setState] = useState<"idle" | "listening" | "writing">("idle");
  async function toggle() {
    if (rec.current) { rec.current.stop(); rec.current = null; return; }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") { toast.error("This browser can't record - type it instead."); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setState("writing");
        try {
          const blob = new Blob(chunks, { type: r.mimeType || "audio/webm" });
          const res = await fetch(endpoint, { method: "POST", headers: { "Content-Type": blob.type }, body: blob });
          const body = await res.json();
          if (!res.ok) throw new Error(body.detail || "");
          onText(body.text);
        } catch (e) { toast.error(friendlyError(e, "Couldn't make out the recording - type it instead.")); }
        finally { setState("idle"); }
      };
      r.start();
      rec.current = r;
      setState("listening");
    } catch { toast.error("The microphone isn't available - type it instead."); }
  }
  return { state, toggle };
}
