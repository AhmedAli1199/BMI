import { Suspense } from "react";
import { LoginForm } from "./login-form";

export default function LoginPage() {
  return (
    <div className="flex min-h-svh flex-1 items-center justify-center bg-background p-4 sm:p-8">
      <Suspense>
        <LoginForm />
      </Suspense>
    </div>
  );
}
