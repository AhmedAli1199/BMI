import type { Metadata } from "next";
import { LegalPage, Section } from "@/components/legal-page";
import { LEGAL } from "@/content/legal";

export const metadata: Metadata = { title: `Zoom review test plan - ${LEGAL.notetaker}` };

/** Public: the step-by-step test plan for Zoom's Marketplace reviewers (no passwords here - the reviewer login is
 * given in the submission's "Test account and credentials" box). */
export default function ZoomTestPlanPage() {
  return (
    <LegalPage title="Test plan for Zoom reviewers" updated={LEGAL.updated}
      intro={`How to test ${LEGAL.notetaker}: connecting a Zoom account, the notetaker joining a Zoom meeting on that person's behalf, the notes it writes, and removing the app. It takes about 15 minutes. There is one kind of user (a BMI salesperson); the reviewer login is in the submission's "Test account and credentials".`}>
      <Section title="What you need">
        <ul>
          <li>The BMI Brain reviewer login from the submission. It can only see test clients, not real BMI data.</li>
          <li>A Zoom account to connect (the reviewer&apos;s own is fine), and a second Zoom account or device to join the meeting as a guest, so there is someone to talk to.</li>
        </ul>
      </Section>

      <Section title="Scopes and why they're used">
        <ul>
          <li><b>user:read:user</b> (View a user): once, when connecting, to read the Zoom user ID and account ID (GET /v2/users/me), so we know whose Zoom it is.</li>
          <li><b>user:read:token</b> (View a user&apos;s token): just before each Zoom meeting, to get the &quot;On Behalf Of&quot; token for that meeting (GET /v2/users/me/token?type=onbehalf&amp;meeting_id=…). Zoom requires it for notetakers to join meetings outside their own account; the notetaker can only join once that user is in the meeting.</li>
          <li>No other scopes. Event subscription: &quot;App deauthorized&quot; only.</li>
        </ul>
      </Section>

      <Section title="1. Connect Zoom (tests authorisation and user:read:user)">
        <ul>
          <li>Go to <a className="underline" href="/zoom">bmi.rabtaai.com/zoom</a> and press <b>Connect Zoom</b>. Sign in to BMI Brain with the reviewer login when asked.</li>
          <li>Zoom&apos;s consent screen opens: sign in to Zoom and press <b>Allow</b>.</li>
          <li>You land on <b>Call notes, Meetings</b>. A green message says &quot;Zoom connected&quot;, and under <b>Your calendars</b> the <b>Zoom</b> row says &quot;Connected - the notetaker can join your Zoom calls&quot;.</li>
        </ul>
      </Section>

      <Section title="2. Send the notetaker into a Zoom meeting (tests user:read:token)">
        <ul>
          <li>Start a Zoom meeting from the Zoom account you connected, and copy its invite link.</li>
          <li>In BMI Brain, on <b>Call notes, Meetings</b>, paste the link into <b>Send the notetaker</b> (optionally add a title, e.g. &quot;Zoom review&quot;) and press <b>Send</b>.</li>
          <li>Within a couple of minutes &quot;BMI Notetaker&quot; asks to join the meeting. Admit it from the waiting room if there is one. It shows in the participant list.</li>
          <li>Talk for a minute or two with the second account, e.g. about booking an advert in a magazine issue, a price and a follow-up date.</li>
          <li>Leave the meeting as the connected user: the notetaker leaves too (Zoom ends its session when the authorising user leaves).</li>
        </ul>
      </Section>

      <Section title="3. Read the notes">
        <ul>
          <li>Open <b>Call notes, Recorded calls</b> and the call. Within a few minutes of the meeting ending its status becomes Completed.</li>
          <li>You see a summary, actions with who does them and when, money and dates mentioned, and the full transcript with speaker names.</li>
        </ul>
      </Section>

      <Section title="4. Remove the app (tests revoking and deauthorisation)">
        <ul>
          <li><b>From BMI Brain:</b> on <b>Call notes, Meetings, Your calendars</b>, next to Zoom press <b>Disconnect</b> and confirm. The token is revoked at Zoom (POST /oauth/revoke) and deleted; the row shows &quot;Connect Zoom&quot; again.</li>
          <li><b>From Zoom:</b> connect again (step 1), then in the Zoom App Marketplace go to <b>Manage, Added Apps</b>, find {LEGAL.notetaker} and press <b>Remove</b>. Zoom sends the App deauthorized event; the sign-in is deleted, and BMI Brain shows Zoom as needing reconnection with a notification.</li>
          <li>Either way, sending the notetaker to a Zoom link now asks you to connect Zoom first.</li>
        </ul>
      </Section>

      <Section title="Documentation and contacts">
        <p>User documentation (adding, using, removing, troubleshooting): <a className="underline" href="/support">bmi.rabtaai.com/support</a>. Privacy: <a className="underline" href="/privacy">bmi.rabtaai.com/privacy</a>. Questions during the review: <a className="underline" href={`mailto:${LEGAL.supportEmail}`}>{LEGAL.supportEmail}</a>.</p>
      </Section>
    </LegalPage>
  );
}
