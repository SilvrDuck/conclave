/** Spec/09 §3, §7 — Proclamation. The ONLY component allowed to
 * render the drop cap. Encapsulating the rule in a component (not a
 * CSS class anyone can apply) keeps the discipline honest as the
 * codebase grows. */

import type { Proclamation as P } from "../api";
import { Linkified } from "./Linkified";
import { toRoman } from "../theme";

interface Props {
  proclamation: P;
  /** Whether to fade the drop cap in on mount (Witness page); off
   * for situations where the proclamation has already been rendered
   * (e.g. re-mount on perspective switch). */
  fadeIn?: boolean;
}

export function Proclamation({ proclamation, fadeIn = true }: Props) {
  return (
    <article style={{ position: "relative" }}>
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          gap: 12,
          marginBottom: 4,
        }}
      >
        <span className="c-numeral c-gold">№ {toRoman(proclamation.seq)}</span>
        <time
          className="c-mono c-faded"
          style={{ fontSize: 12 }}
          dateTime={proclamation.issued_at}
        >
          {new Date(proclamation.issued_at).toLocaleString()}
        </time>
      </header>
      <p
        className={`c-dropcap${fadeIn ? " c-fade-in" : ""}`}
        style={{
          fontFamily: "var(--f-body)",
          fontSize: "var(--t-proclamation)",
          textAlign: "justify",
          lineHeight: 1.55,
          margin: 0,
        }}
      >
        <Linkified text={proclamation.text} />
      </p>
    </article>
  );
}
