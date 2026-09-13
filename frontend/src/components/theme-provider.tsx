"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";

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
