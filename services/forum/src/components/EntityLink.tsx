import { type ReactNode } from "react";
import { usePeek, type EntityKind } from "./PeekContext";

type Props = {
  kind: EntityKind;
  id: string;
  /** Optional override for the displayed label. Defaults to the id. */
  children?: ReactNode;
};

/** Inline clickable token referencing a domain entity. Click → push
 * onto the PeekDrawer stack so the user can traverse the graph of
 * entities without losing the current view (spec/01 interconnection
 * invariant — every mention of an entity is itself a node). */
export function EntityLink({ kind, id, children }: Props) {
  const { push } = usePeek();
  return (
    <button
      type="button"
      className="entity-link"
      onClick={(e) => {
        e.stopPropagation();
        push({ kind, id, label: typeof children === "string" ? children : undefined });
      }}
    >
      {children ?? id}
    </button>
  );
}
