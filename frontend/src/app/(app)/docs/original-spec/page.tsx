import { readFile } from "node:fs/promises";
import path from "node:path";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function OriginalSpecPage() {
  const filePath = path.join(process.cwd(), "public", "build-spec.txt");
  const content = await readFile(filePath, "utf-8");

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 p-8">
      <div>
        <h1 className="text-2xl font-semibold">Original build spec (raw)</h1>
        <p className="mt-1 text-muted-foreground">
          The original n8n/Act! build specification as delivered. Kept verbatim
          for reference — our actual build uses FastAPI + Next.js + Postgres, not
          n8n, but the goals, edge cases and acceptance criteria described here
          still apply. See{" "}
          <Link href="/requirements" className="underline underline-offset-2">
            Requirements &amp; questions
          </Link>{" "}
          for the restructured version.
        </p>
      </div>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            BMI Sales &amp; Data Brain — MVP (Option 2) Build Spec
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
