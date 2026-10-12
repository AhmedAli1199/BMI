/** The address the browser actually used (https://bmi.rabtaai.com), for redirects. Behind a proxy,
 * request.url is the server's own address (0.0.0.0:3000), which the browser can't reach - so use the
 * forwarded host, then the Host header, then APP_BASE_URL. */
export function publicBase(request: Request): string {
  const h = request.headers;
  const host = h.get("x-forwarded-host")?.split(",")[0].trim() || h.get("host");
  const proto = h.get("x-forwarded-proto")?.split(",")[0].trim() || (host?.startsWith("localhost") ? "http" : "https");
  if (host && !host.startsWith("0.0.0.0")) return `${proto}://${host}`;
  return process.env.APP_BASE_URL || new URL(request.url).origin;
}
