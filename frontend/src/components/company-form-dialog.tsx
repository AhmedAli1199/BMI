"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Plus, Pencil } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { createCompany, updateCompany } from "@/lib/actions";

type Existing = {
  id: string;
  name: string;
  industry: string | null;
  category: string | null;
  website: string | null;
};

export function CompanyFormDialog({ existing }: { existing?: Existing }) {
  const [open, setOpen] = useState(false);
  const [pending, startTransition] = useTransition();
  const router = useRouter();

  const [name, setName] = useState(existing?.name ?? "");
  const [industry, setIndustry] = useState(existing?.industry ?? "");
  const [category, setCategory] = useState(existing?.category ?? "");
  const [website, setWebsite] = useState(existing?.website ?? "");

  function submit() {
    startTransition(async () => {
      try {
        if (existing) {
          await updateCompany(existing.id, { name, industry, category, website });
          toast.success("Company updated");
          setOpen(false);
          router.refresh();
        } else {
          const created = await createCompany({ name, industry, category, website });
          toast.success("Company added");
          setOpen(false);
          router.push(`/companies/${created.id}`);
        }
      } catch {
        toast.error(existing ? "Couldn't update company" : "Couldn't add company");
      }
    });
  }

  return (
    <>
      {existing ? (
        <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
          <Pencil className="size-4" />
          Edit
        </Button>
      ) : (
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus className="size-4" />
          Add company
        </Button>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{existing ? "Edit company" : "Add company"}</DialogTitle>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cof-name">Name</Label>
              <Input id="cof-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cof-industry">Industry</Label>
                <Input id="cof-industry" value={industry} onChange={(e) => setIndustry(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="cof-category">Category</Label>
                <Input id="cof-category" value={category} onChange={(e) => setCategory(e.target.value)} />
              </div>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="cof-website">Website</Label>
              <Input id="cof-website" value={website} onChange={(e) => setWebsite(e.target.value)} />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
            <Button onClick={submit} disabled={pending || !name.trim()}>
              {pending ? "Saving…" : existing ? "Save changes" : "Add company"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
