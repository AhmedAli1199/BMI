import Link from "next/link";
import { Mail, MapPin, Phone } from "lucide-react";
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
import { cleanNoteBody } from "@/lib/notes";
import { sourceLabel } from "@/lib/sources";
import { EntityAvatar } from "@/components/entity-avatar";

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
        <div className="flex items-start gap-4">
          <EntityAvatar name={name} className="mt-0.5 size-11 text-sm" />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">{name}</h1>
              <Badge variant="secondary">{sourceLabel(contact.source_db)}</Badge>
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
          <CardContent className="flex flex-col gap-2.5 text-sm">
            {contact.emails.map((e) => (
              <div key={e.id} className="flex items-start gap-2.5">
                <Mail className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div>
                  <div>{e.address}</div>
                  <div className="text-xs text-muted-foreground">{e.type_label || "Email"}</div>
                </div>
              </div>
            ))}
            {contact.phones.map((p) => (
              <div key={p.id} className="flex items-start gap-2.5">
                <Phone className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div>
                  <div>{p.number}</div>
                  <div className="text-xs text-muted-foreground">{p.type_label || "Phone"}</div>
                </div>
              </div>
            ))}
            {contact.addresses.map((a) => (
              <div key={a.id} className="flex items-start gap-2.5">
                <MapPin className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div>
                  <div>{[a.line1, a.city, a.state, a.postal_code, a.country].filter(Boolean).join(", ")}</div>
                  <div className="text-xs text-muted-foreground">{a.type_label || "Address"}</div>
                </div>
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

      {(contact.category ||
        contact.referred_by ||
        contact.birthdate ||
        contact.last_meet_date ||
        contact.last_reach_date ||
        contact.last_attempt_date ||
        contact.last_letter_date) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Status &amp; activity</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
            {contact.category && (
              <div>
                <div className="text-xs text-muted-foreground">ID / Status</div>
                <div>{contact.category}</div>
              </div>
            )}
            {contact.referred_by && (
              <div>
                <div className="text-xs text-muted-foreground">Referred by</div>
                <div>{contact.referred_by}</div>
              </div>
            )}
            {contact.birthdate && (
              <div>
                <div className="text-xs text-muted-foreground">Birthdate</div>
                <div>{new Date(contact.birthdate).toLocaleDateString()}</div>
              </div>
            )}
            {contact.last_meet_date && (
              <div>
                <div className="text-xs text-muted-foreground">Last meeting</div>
                <div>{new Date(contact.last_meet_date).toLocaleDateString()}</div>
              </div>
            )}
            {contact.last_reach_date && (
              <div>
                <div className="text-xs text-muted-foreground">Last call reach</div>
                <div>{new Date(contact.last_reach_date).toLocaleDateString()}</div>
              </div>
            )}
            {contact.last_attempt_date && (
              <div>
                <div className="text-xs text-muted-foreground">Last call attempt</div>
                <div>{new Date(contact.last_attempt_date).toLocaleDateString()}</div>
              </div>
            )}
            {contact.last_letter_date && (
              <div>
                <div className="text-xs text-muted-foreground">Last letter sent</div>
                <div>{new Date(contact.last_letter_date).toLocaleDateString()}</div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
                <p className="whitespace-pre-wrap">{cleanNoteBody(n.body) || "No content."}</p>
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
