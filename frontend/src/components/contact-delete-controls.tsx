"use client";

import { DeleteEntityButton } from "@/components/delete-entity-button";
import { deleteContact } from "@/lib/actions";
import { removeRecent } from "@/lib/recent-adds";

async function deleteAndForget(id: string) {
  await deleteContact(id);
  removeRecent("contact", id);
}

/** Deleting a contact completely (Craig, feedback #8). Anyone who can see the contact's database can delete it,
 * as in Act!, after a confirmation that says exactly what goes with it. */
export function ContactDeleteControls({ contactId, name }: { contactId: string; name: string }) {
  return (
    <DeleteEntityButton
      entityLabel={name}
      id={contactId}
      action={deleteAndForget}
      redirectTo="/contacts"
      className="h-7 gap-1.5 text-xs font-medium"
      description={`This removes ${name} from BMI Brain for good, with their email addresses, phone numbers, addresses, notes, history and group memberships. Their bookings, activities and deals are kept, just no longer linked to them. This can't be undone. If they've only left their company, use "Mark as departed" instead.`}
    />
  );
}
