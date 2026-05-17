/** Spec/09 §6.4 — Phylactery. Speech-scroll message bubble.
 *
 * Sender heraldry: 16px deterministic two-letter monogram on the
 * pod's identity colour. Body in EB Garamond. Augustus's voice
 * uses gold ink and a square frame instead of a scroll. */

import { Markdown } from "./Markdown";
import { EntityLink } from "./EntityLink";
import { C, monogram, podHue } from "../theme";

interface Props {
  sender: string;
  body: string;
  sentAt?: string;
  /** Display "from" label override. Defaults to `sender`. */
  label?: string;
}

const AUGUSTUS = "__augustus__";

export function Phylactery({ sender, body, sentAt, label }: Props) {
  const isAugustus = sender === AUGUSTUS;
  const senderLabel = isAugustus ? "Augustus" : label || sender;
  const hue = isAugustus ? C.gold : podHue(sender);
  const monoLetter = isAugustus ? "AV" : monogram(sender);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "32px 1fr",
        gap: 12,
        margin: "8px 0",
      }}
    >
      {/* Heraldry */}
      <div
        aria-hidden
        style={{
          width: 32,
          height: 32,
          background: hue,
          color: isAugustus ? C.ink : C.parchment,
          borderRadius: isAugustus ? 2 : "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "var(--f-display)",
          fontWeight: 600,
          fontSize: 12,
          letterSpacing: 0,
        }}
      >
        {monoLetter}
      </div>

      {/* Scroll body */}
      <div
        style={{
          background: isAugustus ? C.vellum : C.parchment,
          border: `0.5px solid ${C.inkFaded}`,
          borderRadius: isAugustus ? 2 : 6,
          padding: "8px 12px",
          color: isAugustus ? C.gold : C.ink,
          fontFamily: "var(--f-body)",
          fontSize: "var(--t-body)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
            marginBottom: 4,
            gap: 8,
          }}
        >
          {isAugustus ? (
            <span className="c-display-sm c-gold">{senderLabel}</span>
          ) : (
            <EntityLink kind="pod" id={sender}>
              <span className="c-display-sm">{senderLabel}</span>
            </EntityLink>
          )}
          {sentAt ? (
            <span className="c-mono c-faded">{formatSentAt(sentAt)}</span>
          ) : null}
        </div>
        <Markdown body={body} />
      </div>
    </div>
  );
}

function formatSentAt(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
