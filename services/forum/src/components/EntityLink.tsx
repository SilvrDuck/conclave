/** Spec/09 §6 — Ink-link. The only blue thing in the system.
 * Wrap any reference to a domain entity; click opens its folio. */

import type { ReactNode } from "react";
import { useFolio, type EntityKind } from "../folio";

interface Props {
  kind: EntityKind;
  id: string;
  label?: string;
  children: ReactNode;
}

export function EntityLink({ kind, id, label, children }: Props) {
  const folio = useFolio();
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        folio.open({ kind, id, label });
      }}
      className="c-link"
      style={{
        background: "none",
        border: "none",
        padding: 0,
        font: "inherit",
      }}
    >
      {children}
    </button>
  );
}
