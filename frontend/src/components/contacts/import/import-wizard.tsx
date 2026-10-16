"use client";

import { useState } from "react";
import { Check } from "lucide-react";
import type { ContactImport, ImportTarget } from "@/lib/contact-tools-types";
import { ImportMapStep } from "@/components/contacts/import/import-map-step";
import { ImportReviewStep } from "@/components/contacts/import/import-review-step";
import { ImportDone } from "@/components/contacts/import/import-done";
import { PageHeader } from "@/components/page-header";

const STEPS = ["Upload", "Match columns", "Review", "Done"];

/** The four-step import: the file is already uploaded, so it opens on "Match columns". The state of the
 * import lives on the server, so a refresh or coming back later picks up where you left off. */
export function ImportWizard({ initial, targets, publications }: { initial: ContactImport; targets: ImportTarget[]; publications: { slug: string; name: string }[] }) {
  const [imp, setImp] = useState(initial);
  const [step, setStep] = useState<"map" | "review">("map");
  const current = imp.status !== "mapping" ? 3 : step === "map" ? 1 : 2;

  return (
    <>
      <PageHeader
        title={imp.filename}
        crumbs={[{ label: "Contacts", href: "/contacts" }, { label: "Import contacts", href: "/contacts/import" }]}
        below={
          <ol aria-label="Progress" className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs font-semibold">
            {STEPS.map((s, i) => (
              <li key={s} aria-current={i === current ? "step" : undefined} className={`flex items-center gap-1.5 ${i === current ? "text-foreground" : i < current ? "text-primary" : "text-muted-foreground"}`}>
                <span className={`flex size-5 items-center justify-center rounded-full text-[11px] ${i === current ? "bg-primary text-primary-foreground" : i < current ? "bg-primary/15" : "bg-muted"}`}>
                  {i < current ? <Check className="size-3" aria-hidden="true" /> : i + 1}
                </span>
                {s}
                {i < STEPS.length - 1 && <span aria-hidden="true" className="mx-1 text-muted-foreground/50">›</span>}
              </li>
            ))}
          </ol>
        }
      />

      {imp.status !== "mapping" ? (
        <ImportDone imp={imp} onChange={setImp} />
      ) : step === "map" ? (
        <ImportMapStep imp={imp} targets={targets} publications={publications} onChange={setImp} onNext={() => setStep("review")} />
      ) : (
        <ImportReviewStep imp={imp} onChange={setImp} onBack={() => setStep("map")} />
      )}
    </>
  );
}
