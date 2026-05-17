/** Spec/09 §6.9 — Marginalia rail. 8-px-wide gutter where
 * cross-references appear as small Cinzel scribal numerals. Click =
 * open the referenced entity in the drawer. This is where the
 * manuscript skin earns its keep: it makes the graph of everything
 * visible without cluttering the page. */

import type { EntityRef } from "../folio";
import { useFolio } from "../folio";
import { C } from "../theme";

interface Props {
  /** Each entry is one annotation: a numeral + an entity to open. */
  entries: Array<{ numeral: string; ref: EntityRef; tooltip?: string }>;
}

export function MarginaliaRail({ entries }: Props) {
  const folio = useFolio();
  if (entries.length === 0) return null;
  return (
    <aside
      aria-label="marginalia"
      style={{
        position: "absolute",
        right: 0,
        top: 0,
        bottom: 0,
        width: 28,
        display: "flex",
        flexDirection: "column",
        gap: 6,
        padding: "8px 4px",
        borderLeft: `0.5px dashed ${C.wash}`,
      }}
    >
      {entries.map((e, i) => (
        <button
          type="button"
          key={i}
          onClick={() => folio.open(e.ref)}
          title={e.tooltip}
          className="c-display-sm c-faded"
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            padding: 0,
            textAlign: "center",
          }}
        >
          {e.numeral}
        </button>
      ))}
    </aside>
  );
}
