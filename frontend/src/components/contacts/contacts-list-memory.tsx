"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const LOOKUP_KEY = "bmi.contacts.last-lookup";
export const LAST_OPENED_KEY = "bmi.contacts.last-opened";

function read(key: string): string | null {
  try { return window.localStorage.getItem(key); } catch { return null; }
}
function write(key: string, value: string | null) {
  try { if (value === null) window.localStorage.removeItem(key); else window.localStorage.setItem(key, value); } catch { /* private window */ }
}

/** Coming back to Contacts shows the list as you left it (Craig, feedback #13): the same search, sort and page,
 * scrolled to the contact you last opened, which is briefly highlighted. "Clear lookup" (?fresh=1) starts again. */
export function ContactsListMemory() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  useEffect(() => {
    const qs = new URLSearchParams(params.toString());
    if (qs.get("fresh")) {
      write(LOOKUP_KEY, null);
      write(LAST_OPENED_KEY, null);
      qs.delete("fresh");
      router.replace(qs.size ? `${pathname}?${qs}` : pathname, { scroll: false });
      return;
    }
    if (!qs.size) {
      const saved = read(LOOKUP_KEY);
      if (saved) {
        router.replace(`${pathname}?${saved}`, { scroll: false });
        return;
      }
    } else {
      write(LOOKUP_KEY, qs.toString());
    }
    const last = read(LAST_OPENED_KEY);
    if (!last) return;
    const row = document.querySelector<HTMLElement>(`[data-contact-id="${CSS.escape(last)}"]`);
    if (!row) return;
    // Only move the page if that contact is out of view, and as little as possible, so nothing jumps under your mouse.
    const r = row.getBoundingClientRect();
    if (r.top < 0 || r.bottom > window.innerHeight) row.scrollIntoView({ block: "nearest" });
    row.dataset.lastOpened = "true";
    const t = setTimeout(() => { delete row.dataset.lastOpened; }, 4000);
    return () => clearTimeout(t);
  }, [params, pathname, router]);

  return null;
}

/** On a contact's page: remember it, so the Contacts list can come back to it. */
export function RememberOpenedContact({ id }: { id: string }) {
  useEffect(() => { write(LAST_OPENED_KEY, id); }, [id]);
  return null;
}
