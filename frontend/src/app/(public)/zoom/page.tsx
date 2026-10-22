import type { Metadata } from "next";
import { getSession } from "@/lib/session";
import { LegalPage, Section } from "@/components/legal-page";
import { Button } from "@/components/ui/button";
import { LEGAL } from "@/content/legal";

export const metadata: Metadata = { title: `${LEGAL.notetaker} for Zoom - ${LEGAL.product}` };

/** Public: the Zoom app's landing page ("Adding your app": From your site). Signed-in staff connect Zoom from here;
 * anyone else is told what it is and who to contact. */
export default async function ZoomLandingPage() {
  const session = await getSession();
  return (
    <LegalPage title={`${LEGAL.notetaker} for Zoom`} updated={LEGAL.updated}
      intro={`${LEGAL.notetaker} joins your Zoom sales calls as a visible participant and writes up the notes in ${LEGAL.product}: a summary, the actions agreed and who does them, and the full transcript, saved onto the client's history. It's ${LEGAL.owner}'s own tool, for BMI staff.`}>
      <div className="flex flex-wrap items-center gap-3">
        <Button nativeButton={false} render={<a href="/api/zoom/connect" />}>Connect Zoom</Button>
        <span className="text-sm text-muted-foreground">
          {session ? `Signed in as ${session.name || session.email}.` : "You'll be asked to sign in to BMI Brain first."}
        </span>
      </div>

      <Section title="What it does">
        <ul>
          <li>Joins the Zoom meetings on your calendar (you can skip any), or any Zoom link you send it.</li>
          <li>Joins on your behalf, once you&apos;re in the call, and leaves when you leave. Everyone in the call can see it.</li>
          <li>Writes the notes in BMI Brain after the call: summary, actions, money and dates mentioned, and the transcript.</li>
        </ul>
      </Section>

      <Section title="Before you start">
        <ul>
          <li>A BMI Brain login. {LEGAL.product} is for {LEGAL.owner} staff only; if you work at BMI and don&apos;t have one, ask your manager.</li>
          <li>Your own Zoom account (a free one is fine).</li>
        </ul>
      </Section>

      <Section title="Help">
        <p>Step-by-step guides for connecting, using and removing it are on the <a className="underline" href="/support">Support</a> page. How your information is handled: <a className="underline" href="/privacy">Privacy</a>.</p>
      </Section>
    </LegalPage>
  );
}
