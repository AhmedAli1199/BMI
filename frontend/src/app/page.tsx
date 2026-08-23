import { cookies } from "next/headers";
import { ApiStatus } from "@/components/api-status";
import { LogoutButton } from "@/components/logout-button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SESSION_COOKIE, verifySessionToken } from "@/lib/session";

export default async function Home() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const session = token ? await verifySessionToken(token) : null;

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 bg-zinc-50 p-8 dark:bg-black">
      <Card className="w-full max-w-md">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>BMI Sales Brain</CardTitle>
            <ApiStatus />
          </div>
          <CardDescription>
            FastAPI + Next.js + Postgres, deployed on Dokploy.
          </CardDescription>
        </CardHeader>
      </Card>
      {session && (
        <Card className="w-full max-w-md">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base">{session.name}</CardTitle>
                <CardDescription>{session.email}</CardDescription>
              </div>
              <LogoutButton />
            </div>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}
