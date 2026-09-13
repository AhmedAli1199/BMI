import Link from "next/link";
import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { ContactDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { ContactFormDialog } from "@/components/contact-form-dialog";
import { ContactGroupsEditor } from "@/components/contact-groups-editor";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteContact } from "@/lib/actions";

export default async function ContactDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let contact: ContactDetail;
  try {
    contact = await backendFetch<ContactDetail>(`/api/contacts/${id}`);
  } catch {
    notFound();
  }

  const name =
    contact.full_name ||
    [contact.first_name, contact.last_name].filter(Boolean).join(" ") ||
    "(no name)";

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{name}</h1>
            <Badge variant="secondary">{contact.source_db}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {contact.job_title}
            {contact.job_title && contact.department ? " · " : ""}
            {contact.department}
          </p>
          {contact.company && (
            <Link href={`/companies/${contact.company.id}`} className="text-sm hover:underline">
              {contact.company.name}
            </Link>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <ContactFormDialog
            existing={{
              id: contact.id,
              first_name: contact.first_name,
              last_name: contact.last_name,
              job_title: contact.job_title,
              department: contact.department,
              company: contact.company ? { id: contact.company.id, name: contact.company.name } : null,
            }}
          />
          <DeleteEntityButton entityLabel={name} id={contact.id} action={deleteContact} redirectTo="/contacts" />
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Contact details</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            {contact.emails.map((e) => (
              <div key={e.id}>
                <span className="text-muted-foreground">{e.type_label || "Email"}: </span>
                {e.address}
              </div>
            ))}
            {contact.phones.map((p) => (
              <div key={p.id}>
                <span className="text-muted-foreground">{p.type_label || "Phone"}: </span>
                {p.number}
              </div>
            ))}
            {contact.addresses.map((a) => (
              <div key={a.id}>
                <span className="text-muted-foreground">{a.type_label || "Address"}: </span>
                {[a.line1, a.city, a.state, a.postal_code, a.country].filter(Boolean).join(", ")}
              </div>
            ))}
            {contact.emails.length === 0 && contact.phones.length === 0 && contact.addresses.length === 0 && (
              <span className="text-muted-foreground">No contact details on file.</span>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Groups</CardTitle>
          </CardHeader>
          <CardContent>
            <ContactGroupsEditor contactId={contact.id} groups={contact.groups} />
          </CardContent>
        </Card>
      </div>

      {Object.keys(contact.custom_fields).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Custom fields</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
            {Object.entries(contact.custom_fields).map(([key, value]) => (
              <div key={key}>
                <span className="text-muted-foreground">{key}: </span>
                {String(value)}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notes</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          {contact.notes.length > 0 ? (
            contact.notes.map((n) => (
              <div key={n.id}>
                <div className="text-xs text-muted-foreground">
                  {n.note_type} · {n.act_created_at ? new Date(n.act_created_at).toLocaleDateString() : ""}
                </div>
                <p className="whitespace-pre-wrap">{n.body}</p>
                <Separator className="mt-3" />
              </div>
            ))
          ) : (
            <span className="text-muted-foreground">No notes.</span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">History</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          {contact.history.length > 0 ? (
            contact.history.map((h) => (
              <div key={h.id} className="flex items-center justify-between">
                <div>
                  <Badge variant="outline" className="mr-2">
                    {h.history_type}
                  </Badge>
                  {h.subject}
                </div>
                <span className="text-xs text-muted-foreground">
                  {new Date(h.occurred_at).toLocaleDateString()}
                </span>
              </div>
            ))
          ) : (
            <span className="text-muted-foreground">No history.</span>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
