import Link from "next/link";
import { notFound } from "next/navigation";
import { getSession } from "@/lib/session";
import { isAdmin } from "@/lib/access";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { automations } from "@/lib/requirements-data";

function Section({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
        {title}
      </h3>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2 text-sm leading-relaxed">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-foreground/50" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function generateStaticParams() {
  return automations.map((a) => ({ id: a.id }));
}

export default async function AutomationDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const session = await getSession();
  if (!isAdmin(session)) notFound();

  const { id } = await params;
  const automation = automations.find((a) => a.id === id);
  if (!automation) notFound();

  const dependsOnItems = automation.dependsOn
    .map((depId) => automations.find((a) => a.id === depId))
    .filter((a): a is NonNullable<typeof a> => Boolean(a));

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 p-8">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          {automation.code && <Badge variant="secondary">{automation.code}</Badge>}
          {automation.effort && <Badge variant="outline">{automation.effort}</Badge>}
        </div>
        <h1 className="text-2xl font-semibold">{automation.name}</h1>
        <p className="text-muted-foreground">{automation.whatItDoes}</p>
      </div>

      {automation.howItWorks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">How it works</CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="flex flex-col gap-2">
              {automation.howItWorks.map((step, i) => (
                <li key={i} className="flex gap-3 text-sm leading-relaxed">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="flex flex-col gap-6 pt-6">
          <Section title="Systems & data involved" items={automation.systemsAndData} />
          <Separator />
          <Section
            title="Credentials / access we need"
            items={automation.requirements}
          />
          <Separator />
          <Section
            title="Questions"
            items={automation.questionsForClient}
          />
          <Separator />
          <Section title="Edge cases to handle" items={automation.edgeCases} />
        </CardContent>
      </Card>

      {dependsOnItems.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Depends on</CardTitle>
            <CardDescription>
              These need to exist (or be built first) before this automation can
              work.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {dependsOnItems.map((dep) => (
              <Link key={dep.id} href={`/vault-9f2kq7/requirements/${dep.id}`}>
                <Badge variant="secondary" className="cursor-pointer">
                  {dep.code ?? dep.name}
                </Badge>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
