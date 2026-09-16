"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";

// React 19 development mode warning suppression for next-themes script tag injection
if (typeof window !== "undefined" && process.env.NODE_ENV === "development") {
  const orig = console.error;
  console.error = (...args: unknown[]) => {
    if (
      typeof args[0] === "string" &&
      args[0].includes("Encountered a script tag while rendering React component")
    ) {
      return;
    }
    orig.apply(console, args);
  };
}

/** Three named themes (morning/evening/night), not a light/dark pair -
 * see globals.css for the token sets and layout.tsx for how this is wired
 * up. Preference lives in localStorage (next-themes' default) - no backend
 * setting, on purpose, per the decision this was built under.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <NextThemesProvider
      attribute="data-theme"
      themes={["morning", "evening", "night"]}
      defaultTheme="morning"
      enableSystem={false}
      disableTransitionOnChange
    >
      {children}
    </NextThemesProvider>
  );
}
