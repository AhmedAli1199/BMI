"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmailFromTemplate } from "@/components/mail-merge/email-from-template";

/** "Email from a template" for one contact (contact page). */
export function EmailTemplateButton({ contact }: { contact: { id: string; label: string } }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="outline" size="sm" className="gap-1.5" onClick={() => setOpen(true)}><FileText className="size-3.5" /> Email from a template</Button>
      {open && <EmailFromTemplate open={open} onOpenChange={setOpen} contact={contact} />}
    </>
  );
}
