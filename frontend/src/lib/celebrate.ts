/** A small cheer from the Brain after something worth it (a booking confirmed, a confirmation sent, the Review Queue
 * cleared). Shown by BrainCoach, only if the person has celebrations switched on (Settings > The Brain). Keep the
 * message plain and about the work - never about money or the client. */
export function celebrate(message: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("brain:celebrate", { detail: { message } }));
}
