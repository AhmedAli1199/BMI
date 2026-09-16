import { readFile } from "node:fs/promises";
import path from "node:path";
import { notFound } from "next/navigation";
import { getSession } from "@/lib/session";
import { isAdmin } from "@/lib/access";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Deliberately not linked from anywhere in the app (no sidebar entry) -
 * reachable only by an admin who already knows this exact URL. Source
 * text lives outside public/ so it's never served as a static asset
 * either. See the sibling vault-9f2kq7/requirements page for the
 * restructured version - same access model, also unlinked. */
export default async function BuildSpecArchivePage() {
  const session = await getSession();
  if (!isAdmin(session)) notFound();

  const filePath = path.join(process.cwd(), "private", "build-spec.txt");
  const content = await readFile(filePath, "utf-8");

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-8">
      <div>
        <h1 className="text-2xl font-semibold">Original build spec (raw)</h1>
        <p className="mt-1 text-muted-foreground">
          The original n8n/Act! build specification as delivered. Kept verbatim
          for reference. Our actual build uses FastAPI + Next.js + Postgres, not
          n8n, but the goals, edge cases and acceptance criteria described here
          still apply.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            BMI Sales &amp; Data Brain: MVP (Option 2) Build Spec
          </CardTitle>
          <CardDescription>Prepared by Cybix · 9 July 2026</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="max-h-[70vh] overflow-y-auto rounded-md border bg-muted/30 p-4">
            <pre className="text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {content}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
