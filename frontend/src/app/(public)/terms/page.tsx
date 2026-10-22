import type { Metadata } from "next";
import { LegalPage, Section } from "@/components/legal-page";
import { LEGAL } from "@/content/legal";

export const metadata: Metadata = { title: `Terms - ${LEGAL.product}` };

/** Public: the terms for using BMI Brain and BMI Notetaker. */
export default function TermsPage() {
  return (
    <LegalPage title="Terms of use" updated={LEGAL.updated}
      intro={`These terms cover ${LEGAL.product} and ${LEGAL.notetaker}. They're for ${LEGAL.owner}'s own staff - the service isn't offered to anyone else.`}>
      <Section title="Who can use it">
        <p>Only people {LEGAL.owner} has given a login to. Keep your login to yourself, and tell us straight away if you think someone else has used it.</p>
      </Section>

      <Section title="Using the notetaker fairly">
        <ul>
          <li>Only send {LEGAL.notetaker} into calls you&apos;re part of, for BMI work.</li>
          <li>Let the people in the call know it&apos;s taking notes. It joins with its own name, and on Zoom it only joins with you there.</li>
          <li>If anyone in the call doesn&apos;t want to be recorded, remove the notetaker or press Stop.</li>
          <li>Notes are written by AI, so check anything important before relying on it.</li>
        </ul>
      </Section>

      <Section title="Connected accounts">
        <p>When you connect your email, calendar or Zoom, you allow {LEGAL.product} to use it as described on the <a className="underline" href="/privacy">Privacy</a> page. You can disconnect at any time from the app, or remove BMI Notetaker from your Zoom account&apos;s apps.</p>
      </Section>

      <Section title="Your responsibilities">
        <p>Use {LEGAL.product} lawfully and in line with BMI&apos;s own policies, including on data protection and confidentiality. Don&apos;t try to get into parts of it your role doesn&apos;t cover, or to stop it working for others.</p>
      </Section>

      <Section title="Availability and changes">
        <p>We work to keep {LEGAL.product} running and to fix problems quickly, but we can&apos;t promise it will never be unavailable. We may change how it works, and these terms; the date at the top shows when they last changed.</p>
      </Section>

      <Section title="Contact">
        <p>Questions about these terms: <a className="underline" href={`mailto:${LEGAL.supportEmail}`}>{LEGAL.supportEmail}</a>.</p>
      </Section>
    </LegalPage>
  );
}
