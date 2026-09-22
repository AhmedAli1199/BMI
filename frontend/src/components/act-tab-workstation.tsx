"use client";

import { useState } from "react";
import {
  BookOpen,
  Calendar,
  Clock,
  FileText,
  Layers,
  Search,
  UsersRound,
} from "lucide-react";
import type { ContactDetail } from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { UnifiedActivityTimeline } from "@/components/unified-activity-timeline";
import { TouchpointBar } from "@/components/touchpoint-bar";
import { ContactGroupsEditor } from "@/components/contact-groups-editor";
import { cleanNoteBody, noteSourceLabel } from "@/lib/notes";
import { highlightMatch } from "@/lib/highlight";

export function ActTabWorkstation({
  contact,
  defaultTab = "notes",
}: {
  contact: ContactDetail;
  defaultTab?: string;
}) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [searchTerm, setSearchTerm] = useState("");

  const customEntries = Object.entries(contact.custom_fields || {});
  const publishingEntries = customEntries.filter(([k]) =>
    /issue|ad|print|circulation|tier|title|sponsor|expo|wtce/i.test(k)
  );

  // One search box drives all three content tabs (Activities, Notes,
  // History) at once, rather than each having its own - typing here
  // narrows and highlights matches everywhere that text lives, so a long-
  // history contact doesn't force tab-hopping to find one old note.
  const needle = searchTerm.trim().toLowerCase();
  const filteredNotes = contact.notes.filter(
    (n) =>
      !needle ||
      (n.body && n.body.toLowerCase().includes(needle)) ||
      (n.note_type && n.note_type.toLowerCase().includes(needle))
  );

  const filteredHistory = contact.history.filter(
    (h) =>
      !needle ||
      (h.subject && h.subject.toLowerCase().includes(needle)) ||
      (h.history_type && h.history_type.toLowerCase().includes(needle))
  );

  const filteredActivities = contact.activities.filter(
    (a) =>
      !needle ||
      (a.subject && a.subject.toLowerCase().includes(needle)) ||
      (a.activity_type && a.activity_type.toLowerCase().includes(needle))
  );

  return (
    <div className="flex flex-col gap-3">
      {/* Full-Width Sub-Workstation Tabs Ribbon */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/80 bg-muted/30 px-3 pt-1">
          <TabsList className="bg-transparent gap-1.5 p-0 h-auto flex-wrap">
            <TabsTrigger
              value="activities"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <Calendar className="size-3.5 text-blue-600" />
              <span>
                Activities (
                {needle
                  ? `${filteredNotes.length + filteredHistory.length + filteredActivities.length} of ${contact.notes.length + contact.history.length + contact.activities.length}`
                  : contact.notes.length + contact.history.length + contact.activities.length}
                )
              </span>
            </TabsTrigger>

            <TabsTrigger
              value="notes"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <FileText className="size-3.5 text-emerald-600" />
              <span>
                Notes ({needle ? `${filteredNotes.length} of ${contact.notes.length}` : contact.notes.length})
              </span>
            </TabsTrigger>

            <TabsTrigger
              value="history"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <Clock className="size-3.5 text-amber-600" />
              <span>
                History ({needle ? `${filteredHistory.length} of ${contact.history.length}` : contact.history.length})
              </span>
            </TabsTrigger>

            <TabsTrigger
              value="groups"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <UsersRound className="size-3.5 text-purple-600" />
              <span>Groups ({contact.groups.length})</span>
            </TabsTrigger>

            <TabsTrigger
              value="commercial"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <BookOpen className="size-3.5 text-primary" />
              <span>Magazine &amp; Issues</span>
            </TabsTrigger>

            <TabsTrigger
              value="fields"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <Layers className="size-3.5 text-muted-foreground" />
              <span>User Fields ({customEntries.length})</span>
            </TabsTrigger>
          </TabsList>

          {/* Searches Activities, Notes and History together (see `needle`
              above) - not scoped to whichever tab happens to be open, so a
              match still shows up in the tab counts even before you switch
              to it. */}
          <div className="flex items-center gap-2 pb-1.5">
            <div className="relative w-56 sm:w-72">
              <Search className="absolute left-2 top-2 size-3 text-muted-foreground" />
              <Input
                placeholder="Search this contact's notes & history..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-7 pl-7 text-xs"
              />
            </div>
          </div>
        </div>

        {/* TAB 1: Activities (Combined Touchpoints / Logger) */}
        <TabsContent value="activities" className="mt-4 flex flex-col gap-4">
          <TouchpointBar contactId={contact.id} contactName={contact.full_name || contact.first_name || "Contact"} sourceDb={contact.source_db} />
          <UnifiedActivityTimeline
            notes={contact.notes}
            history={contact.history}
            activities={contact.activities}
            searchTerm={searchTerm}
          />
        </TabsContent>

        {/* TAB 2: Notes (Act! Table & Content View) */}
        <TabsContent value="notes" className="mt-4 flex flex-col gap-4">
          <TouchpointBar contactId={contact.id} contactName={contact.full_name || contact.first_name || "Contact"} sourceDb={contact.source_db} />

          <Card className="overflow-hidden border border-border">
            <div className="bg-muted/40 px-4 py-2 border-b flex items-center justify-between text-xs font-semibold text-muted-foreground">
              <span>Date / Time</span>
              <span>Type</span>
              <span className="w-1/2">Content</span>
              <span>Source</span>
            </div>

            <CardContent className="p-0 divide-y divide-border/60 text-xs">
              {filteredNotes.length > 0 ? (
                filteredNotes.map((n) => {
                  const body = cleanNoteBody(n.body);
                  return (
                    <div
                      key={n.id}
                      className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 p-3.5 hover:bg-muted/20 transition-colors"
                    >
                      <time className="w-28 shrink-0 text-muted-foreground font-mono text-[11px]">
                        {n.act_created_at
                          ? new Date(n.act_created_at).toLocaleDateString("en-GB", {
                              day: "2-digit",
                              month: "short",
                              year: "numeric",
                            })
                          : "—"}
                      </time>
                      <div className="w-24 shrink-0">
                        <Badge variant="outline" className="text-[10px] py-0 px-1.5">
                          {highlightMatch(n.note_type || "Note", searchTerm)}
                        </Badge>
                      </div>
                      <p className="flex-1 text-foreground leading-relaxed whitespace-pre-wrap">
                        {body ? highlightMatch(body, searchTerm) : "No content."}
                      </p>
                      <span className="text-[10px] text-muted-foreground shrink-0 uppercase tracking-wider">
                        {noteSourceLabel(n)}
                      </span>
                    </div>
                  );
                })
              ) : (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {needle ? `Nothing in Notes matches "${searchTerm.trim()}".` : "No notes on file."}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: History (Audit Log) */}
        <TabsContent value="history" className="mt-4 flex flex-col gap-4">
          <Card className="overflow-hidden border border-border">
            <div className="bg-muted/40 px-4 py-2 border-b flex items-center justify-between text-xs font-semibold text-muted-foreground">
              <span>Date</span>
              <span>History Type</span>
              <span className="w-2/3">Subject / Summary</span>
            </div>

            <CardContent className="p-0 divide-y divide-border/60 text-xs">
              {filteredHistory.length > 0 ? (
                filteredHistory.map((h) => (
                  <div
                    key={h.id}
                    className="flex items-center justify-between gap-3 p-3 hover:bg-muted/20 transition-colors"
                  >
                    <time className="w-28 shrink-0 text-muted-foreground font-mono text-[11px]">
                      {new Date(h.occurred_at).toLocaleDateString("en-GB", {
                        day: "2-digit",
                        month: "short",
                        year: "numeric",
                      })}
                    </time>
                    <div className="w-32 shrink-0">
                      <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
                        {highlightMatch(h.history_type, searchTerm)}
                      </Badge>
                    </div>
                    <span className="flex-1 font-medium text-foreground">
                      {h.subject ? highlightMatch(h.subject, searchTerm) : "Event logged"}
                    </span>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-sm text-muted-foreground">
                  {needle ? `Nothing in History matches "${searchTerm.trim()}".` : "No history records on file."}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 4: Groups */}
        <TabsContent value="groups" className="mt-4">
          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-foreground">
                  Assigned Groups &amp; Distribution Lists
                </h3>
                <p className="text-xs text-muted-foreground">
                  Circulation segments, awards panels, and advertising rosters
                </p>
              </div>
            </div>
            <ContactGroupsEditor contactId={contact.id} groups={contact.groups} />
          </Card>
        </TabsContent>

        {/* TAB 5: Magazine & Commercial */}
        <TabsContent value="commercial" className="mt-4">
          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-4 border-b pb-3">
              <div>
                <h3 className="text-sm font-bold text-foreground">
                  Commercial Affiliation &amp; Issue Inserts
                </h3>
                <p className="text-xs text-muted-foreground">
                  Print circulation copies, media kit requests, and magazine features
                </p>
              </div>
              <Badge variant="outline" className="font-semibold text-xs text-primary">
                BMI Media Operations
              </Badge>
            </div>

            {publishingEntries.length > 0 ? (
              <div className="grid gap-3 sm:grid-cols-2 text-xs">
                {publishingEntries.map(([k, v]) => (
                  <div
                    key={k}
                    className="rounded-md border border-border/80 bg-muted/30 p-3"
                  >
                    <span className="text-muted-foreground block text-[11px] mb-1">
                      {k}
                    </span>
                    <span className="font-semibold text-foreground text-sm">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground text-xs">
                No active magazine advertising inserts or issue features recorded for this contact.
              </div>
            )}
          </Card>
        </TabsContent>

        {/* TAB 6: User Fields / Archive */}
        <TabsContent value="fields" className="mt-4">
          <Card className="p-5 border border-border">
            <div className="flex items-center justify-between mb-3 border-b pb-2">
              <h3 className="text-sm font-bold text-foreground">
                Act! Database Custom Fields (user1 .. user15)
              </h3>
              <span className="text-xs text-muted-foreground font-mono">
                {customEntries.length} total attributes
              </span>
            </div>

            {customEntries.length > 0 ? (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 text-xs">
                {customEntries.map(([key, value]) => (
                  <div
                    key={key}
                    className="flex flex-col justify-center rounded border border-border/60 bg-muted/20 p-2.5"
                  >
                    <span className="text-[10px] font-mono text-muted-foreground">
                      {key}
                    </span>
                    <span className="font-medium text-foreground mt-0.5 truncate">
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-muted-foreground">
                No custom fields recorded.
              </div>
            )}
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
