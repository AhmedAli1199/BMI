import type { BrainContext, BrainMessage } from "@/lib/brain-types";

export type AskBody = {
  conversation_id?: string | null;
  message: string;
  context: BrainContext;
  images?: { data: string; label?: string; width?: number; height?: number }[];
};

type Handlers = {
  meta?: (m: { conversation_id: string; message_id: string }) => void;
  step?: (label: string) => void;
  text?: (delta: string) => void;
  done?: (message: BrainMessage) => void;
};

/** Sends a question and reads the answer as it streams in (server-sent events through the files proxy). */
export async function askBrain(body: AskBody, on: Handlers, signal?: AbortSignal): Promise<void> {
  const res = await fetch("/api/files/brain/chat", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), signal,
  });
  if (!res.ok || !res.body) {
    const detail = await res.json().then((b) => b?.detail).catch(() => null);
    throw new Error(typeof detail === "string" ? detail : "");
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let cut: number;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, cut);
      buf = buf.slice(cut + 2);
      const kind = /^event: (\w+)/m.exec(block)?.[1];
      const raw = /^data: (.*)$/m.exec(block)?.[1];
      if (!kind || !raw) continue;
      const data = JSON.parse(raw);
      if (kind === "meta") on.meta?.(data);
      else if (kind === "step") on.step?.(data.label);
      else if (kind === "text") on.text?.(data.delta);
      else if (kind === "done") on.done?.(data.message);
    }
  }
}
