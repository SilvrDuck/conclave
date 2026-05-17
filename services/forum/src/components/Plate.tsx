/** Spec/09 §6.5 — Plate. Decision card.
 *
 * 18th-century scientific-journal plate: 1px rule top + bottom,
 * decision title in Cinzel, body in EB Garamond, sealed footer
 * in scribal numerals, affected-pods row of clickable monograms. */

import { Markdown } from "./Markdown";
import { EntityLink } from "./EntityLink";
import { C, monogram, podHue } from "../theme";

interface Props {
  decisionId: string;
  title: string;
  body: string | null;
  affected: string[];
  status: "placeholder" | "sealed";
  sealedAt: string | null;
}

export function Plate({ decisionId, title, body, affected, status, sealedAt }: Props) {
  const sealed = status === "sealed";
  return (
    <article
      style={{
        background: C.vellum,
        borderTop: `1px solid ${sealed ? C.gold : C.inkFaded}`,
        borderBottom: `1px solid ${sealed ? C.gold : C.inkFaded}`,
        padding: "16px 20px",
        margin: "12px 0",
      }}
    >
      <header style={{ marginBottom: 8 }}>
        <h3
          className="c-display"
          style={{ margin: 0, fontSize: "var(--t-heading)" }}
        >
          {title}
        </h3>
        <div className="c-mono c-faded" style={{ marginTop: 2 }}>
          {decisionId}
        </div>
      </header>
      <div style={{ fontSize: "var(--t-body)" }}>
        {body ? (
          <Markdown body={body} />
        ) : (
          <p className="c-faded" style={{ fontStyle: "italic" }}>
            council pending
          </p>
        )}
      </div>
      {affected.length > 0 ? (
        <footer
          style={{
            marginTop: 12,
            display: "flex",
            gap: 6,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <span className="c-display-sm c-faded" style={{ marginRight: 4 }}>
            Affected
          </span>
          {affected.map((podId) => (
            <EntityLink key={podId} kind="pod" id={podId}>
              <span
                aria-label={`pod ${podId}`}
                style={{
                  width: 22,
                  height: 22,
                  background: podHue(podId),
                  color: C.parchment,
                  borderRadius: "50%",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "var(--f-display)",
                  fontWeight: 600,
                  fontSize: 10,
                }}
              >
                {monogram(podId)}
              </span>
            </EntityLink>
          ))}
        </footer>
      ) : null}
      {sealed && sealedAt ? (
        <div
          className="c-numeral c-gold"
          style={{ marginTop: 12, fontSize: 14, fontStyle: "italic" }}
        >
          Sealed {formatScribalDate(sealedAt)}
        </div>
      ) : null}
    </article>
  );
}

const MONTHS_ROMAN = [
  "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
];

function formatScribalDate(iso: string): string {
  try {
    const d = new Date(iso);
    const day = d.getDate();
    const month = MONTHS_ROMAN[d.getMonth()];
    const year = d.getFullYear();
    return `${toRoman(day)}·${month}·${toRoman(year)}`;
  } catch {
    return iso;
  }
}

function toRoman(n: number): string {
  if (n <= 0) return "";
  const table: Array<[number, string]> = [
    [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"],
    [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
    [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
  ];
  let out = "";
  for (const [v, sym] of table) {
    while (n >= v) {
      out += sym;
      n -= v;
    }
  }
  return out;
}
