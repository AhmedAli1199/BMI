/** True while a pop-up blocks the page (a dialog, menu or list hides the rest of the page from screen readers), so
 * the floating Ask the Brain and Feedback buttons step aside. Side panels don't block the page, so they stay. */
export const PAGE_BLOCKED = 'div[data-base-ui-inert][aria-hidden="true"], div[data-base-ui-inert][inert]';

/** Attributes to watch so the check runs again when a pop-up opens or closes. */
export const BLOCKED_ATTRIBUTES = ["data-base-ui-inert", "aria-hidden", "inert"];
