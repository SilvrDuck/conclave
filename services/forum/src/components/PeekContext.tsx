import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from "react";

/** A peekable entity. The full list maps spec/01-jtbd's interconnection
 * invariant: every mention of a domain entity should be navigable. */
export type EntityKind =
  | "pod"
  | "proclamation"
  | "decision"
  | "proposal"
  | "council"
  | "endpoint";

export type EntityRef = {
  kind: EntityKind;
  id: string;
  /** Optional display hint (e.g. method+path for endpoints). */
  label?: string;
};

type PeekContextValue = {
  stack: EntityRef[];
  /** Push a new entity onto the peek stack. Stacking lets users
   * traverse a chain without losing where they came from. */
  push: (ref: EntityRef) => void;
  /** Pop the topmost peek. Returns to the previous one. */
  pop: () => void;
  /** Clear the stack — close everything. */
  clear: () => void;
};

const PeekContext = createContext<PeekContextValue | null>(null);

const MAX_STACK_DEPTH = 16;

export function PeekProvider({ children }: { children: ReactNode }) {
  const [stack, setStack] = useState<EntityRef[]>([]);
  const push = useCallback((ref: EntityRef) => {
    setStack((s) => {
      // Dedup: if the topmost peek already shows this entity, no-op.
      const top = s[s.length - 1];
      if (top && top.kind === ref.kind && top.id === ref.id) return s;
      // Bound depth: if the user navigates in a cycle, drop the
      // oldest entry so we don't grow unboundedly.
      const next = [...s, ref];
      return next.length > MAX_STACK_DEPTH
        ? next.slice(next.length - MAX_STACK_DEPTH)
        : next;
    });
  }, []);
  const pop = useCallback(() => setStack((s) => s.slice(0, -1)), []);
  const clear = useCallback(() => setStack([]), []);
  return (
    <PeekContext.Provider value={{ stack, push, pop, clear }}>
      {children}
    </PeekContext.Provider>
  );
}

export function usePeek(): PeekContextValue {
  const ctx = useContext(PeekContext);
  if (!ctx) {
    throw new Error("usePeek must be used inside <PeekProvider/>");
  }
  return ctx;
}
