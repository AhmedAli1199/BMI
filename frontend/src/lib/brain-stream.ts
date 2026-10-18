import type { BrainAction, BrainContext, BrainMessage } from "@/lib/brain-types";

/** The Brain's chat stream speaks AG-UI 1.0 (docs.ag-ui.com): server-sent `data: {json}` events with a `type`.
 * Only the events the backend sends (backend/app/api/routes/brain.py) are typed here - camelCase, as in the spec. */
export type AgUiEvent =
  | { type: "RUN_STARTED"; threadId: string; runId: string; metadata?: { message_id?: string } }
  | { type: "STEP_STARTED" | "STEP_FINISHED"; stepName: string }
  | { type: "TEXT_MESSAGE_START"; messageId: string; role?: string }
  | { type: "TEXT_MESSAGE_CONTENT"; messageId: string; delta: string }
  | { type: "TEXT_MESSAGE_END"; messageId: string }
  | { type: "TOOL_CALL_START"; toolCallId: string; toolCallName: string; parentMessageId?: string }
  | { type: "TOOL_CALL_ARGS"; toolCallId: string; delta: string }
  | { type: "TOOL_CALL_END"; toolCallId: string }
  | { type: "TOOL_CALL_RESULT"; toolCallId: string; messageId: string; content: string }
  | { type: "RUN_FINISHED"; threadId: string; runId: string; result?: { message?: BrainMessage; cards?: BrainAction[] };
      outcome?: { type: "success" } | { type: "interrupt"; interrupts: { id: string; reason: string; message?: string; toolCallId?: string }[] } }
  | { type: "RUN_ERROR"; message: string; code?: string };

export type AskBody = {
  conversation_id?: string | null;
  message?: string;
  context?: BrainContext;
  images?: { data: string; label?: string; width?: number; height?: number }[];
  /** AG-UI resume: the answer to cards the last run stopped on (Confirm = "resolved", Cancel = "cancelled"). */
  resume?: { interruptId: string; status: "resolved" | "cancelled" }[];
};

type Handlers = {
  started?: (conversationId: string) => void;
  step?: (label: string) => void;
  text?: (delta: string) => void;
  /** a card the Brain proposed (a "confirm_action" tool call) - shown once its arguments are complete */
  card?: (card: BrainAction) => void;
  /** how a card ended, after Confirm or Cancel */
  cardResult?: (card: BrainAction) => void;
  done?: (message: BrainMessage | undefined) => void;
  /** a plain sentence (not switched on, or it failed) */
  error?: (message: string) => void;
};

/** Sends a question (or the answer to a card) and reads the AG-UI events as they stream in (through the files proxy). */
export async function askBrain(body: AskBody, on: Handlers, signal?: AbortSignal): Promise<void> {
  const res = await fetch("/api/files/brain/chat", {
    method: "POST", headers: { "Content-Type": "application/json", Accept: "text/event-stream" }, body: JSON.stringify(body), signal,
  });
  if (!res.ok || !res.body) {
    const detail = await res.json().then((b) => b?.detail).catch(() => null);
    throw new Error(typeof detail === "string" ? detail : "");
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  const args: Record<string, string> = {};
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let cut: number;
    while ((cut = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, cut);
      buf = buf.slice(cut + 2);
      const raw = block.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trimStart()).join("\n");
      if (!raw) continue;
      const ev = JSON.parse(raw) as AgUiEvent;
      switch (ev.type) {
        case "RUN_STARTED": on.started?.(ev.threadId); break;
        case "STEP_STARTED": on.step?.(ev.stepName); break;
        case "TEXT_MESSAGE_CONTENT": on.text?.(ev.delta); break;
        case "TOOL_CALL_START": args[ev.toolCallId] = ""; break;
        case "TOOL_CALL_ARGS": args[ev.toolCallId] = (args[ev.toolCallId] ?? "") + ev.delta; break;
        case "TOOL_CALL_END": try { on.card?.(JSON.parse(args[ev.toolCallId] || "{}")); } catch { /* a card we can't read is left out */ } break;
        case "TOOL_CALL_RESULT": try { on.cardResult?.(JSON.parse(ev.content)); } catch { /* ignore */ } break;
        case "RUN_FINISHED": on.done?.(ev.result?.message); break;
        case "RUN_ERROR": on.error?.(ev.message); break;
      }
    }
  }
}
