/** Click-traverse plumbing. Spec/09 §0 interconnection invariant:
 * every domain entity is a node in a navigable graph. Click any
 * pod / proclamation / proposal / council / decision / endpoint /
 * app → opens a Folio Drawer over the current perspective. The
 * drawer's own links open into a stacked drawer.
 *
 * Implemented as React context so any descendant can call
 * `useFolio().open({...})` without prop-drilling. */

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type EntityKind =
  | "pod"
  | "proclamation"
  | "decision"
  | "proposal"
  | "council"
  | "endpoint"
  | "app";

export interface EntityRef {
  kind: EntityKind;
  /** Stable id for the entity. For proclamations this is the seq
   * (stringified). For endpoints this is `${pod_id}|${method}|${path}`. */
  id: string;
  /** Optional label to show in the drawer header when the id isn't
   * human-readable on its own. */
  label?: string;
}

interface FolioCtx {
  stack: EntityRef[];
  open: (ref: EntityRef) => void;
  pop: () => void;
  clear: () => void;
}

const FolioContext = createContext<FolioCtx | null>(null);

const MAX_STACK = 16;

export function FolioProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<EntityRef[]>([]);

  const open = useCallback((ref: EntityRef) => {
    setStack((prev) => {
      const top = prev[prev.length - 1];
      // Dedup: clicking the same entity twice in a row is a no-op.
      if (top && top.kind === ref.kind && top.id === ref.id) return prev;
      // Hard cap to prevent infinite-stack from a buggy link.
      if (prev.length >= MAX_STACK) return [...prev.slice(1), ref];
      return [...prev, ref];
    });
  }, []);

  const pop = useCallback(() => {
    setStack((prev) => prev.slice(0, -1));
  }, []);

  const clear = useCallback(() => setStack([]), []);

  return (
    <FolioContext.Provider value={{ stack, open, pop, clear }}>
      {children}
    </FolioContext.Provider>
  );
}

export function useFolio(): FolioCtx {
  const ctx = useContext(FolioContext);
  if (!ctx) throw new Error("useFolio must be used inside <FolioProvider>");
  return ctx;
}
