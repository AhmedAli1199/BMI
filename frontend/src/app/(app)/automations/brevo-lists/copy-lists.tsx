"use client";

import { Copy } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

export type BrevoList = { id: number; name: string; folder: number | null; people: number | null };

export function CopyBrevoLists({ lists }: { lists: BrevoList[] }) {
  const text = ["Number | Name | Folder | People", ...lists.map((l) => `${l.id} | ${l.name} | ${l.folder ?? ""} | ${l.people ?? ""}`)].join("\n");
  const copy = () =>
    navigator.clipboard.writeText(text).then(() => toast.success("Copied")).catch(() => toast.error("Couldn't copy - select the table and copy it instead"));
  if (!lists.length) return <p className="rounded-lg border border-border bg-card p-4 text-sm text-muted-foreground">Brevo has no contact lists.</p>;
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border/80 bg-card p-5 shadow-2xs">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold">{lists.length} list{lists.length === 1 ? "" : "s"}</p>
        <Button size="sm" variant="outline" className="gap-1.5" onClick={copy}>
          <Copy className="size-3.5" aria-hidden="true" /> Copy all
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              <th className="py-1.5 pr-3 font-medium">Number</th>
              <th className="py-1.5 pr-3 font-medium">Name</th>
              <th className="py-1.5 pr-3 font-medium">Folder</th>
              <th className="py-1.5 font-medium">People</th>
            </tr>
          </thead>
          <tbody>
            {lists.map((l) => (
              <tr key={l.id} className="border-b border-border/60">
                <td className="py-1.5 pr-3 font-mono text-xs">{l.id}</td>
                <td className="py-1.5 pr-3">{l.name}</td>
                <td className="py-1.5 pr-3 text-muted-foreground">{l.folder ?? ""}</td>
                <td className="py-1.5 text-muted-foreground">{l.people ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
