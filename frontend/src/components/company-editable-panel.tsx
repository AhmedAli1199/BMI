"use client";

import { useState, useTransition } from "react";
import { Pencil, X } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EntityAvatar } from "@/components/entity-avatar";
import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteCompany, updateCompany } from "@/lib/actions";
import { sourceLabel } from "@/lib/sources";
import type { CompanyDetail } from "@/lib/types";

/** Same in-place editing approach as ContactEditablePanel - see its
 * docstring for why this replaced a separate edit modal. */
export function CompanyEditablePanel({ company }: { company: CompanyDetail }) {
  const [editing, setEditing] = useState(false);
  const [pending, startTransition] = useTransition();

  const [name, setName] = useState(company.name);
  const [industry, setIndustry] = useState(company.industry ?? "");
  const [category, setCategory] = useState(company.category ?? "");
  const [territory, setTerritory] = useState(company.territory ?? "");
  const [region, setRegion] = useState(company.region ?? "");
  const [website, setWebsite] = useState(company.website ?? "");
  const [numEmployees, setNumEmployees] = useState(
    company.num_employees != null ? String(company.num_employees) : ""
  );

  function cancel() {
    setName(company.name);
    setIndustry(company.industry ?? "");
    setCategory(company.category ?? "");
    setTerritory(company.territory ?? "");
    setRegion(company.region ?? "");
    setWebsite(company.website ?? "");
    setNumEmployees(company.num_employees != null ? String(company.num_employees) : "");
    setEditing(false);
  }

  function save() {
    startTransition(async () => {
      try {
        await updateCompany(company.id, {
          name,
          industry,
          category,
          territory,
          region,
          website,
          num_employees: numEmployees ? Number(numEmployees) : undefined,
        });
        toast.success("Company updated");
        setEditing(false);
      } catch {
        toast.error("Couldn't save changes");
      }
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <EntityAvatar name={company.name} square className="mt-0.5 size-11 text-sm" />
          <div className="flex flex-col gap-1.5">
            {editing ? (
              <Input
                className="h-8 w-64 text-base font-semibold"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            ) : (
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-semibold">{company.name}</h1>
                <Badge variant="secondary">{sourceLabel(company.source_db)}</Badge>
              </div>
            )}

            {editing ? (
              <div className="flex flex-wrap gap-2">
                <Input
                  className="h-8 w-40"
                  placeholder="Industry"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                />
                <Input
                  className="h-8 w-40"
                  placeholder="Category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
                <Input
                  className="h-8 w-40"
                  placeholder="Territory"
                  value={territory}
                  onChange={(e) => setTerritory(e.target.value)}
                />
                <Input
                  className="h-8 w-40"
                  placeholder="Region"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                />
              </div>
            ) : (
              (company.industry || company.category) && (
                <p className="text-sm text-muted-foreground">
                  {company.industry}
                  {company.industry && company.category ? " · " : ""}
                  {company.category}
                </p>
              )
            )}

            {editing ? (
              <Input
                className="h-8 w-64"
                placeholder="Website"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
              />
            ) : (
              company.website && (
                <a
                  href={company.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm hover:underline"
                >
                  {company.website}
                </a>
              )
            )}
          </div>
        </div>

        <div className="flex shrink-0 gap-2">
          {editing ? (
            <>
              <Button variant="outline" size="sm" onClick={cancel} disabled={pending}>
                <X className="size-4" />
                Cancel
              </Button>
              <Button size="sm" onClick={save} disabled={pending}>
                {pending ? "Saving…" : "Save"}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                <Pencil className="size-4" />
                Edit
              </Button>
              <DeleteEntityButton
                entityLabel={company.name}
                id={company.id}
                action={deleteCompany}
                redirectTo="/companies"
              />
            </>
          )}
        </div>
      </div>

      {editing && (
        <div className="flex flex-col gap-1.5">
          <Label className="text-xs text-muted-foreground">Employees</Label>
          <Input
            className="h-8 w-32"
            type="number"
            min={0}
            value={numEmployees}
            onChange={(e) => setNumEmployees(e.target.value)}
          />
        </div>
      )}
    </div>
  );
}
