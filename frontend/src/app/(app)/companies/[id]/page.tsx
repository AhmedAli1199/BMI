import Link from "next/link";
import { notFound } from "next/navigation";
import { backendFetch } from "@/lib/backend";
import type { CompanyDetail } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CompanyFormDialog } from "@/components/company-form-dialog";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteCompany } from "@/lib/actions";

export default async function CompanyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let company: CompanyDetail;
  try {
    company = await backendFetch<CompanyDetail>(`/api/companies/${id}`);
  } catch {
    notFound();
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-semibold">{company.name}</h1>
            <Badge variant="secondary">{company.source_db}</Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            {company.industry}
            {company.industry && company.category ? " · " : ""}
            {company.category}
          </p>
          {company.website && (
            <a
              href={company.website}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm hover:underline"
            >
              {company.website}
            </a>
          )}
        </div>
        <div className="flex shrink-0 gap-2">
          <CompanyFormDialog existing={company} />
          <DeleteEntityButton entityLabel={company.name} id={company.id} action={deleteCompany} redirectTo="/companies" />
        </div>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Company details</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2 text-sm">
            {company.emails.map((e) => (
              <div key={e.id}>
                <span className="text-muted-foreground">{e.type_label || "Email"}: </span>
                {e.address}
              </div>
            ))}
            {company.phones.map((p) => (
              <div key={p.id}>
                <span className="text-muted-foreground">{p.type_label || "Phone"}: </span>
                {p.number}
              </div>
            ))}
            {company.addresses.map((a) => (
              <div key={a.id}>
                <span className="text-muted-foreground">{a.type_label || "Address"}: </span>
                {[a.line1, a.city, a.state, a.postal_code, a.country].filter(Boolean).join(", ")}
              </div>
            ))}
            {company.num_employees && (
              <div>
                <span className="text-muted-foreground">Employees: </span>
                {company.num_employees.toLocaleString()}
              </div>
            )}
          </CardContent>
        </Card>

        {Object.keys(company.custom_fields).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Custom fields</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              {Object.entries(company.custom_fields).map(([key, value]) => (
                <div key={key}>
                  <span className="text-muted-foreground">{key}: </span>
                  {String(value)}
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Contacts ({company.contacts.length.toLocaleString()})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {company.contacts.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Job title</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {company.contacts.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>
                      <Link href={`/contacts/${c.id}`} className="hover:underline">
                        {c.full_name || [c.first_name, c.last_name].filter(Boolean).join(" ")}
                      </Link>
                    </TableCell>
                    <TableCell>{c.job_title}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <span className="text-sm text-muted-foreground">No contacts on file.</span>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Notes</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          {company.notes.length > 0 ? (
            company.notes.map((n) => (
              <div key={n.id}>
                <div className="text-xs text-muted-foreground">{n.note_type}</div>
                <p className="whitespace-pre-wrap">{n.body}</p>
              </div>
            ))
          ) : (
            <span className="text-muted-foreground">No notes.</span>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
