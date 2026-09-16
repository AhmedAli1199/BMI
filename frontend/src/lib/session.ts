import { cookies } from "next/headers";
import { SignJWT, jwtVerify } from "jose";

export const SESSION_COOKIE = "bmi_session";

export type SessionAccess = { source_db: string; group_id: string | null; group_name: string | null };

export type SessionPayload = {
  sub: string;
  email: string;
  name: string;
  role: string;
  // Which database(s) - optionally scoped to one group's subtree within
  // it - this session may see. Meaningless for role === "admin" (an
  // admin's access is implicit and unrestricted - see backend/app/roles.py)
  // and may be empty there even though they can see everything.
  access: SessionAccess[];
};

function getSecret() {
  const secret = process.env.SESSION_SECRET;
  if (!secret) throw new Error("SESSION_SECRET is not set");
  return new TextEncoder().encode(secret);
}

export async function createSessionToken(payload: SessionPayload): Promise<string> {
  return new SignJWT({ ...payload })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(getSecret());
}

export async function verifySessionToken(
  token: string
): Promise<SessionPayload | null> {
  try {
    const { payload } = await jwtVerify(token, getSecret());
    return payload as unknown as SessionPayload;
  } catch {
    return null;
  }
}

/** Reads + verifies the session cookie for the current request, falling
 * back to a fixed local-dev identity outside production (or with
 * LOCAL_BYPASS=true) so the app is usable without running the login flow
 * locally. Shared by the app layout and any page that needs to know who's
 * signed in (e.g. /settings, to load/save that user's own preferences) -
 * keep this the one place that bypass logic lives. Note the bypass
 * identity's `sub` ("local-dev") is not a real user id; backend routes
 * keyed by user id treat a non-UUID id as "no user" and fall back to
 * defaults rather than erroring. */
export async function getSession(): Promise<SessionPayload | null> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  const verified = token ? await verifySessionToken(token) : null;
  return (
    verified ??
    (process.env.NODE_ENV !== "production" || process.env.LOCAL_BYPASS === "true"
      ? {
          sub: "local-dev",
          email: "publisher@bmipublishing.co.uk",
          name: "Editorial Team",
          role: "admin",
          access: [],
        }
      : null)
  );
}
