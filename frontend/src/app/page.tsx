import { ApiStatus } from "@/components/api-status";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
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
    </div>
  );
}
