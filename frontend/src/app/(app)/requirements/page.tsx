import Link from "next/link";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { automations, type RequirementStage } from "@/lib/requirements-data";

const STAGE_LABELS: Record<Exclude<RequirementStage, "overview">, string> = {
  foundation: "Foundation",
  stage1: "Stage 1 — Clean Foundation",
  stage2: "Stage 2 — Living Memory + AI Chat",
  stage3: "Stage 3 — Daily Engine",
  stage4: "Stage 4 — Reporting & Leadership",
};

const STAGE_ORDER: Exclude<RequirementStage, "overview">[] = [
  "foundation",
  "stage1",
  "stage2",
  "stage3",
  "stage4",
];

export default function RequirementsPage() {
  const overviewItems = automations.filter(
    (a) => a.stage === "overview" && a.id !== "overview"
  );

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-8 p-8">
      <div>
        <h1 className="text-2xl font-semibold">Requirements &amp; questions</h1>
        <p className="mt-1 text-muted-foreground">
          Every automation from the build spec, with what it does, what we need
          from BMI to build it, and the questions to ask before we start.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {overviewItems.map((item) => (
          <Link key={item.id} href={`/requirements/${item.id}`}>
            <Card className="h-full transition-colors hover:bg-muted/50">
              <CardHeader>
                <CardTitle className="text-base">{item.name}</CardTitle>
                <CardDescription>{item.whatItDoes}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      {STAGE_ORDER.map((stage) => {
        const items = automations.filter((a) => a.stage === stage);
        if (items.length === 0) return null;
        return (
          <div key={stage} className="flex flex-col gap-3">
            <h2 className="text-lg font-medium">{STAGE_LABELS[stage]}</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {items.map((item) => (
                <Link key={item.id} href={`/requirements/${item.id}`}>
                  <Card className="h-full transition-colors hover:bg-muted/50">
                    <CardHeader>
                      <div className="flex items-center justify-between gap-2">
                        <CardTitle className="text-base">
                          {item.code ? `${item.code} — ${item.name}` : item.name}
                        </CardTitle>
                        {item.effort && (
                          <Badge variant="secondary" className="shrink-0">
                            {item.effort.split("·")[0].trim()}
                          </Badge>
                        )}
                      </div>
                      <CardDescription className="line-clamp-2">
                        {item.whatItDoes}
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
