/** What a person sees when something fails. Our own API messages are plain sentences written for users
 * and are shown as they are; anything that looks technical (framework errors, status codes, stack traces,
 * database or network wording) is replaced by the plain fallback - users never see internal errors. */
const TECHNICAL = [
  /minified react/i, /react\.dev\/errors/i, /\berror #\d+/i, /server components?/i, /server action/i, /digest/i,
  /backend request/i, /\bfetch failed\b/i, /network ?error/i, /failed to fetch/i, /econn|etimedout|enotfound/i,
  /traceback/i, /exception/i, /sqlalchemy|psycopg|postgres|sql\b/i, /\bundefined\b|\bnull\b|nan\b/i,
  /typeerror|referenceerror|syntaxerror|rangeerror/i, /\bat .+\(.+:\d+/i, /https?:\/\//i, /[{}<>[\]]/,
  /\b(status|http) ?\d{3}\b/i, /\b[45]\d\d\b.*(error|failed)/i, /graph \d{3}|xero rejected|token/i, /json/i, /uuid|validation error/i,
];

export function isFriendly(message: string): boolean {
  const m = message.trim();
  return m.length > 0 && m.length <= 300 && !TECHNICAL.some((re) => re.test(m));
}

export function friendlyError(e: unknown, fallback: string): string {
  const m = e instanceof Error ? e.message : typeof e === "string" ? e : "";
  return m && isFriendly(m) ? m : fallback;
}
