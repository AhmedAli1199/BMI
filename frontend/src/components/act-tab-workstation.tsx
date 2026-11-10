"use client";

import { useState } from "react";
import { FileText, Search, UsersRound } from "lucide-react";
import type { ContactDetail } from "@/lib/types";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { UnifiedActivityTimeline } from "@/components/unified-activity-timeline";
import { TouchpointBar } from "@/components/touchpoint-bar";
import { ContactGroupsEditor } from "@/components/contact-groups-editor";
import { AddNoteInline } from "@/components/add-note-inline";

/** Below a contact's details: Notes (everything to do with them, in one list) and Groups. Their extra fields
 * from Act! now sit in the details card above, so there's nowhere else to look. */
export function ActTabWorkstation({
  contact,
  defaultTab = "notes",
}: {
  contact: ContactDetail;
  defaultTab?: string;
}) {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [searchTerm, setSearchTerm] = useState("");

  // The search box narrows and highlights the Notes list (notes, history and activities together).
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
              value="notes"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <FileText className="size-3.5 text-[var(--ok)]" />
              <span>
                Notes (
                {needle
                  ? `${filteredNotes.length + filteredHistory.length + filteredActivities.length} of ${contact.notes.length + contact.history.length + contact.activities.length}`
                  : contact.notes.length + contact.history.length + contact.activities.length}
                )
              </span>
            </TabsTrigger>

            <TabsTrigger
              value="groups"
              className="data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-2xs data-[state=active]:border-border border border-transparent rounded-md px-3 py-1.5 text-xs font-semibold cursor-pointer gap-1.5 text-muted-foreground hover:text-foreground transition-all"
            >
              <UsersRound className="size-3.5 text-[var(--chart-1)]" />
              <span>Groups ({contact.groups.length})</span>
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

        {/* Notes: everything to do with this contact in one list, newest first - notes, mail merges and
            emails, calls, meetings and history (Craig, feedback #10). */}
        <TabsContent value="notes" className="mt-4 flex flex-col gap-4">
          <AddNoteInline contactId={contact.id} />
          <TouchpointBar contactId={contact.id} contactName={contact.full_name || contact.first_name || "Contact"} sourceDb={contact.source_db} />
          <UnifiedActivityTimeline
            notes={contact.notes}
            history={contact.history}
            activities={contact.activities}
            searchTerm={searchTerm}
            entityType="contact"
            entityId={contact.id}
          />
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
            <ContactGroupsEditor contactId={contact.id} groups={contact.groups} sourceDb={contact.source_db} />
          </Card>
        </TabsContent>

      </Tabs>
    </div>
  );
}
