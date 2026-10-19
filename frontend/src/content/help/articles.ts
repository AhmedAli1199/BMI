/** The Help Centre's articles (docs/help-centre-plan.md). One object per task, written for the people using BMI Brain,
 * not for developers. Inside any text: **bold** for what's on screen, [words](article-slug) for another article and
 * [words](/app/path) for a page in the app. Screenshots live in public/help/<slug>/<n>.png and are made by
 * docs/help-centre/shoot.mjs - re-run it when a screen changes. */

export type HelpCategory = "Getting started" | "Clients" | "Sales" | "Editorial" | "Outreach" | "The Brain" | "Admin";

export type HelpStep = {
  text: string;
  /** a screenshot number in public/help/<slug>/ */
  shot?: number;
  /** what the picture shows, for people using a screen reader */
  alt?: string;
  tip?: string;
};

export type HelpArticle = {
  slug: string;
  title: string;
  /** one line: what you'll be able to do */
  summary: string;
  category: HelpCategory;
  /** who it's for, in plain words */
  audience: string;
  minutes: number;
  /** the screenshot used on the article's card (the one that best shows the result) */
  cover?: number;
  intro?: string;
  steps: HelpStep[];
  goodToKnow?: string[];
  next?: string;
  problems?: { q: string; a: string }[];
  related: string[];
  /** the Brain's guide it was written from (backend/app/brain/help/...) */
  source: string;
};

export const CATEGORY_BLURB: Record<HelpCategory, string> = {
  "Getting started": "Find your way around BMI Brain.",
  Clients: "Contacts, companies, groups and reminders.",
  Sales: "Bookings, confirmations, proposals and invoicing.",
  Editorial: "Issues, deadlines and features.",
  Outreach: "Mail merge and email templates.",
  "The Brain": "Ask questions and get things done by chatting.",
  Admin: "The team, sections and automations.",
};

export const ARTICLES: HelpArticle[] = [
  {
    slug: "make-a-booking",
    title: "Make a booking",
    summary: "Record what a client has agreed to buy, with the issues it runs in.",
    category: "Sales",
    audience: "Salespeople",
    minutes: 3,
    cover: 7,
    intro: "A booking holds everything the client has agreed in one place: who they are, what they've bought, which issues it runs in and the price. The order confirmation is printed from it.",
    steps: [
      { text: "In the menu, go to **Sales** › **Bookings** and press **New booking** at the top right.", shot: 1, alt: "The Bookings list with the New booking button ringed" },
      { text: "Choose the client. Type the first few letters of the company in the **Client company** box and pick it from the list. **Client name as booked** fills in for you.", shot: 2, alt: "Typing Gate in the company box, with Gate Gourmet suggested" },
      { text: "Choose their contact in the same way. Their name and email address fill in. **Salesperson** and **Booking date** are already set to you and today.", shot: 3, alt: "The contact name and email filled in" },
      { text: "Add what they've bought: choose the **Title**, then the product **From the rate card**. The description and **Price each (£)** fill in from the rate card. If you agreed a different price, just change it.", shot: 4, alt: "Title, rate card product and price filled in", tip: "Selling below the rate card is fine - the booking shows how far below in **Below rate card**." },
      { text: "Under **Runs in**, choose the issue. Each one shows its date and its booking deadline. Running it more than once? Press **Another** and choose the next issue.", shot: 5, alt: "Choosing Issue 108 under Runs in" },
      { text: "Check the rest of the form - **When to invoice** is set to **As soon as allowed** unless the client agreed something else. Then, if the client has said yes, press **Confirm the booking**. Still waiting for them? Press **Pencil it in** instead - see [Pencil a booking in and confirm it later](pencil-a-booking-in).", shot: 6, alt: "The Confirm the booking and Pencil it in buttons ringed" },
      { text: "That's it. The booking opens, marked **Confirmed**, with every item in the **Schedule**.", shot: 7, alt: "The new booking, marked Confirmed, with its schedule" },
    ],
    goodToKnow: [
      "Confirming is your sign-off that the client has agreed. The items now count in the sales figures and in your commission.",
      "Accounts look over the booking later, before it's invoiced. You don't need to wait for them to send the confirmation.",
    ],
    next: "Send the client their confirmation - see [Send the confirmation](send-the-confirmation).",
    problems: [
      { q: "The company isn't in the list", a: "Check the spelling, and that the title switcher at the top isn't set to a different title. If they're a new client, add them in [Companies](/companies) first." },
      { q: "The issue I want isn't there", a: "Only issues in the editorial plan that are still open for adverts are shown. Ask whoever looks after the plan to add or reopen it." },
      { q: "I made a mistake after confirming", a: "Open the booking and press **Change**. If Accounts have already checked it, the button says **Request a change** and your change goes to them." },
    ],
    related: ["send-the-confirmation", "pencil-a-booking-in", "ask-the-brain"],
    source: "sales-orders/booking-form",
  },
  {
    slug: "send-the-confirmation",
    title: "Send the confirmation",
    summary: "Email the client their order confirmation from the booking, or record that you sent it another way.",
    category: "Sales",
    audience: "Salespeople",
    minutes: 2,
    cover: 2,
    intro: "Once a booking is confirmed, you send the client their order confirmation. It goes from your own Outlook, with the confirmation attached as a Word file.",
    steps: [
      { text: "Open the booking. While it hasn't been sent, it says **The confirmation hasn't been sent yet** in amber. Press **Email the confirmation**.", shot: 1, alt: "The amber note and the Email the confirmation button ringed" },
      { text: "Check the email. **To**, **Subject** and **Message** are filled in for you, and the confirmation is attached. Change anything you need, then press **Send**.", shot: 2, alt: "The email window with To, Subject and Message filled in", tip: "Want to see what the client gets first? Press **Print or PDF** on the booking." },
      { text: "Sent it some other way, like from your own email? Open the **…** menu and choose **I sent it another way**. Nothing is emailed - it's just recorded.", shot: 3, alt: "The More menu open with I sent it another way ringed" },
      { text: "Done. The booking now says **Confirmation sent**, with the date and who it went to.", shot: 4, alt: "Confirmation sent, with the date and email address" },
    ],
    goodToKnow: [
      "The production and accounts addresses from the booking's confirmation details are always copied in.",
      "A note is added to the client's company, so everyone can see it went.",
      "Your Outlook needs to be connected once, in [Settings](/settings). If it isn't, the email window tells you.",
    ],
    problems: [
      { q: "There's no Email the confirmation button", a: "The booking may be cancelled, or not yours to change. Ask the salesperson on the booking or a manager." },
      { q: "It says to connect Outlook", a: "Go to [Settings](/settings), connect your Outlook, then try again. Or download the Word file from the **…** menu and use **I sent it another way**." },
    ],
    related: ["make-a-booking", "pencil-a-booking-in"],
    source: "sales-orders/booking-page",
  },
  {
    slug: "pencil-a-booking-in",
    title: "Pencil a booking in and confirm it later",
    summary: "Hold the space for a client who hasn't said yes yet, then confirm it when they do.",
    category: "Sales",
    audience: "Salespeople",
    minutes: 2,
    cover: 2,
    intro: "A pencilled booking holds the space for the client while they decide. It doesn't count in the sales figures or your commission until it's confirmed.",
    steps: [
      { text: "Fill in the booking just as in [Make a booking](make-a-booking), then press **Pencil it in** instead of Confirm.", shot: 1, alt: "The new booking form with Pencil it in ringed" },
      { text: "When the client says yes, open the booking - it's marked **Pencilled** - and press **Confirm**.", shot: 2, alt: "A pencilled booking with the Confirm button ringed" },
    ],
    goodToKnow: [
      "Sending the confirmation of a pencilled booking confirms it too.",
      "Pencilled bookings show in the **Bookings** list with an amber **Pencilled** badge, so you can see what's still waiting on the client.",
    ],
    next: "Once it's confirmed, [send the confirmation](send-the-confirmation).",
    problems: [
      { q: "The client said no", a: "Open the booking, open the **…** menu and choose **Cancel the booking**, with the reason." },
    ],
    related: ["make-a-booking", "send-the-confirmation"],
    source: "sales-orders/booking-page",
  },
  {
    slug: "set-a-reminder",
    title: "Set a reminder",
    summary: "Get a nudge to follow up with a contact or company on the day you choose.",
    category: "Clients",
    audience: "Everyone",
    minutes: 1,
    cover: 3,
    steps: [
      { text: "Open the contact or company and press **Remind me**.", shot: 1, alt: "A contact page with Remind me ringed" },
      { text: "Pick when - **Tomorrow**, **1 week**, **1 month** and so on (they land at 9am), or type your own date and time. Add a note under **What about? (optional)**, then press **Set reminder**.", shot: 2, alt: "The reminder window with 1 week chosen and Set reminder ringed", tip: "Untick **Email me as well** if you only want the reminder under the bell." },
      { text: "It shows in the amber strip at the top of their page until it's done. When it's due you get a notification under the bell. Press **Done** when you've dealt with it.", shot: 3, alt: "The reminder showing in the amber strip on the contact page" },
    ],
    goodToKnow: [
      "All your reminders are in one place under [Calendar & Reminders](/reminders).",
      "You can also ask the Brain: \"remind me on Friday to call Daniel\" - see [Ask the Brain](ask-the-brain).",
    ],
    related: ["ask-the-brain"],
    source: "crm/calendar-and-reminders",
  },
  {
    slug: "ask-the-brain",
    title: "Ask the Brain",
    summary: "Get answers about the app, your clients and the figures - and have it do small jobs for you.",
    category: "The Brain",
    audience: "Everyone",
    minutes: 2,
    cover: 3,
    intro: "The Brain is BMI Brain's helper. Ask it how something works, about a client, or for the figures. It only ever uses what you're allowed to see.",
    steps: [
      { text: "Press **Ask the Brain** at the bottom right of any page (or press Ctrl+J).", shot: 1, alt: "The Ask the Brain button ringed" },
      { text: "Type your question and press Enter. It knows which page you're on, so \"why can't I change this?\" works. Use **Point at it** to show it a button, or **Screenshot** to show it part of the screen.", shot: 2, alt: "The Ask the Brain panel open, with the question box ringed" },
      { text: "Ask it to do something - set a reminder, add a note, send an email, start a booking - and it puts a card under its answer showing exactly what will happen. **Nothing happens until you press the card's button.** Press **Cancel** if it's not right.", shot: 3, alt: "A Set a reminder card with its Set the reminder button" },
    ],
    goodToKnow: [
      "Every figure it gives comes with a link to where it came from, opening in a new tab.",
      "Press the thumbs up or down under an answer to tell the team how it did. **This didn't help** sends it to them as feedback.",
    ],
    problems: [
      { q: "It says it isn't switched on", a: "An administrator needs to switch the Brain on first. Ask whoever looks after BMI Brain." },
      { q: "It says I don't have permission", a: "It only answers about what you can open yourself. If you think you should see it, ask an administrator." },
    ],
    related: ["set-a-reminder", "make-a-booking"],
    source: "platform/ask-ai",
  },
];

export const bySlug = (slug: string) => ARTICLES.find((a) => a.slug === slug);
