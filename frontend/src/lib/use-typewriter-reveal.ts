import { useRef, useState } from "react";

/**
 * A text-field value that can either be set directly (a normal controlled
 * input - the user typing) or "revealed" with a short typewriter-style
 * animation (a fresh AI draft arriving) - eased so it starts fast and
 * settles, bounded to `durationMs` regardless of text length rather than
 * a literal per-character typing speed, which would make a long
 * paragraph take unpleasantly long to appear. Used by
 * draft-review-dialog.tsx so a regenerated draft visibly writes itself
 * in instead of just snapping to the new value.
 */
export function useTypewriterReveal(initial: string, durationMs = 550) {
  const [text, setText] = useState(initial);
  const frameRef = useRef<number | null>(null);

  function reveal(fullText: string) {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    const start = performance.now();
    setText("");
    function step(now: number) {
      const progress = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic - fast start, gentle finish
      setText(fullText.slice(0, Math.round(eased * fullText.length)));
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step);
      } else {
        frameRef.current = null;
      }
    }
    frameRef.current = requestAnimationFrame(step);
  }

  return { text, setText, reveal };
}
