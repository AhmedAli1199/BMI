import type { Metadata } from "next";
import { LegalPage, Section } from "@/components/legal-page";
import { LEGAL } from "@/content/legal";

export const metadata: Metadata = { title: `Privacy - ${LEGAL.product}` };

/** Public: what BMI Brain and BMI Notetaker keep, why, and how to have it removed. */
export default function PrivacyPage() {
  const mail = <a className="underline" href={`mailto:${LEGAL.supportEmail}`}>{LEGAL.supportEmail}</a>;
  return (
    <LegalPage title="Privacy" updated={LEGAL.updated}
      intro={`${LEGAL.product} is ${LEGAL.owner}'s own sales and editorial system, used only by BMI staff. This page explains what it keeps, including what ${LEGAL.notetaker} records from calls, why, and how to have it removed.`}>
      <Section title="Who is responsible">
        <p>{LEGAL.owner} decides what {LEGAL.product} is used for and is responsible for the information in it. {LEGAL.builder} builds and runs it for BMI and only uses the information to do that. Questions or requests: {mail}.</p>
      </Section>

      <Section title="What we keep">
        <ul>
          <li><b>BMI staff accounts</b>: name, work email, role and settings.</li>
          <li><b>Clients and contacts</b>: company and contact details, notes, history, bookings and invoices that BMI staff record, as in any CRM.</li>
          <li><b>Email and calendars</b>, only for staff who connect them: BMI Brain reads their work mailbox and calendar to file emails against clients and to know about meetings, and sends the emails they choose to send from BMI Brain. Calendar access is read-only.</li>
          <li><b>Calls recorded by {LEGAL.notetaker}</b>: the audio, a written transcript, the names of the people in the call and the notes written from it.</li>
          <li><b>Zoom</b>, for staff who connect their Zoom: their Zoom user ID and permission for {LEGAL.notetaker} to join a meeting on their behalf. We don&apos;t read their Zoom contacts, chats, recordings or other meetings.</li>
        </ul>
      </Section>

      <Section id="notetaker" title="How the notetaker works">
        <ul>
          <li>{LEGAL.notetaker} only joins calls that a BMI person is in: ones on their calendar (unless they skip them) or ones they send it to.</li>
          <li>It joins as a visible participant named &quot;{LEGAL.notetaker}&quot;, so everyone can see it. The host can refuse it from the waiting room or remove it at any time.</li>
          <li>On Zoom it only joins on behalf of the BMI person who connected their Zoom, once they&apos;re in the call, and it stops when they leave.</li>
          <li>The recording is turned into a transcript and notes. They&apos;re saved in BMI Brain for the BMI staff in that call and their managers, and can be added to the client&apos;s history.</li>
        </ul>
      </Section>

      <Section title="Why we use it">
        <p>To run BMI&apos;s sales and editorial work: keeping client records, following up, booking and invoicing, and remembering what was agreed on a call. Our legal basis is BMI&apos;s legitimate interest in running its business and keeping accurate client records.</p>
      </Section>

      <Section title="Who else handles it">
        <ul>
          <li><b>Google (Gemini)</b> writes the call notes and powers the Brain&apos;s answers. It processes the text for BMI; under Google&apos;s terms for paid use, it doesn&apos;t use it to train its models.</li>
          <li><b>Microsoft and Google</b> provide the mailboxes and calendars staff connect, and <b>Zoom</b> the Zoom meetings.</li>
          <li><b>Xero</b> holds BMI&apos;s invoices.</li>
          <li>{LEGAL.builder}, which runs the servers. We never sell information or use it for advertising.</li>
        </ul>
      </Section>

      <Section title="How long we keep it">
        <ul>
          <li>Call audio and transcripts are deleted from the notetaker after 30 days (BMI can shorten this). The written notes stay in BMI Brain as part of the client&apos;s history until BMI deletes them.</li>
          <li>Client records are kept for as long as BMI needs them for its business, and removed on request where the law allows.</li>
          <li>Disconnecting an email account, calendar or Zoom stops BMI Brain using it straight away.</li>
        </ul>
      </Section>

      <Section id="your-rights" title="Your rights and how to use them">
        <p>These rights apply to everyone whose information is in {LEGAL.product}, including clients and anyone in a call {LEGAL.notetaker} recorded, not only BMI staff. Under UK data protection law (the UK GDPR) you can ask us to:</p>
        <ul>
          <li><b>See your information</b>: get a copy of what we hold about you, including call recordings, transcripts and notes.</li>
          <li><b>Correct it</b> if it&apos;s wrong or incomplete.</li>
          <li><b>Delete it</b>, including a call&apos;s recording, transcript and notes.</li>
          <li><b>Restrict</b> how we use it while a question about it is being sorted out.</li>
          <li><b>Object</b> to us using it, including to being recorded. In a call, you can also just ask for the notetaker to be removed.</li>
          <li><b>Take it with you</b>: get it in a common, machine-readable format, or have it sent to someone else.</li>
          <li><b>Withdraw permission</b> you gave, for example by disconnecting your Zoom, email or calendar (see <a className="underline" href="/support#remove-zoom">Support</a>).</li>
        </ul>
        <p><b>How to ask:</b> email {mail} and say what you&apos;d like. It&apos;s free. We may ask you to confirm who you are, and we reply within one month (we&apos;ll tell you if a complex request needs longer, up to two more months). If we can&apos;t do all of what you asked, for example because the law requires us to keep an invoice, we&apos;ll explain why.</p>
        <p><b>If you&apos;re unhappy</b> with how we&apos;ve handled your information, please tell us first. You can also complain to the Information Commissioner&apos;s Office: ico.org.uk, or 0303 123 1113.</p>
      </Section>

      <Section title="Where it's stored">
        <p>{LEGAL.product} and {LEGAL.notetaker} run on servers that {LEGAL.builder} operates for BMI. Some of the services named above, such as Google, Microsoft and Zoom, may handle information outside the UK. When they do, it&apos;s protected by the safeguards UK law requires, such as the UK&apos;s adequacy decisions or the standard contract clauses those companies use.</p>
      </Section>

      <Section title="Keeping it safe">
        <p>BMI Brain is only open to BMI staff with their own login, and each person only sees what their role allows. Passwords, connection keys and Zoom permissions are stored encrypted, and everything travels over secure (HTTPS) connections.</p>
      </Section>
    </LegalPage>
  );
}
