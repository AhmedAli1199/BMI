import type { Metadata } from "next";
import { LegalPage, Section } from "@/components/legal-page";
import { LEGAL } from "@/content/legal";

export const metadata: Metadata = { title: `Support - ${LEGAL.product}` };

/** Public: how to get help, and how to connect and remove BMI Notetaker on Zoom (Zoom asks apps to explain this). */
export default function SupportPage() {
  const mail = <a className="underline" href={`mailto:${LEGAL.supportEmail}`}>{LEGAL.supportEmail}</a>;
  return (
    <LegalPage title="Support" updated={LEGAL.updated}
      intro={`Help with ${LEGAL.product} and ${LEGAL.notetaker}. Signed-in BMI staff can also press the "?" Help button in the app, ask the Brain, or send Feedback from any page.`}>
      <Section title="Contact us">
        <p>Email {mail}. We reply on working days, usually the same day. Tell us what you were doing and, if you can, include a screenshot.</p>
      </Section>

      <Section id="connect-zoom" title="Connect your Zoom">
        <ul>
          <li>Sign in to BMI Brain and open <b>Call notes</b>, then <b>Meetings</b>.</li>
          <li>Under <b>Your calendars</b>, next to <b>Zoom</b>, press <b>Connect Zoom</b>.</li>
          <li>Sign in to Zoom with your own account and press <b>Allow</b>. You&apos;re taken back to BMI Brain, which shows Zoom as connected.</li>
        </ul>
        <p>From then on, {LEGAL.notetaker} can join your Zoom calls. It joins once you&apos;re in the call and stops if you leave, so stay until the end.</p>
      </Section>

      <Section id="use" title="Using the notetaker">
        <ul>
          <li>Meetings on your connected calendar are joined automatically, unless you press <b>Skip</b> or have chosen &quot;Just remind me&quot; or &quot;Do nothing&quot;.</li>
          <li>For any other call, paste its link into <b>Send the notetaker</b> on Call notes.</li>
          <li>Let &quot;{LEGAL.notetaker}&quot; in from the waiting room if the meeting has one. The notes appear in Call notes after the call.</li>
        </ul>
      </Section>

      <Section id="remove-zoom" title="Remove the notetaker from your Zoom">
        <ul>
          <li><b>In BMI Brain:</b> Call notes, Meetings, Your calendars, next to Zoom press <b>Disconnect</b>.</li>
          <li><b>Or in Zoom:</b> sign in at marketplace.zoom.us, choose <b>Manage</b>, then <b>Added Apps</b>, find {LEGAL.notetaker} and press <b>Remove</b>.</li>
        </ul>
        <p>Either way, {LEGAL.notetaker} can&apos;t join your Zoom calls any more and BMI Brain stops using your Zoom permission. Notes from earlier calls stay in BMI Brain; email {mail} to have them deleted.</p>
      </Section>

      <Section title="Something's not right">
        <ul>
          <li><b>The notetaker didn&apos;t join a Zoom call:</b> check Zoom shows as connected (not &quot;Needs reconnecting&quot;), that you joined the call, and that someone let it in from the waiting room.</li>
          <li><b>No notes after a call:</b> they can take a few minutes. If nobody spoke, there are none.</li>
          <li><b>Anything else:</b> email {mail}.</li>
        </ul>
      </Section>
    </LegalPage>
  );
}
