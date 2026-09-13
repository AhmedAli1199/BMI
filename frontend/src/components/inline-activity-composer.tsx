"use client";

import { useState, useTransition } from "react";
import { toast } from "sonner";
import {
  Calendar,
  FileText,
  Mail,
  PhoneCall,
  Send,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { addContactNote } from "@/lib/actions";

type ActivityType = "call" | "meeting" | "note" | "email";

export function InlineActivityComposer({
  contactId,
  contactName,
}: {
  contactId: string;
  contactName: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [activityType, setActivityType] = useState<ActivityType>("call");
  const [content, setContent] = useState("");
  const [pending, startTransition] = useTransition();

  function handleSubmit() {
    if (!content.trim()) return;

    const prefixMap: Record<ActivityType, string> = {
      call: "📞 [Call Log]: ",
      meeting: "🤝 [Meeting]: ",
      note: "📝 [Note]: ",
      email: "✉️ [Email Sent]: ",
    };

    const fullBody = `${prefixMap[activityType]}${content.trim()}`;

    startTransition(async () => {
      try {
        await addContactNote(contactId, fullBody);
        toast.success("Touchpoint logged to timeline");
        setContent("");
        setIsOpen(false);
      } catch {
        toast.error("Failed to log activity");
      }
    });
  }

  if (!isOpen) {
    return (
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-card p-3 shadow-xs">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" />
          <span>Quick Touchpoint with {contactName.split(" ")[0]}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setActivityType("call");
              setIsOpen(true);
            }}
            className="h-7 text-xs gap-1.5 cursor-pointer hover:border-primary/50"
          >
            <PhoneCall className="size-3 text-amber-600" />
            <span>Log Call</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setActivityType("meeting");
              setIsOpen(true);
            }}
            className="h-7 text-xs gap-1.5 cursor-pointer hover:border-primary/50"
          >
            <Calendar className="size-3 text-blue-600" />
            <span>Meeting</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setActivityType("note");
              setIsOpen(true);
            }}
            className="h-7 text-xs gap-1.5 cursor-pointer hover:border-primary/50"
          >
            <FileText className="size-3 text-emerald-600" />
            <span>Note</span>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setActivityType("email");
              setIsOpen(true);
            }}
            className="h-7 text-xs gap-1.5 cursor-pointer hover:border-primary/50"
          >
            <Mail className="size-3 text-purple-600" />
            <span>Email</span>
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-primary/30 bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between border-b pb-2">
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            size="sm"
            variant={activityType === "call" ? "default" : "ghost"}
            className="h-7 text-xs gap-1 cursor-pointer"
            onClick={() => setActivityType("call")}
          >
            <PhoneCall className="size-3" />
            <span>Call</span>
          </Button>
          <Button
            type="button"
            size="sm"
            variant={activityType === "meeting" ? "default" : "ghost"}
            className="h-7 text-xs gap-1 cursor-pointer"
            onClick={() => setActivityType("meeting")}
          >
            <Calendar className="size-3" />
            <span>Meeting</span>
          </Button>
          <Button
            type="button"
            size="sm"
            variant={activityType === "note" ? "default" : "ghost"}
            className="h-7 text-xs gap-1 cursor-pointer"
            onClick={() => setActivityType("note")}
          >
            <FileText className="size-3" />
            <span>Note</span>
          </Button>
          <Button
            type="button"
            size="sm"
            variant={activityType === "email" ? "default" : "ghost"}
            className="h-7 text-xs gap-1 cursor-pointer"
            onClick={() => setActivityType("email")}
          >
            <Mail className="size-3" />
            <span>Email</span>
          </Button>
        </div>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => setIsOpen(false)}
          className="h-6 px-2 text-xs text-muted-foreground"
        >
          Cancel
        </Button>
      </div>

      <Textarea
        autoFocus
        placeholder={
          activityType === "call"
            ? "Summary of call (reached, voicemail, discussed ad rates, WTCE meet)..."
            : activityType === "meeting"
            ? "Meeting notes, attendees, next steps, magazine issue discussed..."
            : activityType === "email"
            ? "Summary of email conversation, rate cards sent, artwork deadline..."
            : "Write a note about this contact..."
        }
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="min-h-[80px] text-sm resize-none"
      />

      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">
          Logged with timestamp and added directly to timeline
        </span>
        <Button
          size="sm"
          disabled={pending || !content.trim()}
          onClick={handleSubmit}
          className="gap-1.5 cursor-pointer font-medium"
        >
          <Send className="size-3" />
          <span>{pending ? "Logging..." : "Log to Timeline"}</span>
        </Button>
      </div>
    </div>
  );
}
