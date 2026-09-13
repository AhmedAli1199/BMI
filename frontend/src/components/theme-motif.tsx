"use client";

import { useTheme } from "next-themes";

/** The literal "sun, rays, moon" artifact requested - a small themed icon
 * rendered next to the brand wordmark. Same three themes as everywhere
 * else; colors come from --nav-accent/--nav-accent-2 (globals.css) so it
 * always matches whatever gradient the sidebar is currently wearing.
 */
export function ThemeMotif({ className }: { className?: string }) {
  const { theme } = useTheme();

  if (theme === "evening") {
    return (
      <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
        <defs>
          <clipPath id="horizon"><rect x="0" y="20" width="40" height="20" /></clipPath>
        </defs>
        <circle cx="20" cy="20" r="10" fill="currentColor" clipPath="url(#horizon)" />
        <line x1="4" y1="30" x2="36" y2="30" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
        <line x1="9" y1="34" x2="31" y2="34" stroke="currentColor" strokeWidth="1.5" opacity="0.35" className="accent-2" />
      </svg>
    );
  }

  if (theme === "night") {
    return (
      <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
        <path
          d="M25 6a14 14 0 1 0 9 24.8A11 11 0 0 1 25 6Z"
          fill="currentColor"
        />
        <circle cx="10" cy="12" r="1.2" fill="currentColor" className="accent-2" opacity="0.8" />
        <circle cx="6" cy="22" r="0.9" fill="currentColor" className="accent-2" opacity="0.6" />
        <circle cx="14" cy="28" r="1" fill="currentColor" className="accent-2" opacity="0.7" />
      </svg>
    );
  }

  // morning (default)
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden="true">
      <circle cx="20" cy="20" r="8" fill="currentColor" />
      {Array.from({ length: 8 }).map((_, i) => {
        const angle = (i * Math.PI) / 4;
        const x1 = 20 + Math.cos(angle) * 12;
        const y1 = 20 + Math.sin(angle) * 12;
        const x2 = 20 + Math.cos(angle) * 17;
        const y2 = 20 + Math.sin(angle) * 17;
        return (
          <line
            key={i}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            opacity={i % 2 === 0 ? 0.9 : 0.5}
            className={i % 2 === 0 ? undefined : "accent-2"}
          />
        );
      })}
    </svg>
  );
}
